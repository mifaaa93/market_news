"""Market News — дайджест рынков в Telegram."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import signal
import sys
from urllib.parse import urlsplit
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
from feeds import refresh_all
from jobs import refresh_catalog, refresh_pro, translation_worker
from jobs import send_digests
from keyboards import (
    HOUR,
    LANG,
    PAY,
    PLUS,
    PLANS,
    FEED,
    ADD_SOURCE,
    ADMIN,
    ADMIN_GRANT,
    ADMIN_REVOKE,
    ADMIN_STATUS,
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
    HOME,
    LATEST,
    NEXT,
    OPEN,
    SETTINGS,
    SOURCES,
    STORY,
    home_keyboard,
    admin_keyboard,
    admin_confirm_keyboard,
    feed_source_key,
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
from rss_discovery import discover_custom_feed

log = logging.getLogger(__name__)

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)
router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)

database: Database | None = None


class AdminFlow(StatesGroup):
    action = State()
    confirm_revoke = State()


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
            )
        return await handler(event, data)


def _db() -> Database:
    if database is None:
        raise RuntimeError("database is not ready")
    return database


async def _load_if_empty(message: Message, user: User) -> None:
    if await _db().count_articles() > 0:
        return
    await show_edit(message, t(user.lang, "loading"), home_keyboard(user.lang))
    try:
        await refresh_all(_db())
    except Exception:
        log.exception("refresh failed")


async def _open_article(query: CallbackQuery, user: User, article_id: int, origin: str) -> None:
    article = await _db().get_article(article_id)
    if article is None or query.message is None:
        await ack(query)
        if query.message is not None:
            await show_edit(query.message, t(user.lang, "no_article"), home_keyboard(user.lang))
        return
    user = await _db().add_interaction(user.user_id)
    await _db().mark_seen(user.user_id, article.id)
    await ack(query)
    text, markup = await article_screen(_db(), user, article, origin)
    await show_edit(query.message, text, markup)


async def _content(query: CallbackQuery, user: User, builder) -> None:
    if query.message is None:
        await ack(query)
        return
    await ack(query)
    user = await _db().add_interaction(user.user_id)
    await _load_if_empty(query.message, user)
    text, markup = await builder(_db(), user)
    await show_edit(query.message, text, markup)


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User) -> None:
    log.info("start %s", db_user.user_id)
    if await _db().count_articles() == 0:
        placeholder = await show_message(message, t(db_user.lang, "loading"), home_keyboard(db_user.lang))
        try:
            await refresh_all(_db())
        except Exception:
            log.exception("start refresh failed")
        text, markup = await home_screen(_db(), db_user)
        if placeholder is not None:
            await show_edit(placeholder, text, markup)
        return
    text, markup = await home_screen(_db(), db_user)
    await show_message(message, text, markup)


@router.message(Command("digest", "today"))
async def cmd_digest(message: Message, db_user: User) -> None:
    db_user = await _db().add_interaction(db_user.user_id)
    placeholder = None
    if await _db().count_articles() == 0:
        placeholder = await show_message(message, t(db_user.lang, "loading"), home_keyboard(db_user.lang))
        try:
            await refresh_all(_db())
        except Exception:
            log.exception("digest refresh failed")
    text, markup = await digest_screen(_db(), db_user)
    if placeholder is not None:
        await show_edit(placeholder, text, markup)
        return
    await show_message(message, text, markup)


@router.message(Command("analytics"))
async def cmd_analytics(message: Message, db_user: User) -> None:
    db_user = await _db().add_interaction(db_user.user_id)
    text, markup = await analytics_screen(_db(), db_user)
    await show_message(message, text, markup)


@router.message(Command("settings"))
async def cmd_settings(message: Message, db_user: User) -> None:
    text, markup = await settings_screen(db_user)
    await show_message(message, text, markup)


@router.message(Command("help"))
async def cmd_help(message: Message, db_user: User) -> None:
    text, markup = await help_screen(db_user)
    await show_message(message, text, markup)


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


@router.message()
async def on_other(message: Message, db_user: User) -> None:
    if db_user.source_pending:
        if not db_user.premium_active():
            await _db().set_source_pending(db_user.user_id, False)
            text, markup = await plans_screen(_db(), db_user)
            await show_message(message, text, markup)
            return
        result = await discover_custom_feed(message.text or "")
        if result is None:
            await show_message(message, t(db_user.lang, "source_failed"), menu_only(db_user.lang))
            return
        name, feed_url, _ = result
        existing = await _db().source_by_url(db_user.user_id, feed_url)
        if existing is not None:
            await _db().set_source_pending(db_user.user_id, False)
            await show_message(message, t(db_user.lang, "source_duplicate"), menu_only(db_user.lang))
            return
        source_limit, custom_limit = await _db().source_limits(db_user.plan)
        active_sources = await _db().active_sources(db_user.user_id)
        custom_count = sum(item.custom for item in active_sources)
        if len(active_sources) >= source_limit or custom_count >= custom_limit:
            await _db().set_source_pending(db_user.user_id, False)
            await show_message(message, t(db_user.lang, "source_failed"), menu_only(db_user.lang))
            return
        digest = hashlib.sha256(feed_url.encode("utf-8")).hexdigest()[:16]
        key = f"custom:{db_user.user_id}:{digest}"
        await _db().add_custom_source(db_user.user_id, key, name, feed_url, urlsplit(message.text).scheme + "://" + urlsplit(message.text).netloc)
        await _db().set_source_pending(db_user.user_id, False)
        await show_message(message, fill(t(db_user.lang, "source_added"), name=name), menu_only(db_user.lang))
        return
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

    if action in {ADMIN, ADMIN_GRANT, ADMIN_REVOKE, ADMIN_STATUS, ADMIN_CONFIRM}:
        if not _is_admin(db_user.user_id):
            await ack(query, t(db_user.lang, "unknown"))
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
        await _load_if_empty(message, db_user)
        text, markup = await home_screen(_db(), db_user)
        await show_edit(message, text, markup)
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
            await show_edit(message, text, markup)
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
                await _load_if_empty(message, db_user)
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
        article = await _db().get_article(callback_data.i)
        if article is None:
            await ack(query)
            await show_edit(message, t(db_user.lang, "no_article"), home_keyboard(db_user.lang))
            return
        user = await _db().add_interaction(db_user.user_id, full_read=True)
        await _db().mark_seen(user.user_id, article.id)
        await ack(query)
        text, markup = await full_screen(_db(), user, article, callback_data.c or "-")
        await show_edit(message, text, markup)
        return

    if action == NEXT:
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
        await show_edit(message, text, markup)
        return

    if action == HELP:
        await ack(query)
        text, markup = await help_screen(db_user)
        await show_edit(message, text, markup)
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
        await show_edit(message, text, markup)
        return

    if action == FEED:
        if callback_data.c != "-":
            source = await _db().source(feed_source_key(callback_data.c))
            if source is not None and (
                source.owner_user_id is None or source.owner_user_id == db_user.user_id
            ):
                states = await _db().source_states(db_user.user_id)
                enabled = states.get(source.key, False)
                source_limit, _ = await _db().source_limits(db_user.plan if db_user.premium_active() else "base")
                active = await _db().active_sources(db_user.user_id)
                _, custom_limit = await _db().source_limits(
                    db_user.plan if db_user.premium_active() else "base"
                )
                custom_active = sum(1 for item in active if item.custom)
                if not enabled and (
                    len(active) >= source_limit
                    or (source.custom and custom_active >= custom_limit)
                ):
                    await ack(query, t(db_user.lang, "feed_locked"))
                else:
                    await _db().set_source_enabled(db_user.user_id, source.key, not enabled)
                    await ack(query)
            else:
                await ack(query)
        else:
            await ack(query)
        text, markup = await feed_screen(_db(), db_user)
        await show_edit(message, text, markup)
        return

    if action == ADD_SOURCE:
        fresh = await _db().require_user(db_user.user_id)
        if not fresh.premium_active():
            await ack(query)
            text, markup = await plans_screen(_db(), fresh)
            await show_edit(message, text, markup)
            return
        await _db().set_source_pending(fresh.user_id, True)
        await ack(query)
        await show_message(message, t(fresh.lang, "add_source_prompt"), menu_only(fresh.lang))
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
    from pathlib import Path

    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(Path(config.DB_PATH).parent / "bot.log", encoding="utf-8"),
        ],
    )
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("apscheduler").setLevel(logging.INFO)


async def translation_loop(database: Database, bot: Bot) -> None:
    """One sequential worker; the delay starts only after a completed batch."""
    while True:
        try:
            await translation_worker(database, bot)
        except asyncio.CancelledError:
            log.info("translation worker cancelled during shutdown")
            raise
        except Exception:
            log.exception("translation worker failed")
        await asyncio.sleep(config.TRANSLATION_WORKER_SECONDS)


async def run() -> None:
    global database
    setup_logging()
    database = Database(config.DB_PATH)
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
    scheduler = AsyncIOScheduler(timezone=timezone.utc)
    loop = asyncio.get_running_loop()
    run_task = asyncio.current_task()
    previous_sigint = signal.getsignal(signal.SIGINT)
    translation_task: asyncio.Task | None = None

    def on_sigint(signum, frame):
        # Do not restore SIG_DFL: a second Ctrl+C must not trigger cmd's batch prompt.
        if dp._stop_signal is not None and dp._running_lock.locked():
            loop.call_soon_threadsafe(dp._signal_stop_polling, signal.SIGINT)
        elif run_task is not None:
            loop.call_soon_threadsafe(run_task.cancel)

    signal.signal(signal.SIGINT, on_sigint)

    try:
        await _configure_bot(bot)
        startup = asyncio.create_task(startup_sync())

        async def refresh_job() -> None:
            try:
                await refresh_catalog(database, bot)
            except asyncio.CancelledError:
                log.info("scheduled refresh cancelled during shutdown")
            except Exception:
                log.exception("scheduled refresh failed")

        async def pro_refresh_job() -> None:
            try:
                await refresh_pro(database, bot)
            except asyncio.CancelledError:
                log.info("pro refresh cancelled during shutdown")
            except Exception:
                log.exception("pro refresh failed")

        async def digest_job() -> None:
            try:
                await send_digests(bot, database)
            except asyncio.CancelledError:
                log.info("digest job cancelled during shutdown")
            except Exception:
                log.exception("digest job failed")

        scheduler.add_job(
            refresh_job,
            "interval",
            minutes=config.RSS_REFRESH_MINUTES,
            coalesce=True,
            max_instances=2,
            misfire_grace_time=300,
            next_run_time=datetime.now(timezone.utc) + timedelta(minutes=config.RSS_REFRESH_MINUTES),
        )
        scheduler.add_job(
            pro_refresh_job,
            "interval",
            minutes=config.PRO_REFRESH_MINUTES,
            coalesce=True,
            max_instances=2,
            misfire_grace_time=120,
            next_run_time=datetime.now(timezone.utc) + timedelta(minutes=config.PRO_REFRESH_MINUTES),
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
        translation_task = asyncio.create_task(translation_loop(database, bot))
        log.info("Market News is up, articles=%s", await database.count_articles())
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot, handle_signals=False)
    finally:
        try:
            if scheduler.running:
                scheduler.shutdown(wait=False)
            if startup is not None:
                startup.cancel()
                try:
                    await startup
                except asyncio.CancelledError:
                    pass
            if translation_task is not None:
                translation_task.cancel()
                try:
                    await translation_task
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
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("Market News stopped")


if __name__ == "__main__":
    main()
