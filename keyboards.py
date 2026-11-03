"""Inline-клавиатуры. Внешний URL появляется только на разрешённых экранах."""

from __future__ import annotations

from urllib.parse import quote, unquote

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
from content import button_label
from models import CATEGORIES, Article, User
from texts import fill, t, tz_label

HOME = "home"
DIGEST = "digest"
ANALYTICS = "analytics"
LATEST = "latest"
CATS = "cats"
CAT = "cat"
OPEN = "open"
FULL = "full"
NEXT = "next"
STORY = "story"
SETTINGS = "settings"
HELP = "help"
SOURCES = "sources"
LANG = "lang"
PUSH = "push"
HOUR = "hour"
TZ = "tz"
PLUS = "plus"
PAY = "pay"
WEEK = "week"
PLANS = "plans"
FEED = "feed"
ADD_SOURCE = "add_source"
ADMIN = "admin"
ADMIN_GRANT = "admin_grant"
ADMIN_REVOKE = "admin_revoke"
ADMIN_STATUS = "admin_status"
ADMIN_CONFIRM = "admin_confirm"
HOW_IT_WORKS = "how_it_works"


class Act(CallbackData, prefix="m"):
    a: str
    i: int = 0
    c: str = "-"


def _btn(text: str, action: str, item: int = 0, extra: str = "-") -> InlineKeyboardButton:
    label = text if len(text) <= 64 else text[:63] + "…"
    return InlineKeyboardButton(text=label, callback_data=Act(a=action, i=item, c=extra).pack())


def _article_buttons(articles: list[Article], origin: str) -> list[InlineKeyboardButton]:
    return [
        _btn(button_label(index, article.title), OPEN, article.id, origin)
        for index, article in enumerate(articles, start=1)
    ]


def feed_callback_key(key: str) -> str:
    """Escape ':' which aiogram uses as the CallbackData field separator."""
    return quote(key, safe="")


def feed_source_key(encoded: str) -> str:
    return unquote(encoded)


def origin_back(origin: str) -> tuple[str, int, str]:
    if origin == "d":
        return DIGEST, 0, "-"
    if origin == "l":
        return LATEST, 0, "-"
    if origin == "w":
        return WEEK, 0, "-"
    if origin == "s":
        return HOME, 0, "-"
    if origin == "p":
        return HOME, 0, "-"
    if origin.startswith("k") and origin[1:] in CATEGORIES:
        return CAT, 0, origin[1:]
    return HOME, 0, "-"


def home_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_btn(t(lang, "btn_how_it_works"), HOW_IT_WORKS))
    kb.row(_btn(t(lang, "btn_digest"), DIGEST))
    kb.row(_btn(t(lang, "btn_analytics"), ANALYTICS), _btn(t(lang, "btn_latest"), LATEST))
    kb.row(_btn(t(lang, "btn_cats"), CATS), _btn(t(lang, "btn_story"), STORY))
    kb.row(_btn(t(lang, "btn_subscription"), PLANS), _btn(t(lang, "btn_my_feed"), FEED))
    kb.row(_btn(t(lang, "btn_settings"), SETTINGS), _btn(t(lang, "btn_help"), HELP))
    return kb.as_markup()


