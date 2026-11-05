"""Market News — дайджест рынков в Telegram."""

from __future__ import annotations

import asyncio
import html
import logging
import signal
import sys
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatType, ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    ErrorEvent,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from aiogram import BaseMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from db import Database
from menu_covers import menu_cover_id, preload_menu_covers
from jobs import (
    image_worker,
    refresh_catalog,
    refresh_search,
    refresh_top,
    send_digests,
    translation_worker,
)
from keyboards import (
    HOUR,
    LANG,
    PAY,
    PLUS,
    PLANS,
    FEED,
    FIND,
    ADMIN,
    ADMIN_GRANT,
    ADMIN_REVOKE,
    ADMIN_STATUS,
    ADMIN_STATS,
    ADMIN_CONFIRM,
    PUSH,
    TZ,
    WEEK,
    Act,
    ANALYTICS,
    CAT,
    CATS,
    DIGEST,
    FULL,
    HELP,
    HOW_IT_WORKS,
    HOME,
    LATEST,
    NEXT,
    OPEN,
    SETTINGS,
    SOURCES,
    SOURCE,
    STORY,
    home_keyboard,
    admin_keyboard,
    admin_confirm_keyboard,
    feed_search_keyboard,
    menu_only,
)
from models import CATEGORIES, User
from screens import (
    analytics_screen,
    articles_for_origin,
    article_screen,
    categories_screen,
    category_screen,
    digest_screen,
    full_screen,
    help_screen,
    how_it_works_screen,
    home_screen,
    latest_screen,
    plus_screen,
    plans_screen,
    feed_screen,
    settings_screen,
    sources_screen,
    week_screen,
)
from texts import (
    ABOUT_AR,
    ABOUT_EN,
    ABOUT_RU,
    COMMANDS,
    COMMANDS_RU,
    SHORT_AR,
    SHORT_EN,
    SHORT_RU,
    fill,
    t,
)
from ui import ack, deliver, show_edit, show_message

log = logging.getLogger(__name__)

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)
router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)

database: Database | None = None


class AdminFlow(StatesGroup):
    action = State()
    confirm_revoke = State()


class FeedSearch(StatesGroup):
    waiting = State()


def _is_admin(user_id: int) -> bool:
    return user_id == config.ADMIN_USER_ID


def _admin_status(user: User, lang: str) -> str:
    if not user.premium_active():
        return t(lang, "btn_plan_base")
    from content import format_local

    return f"{user.plan.title()} · {format_local(user.premium_until, user.timezone)}"


def _admin_id(text: str) -> int | None:
    value = text.strip()
    if not value.isascii() or not value.isdecimal():
        return None
    number = int(value)
    return number if 0 < number <= 9223372036854775807 else None


async def _notify_plan_change(bot: Bot, user: User, revoked: bool) -> None:
    from content import format_local

    text = (
        t(user.lang, "admin_user_revoked")
        if revoked
        else fill(
            t(user.lang, "admin_user_granted"),
            plan=user.plan.title(),
            until=format_local(user.premium_until, user.timezone),
        )
    )
    try:
        await deliver(bot, user.user_id, text, home_keyboard(user.lang))
    except Exception:
        log.exception("Could not notify user %s of admin subscription change", user.user_id)


class UserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        from_user = getattr(event, "from_user", None)
        if from_user is not None and database is not None:
            data["db_user"] = await database.upsert_user(
                from_user.id,
                from_user.username,
                from_user.first_name,
                from_user.language_code,
            )
        return await handler(event, data)


def _db() -> Database:
    if database is None:
        raise RuntimeError("database is not ready")
    return database


async def _enable_catalog_source(user: User, source) -> str:
    states = await _db().source_states(user.user_id, [source.id])
    if states.get(source.id):
        return "already"
    limit = await _db().source_limits(user.active_plan())
    active = len(await _db().enabled_source_ids(user.user_id))
    if active >= limit:
        return "locked"
    await _db().set_source_enabled(user.user_id, source.id, True)
    return "ok"


