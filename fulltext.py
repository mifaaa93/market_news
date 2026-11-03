"""Полный текст статьи со страницы издания. В RSS обычно только короткий абзац."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import aiohttp
import trafilatura

from content import clean_text, is_public_article_url
from db import Database
from models import Article
from source_security import PublicResolver, public_site, safe_get

log = logging.getLogger(__name__)
_RATE_LIMIT_UNTIL: dict[str, float] = {}
_COINDESK_LOCK = asyncio.Lock()

_PARAGRAPH = re.compile(r"<p\b[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def is_full_text(article: Article) -> bool:
    summary = len(article.summary.strip())
    body = len(article.body.strip())
    return body >= 900 and body >= summary + 400


def extract_text(raw: bytes | str) -> str:
    extracted = trafilatura.extract(
        raw,
        include_comments=False,
        include_tables=False,
        favor_precision=True,
    )
    text = (extracted or "").strip()
    if len(text) < 400:
        text = _paragraphs(raw)
    text = text.strip()
    if len(text) < 400:
        return ""
    return text[:12000]


def _paragraphs(raw: bytes | str) -> str:
    html_text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
    chunks: list[str] = []
    for match in _PARAGRAPH.finditer(html_text):
        piece = clean_text(match.group(1))
        if len(piece) >= 40:
            chunks.append(piece)
    return "\n\n".join(chunks)


class RateLimited(Exception):
    """The publisher asked us to retry on a later scheduled refresh."""


def _retry_delay(value: str | None) -> int:
    try:
        delay = int(value or "")
    except ValueError:
        try:
            target = parsedate_to_datetime(value or "").astimezone(timezone.utc)
            delay = int((target - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            delay = 60
    return max(60, min(delay, 1200))


async def fetch_article_text(url: str, *, allow_custom: bool = False) -> str:
    if not is_public_article_url(url) and not (allow_custom and public_site(url)):
        return ""
    host = urlsplit(url).hostname or ""
    if time.monotonic() < _RATE_LIMIT_UNTIL.get(host, 0):
        raise RateLimited(host)
    timeout = aiohttp.ClientTimeout(total=15)
    headers = {"User-Agent": _UA, "Accept": "text/html,application/xhtml+xml"}
    try:
        connector = (
            aiohttp.TCPConnector(resolver=PublicResolver(), use_dns_cache=False)
            if allow_custom else None
        )
        async with aiohttp.ClientSession(timeout=timeout, headers=headers, connector=connector) as session:
            if allow_custom:
                page = await safe_get(
                    session, url, host, max_bytes=2_000_000,
                    accept="text/html,application/xhtml+xml",
                )
                return extract_text(page[0]) if page else ""
            async with session.get(url, allow_redirects=True) as response:
                if response.status == 429:
                    delay = _retry_delay(response.headers.get("Retry-After"))
                    _RATE_LIMIT_UNTIL[host] = time.monotonic() + delay
                    log.warning("article page %s rate limited, retry in %s seconds", host, delay)
                    raise RateLimited(host)
                if response.status != 200:
                    log.info("article page %s status %s", url, response.status)
                    return ""
                raw = await response.read()
    except RateLimited:
        raise
    except Exception as exc:
        log.info("article page failed: %s", exc)
        return ""
    return extract_text(raw)


async def fill_full_texts(database: Database, *, concurrency: int = 2, user_id: int | None = None) -> int:
    pending = await database.articles_needing_full_text()
    if not pending:
        return 0
    semaphore = asyncio.Semaphore(concurrency)

    async def load(article: Article) -> tuple[Article, str | None]:
        if is_full_text(article):
            return article, article.body
        async with semaphore:
            try:
                if article.source_key == "coindesk":
                    async with _COINDESK_LOCK:
                        # Avoid bursts against CoinDesk; don't bypass 429 restrictions.
                        await asyncio.sleep(1)
                        text = await fetch_article_text(article.url)
                else:
                    text = await fetch_article_text(
                        article.url,
                        allow_custom=(
                            (user_id is not None or article.source_key.startswith("custom:"))
                            and not is_public_article_url(article.url)
                        ),
                    )
                return article, text
            except RateLimited:
                return article, None

    loaded = await asyncio.gather(*(load(article) for article in pending))
    saved = 0
    for article, text in loaded:
        if text is None:
            continue  # A 429 must remain retryable, not become permanently checked.
        if is_full_text(article):
            await database.save_full_text(article.id, None)
            continue
        if text and len(text) >= len(article.body) + 400:
            await database.save_full_text(article.id, text)
            saved += 1
        else:
            await database.save_full_text(article.id, None)
    deferred = sum(text is None for _, text in loaded)
    log.info("full texts saved %s of %s, rate limited=%s", saved, len(pending), deferred)
    return saved


async def ensure_full_text(database: Database, article: Article) -> Article:
    if article.full_checked or is_full_text(article) or not article.url:
        return article
    try:
        text = await fetch_article_text(
            article.url,
            allow_custom=article.source_key.startswith("custom:") and not is_public_article_url(article.url),
        )
    except RateLimited:
        return article
    if text and len(text) >= len(article.body) + 400:
        saved = await database.save_full_text(article.id, text)
    else:
        saved = await database.save_full_text(article.id, None)
    return saved or article
