---
estimated_steps: 3
estimated_files: 3
---

# T02: Juice Shop integration test and acceptance checklist

**Slice:** S08 — End-to-End Validation
**Milestone:** M001

## Description

Prove the wired pipeline end-to-end against OWASP Juice Shop. Add a session-scoped Juice Shop Docker fixture, write a structural integration test exercising the full 5-phase scan through `_scan_async()`, and document the manual acceptance checklist for human verification of streaming quality and finding accuracy.

## Steps

1. In `tests/conftest.py`, add a session-scoped `juice_shop` fixture that pulls `bkimminich/juice-shop:latest`, starts it on port 3000 (configurable via `OXPWN_JUICESHOP_PORT`), waits for HTTP 200 on the root endpoint (up to 60s), and tears down the container after all tests. Skip if Docker is unreachable or the port is already in use. Return the target URL as `host.docker.internal:<port>`.

2. Create `tests/integration/test_e2e_juiceshop.py` with a single `test_full_scan_pipeline` integration test. It should: import `_scan_async` and `ScanRuntimeConfig` from `cli.main`, create a config targeting the Juice Shop URL from the fixture, call `await _scan_async(config)` directly (not through CliRunner — avoids subprocess timeout issues), and assert structural properties on the returned `ScanState`:
   - `phases_completed` has at least 3 entries (recon + scanning + at least one more)
   - `tool_results` is non-empty (agent executed at least one tool)
   - `findings` attribute exists (list, may be empty if LLM didn't find CVE-bearing vulns)
   - Scan completes without raising an exception
   - `total_tokens > 0` (LLM was used)
   Mark with `@pytest.mark.integration` and `@pytest.mark.timeout(600)`. Skip if Docker, LLM key, or Juice Shop are unavailable.

3. Create `.gsd/milestones/M001/slices/S08/ACCEPTANCE-CHECKLIST.md` with manual verification steps: run `0xpwn scan --target http://host.docker.internal:3000 --model <model>` and verify: (a) all 5 phase transitions render in Rich output, (b) agent reasoning shows tool selection rationale, (c) tool output streams incrementally, (d) scan summary shows findings/cost/duration, (e) no orphan Docker containers after scan, (f) enrichment fields (CVSS/CWE) appear on findings if CVE-bearing vulns were found, (g) container teardown is clean (check `docker ps --filter label=oxpwn.managed=true`).

## Must-Haves

- [ ] `juice_shop` fixture starts/stops Juice Shop container with readiness check
- [ ] Integration test calls `_scan_async()` against Juice Shop and asserts structural properties
- [ ] Integration test skips cleanly when Docker, LLM, or Juice Shop are unavailable
- [ ] Test uses 600s timeout for the full scan
- [ ] Acceptance checklist documents all manual verification steps
- [ ] All existing unit tests still pass

## Verification

- `pytest tests/integration/test_e2e_juiceshop.py -m integration -v --timeout=600` — passes or skips cleanly
- `pytest tests/unit/ -x -q` — no regressions
- `test -f .gsd/milestones/M001/slices/S08/ACCEPTANCE-CHECKLIST.md` — acceptance checklist exists

## Inputs

- `src/oxpwn/cli/main.py` — `_scan_async()` and `ScanRuntimeConfig` for direct invocation
- `tests/conftest.py` — existing `docker_sandbox` fixture pattern for session-scoped Docker lifecycle
- `tests/integration/test_cli_integration.py` — skip gating pattern with inline availability checks
- T01 outputs — 5-phase pipeline, enrichment wiring, extra_hosts support

## Expected Output

- `tests/conftest.py` — `juice_shop` session fixture added
- `tests/integration/test_e2e_juiceshop.py` — full pipeline integration test
- `.gsd/milestones/M001/slices/S08/ACCEPTANCE-CHECKLIST.md` — manual acceptance checklist