async def _open_article(query: CallbackQuery, user: User, article_id: int, origin: str) -> None:
    await ack(query)
    if query.message is None:
        return
    article = await _db().get_article(article_id)
    if article is None:
        await show_edit(query.message, t(user.lang, "no_article"), home_keyboard(user.lang))
        return
    user = await _db().add_interaction(user.user_id)
    await _db().mark_seen(user.user_id, article.id)
    text, markup = await article_screen(_db(), user, article, origin)
    await show_edit(query.message, text, markup, article.telegram_photo_id)


async def _content(query: CallbackQuery, user: User, builder) -> None:
    if query.message is None:
        await ack(query)
        return
    await ack(query)
    user = await _db().add_interaction(user.user_id)
    text, markup = await builder(_db(), user)
    cover = {
        digest_screen: "digest",
        analytics_screen: "analytics",
        latest_screen: "latest",
        categories_screen: "categories",
    }.get(builder)
    await show_edit(query.message, text, markup, menu_cover_id(cover) if cover else None)


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User, state: FSMContext) -> None:
    await state.clear()
    log.info("start %s", db_user.user_id)
    text, markup = await home_screen(_db(), db_user)
    await show_message(message, text, markup, menu_cover_id("how_it_works"))


@router.message(Command("digest", "today"))
async def cmd_digest(message: Message, db_user: User) -> None:
    db_user = await _db().add_interaction(db_user.user_id)
    text, markup = await digest_screen(_db(), db_user)
    await show_message(message, text, markup, menu_cover_id("digest"))


@router.message(Command("analytics"))
async def cmd_analytics(message: Message, db_user: User) -> None:
    db_user = await _db().add_interaction(db_user.user_id)
    text, markup = await analytics_screen(_db(), db_user)
    await show_message(message, text, markup, menu_cover_id("analytics"))


@router.message(Command("settings"))
async def cmd_settings(message: Message, db_user: User) -> None:
    text, markup = await settings_screen(db_user)
    await show_message(message, text, markup, menu_cover_id("settings"))


@router.message(Command("help"))
async def cmd_help(message: Message, db_user: User) -> None:
    text, markup = await help_screen(_db(), db_user)
    await show_message(message, text, markup, menu_cover_id("help"))


@router.message(Command("admin"))
async def cmd_admin(message: Message, db_user: User, state: FSMContext) -> None:
    if not _is_admin(db_user.user_id):
        await show_message(message, t(db_user.lang, "unknown"), home_keyboard(db_user.lang))
        return
    await state.clear()
    await show_message(
        message,
        f"<b>{t(db_user.lang, 'admin_title')}</b>\n\n{t(db_user.lang, 'admin_intro')}",
        admin_keyboard(db_user.lang),
    )


@router.message(AdminFlow.action, F.text)
async def admin_input(message: Message, db_user: User, state: FSMContext) -> None:
    if not _is_admin(db_user.user_id):
        await state.clear()
        return
    data = await state.get_data()
    action = data.get("action")
    parts = (message.text or "").strip().split()
    if action == "grant":
        if len(parts) not in (2, 3):
            await show_message(message, t(db_user.lang, "admin_bad_input"), admin_keyboard(db_user.lang))
            return
        user_id = _admin_id(parts[0])
        plan = parts[1].lower()
        try:
            days = int(parts[2]) if len(parts) == 3 else config.PLUS_DAYS
        except ValueError:
            days = 0
        if user_id is None or plan not in {"plus", "pro"} or not 1 <= days <= 365:
            await show_message(message, t(db_user.lang, "admin_bad_input"), admin_keyboard(db_user.lang))
            return
        user = await _db().admin_grant(db_user.user_id, user_id, plan, days)
        await state.clear()
        from content import format_local

        await show_message(
            message,
            fill(
                t(db_user.lang, "admin_granted"),
                plan=user.plan.title(),
                user_id=user_id,
                until=format_local(user.premium_until, user.timezone),
            ),
            admin_keyboard(db_user.lang),
        )
        await _notify_plan_change(message.bot, user, revoked=False)
        return

    if action not in {"revoke", "status"} or len(parts) != 1:
        await show_message(message, t(db_user.lang, "admin_bad_input"), admin_keyboard(db_user.lang))
        return
    user_id = _admin_id(parts[0])
    user = await _db().get_user(user_id) if user_id is not None else None
    if user_id is None:
        await show_message(message, t(db_user.lang, "admin_bad_input"), admin_keyboard(db_user.lang))
    elif user is None:
        await show_message(message, t(db_user.lang, "admin_not_found"), admin_keyboard(db_user.lang))
    elif action == "status":
        await state.clear()
        await show_message(
            message,
            fill(
                t(db_user.lang, "admin_status_result"),
                user_id=user_id,
                status=_admin_status(user, db_user.lang),
            ),
            admin_keyboard(db_user.lang),
        )
    else:
        await state.set_state(AdminFlow.confirm_revoke)
        await state.update_data(target_user_id=user_id)
        await show_message(
            message,
            fill(
                t(db_user.lang, "admin_confirm_question"),
                user_id=user_id,
                status=_admin_status(user, db_user.lang),
            ),
            admin_confirm_keyboard(db_user.lang, user_id),
        )


