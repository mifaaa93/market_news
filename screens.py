"""Сборка экранов: текст плюс клавиатура, без обращения в Telegram."""

from __future__ import annotations

from datetime import datetime, timezone

from aiogram.types import InlineKeyboardMarkup

import config
from content import (
    is_full_text,
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


async def home_screen(database: Database, user: User) -> Screen:
    picked = await database.list_top(user.lang, 3)
    updated = await database.meta_get("fetched_top_at")
    return render_home(picked, user.lang, user.timezone, updated), home_keyboard(user.lang)


async def digest_screen(database: Database, user: User, *, mailed: bool = False) -> Screen:
    picked = await database.list_top(user.lang, 10)
    updated = await database.meta_get("fetched_top_at")
    text = render_digest(picked, user.lang, user.timezone, updated, mailed=mailed)
    return text, digest_keyboard(user.lang, picked)


async def analytics_screen(database: Database, user: User) -> Screen:
    items = with_summary(await database.recent_for_user(user.user_id, 40))
    text = render_analytics(items, user.lang, premium=user.premium_active())
    return text, analytics_keyboard(user.lang)


async def latest_screen(database: Database, user: User) -> Screen:
    items = await database.recent_for_user(user.user_id, 8)
    return render_latest(items, user.lang), latest_keyboard(user.lang, items)


async def categories_screen(database: Database, user: User) -> Screen:
    counts = await database.category_counts(user.user_id)
    return render_categories(user.lang), categories_keyboard(user.lang, counts)


async def category_screen(database: Database, user: User, category: str) -> Screen:
    if category not in CATEGORIES:
        return await categories_screen(database, user)
    items = await database.by_category(category, 6, user_id=user.user_id)
    return render_category(category, items, user.lang), category_keyboard(user.lang, items, category)


async def article_screen(database: Database, user: User, article: Article, origin: str) -> Screen:
    shown = await database.apply_translations([article], user.lang)
    if not shown or not is_full_text(shown[0]):
        return t(user.lang, "no_article"), home_keyboard(user.lang)
    text = render_article(shown[0], user.lang, user.timezone)
    return text, article_keyboard(user.lang, article.id, origin)


async def full_screen(database: Database, user: User, article: Article, origin: str) -> Screen:
    shown = await database.apply_translations([article], user.lang)
    if not shown or not is_full_text(shown[0]):
        return t(user.lang, "no_article"), home_keyboard(user.lang)
    text = render_full(shown[0], user.lang, user.timezone, expanded=True)
    return text, full_keyboard(user.lang, article, origin)


async def settings_screen(user: User) -> Screen:
    return render_settings(user), settings_keyboard(user)


async def help_screen(database: Database, user: User) -> Screen:
    names = await database.headline_publisher_names(12)
    return render_help(user.lang, names), help_keyboard(user.lang)


async def how_it_works_screen(database: Database, user: User) -> Screen:
    names = await database.headline_publisher_names(12)
    return render_how_it_works(user.lang, names), how_it_works_keyboard(user.lang)


async def sources_screen(database: Database, user: User) -> Screen:
    sources, _ = await database.list_sources_page(offset=0, limit=12)
    names = await database.headline_publisher_names(12)
    blocks = [
        (item.name, t(user.lang, "src_default"))
        for item in sources
    ]
    return render_sources(user.lang, blocks, allow_link=False, names=names), sources_keyboard(user.lang, None)


async def plus_screen(user: User) -> Screen:
    return render_plus(user), plus_keyboard(user.lang, premium=user.premium_active())


async def plans_screen(database: Database, user: User) -> Screen:
    return render_plans(user, await database.count_sources()), plans_keyboard(
        user.lang, premium=user.premium_active()
    )


async def feed_screen(database: Database, user: User, page: int = 1) -> Screen:
    page_size = config.FEED_PAGE_SIZE
    total_sources = await database.count_sources()
    pages = max(1, (total_sources + page_size - 1) // page_size)
    page = min(max(1, page), pages)
    sources, _ = await database.list_sources_page(
        offset=(page - 1) * page_size, limit=page_size
    )
    states = await database.source_states(user.user_id, [item.id for item in sources])
    limit = await database.source_limits(user.active_plan())
    active_count = len(await database.enabled_source_ids(user.user_id))
    rows: list[tuple[int, bool, str | None, str, int]] = []
    for source in sources:
        enabled = states.get(source.id, False)
        locked: str | None = None
        if not enabled and active_count >= limit:
            locked = t(user.lang, "btn_plan_plus" if user.active_plan() == "base" else "btn_plan_pro")
        label = f"★ {source.name}" if source.headline_rank else source.name
        rows.append((source.id, enabled, locked, label, source.article_count))
    return render_feed(
        user, rows, page=page, pages=pages, enabled=active_count, limit=limit
    ), feed_keyboard(user.lang, rows, page=page, pages=pages)


async def week_screen(database: Database, user: User) -> Screen:
    if not user.premium_active():
        return await plus_screen(user)
    picked = pick_digest(
        with_summary(within_days(await database.recent_for_user(user.user_id, 80), 7, datetime.now(timezone.utc))),
        12,
    )
    return render_week(picked, user.lang), week_keyboard(user.lang, picked)


async def articles_for_origin(
    database: Database, origin: str, lang: str, user_id: int | None = None
) -> list[Article]:
    if origin in {"d", "s"}:
        items = await database.list_top(lang, 10)
    elif origin == "l":
        items = await database.recent_for_user(user_id, 8)
    elif origin == "w":
        items = pick_digest(
            with_summary(within_days(await database.recent_for_user(user_id, 80), 7)),
            12,
        )
    elif origin.startswith("k") and origin[1:] in CATEGORIES:
        items = await database.by_category(origin[1:], 6, user_id=user_id)
    else:
        items = await database.recent(8, lang=lang)
    return items
