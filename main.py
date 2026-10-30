"""Market News — дайджест рынков в Telegram."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatType, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
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
from jobs import refresh_catalog
from jobs import send_digests
from keyboards import (
    HOUR,
    LANG,
    PAY,
    PLUS,
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
from ui import ack, show_edit, show_message

log = logging.getLogger(__name__)

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)
router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)

database: Database | None = None


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


@router.message(F.successful_payment)
async def on_paid(message: Message, db_user: User) -> None:
    payment = message.successful_payment
    if payment is None:
        return
    if payment.invoice_payload != "plus30" or payment.currency != "XTR":
        return
    if payment.total_amount < config.PLUS_STARS:
        return
    charge = payment.telegram_payment_charge_id or f"msg:{message.chat.id}:{message.message_id}"
    first = await _db().save_payment(charge, db_user.user_id, payment.total_amount)
    if not first:
        return
    user = await _db().extend_premium(db_user.user_id, config.PLUS_DAYS)
    until = ""
    if user.premium_until:
        from content import format_local

        until = format_local(user.premium_until, user.timezone)
    await show_message(
        message,
        fill(t(user.lang, "plus_thanks"), until=until),
        home_keyboard(user.lang),
    )


@router.message()
async def on_other(message: Message, db_user: User) -> None:
    await show_message(message, t(db_user.lang, "unknown"), home_keyboard(db_user.lang))


@router.callback_query(Act.filter())
async def on_action(query: CallbackQuery, callback_data: Act, db_user: User) -> None:
    action = callback_data.a
    message = query.message
    if message is None:
        await ack(query)
        return

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
            picked = await articles_for_origin(_db(), "s", db_user.lang)
            if not picked:
                await ack(query)
                await _load_if_empty(message, db_user)
                picked = await articles_for_origin(_db(), "s", db_user.lang)
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
        items = await articles_for_origin(_db(), origin, db_user.lang)
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

    if action == PAY:
        await ack(query)
        try:
            await message.answer_invoice(
                title=t(db_user.lang, "plus_invoice_title")[:32],
                description=t(db_user.lang, "plus_invoice_desc")[:255],
                payload="plus30",
                currency="XTR",
                # Для Telegram Stars amount — число звёзд, не копейки.
                prices=[LabeledPrice(label="Plus", amount=config.PLUS_STARS)],
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
    ok = (
        query.invoice_payload == "plus30"
        and query.currency == "XTR"
        and query.total_amount >= config.PLUS_STARS
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

    startup = asyncio.create_task(startup_sync())
    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    router.message.middleware(UserMiddleware())
    router.callback_query.middleware(UserMiddleware())
    dp.include_router(router)
    await _configure_bot(bot)

    scheduler = AsyncIOScheduler(timezone=timezone.utc)

    async def refresh_job() -> None:
        try:
            await refresh_catalog(database)
        except Exception:
            log.exception("scheduled refresh failed")

    async def digest_job() -> None:
        try:
            await send_digests(bot, database)
        except Exception:
            log.exception("digest job failed")

    scheduler.add_job(
        refresh_job,
        "interval",
        minutes=config.RSS_REFRESH_MINUTES,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=300,
        next_run_time=datetime.now(timezone.utc) + timedelta(minutes=config.RSS_REFRESH_MINUTES),
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
    log.info("Market News is up, articles=%s", await database.count_articles())
    loop = asyncio.get_running_loop()

    def on_sigint(signum, frame):
        # На Windows aiogram не ставит обработчик Ctrl+C, и asyncio отменяет весь цикл.
        # Останавливаем только polling, чтобы выход был без traceback.
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        if dp._stop_signal is None or not dp._running_lock.locked():
            raise KeyboardInterrupt
        log.info("Stopping Market News")
        loop.call_soon_threadsafe(dp._signal_stop_polling, signal.SIGINT)

    signal.signal(signal.SIGINT, on_sigint)
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot, handle_signals=False)
    finally:
        log.info("Market News stopped")
        scheduler.shutdown(wait=False)
        startup.cancel()
        try:
            await startup
        except asyncio.CancelledError:
            pass
        await database.close()


def main() -> None:
    if not config.BOT_TOKEN:
        print("Нет токена. Создайте файл .env и укажите BOT_TOKEN. Образец — .env.example")
        raise SystemExit(1)
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("Market News stopped")


if __name__ == "__main__":
    main()
