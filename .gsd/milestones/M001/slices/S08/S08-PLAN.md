# S08: End-to-End Validation

**Goal:** Full `0xpwn scan --target <url>` pipeline runs all 5 phases, produces enriched findings, and streams reasoning in real-time — proving the complete M001 outcome.
**Demo:** Integration test against OWASP Juice Shop completes all 5 phases with tool results, extracted findings, enrichment attempted, and streaming output rendered.

## Must-Haves

- Agent loop executes all 5 phases (recon → scanning → exploitation → validation → reporting), not just 2
- Phase guidance prompts exist for exploitation, validation, and reporting (not just the generic fallback)
- Enrichment pipeline (`findings_from_tool_results()` → `enrich_findings()`) is called after the agent loop in `_scan_async()`
- Docker sandbox supports `extra_hosts` for `host.docker.internal` resolution so tools can reach host-network services
- Integration test against Juice Shop proves the full pipeline end-to-end with structural assertions
- Manual acceptance checklist documents what a human must verify beyond automated tests

## Proof Level

- This slice proves: final-assembly
- Real runtime required: yes (Docker + LLM + Juice Shop)
- Human/UAT required: yes (streaming quality, finding accuracy, UX — documented in acceptance checklist)

## Verification

- `pytest tests/unit/ -x -q` — all existing + new unit tests pass (260+ total, no regressions)
- `pytest tests/unit/test_react_agent.py tests/unit/test_cli_main.py -v -k "phase_order or enrichment or extra_hosts or exploitation or validation or reporting"` — new wiring unit tests pass
- `pytest tests/integration/test_e2e_juiceshop.py -m integration -v --timeout=600` — full pipeline integration test passes (or skips cleanly if Docker/LLM/Juice Shop unavailable)
- `.gsd/milestones/M001/slices/S08/ACCEPTANCE-CHECKLIST.md` exists with manual verification steps

## Observability / Diagnostics

- Runtime signals: `cli.scan_complete` structlog event now includes `enriched_findings` count; `enrichment.resolving_cves` fires after agent loop
- Inspection surfaces: `ScanState.findings` populated after enrichment; `ScanState.phases_completed` contains all 5 phases
- Failure visibility: enrichment errors logged via `enrichment.*` structlog events but never crash the pipeline; phase completion tracked in scan summary
- Redaction constraints: API keys in config remain redacted in streaming output (unchanged from S05/S06)

## Integration Closure

- Upstream surfaces consumed: `ReactAgent.run()` (S03), `DockerSandbox.create()` (S02), `findings_from_tool_results()` + `enrich_findings()` (S07), `RichStreamingCallback` (S05), `_build_scan_config()` (S06), all 5 tool executors (S04)
- New wiring introduced in this slice: enrichment call in `_scan_async()`, `extra_hosts` in `DockerSandbox.create()`, 3 new phase guidance prompts, expanded `_PHASE_ORDER`
- What remains before the milestone is truly usable end-to-end: nothing — this is the final slice

## Tasks

- [x] **T01: Wire 5-phase pipeline, enrichment, and Docker networking** `est:45m`
  - Why: The agent loop only runs 2 of 5 phases, enrichment is completely unwired from the CLI, and the sandbox can't reach host-network services. These are the 4 code-level gaps blocking end-to-end validation.
  - Files: `src/oxpwn/agent/react.py`, `src/oxpwn/agent/prompts.py`, `src/oxpwn/cli/main.py`, `src/oxpwn/sandbox/docker.py`, `tests/unit/test_react_agent.py`, `tests/unit/test_cli_main.py`
  - Do: (1) Expand `_PHASE_ORDER` to all 5 phases. (2) Add exploitation/validation/reporting guidance to `_PHASE_GUIDANCE`. Exploitation: summarize findings and attempt targeted validation with available tools; if no exploitation-specific tools, synthesize results and move on. Validation: re-check top findings with targeted probes to confirm they're real. Reporting: compile a structured summary of all confirmed findings. (3) In `_scan_async()`, after `agent.run()` returns and before `render_final_summary()`, call `findings_from_tool_results()` on `final_state.tool_results`, then `enrich_findings()` with `NvdClient` + `CveCache`, and assign results to `final_state.findings`. Wrap in try/except so enrichment failures don't crash the scan. (4) Add `extra_hosts` parameter to `DockerSandbox.__init__()` and pass it through to `containers.create()`. Default to `{"host.docker.internal": "host-gateway"}`. (5) Add unit tests: phase order contains all 5, phase guidance covers all 5, enrichment is called in `_scan_async`, extra_hosts passed through.
  - Verify: `pytest tests/unit/ -x -q` passes with no regressions; `python3 -c "from oxpwn.agent.react import _PHASE_ORDER; assert len(_PHASE_ORDER) == 5"`
  - Done when: `_PHASE_ORDER` has 5 phases, all 5 have guidance, enrichment is called in `_scan_async()`, `extra_hosts` defaults to `host-gateway`, and all unit tests pass

- [x] **T02: Juice Shop integration test and acceptance checklist** `est:45m`
  - Why: The wiring from T01 must be proven against a real target with real tools, real LLM reasoning, and real enrichment. This is the M001 definition-of-done proof.
  - Files: `tests/conftest.py`, `tests/integration/test_e2e_juiceshop.py`, `.gsd/milestones/M001/slices/S08/ACCEPTANCE-CHECKLIST.md`
  - Do: (1) Add a session-scoped `juice_shop` fixture in conftest.py that pulls/starts `bkimminich/juice-shop:latest` on port 3000 (or `OXPWN_JUICESHOP_PORT`), waits for ready, and tears down after tests. Skip if Docker unavailable or port in use. (2) Write `test_e2e_juiceshop.py` with a single `test_full_scan_pipeline` test: create `ScanRuntimeConfig` targeting `host.docker.internal:3000`, run `_scan_async()` directly (not via CliRunner — avoids timeout issues), assert structural properties: `phases_completed` has ≥3 entries, `tool_results` is non-empty, `findings` list exists (may be empty if LLM doesn't find CVE-bearing vulns), scan completes without exception. Use 600s timeout. (3) Write `ACCEPTANCE-CHECKLIST.md` documenting manual verification steps for streaming quality, finding accuracy, phase transitions, enrichment output, and clean container teardown.
  - Verify: `pytest tests/integration/test_e2e_juiceshop.py -m integration -v --timeout=600` passes or skips cleanly
  - Done when: integration test file exists with structural assertions, acceptance checklist exists, and `pytest tests/unit/ -x -q` still passes

## Files Likely Touched

- `src/oxpwn/agent/react.py`
- `src/oxpwn/agent/prompts.py`
- `src/oxpwn/cli/main.py`
- `src/oxpwn/sandbox/docker.py`
- `tests/unit/test_react_agent.py`
- `tests/unit/test_cli_main.py`
- `tests/conftest.py`
- `tests/integration/test_e2e_juiceshop.py`
- `.gsd/milestones/M001/slices/S08/ACCEPTANCE-CHECKLIST.md`
