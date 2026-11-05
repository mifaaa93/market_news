"""Поведение бота без Telegram: тексты, гейт ссылок, GNews, клавиатуры."""

from __future__ import annotations

import os
import unittest
import dataclasses
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from images import to_jpeg
from content import (
    classify,
    classify_topics,
    clean_text,
    source_search_terms,
    clean_url,
    digest_due,
    is_full_text,
    is_public_article_url,
    links_allowed,
    pick_digest,
    render_article,
    render_digest,
    render_home,
    render_full,
    render_settings,
    resolve_category,
    title_norm,
)
import config
from gnews import (
    headlines_params,
    is_quality_search_article,
    parse_articles,
    parse_published,
    requests_per_cycle,
    search_due,
    search_params,
)
from translate import parse_translation_payload
from jobs import top_quota_reserve
from keyboards import (
    Act,
    analytics_keyboard,
    article_keyboard,
    digest_keyboard,
    feed_keyboard,
    full_keyboard,
    help_keyboard,
    home_keyboard,
    settings_keyboard,
    sources_keyboard,
)
from models import Article, User
from texts import ABOUT_AR, ABOUT_EN, ABOUT_RU, SHORT_AR, SHORT_EN, SHORT_RU, STRINGS, interface_lang, lang_label, t
from ui import as_rich_html, without_images


