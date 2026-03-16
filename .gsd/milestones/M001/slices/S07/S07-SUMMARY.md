---
id: S07
parent: M001
milestone: M001
provides:
  - "Async NVD CVE 2.0 API client with rate limiting, Pydantic response models, and CVSS v3.1→v3.0→v2 fallback"
  - "SQLite CVE cache with WAL mode, 7-day TTL, and XDG cache path convention"
  - "CVE ID regex extraction from nuclei template_ids, nmap scripts, and arbitrary text"
  - "findings_from_tool_results() converts nuclei/ffuf/nmap ToolResult objects into Finding objects"
  - "enrich_findings() batch-deduplicates CVE IDs, resolves via cache→NVD, populates cvss/cwe_id/remediation on findings"
requires:
  - slice: S04
    provides: "Finding model from core/models.py; nuclei/ffuf/nmap parsed_output dict shapes from tool parsers"
affects:
  - S08
key_files:
  - src/oxpwn/enrichment/__init__.py
  - src/oxpwn/enrichment/nvd.py
  - src/oxpwn/enrichment/cache.py
  - src/oxpwn/enrichment/enrichment.py
  - tests/unit/test_nvd_client.py
  - tests/unit/test_cve_cache.py
  - tests/unit/test_enrichment.py
key_decisions:
  - "NVD enrichment proved with mocked HTTP responses and CVE-2021-44228 fixture data — no live NVD integration tests (Decision 31)"
  - "Finding extraction covers nuclei/ffuf/nmap only; httpx/subfinder are recon tools with no vulnerability signal (Decision 32)"
  - "Cache uses synchronous sqlite3 (not aiosqlite) — local I/O negligible latency (Decision 33)"
  - "Nmap findings only for ports with script output — plain open ports are not vulnerability signals (Decision 34)"
  - "NVD description used as remediation field — contains fix/mitigation context for first-pass guidance (Decision 35)"
patterns_established:
  - "Tool converter dispatcher: _TOOL_CONVERTERS dict maps tool_name → converter function for extensible finding extraction"
  - "Three-phase enrichment: collect CVE IDs → batch-resolve via cache/API → apply to findings, with per-phase error isolation"
  - "XDG cache convention mirrors ConfigManager's XDG config convention"
  - "NVD Pydantic response models use field aliases matching NVD JSON camelCase keys"
observability_surfaces:
  - "structlog events: nvd.fetch, nvd.rate_limited, nvd.fetch_error, nvd.cache_hit, nvd.cache_miss, nvd.cache_opened, nvd.cache_closed"
  - "structlog events: enrichment.resolving_cves, enrichment.cve_extracted, enrichment.finding_enriched, enrichment.skipped, enrichment.cve_resolve_error, enrichment.conversion_error"
  - "SQLite cache at ~/.cache/oxpwn/cve-cache.db queryable with sqlite3"
drill_down_paths:
  - .gsd/milestones/M001/slices/S07/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001/slices/S07/tasks/T02-SUMMARY.md
duration: 30m
verification_result: passed
completed_at: 2026-03-15
---

# S07: CVE Enrichment + Finding Quality

**NVD-backed CVE enrichment pipeline that converts nuclei/ffuf/nmap tool results into Finding objects enriched with CVE IDs, CVSS scores, CWE classification, and remediation guidance — with SQLite caching and graceful degradation.**

## What Happened

Built the `src/oxpwn/enrichment/` package in two tasks:

**T01** created the data access layer: an async NVD CVE 2.0 API client (`NvdClient`) with `httpx.AsyncClient`, timestamp-based rate limiting (7s public / 0.6s with API key), and Pydantic response models matching the NVD JSON shape. The `extract_enrichment_data()` function pulls CVSS scores (v3.1→v3.0→v2 fallback chain), primary CWE IDs (filtering `NVD-CWE-noinfo`/`NVD-CWE-Other` placeholders), English descriptions, and reference URLs. A `CveCache` class provides SQLite persistence with WAL mode, 7-day TTL, JSON-serialized data, and XDG cache path convention.

**T02** built the enrichment orchestrator: `extract_cve_ids()` for regex-based CVE ID extraction (case-insensitive, normalized to uppercase), `findings_from_tool_results()` dispatching to tool-specific converters (nuclei→richest findings with template_id/severity/url, ffuf→content discovery entries, nmap→only ports with vuln script output), and `enrich_findings()` implementing three-phase batch enrichment (collect CVE IDs → deduplicate and resolve via cache/NVD → apply cvss/cwe_id/remediation to matching findings). Each phase isolates errors so individual failures don't crash the pipeline.

