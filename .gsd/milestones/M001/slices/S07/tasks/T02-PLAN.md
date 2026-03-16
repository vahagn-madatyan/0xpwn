---
estimated_steps: 5
estimated_files: 3
---

# T02: Build finding extraction and CVE enrichment orchestrator

**Slice:** S07 — CVE Enrichment + Finding Quality
**Milestone:** M001

## Description

Build the enrichment orchestrator that bridges raw tool results and enriched findings. This is the business logic layer that (1) converts nuclei/ffuf/nmap `parsed_output` dicts into `Finding` objects, (2) extracts CVE IDs via regex, and (3) orchestrates batch NVD lookups through T01's client and cache to populate `cve_id`, `cvss`, `cwe_id`, and `remediation` on each finding.

The critical hidden prerequisite from S07 research: the ReAct agent loop accumulates `ToolResult` objects but never creates `Finding` objects. Without a `findings_from_tool_results()` converter, there's nothing to enrich. This task closes that gap.

## Steps

1. Build `src/oxpwn/enrichment/enrichment.py`:
   - `CVE_REGEX = re.compile(r'CVE-\d{4}-\d{4,}', re.IGNORECASE)` for extracting CVE IDs from any text.
   - `extract_cve_ids(text: str) -> list[str]` — find all CVE IDs in text, normalize to uppercase, deduplicate.
   - `findings_from_tool_results(tool_results: list[ToolResult]) -> list[Finding]`:
     - **Nuclei** (`tool_name == "nuclei"`): map each entry in `parsed_output["findings"]` → `Finding` with `title=name or template_id`, `severity` mapped from nuclei severity to `Severity` enum, `description` from nuclei description, `url` from `matched_at` or `url`, `evidence=template_id`, `tool_name="nuclei"`, `cve_id` extracted from `template_id` if it matches CVE regex.
     - **Ffuf** (`tool_name == "ffuf"`): map each entry in `parsed_output["findings"]` → `Finding` with `title=f"Content discovered: {url}"`, `severity=Severity.info`, `description` noting the status code and content type, `url` from finding url, `evidence` from inputs dict, `tool_name="ffuf"`.
     - **Nmap** (`tool_name == "nmap"`): map open ports with vuln script output → `Finding` with `title` from script id, `severity=Severity.medium` (default for nmap script findings), `description` from script output, `url` from address+port, `evidence=script output`, `tool_name="nmap"`, `cve_id` extracted from script output text if CVE regex matches. Skip plain port/service entries (no vulnerability signal).
     - Skip tool results with `parsed_output is None` or unknown tool names.
   - `enrich_findings(findings: list[Finding], client: NvdClient, cache: CveCache) -> list[Finding]`:
     - Collect all CVE IDs from findings (from `cve_id` field and regex extraction from `title`/`description`/`evidence`).
     - Batch-deduplicate CVE IDs.
     - For each unique CVE ID: check cache first, then fetch from NVD client.
     - For each finding with a matched CVE ID: populate `cvss`, `cwe_id`, `remediation` from the resolved NVD data. Use `extract_enrichment_data()` from T01's nvd module.
     - Log `enrichment.finding_enriched` or `enrichment.skipped` per finding.
     - Return the mutated findings list (same objects, modified in-place).
     - Wrap each per-finding enrichment in try/except — log and skip on error, never crash.
2. Update `src/oxpwn/enrichment/__init__.py` with public API exports: `enrich_findings`, `findings_from_tool_results`, `NvdClient`, `CveCache`.
3. Write `tests/unit/test_enrichment.py`:
   - **CVE ID extraction tests**: extract from nuclei template_id `"CVE-2021-44228"`, extract from mixed text `"Found cve-2023-22515 in header"`, extract multiple CVEs from one string, normalize to uppercase, return empty for no-match text.
   - **Finding extraction tests**:
     - Nuclei tool result with realistic `parsed_output` → produces Finding with correct title/severity/url/cve_id.
     - Ffuf tool result with realistic `parsed_output` → produces info-severity Finding with URL and status.
     - Nmap tool result with vuln script output → produces Finding with CVE extracted from script text.
     - Nmap tool result with only open ports (no scripts) → produces no findings (not vulnerability signal).
     - Tool result with `parsed_output=None` → skipped gracefully.
     - Unknown tool name → skipped gracefully.
   - **Enrichment orchestrator tests** (mock NvdClient and CveCache):
     - Finding with CVE ID → enriched with CVSS, CWE, remediation from mocked NVD data.
     - Multiple findings referencing same CVE → only one NVD fetch (batch dedup proven).
     - Finding without CVE ID → left unenriched, logged as skipped.
     - NVD client error for one CVE → that finding skipped, others still enriched (graceful degradation).
     - Cache hit → no NVD client fetch (cache bypass proven).
     - End-to-end: tool results → findings → enrichment pipeline with all fields populated.
4. Run full slice verification: `pytest tests/unit/test_nvd_client.py tests/unit/test_cve_cache.py tests/unit/test_enrichment.py -v` — all pass.
5. Verify the public API surface: `python3 -c "from oxpwn.enrichment import enrich_findings, findings_from_tool_results, NvdClient, CveCache; print('OK')"` succeeds.

## Must-Haves

- [ ] `findings_from_tool_results()` converts nuclei findings into `Finding` objects with CVE IDs extracted from template_ids
- [ ] `findings_from_tool_results()` converts ffuf findings into info-severity `Finding` objects with discovered URLs
- [ ] `findings_from_tool_results()` converts nmap vuln script results into `Finding` objects with CVE IDs extracted from script output
- [ ] `extract_cve_ids()` regex finds CVE IDs case-insensitively and normalizes to uppercase
- [ ] `enrich_findings()` batch-deduplicates CVE IDs before NVD resolution
- [ ] `enrich_findings()` populates `cvss`, `cwe_id`, and `remediation` from NVD data on findings with CVE IDs
- [ ] `enrich_findings()` uses cache before NVD client (cache hit avoids API call)
- [ ] Graceful degradation: per-finding errors are logged and skipped, never crash the pipeline
- [ ] Public API exports work: `from oxpwn.enrichment import enrich_findings, findings_from_tool_results`

## Verification

- `pytest tests/unit/test_enrichment.py -v` — all tests pass
- `pytest tests/unit/test_nvd_client.py tests/unit/test_cve_cache.py tests/unit/test_enrichment.py -v` — full slice verification passes
- `python3 -c "from oxpwn.enrichment import enrich_findings, findings_from_tool_results, NvdClient, CveCache; print('OK')"` — imports succeed

## Inputs

- `src/oxpwn/enrichment/nvd.py` — `NvdClient`, `extract_enrichment_data()` from T01
- `src/oxpwn/enrichment/cache.py` — `CveCache` from T01
- `src/oxpwn/core/models.py` — `Finding`, `Severity`, `ToolResult` models
- `src/oxpwn/sandbox/tools/nuclei.py` — `NucleiFinding` shape and `parsed_output` dict structure
- `src/oxpwn/sandbox/tools/ffuf.py` — `FfufFinding` shape and `parsed_output` dict structure
- `src/oxpwn/sandbox/tools/nmap.py` — `parse_nmap_xml()` output dict structure

## Expected Output

- `src/oxpwn/enrichment/enrichment.py` — CVE extraction, finding conversion, enrichment orchestrator
- `src/oxpwn/enrichment/__init__.py` — updated with public API exports
- `tests/unit/test_enrichment.py` — comprehensive tests for extraction, conversion, and enrichment
