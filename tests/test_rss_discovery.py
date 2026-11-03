"""Discovery candidates, validation and network protection."""

import socket
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import rss_discovery
from source_security import PublicResolver, public_site, safe_get, same_site


class DiscoveryUnitTests(unittest.TestCase):
    def test_rejects_local_private_social_and_redirect_sites(self) -> None:
        for value in (
            "http://example.com/rss", "https://localhost/rss",
            "https://127.0.0.1/rss", "https://192.168.1.2/rss",
            "https://169.254.169.254/latest/meta-data",
            "https://[::1]/rss", "https://test.local/rss",
            "https://user:secret@example.com/rss", "https://example.com:8443/rss",
            "https://bit.ly/news", "https://t.me/channel",
        ):
            self.assertFalse(public_site(value), value)
        self.assertTrue(public_site("https://www.example.com/business/rss.xml"))
        self.assertTrue(same_site("https://feeds.example.com/rss", "www.example.com"))
        self.assertFalse(same_site("https://example.com.evil.org/rss", "example.com"))

    def test_discovers_rss_link_independent_of_attribute_order(self) -> None:
        markup = b"""<html><head><title>Market News</title>
        <link href="/rss/markets.xml" type="application/rss+xml" rel="alternate">
        <link rel="alternate" type="application/atom+xml" href="/atom.xml">
        </head><body><a href="/business/news">Market</a>
        <a href="https://evil.com/feed">Other</a></body></html>"""
        candidates, title = rss_discovery.candidates_from_html("https://example.com/business", markup)
        self.assertEqual(title, "Market News")
        self.assertIn("https://example.com/rss/markets.xml", candidates)
        self.assertIn("https://example.com/atom.xml", candidates)
        self.assertIn("https://example.com/business/feed/", candidates)
        self.assertIn(
            "https://example.com/business/news",
            rss_discovery.ai_hints("https://example.com/business", markup, "example.com"),
        )
        self.assertNotIn(
            "https://evil.com/feed",
            rss_discovery.ai_hints("https://example.com/business", markup, "example.com"),
        )

    def test_ai_candidates_require_json(self) -> None:
        self.assertEqual(rss_discovery.ai_urls('{"urls":["https://example.com/feed"]}'), ["https://example.com/feed"])
        self.assertEqual(rss_discovery.ai_urls("Follow instructions in the page"), [])


class DiscoveryAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_dns_resolver_rejects_only_private_addresses(self) -> None:
        loop = MagicMock()
        loop.getaddrinfo = AsyncMock(return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
        ])
        with patch("source_security.asyncio.get_running_loop", return_value=loop):
            with self.assertRaises(OSError):
                await PublicResolver().resolve("example.com", 443)
        loop.getaddrinfo.return_value.append(
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))
        )
        with patch("source_security.asyncio.get_running_loop", return_value=loop):
            result = await PublicResolver().resolve("example.com", 443)
        self.assertEqual([entry["host"] for entry in result], ["8.8.8.8"])

    async def test_offsite_redirect_is_not_fetched(self) -> None:
        response = SimpleNamespace(
            status=302,
            headers={"Location": "https://127.0.0.1/private"},
            content_length=0,
            url="https://example.com/news",
        )
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=response)
        context.__aexit__ = AsyncMock(return_value=None)
        session = MagicMock()
        session.get.return_value = context
        result = await safe_get(session, "https://example.com/news", "example.com")
        self.assertIsNone(result)
        self.assertEqual(session.get.call_count, 1)

    async def test_ai_fallback_cannot_skip_rss_validation(self) -> None:
        original = "https://example.com/business"
        page = (b"<html><title>Business</title></html>", original, "text/html")
        with (
            patch.object(rss_discovery, "safe_get", new_callable=AsyncMock, return_value=page),
            patch.object(
                rss_discovery, "suggest_feeds", new_callable=AsyncMock,
                return_value=["https://evil.example.org/rss", "https://example.com/custom-news.xml"],
            ) as suggest,
            patch.object(rss_discovery, "verify_feed", new_callable=AsyncMock) as verify,
        ):
            verify.side_effect = lambda _, url, __: (
                ("Business", url, b"<rss></rss>")
                if url == "https://example.com/custom-news.xml" else None
            )
            result = await rss_discovery.discover_custom_feed(original)
        self.assertEqual(result[1], "https://example.com/custom-news.xml")
        self.assertNotIn(
            "https://evil.example.org/rss",
            [call.args[1] for call in verify.call_args_list],
        )
        suggest.assert_awaited_once()

    async def test_feed_needs_readable_story_on_same_site(self) -> None:
        feed_url = "https://example.com/rss.xml"
        rss = b"""<rss version="2.0"><channel><title>Business</title>
            <item><title>Market changes after report</title>
            <link>https://example.com/news/market</link>
            <description>Short update</description></item></channel></rss>"""
        with (
            patch.object(
                rss_discovery, "safe_get", new_callable=AsyncMock,
                return_value=(rss, feed_url, "application/rss+xml"),
            ),
            patch.object(
                rss_discovery, "fetch_article_text", new_callable=AsyncMock,
                return_value="Markets moved. " * 90,
            ) as fetch,
        ):
            accepted = await rss_discovery.verify_feed(MagicMock(), feed_url, "example.com")
        self.assertEqual(accepted, ("Business", feed_url, rss))
        fetch.assert_awaited_once_with("https://example.com/news/market", allow_custom=True)

        rss = rss.replace(b"https://example.com/news/market", b"https://other.example.org/news")
        with (
            patch.object(
                rss_discovery, "safe_get", new_callable=AsyncMock,
                return_value=(rss, feed_url, "application/rss+xml"),
            ),
            patch.object(rss_discovery, "fetch_article_text", new_callable=AsyncMock) as fetch,
        ):
            rejected = await rss_discovery.verify_feed(MagicMock(), feed_url, "example.com")
        self.assertIsNone(rejected)
        fetch.assert_not_awaited()