@router.message(F.successful_payment)
async def on_paid(message: Message, db_user: User) -> None:
    payment = message.successful_payment
    if payment is None:
        return
    payload = payment.invoice_payload or ""
    plan = {"plus30": "plus", "pro30": "pro"}.get(payload)
    expected = config.PLUS_STARS if plan == "plus" else config.PRO_STARS if plan == "pro" else 0
    if not plan or payment.currency != "XTR":
        return
    if payment.total_amount < expected:
        return
    charge = payment.telegram_payment_charge_id or f"msg:{message.chat.id}:{message.message_id}"
    first = await _db().save_payment(charge, db_user.user_id, payment.total_amount)
    if not first:
        return
    user = await _db().extend_plan(db_user.user_id, plan, config.PLUS_DAYS)
    until = ""
    if user.premium_until:
        from content import format_local

        until = format_local(user.premium_until, user.timezone)
    await show_message(
        message,
        fill(t(user.lang, "plus_thanks"), plan=plan.title(), until=until),
        home_keyboard(user.lang),
    )


@router.message(AdminFlow.confirm_revoke, F.text)
async def admin_wait_confirmation(message: Message, db_user: User) -> None:
    if _is_admin(db_user.user_id):
        await show_message(
            message,
            t(db_user.lang, "admin_confirm_wait"),
            admin_keyboard(db_user.lang),
        )


@router.message(FeedSearch.waiting, F.text)
async def on_feed_search(message: Message, db_user: User, state: FSMContext) -> None:
    await state.clear()
    found = await _db().search_sources(message.text or "", limit=8)
    if not found:
        await show_message(
            message,
            t(db_user.lang, "source_not_found"),
            menu_only(db_user.lang),
        )
        return
    if len(found) == 1:
        source = found[0]
        result = await _enable_catalog_source(db_user, source)
        if result == "locked":
            text, markup = await plans_screen(_db(), db_user)
            await show_message(message, text, markup)
            return
        key = "source_already" if result == "already" else "source_enabled"
        notice = fill(t(db_user.lang, key), name=source.name)
        text, markup = await feed_screen(_db(), db_user, 1)
        await show_message(
            message,
            f"<p>{html.escape(notice)}</p>{text}",
            markup,
        )
        return
    enabled_ids = set(await _db().enabled_source_ids(db_user.user_id))
    await show_message(
        message,
        t(db_user.lang, "source_many"),
        feed_search_keyboard(db_user.lang, found, enabled_ids),
    )


@router.message()
async def on_other(message: Message, db_user: User) -> None:
    await show_message(message, t(db_user.lang, "unknown"), home_keyboard(db_user.lang))