def digest_keyboard(lang: str, articles: list[Article]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for button in _article_buttons(articles[:7], "d"):
        kb.row(button)
    kb.row(_btn(t(lang, "btn_analytics"), ANALYTICS), _btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()


def latest_keyboard(lang: str, articles: list[Article]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for button in _article_buttons(articles[:8], "l"):
        kb.row(button)
    kb.row(_btn(t(lang, "btn_digest"), DIGEST), _btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()


def categories_keyboard(lang: str, counts: dict[str, int]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for category in CATEGORIES:
        label = t(lang, f"cat_{category}")
        count = counts.get(category, 0)
        if count:
            label = f"{label} · {count}"
        kb.row(_btn(label, CAT, 0, category))
    kb.row(_btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()


def category_keyboard(lang: str, articles: list[Article], category: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for button in _article_buttons(articles[:6], f"k{category}"):
        kb.row(button)
    kb.row(_btn(t(lang, "btn_back"), CATS), _btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()


def analytics_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_btn(t(lang, "btn_story"), STORY))
    kb.row(_btn(t(lang, "btn_digest"), DIGEST), _btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()


def article_keyboard(lang: str, article_id: int, origin: str) -> InlineKeyboardMarkup:
    back_action, back_i, back_c = origin_back(origin)
    kb = InlineKeyboardBuilder()
    kb.row(_btn(t(lang, "btn_full"), FULL, article_id, origin))
    kb.row(_btn(t(lang, "btn_next"), NEXT, article_id, origin))
    kb.row(_btn(t(lang, "btn_back"), back_action, back_i, back_c), _btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()


def full_keyboard(lang: str, article: Article, origin: str, *, allow_link: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_btn(t(lang, "btn_next"), NEXT, article.id, origin))
    kb.row(
        _btn(t(lang, "btn_collapse"), OPEN, article.id, origin),
        _btn(t(lang, "btn_menu"), HOME),
    )
    return kb.as_markup()


def settings_keyboard(user: User) -> InlineKeyboardMarkup:
    lang = user.lang
    kb = InlineKeyboardBuilder()
    ru = "✓ Русский" if lang == "ru" else "Русский"
    en = "✓ English" if lang == "en" else "English"
    ar = "✓ العربية" if lang == "ar" else "العربية"
    kb.row(_btn(ru, LANG, 0, "ru"), _btn(en, LANG, 0, "en"), _btn(ar, LANG, 0, "ar"))
    push = t(lang, "btn_push_off") if user.notifications else t(lang, "btn_push_on")
    kb.row(_btn(push, PUSH, 0 if user.notifications else 1))
    hours = []
    for hour in config.DIGEST_HOURS:
        mark = "✓ " if user.digest_hour == hour else ""
        hours.append(_btn(f"{mark}{hour:02d}:00", HOUR, hour))
    kb.row(*hours[:3])
    kb.row(*hours[3:])
    zones = []
    for zone in config.TIMEZONES:
        mark = "✓ " if user.timezone == zone else ""
        zones.append(_btn(f"{mark}{tz_label(lang, zone)}", TZ, 0, zone))
    kb.row(*zones[:2])
    kb.row(*zones[2:])
    if user.premium_active():
        kb.row(_btn(t(lang, "btn_week"), WEEK))
        kb.row(_btn(t(lang, "btn_subscription"), PLANS))
    else:
        kb.row(_btn(t(lang, "btn_subscription"), PLANS))
    kb.row(_btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()


def help_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_btn(t(lang, "btn_digest"), DIGEST))
    kb.row(_btn(t(lang, "btn_sources"), SOURCES))
    kb.row(_btn(t(lang, "btn_settings"), SETTINGS), _btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()


def how_it_works_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_btn(t(lang, "btn_subscription"), PLANS), _btn(t(lang, "btn_my_feed"), FEED))
    kb.row(_btn(t(lang, "btn_digest"), DIGEST), _btn(t(lang, "btn_analytics"), ANALYTICS))
    kb.row(_btn(t(lang, "btn_help"), HELP), _btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()


def sources_keyboard(lang: str, links: list[tuple[str, str]] | None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_btn(t(lang, "btn_back"), HELP), _btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()


def plus_keyboard(lang: str, *, premium: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_btn(fill(t(lang, "btn_pay"), stars=config.PLUS_STARS), PAY))
    if premium:
        kb.row(_btn(t(lang, "btn_week"), WEEK))
    kb.row(_btn(t(lang, "btn_back"), SETTINGS), _btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()


def plans_keyboard(lang: str, premium: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_btn(t(lang, "btn_pay_plus"), PAY, 0, "plus"))
    kb.row(_btn(t(lang, "btn_pay_pro"), PAY, 0, "pro"))
    kb.row(_btn(t(lang, "btn_my_feed"), FEED))
    kb.row(_btn(t(lang, "btn_back"), HOME), _btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()


def feed_keyboard(lang: str, sources: list[tuple[str, bool, str | None, str]]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, enabled, locked, label in sources:
        mark = "✓ " if enabled else "○ "
        suffix = f" · {locked}" if locked else ""
        kb.row(_btn(f"{mark}{label}{suffix}", FEED, 0, feed_callback_key(key)))
    kb.row(_btn(t(lang, "btn_add_source"), ADD_SOURCE))
    kb.row(_btn(t(lang, "btn_subscription"), PLANS), _btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()


def week_keyboard(lang: str, articles: list[Article]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for button in _article_buttons(articles[:12], "w"):
        kb.row(button)
    kb.row(_btn(t(lang, "btn_back"), SETTINGS), _btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()


def menu_only(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()


def admin_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_btn(t(lang, "admin_grant"), ADMIN_GRANT))
    kb.row(_btn(t(lang, "admin_revoke"), ADMIN_REVOKE))
    kb.row(_btn(t(lang, "admin_status"), ADMIN_STATUS))
    kb.row(_btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()


def admin_confirm_keyboard(lang: str, user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_btn(t(lang, "admin_confirm"), ADMIN_CONFIRM, user_id))
    kb.row(_btn(t(lang, "admin_cancel"), ADMIN))
    return kb.as_markup()


def push_keyboard(lang: str, article_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_btn(t(lang, "btn_read"), OPEN, article_id, "p"))
    kb.row(_btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()
