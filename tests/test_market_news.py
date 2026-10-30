"""Поведение бота без Telegram: тексты, гейт ссылок, лента, база."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from content import (
    classify,
    clean_image_url,
    clean_text,
    clean_url,
    digest_due,
    is_public_article_url,
    links_allowed,
    pick_digest,
    with_summary,
    render_analytics,
    render_article,
    render_digest,
    render_full,
    render_help,
    render_home,
    render_plus,
    render_settings,
    render_sources,
    resolve_category,
    title_norm,
)
from db import Database
from feeds import Feed, parse_feed, prepare_items
from fulltext import extract_text, is_full_text
from keyboards import (
    Act,
    analytics_keyboard,
    article_keyboard,
    digest_keyboard,
    full_keyboard,
    help_keyboard,
    home_keyboard,
    plus_keyboard,
    settings_keyboard,
    sources_keyboard,
)
from models import Article, User
from screens import full_screen, home_screen
from texts import ABOUT_AR, ABOUT_EN, ABOUT_RU, COMMANDS, SHORT_AR, SHORT_EN, SHORT_RU, STRINGS, lang_label, t
from config import _model_chain
from translate import _rows_from_content, parse_translation_payload
from ui import as_rich_html, without_images

_FIXTURE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Test</title>
<item>
<title>Oil prices rise as OPEC meets in Vienna</title>
<link>https://www.bbc.co.uk/news/business/oil-1?at_medium=RSS&amp;at_campaign=rss</link>
<guid>oil-1</guid>
<pubDate>Thu, 30 Oct 2025 12:00:00 GMT</pubDate>
<description><![CDATA[<img src="https://ichef.bbci.co.uk/news/1024/oil.jpg"/> Brent moved higher after the meeting. <a href="https://www.bbc.co.uk/x">Read more</a>]]></description>
</item>
<item>
<title>Bitcoin slides after a sharp weekend selloff</title>
<link>https://bit.ly/evil</link>
<guid>btc-1</guid>
<pubDate>Thu, 30 Oct 2025 11:00:00 GMT</pubDate>
<description>Traders sold bitcoin. Visit https://t.me/scam for more.</description>
</item>
<item>
<title>Nasdaq falls on weak earnings season</title>
<link>https://www.cnbc.com/2025/10/30/nasdaq.html</link>
<guid>st-1</guid>
<pubDate>Thu, 30 Oct 2025 10:00:00 GMT</pubDate>
<description>Tech shares led the decline across the session.</description>
</item>
</channel>
</rss>
"""


def _article(**kwargs) -> Article:
    title = kwargs.get("title", "Oil prices rise as OPEC meets in Vienna")
    data = {
        "id": 1,
        "guid": "g1",
        "source_key": "bbc",
        "source_name": "BBC Business",
        "title": title,
        "title_norm": title_norm(title),
        "summary": "Brent moved higher after ministers met and left the supply plan unchanged.",
        "body": (
            "Brent moved higher after ministers met and left the supply plan unchanged. "
            "Traders waited for the written statement before the next session."
        ),
        "url": "https://www.bbc.co.uk/news/business/oil-1",
        "category": "oil",
        "published_at": "2026-10-30T12:00:00Z",
        "fetched_at": "2026-10-30T12:05:00Z",
    }
    data.update(kwargs)
    if "title" in kwargs and "title_norm" not in kwargs:
        data["title_norm"] = title_norm(kwargs["title"])
    return Article(**data)


def _user(**kwargs) -> User:
    data = {
        "user_id": 1,
        "lang": "ru",
        "notifications": True,
        "digest_hour": 9,
        "timezone": "Europe/Moscow",
        "interactions": 0,
        "full_reads": 0,
        "premium_until": None,
        "last_digest_on": None,
        "blocked": False,
    }
    data.update(kwargs)
    return User(**data)


def _urls(markup) -> list[str]:
    found = []
    for row in markup.inline_keyboard:
        for button in row:
            if button.url:
                found.append(button.url)
    return found


