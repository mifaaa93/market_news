"""Текст экранов, категории и правило показа внешней ссылки."""

from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import config
from models import CATEGORIES, Article, User
from texts import cat_name, fill, lang_label, t, tz_label

_TAG = re.compile(r"<[^>]+>")
_SCRIPT = re.compile(r"(?is)<(script|style).*?>.*?</\1>")
_URL = re.compile(r"https?://\S+|www\.\S+")
_SPACE = re.compile(r"[ \t]+")
_BREAKS = re.compile(r"\n{3,}")
_TAIL = re.compile(r"\s*(read more|continue reading)\.?$", re.IGNORECASE)
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "crypto",
        (
            r"\bbitcoin\b",
            r"\bcrypto\b",
            r"\bcryptocurrency\b",
            r"\bethereum\b",
            r"\bbtc\b",
            r"\beth\b",
            r"\bblockchain\b",
            r"\bdefi\b",
            r"\bbinance\b",
            r"\bcoinbase\b",
        ),
    ),
    (
        "oil",
        (
            r"\boil\b",
            r"\bcrude\b",
            r"\bbrent\b",
            r"\bwti\b",
            r"\bopec\b",
            r"\bnatural gas\b",
            r"\blng\b",
            r"\bpetroleum\b",
        ),
    ),
    (
        "macro",
        (
            r"\binflation\b",
            r"\bgdp\b",
            r"\bunemployment\b",
            r"\bcentral bank\b",
            r"\bfederal reserve\b",
            r"\bthe fed\b",
            r"\bfed\b",
            r"\becb\b",
            r"\binterest rate\b",
            r"\brate cut\b",
            r"\brate hike\b",
            r"\btariff\b",
            r"\brecession\b",
            r"\bbond yield\b",
            r"\btreasury\b",
            r"\bjobs report\b",
            r"\bpayrolls?\b",
            r"\bretail sales\b",
            r"\bconsumer prices\b",
            r"\bcpi\b",
        ),
    ),
    (
        "stocks",
        (
            r"\bstocks?\b",
            r"\bshares?\b",
            r"\bequity\b",
            r"\bequities\b",
            r"\bnasdaq\b",
            r"\bs&p\b",
            r"\bdow\b",
            r"\bearnings\b",
            r"\bipo\b",
            r"\bwall street\b",
        ),
    ),
)

# Кнопка источника ведёт только на сайты изданий из ленты, не на случайный домен из RSS.
_ALLOWED_HOSTS = (
    "abcnews.com",
    "abcnews.go.com",
    "bbc.co.uk",
    "bbc.com",
    "cnbc.com",
    "marketwatch.com",
    "oilprice.com",
    "coindesk.com",
    "eia.gov",
    "federalreserve.gov",
)

_BLOCKED_HOSTS = {
    "t.me",
    "telegram.me",
    "telegram.dog",
    "bit.ly",
    "tinyurl.com",
    "goo.gl",
    "t.co",
    "ow.ly",
    "is.gd",
    "cutt.ly",
    "rb.gy",
    "buff.ly",
    "rebrand.ly",
    "tiny.cc",
    "lnkd.in",
    "feedburner.com",
    "feeds.feedburner.com",
    "instagram.com",
    "facebook.com",
    "fb.com",
    "fb.me",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "youtube.com",
    "youtu.be",
    "vk.com",
    "ok.ru",
    "wa.me",
    "chat.whatsapp.com",
    "cnb.cx",
    "reut.rs",
    "bloom.bg",
    "on.mktw.net",
    "on.wsj.com",
    "trib.al",
}

_DROP_QUERY = {
    "at_medium",
    "at_campaign",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
}


def clean_text(value: str) -> str:
    raw = value or ""
    raw = _SCRIPT.sub(" ", raw)
    raw = re.sub(r"(?i)<br\s*/?>", "\n", raw)
    raw = re.sub(r"(?i)</p>", "\n", raw)
    raw = _TAG.sub(" ", raw)
    raw = html.unescape(raw)
    raw = _URL.sub(" ", raw)
    raw = _CONTROL.sub(" ", raw)
    raw = _SPACE.sub(" ", raw)
    raw = _BREAKS.sub("\n\n", raw)
    lines = [line.strip() for line in raw.splitlines()]
    raw = "\n".join(line for line in lines if line).strip()
    return _TAIL.sub("", raw).strip()


def one_line(value: str) -> str:
    return " ".join((value or "").split())


def title_norm(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())[:180]


