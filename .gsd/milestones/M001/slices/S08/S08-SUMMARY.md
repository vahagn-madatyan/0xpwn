---
id: S08
parent: M001
milestone: M001
provides:
  - 5-phase agent pipeline (recon → scanning → exploitation → validation → reporting) fully wired
  - Phase-specific LLM guidance prompts for all 5 phases
  - Enrichment pipeline wired into _scan_async() after agent.run()
  - Docker extra_hosts for host-network service reachability
  - End-to-end Juice Shop integration test with structural assertions
  - Manual acceptance checklist for human UAT
requires:
  - slice: S01
    provides: Pydantic models, async LLM client
  - slice: S02
    provides: DockerSandbox container lifecycle
  - slice: S03
    provides: ReactAgent loop with phase iteration and event emission
  - slice: S04
    provides: 5 tool executors with structured parsers
  - slice: S05
    provides: RichStreamingCallback, CLI scan command
  - slice: S06
    provides: Config manager, wizard, _build_scan_config()
  - slice: S07
    provides: findings_from_tool_results(), enrich_findings(), NvdClient, CveCache
affects: []
key_files:
  - src/oxpwn/agent/react.py
  - src/oxpwn/agent/prompts.py
  - src/oxpwn/cli/main.py
  - src/oxpwn/sandbox/docker.py
  - tests/unit/test_react_agent.py
  - tests/unit/test_cli_main.py
  - tests/unit/test_docker_sandbox.py
  - tests/conftest.py
  - tests/integration/test_e2e_juiceshop.py
  - .gsd/milestones/M001/slices/S08/ACCEPTANCE-CHECKLIST.md
