"""Премиальные обложки разделов меню.

Файлы намеренно не содержат текста: один набор подходит для русского,
английского и арабского интерфейса.
"""

from __future__ import annotations

from pathlib import Path
from io import BytesIO
import asyncio

from aiogram import Bot
from PIL import Image, ImageOps

from images import upload_photo


MENU_COVERS_DIR = Path(__file__).resolve().parent / "assets" / "menu"

MENU_COVERS = {
    "how_it_works": MENU_COVERS_DIR / "how_it_works.png",
    "digest": MENU_COVERS_DIR / "digest.png",
    "analytics": MENU_COVERS_DIR / "analytics.png",
    "latest": MENU_COVERS_DIR / "latest.png",
    "categories": MENU_COVERS_DIR / "categories.png",
    "story": MENU_COVERS_DIR / "story.png",
    "subscription": MENU_COVERS_DIR / "subscription.png",
    "feed": MENU_COVERS_DIR / "feed.png",
    "settings": MENU_COVERS_DIR / "settings.png",
    "help": MENU_COVERS_DIR / "help.png",
}

_IDS: dict[str, str] = {}
_LOCK = asyncio.Lock()


def menu_cover(name: str) -> Path:
    """Return a generated menu cover path and fail early on packaging errors."""
    try:
        path = MENU_COVERS[name]
    except KeyError as exc:
        raise KeyError(f"Unknown menu cover: {name}") from exc
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


async def preload_menu_covers(bot: Bot) -> int:
    """Upload local covers once and keep Telegram file IDs in memory."""
    async with _LOCK:
        for name, path in MENU_COVERS.items():
            if name in _IDS:
                continue
            image = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
            image.thumbnail((1280, 1280))
            payload = BytesIO()
            image.save(payload, format="JPEG", quality=88, optimize=True)
            file_id = await upload_photo(bot, payload.getvalue())
            if file_id:
                _IDS[name] = file_id
    return len(_IDS)


def menu_cover_id(name: str) -> str | None:
    return _IDS.get(name)
