"""Загрузка RSS и подготовка материалов к показу внутри бота."""

from __future__ import annotations

import asyncio
import html
import logging
import re
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone

import aiohttp
import feedparser

import config
from content import clean_image_url, clean_text, clean_url, one_line, resolve_category, title_norm
from db import Database, utc_now_iso
from models import Article

log = logging.getLogger(__name__)

UA = "Mozilla/5.0 (compatible; MarketNews/1.0)"
_LOCK = asyncio.Lock()
_LAST_OK = 0.0


@dataclass(frozen=True)
class Publisher:
    key: str
    name: str
    homepage: str
    about_key: str


@dataclass(frozen=True)
class Feed:
    key: str
    name: str
    url: str
    hint: str | None


PUBLISHERS = (
    Publisher("bbc", "BBC Business", "https://www.bbc.com/news/business", "src_bbc"),
    Publisher("cnbc", "CNBC", "https://www.cnbc.com/finance/", "src_cnbc"),
    Publisher("marketwatch", "MarketWatch", "https://www.marketwatch.com/", "src_mw"),
    Publisher("oilprice", "OilPrice", "https://oilprice.com/", "src_oil"),
    Publisher("coindesk", "CoinDesk", "https://www.coindesk.com/", "src_coin"),
)

FEEDS = (
    Feed("bbc", "BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml", None),
    Feed("cnbc-finance", "CNBC", "https://www.cnbc.com/id/10000664/device/rss/rss.html", "stocks"),
    Feed("cnbc-economy", "CNBC", "https://www.cnbc.com/id/20910258/device/rss/rss.html", "macro"),
    Feed("cnbc-oil", "CNBC", "https://www.cnbc.com/id/10000030/device/rss/rss.html", "oil"),
    Feed("marketwatch", "MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories/", None),
    Feed("oilprice", "OilPrice", "https://oilprice.com/rss/main", "oil"),
    Feed("coindesk", "CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml", "crypto"),
)


def _published(entry: feedparser.FeedParserDict, fallback: str) -> str:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return fallback
    try:
        moment = datetime(*parsed[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return fallback
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


_IMG = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", re.IGNORECASE)


def _entry_html(entry: feedparser.FeedParserDict) -> str:
    chunks = [str(entry.get("summary") or ""), str(entry.get("description") or "")]
    content = entry.get("content") or []
    if content and isinstance(content, list):
        chunks.append(str(content[0].get("value") or ""))
    return "\n".join(chunks)


def entry_image(entry: feedparser.FeedParserDict) -> str:
    candidates: list[tuple[str, bool]] = []
    for media in entry.get("media_content") or []:
        url = str(media.get("url") or "")
        kind = f"{media.get('medium') or ''} {media.get('type') or ''}".lower()
        if url:
            candidates.append((url, "image" in kind or not kind.strip()))
    for thumb in entry.get("media_thumbnail") or []:
        url = str(thumb.get("url") or "")
        if url:
            candidates.append((url, True))
    for enc in list(entry.get("enclosures") or []) + list(entry.get("links") or []):
        url = str(enc.get("href") or enc.get("url") or "")
        kind = str(enc.get("type") or "").lower()
        if url and kind.startswith("image"):
            candidates.append((url, True))
    for match in _IMG.finditer(_entry_html(entry)):
        candidates.append((html.unescape(match.group(1)), True))
    for url, trusted in candidates:
        cleaned = clean_image_url(url, trusted=trusted)
        if cleaned:
            return cleaned
    return ""


def _body(entry: feedparser.FeedParserDict) -> str:
    chunks: list[str] = []
    content = entry.get("content") or []
    if content and isinstance(content, list):
        value = content[0].get("value") or ""
        if value:
            chunks.append(str(value))
    summary = entry.get("summary") or entry.get("description") or ""
    if summary:
        chunks.append(str(summary))
    cleaned = [clean_text(chunk) for chunk in chunks]
    cleaned = [chunk for chunk in cleaned if chunk]
    if not cleaned:
        return ""
    cleaned.sort(key=len, reverse=True)
    return cleaned[0][:3000]


def parse_feed(feed: Feed, raw: bytes, *, now: str | None = None) -> list[Article]:
    fetched = now or utc_now_iso()
    try:
        parsed = feedparser.parse(raw)
    except Exception:
        log.warning("feed %s could not be parsed", feed.name)
        return []
    items: list[Article] = []
    for entry in (parsed.entries or [])[:25]:
        title = one_line(clean_text(str(entry.get("title") or "")))
        if len(title) < 12:
            continue
        norm = title_norm(title)
        if len(norm) < 12:
            continue
        summary = one_line(clean_text(str(entry.get("summary") or entry.get("description") or "")))[:700]
        body = _body(entry) or summary
        raw_guid = str(entry.get("id") or entry.get("link") or norm).strip()
        guid = f"{feed.key}:{raw_guid}"[:300]
        link = clean_url(str(entry.get("link") or ""))
        text = f"{title}\n{summary}"
        items.append(
            Article(
                id=0,
                guid=guid,
                source_key=feed.key,
                source_name=feed.name,
                title=title,
                title_norm=norm,
                summary=summary,
                body=body,
                url=link,
                category=resolve_category(text, feed.hint),
                published_at=_published(entry, fetched),
                fetched_at=fetched,
                image_url=entry_image(entry),
            )
        )
    return items


def prepare_items(items: list[Article], known_norms: set[str]) -> list[Article]:
    ready: list[Article] = []
    seen = set(known_norms)
    for item in items:
        if len(item.title_norm) < 12 or item.title_norm in seen:
            continue
        url = item.url if item.url else ""
        if url and not clean_url(url):
            url = ""
        elif url:
            url = clean_url(url)
        image = clean_image_url(item.image_url) if item.image_url else ""
        item = replace(item, url=url, image_url=image)
        seen.add(item.title_norm)
        ready.append(item)
    return ready


async def _fetch(session: aiohttp.ClientSession, feed: Feed) -> list[Article]:
    try:
        async with session.get(feed.url) as response:
            if response.status != 200:
                log.warning("feed %s status %s", feed.name, response.status)
                return []
            raw = await response.read()
    except Exception as exc:
        log.warning("feed %s failed: %s", feed.name, exc)
        return []
    items = await asyncio.to_thread(parse_feed, feed, raw)
    log.info("feed %s items %s", feed.name, len(items))
    return items


async def refresh_all(database: Database) -> int:
    global _LAST_OK
    async with _LOCK:
        fresh = time.monotonic() - _LAST_OK < 30
        if fresh and await database.count_articles():
            return 0
        timeout = aiohttp.ClientTimeout(total=20)
        headers = {"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            batches = await asyncio.gather(*(_fetch(session, feed) for feed in FEEDS))
        flat = [item for batch in batches for item in batch]
        prepared = prepare_items(flat, await database.title_norms())
        saved = await database.upsert_articles(prepared)
        await database.remember_images(flat)
        removed = await database.delete_old(config.ARTICLE_KEEP_DAYS)
        if flat:
            await database.meta_set("fetched_at", utc_now_iso())
            _LAST_OK = time.monotonic()
        log.info("refresh parsed=%s saved=%s pruned=%s", len(flat), saved, removed)
        return saved
