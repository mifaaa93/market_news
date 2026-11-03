"""Guard outgoing requests to user-supplied websites and discovered feeds."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import aiohttp

BLOCKED = (
    "t.me", "telegram.me", "bit.ly", "tinyurl.com", "t.co", "instagram.com",
    "facebook.com", "twitter.com", "x.com", "tiktok.com", "youtube.com",
    "youtu.be", "vk.com", "ok.ru", "wa.me",
)


def public_site(url: str) -> bool:
    if not isinstance(url, str) or len(url) > 2048:
        return False
    try:
        parts = urlsplit(url.strip())
        host = (parts.hostname or "").lower().rstrip(".")
        port = parts.port
    except ValueError:
        return False
    if (
        parts.scheme != "https" or not host or "." not in host
        or parts.username or parts.password or port not in (None, 443)
        or any(
            host == item or host.endswith("." + item)
            or (item in ("t.me", "x.com") and host.endswith(item))
            for item in BLOCKED
        )
        or host.endswith((".localhost", ".local", ".internal", ".test", ".invalid", ".onion"))
    ):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return True


def same_site(url: str, original_host: str) -> bool:
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    base = original_host.lower().removeprefix("www.").rstrip(".")
    if not base or not host:
        return False
    # ABC serves its official RSS via feeds.abcnews.com, then redirects to
    # abcnews.go.com; both are publisher-owned, but arbitrary go.com is not.
    if base == "abcnews.go.com" or base == "abcnews.com" or base.endswith(".abcnews.com"):
        return host == "abcnews.go.com" or host == "abcnews.com" or host.endswith(".abcnews.com")
    return (
        host == base
        or host == "www." + base
        or host.endswith("." + base)
    )


class PublicResolver(aiohttp.abc.AbstractResolver):
    """Filter resolved IPs, so public hostnames cannot redirect DNS to LAN."""

    async def resolve(self, host: str, port: int = 0, family: int = socket.AF_INET) -> list[dict]:
        addresses = await asyncio.get_running_loop().getaddrinfo(
            host, port, family=family, type=socket.SOCK_STREAM
        )
        result = [
            {
                "hostname": host, "host": entry[4][0], "port": entry[4][1],
                "family": entry[0], "proto": entry[2], "flags": socket.AI_NUMERICHOST,
            }
            for entry in addresses
            if ipaddress.ip_address(entry[4][0]).is_global
        ]
        if not result:
            raise OSError("no public address for source host")
        return result

    async def close(self) -> None:
        pass


async def safe_get(
    session: aiohttp.ClientSession, url: str, site_host: str, *,
    max_bytes: int = 1_000_000, accept: str | None = None,
) -> tuple[bytes, str, str] | None:
    """Allow only same-site HTTPS redirects and bounded responses."""
    target = url
    for _ in range(4):
        if not public_site(target) or not same_site(target, site_host):
            return None
        headers = {"Accept": accept} if accept else None
        async with session.get(target, allow_redirects=False, headers=headers) as response:
            if response.status in (301, 302, 303, 307, 308):
                location = response.headers.get("Location", "")
                if not location:
                    return None
                target = urljoin(target, location)
                continue
            if response.status != 200 or (response.content_length or 0) > max_bytes:
                return None
            data = await response.content.read(max_bytes + 1)
            if len(data) > max_bytes:
                return None
            return data, str(response.url), response.headers.get("Content-Type", "")
    return None