def clip(value: str, limit: int) -> str:
    text = one_line(value)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    word = cut.rsplit(" ", 1)[0]
    if len(word) < int(limit * 0.6):
        word = cut
    return word.rstrip(".,;:—- ") + "…"


def clip_block(value: str, limit: int) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    newline = cut.rfind("\n")
    space = cut.rfind(" ")
    pivot = newline if newline > int(limit * 0.6) else space
    if pivot > int(limit * 0.6):
        cut = cut[:pivot]
    return cut.rstrip() + "…"


def fit(text: str, limit: int = 3800) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if cut.count("<") != cut.count(">"):
        start = cut.rfind("<")
        if start >= 0:
            cut = cut[:start]
    newline = cut.rfind("\n")
    if newline > int(limit * 0.7):
        cut = cut[:newline]
    return cut.rstrip() + "\n…"


def classify(text: str) -> str:
    low = text.lower()
    scores = {
        category: sum(1 for pattern in patterns if re.search(pattern, low))
        for category, patterns in _RULES
    }
    best = max(scores, key=lambda category: scores[category])
    if scores[best] == 0:
        return "markets"
    return best


def resolve_category(text: str, hint: str | None) -> str:
    found = classify(text)
    if found != "markets":
        return found
    if hint in CATEGORIES:
        return hint
    return "markets"


def _host(hostname: str) -> str:
    host = (hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        return host[4:]
    return host


def is_public_article_url(url: str) -> bool:
    if not url:
        return False
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return False
    if parts.scheme not in {"http", "https"}:
        return False
    if parts.username or parts.password:
        return False
    if parts.port not in (None, 80, 443):
        return False
    host = _host(parts.hostname or "")
    if not host or "." not in host:
        return False
    if host in _BLOCKED_HOSTS or host.endswith(".t.me"):
        return False
    return any(host == suffix or host.endswith("." + suffix) for suffix in _ALLOWED_HOSTS)


def clean_url(url: str) -> str:
    raw = (url or "").strip()
    if not is_public_article_url(raw):
        return ""
    parts = urlsplit(raw)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in _DROP_QUERY
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


_IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def clean_image_url(url: str, *, trusted: bool = False) -> str:
    """Адрес картинки для встраивания. Ссылка на страницу новости сюда не проходит."""
    raw = html.unescape((url or "").strip())
    if raw.startswith("//"):
        raw = "https:" + raw
    if not raw.lower().startswith("https://"):
        return ""
    try:
        parts = urlsplit(raw)
    except ValueError:
        return ""
    host = _host(parts.hostname or "")
    if not host or "." not in host or host in _BLOCKED_HOSTS or host.endswith(".t.me"):
        return ""
    path = parts.path.lower()
    looks_like_file = any(path.endswith(ext) for ext in _IMAGE_EXT)
    cdn = any(token in host for token in ("ichef.", "image.", "images.", "img.", "cdn.", "cdn-"))
    if not (looks_like_file or trusted or cdn):
        return ""
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in _DROP_QUERY
    ]
    return urlunsplit(("https", parts.netloc, parts.path, urlencode(query), ""))


def links_allowed(interactions: int, distinct_opens: int, available: int) -> bool:
    """Внешняя ссылка только после нескольких внутренних шагов и открытых новостей."""
    if available <= 0 or interactions < config.LINKS_AFTER_STEPS:
        return False
    needed = min(config.LINKS_AFTER_OPENS, available)
    return distinct_opens >= needed


def safe_zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("UTC")


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_local(value: str | None, tz_name: str) -> str:
    moment = parse_utc(value)
    if moment is None:
        return ""
    return moment.astimezone(safe_zone(tz_name)).strftime("%d.%m.%Y %H:%M")


def digest_due(user: User, now_utc: datetime) -> bool:
    if not user.notifications or user.blocked:
        return False
    local = now_utc.astimezone(safe_zone(user.timezone))
    if user.last_digest_on == local.date().isoformat():
        return False
    return user.digest_hour <= local.hour <= user.digest_hour + 1


def source_hash(article: Article) -> str:
    payload = f"{article.title}\n{article.summary}\n{article.body}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def plain_summary(article: Article) -> str:
    """Текст новости из ленты. Пустая строка, если издание прислало только заголовок."""
    text = one_line(article.summary)
    body = one_line(article.body)
    if len(text) < 40 and len(body) > len(text):
        text = body
    if len(text) >= 20:
        return text
    return ""


def with_summary(articles: list[Article]) -> list[Article]:
    rich = [article for article in articles if plain_summary(article)]
    return rich or list(articles)