def _article(**kwargs) -> Article:
    title = kwargs.get("title", "Oil prices rise as OPEC meets in Vienna")
    data = {
        "id": 1,
        "guid": "g1",
        "source_id": 1,
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
        "lang": "en",
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
        self.assertIn("Reuters", ABOUT_RU)
        from content import render_how_it_works
        from texts import format_publishers
        self.assertIn("CNBC", format_publishers(lang="ru"))
        self.assertIn("тысячи", format_publishers(lang="ru"))
        self.assertNotIn("Hortidaily", render_how_it_works("ru", ["Hortidaily", "ing think", "BBC"]))
        self.assertIn("Reuters", render_how_it_works("ru"))
        self.assertNotIn("{sources}", render_how_it_works("ru"))
        self.assertLessEqual(len(t("ru", "plus_invoice_title")), 32)
        self.assertLessEqual(len(t("ar", "plus_invoice_title")), 32)
        self.assertLessEqual(len(t("en", "plus_invoice_desc")), 255)
        self.assertLessEqual(len(t("ru", "plus_invoice_desc")), 255)
        self.assertLessEqual(len(t("ar", "plus_invoice_desc")), 255)
        self.assertIn("العربية", lang_label("ar"))
        self.assertEqual(interface_lang("en"), "en")
        self.assertEqual(interface_lang("en-US"), "en")
        self.assertEqual(interface_lang("AR"), "ar")
        self.assertEqual(interface_lang("uk"), "ru")
        self.assertEqual(interface_lang(None), "ru")

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
        self.assertEqual(classify("Цены на нефть выросли перед ОПЕК"), "oil")
        self.assertEqual(resolve_category("quiet day on the exchange", None), "markets")
        both = classify_topics(
            "Fed holds rates as oil climbs",
            "OPEC kept output unchanged while inflation cooled.",
        )
        self.assertEqual(set(both), {"macro", "oil"})
        self.assertGreaterEqual(len(both), 2)

    def test_source_search_terms(self) -> None:
        name, host = source_search_terms("Reuters")
        self.assertEqual(name, "Reuters")
        self.assertIsNone(host)
        _, host = source_search_terms("https://www.reuters.com/world/asia")
        self.assertEqual(host, "reuters.com")
        from config import source_pin_order

        self.assertEqual(source_pin_order("Reuters", "https://www.reuters.com"), 1)
        self.assertIsNotNone(source_pin_order("Yahoo Finance", "https://finance.yahoo.com"))
        self.assertIsNone(source_pin_order("Hortidaily", "https://www.hortidaily.com"))

    def test_title_norm_keeps_non_latin(self) -> None:
        self.assertIn("нефть", title_norm("Цены на нефть выросли"))
        self.assertTrue(len(title_norm("أسعار النفط ترتفع")) >= 8)

    def test_public_urls(self) -> None:
        self.assertTrue(is_public_article_url("https://www.reuters.com/markets/oil-1"))
        self.assertTrue(is_public_article_url("https://www.cnbc.com/2025/10/30/nasdaq.html"))
        self.assertFalse(is_public_article_url("https://bit.ly/evil"))
        self.assertFalse(is_public_article_url("https://t.me/scam"))
        self.assertEqual(clean_url("https://bit.ly/evil"), "")

    def test_link_gate(self) -> None:
        self.assertFalse(links_allowed(4, 3, 10))
        self.assertFalse(links_allowed(5, 2, 10))
        self.assertTrue(links_allowed(5, 3, 10))

    def test_digest_due(self) -> None:
        now = datetime(2026, 3, 1, 6, 30, tzinfo=timezone.utc)
        user = _user(last_digest_on=None)
        self.assertTrue(digest_due(user, now))
        self.assertFalse(digest_due(_user(last_digest_on="2026-03-01"), now))
        self.assertFalse(digest_due(_user(notifications=False), now))

    def test_pick_digest_spreads_topics(self) -> None:
        items = [
            _article(id=1, category="oil", published_at="2026-10-30T12:00:00Z"),
            _article(id=2, title="Second oil story today after OPEC", category="oil", published_at="2026-10-30T11:00:00Z"),
            _article(id=3, title="Nasdaq falls on weak earnings season", category="stocks", published_at="2026-10-30T10:00:00Z"),
        ]
        picked = pick_digest(items, 2)
        self.assertEqual([item.category for item in picked], ["oil", "stocks"])

    def test_screens_have_no_outbound_links(self) -> None:
        article = _article()
        user = _user(interactions=10, full_reads=5)
        for rendered in (
            render_home([article], "ru", "Europe/Moscow", "2026-10-30T12:00:00Z"),
            render_digest([article], "ru", "Europe/Moscow", "2026-10-30T12:00:00Z"),
            render_article(article, "ru", "Europe/Moscow"),
            render_full(article, "ru", "Europe/Moscow", expanded=True),
        ):
            _no_link(rendered)
            self.assertNotIn("30.10.2026", rendered)
            self.assertNotIn("12:00", rendered)
            self.assertNotIn("инвестиционной рекомендацией", rendered)
        _no_link(render_settings(user))
        self.assertTrue(is_full_text(article))
        self.assertEqual(_urls(home_keyboard("ru")), [])
        self.assertEqual(_urls(digest_keyboard("ru", [article])), [])
        self.assertEqual(_urls(article_keyboard("ru", 1, "d")), [])
        self.assertEqual(_urls(full_keyboard("ru", article, "d")), [])
        self.assertEqual(_urls(settings_keyboard(user)), [])
        self.assertEqual(_urls(help_keyboard("ru")), [])
        self.assertEqual(_urls(sources_keyboard("ru", None)), [])
        self.assertEqual(_urls(analytics_keyboard("ru")), [])
        actions = _actions(home_keyboard("ru"))
        self.assertIn("how_it_works", actions)
        self.assertIn("feed", actions)
        self.assertNotIn("add_source", actions)
        home = render_home([article], "ru", "Europe/Moscow", "2026-10-30T12:00:00Z")
        self.assertNotIn("<img", home.lower())

    def test_article_render_includes_cached_photo(self) -> None:
        article = _article(telegram_photo_id="AgACAgQAAx")
        rendered = render_article(article, "ru", "Europe/Moscow")
        self.assertIn('tg://photo?id=cover', rendered)

    def test_feed_keyboard_paginates(self) -> None:
        rows = [
            (11, True, None, "Reuters", 9),
            (12, False, "Plus", "CNBC", 4),
        ]
        markup = feed_keyboard("en", rows, page=2, pages=3)
        actions = _actions(markup)
        self.assertGreaterEqual(actions.count("feed"), 4)
        self.assertEqual(len(markup.inline_keyboard[0]), 2)
        self.assertEqual(_urls(markup), [])
        packed = markup.inline_keyboard[0][0].callback_data
        data = Act.unpack(packed)
        self.assertEqual(data.i, 11)
        self.assertEqual(data.c, "2")
        extras = [Act.unpack(btn.callback_data).c for row in markup.inline_keyboard for btn in row if btn.callback_data]
        self.assertIn("off", extras)
        self.assertIn("star", extras)

    def test_html_helpers(self) -> None:
        html = "<p>Hi <img src='x'> there</p>"
        self.assertNotIn("<img", without_images(html))
        self.assertIn("<b>", as_rich_html("plain <b>bold</b>"))

    def test_rich_html_escapes_unknown_markup(self) -> None:
        rendered = as_rich_html("<p>Price < 5 & <script>alert(1)</script> <b>safe</b></p>")
        self.assertIn("Price &lt; 5 &amp;", rendered)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendered)
        self.assertIn("<b>safe</b>", rendered)

    def test_news_fields_escape_markup(self) -> None:
        article = _article(
            title="Price < 5 & > 3",
            summary="A <b>quoted</b> & raw update with enough text to remain the summary.",
            source_name="News <Wire>",
        )
        rendered = render_article(article, "ru", "Europe/Moscow")
        self.assertIn("Price &lt; 5 &amp; &gt; 3", rendered)
        self.assertIn("A &lt;b&gt;quoted&lt;/b&gt; &amp; raw", rendered)
        self.assertIn("News &lt;Wire&gt;", rendered)