def _actions(markup) -> list[str]:
    found = []
    for row in markup.inline_keyboard:
        for button in row:
            if button.callback_data:
                found.append(Act.unpack(button.callback_data).a)
                assert len(button.callback_data.encode("utf-8")) <= 64
            assert button.text
            assert len(button.text) <= 64
            assert "\n" not in button.text
    return found


def _no_link(text: str) -> None:
    lowered = text.lower()
    for token in ("http://", "https://", "t.me/", "bit.ly", "://"):
        assert token not in lowered, text


class ContentTests(unittest.TestCase):
    def test_locales_and_limits(self) -> None:
        self.assertEqual(set(STRINGS["ru"]), set(STRINGS["en"]))
        self.assertEqual(set(STRINGS["ru"]), set(STRINGS["ar"]))
        self.assertLessEqual(len(SHORT_RU), 120)
        self.assertLessEqual(len(SHORT_EN), 120)
        self.assertLessEqual(len(SHORT_AR), 120)
        self.assertLessEqual(len(ABOUT_RU), 512)
        self.assertLessEqual(len(ABOUT_EN), 512)
        self.assertLessEqual(len(ABOUT_AR), 512)
        self.assertLessEqual(len(t("ru", "plus_invoice_title")), 32)
        self.assertLessEqual(len(t("ar", "plus_invoice_title")), 32)
        self.assertLessEqual(len(t("en", "plus_invoice_desc")), 255)
        self.assertLessEqual(len(t("ru", "plus_invoice_desc")), 255)
        self.assertLessEqual(len(t("ar", "plus_invoice_desc")), 255)
        self.assertIn("العربية", lang_label("ar"))

    def test_clean_text_strips_links(self) -> None:
        raw = 'Brent moved higher. <a href="https://bit.ly/x">Read more</a> https://t.me/scam'
        cleaned = clean_text(raw)
        self.assertNotIn("http", cleaned)
        self.assertNotIn("t.me", cleaned)
        self.assertNotIn("Read more", cleaned)
        self.assertIn("Brent moved higher", cleaned)

    def test_classify(self) -> None:
        self.assertEqual(classify("Oil prices rise as OPEC meets"), "oil")
        self.assertEqual(classify("Bitcoin slides after ETF outflows"), "crypto")
        self.assertEqual(classify("Federal Reserve holds interest rates"), "macro")
        self.assertEqual(classify("Nasdaq falls on weak earnings"), "stocks")
        self.assertEqual(classify("Company updates its mobile app"), "markets")
        self.assertEqual(resolve_category("Company updates its mobile app", "crypto"), "crypto")

    def test_urls(self) -> None:
        self.assertTrue(is_public_article_url("https://www.bbc.co.uk/news/business/1"))
        self.assertTrue(is_public_article_url("https://www.cnbc.com/finance/"))
        self.assertFalse(is_public_article_url("https://bit.ly/abc"))
        self.assertFalse(is_public_article_url("https://t.me/channel"))
        self.assertFalse(is_public_article_url("https://evil.example/news"))
        self.assertFalse(is_public_article_url(""))
        cleaned = clean_url("https://www.bbc.co.uk/news/business/oil-1?at_medium=RSS&at_campaign=rss")
        self.assertEqual(cleaned, "https://www.bbc.co.uk/news/business/oil-1")
        self.assertEqual(clean_url("https://bit.ly/abc"), "")
        picture = "https://ichef.bbci.co.uk/news/1024/branded_news/oil.jpg"
        self.assertEqual(clean_image_url(picture), picture)
        self.assertEqual(clean_image_url("https://bit.ly/pic.jpg"), "")
        self.assertEqual(clean_image_url("https://www.bbc.co.uk/news/business/oil-1"), "")

    def test_links_gate(self) -> None:
        self.assertFalse(links_allowed(4, 3, 10))
        self.assertFalse(links_allowed(5, 2, 10))
        self.assertTrue(links_allowed(5, 3, 10))
        self.assertTrue(links_allowed(5, 2, 2))
        self.assertFalse(links_allowed(5, 1, 2))
        self.assertFalse(links_allowed(9, 3, 0))

    def test_pick_digest_mixes_topics(self) -> None:
        items = [
            _article(id=1, category="stocks", published_at="2026-10-30T12:00:00Z", title="Nasdaq falls on weak earnings season"),
            _article(id=2, category="stocks", published_at="2026-10-30T11:00:00Z", title="Dow slips as bank shares retreat fast"),
            _article(id=3, category="oil", published_at="2026-10-30T09:00:00Z", title="Oil prices rise as OPEC meets in Vienna"),
        ]
        picked = pick_digest(items, 2)
        self.assertEqual({item.category for item in picked}, {"stocks", "oil"})

    def test_digest_window(self) -> None:
        morning = _user()
        self.assertTrue(digest_due(morning, datetime(2026, 10, 30, 6, 30, tzinfo=timezone.utc)))
        self.assertFalse(digest_due(morning, datetime(2026, 10, 30, 5, 0, tzinfo=timezone.utc)))
        self.assertTrue(digest_due(morning, datetime(2026, 10, 30, 7, 30, tzinfo=timezone.utc)))
        self.assertFalse(digest_due(morning, datetime(2026, 10, 30, 8, 30, tzinfo=timezone.utc)))
        sent = _user(last_digest_on="2026-10-30")
        self.assertFalse(digest_due(sent, datetime(2026, 10, 30, 6, 30, tzinfo=timezone.utc)))
        self.assertFalse(digest_due(_user(notifications=False), datetime(2026, 10, 30, 6, 30, tzinfo=timezone.utc)))

    def test_screens_have_no_outbound_text(self) -> None:
        items = [
            _article(id=1),
            _article(
                id=2,
                guid="g2",
                title="Nasdaq falls on weak earnings season",
                category="stocks",
                source_name="CNBC",
                url="https://www.cnbc.com/2025/10/30/nasdaq.html",
                published_at="2026-10-30T11:00:00Z",
            ),
            _article(
                id=3,
                guid="g3",
                title="Bitcoin slides after a sharp weekend selloff",
                category="crypto",
                source_name="CoinDesk",
                url="https://www.coindesk.com/markets/bitcoin",
                published_at="2026-10-30T10:00:00Z",
            ),
        ]
        user = _user()
        texts = [
            render_home(items, "ru", "Europe/Moscow", "2026-10-30T12:05:00Z"),
            render_home([], "ru", "Europe/Moscow", None),
            render_digest(items, "ru", "Europe/Moscow", "2026-10-30T12:05:00Z", mailed=True),
            render_analytics(items, "ru", premium=False),
            render_analytics(items, "en", premium=True),
            render_article(items[0], "ru", "Europe/Moscow"),
            render_full(items[0], "ru", "Europe/Moscow", expanded=False),
            render_full(items[0], "ru", "Europe/Moscow", expanded=True),
            render_help("ru"),
            render_help("en"),
            render_settings(user),
            render_plus(user),
            render_sources("ru", [("BBC Business", "Деловые новости")], allow_link=False),
            render_sources("ru", [("BBC Business", "Деловые новости")], allow_link=True),
        ]
        for text in texts:
            _no_link(text)
        home = texts[0]
        self.assertIn("Market News", home)
        self.assertIn("Сегодняшние главные новости", home)
        self.assertIn("BBC Business", home)
        self.assertIn("Oil prices rise", home)
        full = render_full(items[0], "ru", "UTC", expanded=True)
        self.assertNotIn(items[0].url, full)
        self.assertNotIn("Текст выше сохранён", full)
        self.assertNotIn("Рядом по теме", full)
        empty = _article(summary="", body="", title="Bitcoin slides after a sharp weekend selloff")
        home_empty = render_home([empty], "ru", "UTC", None)
        _no_link(home_empty)
        self.assertIn("Bitcoin slides", home_empty)
        self.assertNotIn("не было отдельного", home_empty)
        self.assertEqual([item.id for item in with_summary([empty, items[0]])], [items[0].id])
        pictured = _article(image_url="https://ichef.bbci.co.uk/news/1024/branded_news/oil.jpg")
        card = render_article(pictured, "ru", "Europe/Moscow")
        self.assertIn("<h1>", card)
        self.assertIn("<img src=\"https://ichef.bbci.co.uk/news/1024/branded_news/oil.jpg\"", card)
        self.assertNotIn(pictured.url, card)
        second = _article(
            id=2,
            guid="g2",
            title="Nasdaq falls on weak earnings season",
            image_url="https://image.cnbcfm.com/api/v1/image/nasdaq.jpg",
        )
        home_two = render_home([pictured, second], "ru", "UTC", None)
        self.assertNotIn("<tg-collage>", home_two)
        oil_at = home_two.find(pictured.image_url)
        nasdaq_at = home_two.find(second.image_url)
        self.assertLess(home_two.find(pictured.title), oil_at)
        self.assertLess(oil_at, home_two.find(second.title))
        self.assertLess(home_two.find(second.title), nasdaq_at)

    def test_rich_html_keeps_story_when_image_drops(self) -> None:
        card = '<h1>Oil</h1><figure><img src="https://ichef.bbci.co.uk/news/1024/oil.jpg"/></figure><p>Lead</p>'
        plain = without_images(card)
        self.assertNotIn("<img", plain)
        self.assertIn("<h1>Oil</h1>", plain)
        wrapped = as_rich_html("<b>Help</b>\nline two")
        self.assertIn("<p>", wrapped)
        self.assertIn("<br/>", wrapped)

    def test_command_languages(self) -> None:
        self.assertEqual(set(COMMANDS), {"ru", "en", "uk", "ar"})
        names = [name for name, _ in COMMANDS["ru"]]
        for code, rows in COMMANDS.items():
            self.assertEqual([name for name, _ in rows], names)
            for _, description in rows:
                self.assertTrue(description.strip())
                self.assertLessEqual(len(description), 256)

    def test_keyboards_hide_urls_until_allowed(self) -> None:
        items = [_article(id=index, guid=f"g{index}") for index in range(1, 4)]
        user = _user()
        closed = [
            home_keyboard("ru"),
            digest_keyboard("ru", items),
            analytics_keyboard("ru"),
            article_keyboard("ru", 1, "d"),
            full_keyboard("ru", items[0], "d", allow_link=False),
            settings_keyboard(user),
            help_keyboard("ru"),
            plus_keyboard("ru", premium=False),
            sources_keyboard("ru", None),
        ]
        for markup in closed:
            self.assertEqual(_urls(markup), [])
            _actions(markup)
        home_actions = _actions(home_keyboard("ru"))
        for name in ("digest", "analytics", "settings", "help", "latest", "cats", "story"):
            self.assertIn(name, home_actions)
        opened = full_keyboard("ru", items[0], "d", allow_link=True)
        self.assertEqual(_urls(opened), [items[0].url])
        linked = sources_keyboard("ru", [("BBC Business", "https://www.bbc.com/news/business")])
        self.assertEqual(_urls(linked), ["https://www.bbc.com/news/business"])
        poisoned = sources_keyboard("ru", [("BBC Business", "https://t.me/channel")])
        self.assertEqual(_urls(poisoned), [])
        packed = Act(a="open", i=15, c="kmarkets").pack()
        restored = Act.unpack(packed)
        self.assertEqual((restored.a, restored.i, restored.c), ("open", 15, "kmarkets"))