def summary_text(article: Article, lang: str) -> str:
    return plain_summary(article) or t(lang, "no_summary")


def button_label(index: int, title: str) -> str:
    return f"{index}. {clip(title, 42)}"


def pick_digest(articles: list[Article], limit: int = 7) -> list[Article]:
    if limit <= 0:
        return []
    by_category: dict[str, list[Article]] = {}
    for article in articles:
        by_category.setdefault(article.category, []).append(article)
    order = sorted(
        by_category,
        key=lambda category: by_category[category][0].published_at,
        reverse=True,
    )
    picked: list[Article] = []
    seen: set[int] = set()
    for category in order:
        item = by_category[category][0]
        picked.append(item)
        seen.add(item.id)
        if len(picked) >= limit:
            return picked
    for article in articles:
        if article.id in seen:
            continue
        picked.append(article)
        seen.add(article.id)
        if len(picked) >= limit:
            break
    return picked


def within_days(articles: list[Article], days: int, now: datetime | None = None) -> list[Article]:
    moment = now or datetime.now(timezone.utc)
    cutoff = (moment - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return [article for article in articles if article.published_at >= cutoff]


def _names(articles: list[Article]) -> str:
    names: list[str] = []
    for article in articles:
        if article.source_name not in names:
            names.append(article.source_name)
    return ", ".join(names)


def _e(value: str) -> str:
    return html.escape(value or "", quote=True)


def _figure(article: Article) -> str:
    if not article.image_url:
        return ""
    return (
        f'<figure><img src="{_e(article.image_url)}"/>'
        f"<figcaption><cite>{_e(article.source_name)}</cite></figcaption></figure>"
    )


def _paragraphs(text: str) -> str:
    chunks = [chunk.strip() for chunk in re.split(r"\n+", text or "") if chunk.strip()]
    return "".join(f"<p>{_e(chunk)}</p>" for chunk in chunks)


def _story_block(article: Article, lang: str, limit: int, *, index: int | None) -> str:
    title = article.title if index is None else f"{index}. {article.title}"
    parts = [f"<h3>{_e(title)}</h3>", _figure(article)]
    snippet = plain_summary(article)
    if snippet:
        parts.append(f"<p>{_e(clip(snippet, limit))}</p>")
    parts.append(
        f"<footer>{_e(cat_name(lang, article.category))} · {_e(article.source_name)}</footer>"
    )
    return "".join(parts)


def _disclaimer(lang: str) -> str:
    return f"<footer>{_e(t(lang, 'disclaimer'))}</footer>"


def render_home(items: list[Article], lang: str, tz_name: str, updated_iso: str | None) -> str:
    parts = ["<h1>Market News</h1>", f"<p>{_e(t(lang, 'tagline'))}</p>"]
    if not items:
        parts.append(f"<p>{_e(t(lang, 'empty'))}</p>")
        parts.append(_disclaimer(lang))
        return fit("".join(parts))
    shown = items[:3]
    parts.append(f"<h2>{_e(t(lang, 'today_head'))}</h2>")
    for index, article in enumerate(shown, start=1):
        parts.append(_story_block(article, lang, 280, index=index))
    stamp = format_local(updated_iso, tz_name)
    if stamp:
        parts.append(f"<footer>{_e(fill(t(lang, 'updated'), stamp=stamp, tz=tz_label(lang, tz_name)))}</footer>")
    parts.append(_disclaimer(lang))
    return fit("".join(parts))


def render_digest(
    items: list[Article],
    lang: str,
    tz_name: str,
    updated_iso: str | None,
    *,
    mailed: bool = False,
) -> str:
    shown = items[:7]
    parts = [
        f"<h1>{_e(t(lang, 'digest_title'))}</h1>",
        f"<p>{_e(t(lang, 'digest_intro'))}</p>",
    ]
    if not shown:
        parts.append(f"<p>{_e(t(lang, 'empty'))}</p>")
    for index, article in enumerate(shown, start=1):
        parts.append(_story_block(article, lang, 180, index=index))
    if shown:
        parts.append(f"<footer>{_e(fill(t(lang, 'sources_line'), names=_names(shown)))}</footer>")
    stamp = format_local(updated_iso, tz_name)
    if stamp:
        parts.append(f"<footer>{_e(fill(t(lang, 'updated'), stamp=stamp, tz=tz_label(lang, tz_name)))}</footer>")
    if mailed:
        parts.append(f"<footer>{_e(t(lang, 'mail_footer'))}</footer>")
    parts.append(_disclaimer(lang))
    return fit("".join(parts))


def render_analytics(items: list[Article], lang: str, *, premium: bool) -> str:
    parts = [f"<h1>{_e(t(lang, 'analytics_title'))}</h1>"]
    if not items:
        parts.append(f"<p>{_e(t(lang, 'empty'))}</p>")
        parts.append(_disclaimer(lang))
        return fit("".join(parts))
    window = items[:30]
    digest = pick_digest(window, 4)
    counts: dict[str, int] = {}
    for article in window:
        counts[article.category] = counts.get(article.category, 0) + 1
    parts.append(f"<h2>{_e(t(lang, 'plots'))}</h2>")
    for article in digest:
        parts.append(_story_block(article, lang, 160, index=None))
    parts.append(f"<h2>{_e(t(lang, 'spread'))}</h2><ul>")
    ordered = sorted(counts, key=lambda category: counts[category], reverse=True)
    for category in ordered:
        parts.append(f"<li>{_e(cat_name(lang, category))}: {counts[category]}</li>")
    parts.append("</ul>")
    top = ordered[0]
    lead = digest[0]
    parts.append(f"<h2>{_e(t(lang, 'brief'))}</h2>")
    parts.append(
        "<p>"
        + _e(
            fill(
                t(lang, "analytics_blurb"),
                cat=cat_name(lang, top),
                n=counts[top],
                title=lead.title,
                source=lead.source_name,
            )
        )
        + "</p>"
    )
    if premium:
        parts.append(f"<h2>{_e(t(lang, 'by_topic'))}</h2><ul>")
        seen: set[str] = set()
        for article in window:
            if article.category in seen:
                continue
            seen.add(article.category)
            parts.append(
                f"<li><b>{_e(cat_name(lang, article.category))}</b> — {_e(article.title)}</li>"
            )
        parts.append("</ul>")
    parts.append(_disclaimer(lang))
    return fit("".join(parts))


def render_latest(items: list[Article], lang: str) -> str:
    shown = items[:8]
    parts = [
        f"<h1>{_e(t(lang, 'latest_title'))}</h1>",
        f"<p>{_e(t(lang, 'latest_intro'))}</p>",
    ]
    if not shown:
        parts.append(f"<p>{_e(t(lang, 'empty'))}</p>")
    for index, article in enumerate(shown, start=1):
        parts.append(
            f"<h3>{index}. {_e(article.title)}</h3>{_figure(article)}<footer>{_e(article.source_name)}</footer>"
        )
    parts.append(_disclaimer(lang))
    return fit("".join(parts))


def render_categories(lang: str) -> str:
    return fit(
        f"<h1>{_e(t(lang, 'cats_title'))}</h1><p>{_e(t(lang, 'cats_intro'))}</p>{_disclaimer(lang)}"
    )


def render_category(category: str, items: list[Article], lang: str) -> str:
    title = cat_name(lang, category)
    shown = items[:6]
    parts = [f"<h1>{_e(title)}</h1>"]
    if not shown:
        parts.append(f"<p>{_e(fill(t(lang, 'empty_cat'), cat=title))}</p>")
    for index, article in enumerate(shown, start=1):
        parts.append(_story_block(article, lang, 140, index=index))
    parts.append(_disclaimer(lang))
    return fit("".join(parts))


def render_article(article: Article, lang: str, tz_name: str) -> str:
    parts = [
        f"<footer>{_e(cat_name(lang, article.category))}</footer>",
        f"<h1>{_e(article.title)}</h1>",
        _figure(article),
        f"<p>{_e(clip(summary_text(article, lang), 700))}</p>",
        f"<footer>{_e(t(lang, 'source'))}: {_e(article.source_name)}</footer>",
    ]
    when = format_local(article.published_at, tz_name)
    if when:
        parts.append(f"<footer>{_e(when)} · {_e(tz_label(lang, tz_name))}</footer>")
    parts.append(_disclaimer(lang))
    return fit("".join(parts))


def render_full(article: Article, lang: str, tz_name: str, *, expanded: bool) -> str:
    body = article.body.strip()
    text = body if len(body) >= len(article.summary.strip()) else summary_text(article, lang)
    parts = [
        f"<footer>{_e(cat_name(lang, article.category))}</footer>",
        f"<h1>{_e(article.title)}</h1>",
        _figure(article),
    ]
    if not expanded:
        parts.append(f"<p>{_e(t(lang, 'full_missing'))}</p>")
    parts.append(_paragraphs(clip_block(text, 3400 if expanded else 900)))
    when = format_local(article.published_at, tz_name)
    meta = article.source_name if not when else f"{article.source_name} · {when}"
    parts.append(f"<footer>{_e(t(lang, 'source'))}: {_e(meta)}</footer>")
    return fit("".join(parts))


def render_settings(user: User) -> str:
    lang = user.lang
    lines = [f"<b>{html.escape(t(lang, 'settings_title'))}</b>", ""]
    lines.append(html.escape(fill(t(lang, "settings_lang"), lang=lang_label(user.lang))))
    if user.notifications:
        lines.append(
            html.escape(
                fill(
                    t(lang, "settings_push_on"),
                    hour=f"{user.digest_hour:02d}",
                    tz=tz_label(lang, user.timezone),
                )
            )
        )
    else:
        lines.append(html.escape(t(lang, "settings_push_off")))
    if user.premium_active():
        lines.append(
            html.escape(
                fill(
                    t(lang, "plus_active"),
                    until=format_local(user.premium_until, user.timezone),
                ).replace("Plus", user.plan.title())
            )
        )
    else:
        lines.append(html.escape(t(lang, "plus_off")))
    lines.append("")
    lines.append(f"<i>{html.escape(t(lang, 'disclaimer'))}</i>")
    return fit("\n".join(lines))


def render_help(lang: str) -> str:
    return fit(t(lang, "help"))


def render_how_it_works(lang: str) -> str:
    return fit(t(lang, "how_it_works"))


def render_sources(lang: str, blocks: list[tuple[str, str]], *, allow_link: bool) -> str:
    lines = [f"<b>{html.escape(t(lang, 'sources_title'))}</b>", ""]
    lines.append(html.escape(t(lang, "sources_intro")))
    lines.append("")
    for name, about in blocks:
        lines.append(f"<b>{html.escape(name)}</b>")
        lines.append(html.escape(about))
        lines.append("")
    lines.append(f"<i>{html.escape(t(lang, 'disclaimer'))}</i>")
    return fit("\n".join(lines).strip())


def render_week(items: list[Article], lang: str) -> str:
    shown = items[:12]
    parts = [
        f"<h1>{_e(t(lang, 'week_title'))}</h1>",
        f"<p>{_e(t(lang, 'week_intro'))}</p>",
    ]
    if not shown:
        parts.append(f"<p>{_e(t(lang, 'empty'))}</p>")
    for index, article in enumerate(shown, start=1):
        parts.append(_story_block(article, lang, 120, index=index))
    parts.append(_disclaimer(lang))
    return fit("".join(parts))


def render_plus(user: User) -> str:
    lang = user.lang
    lines = [f"<b>{html.escape(t(lang, 'plus_title'))}</b>", ""]
    if user.premium_active():
        lines.append(
            html.escape(fill(t(lang, "plus_active"), until=format_local(user.premium_until, user.timezone)))
        )
        lines.append("")
    lines.append(
        html.escape(
            fill(
                t(lang, "plus_pitch"),
                plus_stars=str(config.PLUS_STARS),
                plus_limit=str(config.PLUS_SOURCE_LIMIT),
                pro_stars=str(config.PRO_STARS),
                pro_limit=str(config.PRO_SOURCE_LIMIT),
            )
        )
    )
    lines.append("")
    lines.append(f"<i>{html.escape(t(lang, 'disclaimer'))}</i>")
    return fit("\n".join(lines))


def render_plans(user: User, catalog_count: int = 0) -> str:
    lines = [
        f"<b>{html.escape(t(user.lang, 'plans_title'))}</b>",
        "",
        html.escape(fill(t(user.lang, "plans_text"), catalog=catalog_count)),
        "",
        html.escape(
            fill(
                t(user.lang, "subscription_status"),
                status=t(user.lang, f"btn_plan_{user.plan}" if user.plan in {"base", "plus", "pro"} else "btn_plan_base"),
            )
        ),
        f"<i>{html.escape(t(user.lang, 'disclaimer'))}</i>",
    ]
    return fit("\n".join(lines))


def render_feed(user: User, sources: list[tuple[str, bool, str | None, str]]) -> str:
    enabled = sum(1 for _, state, _, _ in sources if state)
    lines = [
        f"<b>{html.escape(t(user.lang, 'feed_title'))}</b>",
        "",
        html.escape(t(user.lang, "feed_intro")),
        "",
        html.escape(f"{enabled}"),
        f"<i>{html.escape(t(user.lang, 'disclaimer'))}</i>",
    ]
    return fit("\n".join(lines))