@router.callback_query(Act.filter())
async def on_action(
    query: CallbackQuery, callback_data: Act, db_user: User, state: FSMContext
) -> None:
    action = callback_data.a
    message = query.message
    if message is None:
        await ack(query)
        return

    if action in {ADMIN, ADMIN_GRANT, ADMIN_REVOKE, ADMIN_STATUS, ADMIN_STATS, ADMIN_CONFIRM}:
        if not _is_admin(db_user.user_id):
            await ack(query, t(db_user.lang, "unknown"))
            return
        if action == ADMIN_STATS:
            from content import cat_name

            stats = await _db().admin_stats()
            cats = "<br/>".join(
                f"{html.escape(cat_name(db_user.lang, name))}: {count}"
                for name, count in stats["categories"]
            ) or "—"
            await ack(query)
            await show_edit(
                message,
                fill(
                    t(db_user.lang, "admin_stats_text"),
                    articles=stats["articles"],
                    today=stats["today"],
                    categories=cats,
                    users=stats["users"],
                    picks=stats["picks"],
                    catalog=stats["catalog"],
                ),
                admin_keyboard(db_user.lang),
            )
            return
        if action == ADMIN_CONFIRM:
            data = await state.get_data()
            target = data.get("target_user_id")
            if (
                await state.get_state() != AdminFlow.confirm_revoke.state
                or target != callback_data.i
            ):
                await ack(query, t(db_user.lang, "admin_expired"))
                return
            user = await _db().get_user(target)
            await state.clear()
            if user is None:
                await ack(query)
                await show_edit(message, t(db_user.lang, "admin_not_found"), admin_keyboard(db_user.lang))
                return
            updated = await _db().admin_revoke(db_user.user_id, target)
            await ack(query)
            await show_edit(
                message,
                fill(t(db_user.lang, "admin_revoked"), user_id=target),
                admin_keyboard(db_user.lang),
            )
            await _notify_plan_change(query.bot, updated, revoked=True)
            return
        await state.clear()
        if action == ADMIN:
            text = f"<b>{t(db_user.lang, 'admin_title')}</b>\n\n{t(db_user.lang, 'admin_intro')}"
        else:
            await state.set_state(AdminFlow.action)
            await state.update_data(action={
                ADMIN_GRANT: "grant", ADMIN_REVOKE: "revoke", ADMIN_STATUS: "status",
            }[action])
            text = t(
                db_user.lang,
                "admin_prompt_grant" if action == ADMIN_GRANT else "admin_prompt_user",
            )
        await ack(query)
        await show_edit(message, text, admin_keyboard(db_user.lang))
        return

    if _is_admin(db_user.user_id) and await state.get_state() is not None:
        await state.clear()

    if action == HOME:
        await ack(query)
        text, markup = await home_screen(_db(), db_user)
        await show_edit(message, text, markup, menu_cover_id("how_it_works"))
        return

    if action == HOW_IT_WORKS:
        await ack(query)
        text, markup = await how_it_works_screen(_db(), db_user)
        await show_edit(message, text, markup, menu_cover_id("how_it_works"))
        return

    if action == DIGEST:
        await _content(query, db_user, digest_screen)
        return

    if action == ANALYTICS:
        await _content(query, db_user, analytics_screen)
        return

    if action == LATEST:
        await _content(query, db_user, latest_screen)
        return

    if action == CATS:
        await _content(query, db_user, categories_screen)
        return

    if action == CAT:
        category = callback_data.c
        if category not in CATEGORIES:
            await ack(query)
            text, markup = await categories_screen(_db(), db_user)
            await show_edit(message, text, markup, menu_cover_id("categories"))
            return

        async def _cat(db, user, category=category):
            return await category_screen(db, user, category)

        await _content(query, db_user, _cat)
        return

    if action in {OPEN, STORY}:
        if action == STORY:
            picked = await articles_for_origin(_db(), "s", db_user.lang, db_user.user_id)
            if not picked:
                await ack(query)
                await show_edit(message, t(db_user.lang, "story_empty"), home_keyboard(db_user.lang))
                return
            await _open_article(query, db_user, picked[0].id, "s")
            return
        await _open_article(query, db_user, callback_data.i, callback_data.c or "-")
        return

    if action == FULL:
        await ack(query)
        article = await _db().get_article(callback_data.i)
        if article is None:
            await show_edit(message, t(db_user.lang, "no_article"), home_keyboard(db_user.lang))
            return
        user = await _db().add_interaction(db_user.user_id, full_read=True)
        await _db().mark_seen(user.user_id, article.id)
        text, markup = await full_screen(_db(), user, article, callback_data.c or "-")
        await show_edit(message, text, markup, article.telegram_photo_id)
        return

    if action == SOURCE:
        article = await _db().get_article(callback_data.i)
        if article is None:
            await ack(query)
            await show_edit(message, t(db_user.lang, "no_article"), home_keyboard(db_user.lang))
            return
        states = await _db().source_states(db_user.user_id, [article.source_id])
        enabled = states.get(article.source_id, False)
        if not enabled:
            limit = await _db().source_limits(db_user.active_plan())
            active = len(await _db().enabled_source_ids(db_user.user_id))
            if active >= limit:
                await ack(query)
                text, markup = await plans_screen(_db(), db_user)
                await show_message(message, text, markup, menu_cover_id("subscription"))
                return
        await _db().set_source_enabled(db_user.user_id, article.source_id, not enabled)
        origin = (callback_data.c or "-")[1:]
        await ack(query)
        if callback_data.c.startswith("f"):
            text, markup = await full_screen(_db(), db_user, article, origin)
        else:
            text, markup = await article_screen(_db(), db_user, article, origin)
        await show_edit(message, text, markup, article.telegram_photo_id)
        return

    if action == NEXT:
        await ack(query)
        origin = callback_data.c or "-"
        items = await articles_for_origin(_db(), origin, db_user.lang, db_user.user_id)
        if not items:
            await ack(query)
            await show_edit(message, t(db_user.lang, "empty"), home_keyboard(db_user.lang))
            return
        ids = [item.id for item in items]
        if callback_data.i in ids and len(ids) == 1:
            await ack(query, t(db_user.lang, "only_one"))
            return
        if callback_data.i in ids:
            nxt = ids[(ids.index(callback_data.i) + 1) % len(ids)]
        else:
            nxt = ids[0]
        await _open_article(query, db_user, nxt, origin)
        return

    if action == SETTINGS:
        await ack(query)
        text, markup = await settings_screen(db_user)
        await show_edit(message, text, markup, menu_cover_id("settings"))
        return

    if action == HELP:
        await ack(query)
        text, markup = await help_screen(_db(), db_user)
        await show_edit(message, text, markup, menu_cover_id("help"))
        return

    if action == SOURCES:
        await ack(query)
        text, markup = await sources_screen(_db(), db_user)
        await show_edit(message, text, markup)
        return

    if action == LANG and callback_data.c in {"ru", "en", "ar"}:
        user = await _db().set_lang(db_user.user_id, callback_data.c)
        await ack(query)
        text, markup = await settings_screen(user)
        await show_edit(message, text, markup)
        return

    if action == PUSH and callback_data.i in {0, 1}:
        user = await _db().set_notifications(db_user.user_id, bool(callback_data.i))
        await ack(query)
        text, markup = await settings_screen(user)
        await show_edit(message, text, markup)
        return

    if action == HOUR and callback_data.i in config.DIGEST_HOURS:
        user = await _db().set_hour(db_user.user_id, callback_data.i)
        await ack(query)
        text, markup = await settings_screen(user)
        await show_edit(message, text, markup)
        return

    if action == TZ and callback_data.c in config.TIMEZONES:
        user = await _db().set_timezone(db_user.user_id, callback_data.c)
        await ack(query)
        text, markup = await settings_screen(user)
        await show_edit(message, text, markup)
        return

    if action == PLUS:
        await ack(query)
        text, markup = await plus_screen(db_user)
        await show_edit(message, text, markup)
        return

    if action == PLANS:
        await ack(query)
        text, markup = await plans_screen(_db(), db_user)
        await show_edit(message, text, markup, menu_cover_id("subscription"))
        return

    if action == FIND:
        source = await _db().source(callback_data.i)
        if source is None:
            await ack(query)
            await show_edit(message, t(db_user.lang, "source_not_found"), menu_only(db_user.lang))
            return
        states = await _db().source_states(db_user.user_id, [source.id])
        enabled = states.get(source.id, False)
        if not enabled:
            limit = await _db().source_limits(db_user.active_plan())
            active = len(await _db().enabled_source_ids(db_user.user_id))
            if active >= limit:
                await ack(query)
                text, markup = await plans_screen(_db(), db_user)
                await show_message(message, text, markup, menu_cover_id("subscription"))
                return
        await _db().set_source_enabled(db_user.user_id, source.id, not enabled)
        ids = [
            parsed.i
            for row in (message.reply_markup.inline_keyboard if message.reply_markup else [])
            for button in row
            if button.callback_data
            for parsed in [Act.unpack(button.callback_data)]
            if parsed.a == FIND
        ]
        found = [item for item in [await _db().source(int(source_id)) for source_id in ids] if item]
        if not found:
            found = [source]
        await ack(query)
        await show_edit(
            message,
            t(db_user.lang, "source_many"),
            feed_search_keyboard(
                db_user.lang, found, set(await _db().enabled_source_ids(db_user.user_id))
            ),
        )
        return

    if action == FEED:
        page = 1
        if callback_data.c == "find":
            await state.set_state(FeedSearch.waiting)
            await ack(query)
            await show_edit(
                message,
                t(db_user.lang, "source_search_prompt"),
                menu_only(db_user.lang),
            )
            return
        if callback_data.c in {"off", "star", "all"}:
            page = callback_data.i or 1
            if callback_data.c == "off":
                await _db().disable_all_sources(db_user.user_id)
            elif callback_data.c == "all":
                await _db().enable_all_sources(
                    db_user.user_id, await _db().source_limits(db_user.active_plan())
                )
            else:
                limit = await _db().source_limits(db_user.active_plan())
                await _db().enable_headline_sources(db_user.user_id, limit)
            await ack(query)
        elif callback_data.i > 0:
            if callback_data.c.isdigit():
                page = int(callback_data.c)
            source = await _db().source(callback_data.i)
            if source is not None:
                states = await _db().source_states(db_user.user_id, [source.id])
                enabled = states.get(source.id, False)
                limit = await _db().source_limits(db_user.active_plan())
                active_count = len(await _db().enabled_source_ids(db_user.user_id))
                if not enabled and active_count >= limit:
                    await ack(
                        query,
                        fill(
                            t(db_user.lang, "feed_locked"),
                            plan=t(
                                db_user.lang,
                                "btn_plan_plus" if db_user.active_plan() == "base" else "btn_plan_pro",
                            ),
                        ),
                    )
                else:
                    await _db().set_source_enabled(db_user.user_id, source.id, not enabled)
                    await ack(query)
            else:
                await ack(query)
        else:
            if callback_data.c.isdigit():
                page = int(callback_data.c)
            await ack(query)
        text, markup = await feed_screen(_db(), db_user, page)
        await show_edit(message, text, markup, menu_cover_id("feed"))
        return

    if action == PAY:
        plan = callback_data.c if callback_data.c in {"plus", "pro"} else "plus"
        stars = config.PLUS_STARS if plan == "plus" else config.PRO_STARS
        await ack(query)
        try:
            await message.answer_invoice(
                title=fill(t(db_user.lang, "plus_invoice_title"), plan=plan.title())[:32],
                description=t(db_user.lang, "plus_invoice_desc")[:255],
                payload=f"{plan}30",
                currency="XTR",
                # Для Telegram Stars amount — число звёзд, не копейки.
                prices=[LabeledPrice(label=plan.title(), amount=stars)],
                provider_token="",
            )
        except TelegramBadRequest:
            log.exception("invoice failed")
            await show_message(message, t(db_user.lang, "pay_failed"), menu_only(db_user.lang))
        return

    if action == WEEK:
        await ack(query)
        fresh = await _db().require_user(db_user.user_id)
        if fresh.premium_active():
            fresh = await _db().add_interaction(fresh.user_id)
        text, markup = await week_screen(_db(), fresh)
        await show_edit(message, text, markup)
        return

    await ack(query)
    text, markup = await home_screen(_db(), db_user)
    await show_edit(message, text, markup)


