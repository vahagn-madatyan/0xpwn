---
estimated_steps: 6
estimated_files: 5
---

# T01: Build NVD API client with rate limiting and SQLite CVE cache

**Slice:** S07 — CVE Enrichment + Finding Quality
**Milestone:** M001

## Description

Build the data access layer for CVE enrichment: an async NVD API client with rate limiting and Pydantic response models, plus a file-backed SQLite cache with TTL-based expiry. This is the foundation the enrichment orchestrator (T02) depends on.

The NVD CVE 2.0 API at `services.nvd.nist.gov/rest/json/cves/2.0` supports direct CVE ID lookup (`cveId=CVE-XXXX-XXXX`) and keyword search (`keywordSearch=...&keywordExactMatch`). Rate limits are 5 req/30s without API key, 50/30s with key. The client must throttle requests with timestamp-based spacing and support optional `NVD_API_KEY` from env or constructor arg.

The cache stores enrichment-relevant CVE data (CVSS score, severity, CWE IDs, description, references) as JSON in SQLite with WAL journal mode and 7-day TTL. Cache path follows XDG convention: `$XDG_CACHE_HOME/oxpwn/cve-cache.db` (default `~/.cache/oxpwn/cve-cache.db`).

## Steps

1. Create `src/oxpwn/enrichment/__init__.py` with public API stubs (will be filled in T02).
2. Build `src/oxpwn/enrichment/nvd.py`:
   - Pydantic models for NVD CVE 2.0 response shape: `NvdCveResponse`, `NvdVulnerability`, `NvdCveItem`, `NvdCvssMetric`, `NvdWeakness` — focusing on the enrichment-relevant subset (baseScore, baseSeverity, vectorString, CWE IDs, descriptions, references).
   - `NvdClient` class: constructor takes optional `api_key` (falls back to `NVD_API_KEY` env var), creates `httpx.AsyncClient` with appropriate headers.
   - `fetch_cve(cve_id: str) -> NvdCveItem | None` — direct lookup by CVE ID, returns parsed Pydantic model or None on 404/error.
   - `search_cves(keyword: str, exact: bool = True) -> list[NvdCveItem]` — keyword search with optional exact match.
   - Rate limiter: track last request timestamp, sleep to maintain safe spacing (7s without key, 0.6s with key). Use `asyncio.sleep()`.
   - Error handling: log warnings via structlog on HTTP errors, return None/empty instead of raising. Never expose API key in logs.
   - Helper: `extract_enrichment_data(cve: NvdCveItem) -> dict` — extracts CVSS (v3.1→v3.0→v2 fallback), primary CWE (skip NVD-CWE-noinfo/NVD-CWE-Other), description, and reference URLs into a flat dict.
3. Build `src/oxpwn/enrichment/cache.py`:
   - `CveCache` class: constructor takes optional `db_path` (defaults to XDG cache path), creates parent dirs atomically, opens SQLite with WAL mode.
   - Schema: `cve_cache` table with `cve_id TEXT PRIMARY KEY`, `data TEXT` (JSON), `cached_at REAL` (unix timestamp).
   - `get(cve_id: str) -> dict | None` — return cached data if within TTL (7 days), None if expired or missing.
   - `put(cve_id: str, data: dict) -> None` — upsert with current timestamp.
   - `close() -> None` — close DB connection.
   - Context manager support (`__enter__`/`__exit__`).
4. Write `tests/unit/test_nvd_client.py`:
   - Mock `httpx.AsyncClient` responses with realistic NVD JSON fixtures (CVE-2021-44228 shape).
   - Test `fetch_cve` returns parsed data with correct CVSS/CWE/description.
   - Test `fetch_cve` returns None on 404 and on HTTP errors.
   - Test `extract_enrichment_data` CVSS version fallback chain (v3.1 → v3.0 → v2).
   - Test CWE placeholder filtering (NVD-CWE-noinfo, NVD-CWE-Other skipped).
   - Test rate limiter spacing (mock asyncio.sleep, verify call count/timing).
   - Test API key header presence when key is provided, absence when not.
5. Write `tests/unit/test_cve_cache.py`:
   - Test put/get round-trip with JSON data.
   - Test TTL expiry (mock time to advance past 7 days).
   - Test get returns None for missing CVE ID.
   - Test upsert overwrites existing entries.
   - Test WAL journal mode is set.
   - Test cache creates parent directories atomically.
   - Test cache works with in-memory path (`:memory:` or tmp_path).
6. Run `pytest tests/unit/test_nvd_client.py tests/unit/test_cve_cache.py -v` and fix until all pass.

## Must-Haves

- [ ] NVD client fetches and parses CVE data from mocked HTTP responses into Pydantic models
- [ ] Rate limiter enforces 7s spacing (no API key) or 0.6s spacing (with API key) between NVD requests
- [ ] CVSS version fallback: v3.1 preferred → v3.0 → v2, with score and severity extracted
- [ ] CWE extraction skips `NVD-CWE-noinfo` and `NVD-CWE-Other` placeholders
- [ ] SQLite cache with WAL mode stores/retrieves CVE data with 7-day TTL expiry
- [ ] Graceful degradation: HTTP errors and NVD downtime return None with structlog warnings, never raise
- [ ] API key never appears in log output

## Verification

- `pytest tests/unit/test_nvd_client.py tests/unit/test_cve_cache.py -v` — all tests pass
- Confirm NVD response models parse the CVE-2021-44228 fixture correctly (CVSS 10.0, CWE-917 or equivalent)
- Confirm cache TTL expiry works with mocked time advancement

## Observability Impact

- Signals added/changed: `nvd.fetch`, `nvd.rate_limited`, `nvd.fetch_error`, `nvd.cache_hit`, `nvd.cache_miss` structlog events
- How a future agent inspects this: query `~/.cache/oxpwn/cve-cache.db` with `sqlite3` to see cached CVE data
- Failure state exposed: NVD HTTP status code, CVE ID, and truncated response body logged on fetch errors

## Inputs

- `src/oxpwn/core/models.py` — `Finding` model with `cve_id`, `cvss`, `cwe_id`, `remediation` fields (target for enrichment)
- `src/oxpwn/config/manager.py` — XDG path convention to follow for cache directory
- S07-RESEARCH.md — NVD API response structure validated against CVE-2021-44228 and CVE-2023-22515
- Constraints: `httpx>=0.24` already in pyproject.toml, `sqlite3` is stdlib, no new dependencies

## Expected Output

- `src/oxpwn/enrichment/__init__.py` — package init with public API stubs
- `src/oxpwn/enrichment/nvd.py` — async NVD client with rate limiting, Pydantic response models, enrichment data extractor
- `src/oxpwn/enrichment/cache.py` — SQLite CVE cache with TTL, WAL mode, XDG path convention
- `tests/unit/test_nvd_client.py` — unit tests for NVD client, rate limiter, CVSS fallback, CWE filtering
- `tests/unit/test_cve_cache.py` — unit tests for cache put/get/TTL/WAL/directory creation
