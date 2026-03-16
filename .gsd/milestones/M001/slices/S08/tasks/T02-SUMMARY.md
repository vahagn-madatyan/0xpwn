---
id: T02
parent: S08
milestone: M001
provides:
  - Session-scoped Juice Shop Docker fixture for end-to-end testing
  - Structural integration test exercising full 5-phase pipeline via _scan_async()
  - Manual acceptance checklist for human verification of streaming quality and finding accuracy
key_files:
  - tests/conftest.py
  - tests/integration/test_e2e_juiceshop.py
  - .gsd/milestones/M001/slices/S08/ACCEPTANCE-CHECKLIST.md
key_decisions:
  - juice_shop fixture uses remove=True on container for automatic cleanup
  - Integration test calls _scan_async() directly (not CliRunner) to avoid subprocess timeout issues
  - Test uses max_iterations_per_phase=5 to keep scan duration reasonable while still exercising multi-phase flow
patterns_established:
  - juice_shop fixture returns host.docker.internal URL for cross-container reachability
  - Port availability check before starting fixture container (socket connect_ex)
  - Structural assertions pattern — assert pipeline properties without depending on LLM output content
observability_surfaces:
  - Integration test skip reasons visible in pytest output (Docker/LLM/readiness)
  - Acceptance checklist references cli.scan_complete structlog event and oxpwn.managed container labels for post-scan verification
duration: 10m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Juice Shop integration test and acceptance checklist

**Added session-scoped Juice Shop Docker fixture, structural integration test for full 5-phase pipeline, and manual acceptance checklist.**

## What Happened

1. **`juice_shop` fixture** added to `tests/conftest.py` — session-scoped, pulls `bkimminich/juice-shop:latest`, starts on port 3000 (configurable via `OXPWN_JUICESHOP_PORT`), waits up to 60s for HTTP 200, tears down on completion. Skips cleanly if Docker is unreachable or port is in use.

2. **`test_full_scan_pipeline`** created in `tests/integration/test_e2e_juiceshop.py` — async test that creates a `ScanRuntimeConfig` targeting the Juice Shop fixture URL, calls `_scan_async()` directly, and asserts:
   - `phases_completed` ≥ 3 entries
   - `tool_results` non-empty
   - `findings` is a list (may be empty)
   - Scan completes without exception
   - `total_tokens > 0`
   Marked with `@pytest.mark.integration`, `@pytest.mark.timeout(600)`, and `@pytest.mark.asyncio`. Skips if Docker or LLM key unavailable.

3. **`ACCEPTANCE-CHECKLIST.md`** created with 7 manual verification categories: phase transitions, agent reasoning, streaming output, scan summary, container cleanup, enrichment fields, and clean teardown.

## Verification

- `pytest tests/unit/ -x -q` — ✅ 261 tests passed, no regressions
- `pytest tests/unit/test_react_agent.py tests/unit/test_cli_main.py -v -k "phase_order or enrichment or extra_hosts or exploitation or validation or reporting"` — ✅ 7 wiring tests pass
- `pytest tests/integration/test_e2e_juiceshop.py -m integration -v --timeout=600` — ✅ 1 test skipped cleanly (no LLM key in CI env)
- `pytest tests/integration/test_e2e_juiceshop.py --collect-only` — ✅ 1 test collected (syntax valid, imports resolve)
- `test -f .gsd/milestones/M001/slices/S08/ACCEPTANCE-CHECKLIST.md` — ✅ exists

## Diagnostics

- Integration test skip reasons surface in pytest `-v` output with descriptive messages
- Juice Shop fixture labels containers with `oxpwn.managed=true` and `oxpwn.fixture=juice-shop` for post-test inspection
- Acceptance checklist includes `docker ps --filter` commands for container leak detection

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `tests/conftest.py` — added `juice_shop` session fixture with Docker lifecycle and readiness check
- `tests/integration/test_e2e_juiceshop.py` — full pipeline integration test with structural assertions
- `.gsd/milestones/M001/slices/S08/ACCEPTANCE-CHECKLIST.md` — manual acceptance checklist (7 verification categories)