class GNewsTests(unittest.TestCase):
    def test_requests_per_cycle(self) -> None:
        self.assertEqual(requests_per_cycle(), 1)

    def test_headlines_params(self) -> None:
        params = headlines_params("en")
        self.assertEqual(params["category"], "business")
        self.assertEqual(params["lang"], "en")
        self.assertEqual(params["max"], str(config.GNEWS_MAX))
        self.assertEqual(params["nullable"], "image")

    def test_search_params(self) -> None:
        params = search_params("en")
        self.assertIn("stock", params["q"])
        self.assertEqual(params["lang"], "en")
        self.assertEqual(params["sortby"], "publishedAt")
        self.assertEqual(params["page"], "1")
        self.assertEqual(params["in"], "title,description")
        self.assertEqual(
            search_params("en", query="oil OR Brent")["q"],
            "oil OR Brent",
        )
        self.assertTrue(all(len(query) <= 200 for query in config.GNEWS_SEARCH_QUERIES))

    def test_search_quality_filter(self) -> None:
        good = _article(
            title="Federal Reserve holds interest rates as inflation cools",
            summary="Investors watched the central bank decision.",
            body="Bond yields fell after the Federal Reserve published its decision.",
            category="macro",
        )
        noise = _article(
            title="UK households should stock up on essential foods before winter",
            summary="A weather warning was issued.",
            body="A weather warning was issued and households prepared supplies.",
            category="markets",
        )
        from gnews import IncomingArticle

        good_incoming = IncomingArticle(
            guid=good.guid,
            title=good.title,
            title_norm=good.title_norm,
            summary=good.summary,
            body=good.body,
            url=good.url,
            image_url=good.image_url,
            category=good.category,
            published_at=good.published_at,
            lang=good.lang,
            source_name=good.source_name,
            source_url="https://www.bbc.co.uk",
            source_extra={},
        )
        noise_incoming = IncomingArticle(
            guid=noise.guid,
            title=noise.title,
            title_norm=noise.title_norm,
            summary=noise.summary,
            body=noise.body,
            url=noise.url,
            image_url=noise.image_url,
            category=noise.category,
            published_at=noise.published_at,
            lang=noise.lang,
            source_name=noise.source_name,
            source_url="https://www.example.com",
            source_extra={},
        )
        self.assertTrue(is_quality_search_article(good_incoming))
        self.assertFalse(is_quality_search_article(noise_incoming))
        market = dataclasses.replace(
            good_incoming,
            title="Market traders celebrate town centre reopening",
            summary="An annual festival opens in the town centre.",
            body="An annual festival opens in the town centre.",
            category="markets",
        )
        self.assertFalse(is_quality_search_article(market))

    def test_search_cadence(self) -> None:
        from unittest.mock import patch

        with patch.object(config, "GNEWS_SEARCH_TIMEZONE", "UTC"):
            last = "2026-11-05T06:45:00Z"
            self.assertFalse(search_due(last, datetime(2026, 11, 5, 6, 50, tzinfo=timezone.utc)))
            self.assertTrue(search_due(last, datetime(2026, 11, 5, 7, 0, tzinfo=timezone.utc)))
            self.assertTrue(search_due(
                "2026-11-05T12:00:05Z",
                datetime(2026, 11, 5, 12, 1, tzinfo=timezone.utc),
            ))
            self.assertFalse(search_due(
                "2026-11-05T12:00:05Z",
                datetime(2026, 11, 5, 12, 0, 40, tzinfo=timezone.utc),
            ))
            self.assertFalse(search_due("2026-11-05T22:00:00Z", datetime(2026, 11, 5, 22, 15, tzinfo=timezone.utc)))
            self.assertTrue(search_due("2026-11-05T22:00:00Z", datetime(2026, 11, 5, 22, 30, tzinfo=timezone.utc)))
        with patch.object(config, "GNEWS_SEARCH_TIMEZONE", "Europe/Kiev"):
            # In November Kyiv is UTC+2; the active period begins at 05:00 UTC.
            self.assertEqual(
                config.search_interval_minutes(datetime(2026, 11, 5, 5, tzinfo=timezone.utc)),
                1,
            )
            self.assertEqual(
                config.search_interval_minutes(datetime(2026, 11, 5, 22, tzinfo=timezone.utc)),
                30,
            )

    def test_top_quota_reserve(self) -> None:
        noon = datetime(2026, 3, 1, 12, 30, tzinfo=timezone.utc)
        after_run = "2026-03-01T12:01:00Z"
        self.assertEqual(top_quota_reserve(noon, after_run), 1)
        before_run = "2026-03-01T06:01:00Z"
        self.assertEqual(top_quota_reserve(noon, before_run), 2)

    def test_parse_published(self) -> None:
        self.assertEqual(parse_published("2026-03-01T12:00:00Z", "x"), "2026-03-01T12:00:00Z")
        self.assertEqual(parse_published("not-a-date", "fallback"), "fallback")

    def test_parse_articles_keeps_source_and_drops_junk(self) -> None:
        payload = {
            "totalArticles": 2,
            "articles": [
                {
                    "title": "Oil prices rise as OPEC meets in Vienna",
                    "description": "Brent moved higher after the meeting.",
                    "content": "Ministers left the supply plan unchanged. " * 5,
                    "url": "https://www.reuters.com/markets/oil-opec",
                    "image": "https://www.reuters.com/resizer/oil.jpg",
                    "publishedAt": "2026-03-01T12:00:00Z",
                    "source": {"name": "Reuters", "url": "https://www.reuters.com", "country": "us"},
                },
                {
                    "title": "Tiny",
                    "url": "https://t.me/scam",
                    "source": {"name": "Spam", "url": "https://t.me/scam"},
                },
            ],
        }
        items = parse_articles(payload, "en", now="2026-03-01T12:05:00Z")
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.source_name, "Reuters")
        self.assertEqual(item.source_url, "https://www.reuters.com")
        self.assertEqual(item.source_extra, {"country": "us"})
        self.assertEqual(item.lang, "en")
        self.assertEqual(item.category, "oil")
        self.assertTrue(item.url.startswith("https://www.reuters.com/"))

    def test_to_jpeg_from_png_bytes(self) -> None:
        from io import BytesIO

        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (12, 12), color=(20, 80, 160)).save(buf, format="PNG")
        jpeg = to_jpeg(buf.getvalue())
        self.assertIsNotNone(jpeg)
        self.assertGreater(len(jpeg or b""), 20)
        self.assertEqual(jpeg[:2], b"\xff\xd8")

    def test_parse_translation_payload(self) -> None:
        rows = parse_translation_payload(
            '{"items":[{"id":7,"title":"Нефть выросла","summary":"Брент","body":"","topics":["oil","macro"]}]}'
        )
        self.assertEqual(rows[0]["id"], "7")
        self.assertEqual(rows[0]["title"], "Нефть выросла")
        self.assertEqual(rows[0]["topics"], ("oil", "macro"))
        from translate import normalize_topics

        self.assertEqual(normalize_topics(["Energy", "Equities", "markets"]), ("oil", "stocks"))


class SearchPollingTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_rotates_queries_and_filters_before_ingest(self) -> None:
        from jobs import poll_gnews

        data = {
            "totalArticles": 2,
            "articles": [
                {
                    "title": "Federal Reserve holds interest rates as inflation cools",
                    "description": "The central bank's policy decision moved bond yields.",
                    "content": "Investors assessed the decision and market impact.",
                    "url": "https://example.com/fed-rates",
                    "publishedAt": "2026-11-05T12:00:00Z",
                    "source": {"name": "Example Business", "url": "https://example.com"},
                },
                {
                    "title": "UK households should stock up on essential foods before winter",
                    "description": "A weather warning for local households.",
                    "content": "Households prepare for extreme weather.",
                    "url": "https://example.com/stock-up",
                    "publishedAt": "2026-11-05T12:01:00Z",
                    "source": {"name": "Example Local", "url": "https://example.com"},
                },
            ],
        }
        meta = {"search_query_index": "0"}

        async def meta_get(key: str) -> str | None:
            return meta.get(key)

        async def meta_set(key: str, value: str) -> None:
            meta[key] = value

        database = SimpleNamespace(
            quota_remaining=AsyncMock(return_value=1000),
            quota_consume=AsyncMock(return_value=True),
            meta_get=AsyncMock(side_effect=meta_get),
            meta_set=AsyncMock(side_effect=meta_set),
            ingest_articles=AsyncMock(return_value=1),
            delete_old=AsyncMock(return_value=0),
            seed_missing_feeds=AsyncMock(),
        )
        with patch("jobs.fetch_lang", new_callable=AsyncMock, return_value=data) as fetch:
            self.assertEqual(await poll_gnews(database, "search"), 1)
            first = database.ingest_articles.call_args.args[0]
            self.assertEqual([item.title for item in first], [data["articles"][0]["title"]])
            self.assertEqual(fetch.call_args.kwargs["query"], config.GNEWS_SEARCH_QUERIES[0])
            self.assertEqual(meta["search_query_index"], "1")
            self.assertEqual(await poll_gnews(database, "search"), 1)
            self.assertEqual(fetch.call_args.kwargs["query"], config.GNEWS_SEARCH_QUERIES[1])
            self.assertEqual(meta["search_query_index"], "2")


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "TEST_DATABASE_URL is not set")
class DatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        from db import Database

        self.db = Database(os.environ["TEST_DATABASE_URL"])
        await self.db.connect()

    async def asyncTearDown(self) -> None:
        async with self.db.pool.acquire() as conn:
            await conn.execute(
                "TRUNCATE article_pushes, seen, user_sources, articles, sources, users, payments, admin_actions, api_quota, meta CASCADE"
            )
        await self.db.close()

    async def test_user_lang_and_conflict(self) -> None:
        user = await self.db.upsert_user(7, "ann", "Ann")
        self.assertEqual(user.lang, "ru")
        user = await self.db.set_lang(7, "en")
        user = await self.db.upsert_user(7, "ann", "Ann", "ru")
        self.assertEqual(user.lang, "en")
        english = await self.db.upsert_user(8, "ben", "Ben", "en-GB")
        self.assertEqual(english.lang, "en")
        other = await self.db.upsert_user(10, "max", "Max", "de")
        self.assertEqual(other.lang, "ru")

    async def test_ingest_and_language_remap(self) -> None:
        from gnews import IncomingArticle

        en = IncomingArticle(
            guid="https://www.reuters.com/a",
            title="Oil prices rise as OPEC meets in Vienna today",
            title_norm=title_norm("Oil prices rise as OPEC meets in Vienna today"),
            summary="Brent moved higher after ministers met.",
            body="Brent moved higher after ministers met and left the plan unchanged.",
            url="https://www.reuters.com/a",
            image_url="",
            category="oil",
            published_at="2026-03-01T12:00:00Z",
            lang="en",
            source_name="Reuters",
            source_url="https://www.reuters.com",
            source_extra={},
        )
        ar = IncomingArticle(
            guid="https://www.reuters.com/ar/a",
            title="أسعار النفط ترتفع قبل اجتماع أوبك اليوم",
            title_norm=title_norm("أسعار النفط ترتفع قبل اجتماع أوبك اليوم"),
            summary="ارتفع خام برنت بعد الاجتماع.",
            body="ارتفع خام برنت بعد أن أبقى الوزراء خطة الإمداد دون تغيير.",
            url="https://www.reuters.com/ar/a",
            image_url="",
            category="oil",
            published_at="2026-03-01T12:01:00Z",
            lang="ar",
            source_name="Reuters",
            source_url="https://www.reuters.com",
            source_extra={},
        )
        await self.db.ingest_articles([en, ar])
        user = await self.db.upsert_user(42, None, "Reader", "en")
        enabled = await self.db.enabled_source_names(42, "en")
        self.assertEqual(enabled, ["Reuters"])
        switched = await self.db.set_lang(42, "ar")
        self.assertEqual(switched.lang, "ar")
        self.assertEqual(await self.db.enabled_source_names(42, "ar"), ["Reuters"])
        feed = await self.db.recent_for_user(42, 10)
        self.assertEqual(len(feed), 1)
        self.assertEqual(feed[0].lang, "ar")


if __name__ == "__main__":
    unittest.main()
