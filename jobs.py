"""Фоновое обновление ленты и утренняя рассылка без внешних ссылок."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter

import config
from content import digest_due, pick_digest, render_digest, safe_zone, with_summary
from db import Database
from feeds import refresh_all
from fulltext import fill_full_texts
from keyboards import digest_keyboard
from translate import translate_pending
from ui import deliver

log = logging.getLogger(__name__)


async def refresh_catalog(database: Database) -> None:
    """Ленты, полные тексты и переводы. Экран читает только то, что уже в базе."""
    await refresh_all(database)
    await fill_full_texts(database)
    if not config.CVC_API_KEY:
        log.info("CVC_API_KEY is empty, stories stay in the source language")
        return
    for _ in range(40):
        done = await translate_pending(database, limit=25)
        if done == 0:
            break


async def send_digests(bot: Bot, database: Database) -> int:
    now = datetime.now(timezone.utc)
    users = [user for user in await database.list_digest_subscribers() if digest_due(user, now)]
    if not users:
        return 0
    picked = pick_digest(with_summary(await database.recent(60, full_only=True)), 7)
    if len(picked) < 3:
        log.info("digest skipped, stories=%s", len(picked))
        return 0
    updated = await database.meta_get("fetched_at")
    sent = 0
    for user in users:
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
