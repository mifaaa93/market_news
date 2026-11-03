"""Настройки Market News. Токен берётся из .env, в код его не кладём."""

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

_db = os.getenv("DB_PATH", "data/market_news.sqlite3")
DB_PATH = _db if Path(_db).is_absolute() else str(ROOT / _db)

DIGEST_HOURS = (8, 9, 12, 18, 21)
TIMEZONES = ("Europe/Moscow", "Asia/Dubai", "Europe/London", "UTC")

DEFAULT_TZ = os.getenv("DEFAULT_TZ", "Europe/Moscow")
if DEFAULT_TZ not in TIMEZONES:
    DEFAULT_TZ = "Europe/Moscow"

DEFAULT_HOUR = _int("DEFAULT_HOUR", 9, 0)
if DEFAULT_HOUR not in DIGEST_HOURS:
    DEFAULT_HOUR = 9

# Ниже этих порогов ссылку на источник не показываем. ТЗ: минимум 5 касаний.
LINKS_AFTER_STEPS = _int("LINKS_AFTER_STEPS", 5, 5)
LINKS_AFTER_OPENS = _int("LINKS_AFTER_OPENS", 3, 3)

RSS_REFRESH_MINUTES = _int("RSS_REFRESH_MINUTES", 20, 5)
PRO_REFRESH_MINUTES = _int("PRO_REFRESH_MINUTES", 5, 1)
TRANSLATION_WORKER_SECONDS = _int("TRANSLATION_WORKER_SECONDS", 10, 1)
PUSH_FRESH_MINUTES = _int("PUSH_FRESH_MINUTES", 30, 1)
PUSH_PER_USER_PER_CYCLE = _int("PUSH_PER_USER_PER_CYCLE", 3, 1)
TRANSLATION_BATCH_LIMIT = _int("TRANSLATION_BATCH_LIMIT", 8, 1)
PLUS_STARS = _int("PLUS_STARS", 200, 1)
PRO_STARS = _int("PRO_STARS", 500, 1)
PLUS_DAYS = _int("PLUS_DAYS", 30, 1)
BASE_SOURCE_LIMIT = _int("BASE_SOURCE_LIMIT", 5, 1)
PLUS_SOURCE_LIMIT = _int("PLUS_SOURCE_LIMIT", 100, 1)
PRO_SOURCE_LIMIT = _int("PRO_SOURCE_LIMIT", 500, 1)
PLUS_CUSTOM_LIMIT = _int("PLUS_CUSTOM_LIMIT", 5, 0)
PRO_CUSTOM_LIMIT = _int("PRO_CUSTOM_LIMIT", 20, 0)
BOT_USERNAME = os.getenv("BOT_USERNAME", "market_news_bot").strip().lstrip("@")
LANDING_BOT_URL = os.getenv("LANDING_BOT_URL", f"https://t.me/{BOT_USERNAME}")
ARTICLE_KEEP_DAYS = _int("ARTICLE_KEEP_DAYS", 14, 3)

# Перевод новостей. Сейчас русский. Арабский добавляется сюда же: ru,ar
_translation_langs = os.getenv("TRANSLATION_LANGS", "ru")
TRANSLATION_LANGS = tuple(
    part.strip()
    for part in _translation_langs.split(",")
    if part.strip() and part.strip() != "en"
)

CVC_API_KEY = os.getenv("CVC_API_KEY", "").strip()
CVC_BASE_URL = os.getenv("CVC_BASE_URL", "https://ru.cheapvibecode.ru/v1").strip().rstrip("/")


def _model_chain(*names: str) -> tuple[str, ...]:
    chain: list[str] = []
    for name in names:
        value = name.strip()
        if value and value not in chain:
            chain.append(value)
    return tuple(chain)


# Сначала дешёвая модель GPT для пачки новостей, при сбое — Claude другого провайдера.
CVC_MODELS = _model_chain(
    os.getenv("CVC_MODEL", "gpt-6-luna"),
    os.getenv("CVC_FALLBACK_MODEL", "claude-haiku-5-5"),
)
