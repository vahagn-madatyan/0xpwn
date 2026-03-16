---
estimated_steps: 5
estimated_files: 6
---

# T01: Wire 5-phase pipeline, enrichment, and Docker networking

**Slice:** S08 — End-to-End Validation
**Milestone:** M001

## Description

Close the 4 code-level integration gaps that prevent the pipeline from running end-to-end: expand the agent's phase list from 2 to 5, add phase-specific LLM guidance for exploitation/validation/reporting, wire the S07 enrichment module into the CLI's `_scan_async()` composition point, and add `extra_hosts` to the Docker sandbox so containers can reach host-network services like Juice Shop.

## Steps

1. In `src/oxpwn/agent/react.py`, change `_PHASE_ORDER` from `[Phase.recon, Phase.scanning]` to `[Phase.recon, Phase.scanning, Phase.exploitation, Phase.validation, Phase.reporting]`. Update the comment to reflect S08 scope.

2. In `src/oxpwn/agent/prompts.py`, add 3 entries to `_PHASE_GUIDANCE` for `Phase.exploitation`, `Phase.validation`, and `Phase.reporting`. Exploitation: review scanning findings, attempt targeted validation with available tools (nuclei with specific templates, nmap scripts), synthesize exploitation evidence, move on if no dedicated exploitation tools available. Validation: re-probe top findings with targeted checks to confirm they're real, not false positives. Reporting: compile a structured summary of all confirmed findings with severity, evidence, and remediation context.

3. In `src/oxpwn/sandbox/docker.py`, add an `extra_hosts` parameter to `DockerSandbox.__init__()` defaulting to `{"host.docker.internal": "host-gateway"}`. Pass it through to `client.containers.create()` in the `create()` method.

4. In `src/oxpwn/cli/main.py`, after `final_state = await agent.run(scan_state)` in `_scan_async()`, add enrichment wiring: import and call `findings_from_tool_results(final_state.tool_results)`, then `await enrich_findings(findings, NvdClient(), CveCache())`, assign to `final_state.findings`, and close the NVD client/cache. Wrap the entire enrichment block in try/except so failures log a warning but never crash the scan. Log enriched finding count in the `cli.scan_complete` event.

5. Add unit tests in `tests/unit/test_react_agent.py` verifying `_PHASE_ORDER` contains all 5 phases. Add tests in `tests/unit/test_cli_main.py` verifying enrichment is invoked via the mock factory pattern. Verify prompts.py has guidance for all 5 phases.

## Must-Haves

- [ ] `_PHASE_ORDER` contains exactly `[recon, scanning, exploitation, validation, reporting]`
- [ ] `_PHASE_GUIDANCE` has entries for all 5 phases (no phase falls through to `_DEFAULT_GUIDANCE`)
- [ ] `_scan_async()` calls `findings_from_tool_results()` and `enrich_findings()` after agent.run()
- [ ] Enrichment failures are caught and logged, never crash the scan
- [ ] `DockerSandbox.create()` passes `extra_hosts` to `containers.create()`
- [ ] All existing unit tests still pass (no regressions)

## Verification

- `python3 -c "from oxpwn.agent.react import _PHASE_ORDER; from oxpwn.core.models import Phase; assert [Phase.recon, Phase.scanning, Phase.exploitation, Phase.validation, Phase.reporting] == _PHASE_ORDER"`
- `python3 -c "from oxpwn.agent.prompts import _PHASE_GUIDANCE; from oxpwn.core.models import Phase; assert all(p in _PHASE_GUIDANCE for p in Phase)"`
- `pytest tests/unit/ -x -q` — 260+ tests pass, no regressions

## Observability Impact

- Signals added/changed: `cli.scan_complete` event now includes `enriched_findings` count; enrichment structlog events (`enrichment.resolving_cves`, `enrichment.finding_enriched`) fire during real scans
- How a future agent inspects this: `ScanState.findings` is populated after enrichment; `ScanState.phases_completed` contains all 5 phases after a full scan
- Failure state exposed: enrichment try/except logs `cli.enrichment_failed` warning with exc_info on failure

## Inputs

- `src/oxpwn/agent/react.py` — `_PHASE_ORDER` on line 30 is the sole phase gate
- `src/oxpwn/agent/prompts.py` — `_PHASE_GUIDANCE` dict on lines 84-102 needs 3 new entries
- `src/oxpwn/cli/main.py` — `_scan_async()` lines 249-327 is the composition point
- `src/oxpwn/sandbox/docker.py` — `create()` lines 77-110 passes `network_mode` but needs `extra_hosts`
- `src/oxpwn/enrichment/` — `findings_from_tool_results()` and `enrich_findings()` ready to wire in
- S07 Summary — NvdClient and CveCache init patterns, async `enrich_findings()` signature

## Expected Output

- `src/oxpwn/agent/react.py` — `_PHASE_ORDER` expanded to 5 phases
- `src/oxpwn/agent/prompts.py` — 3 new `_PHASE_GUIDANCE` entries
- `src/oxpwn/cli/main.py` — enrichment block in `_scan_async()` after agent.run()
- `src/oxpwn/sandbox/docker.py` — `extra_hosts` parameter with `host-gateway` default
- `tests/unit/test_react_agent.py` — phase order coverage tests
- `tests/unit/test_cli_main.py` — enrichment wiring tests
