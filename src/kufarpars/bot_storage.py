"""SQLite storage for Telegram bot profiles and seen listings.

The production default is SQLite because it is simple to deploy, persistent,
and perfectly adequate for one bot process. The schema keeps profiles and seen
advertisements separate: profile rows are tiny, while ``seen_ads`` can grow and
be pruned independently.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from kufarpars.client import SearchRequest


@dataclass
class UserProfile:
    """A Telegram chat profile with search settings and recent seen listing ids."""

    chat_id: int
    enabled: bool = False
    request: SearchRequest = field(default_factory=SearchRequest)
    seen_ids: list[int] = field(default_factory=list)


class BotStorage:
    """Persist bot profiles and seen listing ids in SQLite."""

    def __init__(
        self,
        path: str,
        legacy_json_path: str | None = None,
        seen_ttl_days: int = 60,
        max_seen_per_chat: int = 5000,
    ) -> None:
        """Create storage, initialize schema, and migrate old JSON state if found."""
        self._path = Path(path)
        self._legacy_json_path = Path(legacy_json_path) if legacy_json_path else None
        self._seen_ttl_days = seen_ttl_days
        self._max_seen_per_chat = max_seen_per_chat
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self._path)
        self._connection.row_factory = sqlite3.Row
        self._initialize()
        self._migrate_legacy_json()

    def close(self) -> None:
        """Close the SQLite connection."""
        self._connection.close()

    def get(self, chat_id: int) -> UserProfile:
        """Return an existing profile or create a new default one."""
        row = self._connection.execute(
            "SELECT chat_id, enabled, request_json FROM profiles WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
        if row is None:
            profile = UserProfile(chat_id=chat_id)
            self.update(profile)
            return profile
        return UserProfile(
            chat_id=int(row["chat_id"]),
            enabled=bool(row["enabled"]),
            request=_request_from_json(row["request_json"]),
            seen_ids=self.recent_seen_ids(chat_id),
        )

    def update(self, profile: UserProfile) -> None:
        """Upsert profile settings and optionally persist provided seen ids."""
        self._connection.execute(
            """
            INSERT INTO profiles (chat_id, enabled, request_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                enabled = excluded.enabled,
                request_json = excluded.request_json,
                updated_at = excluded.updated_at
            """,
            (
                profile.chat_id,
                int(profile.enabled),
                _request_to_json(profile.request),
                _now_iso(),
            ),
        )
        if profile.seen_ids:
            self.mark_seen(profile.chat_id, profile.seen_ids)
        self._connection.commit()

    def all_enabled(self) -> list[UserProfile]:
        """Return all profiles with background monitoring enabled."""
        rows = self._connection.execute(
            "SELECT chat_id, enabled, request_json FROM profiles WHERE enabled = 1"
        ).fetchall()
        return [
            UserProfile(
                chat_id=int(row["chat_id"]),
                enabled=bool(row["enabled"]),
                request=_request_from_json(row["request_json"]),
                seen_ids=self.recent_seen_ids(int(row["chat_id"])),
            )
            for row in rows
        ]

    def recent_seen_ids(self, chat_id: int, limit: int | None = None) -> list[int]:
        """Return recent seen listing ids for one chat."""
        rows = self._connection.execute(
            """
            SELECT ad_id
            FROM seen_ads
            WHERE chat_id = ?
            ORDER BY seen_at DESC
            LIMIT ?
            """,
            (chat_id, limit or self._max_seen_per_chat),
        ).fetchall()
        return [int(row["ad_id"]) for row in rows]

    def mark_seen(self, chat_id: int, ad_ids: list[int]) -> None:
        """Insert seen listing ids using a unique key to prevent duplicates."""
        if not ad_ids:
            return
        seen_at = _now_iso()
        unique_ids = list(dict.fromkeys(int(ad_id) for ad_id in ad_ids))
        self._connection.executemany(
            """
            INSERT INTO seen_ads (chat_id, ad_id, seen_at)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id, ad_id) DO UPDATE SET seen_at = excluded.seen_at
            """,
            [(chat_id, ad_id, seen_at) for ad_id in unique_ids],
        )
        self.prune_seen(chat_id)
        self._connection.commit()

    def unseen_ids(self, chat_id: int, ad_ids: list[int]) -> list[int]:
        """Return ids from ``ad_ids`` that have not been seen for this chat."""
        if not ad_ids:
            return []
        placeholders = ",".join("?" for _ in ad_ids)
        rows = self._connection.execute(
            f"""
            SELECT ad_id
            FROM seen_ads
            WHERE chat_id = ? AND ad_id IN ({placeholders})
            """,
            [chat_id, *ad_ids],
        ).fetchall()
        seen = {int(row["ad_id"]) for row in rows}
        return [ad_id for ad_id in ad_ids if ad_id not in seen]

    def reset_seen(self, chat_id: int) -> None:
        """Delete seen listing ids for one chat, usually after filter changes."""
        self._connection.execute("DELETE FROM seen_ads WHERE chat_id = ?", (chat_id,))
        self._connection.commit()

    def prune_seen(self, chat_id: int | None = None) -> None:
        """Remove old and excessive seen-id rows to keep SQLite small."""
        cutoff = datetime.now(UTC) - timedelta(days=self._seen_ttl_days)
        params: list[Any] = [cutoff.isoformat()]
        where_chat = ""
        if chat_id is not None:
            where_chat = "AND chat_id = ?"
            params.append(chat_id)
        self._connection.execute(
            f"DELETE FROM seen_ads WHERE seen_at < ? {where_chat}",
            params,
        )
        if chat_id is not None:
            self._prune_seen_limit(chat_id)

    def _initialize(self) -> None:
        """Create tables and indexes if they do not exist."""
        self._connection.executescript(
            """
            PRAGMA journal_mode = WAL;
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS profiles (
                chat_id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 0,
                request_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS seen_ads (
                chat_id INTEGER NOT NULL,
                ad_id INTEGER NOT NULL,
                seen_at TEXT NOT NULL,
                PRIMARY KEY (chat_id, ad_id),
                FOREIGN KEY (chat_id) REFERENCES profiles(chat_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_seen_ads_chat_seen_at
                ON seen_ads(chat_id, seen_at DESC);
            """
        )
        self._connection.commit()

    def _migrate_legacy_json(self) -> None:
        """Import profiles from the previous JSON storage file once."""
        if self._legacy_json_path is None or not self._legacy_json_path.exists():
            return
        marker_path = self._path.with_suffix(self._path.suffix + ".json_migrated")
        if marker_path.exists():
            return
        data = json.loads(self._legacy_json_path.read_text(encoding="utf-8"))
        for item in (data.get("profiles") or {}).values():
            profile = _profile_from_legacy_dict(item)
            self.update(profile)
        marker_path.write_text(_now_iso(), encoding="utf-8")

    def _prune_seen_limit(self, chat_id: int) -> None:
        """Keep only the newest configured number of seen ids for one chat."""
        self._connection.execute(
            """
            DELETE FROM seen_ads
            WHERE chat_id = ?
              AND ad_id NOT IN (
                  SELECT ad_id
                  FROM seen_ads
                  WHERE chat_id = ?
                  ORDER BY seen_at DESC
                  LIMIT ?
              )
            """,
            (chat_id, chat_id, self._max_seen_per_chat),
        )


def _request_to_json(request: SearchRequest) -> str:
    """Serialize SearchRequest as compact JSON."""
    return json.dumps(asdict(request), ensure_ascii=False, separators=(",", ":"))


def _request_from_json(value: str) -> SearchRequest:
    """Deserialize SearchRequest from JSON stored in SQLite."""
    data = json.loads(value)
    return SearchRequest(**data)


def _profile_from_legacy_dict(data: dict[str, object]) -> UserProfile:
    """Deserialize a profile from the old JSON file format."""
    request_data = data.get("request") or {}
    if not isinstance(request_data, dict):
        request_data = {}
    return UserProfile(
        chat_id=int(data["chat_id"]),
        enabled=bool(data.get("enabled")),
        request=SearchRequest(**request_data),
        seen_ids=[int(item) for item in data.get("seen_ids", [])],
    )


def _now_iso() -> str:
    """Return a timezone-aware timestamp for database rows."""
    return datetime.now(UTC).isoformat()
