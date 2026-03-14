# S03: ReAct Agent Loop — UAT

**Milestone:** M001
**Written:** 2026-03-13

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: The agent loop is an internal subsystem consumed by S04/S05, not a user-facing feature. Correctness is proven by unit tests (mocked mechanics) and integration test (real LLM + Docker). No human UX to evaluate until S05 adds streaming CLI.

## Preconditions

- `pip install -e .` completed successfully
- For integration test: Docker daemon running, GEMINI_API_KEY (or other LLM key) set
- For unit tests: no external dependencies required

## Smoke Test

```bash
python3 -c "from oxpwn.agent import ReactAgent, ToolRegistry; print('agent subsystem importable')"
pytest tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v
```
Both should succeed — imports clean, 24/24 tests pass.

## Test Cases

### 1. Tool registry mechanics

1. Run `pytest tests/unit/test_tool_registry.py -v`
2. **Expected:** 12/12 pass — register, schema generation (OpenAI format), dispatch, unknown tool error, nmap default registration, parse_tool_arguments edge cases

### 2. Agent loop mechanics

1. Run `pytest tests/unit/test_react_agent.py -v`
2. **Expected:** 12/12 pass — tool call dispatch with result feedback, tool_call_id matching, phase transitions on non-tool-call response, max iterations error, multiple tool calls, malformed arguments handling, event ordering, broken callback resilience, LLM usage accumulation, parsed_output fed to LLM

### 3. Integration proof (requires Docker + LLM)

1. Ensure Docker is running and GEMINI_API_KEY is set
2. Run `pytest tests/integration/test_agent_integration.py -m integration -v`
3. **Expected:** Agent autonomously calls nmap via Docker, accumulates tool_results, completes recon phase, consumes tokens. Passes in ~18s.

### 4. No regression on S01/S02

1. Run `pytest tests/unit/ -v`
2. **Expected:** All 87 tests pass (43 S01 + 20 S02 + 24 S03)

## Edge Cases

### Max iterations safety valve

1. Covered by `test_raises_on_budget_exhaustion` in unit tests
2. **Expected:** AgentMaxIterationsError raised with correct phase and iteration count when LLM keeps calling tools past the limit

### Malformed tool arguments from LLM

1. Covered by `test_bad_arguments_skipped` in unit tests
2. **Expected:** Agent logs warning and continues loop instead of crashing — graceful degradation

### Broken event callback

1. Covered by `test_broken_callback_does_not_crash_agent` in unit tests
2. **Expected:** Exception in callback is swallowed with structlog warning, agent loop continues unaffected

## Failure Signals

- Any unit test failure in test_tool_registry.py or test_react_agent.py
- Import errors from `oxpwn.agent`
- Integration test fails to call nmap or accumulate state (when Docker + LLM available)
- Regression in S01/S02 unit tests

## Requirements Proved By This UAT

- R001 (Autonomous 5-phase pipeline) — Partially proved. Agent loop architecture works for 2 phases with autonomous tool selection, execution, state accumulation, and phase transition. Full validation requires S04 (all tools) + S08 (end-to-end).

## Not Proven By This UAT

- Agent behavior with 5 tools registered (S04)
- Real-time streaming CLI output (S05)
- Agent stuck detection and recovery (M002/S06)
- Full 5-phase pipeline execution (S08)
- Quality of agent reasoning across diverse targets (ongoing)

## Notes for Tester

- Integration test skips cleanly if Docker or LLM credentials are unavailable — this is by design, not a failure
- The unit tests use mocked LLM responses, so they prove loop mechanics but not reasoning quality
- Agent reasoning quality was validated during T02 development — Gemini 2.5 Flash selected nmap autonomously on first attempt
