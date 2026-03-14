---
id: T02
parent: S03
milestone: M001
provides:
  - Integration test proving agent autonomously reasons through Recon+Scanning with real LLM and Docker
  - llm_client and react_agent session fixtures in conftest.py
key_files:
  - tests/integration/test_agent_integration.py
  - tests/conftest.py
key_decisions:
  - none
patterns_established:
  - _EventCollector pattern for capturing agent events in integration tests
  - Session-scoped llm_client fixture with OXPWN_TEST_MODEL override and multi-provider API key skip logic
  - Session-scoped react_agent fixture composing LLMClient + docker_sandbox + ToolRegistry
observability_surfaces:
  - EventCollector in tests captures ToolCallEvent/ToolResultEvent for assertion
  - ScanState.tool_results, .phases_completed, .total_tokens inspectable after run
duration: 15m
verification_result: passed
completed_at: 2026-03-13
blocker_discovered: false
---

# T02: Integration test proving autonomous Recon→Scanning with real LLM and Docker

**Proved agent autonomously selects and runs nmap in Docker via real Gemini LLM reasoning, accumulating structured state across both Recon and Scanning phases.**

## What Happened

Added `llm_client` and `react_agent` session fixtures to `tests/conftest.py` — the LLM fixture reads `OXPWN_TEST_MODEL` (default `gemini/gemini-2.5-flash`) and skips if no API key is set. The `react_agent` fixture composes LLMClient + docker_sandbox + ToolRegistry (nmap registered).

Wrote `tests/integration/test_agent_integration.py` with a single test that creates a ScanState targeting localhost, runs the full agent loop, and asserts four structural properties: (a) at least one nmap tool_result, (b) parsed_output present, (c) recon phase completed, (d) total_tokens > 0. Also verifies ToolCallEvent and ToolResultEvent were emitted. All assertions are structural — no exact LLM output matching.

Test passed on first run in 17.76s with real Gemini 2.5 Flash + real Docker nmap execution.

## Verification

- `pytest tests/integration/test_agent_integration.py -m integration -v` — **PASSED** (17.76s, agent called nmap, accumulated state, advanced phases)
- `pytest tests/unit/ -v` — **87 passed** (no regression)
- `pytest tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v` — **24 passed** (slice verification)

## Diagnostics

- Inspect `ScanState.tool_results` after a run — should contain nmap entries with `parsed_output`
- `ScanState.phases_completed` shows which phases the agent completed
- `ScanState.total_tokens` confirms LLM was actually called
- EventCollector in tests captures full event stream for debugging agent behavior

## Deviations

None. The test used a fresh agent per test (not the session fixture) with an EventCollector, which is cleaner — the session fixture remains available for future tests.

## Known Issues

None.

## Files Created/Modified

- `tests/conftest.py` — Added `llm_client` and `react_agent` session fixtures with skip logic
- `tests/integration/test_agent_integration.py` — Integration test proving agent loop quality with real LLM + Docker
