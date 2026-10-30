"""Сборка экранов: текст плюс клавиатура, без обращения в Telegram."""

from __future__ import annotations

from datetime import datetime, timezone

from aiogram.types import InlineKeyboardMarkup

from content import (
    links_allowed,
    pick_digest,
    render_analytics,
    render_article,
    render_categories,
    render_category,
    render_digest,
    render_full,
    render_help,
    render_home,
    render_latest,
    render_plus,
    render_settings,
    render_sources,
    render_week,
    with_summary,
    within_days,
)
from db import Database
from feeds import PUBLISHERS
from fulltext import is_full_text
from keyboards import (
    analytics_keyboard,
    article_keyboard,
    categories_keyboard,
    category_keyboard,
    digest_keyboard,
    full_keyboard,
    help_keyboard,
    home_keyboard,
    latest_keyboard,
    plus_keyboard,
    settings_keyboard,
    sources_keyboard,
    week_keyboard,
)
from models import CATEGORIES, Article, User
from texts import t

Screen = tuple[str, InlineKeyboardMarkup]


async def external_links_open(database: Database, user: User) -> bool:
    return links_allowed(
        user.interactions,
        await database.count_seen(user.user_id),
        await database.count_articles(),
    )


async def _translated(database: Database, articles: list[Article], lang: str) -> list[Article]:
    return await database.apply_translations(articles, lang)


async def home_screen(database: Database, user: User) -> Screen:
    picked = pick_digest(with_summary(await database.recent(60, full_only=True)), 3)
    items = await _translated(database, picked, user.lang)
    updated = await database.meta_get("fetched_at")
    return render_home(items, user.lang, user.timezone, updated), home_keyboard(user.lang)


async def digest_screen(database: Database, user: User, *, mailed: bool = False) -> Screen:
    picked = pick_digest(with_summary(await database.recent(60, full_only=True)), 7)
    items = await _translated(database, picked, user.lang)
    updated = await database.meta_get("fetched_at")
    text = render_digest(items, user.lang, user.timezone, updated, mailed=mailed)
    return text, digest_keyboard(user.lang, items)


async def analytics_screen(database: Database, user: User) -> Screen:
    items = await _translated(database, with_summary(await database.recent(40, full_only=True)), user.lang)
    text = render_analytics(items, user.lang, premium=user.premium_active())
    return text, analytics_keyboard(user.lang)


async def latest_screen(database: Database, user: User) -> Screen:
    items = await _translated(database, await database.recent(8, full_only=True), user.lang)
    return render_latest(items, user.lang), latest_keyboard(user.lang, items)


async def categories_screen(database: Database, user: User) -> Screen:
    counts = await database.category_counts(full_only=True)
    return render_categories(user.lang), categories_keyboard(user.lang, counts)


async def category_screen(database: Database, user: User, category: str) -> Screen:
    if category not in CATEGORIES:
        return await categories_screen(database, user)
    items = await _translated(database, await database.by_category(category, 6, full_only=True), user.lang)
    return render_category(category, items, user.lang), category_keyboard(user.lang, items, category)


async def article_screen(database: Database, user: User, article: Article, origin: str) -> Screen:
    if not is_full_text(article):
        return t(user.lang, "no_article"), home_keyboard(user.lang)
    shown = (await _translated(database, [article], user.lang))[0]
    text = render_article(shown, user.lang, user.timezone)
    return text, article_keyboard(user.lang, shown.id, origin)


async def full_screen(database: Database, user: User, article: Article, origin: str) -> Screen:
    if not is_full_text(article):
        return t(user.lang, "no_article"), home_keyboard(user.lang)
    shown = (await _translated(database, [article], user.lang))[0]
    allow = await external_links_open(database, user)
    text = render_full(shown, user.lang, user.timezone, expanded=is_full_text(shown))
    return text, full_keyboard(user.lang, shown, origin, allow_link=allow)


async def settings_screen(user: User) -> Screen:
    return render_settings(user), settings_keyboard(user)


async def help_screen(user: User) -> Screen:
    return render_help(user.lang), help_keyboard(user.lang)


async def sources_screen(database: Database, user: User) -> Screen:
    blocks = [(item.name, t(user.lang, item.about_key)) for item in PUBLISHERS]
    allow = await external_links_open(database, user)
    links = [(item.name, item.homepage) for item in PUBLISHERS] if allow else None
    return render_sources(user.lang, blocks, allow_link=allow), sources_keyboard(user.lang, links)


async def plus_screen(user: User) -> Screen:
    return render_plus(user), plus_keyboard(user.lang, premium=user.premium_active())


async def week_screen(database: Database, user: User) -> Screen:
    if not user.premium_active():
        return await plus_screen(user)
    picked = pick_digest(
        with_summary(within_days(await database.recent(80, full_only=True), 7, datetime.now(timezone.utc))),
        12,
    )
    items = await _translated(database, picked, user.lang)
    return render_week(items, user.lang), week_keyboard(user.lang, items)


async def articles_for_origin(database: Database, origin: str, lang: str) -> list[Article]:
    if origin in {"d", "s"}:
        items = pick_digest(with_summary(await database.recent(60, full_only=True)), 7)
    elif origin == "l":
        items = await database.recent(8, full_only=True)
    elif origin == "w":
        items = pick_digest(with_summary(within_days(await database.recent(80, full_only=True), 7)), 12)
    elif origin.startswith("k") and origin[1:] in CATEGORIES:
        items = await database.by_category(origin[1:], 6, full_only=True)
    else:
        items = await database.recent(8, full_only=True)
    return await database.apply_translations(items, lang)
