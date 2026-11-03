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
    render_how_it_works,
    render_home,
    render_latest,
    render_plus,
    render_plans,
    render_feed,
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
    how_it_works_keyboard,
    home_keyboard,
    latest_keyboard,
    plus_keyboard,
    plans_keyboard,
    feed_keyboard,
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
    picked = pick_digest(with_summary(await database.recent_for_user(user.user_id, 60, full_only=True)), 3)
    items = await _translated(database, picked, user.lang)
    updated = await database.meta_get("fetched_at")
    return render_home(items, user.lang, user.timezone, updated), home_keyboard(user.lang)


async def digest_screen(database: Database, user: User, *, mailed: bool = False) -> Screen:
    picked = pick_digest(with_summary(await database.recent_for_user(user.user_id, 60, full_only=True)), 7)
    items = await _translated(database, picked, user.lang)
    updated = await database.meta_get("fetched_at")
    text = render_digest(items, user.lang, user.timezone, updated, mailed=mailed)
    return text, digest_keyboard(user.lang, items)


async def analytics_screen(database: Database, user: User) -> Screen:
    items = await _translated(database, with_summary(await database.recent_for_user(user.user_id, 40, full_only=True)), user.lang)
    text = render_analytics(items, user.lang, premium=user.premium_active())
    return text, analytics_keyboard(user.lang)


async def latest_screen(database: Database, user: User) -> Screen:
    items = await _translated(database, await database.recent_for_user(user.user_id, 8, full_only=True), user.lang)
    return render_latest(items, user.lang), latest_keyboard(user.lang, items)


async def categories_screen(database: Database, user: User) -> Screen:
    counts = await database.category_counts(full_only=True)
    return render_categories(user.lang), categories_keyboard(user.lang, counts)


async def category_screen(database: Database, user: User, category: str) -> Screen:
    if category not in CATEGORIES:
        return await categories_screen(database, user)
    items = await _translated(database, await database.by_category(category, 6, full_only=True, user_id=user.user_id), user.lang)
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
    text = render_full(shown, user.lang, user.timezone, expanded=is_full_text(shown))
    return text, full_keyboard(user.lang, shown, origin)


async def settings_screen(user: User) -> Screen:
    return render_settings(user), settings_keyboard(user)


async def help_screen(user: User) -> Screen:
    return render_help(user.lang), help_keyboard(user.lang)


async def how_it_works_screen(user: User) -> Screen:
    return render_how_it_works(user.lang), how_it_works_keyboard(user.lang)


async def sources_screen(database: Database, user: User) -> Screen:
    catalog = await database.list_sources()
    known = {item.key: item for item in PUBLISHERS}
    blocks = [
        (
            item.name,
            t(user.lang, known[item.key].about_key)
            if item.key in known
            else t(user.lang, "src_default"),
        )
        for item in catalog
    ]
    return render_sources(user.lang, blocks, allow_link=False), sources_keyboard(user.lang, None)


async def plus_screen(user: User) -> Screen:
    return render_plus(user), plus_keyboard(user.lang, premium=user.premium_active())


async def plans_screen(database: Database, user: User) -> Screen:
    return render_plans(user, len(await database.list_sources())), plans_keyboard(
        user.lang, premium=user.premium_active()
    )


async def feed_screen(database: Database, user: User) -> Screen:
    sources = await database.list_sources(user.user_id)
    states = await database.source_states(user.user_id)
    source_limit, custom_limit = await database.source_limits(user.plan if user.premium_active() else "base")
    active = await database.active_sources(user.user_id)
    active_count = len(active)
    custom_count = sum(1 for item in active if item.custom)
    rows: list[tuple[str, bool, str | None, str]] = []
    for source in sources:
        enabled = states.get(source.key, False)
        locked: str | None = None
        if not enabled and active_count >= source_limit:
            locked = t(user.lang, "btn_plan_plus" if user.plan == "base" else "btn_plan_pro")
        if source.custom and not enabled and custom_count >= custom_limit:
            locked = t(user.lang, "btn_plan_plus")
        rows.append((source.key, enabled, locked, source.name))
    return render_feed(user, rows), feed_keyboard(user.lang, rows)


async def week_screen(database: Database, user: User) -> Screen:
    if not user.premium_active():
        return await plus_screen(user)
    picked = pick_digest(
        with_summary(within_days(await database.recent_for_user(user.user_id, 80, full_only=True), 7, datetime.now(timezone.utc))),
        12,
    )
    items = await _translated(database, picked, user.lang)
    return render_week(items, user.lang), week_keyboard(user.lang, items)


async def articles_for_origin(
    database: Database, origin: str, lang: str, user_id: int | None = None
) -> list[Article]:
    if origin in {"d", "s"}:
        items = pick_digest(
            with_summary(await database.recent_for_user(user_id, 60, full_only=True)),
            7,
        )
    elif origin == "l":
        items = await database.recent_for_user(user_id, 8, full_only=True)
    elif origin == "w":
        items = pick_digest(
            with_summary(within_days(await database.recent_for_user(user_id, 80, full_only=True), 7)),
            12,
        )
    elif origin.startswith("k") and origin[1:] in CATEGORIES:
        items = await database.by_category(origin[1:], 6, full_only=True, user_id=user_id)
    else:
        items = await database.recent(8, full_only=True)
    return await database.apply_translations(items, lang)
