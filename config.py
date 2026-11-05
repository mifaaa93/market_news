"""Настройки Market News. Секреты только из .env."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def _int(name: str, default: int, minimum: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_USER_ID = _int("ADMIN_USER_ID", 480055341, 1)

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DATA_DIR = os.getenv("DATA_DIR", "data")
DATA_PATH = Path(DATA_DIR) if Path(DATA_DIR).is_absolute() else ROOT / DATA_DIR

DIGEST_HOURS = (8, 9, 12, 18, 21)
TIMEZONES = ("Europe/Moscow", "Asia/Dubai", "Europe/London", "UTC")

DEFAULT_TZ = os.getenv("DEFAULT_TZ", "Europe/Moscow")
if DEFAULT_TZ not in TIMEZONES:
    DEFAULT_TZ = "Europe/Moscow"

DEFAULT_HOUR = _int("DEFAULT_HOUR", 9, 0)
if DEFAULT_HOUR not in DIGEST_HOURS:
    DEFAULT_HOUR = 9

LINKS_AFTER_STEPS = _int("LINKS_AFTER_STEPS", 5, 5)
LINKS_AFTER_OPENS = _int("LINKS_AFTER_OPENS", 3, 3)

def _hours(name: str, default: str) -> tuple[int, ...]:
    hours: list[int] = []
    for part in os.getenv(name, default).split(","):
        try:
            hour = int(part.strip())
        except ValueError:
            continue
        if 0 <= hour <= 23 and hour not in hours:
            hours.append(hour)
    return tuple(hours) or (0, 6, 12, 18)


GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "").strip()
GNEWS_BASE_URL = os.getenv("GNEWS_BASE_URL", "https://gnews.io/api/v4").strip().rstrip("/")
GNEWS_DAILY_LIMIT = _int("GNEWS_DAILY_LIMIT", 1000, 1)
GNEWS_MAX = _int("GNEWS_MAX", 25, 1)
GNEWS_SEARCH_MINUTES = _int("GNEWS_SEARCH_MINUTES", 2, 1)
GNEWS_SEARCH_PAGES = _int("GNEWS_SEARCH_PAGES", 1, 1)
GNEWS_TOP_HOURS = _hours("GNEWS_TOP_HOURS", "0,6,12,18")
GNEWS_LANGS = ("en",)
INTERFACE_LANGS = ("ru", "en", "ar")
GNEWS_CONTENT_LANG = "en"
GNEWS_CATEGORY = os.getenv("GNEWS_CATEGORY", "business").strip() or "business"
GNEWS_QUERY = os.getenv(
    "GNEWS_QUERY_EN",
    "stock OR stocks OR oil OR crypto OR economy OR market OR nasdaq",
).strip()

PINNED_SOURCE_KEYS = (
    "reuters.com",
    "bbc.com",
    "bbc.co.uk",
    "cnbc.com",
    "theguardian.com",
    "bloomberg.com",
    "yahoo.com",
    "ft.com",
    "wsj.com",
    "apnews.com",
    "businessinsider.com",
    "forbes.com",
    "economist.com",
    "marketwatch.com",
    "seekingalpha.com",
    "aljazeera.com",
    "nytimes.com",
    "nasdaq.com",
    "oilprice.com",
    "coindesk.com",
    "cnn.com",
)


def source_pin_order(name: str, url: str) -> int | None:
    blob = f"{name} {url}".lower()
    for index, key in enumerate(PINNED_SOURCE_KEYS, start=1):
        if key in blob:
            return index
    return None

TRANSLATION_WORKER_SECONDS = _int("TRANSLATION_WORKER_SECONDS", 10, 1)
TRANSLATION_BATCH_LIMIT = _int("TRANSLATION_BATCH_LIMIT", 16, 1)
_translation_langs = os.getenv("TRANSLATION_LANGS", "ru,ar")
TRANSLATION_LANGS = tuple(
    part.strip()
    for part in _translation_langs.split(",")
    if part.strip() in INTERFACE_LANGS and part.strip() != "en"
)
IMAGE_CACHE_CHAT_ID = _int("IMAGE_CACHE_CHAT_ID", ADMIN_USER_ID, 1)
IMAGE_BATCH_LIMIT = _int("IMAGE_BATCH_LIMIT", 4, 1)
IMAGE_WORKER_SECONDS = _int("IMAGE_WORKER_SECONDS", 2, 1)

CVC_API_KEY = os.getenv("CVC_API_KEY", "").strip()
CVC_BASE_URL = os.getenv("CVC_BASE_URL", "https://ru.cheapvibecode.ru/v1").strip().rstrip("/")


def _model_chain(*names: str) -> tuple[str, ...]:
    chain: list[str] = []
    for name in names:
        value = name.strip()
        if value and value not in chain:
            chain.append(value)
    return tuple(chain)


CVC_MODELS = _model_chain(
    os.getenv("CVC_MODEL", "gpt-6-luna"),
    os.getenv("CVC_FALLBACK_MODEL", "claude-haiku-5-5"),
)

FEED_PAGE_SIZE = _int("FEED_PAGE_SIZE", 16, 4)

PUSH_FRESH_MINUTES = _int("PUSH_FRESH_MINUTES", 180, 1)
PUSH_PER_USER_PER_CYCLE = _int("PUSH_PER_USER_PER_CYCLE", 3, 1)
PLUS_STARS = _int("PLUS_STARS", 200, 1)
PRO_STARS = _int("PRO_STARS", 500, 1)
PLUS_DAYS = _int("PLUS_DAYS", 30, 1)
BASE_SOURCE_LIMIT = _int("BASE_SOURCE_LIMIT", 5, 1)
PLUS_SOURCE_LIMIT = _int("PLUS_SOURCE_LIMIT", 100, 1)
PRO_SOURCE_LIMIT = _int("PRO_SOURCE_LIMIT", 500, 1)
BOT_USERNAME = os.getenv("BOT_USERNAME", "market_news_bot").strip().lstrip("@")
LANDING_BOT_URL = os.getenv("LANDING_BOT_URL", f"https://t.me/{BOT_USERNAME}")
ARTICLE_KEEP_DAYS = _int("ARTICLE_KEEP_DAYS", 14, 3)


def source_limit_for(plan: str) -> int:
    if plan == "pro":
        return PRO_SOURCE_LIMIT
    if plan == "plus":
        return PLUS_SOURCE_LIMIT
    return BASE_SOURCE_LIMIT
