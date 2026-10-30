"""Перевод новостей через CheapVibeCode. Сейчас русский, арабский добавляется в TRANSLATION_LANGS."""

from __future__ import annotations

import asyncio
import json
import logging
import re

import config
from db import Database
from models import Article

log = logging.getLogger(__name__)

_LOCK = asyncio.Lock()
_LANG_NAME = {
    "ru": "Russian",
    "ar": "Arabic",
    "uk": "Ukrainian",
    "en": "English",
}

_SYSTEM = (
    "You translate financial news. Return only JSON with the shape "
    '{"items":[{"id":1,"title":"...","summary":"...","body":"..."}]}. '
    "Keep every number, ticker, company name, and the meaning of the source. "
    "Do not add facts, prices, forecasts, or advice. "
    "If summary or body is empty, return an empty string for that field. "
    "The id values must be copied unchanged."
)


def parse_translation_payload(raw: str) -> list[dict[str, str]]:
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
            }
        )
    return parsed


def _chunks(items: list[Article], size: int) -> list[list[Article]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _rows_from_content(content: str, articles: list[Article]) -> list[tuple[Article, str, str, str]]:
    by_id = {article.id: article for article in articles}
    ready: list[tuple[Article, str, str, str]] = []
    for item in parse_translation_payload(content):
        article = by_id.get(int(item["id"]))
        if article is None or not item["title"]:
            continue
        ready.append((article, item["title"], item["summary"], item["body"]))
    return ready


async def _translate_with_model(
    client: object,
    model: str,
    articles: list[Article],
    lang: str,
) -> list[tuple[Article, str, str, str]]:
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
                "content": f"Translate every item into {language}.\n{json.dumps(payload, ensure_ascii=False)}",
            },
        ],
    )
    content = response.choices[0].message.content or ""
    return _rows_from_content(content, articles)


async def _translate_batch(articles: list[Article], lang: str) -> list[tuple[Article, str, str, str]]:
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
            log.info("translated %s stories with %s", len(rows), model)
            return rows
        log.warning("translation model %s returned no usable titles", model)
    if last_error is not None:
        raise last_error
    return []


async def translate_article(database: Database, article: Article, lang: str) -> None:
    if lang not in config.TRANSLATION_LANGS or not config.CVC_API_KEY or not article.id:
        return
    hashes = await database.translation_hashes(lang, [article.id])
    from content import source_hash

    if hashes.get(article.id) == source_hash(article):
        return
    rows = await _translate_batch([article], lang)
    if rows:
        await database.save_translations(lang, rows)


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
            counts = await asyncio.gather(*(run_batch(lang, batch) for batch in batches))
            done += sum(counts)
        if done:
            log.info("translated %s stories", done)
        return done
