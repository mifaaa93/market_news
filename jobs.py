"""Опрос GNews: топ 4 раза в сутки, поиск постоянно, рассылка по выбранным источникам."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import aiohttp
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter

import config
from content import digest_due, render_digest, safe_zone, source_hash
from db import Database, utc_now, utc_now_iso
from gnews import UA, fetch_lang, mark_origin, parse_articles, requests_per_cycle
from keyboards import digest_keyboard, push_keyboard
from images import cache_pending_photos
from translate import translate_pending
from ui import deliver

log = logging.getLogger(__name__)
_REFRESH_LOCK = asyncio.Lock()


def top_quota_reserve(now: datetime | None = None, last_top_at: str | None = None) -> int:
    moment = now or utc_now()
    pending = 0
    last: datetime | None = None
    if last_top_at:
        try:
            last = datetime.strptime(last_top_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            last = None
    for hour in config.GNEWS_TOP_HOURS:
        if hour > moment.hour:
            pending += 1
        elif hour == moment.hour:
            already = (
                last is not None
                and last.date() == moment.date()
                and last.hour == moment.hour
            )
            if not already:
                pending += 1
    return pending * requests_per_cycle()


async def refresh_catalog(database: Database, bot: Bot | None = None) -> int:
    if _REFRESH_LOCK.locked():
        log.info("catalog refresh skipped: another refresh is still running")
        return 0
    async with _REFRESH_LOCK:
        saved = await poll_gnews(database, "top")
        saved += await poll_gnews(database, "search")
        if saved:
            log.info("catalog refresh saved=%s", saved)
        return saved


async def refresh_top(database: Database, bot: Bot | None = None) -> int:
    if _REFRESH_LOCK.locked():
        log.info("top refresh skipped: another refresh is still running")
        return 0
    async with _REFRESH_LOCK:
        saved = await poll_gnews(database, "top")
        if saved:
            log.info("top refresh saved=%s", saved)
        return saved


async def refresh_search(database: Database, bot: Bot | None = None) -> int:
    if _REFRESH_LOCK.locked():
        log.info("search refresh skipped: another refresh is still running")
        return 0
    async with _REFRESH_LOCK:
        saved = await poll_gnews(database, "search")
        if saved:
            log.info("search refresh saved=%s", saved)
        return saved


async def translation_worker(database: Database, bot: Bot | None = None) -> int:
    sent = await push_new_articles(database, bot)
    photos = await cache_pending_photos(database, bot, limit=config.IMAGE_BATCH_LIMIT)
    translated = 0
    if config.CVC_API_KEY:
        translated = await translate_pending(database, limit=config.TRANSLATION_BATCH_LIMIT)
    sent += await push_new_articles(database, bot)
    if translated or sent or photos:
        log.info(
            "translation worker: translated=%s pushed=%s photos=%s",
            translated,
            sent,
            photos,
        )
    return translated


async def poll_gnews(database: Database, kind: str) -> int:
    if not config.GNEWS_API_KEY:
        log.warning("GNEWS_API_KEY is empty, skip poll")
        return 0
    pages = config.GNEWS_SEARCH_PAGES if kind == "search" else 1
    needed = pages * requests_per_cycle()
    remaining = await database.quota_remaining()
    if kind == "search":
        floor = top_quota_reserve(utc_now(), await database.meta_get("fetched_top_at"))
        if remaining - floor < needed:
            log.info(
                "gnews search skipped remaining=%s reserve_top=%s needed=%s",
                remaining,
                floor,
                needed,
            )
            return 0
    elif remaining < needed:
        log.info("gnews top skipped remaining=%s needed=%s", remaining, needed)
        return 0
    timeout = aiohttp.ClientTimeout(total=30)
    headers = {"User-Agent": UA, "Accept": "application/json"}
    saved = 0
    used = 0
    since = None
    if kind == "search":
        since = (
            datetime.now(timezone.utc) - timedelta(hours=24)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        stop = False
        for lang in config.GNEWS_LANGS:
            if stop:
                break
            for page in range(1, pages + 1):
                if not await database.quota_consume(1):
                    log.info("gnews quota exhausted after %s calls", used)
                    stop = True
                    break
                used += 1
                if used > 1:
                    await asyncio.sleep(1.1)
                payload = await fetch_lang(
                    session, lang, kind=kind, page=page, since=since
                )
                if payload is None:
                    continue
                items = mark_origin(
                    parse_articles(payload, lang),
                    kind,
                    ranked=(kind == "top"),
                )
                batch = 0
                if kind == "top":
                    batch = await database.replace_top(lang, items)
                else:
                    batch = await database.ingest_articles(items)
                saved += batch
                log.info(
                    "gnews %s lang=%s page=%s total=%s parsed=%s saved=%s",
                    kind,
                    lang,
                    page,
                    payload.get("totalArticles"),
                    len(items),
                    batch,
                )
    if saved or used:
        key = "fetched_top_at" if kind == "top" else "fetched_at"
        await database.meta_set(key, utc_now_iso())
        removed = await database.delete_old(config.ARTICLE_KEEP_DAYS)
        await database.seed_missing_feeds()
        log.info(
            "gnews %s used=%s remaining=%s saved=%s pruned=%s",
            kind,
            used,
            await database.quota_remaining(),
            saved,
            removed,
        )
    return saved


async def push_new_articles(database: Database, bot: Bot | None = None) -> int:
    if bot is None:
        return 0
    cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=config.PUSH_FRESH_MINUTES)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    articles = await database.articles_since(cutoff)
    sent = 0
    per_user: dict[int, int] = {}
    for article in articles:
        for user in await database.list_push_subscribers(article):
            if not user.notifications:
                continue
            if per_user.get(user.user_id, 0) >= config.PUSH_PER_USER_PER_CYCLE:
                continue
            if await database.push_already_sent(user.user_id, article.id):
                continue
            if config.CVC_API_KEY and user.lang in config.TRANSLATION_LANGS:
                hashes = await database.translation_hashes(user.lang, [article.id])
                if hashes.get(article.id) != source_hash(article):
                    continue
            shown = await database.apply_translations([article], user.lang)
            if not shown:
                continue
            item = shown[0]
            text = (
                f"<b>{item.title}</b>\n\n"
                f"{item.source_name}\n"
                f"{item.summary}"
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
        log.info("sent %s story notifications (up to %s per user)", sent, config.PUSH_PER_USER_PER_CYCLE)
    return sent


async def send_digests(bot: Bot, database: Database) -> int:
    now = datetime.now(timezone.utc)
    users = [user for user in await database.list_digest_subscribers() if digest_due(user, now)]
    if not users:
        return 0
    sent = 0
    cache: dict[str, list] = {}
    for user in users:
        picked = cache.get(user.lang)
        if picked is None:
            picked = await database.list_top(user.lang, 10)
            cache[user.lang] = picked
        if len(picked) < 3:
            continue
        updated = await database.meta_get("fetched_top_at")
        text = render_digest(picked, user.lang, user.timezone, updated, mailed=True)
        markup = digest_keyboard(user.lang, picked)
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
