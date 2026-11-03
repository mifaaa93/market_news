"""GNews top-headlines: один запрос на язык, источники появляются из ответов."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import aiohttp

import config
from content import classify_topics, clean_image_url, clean_text, clean_url, one_line, title_norm

log = logging.getLogger(__name__)

UA = "MarketNews/2.0"


@dataclass(frozen=True)
class IncomingArticle:
    guid: str
    title: str
    title_norm: str
    summary: str
    body: str
    url: str
    image_url: str
    category: str
    published_at: str
    lang: str
    source_name: str
    source_url: str
    source_extra: dict
    origin: str = "search"
    top_rank: int | None = None
    categories: tuple[str, ...] = ()


def parse_published(value: str, fallback: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return fallback
    try:
        if raw.endswith("Z"):
            moment = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        else:
            moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return fallback


def parse_articles(payload: dict, lang: str, *, now: str | None = None) -> list[IncomingArticle]:
    fetched = now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    items: list[IncomingArticle] = []
    for raw in payload.get("articles") or []:
        if not isinstance(raw, dict):
            continue
        title = one_line(clean_text(str(raw.get("title") or "")))
        if len(title) < 8:
            continue
        norm = title_norm(title)
        if len(norm) < 8:
            continue
        url = clean_url(str(raw.get("url") or ""))
        if not url:
            continue
        summary = one_line(clean_text(str(raw.get("description") or "")))[:700]
        body = clean_text(str(raw.get("content") or ""))[:4000] or summary
        source = raw.get("source") if isinstance(raw.get("source"), dict) else {}
        source_name = one_line(str(source.get("name") or ""))[:200]
        if not source_name:
            continue
        source_url = str(source.get("url") or "").strip()
        extra = {key: value for key, value in source.items() if key not in {"name", "url"}}
        topics = tuple(classify_topics(title, f"{summary}\n{body}"))
        items.append(
            IncomingArticle(
                guid=url[:500],
                title=title,
                title_norm=norm,
                summary=summary,
                body=body,
                url=url,
                image_url=clean_image_url(str(raw.get("image") or ""), trusted=True),
                category=topics[0],
                published_at=parse_published(str(raw.get("publishedAt") or ""), fetched),
                lang=lang,
                source_name=source_name,
                source_url=source_url[:500],
                source_extra=extra,
                categories=topics,
            )
        )
    return items


def requests_per_cycle() -> int:
    return len(config.GNEWS_LANGS)


def headlines_params(lang: str) -> dict[str, str]:
    return {
        "category": config.GNEWS_CATEGORY,
        "lang": lang,
        "max": str(config.GNEWS_MAX),
        "nullable": "image",
        "apikey": config.GNEWS_API_KEY,
    }


def search_params(
    lang: str, *, page: int = 1, since: str | None = None
) -> dict[str, str]:
    params = {
        "q": config.GNEWS_QUERY,
        "lang": lang,
        "max": str(config.GNEWS_MAX),
        "sortby": "publishedAt",
        "page": str(max(1, page)),
        "nullable": "image",
        "apikey": config.GNEWS_API_KEY,
    }
    if since:
        params["from"] = since
    return params


def mark_origin(
    items: list[IncomingArticle], origin: str, *, ranked: bool = False
) -> list[IncomingArticle]:
    marked: list[IncomingArticle] = []
    for index, item in enumerate(items, start=1):
        marked.append(
            IncomingArticle(
                **{
                    **item.__dict__,
                    "origin": origin,
                    "top_rank": index if ranked else None,
                }
            )
        )
    return marked


async def fetch_lang(
    session: aiohttp.ClientSession,
    lang: str,
    *,
    kind: str,
    page: int = 1,
    since: str | None = None,
) -> dict | None:
    if kind == "top":
        params = headlines_params(lang)
        path = "top-headlines"
    else:
        params = search_params(lang, page=page, since=since)
        path = "search"
    url = f"{config.GNEWS_BASE_URL}/{path}"
    try:
        async with session.get(url, params=params) as response:
            body = await response.json(content_type=None)
            if response.status != 200:
                log.warning(
                    "gnews %s %s page=%s status %s body=%s",
                    kind,
                    lang,
                    page,
                    response.status,
                    body,
                )
                return None
            if not isinstance(body, dict):
                return None
            if body.get("errors"):
                log.warning("gnews %s %s errors=%s", kind, lang, body.get("errors"))
            return body
    except Exception:
        log.exception("gnews %s %s request failed", kind, lang)
        return None


async def fetch_all_langs(
    session: aiohttp.ClientSession, *, kind: str
) -> dict[str, list[IncomingArticle]]:
    result: dict[str, list[IncomingArticle]] = {}
    for index, lang in enumerate(config.GNEWS_LANGS):
        if index:
            await asyncio.sleep(1.1)
        payload = await fetch_lang(session, lang, kind=kind)
        if payload is None:
            result[lang] = []
            continue
        items = parse_articles(payload, lang)
        log.info("gnews %s %s articles=%s total=%s", kind, lang, len(items), payload.get("totalArticles"))
        result[lang] = items
    return result
