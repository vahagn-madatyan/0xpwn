"""SQLite-backed CVE cache with TTL-based expiry and WAL journal mode."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Default TTL: 7 days in seconds.
_DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60  # 604_800

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cve_cache (
    cve_id    TEXT PRIMARY KEY,
    data      TEXT NOT NULL,
    cached_at REAL NOT NULL
);
"""


def _default_cache_path() -> Path:
    """Resolve the default cache DB path following XDG conventions.

    Precedence:
        1. ``$XDG_CACHE_HOME/oxpwn/cve-cache.db``
        2. ``~/.cache/oxpwn/cve-cache.db``
    """
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / "oxpwn" / "cve-cache.db"
    return Path.home() / ".cache" / "oxpwn" / "cve-cache.db"


class CveCache:
    """File-backed SQLite CVE cache with TTL expiry.

    Parameters
    ----------
    db_path:
        Path to the SQLite database.  Defaults to the XDG cache location.
        Pass ``":memory:"`` for an ephemeral in-memory cache (useful in tests).
    ttl_seconds:
        Time-to-live for cached entries in seconds.  Default is 7 days.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    ) -> None:
        if db_path is None:
            db_path = _default_cache_path()

        self._db_path = Path(db_path) if str(db_path) != ":memory:" else None
        self._ttl = ttl_seconds

        # Create parent directories atomically for file-backed DBs.
        if self._db_path is not None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(str(db_path))

        # Enable WAL for better concurrent read performance.
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(_SCHEMA_SQL)
        self._conn.commit()

        logger.debug("nvd.cache_opened", path=str(db_path))

    # -- Public API ---------------------------------------------------------

    def get(self, cve_id: str) -> dict[str, Any] | None:
        """Return cached data if within TTL, else None."""
        cve_id = cve_id.upper().strip()
        row = self._conn.execute(
            "SELECT data, cached_at FROM cve_cache WHERE cve_id = ?",
            (cve_id,),
        ).fetchone()

        if row is None:
            logger.debug("nvd.cache_miss", cve_id=cve_id)
            return None

        data_json, cached_at = row
        age = time.time() - cached_at
        if age > self._ttl:
            logger.debug("nvd.cache_miss", cve_id=cve_id, reason="expired", age_days=round(age / 86400, 1))
            return None

        logger.debug("nvd.cache_hit", cve_id=cve_id, age_days=round(age / 86400, 1))
        return json.loads(data_json)

    def put(self, cve_id: str, data: dict[str, Any]) -> None:
        """Upsert cached data with current timestamp."""
        cve_id = cve_id.upper().strip()
        self._conn.execute(
            """
            INSERT INTO cve_cache (cve_id, data, cached_at)
            VALUES (?, ?, ?)
            ON CONFLICT(cve_id) DO UPDATE SET
                data = excluded.data,
                cached_at = excluded.cached_at
            """,
            (cve_id, json.dumps(data), time.time()),
        )
        self._conn.commit()

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()
        logger.debug("nvd.cache_closed")

    # -- Context manager support -------------------------------------------

    def __enter__(self) -> CveCache:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