@router.callback_query()
async def on_unknown_callback(query: CallbackQuery, db_user: User) -> None:
    await ack(query)
    if query.message is None:
        return
    text, markup = await home_screen(_db(), db_user)
    await show_edit(query.message, text, markup)


@router.pre_checkout_query()
async def on_checkout(query: PreCheckoutQuery) -> None:
    plan = {"plus30": "plus", "pro30": "pro"}.get(query.invoice_payload)
    expected = config.PLUS_STARS if plan == "plus" else config.PRO_STARS if plan == "pro" else 0
    ok = (
        plan is not None
        and query.currency == "XTR"
        and query.total_amount >= expected
    )
    if ok:
        await query.answer(ok=True)
        return
    await query.answer(ok=False, error_message="Payment is not available.")


@router.error()
async def on_error(event: ErrorEvent) -> None:
    log.exception("update failed", exc_info=event.exception)
    message = None
    if event.update.message:
        message = event.update.message
    elif event.update.callback_query and event.update.callback_query.message:
        message = event.update.callback_query.message
        try:
            await event.update.callback_query.answer()
        except TelegramBadRequest:
            pass
    if message is not None:
        try:
            await show_message(message, t("ru", "error"), home_keyboard("ru"))
        except Exception:
            log.exception("could not send the error note")


