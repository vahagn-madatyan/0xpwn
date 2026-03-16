# S07: CVE Enrichment + Finding Quality

**Goal:** Findings include CVE IDs, CVSS scores, CWE classification, and remediation guidance from NVD API with local caching
**Demo:** Unit tests prove that nuclei/ffuf/nmap tool results are converted into `Finding` objects, enriched via NVD with CVE-2021-44228 fixture data showing populated `cve_id`, `cvss`, `cwe_id`, and `remediation` fields, with cache hits avoiding redundant API calls

## Must-Haves

- NVD API client (`httpx.AsyncClient`) with rate-limiting (5 req/30s public, 50/30s with API key) and API key support via `NVD_API_KEY` env var
- SQLite CVE cache at `$XDG_CACHE_HOME/oxpwn/cve-cache.db` with 7-day TTL, WAL mode, atomic writes
- Pydantic response models for NVD CVE 2.0 API shape (CVSS v3.1→v3.0→v2 fallback, primary CWE selection, description, references)
- CVE ID extraction via regex from nuclei `template_id`, finding `title`/`description`, and nmap script output
- Finding extraction: `findings_from_tool_results()` converts nuclei/ffuf/nmap `parsed_output` dicts into `Finding` objects
- Enrichment orchestrator: batch-deduplicates CVE IDs, resolves cache→NVD, populates `cve_id`/`cvss`/`cwe_id`/`remediation` on Finding objects in-place
- Graceful degradation: NVD downtime/errors produce warnings, not crashes — unenriched findings are valid
- CVE IDs normalized to uppercase before lookup
- `NVD-CWE-noinfo` and `NVD-CWE-Other` CWE placeholders are skipped

## Proof Level

- This slice proves: contract — enrichment pipeline transforms tool outputs into enriched findings with correct NVD data
- Real runtime required: no — unit tests with mocked NVD responses and realistic fixture data are sufficient; real NVD API is flaky (documented outages)
- Human/UAT required: no

## Verification

- `pytest tests/unit/test_nvd_client.py tests/unit/test_cve_cache.py tests/unit/test_enrichment.py -v` — all pass
- Test coverage: NVD client fetch/rate-limit/error-handling, cache put/get/TTL-expiry/WAL-mode, CVE ID extraction from nuclei/nmap/plain-text, finding extraction from all 3 tool result shapes, enrichment populating all 4 Finding fields, graceful degradation on NVD errors, CWE placeholder filtering, CVSS version fallback chain

## Observability / Diagnostics

- Runtime signals: `structlog` events for `nvd.fetch`, `nvd.rate_limited`, `nvd.fetch_error`, `nvd.cache_hit`, `nvd.cache_miss`, `enrichment.cve_extracted`, `enrichment.finding_enriched`, `enrichment.skipped`
- Inspection surfaces: cache DB at `~/.cache/oxpwn/cve-cache.db` queryable with `sqlite3`
- Failure visibility: NVD errors logged with status code, CVE ID, and response body head; enrichment failures logged per-finding with skip reason
- Redaction constraints: `NVD_API_KEY` must not appear in logs or error messages

## Integration Closure

- Upstream surfaces consumed: `Finding` model from `core/models.py`, nuclei/ffuf/nmap `parsed_output` dict shapes from S04 tool parsers
- New wiring introduced in this slice: `src/oxpwn/enrichment/` module with `enrich_findings()` and `findings_from_tool_results()` entry points
- What remains before the milestone is truly usable end-to-end: S08 wires enrichment into the agent loop after phase completion and validates against a live Juice Shop scan

## Tasks

- [x] **T01: Build NVD API client with rate limiting and SQLite CVE cache** `est:1h`
  - Why: The data access layer that enrichment depends on — NVD fetch, rate limiting, response parsing, and caching must exist before the orchestrator can use them
  - Files: `src/oxpwn/enrichment/__init__.py`, `src/oxpwn/enrichment/nvd.py`, `src/oxpwn/enrichment/cache.py`, `tests/unit/test_nvd_client.py`, `tests/unit/test_cve_cache.py`
  - Do: Implement async NVD client with `httpx.AsyncClient` supporting both `cveId` direct lookup and `keywordSearch` with `keywordExactMatch`; add timestamp-based rate limiter (7s spacing without key, 0.6s with key); build Pydantic models for CVE 2.0 response; implement SQLite cache with WAL mode, 7-day TTL, JSON-serialized enrichment subset keyed by CVE ID; follow XDG cache path convention from config/manager.py
  - Verify: `pytest tests/unit/test_nvd_client.py tests/unit/test_cve_cache.py -v` — all pass
  - Done when: NVD client fetches CVE data from mocked responses, respects rate limits, handles errors gracefully; cache stores/retrieves/expires entries correctly

- [x] **T02: Build finding extraction and CVE enrichment orchestrator** `est:1h`
  - Why: Bridges the gap between raw tool results and enriched findings — extracts CVE IDs, converts tool output to Finding objects, and orchestrates the NVD lookup pipeline
  - Files: `src/oxpwn/enrichment/enrichment.py`, `src/oxpwn/enrichment/__init__.py`, `tests/unit/test_enrichment.py`
  - Do: Implement `findings_from_tool_results()` mapping nuclei findings (richest: template_id, severity, name, matched_at, url) → Finding, ffuf findings (url, status, content discovery) → Finding, nmap parsed_output (open ports, services, vuln scripts) → Finding; implement CVE ID regex extraction (`CVE-\d{4}-\d{4,}`, case-insensitive, normalized to uppercase); implement `enrich_findings()` that batch-deduplicates CVE IDs, resolves cache→NVD via T01 client, populates `cve_id`/`cvss`/`cwe_id`/`remediation` with CVSS v3.1→v3.0→v2 fallback, primary CWE selection (skip `NVD-CWE-noinfo`/`NVD-CWE-Other`), and description+references for remediation; degrade gracefully on per-finding errors
  - Verify: `pytest tests/unit/test_enrichment.py -v` — all pass
  - Done when: Tool results produce correct Finding objects; CVE IDs extracted from nuclei template_ids and nmap scripts; enrichment populates all 4 fields from realistic NVD fixture data; graceful degradation proven

## Files Likely Touched

- `src/oxpwn/enrichment/__init__.py`
- `src/oxpwn/enrichment/nvd.py`
- `src/oxpwn/enrichment/cache.py`
- `src/oxpwn/enrichment/enrichment.py`
- `tests/unit/test_nvd_client.py`
- `tests/unit/test_cve_cache.py`
- `tests/unit/test_enrichment.py`
