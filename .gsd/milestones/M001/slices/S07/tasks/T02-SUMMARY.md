---
id: T02
parent: S07
milestone: M001
provides:
  - "findings_from_tool_results() converts nuclei/ffuf/nmap ToolResult objects into Finding objects with CVE IDs extracted"
  - "enrich_findings() batch-deduplicates CVE IDs, resolves via cache→NVD, populates cvss/cwe_id/remediation on findings"
  - "extract_cve_ids() regex utility for case-insensitive CVE ID extraction from arbitrary text"
key_files:
  - src/oxpwn/enrichment/enrichment.py
  - src/oxpwn/enrichment/__init__.py
  - tests/unit/test_enrichment.py
key_decisions:
  - "Nmap findings only created for ports with script output (not plain open ports) — plain port/service entries are not vulnerability signals"
  - "Enrichment uses NVD description as remediation field — NVD descriptions contain fix/mitigation context that serves as first-pass remediation guidance"
  - "enrich_findings() mutates findings in-place and returns the same list — avoids unnecessary copies for large finding sets"
patterns_established:
  - "Tool converter dispatcher pattern: _TOOL_CONVERTERS dict maps tool_name → converter function, making new tool support a single function + dict entry"
  - "Three-phase enrichment: collect CVE IDs → batch-resolve via cache/API → apply to findings, with per-phase error isolation"
observability_surfaces:
  - "structlog events: enrichment.resolving_cves (batch start), enrichment.cve_extracted, enrichment.finding_enriched, enrichment.skipped, enrichment.cve_resolve_error, enrichment.conversion_error"
duration: 15m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Build finding extraction and CVE enrichment orchestrator

**Built the enrichment orchestrator that converts nuclei/ffuf/nmap ToolResult objects into Finding objects and batch-enriches them with NVD CVE data (CVSS, CWE, remediation).**

## What Happened

Implemented `src/oxpwn/enrichment/enrichment.py` with three core functions:

1. **`extract_cve_ids(text)`** — regex-based CVE ID extraction, case-insensitive, normalizes to uppercase, deduplicates while preserving order.

2. **`findings_from_tool_results(tool_results)`** — dispatches to tool-specific converters:
   - Nuclei: maps each finding with template_id→evidence, nuclei severity→Severity enum, matched_at→url, extracts CVE from template_id
   - Ffuf: maps each finding as info-severity content discovery with URL and status
   - Nmap: only creates findings for ports with script output (vuln signal), extracts CVE IDs from script text

3. **`enrich_findings(findings, client, cache)`** — three-phase async orchestrator:
   - Phase 1: Collect all CVE IDs from cve_id/title/description/evidence fields across all findings
   - Phase 2: Batch-deduplicate, resolve each unique CVE via cache→NVD API (using T01's client and cache)
   - Phase 3: Apply enrichment data (cvss, cwe_id, remediation) to matching findings

Updated `__init__.py` with all public exports. Wrote 21 comprehensive tests covering CVE extraction, finding conversion for all 3 tools, enrichment orchestration with mocks.

## Verification

- `pytest tests/unit/test_enrichment.py -v` — **21/21 passed**
- `pytest tests/unit/test_nvd_client.py tests/unit/test_cve_cache.py tests/unit/test_enrichment.py -v` — **60/60 passed** (full slice verification)
- `python3 -c "from oxpwn.enrichment import enrich_findings, findings_from_tool_results, NvdClient, CveCache; print('OK')"` — **OK**

### Slice verification status (final task — all must pass):
- ✅ Full slice test suite: 60/60 pass
- ✅ NVD client fetch/rate-limit/error-handling
- ✅ Cache put/get/TTL-expiry/WAL-mode
- ✅ CVE ID extraction from nuclei/nmap/plain-text
- ✅ Finding extraction from all 3 tool result shapes
- ✅ Enrichment populating all 4 Finding fields
- ✅ Graceful degradation on NVD errors
- ✅ CWE placeholder filtering
- ✅ CVSS version fallback chain
- ✅ Public API imports

## Diagnostics

- structlog events: `enrichment.resolving_cves`, `enrichment.cve_extracted`, `enrichment.finding_enriched`, `enrichment.skipped`, `enrichment.cve_resolve_error`, `enrichment.conversion_error`, `enrichment.skipped_no_output`, `enrichment.skipped_unknown_tool`
- All NVD-level diagnostics from T01 remain active (`nvd.fetch`, `nvd.cache_hit`, `nvd.cache_miss`, `nvd.fetch_error`, `nvd.rate_limited`)

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `src/oxpwn/enrichment/enrichment.py` — CVE extraction, finding conversion (nuclei/ffuf/nmap), enrichment orchestrator
- `src/oxpwn/enrichment/__init__.py` — updated public API exports with enrich_findings and findings_from_tool_results
- `tests/unit/test_enrichment.py` — 21 tests: CVE extraction (8), finding conversion (7), enrichment orchestration (6)
