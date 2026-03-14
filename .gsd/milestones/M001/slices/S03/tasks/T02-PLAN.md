---
estimated_steps: 4
estimated_files: 2
---

# T02: Integration test proving autonomous Recon→Scanning with real LLM and Docker

**Slice:** S03 — ReAct Agent Loop
**Milestone:** M001

## Description

Write and run the integration test that proves the agent autonomously reasons through at least the Recon phase — selecting nmap, executing it in Docker, and accumulating state. This is the primary risk retirement proof for "agent loop quality" from the roadmap. Unit tests (T01) prove mechanics; this proves the agent actually works when composed with real LLM and real Docker.

## Steps

1. Add fixtures to `tests/conftest.py`: `llm_client` fixture creating `LLMClient` with the test model (env var `OXPWN_TEST_MODEL` or default `gemini/gemini-2.5-flash`), skip if no API key. `react_agent` fixture composing `LLMClient` + `docker_sandbox` + `ToolRegistry` (nmap registered) into a `ReactAgent`.

2. Write `tests/integration/test_agent_integration.py`: test that creates a `ScanState` targeting a scannable address (the Docker gateway or localhost), runs the agent for the Recon phase, and asserts structural properties: (a) at least one tool_result in scan_state with tool_name="nmap", (b) the tool_result has parsed_output (not None), (c) scan_state.phases_completed contains Phase.recon or current_phase has advanced past recon, (d) scan_state.total_tokens > 0 (LLM was actually called). Use `pytest.mark.integration` and `pytest.mark.timeout(120)`.

3. If integration test fails on first run — debug by inspecting the actual LLM messages, tool call arguments, and agent behavior. Common issues: LLM not calling nmap (system prompt too vague), wrong nmap arguments (schema mismatch), Docker networking preventing scan. Adjust prompts, schema descriptions, or test target until it passes.

4. Run the full test suite (`unit + integration`) to confirm nothing regressed.

## Must-Haves

- [ ] Integration test proves agent calls nmap via sandbox with real LLM reasoning
- [ ] ScanState accumulates tool_results from real nmap execution
- [ ] Test asserts structural properties, not exact LLM output content
- [ ] Test skips cleanly when Docker or LLM credentials are unavailable
- [ ] Full test suite (unit + integration) passes

## Verification

- `pytest tests/integration/test_agent_integration.py -m integration -v` — passes
- `pytest tests/unit/ -v` — still passes (no regression)

## Inputs

- `src/oxpwn/agent/react.py` — ReactAgent from T01
- `src/oxpwn/agent/tools.py` — ToolRegistry with nmap from T01
- `tests/conftest.py` — docker_sandbox fixture from S02
- S01 forward intelligence: LLMClient accepts any LiteLLM model string, `GEMINI_API_KEY` or `OXPWN_TEST_MODEL` for provider selection

## Expected Output

- `tests/conftest.py` — updated with llm_client and react_agent fixtures
- `tests/integration/test_agent_integration.py` — integration test proving agent loop quality with real runtime