async def _configure_bot(bot: Bot) -> None:
    async def attempt(label: str, coro) -> None:
        try:
            await coro
        except Exception:
            log.exception("bot setup failed: %s", label)

    await attempt(
        "commands",
        bot.set_my_commands([BotCommand(command=name, description=desc) for name, desc in COMMANDS_RU]),
    )
    for code, rows in COMMANDS.items():
        await attempt(
            f"commands-{code}",
            bot.set_my_commands(
                [BotCommand(command=name, description=desc) for name, desc in rows],
                language_code=code,
            ),
        )
    if len(ABOUT_RU) <= 512:
        await attempt("about", bot.set_my_description(description=ABOUT_RU))
        await attempt("about-ru", bot.set_my_description(description=ABOUT_RU, language_code="ru"))
    if len(ABOUT_EN) <= 512:
        await attempt("about-en", bot.set_my_description(description=ABOUT_EN, language_code="en"))
    if len(ABOUT_AR) <= 512:
        await attempt("about-ar", bot.set_my_description(description=ABOUT_AR, language_code="ar"))
    if len(SHORT_RU) <= 120:
        await attempt("short", bot.set_my_short_description(short_description=SHORT_RU))
        await attempt("short-ru", bot.set_my_short_description(short_description=SHORT_RU, language_code="ru"))
    if len(SHORT_EN) <= 120:
        await attempt("short-en", bot.set_my_short_description(short_description=SHORT_EN, language_code="en"))
    if len(SHORT_AR) <= 120:
        await attempt("short-ar", bot.set_my_short_description(short_description=SHORT_AR, language_code="ar"))


