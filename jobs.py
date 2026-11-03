"""Фоновое обновление ленты и утренняя рассылка без внешних ссылок."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter

import config
from content import digest_due, pick_digest, render_digest, safe_zone, source_hash, with_summary
from db import Database
from feeds import refresh_all, refresh_custom_sources
from fulltext import fill_full_texts
from keyboards import digest_keyboard, push_keyboard
from translate import translate_pending
from ui import deliver

log = logging.getLogger(__name__)
_REFRESH_LOCK = asyncio.Lock()


async def refresh_catalog(database: Database, bot: Bot | None = None) -> None:
    """Ленты, полные тексты и переводы. Экран читает только то, что уже в базе."""
    if _REFRESH_LOCK.locked():
        log.info("catalog refresh skipped: another refresh is still running")
        return
    await _REFRESH_LOCK.acquire()
    try:
        await refresh_all(database)
        await refresh_custom_sources(database, only_plan="plus")
        await fill_full_texts(database)
    finally:
        _REFRESH_LOCK.release()


async def refresh_pro(database: Database, bot: Bot | None = None) -> None:
    if _REFRESH_LOCK.locked():
        log.info("pro refresh skipped: another refresh is still running")
        return
    await _REFRESH_LOCK.acquire()
    try:
        keys = await database.paid_catalog_keys("pro")
        if keys:
            await refresh_all(database, feed_keys=keys)
        await refresh_custom_sources(database, only_plan="pro")
        await fill_full_texts(database)
    finally:
        _REFRESH_LOCK.release()


async def translation_worker(database: Database, bot: Bot | None = None) -> int:
    """Translate ready full-text articles, then deliver their individual pushes."""
    translated = 0
    if config.CVC_API_KEY:
        translated = await translate_pending(
            database,
            limit=config.TRANSLATION_BATCH_LIMIT,
            full_only=True,
        )
    sent = await push_new_articles(database, bot)
    if translated or sent:
        log.info("translation worker: translated=%s pushed=%s", translated, sent)
    return translated


async def push_new_articles(database: Database, bot: Bot | None = None) -> int:
    """Send recent full-text stories without dumping a translation backlog into chat."""
    if bot is None:
        return 0
    stamp = await database.meta_get("push_checked_at")
    if stamp is None:
        await database.meta_set(
            "push_checked_at",
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        return 0
    cutoff = (datetime.now(timezone.utc) - timedelta(
        minutes=config.PUSH_FRESH_MINUTES
    )).strftime("%Y-%m-%dT%H:%M:%SZ")
    # The saved stamp is the first launch of push delivery. Afterwards use a
    # rolling time window: unprocessed articles stay retryable until they age out.
    articles = await database.articles_since(max(stamp, cutoff))
    sent = 0
    per_user: dict[int, int] = {}
    for article in articles:
        for user in await database.list_push_subscribers(article):
            if per_user.get(user.user_id, 0) >= config.PUSH_PER_USER_PER_CYCLE:
                continue
            if await database.push_already_sent(user.user_id, article.id):
                continue
            if config.CVC_API_KEY and user.lang in config.TRANSLATION_LANGS:
                hashes = await database.translation_hashes(user.lang, [article.id])
                if hashes.get(article.id) != source_hash(article):
                    continue
            translated = (await database.apply_translations([article], user.lang))[0]
            text = (
                f"<b>{translated.title}</b>\n\n"
                f"{translated.source_name}\n"
                f"{translated.summary}"
            )
            try:
                await deliver(bot, user.user_id, text, push_keyboard(user.lang, article.id))
                await database.mark_push_sent(user.user_id, article.id)
                per_user[user.user_id] = per_user.get(user.user_id, 0) + 1
                sent += 1
            except TelegramForbiddenError:
                await database.set_blocked(user.user_id, True)
            except Exception:
                log.exception("push to %s failed", user.user_id)
    if sent:
        log.info("sent %s individual story notifications (up to %s per user)", sent, config.PUSH_PER_USER_PER_CYCLE)
    return sent


async def send_digests(bot: Bot, database: Database) -> int:
    now = datetime.now(timezone.utc)
    users = [user for user in await database.list_digest_subscribers() if digest_due(user, now)]
    if not users:
        return 0
    sent = 0
    for user in users:
        picked = pick_digest(
            with_summary(await database.recent_for_user(user.user_id, 60, full_only=True)),
            7,
        )
        if len(picked) < 3:
            continue
        updated = await database.meta_get("fetched_at")
        items = await database.apply_translations(picked, user.lang)
        text = render_digest(items, user.lang, user.timezone, updated, mailed=True)
        markup = digest_keyboard(user.lang, items)
        try:
            await deliver(bot, user.user_id, text, markup)
            local_day = now.astimezone(safe_zone(user.timezone)).date().isoformat()
            await database.mark_digest_sent(user.user_id, local_day)
            sent += 1
        except TelegramForbiddenError:
            log.info("user %s blocked the bot", user.user_id)
            await database.set_blocked(user.user_id, True)
        except TelegramRetryAfter as exc:
            log.warning("telegram asked to wait %s seconds", exc.retry_after)
            break
        except TelegramBadRequest as exc:
            lowered = str(exc).lower()
            log.warning("digest to %s failed: %s", user.user_id, exc)
            if "chat not found" in lowered or "deactivated" in lowered:
                await database.set_blocked(user.user_id, True)
        except Exception:
            log.exception("digest to %s failed", user.user_id)
        await asyncio.sleep(0.05)
    log.info("digest sent %s", sent)
    return sent
