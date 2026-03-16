---
id: T01
parent: S08
milestone: M001
provides:
  - 5-phase agent pipeline (recon → scanning → exploitation → validation → reporting)
  - Phase-specific LLM guidance for all 5 phases
  - Enrichment wiring in _scan_async() after agent.run()
  - Docker extra_hosts for host-network service reachability
key_files:
  - src/oxpwn/agent/react.py
  - src/oxpwn/agent/prompts.py
  - src/oxpwn/cli/main.py
  - src/oxpwn/sandbox/docker.py
  - tests/unit/test_react_agent.py
  - tests/unit/test_cli_main.py
  - tests/unit/test_docker_sandbox.py
key_decisions:
  - Enrichment uses in-memory CveCache (":memory:") in CLI path — no persistent cache file for now
  - extra_hosts defaults to {"host.docker.internal": "host-gateway"} when None, not when empty dict
patterns_established:
  - Enrichment try/except in _scan_async() logs cli.enrichment_failed but never crashes
  - All existing tests updated for 5-phase responses (not 2-phase)
observability_surfaces:
  - cli.scan_complete structlog event includes enriched_findings count
  - cli.enrichment_failed warning with exc_info on enrichment failure
  - enrichment.resolving_cves fires during real scans with CVE-bearing findings
duration: 20m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Wire 5-phase pipeline, enrichment, and Docker networking

**Expanded agent to all 5 phases, wired enrichment into CLI scan path, and added Docker extra_hosts for host-network reachability.**

## What Happened

1. **`_PHASE_ORDER` expanded** from `[recon, scanning]` to all 5 phases in `react.py`. Comment updated to reflect S08 scope.

2. **3 new `_PHASE_GUIDANCE` entries** added to `prompts.py`:
   - Exploitation: review scanning findings, attempt targeted validation with available tools, synthesize evidence, move on if no dedicated tools available.
   - Validation: re-probe top findings with targeted checks to confirm they're real (not false positives), downgrade unconfirmed findings.
   - Reporting: compile structured summary with severity, CVE, evidence, CVSS, and remediation context. No tool calls — pure text output.

3. **`extra_hosts` parameter** added to `DockerSandbox.__init__()` with default `{"host.docker.internal": "host-gateway"}`. Passed through to `client.containers.create()` in the `create()` method.

4. **Enrichment wired into `_scan_async()`** after `agent.run()` returns and before `render_final_summary()`:
   - Calls `findings_from_tool_results(final_state.tool_results)` to extract findings
   - Creates `NvdClient()` and `CveCache(db_path=":memory:")`, calls `enrich_findings()`
   - Closes both clients in a `finally` block
   - Assigns enriched findings to `final_state.findings`
   - Entire block wrapped in `try/except` — failures log `cli.enrichment_failed` but never crash
   - `cli.scan_complete` event now includes `enriched_findings` count

5. **All existing tests updated** for 5-phase pipeline (LLM mock side_effects expanded from 2 to 5 phase-complete responses). New tests added for phase order, guidance coverage, enrichment wiring, and enrichment failure resilience.

## Verification

- `python3 -c "from oxpwn.agent.react import _PHASE_ORDER; ..."` — ✅ asserts 5 phases in correct order
- `python3 -c "from oxpwn.agent.prompts import _PHASE_GUIDANCE; ..."` — ✅ all phases have guidance
- `pytest tests/unit/ -x -q` — ✅ 261 tests passed, no regressions
- `pytest tests/unit/test_react_agent.py tests/unit/test_cli_main.py -v -k "phase_order or enrichment or ..."` — ✅ 7 new wiring tests pass
- Integration test (T02) — not yet created (next task)

## Diagnostics

- `cli.scan_complete` structlog event: check `enriched_findings` field for enrichment count
- `cli.enrichment_failed` structlog warning: fires on enrichment errors with `exc_info=True`
- `ScanState.findings`: populated after enrichment with Finding objects
- `ScanState.phases_completed`: should contain all 5 Phase enum values after a full scan

## Deviations

- Updated `tests/unit/test_docker_sandbox.py` assertion for `containers.create()` to include `extra_hosts` — not listed in the task plan but required to prevent regression.
- Token/cost assertions in `test_llm_usage_accumulated` updated from 2-call to 5-call expectations.

## Known Issues

None.

## Files Created/Modified

- `src/oxpwn/agent/react.py` — `_PHASE_ORDER` expanded to 5 phases
- `src/oxpwn/agent/prompts.py` — 3 new `_PHASE_GUIDANCE` entries for exploitation/validation/reporting
- `src/oxpwn/cli/main.py` — enrichment wiring in `_scan_async()`, enriched_findings in scan_complete event
- `src/oxpwn/sandbox/docker.py` — `extra_hosts` parameter with host-gateway default
- `tests/unit/test_react_agent.py` — all tests updated for 5 phases, new phase order + guidance tests
- `tests/unit/test_cli_main.py` — FakeAgent updated for 5 phases, 2 new enrichment wiring tests
- `tests/unit/test_docker_sandbox.py` — assertion updated for extra_hosts
