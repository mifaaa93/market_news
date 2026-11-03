"""Public catalog replacement and temporary publisher throttling."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import fulltext
from content import is_public_article_url
from db import Database
from feeds import CATALOG_ROWS, FEEDS, Feed, parse_feed, prepare_items
from models import Article
from rss_discovery import ai_urls, candidates_from_html
from source_security import same_site


class CatalogTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.database = Database(str(Path(self.temp.name) / "catalog.sqlite3"))
        await self.database.connect()

    async def asyncTearDown(self) -> None:
        await self.database.close()
        self.temp.cleanup()

    async def test_retired_public_feeds_removed_without_touching_private_feed(self) -> None:
        await self.database.upsert_user(42, None, "Test")
        await self.database.ensure_catalog(
            [("marketwatch", "MarketWatch", "https://feeds.marketwatch.com/rss", "")]
        )
        await self.database.ensure_catalog(
            CATALOG_ROWS + [("guardian-business", "The Guardian", "https://example.com/rss", "")]
        )
        await self.database.add_custom_source(
            42, "custom:42:myfeed", "My feed", "https://example.com/feed", "https://example.com"
        )
        await self.database.ensure_catalog(CATALOG_ROWS)
        catalog = await self.database.list_sources()
        self.assertEqual({row[0] for row in CATALOG_ROWS}, {item.key for item in catalog})
        self.assertIsNone(await self.database.source("marketwatch"))
        self.assertIsNone(await self.database.source("guardian-business"))
        self.assertIsNotNone(await self.database.source("custom:42:myfeed"))
        self.assertEqual(len(await self.database.list_sources(42)), len(CATALOG_ROWS) + 1)

    async def test_retired_guardian_articles_are_removed(self) -> None:
        article = Article(
            id=0, guid="guardian-business:sample", source_key="guardian-business",
            source_name="The Guardian", title="Markets rally after central bank statement",
            title_norm="marketsrallyaftercentralbankstatement", summary="Markets rose.",
            body="Markets rose. " * 100, url="", category="stocks",
            published_at="2026-11-01T12:00:00Z", fetched_at="2026-11-01T12:01:00Z",
        )
        await self.database.upsert_articles([article])
        self.assertEqual(len(await self.database.recent(10)), 1)
        await self.database.ensure_catalog(CATALOG_ROWS)
        self.assertEqual(await self.database.recent(10), [])

    async def test_abc_is_opt_in_for_existing_basic_users(self) -> None:
        await self.database.upsert_user(10, None, "Existing user")
        await self.database.ensure_catalog(CATALOG_ROWS)
        selected = {source.key for source in await self.database.active_sources(10)}
        self.assertEqual(
            selected,
            {"bbc", "cnbc-economy", "cnbc-finance", "cnbc-oil", "coindesk"},
        )
        await self.database.set_source_enabled(10, "coindesk", False)
        await self.database.set_source_enabled(10, "abc-business", True)
        selected = {source.key for source in await self.database.active_sources(10)}
        self.assertIn("abc-business", selected)
        self.assertNotIn("coindesk", selected)

    async def test_pro_only_article_does_not_push_to_plus_until_catalog_cycle(self) -> None:
        await self.database.ensure_catalog(CATALOG_ROWS)
        await self.database.upsert_user(101, None, "Plus")
        await self.database.upsert_user(102, None, "Pro")
        await self.database.extend_plan(101, "plus", 30)
        await self.database.extend_plan(102, "pro", 30)
        article = Article(
            id=0, guid="pro-only", source_key="bbc", source_name="BBC Business",
            title="Markets react after a central bank decision",
            title_norm="marketsreactafteracentralbankdecision",
            summary="Markets moved after the decision.",
            body="Markets moved after the decision. " * 60,
            url="https://www.bbc.co.uk/news/business/pro-only",
            category="macro", published_at="2026-11-02T10:00:00Z",
            fetched_at="2026-11-02T10:00:00Z", catalog_visible=False,
        )
        await self.database.upsert_articles([article], catalog_visible=False)
        stored = (await self.database.recent(1))[0]
        subscribers = {user.user_id for user in await self.database.list_push_subscribers(stored)}
        self.assertEqual(subscribers, {102})
        await self.database.mark_catalog_visible([stored])
        stored = await self.database.get_article(stored.id)
        subscribers = {user.user_id for user in await self.database.list_push_subscribers(stored)}
        self.assertEqual(subscribers, {101, 102})

    def test_catalog_display_names_are_unique(self) -> None:
        names = [name for _, name, _, _ in CATALOG_ROWS]
        self.assertEqual(len(names), len(set(names)))

    def test_new_sources_allow_only_their_public_article_urls(self) -> None:
        for url in (
            "https://abcnews.com/Business/wireStory/fbi-blames-north-korea-137741287",
            "https://abcnews.go.com/Business/wireStory/fbi-blames-north-korea-137741287",
            "https://www.eia.gov/todayinenergy/detail.php?id=68384",
            "https://www.eia.gov/pressroom/releases/press593.php",
            "https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm",
        ):
            self.assertTrue(is_public_article_url(url), url)
        self.assertFalse(is_public_article_url("https://bit.ly/fake"))
        self.assertFalse(is_public_article_url("https://abcnews.com.example.org/Business/story"))

    def test_abc_feed_keeps_article_url_for_full_text(self) -> None:
        feed = next(item for item in FEEDS if item.key == "abc-business")
        self.assertIn(("abc-business", feed.name, feed.url, "https://abcnews.go.com/Business"), CATALOG_ROWS)
        raw = b"""<rss version="2.0"><channel>
            <item><title>Stock markets react after central bank decision</title>
            <link>https://abcnews.com/Business/wireStory/stock-markets-react-12345</link>
            <guid>abc-stock-12345</guid><description>Shares moved.</description></item>
            </channel></rss>"""
        parsed = parse_feed(feed, raw)
        self.assertEqual(len(parsed), 1)
        prepared = prepare_items(parsed, set())
        self.assertEqual(prepared[0].source_key, "abc-business")
        self.assertEqual(
            prepared[0].url,
            "https://abcnews.com/Business/wireStory/stock-markets-react-12345",
        )

    def test_discovery_handles_subdomain_feed_and_ai_json(self) -> None:
        self.assertTrue(
            same_site("https://abcnews.com/Business/story", "feeds.abcnews.com")
        )
        self.assertTrue(
            same_site("https://abcnews.go.com/Business/story", "feeds.abcnews.com")
        )
        self.assertFalse(
            same_site("https://example.com/story", "feeds.abcnews.com")
        )
        html = b"""<html><head><title>Business</title>
          <link rel="alternate" type="application/rss+xml" href="/rss.xml">
        </head></html>"""
        candidates, title = candidates_from_html("https://example.com/business", html)
        self.assertEqual(title, "Business")
        self.assertIn("https://example.com/rss.xml", candidates)
        self.assertEqual(
            ai_urls('```json\n{"urls":["https://example.com/feed.xml"]}\n```'),
            ["https://example.com/feed.xml"],
        )
        self.assertEqual(ai_urls("not json"), [])

    def test_eia_relative_feed_links_are_normalized(self) -> None:
        raw = b"""<rss version="2.0"><channel>
            <item><title>Energy prices change after weekly report</title>
            <link>/pressroom/releases/press593.php</link><guid>press593</guid>
            <description>Energy market news.</description></item>
            </channel></rss>"""
        items = parse_feed(
            Feed("eia-press", "U.S. EIA", "https://www.eia.gov/rss/press_rss.xml", "oil"),
            raw,
        )
        self.assertEqual(items[0].url, "https://www.eia.gov/pressroom/releases/press593.php")

    async def test_rate_limit_does_not_permanently_reject_coindesk(self) -> None:
        article = Article(
            id=0, guid="retry:coindesk", source_key="coindesk", source_name="CoinDesk",
            title="Crypto markets remain volatile after today's report",
            title_norm="cryptomarketsremainvolatileaftertodaysreport",
            summary="Short summary", body="Short summary",
            url="https://www.coindesk.com/markets/test-story", category="crypto",
            published_at="2026-10-31T12:00:00Z", fetched_at="2026-10-31T12:01:00Z",
        )
        await self.database.upsert_articles([article])
        with (
            patch.object(fulltext, "fetch_article_text", side_effect=fulltext.RateLimited("coindesk.com")),
            patch.object(fulltext.asyncio, "sleep", new_callable=AsyncMock),
        ):
            self.assertEqual(await fulltext.fill_full_texts(self.database), 0)
        pending = await self.database.articles_needing_full_text()
        self.assertEqual([item.guid for item in pending], [article.guid])
        self.assertFalse(pending[0].full_checked)


class RetryDelayTests(unittest.TestCase):
    def test_retry_after_is_bounded(self) -> None:
        self.assertEqual(fulltext._retry_delay("120"), 120)
        self.assertEqual(fulltext._retry_delay("0"), 60)
        self.assertEqual(fulltext._retry_delay("3000"), 1200)
        self.assertEqual(fulltext._retry_delay("garbage"), 60)
