"""Перевод английских новостей на языки интерфейса через CheapVibeCode."""

from __future__ import annotations

import asyncio
import json
import logging
import re

import config
from db import Database
from models import CATEGORIES, Article

log = logging.getLogger(__name__)

_LOCK = asyncio.Lock()
_LANG_NAME = {
    "ru": "Russian",
    "ar": "Arabic",
}

_ALLOWED = ", ".join(CATEGORIES)
_SYSTEM = (
    "You translate financial news and label topics. Return only JSON with the shape "
    '{"items":[{"id":1,"title":"...","summary":"...","body":"...","topics":["oil","macro"]}]}. '
    "Keep every number, ticker, company name, and the meaning of the source. "
    "Do not add facts, prices, forecasts, or advice. "
    "If summary or body is empty, return an empty string for that field. "
    "The id values must be copied unchanged. "
    f"topics must be a subset of [{_ALLOWED}]. "
    "A story may have several topics. Use markets only when nothing else fits."
)

_TOPIC_ALIASES = {
    "oil": "oil",
    "energy": "oil",
    "gas": "oil",
    "crude": "oil",
    "oil and gas": "oil",
    "crypto": "crypto",
    "cryptocurrency": "crypto",
    "cryptocurrencies": "crypto",
    "bitcoin": "crypto",
    "macro": "macro",
    "economy": "macro",
    "economics": "macro",
    "monetary": "macro",
    "rates": "macro",
    "stocks": "stocks",
    "equities": "stocks",
    "shares": "stocks",
    "equity": "stocks",
    "markets": "markets",
    "market": "markets",
    "general": "markets",
    "business": "markets",
}


def normalize_topics(raw: object) -> tuple[str, ...]:
    values: list[str] = []
    if isinstance(raw, str):
        raw = [part.strip() for part in raw.split(",")]
    if not isinstance(raw, list):
        return ()
    for item in raw:
        key = str(item or "").strip().lower().replace("_", " ")
        mapped = _TOPIC_ALIASES.get(key, key if key in CATEGORIES else "")
        if mapped and mapped not in values:
            values.append(mapped)
    if "markets" in values and len(values) > 1:
        values = [item for item in values if item != "markets"]
    return tuple(values)


def parse_translation_payload(raw: str) -> list[dict[str, object]]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text.strip(), flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    if start > 0:
        text = text[start:]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data, _ = json.JSONDecoder().raw_decode(text)
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("translation payload has no items")
    parsed: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict) or "id" not in item:
            continue
        parsed.append(
            {
                "id": str(item["id"]),
                "title": str(item.get("title") or "").strip(),
                "summary": str(item.get("summary") or "").strip(),
                "body": str(item.get("body") or "").strip(),
                "topics": normalize_topics(item.get("topics")),
            }
        )
    return parsed


def _chunks(items: list[Article], size: int) -> list[list[Article]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _rows_from_content(
    content: str, articles: list[Article]
) -> list[tuple[Article, str, str, str, tuple[str, ...]]]:
    by_id = {article.id: article for article in articles}
    ready: list[tuple[Article, str, str, str, tuple[str, ...]]] = []
    for item in parse_translation_payload(content):
        article = by_id.get(int(item["id"]))
        title = str(item.get("title") or "")
        if article is None or not title:
            continue
        topics = item.get("topics")
        ready.append(
            (
                article,
                title,
                str(item.get("summary") or ""),
                str(item.get("body") or ""),
                topics if isinstance(topics, tuple) else (),
            )
        )
    return ready


async def _translate_with_model(
    client: object,
    model: str,
    articles: list[Article],
    lang: str,
) -> list[tuple[Article, str, str, str, tuple[str, ...]]]:
    language = _LANG_NAME.get(lang, lang)
    payload = {
        "language": language,
        "items": [
            {
                "id": article.id,
                "title": article.title,
                "summary": article.summary[:900],
                "body": article.body[:4500],
            }
            for article in articles
        ],
    }
    response = await client.chat.completions.create(
        model=model,
        temperature=0,
        max_tokens=8000,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Translate every item into {language} and set topics.\n"
                    f"{json.dumps(payload, ensure_ascii=False)}"
                ),
            },
        ],
    )
    content = response.choices[0].message.content or ""
    return _rows_from_content(content, articles)


async def _translate_batch(articles: list[Article], lang: str) -> list[tuple[Article, str, str, str, tuple[str, ...]]]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=config.CVC_API_KEY, base_url=config.CVC_BASE_URL)
    last_error: Exception | None = None
    for model in config.CVC_MODELS:
        try:
            rows = await _translate_with_model(client, model, articles, lang)
        except Exception as exc:
            last_error = exc
            log.warning("translation model %s failed: %s", model, exc)
            continue
        if rows:
            log.info("translated %s stories with %s into %s", len(rows), model, lang)
            return rows
        log.warning("translation model %s returned no usable titles", model)
    if last_error is not None:
        raise last_error
    return []


async def translate_pending(database: Database, *, limit: int = 40) -> int:
    if not config.CVC_API_KEY or not config.TRANSLATION_LANGS:
        return 0
    async with _LOCK:
        done = 0
        write_lock = asyncio.Lock()
        gate = asyncio.Semaphore(4)

        async def run_batch(lang: str, batch: list[Article]) -> int:
            async with gate:
                try:
                    rows = await _translate_batch(batch, lang)
                except Exception:
                    log.exception("translation batch failed for %s", lang)
                    return 0
            if not rows:
                return 0
            async with write_lock:
                await database.save_translations(lang, rows)
            return len(rows)

        for lang in config.TRANSLATION_LANGS:
            missing = await database.articles_missing_translation(lang, limit)
            short = [article for article in missing if len(article.body) <= 1800]
            long = [article for article in missing if len(article.body) > 1800]
            batches = _chunks(short, 4) + [[article] for article in long]
            if not batches:
                continue
            counts = await asyncio.gather(*(run_batch(lang, batch) for batch in batches))
            done += sum(counts)
        if done:
            log.info("translated %s stories", done)
        return done