class FullTextTests(unittest.TestCase):
    def test_extracts_article_paragraphs(self) -> None:
        html = """
        <html><body><article>
        <p>Brent moved higher after ministers met and left the supply plan unchanged for the next quarter. Shipping data showed fewer cargoes leaving the Gulf, and refiners in Europe started bidding for later deliveries.</p>
        <p>Traders waited for the written statement before the next session and watched shipping through the strait. Several banks kept their price forecasts unchanged until the official communique is published later this week.</p>
        <p>Menu</p>
        </article></body></html>
        """
        text = extract_text(html)
        self.assertIn("Brent moved higher", text)
        self.assertIn("written statement", text)

    def test_short_blurb_is_not_full_text(self) -> None:
        self.assertFalse(is_full_text(_article()))
        long = _article(body=("Brent moved higher. " * 80))
        self.assertTrue(is_full_text(long))


class FeedTests(unittest.TestCase):
    def test_parse_fixture(self) -> None:
        feed = Feed("bbc", "BBC Business", "https://example.invalid/rss", None)
        items = parse_feed(feed, _FIXTURE, now="2026-10-30T12:05:00Z")
        by_title = {item.title: item for item in items}
        oil = by_title["Oil prices rise as OPEC meets in Vienna"]
        self.assertEqual(oil.category, "oil")
        self.assertEqual(oil.url, "https://www.bbc.co.uk/news/business/oil-1")
        self.assertEqual(oil.image_url, "https://ichef.bbci.co.uk/news/1024/oil.jpg")
        self.assertNotIn("http", oil.summary)
        self.assertNotIn("Read more", oil.summary)
        bitcoin = by_title["Bitcoin slides after a sharp weekend selloff"]
        self.assertEqual(bitcoin.category, "crypto")
        self.assertEqual(bitcoin.url, "")
        self.assertNotIn("t.me", bitcoin.summary)
        self.assertNotIn("http", bitcoin.body)
        stocks = by_title["Nasdaq falls on weak earnings season"]
        self.assertEqual(stocks.category, "stocks")
        prepared = prepare_items(items + [items[0]], set())
        self.assertEqual(len(prepared), len(items))


class DatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(str(Path(self.tmp.name) / "t.sqlite3"))
        await self.db.connect()

    async def asyncTearDown(self) -> None:
        await self.db.close()
        self.tmp.cleanup()

    async def test_user_settings_and_reads(self) -> None:
        user = await self.db.upsert_user(7, "ann", "Ann")
        self.assertEqual(user.lang, "ru")
        self.assertEqual(user.digest_hour, 9)
        user = await self.db.set_lang(7, "en")
        user = await self.db.set_hour(7, 18)
        user = await self.db.set_notifications(7, False)
        await self.db.set_blocked(7, True)
        user = await self.db.upsert_user(7, "ann", "Ann")
        self.assertEqual(user.lang, "en")
        self.assertEqual(user.digest_hour, 18)
        self.assertFalse(user.notifications)
        self.assertFalse(user.blocked)
        user = await self.db.add_interaction(7, full_read=True)
        self.assertEqual((user.interactions, user.full_reads), (1, 1))

    async def test_articles_dedup_and_gate(self) -> None:
        first = _article(id=0, guid="same", title="Oil prices rise as OPEC meets in Vienna", summary="First long summary about the oil meeting today.")
        second = _article(id=0, guid="same", title="Oil prices rise as OPEC meets in Vienna", summary="Second long summary about the same oil meeting.")
        other = _article(id=0, guid="other", title="Oil prices rise as OPEC meets in Vienna", summary="Duplicate headline from another feed should be skipped.")
        stocks = _article(
            id=0,
            guid="st",
            title="Nasdaq falls on weak earnings season",
            category="stocks",
            url="https://www.cnbc.com/2025/10/30/nasdaq.html",
            source_name="CNBC",
        )
        bad = _article(
            id=0,
            guid="bad",
            title="Bitcoin slides after a sharp weekend selloff",
            category="crypto",
            url="https://bit.ly/evil",
            source_name="CoinDesk",
        )
        await self.db.upsert_articles([first, stocks, bad])
        await self.db.upsert_articles([second, other])
        self.assertEqual(await self.db.count_articles(), 3)
        stored = {item.guid: item for item in await self.db.recent(10)}
        self.assertEqual(stored["same"].summary, second.summary)
        self.assertEqual(stored["bad"].url, "")
        self.assertTrue(stored["st"].url.startswith("https://www.cnbc.com/"))

        user = await self.db.upsert_user(3, None, "M")
        for item in stored.values():
            await self.db.mark_seen(3, item.id)
        await self.db.mark_seen(3, stored["same"].id)
        self.assertEqual(await self.db.count_seen(3), 3)
        for _ in range(4):
            user = await self.db.add_interaction(3)
        from content import links_allowed

        self.assertFalse(
            links_allowed(user.interactions, await self.db.count_seen(3), await self.db.count_articles())
        )
        user = await self.db.add_interaction(3)
        self.assertTrue(
            links_allowed(user.interactions, await self.db.count_seen(3), await self.db.count_articles())
        )

        for item in stored.values():
            await self.db.save_full_text(item.id, None)
        await self.db.save_full_text(stored["st"].id, "Nasdaq fell after weak earnings. " * 40)
        stored = {item.guid: item for item in await self.db.recent(10)}

        locked_text, locked_markup = await full_screen(self.db, _user(user_id=9, interactions=0), stored["st"], "d")
        _no_link(locked_text)
        self.assertEqual(_urls(locked_markup), [])

        open_text, open_markup = await full_screen(self.db, user, stored["st"], "d")
        _no_link(open_text)
        self.assertEqual(_urls(open_markup), [stored["st"].url])

        home_text, home_markup = await home_screen(self.db, user)
        _no_link(home_text)
        self.assertIn("Сегодняшние главные новости", home_text)
        self.assertEqual(_urls(home_markup), [])

    async def test_russian_translation_overlays_the_story(self) -> None:
        original = _article(id=0, guid="tr", title="Oil prices rise as OPEC meets in Vienna")
        await self.db.upsert_articles([original])
        stored = (await self.db.recent(5))[0]
        english = await self.db.apply_translations([stored], "en")
        self.assertEqual(english[0].title, stored.title)
        await self.db.save_translations(
            "ru",
            [(stored, "Цены на нефть выросли перед встречей ОПЕК", "Краткий перевод.", "Полный перевод.")],
        )
        russian = await self.db.apply_translations([stored], "ru")
        self.assertEqual(russian[0].title, "Цены на нефть выросли перед встречей ОПЕК")
        self.assertEqual(russian[0].summary, "Краткий перевод.")
        self.assertEqual(russian[0].title_norm, stored.title_norm)
        changed = _article(
            id=stored.id,
            guid=stored.guid,
            title="Oil prices rise as OPEC meets in Vienna today",
            title_norm=stored.title_norm,
        )
        stale = await self.db.apply_translations([changed], "ru")
        self.assertEqual(stale[0].title, changed.title)

    def test_translation_payload(self) -> None:
        raw = """```json
{"items":[{"id":7,"title":"Заголовок","summary":"Кратко","body":""}]}
```"""
        parsed = parse_translation_payload(raw)
        self.assertEqual(parsed[0]["id"], "7")
        self.assertEqual(parsed[0]["title"], "Заголовок")
        self.assertEqual(parsed[0]["body"], "")
        extra = parsed[0]
        parsed_extra = parse_translation_payload(raw + " trailing note")
        self.assertEqual(parsed_extra[0]["title"], extra["title"])
        article = _article(id=7, guid="tr-json", title="Oil prices rise as OPEC meets in Vienna")
        rows = _rows_from_content(raw, [article])
        self.assertEqual(rows[0][1], "Заголовок")
        self.assertEqual(_model_chain("gpt-6-luna", "claude-haiku-5-5", "gpt-6-luna"), ("gpt-6-luna", "claude-haiku-5-5"))

    async def test_payment_is_idempotent(self) -> None:
        await self.db.upsert_user(5, None, "P")
        self.assertTrue(await self.db.save_payment("ch1", 5, 50))
        self.assertFalse(await self.db.save_payment("ch1", 5, 50))
        user = await self.db.extend_premium(5, 30)
        self.assertTrue(user.premium_active())


if __name__ == "__main__":
    unittest.main()
