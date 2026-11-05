"""Отправка Rich Message. Картинки встроены в материал, превью чужих ссылок нет."""

from __future__ import annotations

import html
import logging
import re
from html.parser import HTMLParser

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputRichMessage,
    InputRichMessageMedia,
    Message,
)

from content import fit

log = logging.getLogger(__name__)

_BLOCK = re.compile(r"<(h1|h2|h3|p|figure|footer|ul|tg-collage|hr)\b", re.IGNORECASE)
_FIGURE = re.compile(r"<figure\b.*?</figure>", re.IGNORECASE | re.DOTALL)
_COLLAGE = re.compile(r"<tg-collage\b.*?</tg-collage>", re.IGNORECASE | re.DOTALL)
_IMG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_TAGS = re.compile(r"<[^>]+>")
_RICH_TAGS = {
    "b",
    "br",
    "cite",
    "em",
    "figcaption",
    "figure",
    "footer",
    "h1",
    "h2",
    "h3",
    "i",
    "img",
    "li",
    "p",
    "strong",
    "tg-collage",
    "ul",
}
_VOID_RICH_TAGS = {"br", "img"}
_SAFE_PHOTO_SRC = "tg://photo?id=cover"


class _RichHTMLSanitizer(HTMLParser):
    """Keep only the small Rich Message HTML subset used by the bot.

    Renderers escape dynamic article data themselves. This second boundary is
    intentional: it protects the Telegram payload even if a future screen
    passes raw text containing markup-looking characters.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(html.escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.parts.append(f"&#{name};")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag not in _RICH_TAGS:
            self.parts.append(html.escape(self.get_starttag_text() or "", quote=False))
            return
        if tag == "img":
            src = next(
                (
                    value
                    for name, value in attrs
                    if name.lower() == "src" and value == _SAFE_PHOTO_SRC
                ),
                None,
            )
            if src:
                self.parts.append(f'<img src="{_SAFE_PHOTO_SRC}"/>')
            return
        self.parts.append(f"<{tag}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _RICH_TAGS and tag not in _VOID_RICH_TAGS:
            self.parts.append(f"</{tag}>")
        elif tag not in _RICH_TAGS:
            self.parts.append(html.escape(f"</{tag}>", quote=False))

    def handle_comment(self, data: str) -> None:
        self.parts.append(html.escape(f"<!--{data}-->", quote=False))

    def handle_decl(self, decl: str) -> None:
        self.parts.append(html.escape(f"<!{decl}>", quote=False))

    def handle_pi(self, data: str) -> None:
        self.parts.append(html.escape(f"<?{data}>", quote=False))


def sanitize_rich_html(text: str) -> str:
    parser = _RichHTMLSanitizer()
    parser.feed(text or "")
    parser.close()
    return "".join(parser.parts)


def as_rich_html(text: str) -> str:
    payload = fit(text).strip()
    if _BLOCK.search(payload):
        return sanitize_rich_html(payload)
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", payload) if chunk.strip()]
    if not chunks:
        return "<p></p>"
    parts = []
    for chunk in chunks:
        inner = "<br/>".join(line.strip() for line in chunk.splitlines() if line.strip())
        parts.append(f"<p>{inner}</p>")
    return sanitize_rich_html("".join(parts))


def without_images(text: str) -> str:
    cleaned = _COLLAGE.sub("", text)
    cleaned = _FIGURE.sub("", cleaned)
    return _IMG.sub("", cleaned)


_ARABIC = re.compile(r"[\u0600-\u06FF]")


def _photo_id(value: str | None) -> str | None:
    token = (value or "").strip()
    return token if len(token) > 10 else None


def rich_message(text: str, photo_id: str | None = None) -> InputRichMessage:
    html_text = as_rich_html(text)
    file_id = _photo_id(photo_id)
    if file_id and "tg://photo?id=cover" not in html_text:
        html_text = '<figure><img src="tg://photo?id=cover"/></figure>' + html_text
    if not file_id:
        html_text = without_images(html_text)
        return InputRichMessage(
            html=html_text,
            skip_entity_detection=True,
            is_rtl=True if _ARABIC.search(html_text) else None,
        )
    return InputRichMessage(
        html=html_text,
        skip_entity_detection=True,
        is_rtl=True if _ARABIC.search(html_text) else None,
        media=[InputRichMessageMedia(id="cover", media=InputMediaPhoto(media=file_id))],
    )


async def ack(query, text: str | None = None) -> None:
    try:
        if text:
            await query.answer(text[:200])
        else:
            await query.answer()
    except TelegramBadRequest:
        return


async def deliver(
    bot: Bot,
    chat_id: int,
    text: str,
    markup: InlineKeyboardMarkup | None,
    photo_id: str | None = None,
) -> Message:
    payload = as_rich_html(text)
    try:
        return await bot.send_rich_message(
            chat_id, rich_message(payload, photo_id), reply_markup=markup
        )
    except TelegramBadRequest:
        if not _photo_id(photo_id) and "<img" not in payload.lower():
            raise
        log.info("rich message image was rejected, sending the story without it")
        return await bot.send_rich_message(
            chat_id, rich_message(without_images(payload)), reply_markup=markup
        )


async def show_message(
    message: Message,
    text: str,
    markup: InlineKeyboardMarkup | None,
    photo_id: str | None = None,
) -> Message | None:
    try:
        return await deliver(message.bot, message.chat.id, text, markup, photo_id)
    except TelegramBadRequest:
        log.exception("rich message was rejected")
        plain = html.escape(_TAGS.sub("", as_rich_html(text)))
        return await message.answer(plain, reply_markup=markup)


async def show_edit(
    message: Message,
    text: str,
    markup: InlineKeyboardMarkup | None,
    photo_id: str | None = None,
) -> None:
    payload = as_rich_html(text)

    async def edit(body: str, file_id: str | None) -> None:
        await message.edit_text(
            rich_message=rich_message(body, file_id),
            reply_markup=markup,
            parse_mode=None,
            link_preview_options=None,
        )

    try:
        await edit(payload, photo_id)
    except TelegramBadRequest as exc:
        lowered = str(exc).lower()
        if "message is not modified" in lowered:
            return
        if _photo_id(photo_id) or "<img" in payload.lower():
            try:
                await edit(without_images(payload), None)
                return
            except TelegramBadRequest as second:
                if "message is not modified" in str(second).lower():
                    return
                log.info("rich edit failed: %s", second)
                return
        log.info("rich edit failed: %s", exc)
