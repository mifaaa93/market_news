"""Качаем обложки браузерным TLS (curl_cffi) и кладём file_id в Telegram."""

from __future__ import annotations

import asyncio
import logging
from io import BytesIO
from urllib.parse import urlsplit

from aiogram import Bot
from aiogram.types import BufferedInputFile
from PIL import Image, ImageOps, UnidentifiedImageError

import config
from db import Database

log = logging.getLogger(__name__)
_LOCK = asyncio.Lock()

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
_MAX_BYTES = 4_000_000
_MAX_SIDE = 1280


def to_jpeg(data: bytes) -> bytes | None:
    try:
        image = Image.open(BytesIO(data))
        image = ImageOps.exif_transpose(image)
        if image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
        elif image.mode == "L":
            image = image.convert("RGB")
        image.thumbnail((_MAX_SIDE, _MAX_SIDE))
        out = BytesIO()
        image.save(out, format="JPEG", quality=85, optimize=True)
        payload = out.getvalue()
    except (UnidentifiedImageError, OSError, ValueError):
        return None
    if not payload or len(payload) > _MAX_BYTES:
        return None
    return payload


def _referer(url: str) -> str:
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return url
    return f"{parts.scheme}://{parts.netloc}/"


async def download_image(url: str) -> bytes | None:
    if not url.startswith("http"):
        return None
    headers = {
        "User-Agent": _UA,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": _referer(url),
    }
    try:
        from curl_cffi.requests import AsyncSession

        async with AsyncSession(impersonate="chrome") as session:
            response = await session.get(url, headers=headers, timeout=20, allow_redirects=True)
            if response.status_code != 200:
                log.info("image http %s %s", response.status_code, url[:80])
                return None
            data = response.content or b""
    except Exception:
        log.info("image download failed %s", url[:80], exc_info=True)
        return None
    if len(data) < 64 or len(data) > 8_000_000:
        return None
    return to_jpeg(data)


async def upload_photo(bot: Bot, jpeg: bytes) -> str | None:
    chat_id = config.IMAGE_CACHE_CHAT_ID
    message = await bot.send_photo(
        chat_id,
        BufferedInputFile(jpeg, filename="cover.jpg"),
        disable_notification=True,
    )
    photos = message.photo or []
    file_id = photos[-1].file_id if photos else None
    try:
        await bot.delete_message(chat_id, message.message_id)
    except Exception:
        log.info("could not delete cache photo %s", message.message_id)
    return file_id


async def cache_pending_photos(database: Database, bot: Bot | None, *, limit: int = 4) -> int:
    if bot is None:
        return 0
    async with _LOCK:
        items = await database.articles_missing_photo(limit)
        done = 0
        for article in items:
            jpeg = await download_image(article.image_url)
            if jpeg is None:
                await database.save_photo_id(article.id, "")
                continue
            try:
                file_id = await upload_photo(bot, jpeg)
            except Exception:
                log.exception("telegram photo upload failed article=%s", article.id)
                await database.save_photo_id(article.id, "")
                continue
            if not file_id:
                await database.save_photo_id(article.id, "")
                continue
            await database.save_photo_id(article.id, file_id)
            done += 1
        if done:
            log.info("cached %s telegram photos", done)
        return done
