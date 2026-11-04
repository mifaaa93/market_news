"""PostgreSQL: пользователи, источники GNews и лента."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import asyncpg

import config
from content import classify_topics, source_hash
from gnews import IncomingArticle
from models import CATEGORIES, Article, Source, User
from texts import interface_lang

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    lang TEXT NOT NULL DEFAULT 'ru',
    notifications BOOLEAN NOT NULL DEFAULT TRUE,
    digest_hour INTEGER NOT NULL DEFAULT 9,
    timezone TEXT NOT NULL DEFAULT 'Europe/Moscow',
    interactions INTEGER NOT NULL DEFAULT 0,
    full_reads INTEGER NOT NULL DEFAULT 0,
    premium_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    last_digest_on TEXT,
    blocked BOOLEAN NOT NULL DEFAULT FALSE,
    plan TEXT NOT NULL DEFAULT 'base',
    subscribed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS sources (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL DEFAULT '',
    lang TEXT NOT NULL DEFAULT 'en',
    extra JSONB NOT NULL DEFAULT '{}'::jsonb,
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    pin_order INTEGER
);

CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    guid TEXT NOT NULL UNIQUE,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    title_norm TEXT NOT NULL UNIQUE,
    summary TEXT NOT NULL,
    body TEXT NOT NULL,
    url TEXT NOT NULL,
    image_url TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL,
    lang TEXT NOT NULL DEFAULT 'en',
    published_at TIMESTAMPTZ NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL,
    origin TEXT NOT NULL DEFAULT 'search',
    top_rank INTEGER,
    telegram_photo_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source_id);
CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_top ON articles(top_rank);

CREATE TABLE IF NOT EXISTS article_topics (
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    PRIMARY KEY (article_id, category)
);
CREATE INDEX IF NOT EXISTS idx_article_topics_category ON article_topics(category);

CREATE TABLE IF NOT EXISTS translations (
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    lang TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    body TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (article_id, lang)
);

CREATE TABLE IF NOT EXISTS user_sources (
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (user_id, source_id)
);

CREATE TABLE IF NOT EXISTS seen (
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    opened_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, article_id)
);

CREATE TABLE IF NOT EXISTS payments (
    charge_id TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    amount INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS article_pushes (
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    sent_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, article_id)
);

CREATE TABLE IF NOT EXISTS admin_actions (
    id SERIAL PRIMARY KEY,
    admin_user_id BIGINT NOT NULL,
    target_user_id BIGINT NOT NULL,
    action TEXT NOT NULL,
    plan TEXT,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS api_quota (
    day DATE PRIMARY KEY,
    used INTEGER NOT NULL
);
"""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    moment = value
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_dt(value: str) -> datetime:
    if value.endswith("Z"):
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


async def _init_connection(conn: asyncpg.Connection) -> None:
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