## Verification

- `pytest tests/unit/test_nvd_client.py tests/unit/test_cve_cache.py tests/unit/test_enrichment.py -v` — **60/60 passed** in 0.33s
- Full unit suite: **252/252 passed** in 1.56s (no regressions)
- `python3 -c "from oxpwn.enrichment import enrich_findings, findings_from_tool_results, NvdClient, CveCache; print('OK')"` — OK

### Coverage matrix (all proven):
- ✅ NVD client fetch/rate-limit/error-handling (23 tests)
- ✅ Cache put/get/TTL-expiry/WAL-mode/XDG-paths (16 tests)
- ✅ CVE ID extraction from nuclei/nmap/plain-text (8 tests)
- ✅ Finding extraction from nuclei/ffuf/nmap tool results (7 tests)
- ✅ Enrichment populating all 4 Finding fields (cvss, cwe_id, cve_id, remediation) (6 tests)
- ✅ Graceful degradation on NVD errors
- ✅ CWE placeholder filtering (NVD-CWE-noinfo, NVD-CWE-Other)
- ✅ CVSS version fallback chain (v3.1→v3.0→v2)
- ✅ Batch deduplication of CVE IDs
- ✅ Cache hits avoid redundant NVD API calls

## Requirements Advanced

- R006 — CVE/NVD enrichment pipeline fully implemented with NVD client, cache, finding extraction, and enrichment orchestrator

## Requirements Validated

- R006 — 60 unit tests prove CVE ID extraction, CVSS/CWE/remediation enrichment from NVD data, cache behavior, rate limiting, error handling, and graceful degradation. Live NVD integration deferred to S08.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

None.

## Known Limitations

- Enrichment is not yet wired into the agent loop — S08 will integrate `enrich_findings()` after phase completion
- NVD API live integration not tested (by design — NVD is flaky); S08 validates end-to-end
- Only nuclei/ffuf/nmap produce findings; httpx/subfinder are recon-only (by design)

## Follow-ups

- S08: Wire `enrich_findings()` into the ReactAgent post-phase pipeline
- S08: Validate enrichment against real Juice Shop scan findings with live NVD API

## Files Created/Modified

- `src/oxpwn/enrichment/__init__.py` — Package init with public API exports
- `src/oxpwn/enrichment/nvd.py` — Async NVD client, Pydantic response models, rate limiter, enrichment data extractor
- `src/oxpwn/enrichment/cache.py` — SQLite CVE cache with WAL mode, TTL expiry, XDG path convention
- `src/oxpwn/enrichment/enrichment.py` — CVE extraction, finding conversion (nuclei/ffuf/nmap), enrichment orchestrator
- `tests/unit/test_nvd_client.py` — 23 tests for NVD client
- `tests/unit/test_cve_cache.py` — 16 tests for CVE cache
- `tests/unit/test_enrichment.py` — 21 tests for enrichment orchestrator

## Forward Intelligence

### What the next slice should know
- `enrich_findings(findings, client, cache)` is the single entry point — create `NvdClient()` and `CveCache()`, call `findings_from_tool_results()` on the agent's tool results, then pass to `enrich_findings()`
- The enrichment module is fully async — `enrich_findings()` is an `async` function that needs to be awaited
- `NvdClient` accepts an optional `api_key` param or reads `NVD_API_KEY` from env; without a key, rate limiting is 7s between requests (slow but functional)

### What's fragile
- NVD API availability — the real API has documented outages; enrichment degrades gracefully but unenriched findings are expected in unreliable network conditions
- Rate limiter is timestamp-based (simple) — if multiple concurrent enrichment calls happen, they share the same client's `_last_request_time` which is correct but sequential

### Authoritative diagnostics
- `sqlite3 ~/.cache/oxpwn/cve-cache.db "SELECT cve_id, cached_at FROM cve_cache"` — shows cached CVE entries
- structlog events filtered by `nvd.*` and `enrichment.*` namespaces — full pipeline visibility
- Test command: `pytest tests/unit/test_nvd_client.py tests/unit/test_cve_cache.py tests/unit/test_enrichment.py -v`

### What assumptions changed
- None — the slice executed exactly as planned
