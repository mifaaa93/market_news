"""GNews top-headlines: один запрос на язык, источники появляются из ответов."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

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


_SEARCH_STRONG_PATTERNS = (
    r"\bstocks?\b",
    r"\bshares?\b",
    r"\bequities\b",
    r"\bearnings?\b",
    r"\bfinancial results?\b",
    r"\bquarterly results?\b",
    r"\bq[1-4]\b",
    r"\brevenue\b",
    r"\bprofit(?:s)?\b",
    r"\bipo\b",
    r"\bnasdaq\b",
    r"\bnifty\b",
    r"\bsensex\b",
    r"\bbse\b",
    r"\bfii\b",
    r"\bipo(?:s)?\b",
    r"\bmarket rally\b",
    r"\bs&p\s*500\b",
    r"\bwall street\b",
    r"\boil\b",
    r"\bcrude\b",
    r"\bbrent\b",
    r"\bwti\b",
    r"\bopec\+?\b",
    r"\bnatural gas\b",
    r"\bgold\b",
    r"\bcopper\b",
    r"\binflation\b",
    r"\bgdp\b",
    r"\binterest rates?\b",
    r"\bcentral bank\b",
    r"\bfederal reserve\b",
    r"\bthe fed\b",
    r"\becb\b",
    r"\brecession\b",
    r"\bbond yields?\b",
    r"\btreasur(?:y|ies)\b",
    r"\bbitcoin\b",
    r"\bethereum\b",
    r"\bcrypto(?:currency)?\b",
    r"\bblockchain\b",
    r"\bforex\b",
    r"\bcurrency\b",
    r"\bdollar\b",
    r"\byen\b",
    r"\beuro\b",
)

_SEARCH_NOISE_PATTERNS = (
    r"\bweather\b",
    r"\bfoods?\b",
    r"\bstock up\b",
    r"\brecipe\b",
    r"\bfootball\b",
    r"\bsoccer\b",
    r"\bcricket\b",
    r"\bmovie\b",
    r"\bfilm\b",
    r"\bmusic\b",
    r"\bcelebrity\b",
    r"\btravel\b",
    r"\btourism\b",
    r"\bcars?\b",
    r"\bvehicles?\b",
    r"\baccident\b",
    r"\bpolice\b",
    r"\bcrime\b",
    r"\bschool\b",
    r"\bhospital\b",
    r"\bobituary\b",
    r"\bwedding\b",
    r"\bquiz\b",
    r"\bfestival\b",
    r"\breopening\b",
    r"\bprice prediction\b",
    r"\bprice target\b",
    r"\bto buy now\b",
    r"\bstocks? to buy\b",
    r"\bcryptos? to buy\b",
    r"\bno.brainer\b",
    r"\bhoroscope\b",
    r"\bhow to invest\b",
)


def _term_hits(text: str, patterns: tuple[str, ...]) -> int:
    lowered = text.casefold()
    return sum(bool(re.search(pattern, lowered)) for pattern in patterns)


def search_quality_score(item: IncomingArticle) -> int:
    """Score a search result using the title first and description second."""
    title_hits = _term_hits(item.title, _SEARCH_STRONG_PATTERNS)
    body_hits = _term_hits(f"{item.summary}\n{item.body}", _SEARCH_STRONG_PATTERNS)
    noise_hits = _term_hits(item.title, _SEARCH_NOISE_PATTERNS)
    score = title_hits * 3 + body_hits - noise_hits * 4
    if item.category != "markets":
        score += 1
    if config.source_pin_order(item.source_name, item.source_url) is not None:
        score += 1
    return score


def is_quality_search_article(item: IncomingArticle) -> bool:
    """Reject generic news where finance appears only incidentally."""
    title_hits = _term_hits(item.title, _SEARCH_STRONG_PATTERNS)
    if _term_hits(item.title, _SEARCH_NOISE_PATTERNS):
        return False
    score = search_quality_score(item)
    return title_hits >= 1 and score >= 3


def is_non_priority_indian_article(item: IncomingArticle) -> bool:
    """Reject Indian-source news unless the source is in the priority list."""
    country = str(item.source_extra.get("country") or "").strip().casefold()
    return country == "in" and config.source_pin_order(item.source_name, item.source_url) is None


def search_due(last_search_at: str | None, now: datetime | None = None) -> bool:
    moment = now or datetime.now(timezone.utc)
    if not last_search_at:
        return True
    try:
        previous = datetime.strptime(last_search_at, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return True
    # The scheduler fires on minute boundaries, but fetched_at is recorded
    # *after* the API response. Compare minute buckets so a 2-second response
    # does not turn a one-minute schedule into two minutes in practice.
    elapsed = moment.replace(second=0, microsecond=0) - previous.replace(
        second=0, microsecond=0
    )
    return elapsed >= timedelta(minutes=config.search_interval_minutes(moment))


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
    lang: str,
    *,
    page: int = 1,
    since: str | None = None,
    query: str | None = None,
) -> dict[str, str]:
    params = {
        "q": query or config.GNEWS_QUERY,
        "lang": lang,
        "max": str(config.GNEWS_MAX),
        "sortby": "publishedAt",
        "page": str(max(1, page)),
        "in": "title,description",
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
    query: str | None = None,
) -> dict | None:
    if kind == "top":
        params = headlines_params(lang)
        path = "top-headlines"
    else:
        params = search_params(lang, page=page, since=since, query=query)
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
