# S07: CVE Enrichment + Finding Quality — Research

**Date:** 2026-03-15

## Summary

S07 builds the NVD enrichment pipeline that takes raw tool findings and augments them with CVE IDs, CVSS v3.1 scores, CWE classification, and remediation references from the NVD API. The existing `Finding` model already has the destination fields (`cve_id`, `cvss`, `cwe_id`, `remediation`) — they're all `Optional[None]` today and never populated. The NVD REST API at `services.nvd.nist.gov/rest/json/cves/2.0` has been validated as working, supports both direct CVE ID lookup and keyword search, and returns structured JSON with CVSS v3.1/v2 metrics, CWE arrays, descriptions, and references.

The primary enrichment source is nuclei template IDs, which frequently embed CVE IDs directly (e.g., `CVE-2021-44228` as a template_id). For findings without explicit CVE IDs, keyword-based search against NVD provides fallback enrichment. Rate limiting (5 req/30s without key, 50/30s with key) requires a local SQLite cache and request throttling. No new dependencies are needed — `httpx` (async), `sqlite3` (stdlib), and `pydantic` are already in the project.

One critical finding: the current ReAct agent loop (`react.py`) adds `ToolResult` objects to `ScanState.tool_results` but **never calls `add_finding()`**. Findings are structurally present on the model but empty during actual scans. S07 must therefore include a finding extraction step that converts tool parsed_output (especially nuclei/ffuf findings) into `Finding` objects before enrichment can operate on them. This is the hidden prerequisite the S04 forward intelligence didn't explicitly call out.

## Recommendation

Build a three-layer enrichment module at `src/oxpwn/enrichment/`:

1. **`nvd.py` — NVD API client**: Async `httpx.AsyncClient` wrapper with rate-limiting (token bucket or simple sleep-based throttle), API key support via env var `NVD_API_KEY`, and Pydantic response models for the CVE 2.0 response shape. Supports both `cveId=CVE-XXXX-XXXX` (direct lookup) and `keywordSearch=...` (fallback).

2. **`cache.py` — SQLite CVE cache**: File-backed cache at `~/.cache/oxpwn/cve-cache.db` with TTL-based expiry (default 7 days). Keyed by CVE ID. Stores the enrichment-relevant subset (CVSS score, severity, CWE IDs, description, references) as JSON. Eliminates redundant API calls across scans and stays within rate limits.

3. **`enrichment.py` — Enrichment orchestrator**: Takes a list of `Finding` objects, extracts CVE IDs (regex from `cve_id` field, nuclei `template_id`, or title/description), batch-resolves against cache then NVD, and mutates the Finding fields (`cve_id`, `cvss`, `cwe_id`, `remediation`). Also includes a `findings_from_tool_results()` helper that converts nuclei/ffuf/nmap parsed_output dicts into `Finding` objects.