class Database:
    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or config.DATABASE_URL
        self._pool: asyncpg.Pool | None = None

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("database is not connected")
        return self._pool

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(
            dsn=self.dsn,
            min_size=1,
            max_size=8,
            init=_init_connection,
        )
        async with self.pool.acquire() as conn:
            await conn.execute(_SCHEMA)
            await conn.execute(
                "ALTER TABLE articles ADD COLUMN IF NOT EXISTS origin TEXT NOT NULL DEFAULT 'search'"
            )
            await conn.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS top_rank INTEGER")
            await conn.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS telegram_photo_id TEXT")
            await conn.execute("ALTER TABLE sources ADD COLUMN IF NOT EXISTS pin_order INTEGER")
        await self.backfill_topics()
        await self.backfill_pins()

    async def reset_all(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                DROP TABLE IF EXISTS article_topics, translations, article_pushes, seen, user_sources,
                    articles, sources, payments, admin_actions, api_quota, meta, users CASCADE
                """
            )
            await conn.execute(_SCHEMA)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def upsert_user(
        self,
        user_id: int,
        username: str | None,
        first_name: str | None,
        language_code: str | None = None,
    ) -> User:
        lang = interface_lang(language_code)
        now = utc_now()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO users (
                    user_id, username, first_name, lang, notifications, digest_hour,
                    timezone, interactions, full_reads, premium_until, created_at,
                    last_digest_on, blocked, plan
                ) VALUES ($1, $2, $3, $4, TRUE, $5, $6, 0, 0, NULL, $7, NULL, FALSE, 'base')
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    blocked = FALSE
                RETURNING *, (xmax = 0) AS inserted
                """,
                user_id,
                username,
                first_name,
                lang,
                config.DEFAULT_HOUR,
                config.DEFAULT_TZ,
                now,
            )
        user = _user(row)
        if row["inserted"]:
            await self.ensure_default_sources(user)
        return user

    async def get_user(self, user_id: int) -> User | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
        return _user(row) if row else None

    async def require_user(self, user_id: int) -> User:
        user = await self.get_user(user_id)
        if user is None:
            raise LookupError(user_id)
        return user

    async def _fetch_user_after(self, conn: asyncpg.Connection, user_id: int) -> User:
        row = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
        if row is None:
            raise LookupError(user_id)
        return _user(row)

    async def set_lang(self, user_id: int, lang: str) -> User:
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET lang=$1 WHERE user_id=$2", lang, user_id)
            return await self._fetch_user_after(conn, user_id)

    async def set_notifications(self, user_id: int, enabled: bool) -> User:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET notifications=$1 WHERE user_id=$2",
                enabled,
                user_id,
            )
            return await self._fetch_user_after(conn, user_id)

    async def set_hour(self, user_id: int, hour: int) -> User:
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET digest_hour=$1 WHERE user_id=$2", hour, user_id)
            return await self._fetch_user_after(conn, user_id)

    async def set_timezone(self, user_id: int, zone: str) -> User:
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET timezone=$1 WHERE user_id=$2", zone, user_id)
            return await self._fetch_user_after(conn, user_id)

    async def add_interaction(self, user_id: int, *, full_read: bool = False) -> User:
        async with self.pool.acquire() as conn:
            if full_read:
                await conn.execute(
                    """
                    UPDATE users
                    SET interactions = interactions + 1, full_reads = full_reads + 1
                    WHERE user_id=$1
                    """,
                    user_id,
                )
            else:
                await conn.execute(
                    "UPDATE users SET interactions = interactions + 1 WHERE user_id=$1",
                    user_id,
                )
            return await self._fetch_user_after(conn, user_id)

    async def mark_seen(self, user_id: int, article_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO seen (user_id, article_id, opened_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, article_id) DO NOTHING
                """,
                user_id,
                article_id,
                utc_now(),
            )

    async def count_seen(self, user_id: int) -> int:
        async with self.pool.acquire() as conn:
            value = await conn.fetchval("SELECT COUNT(*) FROM seen WHERE user_id=$1", user_id)
        return int(value or 0)

    async def count_articles(self, lang: str | None = None) -> int:
        async with self.pool.acquire() as conn:
            if lang:
                value = await conn.fetchval("SELECT COUNT(*) FROM articles WHERE lang=$1", lang)
            else:
                value = await conn.fetchval("SELECT COUNT(*) FROM articles")
        return int(value or 0)

    async def category_counts(self, user_id: int) -> dict[str, int]:
        enabled = await self.enabled_source_ids(user_id)
        if not enabled:
            return {}
        user = await self.require_user(user_id)
        params: list[object] = [enabled]
        ready = self._ready_sql(user.lang, params)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT t.category, COUNT(*) AS n
                FROM article_topics t
                JOIN articles a ON a.id = t.article_id
                WHERE a.source_id = ANY($1::int[]){ready}
                GROUP BY t.category
                """,
                *params,
            )
        return {str(row["category"]): int(row["n"]) for row in rows}

    async def upsert_source(
        self,
        conn: asyncpg.Connection,
        *,
        name: str,
        url: str,
        lang: str,
        extra: dict,
        seen_at: datetime,
    ) -> int:
        pin_order = config.source_pin_order(name, url)
        row = await conn.fetchrow(
            """
            INSERT INTO sources (name, url, lang, extra, first_seen_at, last_seen_at, pin_order)
            VALUES ($1, $2, $3, $4::jsonb, $5, $5, $6)
            ON CONFLICT (name) DO UPDATE SET
                url = CASE WHEN EXCLUDED.url <> '' THEN EXCLUDED.url ELSE sources.url END,
                extra = CASE
                    WHEN EXCLUDED.extra = '{}'::jsonb THEN sources.extra
                    ELSE EXCLUDED.extra
                END,
                last_seen_at = EXCLUDED.last_seen_at,
                pin_order = EXCLUDED.pin_order
            RETURNING id
            """,
            name,
            url,
            lang,
            extra,
            seen_at,
            pin_order,
        )
        return int(row["id"])

    async def backfill_pins(self) -> None:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, name, url FROM sources")
            for row in rows:
                order = config.source_pin_order(str(row["name"]), str(row["url"] or ""))
                await conn.execute(
                    "UPDATE sources SET pin_order=$1 WHERE id=$2",
                    order,
                    int(row["id"]),
                )

    async def ingest_articles(self, items: list[IncomingArticle]) -> int:
        if not items:
            return 0
        saved = 0
        now = utc_now()
        async with self.pool.acquire() as conn:
            for item in items:
                source_id = await self.upsert_source(
                    conn,
                    name=item.source_name,
                    url=item.source_url,
                    lang=item.lang,
                    extra=item.source_extra,
                    seen_at=now,
                )
                published = _parse_dt(item.published_at)
                origin = item.origin if item.origin in {"search", "top"} else "search"
                try:
                    row = await conn.fetchrow(
                        """
                        INSERT INTO articles (
                            guid, source_id, title, title_norm, summary, body, url,
                            image_url, category, lang, published_at, fetched_at, first_seen_at,
                            origin, top_rank
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $12, $13, $14
                        )
                        ON CONFLICT (guid) DO NOTHING
                        RETURNING id
                        """,
                        item.guid,
                        source_id,
                        item.title,
                        item.title_norm,
                        item.summary,
                        item.body,
                        item.url,
                        item.image_url,
                        item.category,
                        item.lang,
                        published,
                        now,
                        origin,
                        item.top_rank,
                    )
                    if row is None:
                        continue
                    await self._replace_topics(
                        conn, int(row["id"]), item.categories or (item.category,)
                    )
                    saved += 1
                except asyncpg.UniqueViolationError:
                    continue
        return saved

    async def _replace_topics(
        self, conn: asyncpg.Connection, article_id: int, categories: tuple[str, ...] | list[str]
    ) -> None:
        cats = [category for category in categories if category in CATEGORIES]
        if not cats:
            cats = ["markets"]
        await conn.execute("DELETE FROM article_topics WHERE article_id=$1", article_id)
        await conn.executemany(
            "INSERT INTO article_topics(article_id, category) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            [(article_id, category) for category in cats],
        )

    async def backfill_topics(self) -> None:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT a.id, a.title, a.summary, a.body
                FROM articles a
                LEFT JOIN article_topics t ON t.article_id = a.id
                WHERE t.article_id IS NULL
                """
            )
            for row in rows:
                topics = classify_topics(row["title"], f"{row['summary']}\n{row['body']}")
                await self._replace_topics(conn, int(row["id"]), topics)
                await conn.execute(
                    "UPDATE articles SET category=$1 WHERE id=$2",
                    topics[0],
                    int(row["id"]),
                )

    async def replace_top(self, lang: str, items: list[IncomingArticle]) -> int:
        saved = await self.ingest_articles(items)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("UPDATE articles SET top_rank=NULL")
                for item in items:
                    if item.top_rank is None:
                        continue
                    await conn.execute(
                        """
                        UPDATE articles
                        SET origin='top', top_rank=$1
                        WHERE guid=$2
                        """,
                        item.top_rank,
                        item.guid,
                    )
        await self.meta_set("fetched_top_at", utc_now_iso())
        return saved

    def _ready_sql(self, lang: str | None, params: list[object]) -> str:
        if lang not in config.TRANSLATION_LANGS:
            return ""
        params.append(lang)
        return (
            " AND EXISTS (SELECT 1 FROM translations x"
            f" WHERE x.article_id = a.id AND x.lang=${len(params)})"
        )

    async def list_top(self, lang: str | None = None, limit: int = 10) -> list[Article]:
        params: list[object] = []
        ready = self._ready_sql(lang, params)
        params.append(limit)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT a.*, s.name AS source_name,
                       COALESCE((
                           SELECT array_agg(t.category)
                           FROM article_topics t
                           WHERE t.article_id = a.id
                       ), ARRAY[a.category]) AS topics
                FROM articles a
                JOIN sources s ON s.id = a.source_id
                WHERE a.top_rank IS NOT NULL{ready}
                ORDER BY a.top_rank ASC, a.id ASC
                LIMIT ${len(params)}
                """,
                *params,
            )
        items = [_article(row) for row in rows]
        if lang:
            return await self.apply_translations(items, lang)
        return items

    async def headline_publisher_names(self, limit: int = 12) -> list[str]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT s.name
                FROM sources s
                JOIN articles a ON a.source_id = s.id AND a.top_rank IS NOT NULL
                GROUP BY s.id, s.name
                ORDER BY MIN(a.top_rank) ASC, s.name
                LIMIT $1
                """,
                limit,
            )
        return [str(row["name"]) for row in rows]

    async def source(self, source_id: int) -> Source | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT s.*, COUNT(a.id) AS article_count
                FROM sources s
                LEFT JOIN articles a ON a.source_id = s.id
                WHERE s.id=$1
                GROUP BY s.id
                """,
                source_id,
            )
        return _source(row) if row else None

    async def list_sources_page(
        self, lang: str | None = None, *, offset: int, limit: int
    ) -> tuple[list[Source], int]:
        async with self.pool.acquire() as conn:
            total = int(await conn.fetchval("SELECT COUNT(*) FROM sources") or 0)
            rows = await conn.fetch(
                """
                SELECT s.*,
                       COUNT(a.id) AS article_count,
                       s.pin_order AS headline_rank
                FROM sources s
                LEFT JOIN articles a ON a.source_id = s.id
                GROUP BY s.id
                ORDER BY s.pin_order NULLS LAST, COUNT(a.id) DESC, s.name
                OFFSET $1 LIMIT $2
                """,
                offset,
                limit,
            )
        return [_source(row) for row in rows], total

    async def count_sources(self, lang: str | None = None) -> int:
        async with self.pool.acquire() as conn:
            value = await conn.fetchval("SELECT COUNT(*) FROM sources")
        return int(value or 0)

    async def top_sources(self, lang: str | None = None, limit: int = 5) -> list[Source]:
        sources, _ = await self.list_sources_page(None, offset=0, limit=limit)
        return sources

    async def sources_by_names(self, lang: str, names: list[str]) -> list[Source]:
        if not names:
            return []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT s.*, COUNT(a.id) AS article_count
                FROM sources s
                LEFT JOIN articles a ON a.source_id = s.id
                WHERE s.lang=$1 AND s.name = ANY($2::text[])
                GROUP BY s.id
                """,
                lang,
                names,
            )
        by_name = {row["name"]: _source(row) for row in rows}
        return [by_name[name] for name in names if name in by_name]

    async def enabled_source_ids(self, user_id: int) -> list[int]:
        user = await self.require_user(user_id)
        limit = await self.source_limits(user.active_plan())
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT us.source_id
                FROM user_sources us
                JOIN sources s ON s.id = us.source_id
                LEFT JOIN articles a ON a.source_id = s.id
                WHERE us.user_id=$1 AND us.enabled
                GROUP BY us.source_id
                ORDER BY MIN(s.pin_order) NULLS LAST, COUNT(a.id) DESC, MIN(s.name)
                LIMIT $2
                """,
                user_id,
                limit,
            )
        return [int(row["source_id"]) for row in rows]

    async def enabled_source_names(self, user_id: int, lang: str) -> list[str]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT s.name
                FROM user_sources us
                JOIN sources s ON s.id = us.source_id
                WHERE us.user_id=$1 AND us.enabled AND s.lang=$2
                ORDER BY s.name
                """,
                user_id,
                lang,
            )
        return [str(row["name"]) for row in rows]

    async def source_has_choice(self, user_id: int, lang: str | None = None) -> bool:
        async with self.pool.acquire() as conn:
            value = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM user_sources WHERE user_id=$1)",
                user_id,
            )
        return bool(value)

    async def search_sources(self, query: str, limit: int = 8) -> list[Source]:
        from content import source_search_terms

        needle, host = source_search_terms(query)
        if len(needle) < 2 and not host:
            return []
        pattern = f"%{needle}%"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT s.*,
                       COUNT(a.id) AS article_count,
                       s.pin_order AS headline_rank
                FROM sources s
                LEFT JOIN articles a ON a.source_id = s.id
                WHERE s.name ILIKE $1
                   OR s.url ILIKE $1
                   OR ($2::text IS NOT NULL AND s.url ILIKE '%' || $2 || '%')
                GROUP BY s.id
                ORDER BY s.pin_order NULLS LAST, COUNT(a.id) DESC, s.name
                LIMIT $3
                """,
                pattern,
                host,
                limit,
            )
        return [_source(row) for row in rows]

    async def disable_all_sources(self, user_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE user_sources SET enabled=FALSE WHERE user_id=$1",
                user_id,
            )

    async def enable_headline_sources(self, user_id: int, limit: int) -> None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "UPDATE user_sources SET enabled=FALSE WHERE user_id=$1",
                    user_id,
                )
                rows = await conn.fetch(
                    """
                    SELECT s.id
                    FROM sources s
                    WHERE s.pin_order IS NOT NULL
                    ORDER BY s.pin_order ASC, s.name
                    LIMIT $1
                    """,
                    limit,
                )
        for row in rows:
            await self.set_source_enabled(user_id, int(row["id"]), True)

    async def add_headline_sources(self, user_id: int, limit: int) -> None:
        enabled = list(await self.enabled_source_ids(user_id))
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT s.id
                FROM sources s
                WHERE s.pin_order IS NOT NULL
                ORDER BY s.pin_order ASC, s.name
                """
            )
        for row in rows:
            source_id = int(row["id"])
            if source_id in enabled:
                continue
            if len(enabled) >= limit:
                break
            await self.set_source_enabled(user_id, source_id, True)
            enabled.append(source_id)

    async def set_source_enabled(self, user_id: int, source_id: int, enabled: bool) -> None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO user_sources(user_id, source_id, enabled)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id, source_id) DO UPDATE SET enabled=EXCLUDED.enabled
                    """,
                    user_id,
                    source_id,
                    enabled,
                )
                if enabled:
                    await conn.execute(
                        """
                        INSERT INTO article_pushes(user_id, article_id, sent_at)
                        SELECT $1, id, $3
                        FROM articles
                        WHERE source_id=$2
                        ON CONFLICT DO NOTHING
                        """,
                        user_id,
                        source_id,
                        utc_now(),
                    )

    async def source_states(self, user_id: int, source_ids: list[int]) -> dict[int, bool]:
        enabled = set(await self.enabled_source_ids(user_id))
        return {source_id: source_id in enabled for source_id in source_ids}

    async def active_sources(self, user_id: int) -> list[Source]:
        ids = await self.enabled_source_ids(user_id)
        if not ids:
            return []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT s.*, COUNT(a.id) AS article_count
                FROM sources s
                LEFT JOIN articles a ON a.source_id = s.id
                WHERE s.id = ANY($1::int[])
                GROUP BY s.id
                ORDER BY COUNT(a.id) DESC, s.name
                """,
                ids,
            )
        return [_source(row) for row in rows]

    async def source_limits(self, plan: str) -> int:
        return config.source_limit_for(plan)

    async def ensure_default_sources(self, user: User) -> None:
        if await self.source_has_choice(user.user_id):
            return
        limit = await self.source_limits(user.active_plan())
        top = await self.top_sources(limit=limit)
        for source in top:
            await self.set_source_enabled(user.user_id, source.id, True)

    async def remap_sources(self, user_id: int, names: list[str], new_lang: str, plan: str) -> None:
        if await self.source_has_choice(user_id, new_lang):
            return
        matched = await self.sources_by_names(new_lang, names)
        limit = await self.source_limits(plan)
        for source in matched[:limit]:
            await self.set_source_enabled(user_id, source.id, True)
        if matched:
            return
        user = await self.require_user(user_id)
        await self.ensure_default_sources(user)

    async def seed_missing_feeds(self) -> None:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT u.*
                FROM users u
                WHERE NOT EXISTS (
                    SELECT 1 FROM user_sources us WHERE us.user_id = u.user_id
                )
                """
            )
        for row in rows:
            await self.ensure_default_sources(_user(row))

    async def list_push_subscribers(self, article: Article) -> list[User]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT u.*
                FROM users u
                JOIN user_sources us
                    ON us.user_id = u.user_id AND us.source_id = $1 AND us.enabled
                WHERE u.blocked = FALSE
                  AND u.plan IN ('plus', 'pro')
                """,
                article.source_id,
            )
        return [user for user in (_user(row) for row in rows) if user.premium_active()]

    async def push_already_sent(self, user_id: int, article_id: int) -> bool:
        async with self.pool.acquire() as conn:
            value = await conn.fetchval(
                "SELECT 1 FROM article_pushes WHERE user_id=$1 AND article_id=$2",
                user_id,
                article_id,
            )
        return value is not None

    async def mark_push_sent(self, user_id: int, article_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO article_pushes(user_id, article_id, sent_at)
                VALUES ($1, $2, $3)
                ON CONFLICT DO NOTHING
                """,
                user_id,
                article_id,
                utc_now(),
            )

    async def articles_since(self, stamp: str) -> list[Article]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT a.*, s.name AS source_name,
                       COALESCE((
                           SELECT array_agg(t.category)
                           FROM article_topics t
                           WHERE t.article_id = a.id
                       ), ARRAY[a.category]) AS topics
                FROM articles a
                JOIN sources s ON s.id = a.source_id
                WHERE a.first_seen_at > $1
                ORDER BY a.published_at DESC, a.id DESC
                """,
                _parse_dt(stamp),
            )
        return [_article(row) for row in rows]

    async def recent(self, limit: int, *, lang: str | None = None) -> list[Article]:
        return await self.recent_for_user(None, limit, lang=lang)

    async def recent_for_user(
        self, user_id: int | None, limit: int, *, lang: str | None = None
    ) -> list[Article]:
        params: list[object] = []
        where = []
        user = None
        if user_id is not None:
            user = await self.require_user(user_id)
            enabled = await self.enabled_source_ids(user_id)
            if not enabled:
                return []
            where.append("a.source_id = ANY($%d::int[])" % (len(params) + 1))
            params.append(enabled)
        ready_lang = user.lang if user is not None else lang
        ready = self._ready_sql(ready_lang, params)
        if ready:
            where.append(ready.removeprefix(" AND "))
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        params.append(limit)
        sql = f"""
            SELECT a.*, s.name AS source_name,
                       COALESCE((
                           SELECT array_agg(t.category)
                           FROM article_topics t
                           WHERE t.article_id = a.id
                       ), ARRAY[a.category]) AS topics
            FROM articles a
            JOIN sources s ON s.id = a.source_id
            {clause}
            ORDER BY a.published_at DESC, a.id DESC
            LIMIT ${len(params)}
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
        items = [_article(row) for row in rows]
        if user is not None:
            return await self.apply_translations(items, user.lang)
        if lang:
            return await self.apply_translations(items, lang)
        return items

    async def by_category(
        self,
        category: str,
        limit: int,
        *,
        user_id: int | None = None,
    ) -> list[Article]:
        params: list[object] = [category]
        extra = ""
        user = None
        if user_id is not None:
            user = await self.require_user(user_id)
            enabled = await self.enabled_source_ids(user_id)
            if not enabled:
                return []
            extra = " AND a.source_id = ANY($2::int[])"
            params.append(enabled)
        extra += self._ready_sql(user.lang if user is not None else None, params)
        params.append(limit)
        sql = f"""
            SELECT a.*, s.name AS source_name,
                       COALESCE((
                           SELECT array_agg(t.category)
                           FROM article_topics t
                           WHERE t.article_id = a.id
                       ), ARRAY[a.category]) AS topics
            FROM articles a
            JOIN sources s ON s.id = a.source_id
            JOIN article_topics tp ON tp.article_id = a.id AND tp.category=$1
            WHERE TRUE{extra}
            ORDER BY a.published_at DESC, a.id DESC
            LIMIT ${len(params)}
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
        items = [_article(row) for row in rows]
        if user is not None:
            return await self.apply_translations(items, user.lang)
        return items

    async def get_article(self, article_id: int) -> Article | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT a.*, s.name AS source_name,
                       COALESCE((
                           SELECT array_agg(t.category)
                           FROM article_topics t
                           WHERE t.article_id = a.id
                       ), ARRAY[a.category]) AS topics
                FROM articles a
                JOIN sources s ON s.id = a.source_id
                WHERE a.id=$1
                """,
                article_id,
            )
        article = _article(row) if row else None
        return article

    async def articles_missing_photo(self, limit: int) -> list[Article]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT a.*, s.name AS source_name,
                       COALESCE((
                           SELECT array_agg(t.category)
                           FROM article_topics t
                           WHERE t.article_id = a.id
                       ), ARRAY[a.category]) AS topics
                FROM articles a
                JOIN sources s ON s.id = a.source_id
                WHERE a.image_url <> '' AND a.telegram_photo_id IS NULL
                ORDER BY a.top_rank NULLS LAST, a.published_at DESC, a.id DESC
                LIMIT $1
                """,
                limit,
            )
        return [_article(row) for row in rows]

    async def save_photo_id(self, article_id: int, file_id: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE articles SET telegram_photo_id=$1 WHERE id=$2",
                file_id,
                article_id,
            )

    async def translation_hashes(self, lang: str, article_ids: list[int]) -> dict[int, str]:
        if not article_ids:
            return {}
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT article_id, source_hash
                FROM translations
                WHERE lang=$1 AND article_id = ANY($2::int[])
                """,
                lang,
                article_ids,
            )
        return {int(row["article_id"]): str(row["source_hash"]) for row in rows}

    async def articles_missing_translation(self, lang: str, limit: int) -> list[Article]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT a.*, s.name AS source_name,
                       COALESCE((
                           SELECT array_agg(t.category)
                           FROM article_topics t
                           WHERE t.article_id = a.id
                       ), ARRAY[a.category]) AS topics
                FROM articles a
                JOIN sources s ON s.id = a.source_id
                LEFT JOIN translations t ON t.article_id = a.id AND t.lang = $1
                WHERE t.article_id IS NULL
                ORDER BY a.top_rank NULLS LAST, a.published_at DESC, a.id DESC
                LIMIT $2
                """,
                lang,
                limit,
            )
        missing = [_article(row) for row in rows]
        if len(missing) >= limit:
            return missing
        seen = {article.id for article in missing}
        recent = await self.recent(80)
        hashes = await self.translation_hashes(lang, [article.id for article in recent])
        for article in recent:
            if len(missing) >= limit or article.id in seen:
                continue
            if hashes.get(article.id) != source_hash(article):
                missing.append(article)
                seen.add(article.id)
        return missing

    async def save_translations(
        self, lang: str, rows: list[tuple[Article, str, str, str, tuple[str, ...]]]
    ) -> None:
        now = utc_now()
        async with self.pool.acquire() as conn:
            for article, title, summary, body, topics in rows:
                await conn.execute(
                    """
                    INSERT INTO translations (
                        article_id, lang, title, summary, body, source_hash, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (article_id, lang) DO UPDATE SET
                        title=EXCLUDED.title,
                        summary=EXCLUDED.summary,
                        body=EXCLUDED.body,
                        source_hash=EXCLUDED.source_hash,
                        created_at=EXCLUDED.created_at
                    """,
                    article.id,
                    lang,
                    title,
                    summary,
                    body,
                    source_hash(article),
                    now,
                )
                if topics:
                    await self._replace_topics(conn, article.id, topics)
                    await conn.execute(
                        "UPDATE articles SET category=$1 WHERE id=$2",
                        topics[0],
                        article.id,
                    )

    async def apply_translations(self, articles: list[Article], lang: str) -> list[Article]:
        if lang not in config.TRANSLATION_LANGS or not articles:
            return articles
        hashes = await self.translation_hashes(lang, [article.id for article in articles if article.id])
        if not hashes:
            return []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT article_id, title, summary, body, source_hash
                FROM translations
                WHERE lang=$1 AND article_id = ANY($2::int[])
                """,
                lang,
                list(hashes.keys()),
            )
        by_id = {int(row["article_id"]): row for row in rows}
        localized: list[Article] = []
        for article in articles:
            row = by_id.get(article.id)
            if row is None or str(row["source_hash"]) != source_hash(article):
                continue
            localized.append(
                replace(
                    article,
                    title=str(row["title"] or article.title),
                    summary=str(row["summary"] or article.summary),
                    body=str(row["body"] or article.body),
                )
            )
        return localized

    async def delete_old(self, days: int) -> int:
        cutoff = utc_now() - timedelta(days=days)
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM articles WHERE published_at < $1",
                cutoff,
            )
        return int(result.split()[-1]) if result.startswith("DELETE") else 0

    async def meta_get(self, key: str) -> str | None:
        async with self.pool.acquire() as conn:
            value = await conn.fetchval("SELECT value FROM meta WHERE key=$1", key)
        return str(value) if value is not None else None

    async def meta_set(self, key: str, value: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO meta (key, value) VALUES ($1, $2)
                ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value
                """,
                key,
                value,
            )

    async def quota_used_today(self) -> int:
        async with self.pool.acquire() as conn:
            value = await conn.fetchval(
                "SELECT used FROM api_quota WHERE day = CURRENT_DATE"
            )
        return int(value or 0)

    async def quota_remaining(self) -> int:
        return max(0, config.GNEWS_DAILY_LIMIT - await self.quota_used_today())

    async def quota_consume(self, n: int = 1) -> bool:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO api_quota(day, used) VALUES (CURRENT_DATE, $1)
                ON CONFLICT (day) DO UPDATE SET used = api_quota.used + EXCLUDED.used
                WHERE api_quota.used + EXCLUDED.used <= $2
                RETURNING used
                """,
                n,
                config.GNEWS_DAILY_LIMIT,
            )
        return row is not None

    async def list_digest_subscribers(self) -> list[User]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM users WHERE notifications=TRUE AND blocked=FALSE"
            )
        return [_user(row) for row in rows]

    async def mark_digest_sent(self, user_id: int, day: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_digest_on=$1 WHERE user_id=$2",
                day,
                user_id,
            )

    async def set_blocked(self, user_id: int, blocked: bool) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET blocked=$1 WHERE user_id=$2",
                blocked,
                user_id,
            )

    async def save_payment(self, charge_id: str, user_id: int, amount: int) -> bool:
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO payments (charge_id, user_id, amount, created_at)
                    VALUES ($1, $2, $3, $4)
                    """,
                    charge_id,
                    user_id,
                    amount,
                    utc_now(),
                )
            return True
        except asyncpg.UniqueViolationError:
            return False

    async def extend_premium(self, user_id: int, days: int) -> User:
        return await self.extend_plan(user_id, "plus", days)

    async def extend_plan(self, user_id: int, plan: str, days: int) -> User:
        user = await self.require_user(user_id)
        first_paid = user.active_plan() == "base" and plan in {"plus", "pro"}
        now = utc_now()
        base = now
        if user.premium_active(now) and user.premium_until:
            parsed = datetime.fromisoformat(user.premium_until)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            base = parsed
        until = (base + timedelta(days=days)).astimezone(timezone.utc)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users
                SET premium_until=$1, plan=$2, subscribed_at=COALESCE(subscribed_at, $3)
                WHERE user_id=$4
                """,
                until,
                plan,
                now,
                user_id,
            )
            updated = await self._fetch_user_after(conn, user_id)
        if first_paid:
            await self.add_headline_sources(user_id, await self.source_limits(plan))
        return updated

    async def revoke_plan(self, user_id: int) -> User:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET plan='base', premium_until=NULL WHERE user_id=$1",
                user_id,
            )
            return await self._fetch_user_after(conn, user_id)

    async def record_admin_action(
        self, admin_user_id: int, target_user_id: int, action: str, plan: str | None = None
    ) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO admin_actions(admin_user_id, target_user_id, action, plan, created_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                admin_user_id,
                target_user_id,
                action,
                plan,
                utc_now(),
            )

    async def admin_grant(self, admin_user_id: int, user_id: int, plan: str, days: int) -> User:
        if admin_user_id != config.ADMIN_USER_ID:
            raise PermissionError("subscription admin only")
        if plan not in {"plus", "pro"} or not 1 <= days <= 365:
            raise ValueError("invalid subscription")
        if await self.get_user(user_id) is None:
            await self.upsert_user(user_id, None, None)
        user = await self.extend_plan(user_id, plan, days)
        await self.record_admin_action(admin_user_id, user_id, f"grant_{days}d", plan)
        return user

    async def admin_revoke(self, admin_user_id: int, user_id: int) -> User:
        if admin_user_id != config.ADMIN_USER_ID:
            raise PermissionError("subscription admin only")
        user = await self.revoke_plan(user_id)
        await self.record_admin_action(admin_user_id, user_id, "revoke", None)
        return user

    async def admin_stats(self) -> dict:
        async with self.pool.acquire() as conn:
            articles = int(await conn.fetchval("SELECT COUNT(*) FROM articles") or 0)
            today = int(
                await conn.fetchval(
                    "SELECT COUNT(*) FROM articles WHERE first_seen_at::date = CURRENT_DATE"
                )
                or 0
            )
            cat_rows = await conn.fetch(
                """
                SELECT COALESCE(t.category, a.category) AS category, COUNT(*) AS n
                FROM articles a
                LEFT JOIN article_topics t ON t.article_id = a.id
                GROUP BY COALESCE(t.category, a.category)
                ORDER BY COUNT(*) DESC
                """
            )
            users = int(await conn.fetchval("SELECT COUNT(*) FROM users") or 0)
            picks = int(
                await conn.fetchval(
                    "SELECT COUNT(*) FROM user_sources WHERE enabled"
                )
                or 0
            )
            catalog = int(await conn.fetchval("SELECT COUNT(*) FROM sources") or 0)
        return {
            "articles": articles,
            "today": today,
            "categories": [(str(row["category"]), int(row["n"])) for row in cat_rows],
            "users": users,
            "picks": picks,
            "catalog": catalog,
        }


