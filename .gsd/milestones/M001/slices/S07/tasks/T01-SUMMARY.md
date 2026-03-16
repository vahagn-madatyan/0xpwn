---
id: T01
parent: S07
milestone: M001
provides:
  - Async NVD CVE 2.0 API client with rate limiting and Pydantic response models
  - SQLite CVE cache with WAL mode and 7-day TTL
  - Enrichment data extractor with CVSS version fallback and CWE filtering
key_files:
  - src/oxpwn/enrichment/__init__.py
  - src/oxpwn/enrichment/nvd.py
  - src/oxpwn/enrichment/cache.py
  - tests/unit/test_nvd_client.py
  - tests/unit/test_cve_cache.py
key_decisions:
  - Rate limiter uses simple timestamp-based spacing (7s no key, 0.6s with key) rather than token bucket — matches NVD's simple rate limit model
  - Cache uses synchronous sqlite3 (not aiosqlite) since cache operations are local I/O bound and negligible latency
patterns_established:
  - NVD Pydantic response models use field aliases matching NVD JSON camelCase keys
  - CveCache follows XDG cache convention mirroring ConfigManager's XDG config convention
  - enrichment module uses structlog events with nvd.* namespace
observability_surfaces:
  - structlog events: nvd.fetch, nvd.rate_limited, nvd.fetch_error, nvd.cache_hit, nvd.cache_miss, nvd.cache_opened, nvd.cache_closed
  - SQLite cache at ~/.cache/oxpwn/cve-cache.db queryable with sqlite3
  - NVD errors logged with status code, CVE ID, and response body head (API key never in logs)
duration: 15m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Build NVD API client with rate limiting and SQLite CVE cache

**Built async NVD CVE 2.0 client with rate-limited fetch, Pydantic response parsing, CVSS v3.1→v3.0→v2 fallback, CWE placeholder filtering, and SQLite cache with WAL mode and 7-day TTL.**

## What Happened

Created the `src/oxpwn/enrichment/` package with three files:

1. **`nvd.py`** — Pydantic models for the NVD CVE 2.0 response shape (`NvdCveResponse`, `NvdVulnerability`, `NvdCveItem`, `NvdCveMetrics`, `NvdCvssMetric`, `NvdWeakness`, etc.) plus `NvdClient` class with `fetch_cve()` and `search_cves()` methods. Rate limiter tracks `_last_request_time` and sleeps via `asyncio.sleep()` to maintain safe spacing. `extract_enrichment_data()` pulls CVSS (v3.1→v3.0→v2 fallback), primary CWE (skipping NVD-CWE-noinfo/NVD-CWE-Other), English description, and reference URLs into a flat dict.

2. **`cache.py`** — `CveCache` class with SQLite WAL mode, JSON-serialized data column, `put()`/`get()` with TTL-based expiry, context manager support, and XDG cache path convention (`$XDG_CACHE_HOME/oxpwn/cve-cache.db`).

3. **`__init__.py`** — Package init exporting `NvdClient`, `CveCache`, and `extract_enrichment_data`. Stubs for T02's `enrich_findings()` and `findings_from_tool_results()` noted in docstring.

## Verification

- `pytest tests/unit/test_nvd_client.py tests/unit/test_cve_cache.py -v` — **39/39 passed** in 0.23s
- CVE-2021-44228 fixture correctly parses with CVSS 10.0, severity CRITICAL, CWE-917
- CVSS fallback chain verified: v3.1 preferred → v3.0 (7.5/HIGH) → v2 (5.0/MEDIUM)
- CWE placeholder filtering verified: NVD-CWE-noinfo and NVD-CWE-Other skipped; mixed fixture finds CWE-79
- Rate limiter: 7s spacing without key, 0.6s with key, no sleep when enough time elapsed
- API key header present when key provided, absent when not; env var fallback works
- Cache: round-trip, upsert, TTL expiry with mocked time, WAL mode confirmed, directory creation, context manager
- Slice-level verification partial: `test_nvd_client.py` ✅, `test_cve_cache.py` ✅, `test_enrichment.py` — expected missing (T02)

## Diagnostics

- Query cache: `sqlite3 ~/.cache/oxpwn/cve-cache.db "SELECT cve_id, cached_at FROM cve_cache"`
- Structlog events: filter for `nvd.fetch`, `nvd.cache_hit`, `nvd.cache_miss`, `nvd.fetch_error`
- Rate limit events: `nvd.rate_limited` with `wait_seconds` field
- Error shape: `nvd.fetch_error` with `cve_id`, `status`, `body_head` (truncated to 200 chars)

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `src/oxpwn/enrichment/__init__.py` — Package init with public API exports and T02 stubs
- `src/oxpwn/enrichment/nvd.py` — Async NVD client, Pydantic response models, rate limiter, enrichment extractor
- `src/oxpwn/enrichment/cache.py` — SQLite CVE cache with WAL mode, TTL expiry, XDG path convention
- `tests/unit/test_nvd_client.py` — 23 tests: response parsing, CVSS fallback, CWE filtering, fetch, rate limiter, API key
- `tests/unit/test_cve_cache.py` — 16 tests: put/get, TTL, WAL, directory creation, context manager, schema, XDG path
