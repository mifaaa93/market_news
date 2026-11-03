"""Общие структуры бота."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

CATEGORIES = ("stocks", "oil", "macro", "crypto", "markets")


@dataclass(frozen=True)
class Article:
    id: int
    guid: str
    source_id: int
    source_name: str
    title: str
    title_norm: str
    summary: str
    body: str
    url: str
    category: str
    published_at: str
    fetched_at: str
    image_url: str = ""
    lang: str = "en"
    origin: str = "search"
    top_rank: int | None = None
    categories: tuple[str, ...] = ()
    telegram_photo_id: str = ""


@dataclass(frozen=True)
class Source:
    id: int
    name: str
    url: str
    lang: str
    extra: dict = field(default_factory=dict)
    article_count: int = 0
    headline_rank: int | None = None


@dataclass(frozen=True)
class User:
    user_id: int
    lang: str
    notifications: bool
    digest_hour: int
    timezone: str
    interactions: int
    full_reads: int
    premium_until: str | None
    last_digest_on: str | None
    blocked: bool
    plan: str = "base"
    subscribed_at: str | None = None

    def premium_active(self, now: datetime | None = None) -> bool:
        if self.plan not in {"plus", "pro"} and not self.premium_until:
            return False
        if not self.premium_until:
            return False
        moment = now or datetime.now(timezone.utc)
        try:
            until = datetime.fromisoformat(self.premium_until)
        except ValueError:
            return False
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        return until > moment

    def is_pro(self, now: datetime | None = None) -> bool:
        return self.plan == "pro" and self.premium_active(now)

    def active_plan(self, now: datetime | None = None) -> str:
        if self.premium_active(now):
            return self.plan
        return "base"
