"""Полный текст статьи со страницы издания. В RSS обычно только короткий абзац."""

from __future__ import annotations

import asyncio
import logging
import re

import aiohttp
import trafilatura

from content import clean_text, is_public_article_url
from db import Database
from models import Article

log = logging.getLogger(__name__)

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


async def fetch_article_text(url: str) -> str:
    if not is_public_article_url(url):
        return ""
    timeout = aiohttp.ClientTimeout(total=15)
    headers = {"User-Agent": _UA, "Accept": "text/html,application/xhtml+xml"}
    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, allow_redirects=True) as response:
                if response.status != 200:
                    log.info("article page %s status %s", url, response.status)
                    return ""
                raw = await response.read()
    except Exception as exc:
        log.info("article page failed: %s", exc)
        return ""
    return extract_text(raw)


async def fill_full_texts(database: Database, *, concurrency: int = 4) -> int:
    pending = await database.articles_needing_full_text()
    if not pending:
        return 0
    semaphore = asyncio.Semaphore(concurrency)

    async def load(article: Article) -> tuple[Article, str]:
        async with semaphore:
            return article, await fetch_article_text(article.url)

    loaded = await asyncio.gather(*(load(article) for article in pending))
    saved = 0
    for article, text in loaded:
        if text and len(text) >= len(article.body) + 400:
            await database.save_full_text(article.id, text)
            saved += 1
        else:
            await database.save_full_text(article.id, None)
    log.info("full texts saved %s of %s", saved, len(pending))
    return saved


async def ensure_full_text(database: Database, article: Article) -> Article:
    if article.full_checked or is_full_text(article) or not article.url:
        return article
    text = await fetch_article_text(article.url)
    if text and len(text) >= len(article.body) + 400:
        saved = await database.save_full_text(article.id, text)
    else:
        saved = await database.save_full_text(article.id, None)
    return saved or article
