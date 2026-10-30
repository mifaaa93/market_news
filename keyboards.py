"""Inline-клавиатуры. Внешний URL появляется только на разрешённых экранах."""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
from content import button_label, is_public_article_url
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


def origin_back(origin: str) -> tuple[str, int, str]:
    if origin == "d":
        return DIGEST, 0, "-"
    if origin == "l":
        return LATEST, 0, "-"
    if origin == "w":
        return WEEK, 0, "-"
    if origin == "s":
        return HOME, 0, "-"
    if origin.startswith("k") and origin[1:] in CATEGORIES:
        return CAT, 0, origin[1:]
    return HOME, 0, "-"


def home_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_btn(t(lang, "btn_digest"), DIGEST), _btn(t(lang, "btn_analytics"), ANALYTICS))
    kb.row(_btn(t(lang, "btn_latest"), LATEST), _btn(t(lang, "btn_cats"), CATS))
    kb.row(_btn(t(lang, "btn_story"), STORY))
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


def full_keyboard(lang: str, article: Article, origin: str, *, allow_link: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_btn(t(lang, "btn_next"), NEXT, article.id, origin))
    if allow_link and is_public_article_url(article.url):
        kb.row(InlineKeyboardButton(text=t(lang, "btn_source"), url=article.url))
    kb.row(
        _btn(t(lang, "btn_back"), OPEN, article.id, origin),
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
        kb.row(_btn(t(lang, "btn_plus_renew"), PLUS))
    else:
        kb.row(_btn(t(lang, "btn_plus"), PLUS))
    kb.row(_btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()


def help_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_btn(t(lang, "btn_digest"), DIGEST))
    kb.row(_btn(t(lang, "btn_sources"), SOURCES))
    kb.row(_btn(t(lang, "btn_settings"), SETTINGS), _btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()


def sources_keyboard(lang: str, links: list[tuple[str, str]] | None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if links:
        for name, url in links:
            if is_public_article_url(url):
                kb.row(InlineKeyboardButton(text=name, url=url))
    kb.row(_btn(t(lang, "btn_back"), HELP), _btn(t(lang, "btn_menu"), HOME))
    return kb.as_markup()


def plus_keyboard(lang: str, *, premium: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_btn(fill(t(lang, "btn_pay"), stars=config.PLUS_STARS), PAY))
    if premium:
        kb.row(_btn(t(lang, "btn_week"), WEEK))
    kb.row(_btn(t(lang, "btn_back"), SETTINGS), _btn(t(lang, "btn_menu"), HOME))
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