key_decisions:
  - Enrichment runs post-loop in _scan_async(), not inside agent reasoning (Decision #36)
  - Docker extra_hosts defaults to host-gateway for cross-container reachability (Decision #37)
  - Integration test calls _scan_async() directly, not CliRunner (Decision #38)
  - In-memory CveCache in CLI enrichment path — no persistent cache file for now
patterns_established:
  - Enrichment try/except in _scan_async() logs cli.enrichment_failed but never crashes the scan
  - All unit tests use 5-phase LLM mock responses (not 2-phase)
  - Session-scoped Docker fixtures with port availability checks and readiness polling
  - Structural assertions — assert pipeline properties without depending on LLM output content
observability_surfaces:
  - cli.scan_complete structlog event includes enriched_findings count
  - cli.enrichment_failed warning with exc_info on enrichment failure
  - ScanState.findings populated after enrichment
  - ScanState.phases_completed contains all 5 Phase enum values after full scan
drill_down_paths:
  - .gsd/milestones/M001/slices/S08/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001/slices/S08/tasks/T02-SUMMARY.md
duration: 30m
verification_result: passed
completed_at: 2026-03-15
---

# S08: End-to-End Validation

**Full 5-phase pipeline wired end-to-end with enrichment, Docker networking, Juice Shop integration test, and manual acceptance checklist — completing M001.**

## What Happened

S08 closed the four remaining gaps blocking end-to-end validation: the agent only ran 2 of 5 phases, enrichment was unwired from the CLI, the sandbox couldn't reach host-network services, and no integration test proved the full pipeline.

**T01** expanded `_PHASE_ORDER` from `[recon, scanning]` to all 5 phases and added phase-specific LLM guidance for exploitation (synthesize scanning results, attempt targeted validation), validation (re-probe top findings to confirm they're real), and reporting (compile structured summary — no tool calls). Enrichment was wired into `_scan_async()` after `agent.run()` returns: `findings_from_tool_results()` extracts findings from tool results, `enrich_findings()` populates CVE/CVSS/CWE data via NVD, and the whole block is wrapped in try/except so failures never crash the scan. `DockerSandbox` gained an `extra_hosts` parameter defaulting to `{"host.docker.internal": "host-gateway"}` so sandbox containers can reach host-network services like Juice Shop. All existing tests were updated for 5-phase expectations.

**T02** added a session-scoped `juice_shop` fixture that pulls and starts `bkimminich/juice-shop:latest`, waits for HTTP readiness, and tears down after tests. The `test_full_scan_pipeline` integration test creates a `ScanRuntimeConfig` targeting the Juice Shop, calls `_scan_async()` directly, and asserts structural properties: ≥3 phases completed, non-empty tool results, findings list exists, total tokens consumed. It skips cleanly when Docker, LLM, or Juice Shop are unavailable. A 7-category acceptance checklist documents what a human must verify beyond automated tests.

## Verification

- `pytest tests/unit/ -x -q` — **261 passed**, no regressions
- `pytest tests/unit/test_react_agent.py tests/unit/test_cli_main.py -v -k "phase_order or enrichment or extra_hosts or exploitation or validation or reporting"` — **7 wiring tests passed**
- `pytest tests/integration/test_e2e_juiceshop.py -m integration -v --timeout=600` — **1 test skipped cleanly** (no LLM key in env)
- `python3 -c "from oxpwn.agent.react import _PHASE_ORDER; assert len(_PHASE_ORDER) == 5"` — ✅
- `python3 -c "from oxpwn.agent.prompts import _PHASE_GUIDANCE; ..."` — ✅ all 5 phases have guidance
- `ACCEPTANCE-CHECKLIST.md` exists — ✅
- Observability: `cli.scan_complete` includes `enriched_findings` count, `cli.enrichment_failed` logs on failure — confirmed in source

## Requirements Advanced

- R001 (Autonomous 5-phase pentesting pipeline) — all 5 phases wired with guidance, enrichment post-processing, structural tests proving pipeline shape
- R004 (Real-time agent reasoning stream) — 5-phase streaming now exercises full pipeline; S05's streaming infrastructure extended to cover all phases
- R002 (Isolated Docker/Kali sandbox) — extra_hosts added for host-network reachability in integration testing

## Requirements Validated

- R001 — Validated by 261 unit tests proving 5-phase order, all-phase guidance, enrichment wiring, and pipeline structure; integration test with structural assertions exists for live proof. Human UAT documented in acceptance checklist.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- `tests/unit/test_docker_sandbox.py` updated for `extra_hosts` assertion — not in task plan but required to prevent regression
- Token/cost assertions in `test_llm_usage_accumulated` updated from 2-call to 5-call expectations

## Known Limitations

- Integration test skips when LLM key is unavailable — full live proof requires manual execution with a configured LLM provider
- Enrichment uses in-memory CveCache — no persistent cache across scans (acceptable for M001; persistence comes with M002/SQLite)
- Live NVD API calls during enrichment are rate-limited; first scan with many CVEs may be slow

## Follow-ups

- None — this is the final M001 slice. M002 picks up safety, persistence, and operational concerns.

## Files Created/Modified

- `src/oxpwn/agent/react.py` — `_PHASE_ORDER` expanded to 5 phases
- `src/oxpwn/agent/prompts.py` — 3 new `_PHASE_GUIDANCE` entries
- `src/oxpwn/cli/main.py` — enrichment wiring in `_scan_async()`
- `src/oxpwn/sandbox/docker.py` — `extra_hosts` parameter with host-gateway default
- `tests/unit/test_react_agent.py` — 5-phase updates, new phase order + guidance tests
- `tests/unit/test_cli_main.py` — 5-phase FakeAgent, enrichment wiring tests
- `tests/unit/test_docker_sandbox.py` — extra_hosts assertion
- `tests/conftest.py` — `juice_shop` session fixture
- `tests/integration/test_e2e_juiceshop.py` — full pipeline integration test
- `.gsd/milestones/M001/slices/S08/ACCEPTANCE-CHECKLIST.md` — 7-category manual verification checklist

## Forward Intelligence

### What the next slice should know
- M001 is complete at the contract/structural level. All 8 slices wired together, 261 unit tests pass, integration test structure exists. Live proof against Juice Shop requires a configured LLM provider and Docker daemon.
- The enrichment path in `_scan_async()` is intentionally resilient — failures are logged but never crash. This means a scan can "succeed" with zero enriched findings if NVD is down.

### What's fragile
- The 5-phase agent loop depends heavily on LLM quality — the phase guidance prompts steer but can't force correct tool selection. Exploitation and validation phases may produce thin results with weaker models.
- `extra_hosts` host-gateway works on Docker Desktop and modern Linux but may not resolve on older Docker Engine versions.

### Authoritative diagnostics
- `cli.scan_complete` structlog event — check `enriched_findings` field to confirm enrichment ran and found CVEs
- `ScanState.phases_completed` — should contain all 5 Phase enum values after a successful full scan
- `pytest tests/unit/ -x -q` — 261 tests is the current baseline; any regression here is a real signal

### What assumptions changed
- Original plan assumed enrichment might need to run inside the agent loop — it runs cleanly as post-processing, avoiding NVD rate-limit delays during reasoning.
