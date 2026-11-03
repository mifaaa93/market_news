"""SQLite: пользователи, лента и учёт прочитанного."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiosqlite

import config
from content import is_public_article_url, source_hash
from models import Article, Source, User

# Тот же порог, что is_full_text: короткий анонс из RSS пользователю не показываем.
_FULL_TEXT_SQL = "length(body) >= 900 AND length(body) >= length(summary) + 400"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    lang TEXT NOT NULL DEFAULT 'ru',
    notifications INTEGER NOT NULL DEFAULT 1,
    digest_hour INTEGER NOT NULL DEFAULT 9,
    timezone TEXT NOT NULL DEFAULT 'Europe/Moscow',
    interactions INTEGER NOT NULL DEFAULT 0,
    full_reads INTEGER NOT NULL DEFAULT 0,
    premium_until TEXT,
    created_at TEXT NOT NULL,
    last_digest_on TEXT,
    blocked INTEGER NOT NULL DEFAULT 0,
    plan TEXT NOT NULL DEFAULT 'base',
    source_pending INTEGER NOT NULL DEFAULT 0,
    subscribed_at TEXT
);

CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL UNIQUE,
    source_key TEXT NOT NULL,
    source_name TEXT NOT NULL,
    title TEXT NOT NULL,
    title_norm TEXT NOT NULL UNIQUE,
    summary TEXT NOT NULL,
    body TEXT NOT NULL,
    url TEXT NOT NULL,
    image_url TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL,
    published_at TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    full_checked INTEGER NOT NULL DEFAULT 0,
    first_seen_at TEXT NOT NULL DEFAULT '',
    catalog_visible INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category, published_at DESC);

CREATE TABLE IF NOT EXISTS seen (
    user_id INTEGER NOT NULL,
    article_id INTEGER NOT NULL,
    opened_at TEXT NOT NULL,
    PRIMARY KEY (user_id, article_id),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS payments (
    charge_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS translations (
    article_id INTEGER NOT NULL,
    lang TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    body TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (article_id, lang),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feed_catalog (
    source_key TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    feed_url TEXT NOT NULL,
    homepage TEXT NOT NULL DEFAULT '',
    owner_user_id INTEGER,
    custom INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_sources (
    user_id INTEGER NOT NULL,
    source_key TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, source_key),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (source_key) REFERENCES feed_catalog(source_key) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS article_pushes (
    user_id INTEGER NOT NULL,
    article_id INTEGER NOT NULL,
    sent_at TEXT NOT NULL,
    PRIMARY KEY (user_id, article_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS admin_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_user_id INTEGER NOT NULL,
    target_user_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    plan TEXT,
    created_at TEXT NOT NULL
);
"""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        cursor = await self._conn.execute("PRAGMA journal_mode=WAL")
        await cursor.fetchone()
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._conn.execute("PRAGMA busy_timeout=5000")
        await self._conn.executescript(_SCHEMA)
        await self._ensure_columns()
        # Older versions marked HTTP 429 as a permanent failure. Retry those
        # CoinDesk entries once after the new backoff mechanism is installed.
        cursor = await self.conn.execute(
            "SELECT 1 FROM meta WHERE key='retry_coindesk_429_v1'"
        )
        if await cursor.fetchone() is None:
            await self.conn.execute(
                "UPDATE articles SET full_checked=0 "
                "WHERE source_key='coindesk' AND full_checked=1 AND url!='' "
                f"AND NOT ({_FULL_TEXT_SQL})"
            )
            await self.conn.execute(
                "INSERT INTO meta(key, value) VALUES ('retry_coindesk_429_v1', '1')"
            )
        await self._conn.commit()

    async def _ensure_columns(self) -> None:
        cursor = await self.conn.execute("PRAGMA table_info(users)")
        user_names = {row["name"] for row in await cursor.fetchall()}
        if "plan" not in user_names:
            await self.conn.execute("ALTER TABLE users ADD COLUMN plan TEXT NOT NULL DEFAULT 'base'")
        if "source_pending" not in user_names:
            await self.conn.execute(
                "ALTER TABLE users ADD COLUMN source_pending INTEGER NOT NULL DEFAULT 0"
            )
        if "subscribed_at" not in user_names:
            await self.conn.execute("ALTER TABLE users ADD COLUMN subscribed_at TEXT")
        await self.conn.execute(
            "UPDATE users SET plan='plus' WHERE premium_until IS NOT NULL AND plan='base'"
        )
        cursor = await self.conn.execute("PRAGMA table_info(articles)")
        rows = await cursor.fetchall()
        names = {row["name"] for row in rows}
        if "image_url" not in names:
            await self.conn.execute(
                "ALTER TABLE articles ADD COLUMN image_url TEXT NOT NULL DEFAULT ''"
            )
        if "full_checked" not in names:
            await self.conn.execute(
                "ALTER TABLE articles ADD COLUMN full_checked INTEGER NOT NULL DEFAULT 0"
            )
        if "first_seen_at" not in names:
            await self.conn.execute(
                "ALTER TABLE articles ADD COLUMN first_seen_at TEXT NOT NULL DEFAULT ''"
            )
            await self.conn.execute("UPDATE articles SET first_seen_at=fetched_at")
        if "catalog_visible" not in names:
            await self.conn.execute(
                "ALTER TABLE articles ADD COLUMN catalog_visible INTEGER NOT NULL DEFAULT 1"
            )

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("database is not connected")
        return self._conn

    async def upsert_user(self, user_id: int, username: str | None, first_name: str | None) -> User:
        await self.conn.execute(
            """
            INSERT INTO users (
                user_id, username, first_name, lang, notifications, digest_hour,
                timezone, interactions, full_reads, premium_until, created_at,
                last_digest_on, blocked, plan, source_pending
            ) VALUES (?, ?, ?, 'ru', 1, ?, ?, 0, 0, NULL, ?, NULL, 0, 'base', 0)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                blocked=0
            """,
            (user_id, username, first_name, config.DEFAULT_HOUR, config.DEFAULT_TZ, utc_now_iso()),
        )
        await self.conn.commit()
        return await self.require_user(user_id)

    async def get_user(self, user_id: int) -> User | None:
        cursor = await self.conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return _user(row)

    async def require_user(self, user_id: int) -> User:
        user = await self.get_user(user_id)
        if user is None:
            raise LookupError(user_id)
        return user

    async def _update_user(self, user_id: int, sql: str, params: tuple) -> User:
        await self.conn.execute(sql, (*params, user_id))
        await self.conn.commit()
        return await self.require_user(user_id)

    async def set_lang(self, user_id: int, lang: str) -> User:
        return await self._update_user(user_id, "UPDATE users SET lang=? WHERE user_id=?", (lang,))

    async def set_notifications(self, user_id: int, enabled: bool) -> User:
        return await self._update_user(
            user_id,
            "UPDATE users SET notifications=? WHERE user_id=?",
            (1 if enabled else 0,),
        )

    async def set_hour(self, user_id: int, hour: int) -> User:
        return await self._update_user(user_id, "UPDATE users SET digest_hour=? WHERE user_id=?", (hour,))

    async def set_timezone(self, user_id: int, zone: str) -> User:
        return await self._update_user(user_id, "UPDATE users SET timezone=? WHERE user_id=?", (zone,))

    async def set_source_pending(self, user_id: int, pending: bool) -> User:
        return await self._update_user(
            user_id,
            "UPDATE users SET source_pending=? WHERE user_id=?",
            (1 if pending else 0,),
        )

    async def add_interaction(self, user_id: int, *, full_read: bool = False) -> User:
        if full_read:
            sql = """
                UPDATE users
                SET interactions = interactions + 1, full_reads = full_reads + 1
                WHERE user_id=?
            """
        else:
            sql = "UPDATE users SET interactions = interactions + 1 WHERE user_id=?"
        await self.conn.execute(sql, (user_id,))
        await self.conn.commit()
        return await self.require_user(user_id)

    async def mark_seen(self, user_id: int, article_id: int) -> None:
        await self.conn.execute(
            """
            INSERT INTO seen (user_id, article_id, opened_at) VALUES (?, ?, ?)
            ON CONFLICT(user_id, article_id) DO NOTHING
            """,
            (user_id, article_id, utc_now_iso()),
        )
        await self.conn.commit()

    async def count_seen(self, user_id: int) -> int:
        cursor = await self.conn.execute("SELECT COUNT(*) FROM seen WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        return int(row[0])

    async def count_articles(self) -> int:
        cursor = await self.conn.execute("SELECT COUNT(*) FROM articles")
        row = await cursor.fetchone()
        return int(row[0])

    async def category_counts(self, *, full_only: bool = False) -> dict[str, int]:
        where = f"WHERE {_FULL_TEXT_SQL}" if full_only else ""
        cursor = await self.conn.execute(
            f"SELECT category, COUNT(*) AS n FROM articles {where} GROUP BY category"
        )
        rows = await cursor.fetchall()
        return {row["category"]: int(row["n"]) for row in rows}

    async def upsert_articles(
        self, items: list[Article], *, catalog_visible: bool = False
    ) -> int:
        saved = 0
        for item in items:
            url = (
                item.url
                if is_public_article_url(item.url)
                or (item.source_key.startswith("custom:") and item.url.startswith("https://"))
                else ""
            )
            try:
                await self.conn.execute(
                    """
                    INSERT INTO articles (
                        guid, source_key, source_name, title, title_norm, summary,
                        body, url, image_url, category, published_at, fetched_at,
                        first_seen_at, catalog_visible
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(guid) DO UPDATE SET
                        summary=excluded.summary,
                        body=CASE
                            WHEN length(articles.body) > length(excluded.body) + 400 THEN articles.body
                            ELSE excluded.body
                        END,
                        fetched_at=excluded.fetched_at,
                        url=CASE WHEN excluded.url != '' THEN excluded.url ELSE articles.url END,
                        image_url=CASE WHEN excluded.image_url != '' THEN excluded.image_url ELSE articles.image_url END
                    """,
                    (
                        item.guid,
                        item.source_key,
                        item.source_name,
                        item.title,
                        item.title_norm,
                        item.summary,
                        item.body,
                        url,
                        item.image_url,
                        item.category,
                        item.published_at,
                        item.fetched_at,
                        item.fetched_at,
                        1 if catalog_visible else 0,
                    ),
                )
                saved += 1
            except aiosqlite.IntegrityError:
                continue
        await self.conn.commit()
        return saved

    async def mark_catalog_visible(self, items: list[Article]) -> None:
        norms = [item.title_norm for item in items if item.title_norm]
        if not norms:
            return
        marks = ",".join("?" for _ in norms)
        await self.conn.execute(
            f"UPDATE articles SET catalog_visible=1 WHERE title_norm IN ({marks})",
            norms,
        )
        await self.conn.commit()

    async def ensure_catalog(self, rows: list[tuple[str, str, str, str]]) -> None:
        # Remove only known discontinued public feeds. Never touch a user's private source.
        retired = (
            "marketwatch", "investing", "cnn-business", "yahoo-finance", "sec-press",
            "guardian-business", "guardian-markets",
        )
        marks = ",".join("?" for _ in retired)
        await self.conn.execute(
            f"DELETE FROM feed_catalog WHERE owner_user_id IS NULL AND source_key IN ({marks})",
            retired,
        )
        await self.conn.execute(
            "DELETE FROM articles WHERE source_key IN ('guardian-business', 'guardian-markets')"
        )
        for key, name, feed_url, homepage in rows:
            await self.conn.execute(
                """
                INSERT INTO feed_catalog(source_key, name, feed_url, homepage, owner_user_id, custom, created_at)
                VALUES (?, ?, ?, ?, NULL, 0, ?)
                ON CONFLICT(source_key) DO UPDATE SET
                    name=excluded.name, feed_url=excluded.feed_url, homepage=excluded.homepage
                """,
                (key, name, feed_url, homepage, utc_now_iso()),
            )
        await self.conn.commit()

    async def list_sources(self, user_id: int | None = None) -> list[Source]:
        if user_id is None:
            cursor = await self.conn.execute(
                "SELECT * FROM feed_catalog WHERE owner_user_id IS NULL ORDER BY custom, name"
            )
        else:
            cursor = await self.conn.execute(
                """
                SELECT * FROM feed_catalog
                WHERE owner_user_id IS NULL OR owner_user_id=?
                ORDER BY custom, name
                """,
                (user_id,),
            )
        return [_source(row) for row in await cursor.fetchall()]

    async def source(self, key: str) -> Source | None:
        cursor = await self.conn.execute("SELECT * FROM feed_catalog WHERE source_key=?", (key,))
        row = await cursor.fetchone()
        return _source(row) if row else None

    async def source_by_url(self, user_id: int, url: str) -> Source | None:
        cursor = await self.conn.execute(
            """
            SELECT * FROM feed_catalog
            WHERE owner_user_id=? AND feed_url=?
            LIMIT 1
            """,
            (user_id, url),
        )
        row = await cursor.fetchone()
        return _source(row) if row else None

    async def add_custom_source(self, user_id: int, key: str, name: str, feed_url: str, homepage: str) -> Source:
        await self.conn.execute(
            """
            INSERT INTO feed_catalog(source_key, name, feed_url, homepage, owner_user_id, custom, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?)
            ON CONFLICT(source_key) DO UPDATE SET name=excluded.name, feed_url=excluded.feed_url
            """,
            (key, name, feed_url, homepage, user_id, utc_now_iso()),
        )
        await self.conn.execute(
            """
            INSERT INTO user_sources(user_id, source_key, enabled) VALUES (?, ?, 1)
            ON CONFLICT(user_id, source_key) DO UPDATE SET enabled=1
            """,
            (user_id, key),
        )
        await self.conn.commit()
        result = await self.source(key)
        if result is None:
            raise LookupError(key)
        return result

    async def source_states(self, user_id: int) -> dict[str, bool]:
        sources = await self.list_sources(user_id)
        cursor = await self.conn.execute(
            "SELECT source_key, enabled FROM user_sources WHERE user_id=?",
            (user_id,),
        )
        explicit = {str(row["source_key"]): bool(row["enabled"]) for row in await cursor.fetchall()}
        global_sources = [item for item in sources if not item.custom]
        # Preserve the existing five default feeds when new catalog entries
        # sort ahead of them; new sources can still be enabled manually.
        original = ("bbc", "cnbc-economy", "cnbc-finance", "cnbc-oil", "coindesk")
        preferred = sorted(
            global_sources,
            key=lambda item: (original.index(item.key) if item.key in original else len(original), item.name),
        )
        defaults = {item.key for item in preferred[: config.BASE_SOURCE_LIMIT]}
        user = await self.require_user(user_id)
        allowed = config.PRO_SOURCE_LIMIT if user.is_pro() else (
            config.PLUS_SOURCE_LIMIT if user.premium_active() else config.BASE_SOURCE_LIMIT
        )
        custom_limit = (
            config.PRO_CUSTOM_LIMIT if user.is_pro()
            else config.PLUS_CUSTOM_LIMIT if user.premium_active()
            else 0
        )
        custom_seen = 0
        states: dict[str, bool] = {}
        for item in sources:
            state = explicit.get(item.key, item.custom or item.key in defaults)
            if item.custom:
                if custom_seen >= custom_limit:
                    state = False
                elif state:
                    custom_seen += 1
            states[item.key] = state
        count = 0
        for item in sources:
            if states[item.key]:
                count += 1
                if count > allowed:
                    states[item.key] = False
        return states

    async def set_source_enabled(self, user_id: int, source_key: str, enabled: bool) -> None:
        await self.conn.execute(
            """
            INSERT INTO user_sources(user_id, source_key, enabled) VALUES (?, ?, ?)
            ON CONFLICT(user_id, source_key) DO UPDATE SET enabled=excluded.enabled
            """,
            (user_id, source_key, 1 if enabled else 0),
        )
        await self.conn.commit()

    async def active_sources(self, user_id: int) -> list[Source]:
        states = await self.source_states(user_id)
        sources = await self.list_sources(user_id)
        return [source for source in sources if states.get(source.key, False)]

    async def source_limits(self, plan: str) -> tuple[int, int]:
        if plan == "pro":
            return config.PRO_SOURCE_LIMIT, config.PRO_CUSTOM_LIMIT
        if plan == "plus":
            return config.PLUS_SOURCE_LIMIT, config.PLUS_CUSTOM_LIMIT
        return config.BASE_SOURCE_LIMIT, 0

    async def set_plan(self, user_id: int, plan: str, until: str) -> User:
        return await self._update_user(
            user_id,
            "UPDATE users SET plan=?, premium_until=? WHERE user_id=?",
            (plan, until),
        )

    async def list_push_subscribers(self, article: Article) -> list[User]:
        cursor = await self.conn.execute(
            "SELECT * FROM users WHERE blocked=0 AND plan IN ('plus','pro')"
        )
        users = [_user(row) for row in await cursor.fetchall()]
        result: list[User] = []
        for user in users:
            if not user.premium_active():
                continue
            if (
                user.plan == "plus"
                and not article.catalog_visible
                and not article.source_key.startswith("custom:")
            ):
                continue
            active = await self.active_sources(user.user_id)
            if any(item.key == article.source_key for item in active):
                result.append(user)
        return result

    async def push_already_sent(self, user_id: int, article_id: int) -> bool:
        cursor = await self.conn.execute(
            "SELECT 1 FROM article_pushes WHERE user_id=? AND article_id=?",
            (user_id, article_id),
        )
        return await cursor.fetchone() is not None

    async def mark_push_sent(self, user_id: int, article_id: int) -> None:
        await self.conn.execute(
            "INSERT OR IGNORE INTO article_pushes(user_id, article_id, sent_at) VALUES (?, ?, ?)",
            (user_id, article_id, utc_now_iso()),
        )
        await self.conn.commit()

    async def articles_since(self, stamp: str) -> list[Article]:
        cursor = await self.conn.execute(
            f"SELECT * FROM articles WHERE first_seen_at>? AND {_FULL_TEXT_SQL} ORDER BY published_at DESC, id DESC",
            (stamp,),
        )
        return [_article(row) for row in await cursor.fetchall()]

    async def save_full_text(self, article_id: int, body: str | None) -> Article | None:
        if body:
            await self.conn.execute(
                "UPDATE articles SET body=?, full_checked=1 WHERE id=?",
                (body[:12000], article_id),
            )
        else:
            await self.conn.execute(
                "UPDATE articles SET full_checked=1 WHERE id=?",
                (article_id,),
            )
        await self.conn.commit()
        return await self.get_article(article_id)

    async def articles_needing_full_text(self, limit: int = 300) -> list[Article]:
        await self.conn.execute(
            "UPDATE articles SET full_checked=1 WHERE full_checked=0 AND url=''"
        )
        await self.conn.commit()
        cursor = await self.conn.execute(
            """
            SELECT * FROM articles
            WHERE full_checked=0
            ORDER BY published_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [_article(row) for row in rows]

    async def remember_images(self, items: list[Article]) -> None:
        for item in items:
            if not item.image_url:
                continue
            await self.conn.execute(
                """
                UPDATE articles
                SET image_url=?
                WHERE title_norm=? AND (image_url='' OR image_url IS NULL)
                """,
                (item.image_url, item.title_norm),
            )
        await self.conn.commit()

    async def translation_hashes(self, lang: str, article_ids: list[int]) -> dict[int, str]:
        if not article_ids:
            return {}
        marks = ",".join("?" for _ in article_ids)
        cursor = await self.conn.execute(
            f"SELECT article_id, source_hash FROM translations WHERE lang=? AND article_id IN ({marks})",
            (lang, *article_ids),
        )
        rows = await cursor.fetchall()
        return {int(row["article_id"]): str(row["source_hash"]) for row in rows}

    async def articles_missing_translation(
        self, lang: str, limit: int, *, full_only: bool = False
    ) -> list[Article]:
        full_filter = (
            " AND length(a.body) >= 900 "
            "AND length(a.body) >= length(a.summary) + 400"
            if full_only
            else ""
        )
        cursor = await self.conn.execute(
            f"""
            SELECT a.*
            FROM articles a
            LEFT JOIN translations t ON t.article_id = a.id AND t.lang = ?
            WHERE t.article_id IS NULL{full_filter}
            ORDER BY a.published_at DESC, a.id DESC
            LIMIT ?
            """,
            (lang, limit),
        )
        missing = [_article(row) for row in await cursor.fetchall()]
        if len(missing) >= limit:
            return missing
        seen = {article.id for article in missing}
        recent = await self.recent(80, full_only=full_only)
        hashes = await self.translation_hashes(lang, [article.id for article in recent])
        for article in recent:
            if len(missing) >= limit or article.id in seen:
                continue
            if hashes.get(article.id) != source_hash(article):
                missing.append(article)
                seen.add(article.id)
        return missing

    async def save_translations(self, lang: str, rows: list[tuple[Article, str, str, str]]) -> None:
        now = utc_now_iso()
        for article, title, summary, body in rows:
            await self.conn.execute(
                """
                INSERT INTO translations (
                    article_id, lang, title, summary, body, source_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(article_id, lang) DO UPDATE SET
                    title=excluded.title,
                    summary=excluded.summary,
                    body=excluded.body,
                    source_hash=excluded.source_hash,
                    created_at=excluded.created_at
                """,
                (article.id, lang, title, summary, body, source_hash(article), now),
            )
        await self.conn.commit()

    async def apply_translations(self, articles: list[Article], lang: str) -> list[Article]:
        if lang not in config.TRANSLATION_LANGS or not articles:
            return articles
        hashes = await self.translation_hashes(lang, [article.id for article in articles if article.id])
        if not hashes:
            return articles
        marks = ",".join("?" for _ in hashes)
        cursor = await self.conn.execute(
            f"""
            SELECT article_id, title, summary, body, source_hash
            FROM translations
            WHERE lang=? AND article_id IN ({marks})
            """,
            (lang, *hashes.keys()),
        )
        rows = await cursor.fetchall()
        by_id = {int(row["article_id"]): row for row in rows}
        localized: list[Article] = []
        for article in articles:
            row = by_id.get(article.id)
            if row is None or str(row["source_hash"]) != source_hash(article):
                localized.append(article)
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

    async def recent(self, limit: int, *, full_only: bool = False) -> list[Article]:
        return await self.recent_for_user(None, limit, full_only=full_only)

    async def recent_for_user(
        self, user_id: int | None, limit: int, *, full_only: bool = False
    ) -> list[Article]:
        where = f"WHERE {_FULL_TEXT_SQL}" if full_only else ""
        params: list[object] = []
        if user_id is not None:
            states = await self.source_states(user_id)
            if not states:
                return await self.recent(limit, full_only=full_only)
            enabled = [key for key, value in states.items() if value]
            if not enabled:
                return []
            marks = ",".join("?" for _ in enabled)
            where += f" {'AND' if where else 'WHERE'} source_key IN ({marks})"
            params.extend(enabled)
        cursor = await self.conn.execute(
            f"""
            SELECT * FROM articles
            {where}
            ORDER BY published_at DESC, id DESC
            LIMIT ?
            """,
            (*params, limit),
        )
        rows = await cursor.fetchall()
        return [_article(row) for row in rows]

    async def by_category(
        self,
        category: str,
        limit: int,
        *,
        full_only: bool = False,
        user_id: int | None = None,
    ) -> list[Article]:
        extra = f" AND {_FULL_TEXT_SQL}" if full_only else ""
        params: list[object] = [category]
        if user_id is not None:
            states = await self.source_states(user_id)
            enabled = [key for key, value in states.items() if value]
            if not enabled:
                return []
            marks = ",".join("?" for _ in enabled)
            extra += f" AND source_key IN ({marks})"
            params.extend(enabled)
        cursor = await self.conn.execute(
            f"""
            SELECT * FROM articles
            WHERE category=?{extra}
            ORDER BY published_at DESC, id DESC
            LIMIT ?
            """,
            (*params, limit),
        )
        rows = await cursor.fetchall()
        return [_article(row) for row in rows]

    async def get_article(self, article_id: int) -> Article | None:
        cursor = await self.conn.execute("SELECT * FROM articles WHERE id=?", (article_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return _article(row)

    async def title_norms(self) -> set[str]:
        cursor = await self.conn.execute("SELECT title_norm FROM articles")
        rows = await cursor.fetchall()
        return {row["title_norm"] for row in rows}

    async def delete_old(self, days: int) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        cursor = await self.conn.execute("DELETE FROM articles WHERE published_at < ?", (cutoff,))
        await self.conn.commit()
        return cursor.rowcount or 0

    async def meta_get(self, key: str) -> str | None:
        cursor = await self.conn.execute("SELECT value FROM meta WHERE key=?", (key,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return str(row["value"])

    async def meta_set(self, key: str, value: str) -> None:
        await self.conn.execute(
            """
            INSERT INTO meta (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (key, value),
        )
        await self.conn.commit()

    async def list_digest_subscribers(self) -> list[User]:
        cursor = await self.conn.execute(
            "SELECT * FROM users WHERE notifications=1 AND blocked=0"
        )
        rows = await cursor.fetchall()
        return [_user(row) for row in rows]

    async def list_paid_users(self) -> list[User]:
        cursor = await self.conn.execute(
            "SELECT * FROM users WHERE blocked=0 AND plan IN ('plus','pro')"
        )
        return [user for user in [_user(row) for row in await cursor.fetchall()] if user.premium_active()]

    async def paid_catalog_keys(self, plan: str | None = None) -> set[str]:
        keys: set[str] = set()
        for user in await self.list_paid_users():
            if plan and user.plan != plan:
                continue
            keys.update(item.key for item in await self.active_sources(user.user_id) if not item.custom)
        return keys

    async def mark_digest_sent(self, user_id: int, day: str) -> None:
        await self.conn.execute(
            "UPDATE users SET last_digest_on=? WHERE user_id=?",
            (day, user_id),
        )
        await self.conn.commit()

    async def set_blocked(self, user_id: int, blocked: bool) -> None:
        await self.conn.execute(
            "UPDATE users SET blocked=? WHERE user_id=?",
            (1 if blocked else 0, user_id),
        )
        await self.conn.commit()

    async def save_payment(self, charge_id: str, user_id: int, amount: int) -> bool:
        try:
            await self.conn.execute(
                """
                INSERT INTO payments (charge_id, user_id, amount, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (charge_id, user_id, amount, utc_now_iso()),
            )
            await self.conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def extend_premium(self, user_id: int, days: int) -> User:
        return await self.extend_plan(user_id, "plus", days)

    async def extend_plan(self, user_id: int, plan: str, days: int) -> User:
        user = await self.require_user(user_id)
        now = datetime.now(timezone.utc)
        base = now
        if user.premium_active(now) and user.premium_until:
            parsed = datetime.fromisoformat(user.premium_until)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            base = parsed
        until = (base + timedelta(days=days)).astimezone(timezone.utc)
        stamp = until.strftime("%Y-%m-%dT%H:%M:%SZ")
        return await self._update_user(
            user_id,
            "UPDATE users SET premium_until=?, plan=?, subscribed_at=COALESCE(subscribed_at, ?) WHERE user_id=?",
            (stamp, plan, utc_now_iso()),
        )

    async def revoke_plan(self, user_id: int) -> User:
        return await self._update_user(
            user_id,
            "UPDATE users SET plan='base', premium_until=NULL WHERE user_id=?",
            (),
        )

    async def record_admin_action(
        self, admin_user_id: int, target_user_id: int, action: str, plan: str | None = None
    ) -> None:
        await self.conn.execute(
            """
            INSERT INTO admin_actions(admin_user_id, target_user_id, action, plan, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (admin_user_id, target_user_id, action, plan, utc_now_iso()),
        )
        await self.conn.commit()

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


def _user(row: aiosqlite.Row) -> User:
    premium = row["premium_until"]
    last = row["last_digest_on"]
    return User(
        user_id=int(row["user_id"]),
        lang=row["lang"] or "ru",
        notifications=bool(row["notifications"]),
        digest_hour=int(row["digest_hour"]),
        timezone=row["timezone"],
        interactions=int(row["interactions"]),
        full_reads=int(row["full_reads"]),
        premium_until=str(premium) if premium else None,
        last_digest_on=str(last) if last else None,
        blocked=bool(row["blocked"]),
        plan=str(row["plan"] or "base") if "plan" in row.keys() else "base",
        source_pending=bool(row["source_pending"]) if "source_pending" in row.keys() else False,
        subscribed_at=str(row["subscribed_at"]) if "subscribed_at" in row.keys() and row["subscribed_at"] else None,
    )


def _source(row: aiosqlite.Row) -> Source:
    return Source(
        key=str(row["source_key"]),
        name=str(row["name"]),
        url=str(row["feed_url"]),
        homepage=str(row["homepage"] or ""),
        owner_user_id=int(row["owner_user_id"]) if row["owner_user_id"] is not None else None,
        custom=bool(row["custom"]),
    )


def _article(row: aiosqlite.Row) -> Article:
    return Article(
        id=int(row["id"]),
        guid=row["guid"],
        source_key=row["source_key"],
        source_name=row["source_name"],
        title=row["title"],
        title_norm=row["title_norm"],
        summary=row["summary"],
        body=row["body"],
        url=row["url"],
        image_url=row["image_url"] or "",
        category=row["category"],
        published_at=row["published_at"],
        fetched_at=row["fetched_at"],
        full_checked=bool(row["full_checked"]) if "full_checked" in row.keys() else False,
        catalog_visible=bool(row["catalog_visible"]) if "catalog_visible" in row.keys() else True,
    )