Integration point: called from the agent loop after phase completion (or from S08's end-to-end flow), operating on `ScanState.findings` in-place.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| HTTP client with async | `httpx.AsyncClient` (already a dep) | Already in pyproject.toml, proven async support, tested against NVD in research |
| Local caching | `sqlite3` (stdlib) | Zero new dependencies, sufficient for single-user key-value cache with TTL |
| Rate limiting | Simple `asyncio.sleep()` + timestamp tracking | NVD rate limits are simple (5 or 50 per 30s window); no need for a rate-limiting library |
| CVE response parsing | Pydantic models | Consistent with every other parser in the codebase (nuclei, ffuf, httpx, etc.) |
| CVE ID extraction | `re.compile(r'CVE-\d{4}-\d{4,}', re.IGNORECASE)` | Nuclei template_ids directly embed CVE IDs; regex is sufficient and proven |

## Existing Code and Patterns

- `src/oxpwn/core/models.py` — `Finding` already has `cve_id: str | None`, `cvss: float | None`, `cwe_id: str | None`, `remediation: str | None` fields with a CVSS range validator (0.0–10.0). This is the target data model — enrichment populates these fields.
- `src/oxpwn/sandbox/tools/nuclei.py` — `NucleiFinding` has `template_id`, `severity`, `name`, `description`, `matched_at`, `url` — the richest source for CVE extraction. Template IDs like `CVE-2021-44228` directly map to NVD lookups.
- `src/oxpwn/sandbox/tools/ffuf.py` — `FfufFinding` has `url`, `status`, `inputs` — content discovery findings that won't have CVE IDs but may benefit from CWE classification (e.g., CWE-538 for exposed files).
- `src/oxpwn/sandbox/tools/nmap.py` — `parse_nmap_xml()` returns hosts/ports/services/scripts. Nmap script output (e.g., `http-vuln-*`) sometimes references CVEs in the script output text.
- `src/oxpwn/agent/react.py` — The ReAct loop dispatches tools and accumulates `ToolResult` but does NOT create `Finding` objects. `scan_state.findings` is always empty in current flow. Enrichment must bridge this gap.
- `src/oxpwn/agent/tools.py` — `ToolRegistry`/`register_default_tools()` pattern. Enrichment is NOT a tool — it's a post-processing step, so it doesn't register here.
- `tests/conftest.py` — Has a `sample_finding` fixture with `cve_id="CVE-2024-1234"`, `cvss=9.8`, `cwe_id="CWE-89"` — proves the model accepts enrichment data. Reuse this pattern for enrichment tests.
- `src/oxpwn/config/manager.py` — Config manager pattern with XDG paths. Cache path should follow same XDG convention (`XDG_CACHE_HOME/oxpwn/`).

## Constraints

- **NVD rate limit without API key: 5 requests per 30 seconds** — this is the binding constraint for scans with many findings. A scan finding 10+ CVEs will need request throttling and caching to avoid 403 errors.
- **NVD rate limit with API key: 50 requests per 30 seconds** — significantly better but still requires throttling for large scans.
- **NVD API key is optional** — the enrichment module must work without one, degrading gracefully to slower throughput. API key passed via `NVD_API_KEY` env var or config.
- **httpx is already `>=0.24` in pyproject.toml** — must use the installed version (0.28.1). `httpx.AsyncClient` is the async HTTP path.
- **sqlite3 is stdlib** — no new dependency needed, but cache DB must be created atomically and handle concurrent access safely (WAL mode).
- **No new pip dependencies** — everything needed (`httpx`, `sqlite3`, `pydantic`, `structlog`, `asyncio`) is already available.
- **Finding model fields are fixed** — `cve_id`, `cvss`, `cwe_id`, `remediation` are already defined with their types. Enrichment populates them, does not change them.
- **CVSS validator rejects > 10.0 or < 0.0** — NVD scores are always 0.0–10.0, so this is safe, but the enrichment code should still validate.
- **NVD may return CVSS v3.1, v3.0, v2, or v4.0** — prefer v3.1, fall back to v3.0, then v2. v4.0 is rare and can be ignored for M001.
- **NVD may return multiple CWE IDs per CVE** — the `Finding.cwe_id` field is a single string. Use the primary (source: `nvd@nist.gov`) CWE, or the first one.
- **Findings with `NVD-CWE-noinfo` or `NVD-CWE-Other` CWE** — these are NVD placeholders, not real CWEs. Skip them during enrichment.

## Common Pitfalls

- **Calling NVD API without rate limiting** — API returns 403 and may temporarily block the IP. Must implement request throttling with `asyncio.sleep()` between calls (6 seconds recommended by NVD for safety, 7 seconds without API key to stay under 5/30s).
- **Not handling NVD API downtime gracefully** — NVD has scheduled maintenance windows. Enrichment must degrade to unenriched findings, not crash the scan. Use try/except with structlog warnings.
- **Treating nuclei template_ids as always containing CVE IDs** — many template IDs are descriptive names like `http-missing-security-headers` or `exposed-admin-panel`. Only extract when the CVE regex matches.
- **Keyword search returning irrelevant CVEs** — NVD keyword search (`keywordSearch=sql injection`) returns broad results. Must use `keywordExactMatch` and pick the highest-relevance result, or skip enrichment rather than attach a wrong CVE.
- **SQLite cache corruption on Ctrl+C** — use WAL journal mode and keep transactions short. Atomic writes prevent partial cache entries.
- **Forgetting to normalize CVE IDs to uppercase** — NVD requires `CVE-XXXX-XXXX` format. Nuclei may emit lowercase `cve-2021-44228`. Always `.upper()` before lookup.
- **Enriching the same CVE multiple times** — batch-deduplicate CVE IDs before API calls. A scan may have multiple findings referencing the same CVE.
- **Not creating `Finding` objects from tool results** — the current agent loop never calls `add_finding()`. Without a finding-extraction step, there's nothing to enrich. This is the most dangerous gap.

## Open Risks

- **NVD API availability** — NVD has had extended outages (2024 backlog documented). Integration tests that hit NVD directly may be flaky. Mitigation: unit tests use fixtures/mocks; integration tests have skip-on-network-failure like S04's subfinder pattern.
- **Finding extraction quality** — Converting tool `parsed_output` dicts to `Finding` objects requires mapping tool-specific fields (nuclei severity, nmap script output) to the generic `Finding` model. The mapping heuristics may miss edge cases or produce low-quality findings that don't benefit from enrichment.
- **Keyword search false positives** — NVD keyword search may return CVEs unrelated to the actual finding. A conservative approach (only enrich when CVE ID is explicitly present, skip keyword-based enrichment for M001) would be safer but less useful.
- **Cache path permissions** — `~/.cache/oxpwn/` must be writable. Containerized environments may not have a writable home directory. Fallback to in-memory cache or temp directory.
- **The agent loop doesn't produce findings yet** — S07 can build and test the enrichment pipeline against manually created findings and fixture data, but end-to-end proof (real scan → real findings → real enrichment) depends on S08 or on adding a finding-extraction step to the agent loop within S07.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| NVD/CVE API | `dengineproblem/agents-monorepo@cve-tracking-system` (57 installs) | available — not directly relevant (tracking system, not enrichment pipeline) |
| NVD/CVE API | `fusengine/agents@cve-research` (15 installs) | available — low install count, tangential |
| Pydantic | none found | no relevant skill |
| Security/pentesting | `prompt-security/clawsec@clawsec-feed` (99 installs) | available — security feed, not enrichment |

No skills installed — the NVD API is straightforward REST and the codebase patterns are well-established. Installing a CVE tracking skill would add complexity without value for this slice.

## Sources

- NVD CVE API 2.0 base URL: `https://services.nvd.nist.gov/rest/json/cves/2.0` with `cveId` and `keywordSearch` parameters validated via live calls (source: [NVD API Docs](https://nvd.nist.gov/developers/vulnerabilities))
- Rate limits confirmed: 5 req/30s public, 50 req/30s with API key, 6-second sleep recommended between requests (source: [NVD Getting Started](https://nvd.nist.gov/developers/start-here))
- NVD CVE response structure validated: `vulnerabilities[].cve.{id, descriptions, metrics.cvssMetricV31[].cvssData.{baseScore, baseSeverity, vectorString}, weaknesses[].description[].value, references[]}` (source: live API calls against CVE-2021-44228 and CVE-2023-22515)
- Multiple CWE IDs possible per CVE (e.g., CVE-2021-44228 has CWE-20, CWE-400, CWE-502, CWE-917 from different sources); NVD-sourced CWE should be preferred
- NVD keyword search returns paginated results with `totalResults` count; useful for finding-to-CVE correlation but requires careful relevance filtering
- `httpx.AsyncClient` confirmed working for async NVD calls (tested in research)
- `sqlite3` module confirmed available (v3.50.4) for local caching
