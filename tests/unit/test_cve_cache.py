"""Unit tests for the SQLite CVE cache."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from oxpwn.enrichment.cache import CveCache


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_CVE_DATA = {
    "cvss": 10.0,
    "cvss_severity": "CRITICAL",
    "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
    "cwe_id": "CWE-917",
    "description": "Apache Log4j2 vulnerability.",
    "references": ["https://logging.apache.org/log4j/2.x/security.html"],
}


@pytest.fixture()
def memory_cache() -> CveCache:
    """In-memory cache for fast tests."""
    cache = CveCache(":memory:")
    yield cache
    cache.close()


@pytest.fixture()
def file_cache(tmp_path: Path) -> CveCache:
    """File-backed cache in a temporary directory."""
    db_path = tmp_path / "test-cache" / "cve-cache.db"
    cache = CveCache(db_path)
    yield cache
    cache.close()


# ---------------------------------------------------------------------------
# Tests: basic put/get round-trip
# ---------------------------------------------------------------------------


class TestPutGet:
    def test_round_trip(self, memory_cache: CveCache):
        """Put then get returns identical data."""
        memory_cache.put("CVE-2021-44228", SAMPLE_CVE_DATA)
        result = memory_cache.get("CVE-2021-44228")
        assert result == SAMPLE_CVE_DATA

    def test_get_missing_returns_none(self, memory_cache: CveCache):
        """Get for missing CVE ID returns None."""
        result = memory_cache.get("CVE-9999-99999")
        assert result is None

    def test_normalizes_cve_id_case(self, memory_cache: CveCache):
        """CVE IDs are normalized to uppercase."""
        memory_cache.put("cve-2021-44228", SAMPLE_CVE_DATA)
        result = memory_cache.get("CVE-2021-44228")
        assert result == SAMPLE_CVE_DATA

    def test_upsert_overwrites(self, memory_cache: CveCache):
        """Second put with same CVE ID overwrites the first."""
        memory_cache.put("CVE-2021-44228", {"cvss": 9.0})
        memory_cache.put("CVE-2021-44228", {"cvss": 10.0})
        result = memory_cache.get("CVE-2021-44228")
        assert result == {"cvss": 10.0}


# ---------------------------------------------------------------------------
# Tests: TTL expiry
# ---------------------------------------------------------------------------


class TestTTLExpiry:
    def test_data_within_ttl_is_returned(self, memory_cache: CveCache):
        """Data within TTL window is returned."""
        memory_cache.put("CVE-2021-44228", SAMPLE_CVE_DATA)
        # Immediately after put, data should be fresh.
        result = memory_cache.get("CVE-2021-44228")
        assert result is not None

    def test_data_past_ttl_returns_none(self, memory_cache: CveCache):
        """Data past TTL is treated as expired."""
        memory_cache.put("CVE-2021-44228", SAMPLE_CVE_DATA)

        # Advance time past 7-day TTL.
        eight_days = 8 * 24 * 60 * 60
        with patch("oxpwn.enrichment.cache.time.time", return_value=time.time() + eight_days):
            result = memory_cache.get("CVE-2021-44228")
        assert result is None

    def test_custom_ttl(self, tmp_path: Path):
        """Custom TTL is respected."""
        cache = CveCache(":memory:", ttl_seconds=10)
        cache.put("CVE-2021-44228", SAMPLE_CVE_DATA)

        # 5 seconds later: still valid.
        with patch("oxpwn.enrichment.cache.time.time", return_value=time.time() + 5):
            assert cache.get("CVE-2021-44228") is not None

        # 15 seconds later: expired.
        with patch("oxpwn.enrichment.cache.time.time", return_value=time.time() + 15):
            assert cache.get("CVE-2021-44228") is None

        cache.close()


# ---------------------------------------------------------------------------
# Tests: WAL journal mode
# ---------------------------------------------------------------------------


class TestWalMode:
    def test_wal_mode_set(self, file_cache: CveCache):
        """WAL journal mode is enabled."""
        row = file_cache._conn.execute("PRAGMA journal_mode").fetchone()
        assert row[0] == "wal"

    def test_wal_mode_in_memory(self, memory_cache: CveCache):
        """In-memory DBs report 'memory' journal mode (WAL not applicable)."""
        row = memory_cache._conn.execute("PRAGMA journal_mode").fetchone()
        # SQLite in-memory databases use 'memory' journal mode
        assert row[0] in ("memory", "wal")


# ---------------------------------------------------------------------------
# Tests: directory creation
# ---------------------------------------------------------------------------


class TestDirectoryCreation:
    def test_creates_parent_directories(self, tmp_path: Path):
        """Cache creates parent directories atomically."""
        deep_path = tmp_path / "a" / "b" / "c" / "cve-cache.db"
        assert not deep_path.parent.exists()

        cache = CveCache(deep_path)
        assert deep_path.parent.exists()
        cache.close()

    def test_existing_directory_is_ok(self, tmp_path: Path):
        """No error if directory already exists."""
        db_path = tmp_path / "existing" / "cve-cache.db"
        db_path.parent.mkdir(parents=True)

        cache = CveCache(db_path)
        cache.put("CVE-2021-44228", SAMPLE_CVE_DATA)
        assert cache.get("CVE-2021-44228") is not None
        cache.close()


# ---------------------------------------------------------------------------
# Tests: context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    def test_context_manager_closes(self, tmp_path: Path):
        """Context manager closes the connection."""
        db_path = tmp_path / "ctx-test" / "cve-cache.db"
        with CveCache(db_path) as cache:
            cache.put("CVE-2021-44228", SAMPLE_CVE_DATA)
            assert cache.get("CVE-2021-44228") is not None

        # After exit, connection should be closed.
        # Attempting to use it should raise.
        with pytest.raises(Exception):
            cache.get("CVE-2021-44228")


# ---------------------------------------------------------------------------
# Tests: schema
# ---------------------------------------------------------------------------


class TestSchema:
    def test_table_exists(self, memory_cache: CveCache):
        """cve_cache table exists with expected columns."""
        cursor = memory_cache._conn.execute("PRAGMA table_info(cve_cache)")
        columns = {row[1] for row in cursor.fetchall()}
        assert columns == {"cve_id", "data", "cached_at"}

    def test_stores_json(self, memory_cache: CveCache):
        """Data column stores valid JSON."""
        memory_cache.put("CVE-2021-44228", SAMPLE_CVE_DATA)
        row = memory_cache._conn.execute(
            "SELECT data FROM cve_cache WHERE cve_id = ?", ("CVE-2021-44228",)
        ).fetchone()
        parsed = json.loads(row[0])
        assert parsed == SAMPLE_CVE_DATA


# ---------------------------------------------------------------------------
# Tests: XDG default path
# ---------------------------------------------------------------------------


class TestDefaultPath:
    def test_default_uses_xdg_cache_home(self):
        """Default path respects XDG_CACHE_HOME."""
        with patch.dict("os.environ", {"XDG_CACHE_HOME": "/tmp/test-xdg-cache"}):
            from oxpwn.enrichment.cache import _default_cache_path
            path = _default_cache_path()
        assert str(path) == "/tmp/test-xdg-cache/oxpwn/cve-cache.db"

    def test_default_falls_back_to_home_cache(self):
        """Default path falls back to ~/.cache/oxpwn/."""
        with patch.dict("os.environ", {}, clear=True):
            from oxpwn.enrichment.cache import _default_cache_path
            path = _default_cache_path()
        assert str(path).endswith(".cache/oxpwn/cve-cache.db")
