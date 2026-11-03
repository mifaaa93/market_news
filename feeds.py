"""Загрузка RSS и подготовка материалов к показу внутри бота."""

from __future__ import annotations

import asyncio
import html
import logging
import re
import time
from urllib.parse import urljoin, urlsplit
from dataclasses import dataclass, replace
from datetime import datetime, timezone

import aiohttp
import feedparser

import config
from content import clean_image_url, clean_text, clean_url, one_line, resolve_category, title_norm
from db import Database, utc_now_iso
from models import Article, Source
from source_security import PublicResolver, public_site, safe_get, same_site

log = logging.getLogger(__name__)

UA = "Mozilla/5.0 (compatible; MarketNews/1.0)"
_LOCK = asyncio.Lock()
_LAST_OK: dict[str, float] = {}


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
    Publisher("abc-business", "ABC News Business", "https://abcnews.go.com/Business", "src_abc"),
    Publisher("bbc", "BBC Business", "https://www.bbc.com/news/business", "src_bbc"),
    Publisher("cnbc", "CNBC", "https://www.cnbc.com/finance/", "src_cnbc"),
    Publisher("oilprice", "OilPrice", "https://oilprice.com/", "src_oil"),
    Publisher("coindesk", "CoinDesk", "https://www.coindesk.com/", "src_coin"),
    Publisher("eia", "U.S. EIA", "https://www.eia.gov/todayinenergy/", "src_eia"),
    Publisher("fed", "Federal Reserve", "https://www.federalreserve.gov/newsevents.htm", "src_fed"),
)

FEEDS = (
    Feed("abc-business", "ABC News Business", "https://feeds.abcnews.com/abcnews/moneyheadlines", "stocks"),
    Feed("bbc", "BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml", None),
    Feed("cnbc-finance", "CNBC · Finance", "https://www.cnbc.com/id/10000664/device/rss/rss.html", "stocks"),
    Feed("cnbc-economy", "CNBC · Economy", "https://www.cnbc.com/id/20910258/device/rss/rss.html", "macro"),
    Feed("cnbc-oil", "CNBC · Oil", "https://www.cnbc.com/id/10000030/device/rss/rss.html", "oil"),
    Feed("oilprice", "OilPrice", "https://oilprice.com/rss/main", "oil"),
    Feed("coindesk", "CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml", "crypto"),
    Feed("eia-energy", "U.S. EIA · Energy", "https://www.eia.gov/rss/todayinenergy.xml", "oil"),
    Feed("eia-press", "U.S. EIA · Press", "https://www.eia.gov/rss/press_rss.xml", "oil"),
    Feed("fed-monetary", "Federal Reserve · Monetary policy", "https://www.federalreserve.gov/feeds/press_monetary.xml", "macro"),
    Feed("fed-speeches", "Federal Reserve · Speeches", "https://www.federalreserve.gov/feeds/speeches.xml", "macro"),
)

CATALOG_ROWS = [
    (
        feed.key,
        feed.name,
        feed.url,
        next(
            (p.homepage for p in PUBLISHERS if feed.key == p.key or feed.key.startswith(p.key + "-")),
            "",
        ),
    )
    for feed in FEEDS
]


def _custom_site_allowed(url: str) -> bool:
    return public_site(url)


async def discover_custom_feed(url: str) -> tuple[str, str, bytes] | None:
    """Compatibility entry point for the validated discovery pipeline."""
    from rss_discovery import discover_custom_feed as discover

    return await discover(url)


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
        raw_link = str(entry.get("link") or "")
        if feed.key == "eia-press" and raw_link.startswith("/"):
            raw_link = urljoin("https://www.eia.gov", raw_link)
        if (
            feed.key.startswith("custom:")
            and _custom_site_allowed(raw_link)
            and same_site(raw_link, urlsplit(feed.url).hostname or "")
        ):
            link = raw_link.strip()
        else:
            link = clean_url(raw_link)
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
        if url and item.source_key.startswith("custom:") and _custom_site_allowed(url):
            url = url.strip()
        elif url and not clean_url(url):
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
        if feed.key.startswith("custom:"):
            response = await safe_get(
                session, feed.url, urlsplit(feed.url).hostname or ""
            )
            if response is None:
                log.warning("feed %s not available or redirected off-site", feed.key)
                return []
            raw = response[0]
        else:
            async with session.get(feed.url) as response:
                if response.status != 200:
                    log.warning("feed %s status %s", feed.key, response.status)
                    return []
                raw = await response.read()
        items = await asyncio.to_thread(parse_feed, feed, raw)
    except Exception as exc:
        log.warning("feed %s failed: %s", feed.key, exc)
        return []
    log.info("feed %s items %s", feed.key, len(items))
    return items


async def refresh_all(
    database: Database,
    *,
    feed_keys: set[str] | None = None,
    force: bool = False,
) -> int:
    async with _LOCK:
        scope = "all" if feed_keys is None else ",".join(sorted(feed_keys))
        fresh = time.monotonic() - _LAST_OK.get(scope, 0.0) < 30
        if fresh and not force and await database.count_articles():
            return 0
        await database.ensure_catalog(CATALOG_ROWS)
        catalog = await database.list_sources()
        active_feeds = [
            Feed(item.key, item.name, item.url, None)
            for item in catalog
            if feed_keys is None or item.key in feed_keys
        ]
        timeout = aiohttp.ClientTimeout(total=20)
        headers = {"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            batches = await asyncio.gather(*(_fetch(session, feed) for feed in active_feeds))
        flat = [item for batch in batches for item in batch]
        prepared = prepare_items(flat, await database.title_norms())
        saved = await database.upsert_articles(
            prepared,
            catalog_visible=feed_keys is None,
        )
        if feed_keys is None:
            await database.mark_catalog_visible(flat)
        await database.remember_images(flat)
        removed = await database.delete_old(config.ARTICLE_KEEP_DAYS)
        if flat:
            await database.meta_set("fetched_at", utc_now_iso())
            _LAST_OK[scope] = time.monotonic()
        log.info("refresh parsed=%s saved=%s pruned=%s", len(flat), saved, removed)
        return saved


async def refresh_custom_sources(
    database: Database,
    user_id: int | None = None,
    *,
    only_plan: str | None = None,
) -> int:
    """Refresh private RSS sources; their articles are visible only to that owner."""
    users = [await database.require_user(user_id)] if user_id is not None else await database.list_paid_users()
    if only_plan:
        users = [user for user in users if user.plan == only_plan]
    total = 0
    for user in users:
        sources = [item for item in await database.active_sources(user.user_id) if item.custom]
        if not sources:
            continue
        timeout = aiohttp.ClientTimeout(total=20)
        headers = {"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"}
        async with aiohttp.ClientSession(
            timeout=timeout, headers=headers,
            connector=aiohttp.TCPConnector(resolver=PublicResolver(), use_dns_cache=False),
        ) as session:
            batches = await asyncio.gather(
                *(_fetch(session, Feed(item.key, item.name, item.url, None)) for item in sources)
            )
        flat = [item for batch in batches for item in batch]
        prepared = prepare_items(flat, await database.title_norms())
        total += await database.upsert_articles(prepared)
    return total
