"""Отправка Rich Message. Картинки встроены в материал, превью чужих ссылок нет."""

from __future__ import annotations

import html
import logging
import re

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InputRichMessage, Message

from content import fit

log = logging.getLogger(__name__)

_BLOCK = re.compile(r"<(h1|h2|h3|p|figure|footer|ul|tg-collage|hr)\b", re.IGNORECASE)
_FIGURE = re.compile(r"<figure\b.*?</figure>", re.IGNORECASE | re.DOTALL)
_COLLAGE = re.compile(r"<tg-collage\b.*?</tg-collage>", re.IGNORECASE | re.DOTALL)
_IMG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_TAGS = re.compile(r"<[^>]+>")


def as_rich_html(text: str) -> str:
    payload = fit(text).strip()
    if _BLOCK.search(payload):
        return payload
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", payload) if chunk.strip()]
    if not chunks:
        return "<p></p>"
    parts = []
    for chunk in chunks:
        inner = "<br/>".join(line.strip() for line in chunk.splitlines() if line.strip())
        parts.append(f"<p>{inner}</p>")
    return "".join(parts)


def without_images(text: str) -> str:
    cleaned = _COLLAGE.sub("", text)
    cleaned = _FIGURE.sub("", cleaned)
    return _IMG.sub("", cleaned)


_ARABIC = re.compile(r"[\u0600-\u06FF]")


def rich_message(text: str) -> InputRichMessage:
    html_text = as_rich_html(text)
    return InputRichMessage(
        html=html_text,
        skip_entity_detection=True,
        is_rtl=True if _ARABIC.search(html_text) else None,
    )


async def ack(query, text: str | None = None) -> None:
    try:
        if text:
            await query.answer(text[:200])
        else:
            await query.answer()
    except TelegramBadRequest:
        return


async def deliver(bot: Bot, chat_id: int, text: str, markup: InlineKeyboardMarkup | None) -> Message:
    payload = as_rich_html(text)
    try:
        return await bot.send_rich_message(chat_id, rich_message(payload), reply_markup=markup)
    except TelegramBadRequest:
        if "<img" not in payload.lower():
            raise
        log.info("rich message image was rejected, sending the story without it")
        return await bot.send_rich_message(chat_id, rich_message(without_images(payload)), reply_markup=markup)


async def show_message(message: Message, text: str, markup: InlineKeyboardMarkup | None) -> Message | None:
    try:
        return await deliver(message.bot, message.chat.id, text, markup)
    except TelegramBadRequest:
        log.exception("rich message was rejected")
        plain = html.escape(_TAGS.sub("", as_rich_html(text)))
        return await message.answer(plain, reply_markup=markup)


async def show_edit(message: Message, text: str, markup: InlineKeyboardMarkup | None) -> None:
    payload = as_rich_html(text)

    async def edit(body: str) -> None:
        await message.edit_text(
            rich_message=rich_message(body),
            reply_markup=markup,
            parse_mode=None,
            link_preview_options=None,
        )

    try:
        await edit(payload)
    except TelegramBadRequest as exc:
        lowered = str(exc).lower()
        if "message is not modified" in lowered:
            return
        if "<img" in payload.lower():
            try:
                await edit(without_images(payload))
                return
            except TelegramBadRequest as second:
                if "message is not modified" in str(second).lower():
                    return
                log.info("rich edit failed, sending a new message: %s", second)
        else:
            log.info("rich edit failed, sending a new message: %s", exc)
        await show_message(message, without_images(payload), markup)