def setup_logging() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    config.DATA_PATH.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(config.DATA_PATH / "bot.log", encoding="utf-8"),
        ],
    )
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("apscheduler").setLevel(logging.INFO)


async def run() -> None:
    global database
    setup_logging()
    database = Database(config.DATABASE_URL)
    await database.connect()

    async def startup_sync() -> None:
        try:
            await refresh_catalog(database)
        except Exception:
            log.exception("startup sync failed")

    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    router.message.middleware(UserMiddleware())
    router.callback_query.middleware(UserMiddleware())
    dp.include_router(router)
    startup: asyncio.Task | None = None
    translation_task: asyncio.Task | None = None
    image_task: asyncio.Task | None = None
    scheduler = AsyncIOScheduler(timezone=timezone.utc)
    loop = asyncio.get_running_loop()
    run_task = asyncio.current_task()
    previous_sigint = signal.getsignal(signal.SIGINT)
    def on_sigint(signum, frame):
        # Do not restore SIG_DFL: a second Ctrl+C must not trigger cmd's batch prompt.
        if dp._stop_signal is not None and dp._running_lock.locked():
            loop.call_soon_threadsafe(dp._signal_stop_polling, signal.SIGINT)
        elif run_task is not None:
            loop.call_soon_threadsafe(run_task.cancel)

    signal.signal(signal.SIGINT, on_sigint)

    try:
        await _configure_bot(bot)
        try:
            cached = await preload_menu_covers(bot)
            log.info("menu covers cached=%s", cached)
        except Exception:
            log.exception("menu cover preload failed; continuing without covers")
        startup = asyncio.create_task(startup_sync())

        async def search_job() -> None:
            try:
                await refresh_search(database, bot)
            except asyncio.CancelledError:
                log.info("search refresh cancelled during shutdown")
            except Exception:
                log.exception("scheduled search failed")

        async def top_job() -> None:
            try:
                await refresh_top(database, bot)
            except asyncio.CancelledError:
                log.info("top refresh cancelled during shutdown")
            except Exception:
                log.exception("scheduled top failed")

        async def digest_job() -> None:
            try:
                await send_digests(bot, database)
            except asyncio.CancelledError:
                log.info("digest job cancelled during shutdown")
            except Exception:
                log.exception("digest job failed")

        scheduler.add_job(
            search_job,
            "interval",
            minutes=1,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=120,
            next_run_time=datetime.now(timezone.utc) + timedelta(minutes=1),
        )
        scheduler.add_job(
            top_job,
            "cron",
            hour=",".join(str(hour) for hour in config.GNEWS_TOP_HOURS),
            minute=0,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=600,
        )
        scheduler.add_job(
            digest_job,
            "interval",
            minutes=1,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=120,
        )
        scheduler.start()

        async def translation_loop() -> None:
            while True:
                try:
                    await translation_worker(database, bot)
                except asyncio.CancelledError:
                    log.info("translation worker cancelled during shutdown")
                    raise
                except Exception:
                    log.exception("translation worker failed")
                await asyncio.sleep(config.TRANSLATION_WORKER_SECONDS)

        async def image_loop() -> None:
            while True:
                try:
                    await image_worker(database, bot)
                except asyncio.CancelledError:
                    log.info("image worker cancelled during shutdown")
                    raise
                except Exception:
                    log.exception("image worker failed")
                await asyncio.sleep(config.IMAGE_WORKER_SECONDS)

        image_task = asyncio.create_task(image_loop())
        translation_task = asyncio.create_task(translation_loop())
        log.info("Market News is up, articles=%s", await database.count_articles())
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot, handle_signals=False)
    finally:
        try:
            if scheduler.running:
                scheduler.shutdown(wait=False)
            if translation_task is not None:
                translation_task.cancel()
                try:
                    await translation_task
                except asyncio.CancelledError:
                    pass
            if image_task is not None:
                image_task.cancel()
                try:
                    await image_task
                except asyncio.CancelledError:
                    pass
            if startup is not None:
                startup.cancel()
                try:
                    await startup
                except asyncio.CancelledError:
                    pass
            await database.close()
        finally:
            try:
                await bot.session.close()
            finally:
                signal.signal(signal.SIGINT, previous_sigint)
                log.info("Market News stopped")


def main() -> None:
    if not config.BOT_TOKEN:
        print("Нет токена. Создайте файл .env и укажите BOT_TOKEN. Образец — .env.example")
        raise SystemExit(1)
    if not config.DATABASE_URL:
        print("Нет DATABASE_URL. Задайте его в .env или через docker compose.")
        raise SystemExit(1)
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("Market News stopped")


if __name__ == "__main__":
    main()
