# S07: CVE Enrichment + Finding Quality — UAT

**Milestone:** M001
**Written:** 2026-03-15

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: The enrichment pipeline is pure data transformation (tool results → findings → NVD lookup → enriched findings). Unit tests with realistic CVE-2021-44228 fixture data and mocked HTTP responses prove correctness without requiring a running NVD API. Live end-to-end validation is deferred to S08.

## Preconditions

- `pip install -e .` completed successfully
- Python 3.12+ available
- No Docker, NVD API, or network access required

## Smoke Test

```bash
pytest tests/unit/test_nvd_client.py tests/unit/test_cve_cache.py tests/unit/test_enrichment.py -v
# Expected: 60/60 passed
```

## Test Cases

### 1. NVD response parsing with CVSS fallback

1. Run `pytest tests/unit/test_nvd_client.py::TestExtractEnrichmentData -v`
2. **Expected:** All 5 tests pass — CVSS v3.1 preferred, v3.0 fallback works, v2 fallback works, CWE placeholders filtered, English description selected

### 2. CVE cache lifecycle

1. Run `pytest tests/unit/test_cve_cache.py -v`
2. **Expected:** All 16 tests pass — round-trip storage, TTL expiry, WAL mode, XDG path convention, context manager cleanup

### 3. CVE ID extraction from tool output

1. Run `pytest tests/unit/test_enrichment.py::TestExtractCveIds -v`
2. **Expected:** All 8 tests pass — extracts from nuclei template_ids (e.g., `CVE-2021-44228`), case-insensitive matching, deduplication, uppercase normalization

### 4. Finding conversion from tool results

1. Run `pytest tests/unit/test_enrichment.py::TestFindingsFromToolResults -v`
2. **Expected:** All 7 tests pass — nuclei findings include severity/url/evidence, ffuf findings are info-severity content discovery, nmap only creates findings for script output, unknown tools skipped

### 5. End-to-end enrichment pipeline

1. Run `pytest tests/unit/test_enrichment.py::TestEnrichFindings::test_end_to_end_pipeline -v`
2. **Expected:** Passes — nuclei tool result with CVE-2021-44228 template_id converts to Finding, enrichment populates cvss=10.0, cwe_id=CWE-917, remediation from NVD description

### 6. Graceful degradation

1. Run `pytest tests/unit/test_enrichment.py::TestEnrichFindings::test_nvd_error_graceful_degradation -v`
2. **Expected:** Passes — NVD API errors produce warnings, finding remains valid but unenriched

## Edge Cases

### CWE placeholder filtering

1. Run `pytest tests/unit/test_nvd_client.py::TestExtractEnrichmentData::test_cwe_placeholder_filtering -v`
2. **Expected:** `NVD-CWE-noinfo` and `NVD-CWE-Other` produce `cwe_id=None`, not the placeholder string

### Cache TTL expiry

1. Run `pytest tests/unit/test_cve_cache.py::TestTTLExpiry -v`
2. **Expected:** Data within 7-day TTL is returned; expired data returns None (forces fresh NVD fetch)

### Batch CVE deduplication

1. Run `pytest tests/unit/test_enrichment.py::TestEnrichFindings::test_batch_dedup_same_cve -v`
2. **Expected:** Multiple findings referencing the same CVE ID result in only one NVD API call

## Failure Signals

- Any test failure in the 60-test suite
- Import errors from `from oxpwn.enrichment import enrich_findings, findings_from_tool_results, NvdClient, CveCache`
- `NVD_API_KEY` appearing in any log output or error message (redaction violation)
- CVSS score not matching expected values for known CVEs in fixture data

## Requirements Proved By This UAT

- R006 — CVE/NVD enrichment for findings: 60 unit tests prove CVE ID extraction, CVSS/CWE/remediation enrichment, cache behavior, rate limiting, and graceful degradation

## Not Proven By This UAT

- Live NVD API integration (deferred to S08 — NVD is flaky)
- Enrichment wired into the agent loop (S08 responsibility)
- Enrichment of real Juice Shop scan findings (S08 end-to-end validation)

## Notes for Tester

- All tests use mocked HTTP responses with realistic NVD CVE 2.0 API shapes — no network access needed
- The CVE-2021-44228 (Log4Shell) fixture is the primary test case: CVSS 10.0, CWE-917, CRITICAL severity
- Cache tests use mocked time to verify TTL without waiting 7 days
- The enrichment module is not yet called by the agent — S08 will wire it in