def _user(row: asyncpg.Record) -> User:
    return User(
        user_id=int(row["user_id"]),
        lang=row["lang"] or "ru",
        notifications=bool(row["notifications"]),
        digest_hour=int(row["digest_hour"]),
        timezone=row["timezone"],
        interactions=int(row["interactions"]),
        full_reads=int(row["full_reads"]),
        premium_until=_iso(row["premium_until"]),
        last_digest_on=str(row["last_digest_on"]) if row["last_digest_on"] else None,
        blocked=bool(row["blocked"]),
        plan=str(row["plan"] or "base"),
        subscribed_at=_iso(row["subscribed_at"]),
    )


def _topics(row: asyncpg.Record) -> tuple[str, ...]:
    if "topics" in row.keys() and row["topics"]:
        values = [str(item) for item in row["topics"] if item]
        if values:
            return tuple(values)
    category = str(row["category"]) if "category" in row.keys() else "markets"
    return (category,)


def _pin_rank(row: asyncpg.Record) -> int | None:
    for key in ("headline_rank", "pin_order"):
        if key in row.keys() and row[key] is not None:
            return int(row[key])
    return None


def _source(row: asyncpg.Record) -> Source:
    extra = row["extra"] or {}
    if isinstance(extra, str):
        extra = json.loads(extra)
    return Source(
        id=int(row["id"]),
        name=str(row["name"]),
        url=str(row["url"] or ""),
        lang=str(row["lang"]),
        extra=extra if isinstance(extra, dict) else {},
        article_count=int(row["article_count"]) if "article_count" in row.keys() else 0,
        headline_rank=_pin_rank(row),
    )


def _article(row: asyncpg.Record) -> Article:
    return Article(
        id=int(row["id"]),
        guid=row["guid"],
        source_id=int(row["source_id"]),
        source_name=str(row["source_name"]),
        title=row["title"],
        title_norm=row["title_norm"],
        summary=row["summary"],
        body=row["body"],
        url=row["url"],
        image_url=row["image_url"] or "",
        category=row["category"],
        published_at=_iso(row["published_at"]) or "",
        fetched_at=_iso(row["fetched_at"]) or "",
        lang=str(row["lang"]),
        origin=str(row["origin"]) if "origin" in row.keys() and row["origin"] else "search",
        top_rank=int(row["top_rank"]) if "top_rank" in row.keys() and row["top_rank"] is not None else None,
        categories=_topics(row),
        telegram_photo_id=(
            str(row["telegram_photo_id"])
            if "telegram_photo_id" in row.keys() and row["telegram_photo_id"]
            else ""
        ),
    )
