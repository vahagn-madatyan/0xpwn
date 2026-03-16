# S08: End-to-End Validation — UAT

**Milestone:** M001
**Written:** 2026-03-15

## UAT Type

- UAT mode: mixed
- Why this mode is sufficient: Structural pipeline properties are verified by 261 unit tests and an integration test with structural assertions. Live scan quality, streaming UX, and finding accuracy require human observation documented in the acceptance checklist.

## Preconditions

- `pip install -e .` completed successfully
- Docker daemon running with access to pull images
- LLM provider configured (env var `GEMINI_API_KEY` or `OPENAI_API_KEY`, or Ollama running locally)
- OWASP Juice Shop running: `docker run -d -p 3000:3000 bkimminich/juice-shop:latest`
- Juice Shop responding at `http://localhost:3000`

## Smoke Test

Run `0xpwn scan --target http://localhost:3000` and confirm:
- Output begins streaming within 10 seconds
- Phase transition banners appear (at minimum: Recon, Scanning)
- Scan completes without crashing (exit code 0)

## Test Cases

### 1. Full 5-phase pipeline execution

1. Run `0xpwn scan --target http://localhost:3000`
2. Observe terminal output for phase transition banners
3. Wait for scan to complete (may take 5-15 minutes depending on model)
4. **Expected:** At least 3 of 5 phases appear in output (recon, scanning, exploitation, validation, reporting). Scan completes with a final summary.

### 2. Agent reasoning visibility

1. During the scan from Test 1, observe the reasoning output
2. **Expected:** Agent thinking blocks show tool selection rationale. Tool calls show the tool name and arguments. Tool results show parsed output (not raw XML/JSON dumps).

### 3. Enrichment execution

1. After scan completes, check the final summary output
2. **Expected:** If vulnerabilities were found, enriched findings show CVE IDs, CVSS scores, and/or CWE classifications. If no CVE-bearing vulnerabilities found, summary still displays without errors.

### 4. Container cleanup

1. After scan completes, run `docker ps --filter label=oxpwn.managed=true`
2. **Expected:** No containers with `oxpwn.managed=true` label are running. Sandbox container was cleaned up.

### 5. Integration test execution

1. Set LLM provider env var (e.g., `GEMINI_API_KEY`)
2. Run `pytest tests/integration/test_e2e_juiceshop.py -m integration -v --timeout=600`
3. **Expected:** Test passes with structural assertions (≥3 phases completed, non-empty tool results, findings list exists, tokens consumed).

## Edge Cases

### No LLM key configured

1. Unset all LLM-related env vars
2. Run `pytest tests/integration/test_e2e_juiceshop.py -m integration -v`
3. **Expected:** Test skips cleanly with descriptive skip message. No crash or hang.

### Juice Shop not running

1. Stop Juice Shop container
2. Run `pytest tests/integration/test_e2e_juiceshop.py -m integration -v`
3. **Expected:** Fixture detects port unavailability and skips. No crash or hang.

### Enrichment with no CVE-bearing findings

1. Run scan against a target with no known CVEs
2. **Expected:** Scan completes normally. `enriched_findings=0` in output. No crash from empty enrichment.

## Failure Signals

- Scan crashes with unhandled exception (enrichment failure should be caught, never crash)
- Phase transitions stop at scanning (regression to 2-phase)
- No streaming output — terminal hangs silently
- Docker containers leak after scan (`docker ps --filter label=oxpwn.managed=true` shows leftovers)
- `pytest tests/unit/ -x -q` shows fewer than 261 tests or any failures
- Integration test crashes instead of skipping when prerequisites are missing

## Requirements Proved By This UAT

- R001 — Autonomous 5-phase pentesting pipeline: UAT proves all 5 phases execute with tool selection, state accumulation, and phase transitions
- R002 — Isolated Docker/Kali sandbox execution: container lifecycle proven through scan execution and cleanup verification
- R004 — Real-time agent reasoning stream: streaming output quality verified by human observation during live scan
- R006 — CVE/NVD enrichment for findings: enrichment pipeline exercised on real scan findings (if CVE-bearing vulns found)

## Not Proven By This UAT

- R003 (Provider-agnostic LLM support) — only tested with one provider; multi-provider validation is a separate concern
- R005 (First-run wizard) — wizard UX tested in S06 UAT; this UAT assumes config is already set up
- Live NVD API reliability under rate limiting — cache covers happy path but sustained high-volume enrichment not tested
- Quality of findings against hardened targets — Juice Shop is intentionally vulnerable; real-world target effectiveness not measured

## Notes for Tester

- Scan duration varies significantly by LLM model. Gemini Flash: ~3-5 min. GPT-4: ~5-10 min. Local Ollama models: ~10-20 min.
- The exploitation and validation phases may produce minimal output if the LLM doesn't find exploitation-specific tools. This is expected — the guidance instructs the agent to synthesize and move on.
- `max_iterations_per_phase` defaults to 10 in the CLI. The integration test uses 5 to keep runtime reasonable.
- If enrichment shows `enriched_findings=0`, it means no CVE IDs were extractable from tool output — this is not a failure, just a data quality note.
- Refer to `.gsd/milestones/M001/slices/S08/ACCEPTANCE-CHECKLIST.md` for the detailed manual verification checklist with specific commands and expected outputs.
