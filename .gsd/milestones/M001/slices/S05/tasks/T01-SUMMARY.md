---
id: T01
parent: S05
milestone: M001
provides:
  - Typed additive streaming events, agent output-sink wiring, and Docker sandbox live-output buffering without breaking the existing ToolResult contract.
key_files:
  - src/oxpwn/agent/events.py
  - src/oxpwn/agent/react.py
  - src/oxpwn/agent/tools.py
  - src/oxpwn/sandbox/docker.py
  - tests/unit/test_react_agent.py
  - tests/unit/test_tool_registry.py
  - tests/unit/test_docker_sandbox.py
key_decisions:
  - Keep streaming additive by always passing an agent-level output sink, but only inject it into executors that explicitly opt into `output_sink` (or accept `**kwargs`).
  - Use Docker's low-level streaming exec path for live stdout/stderr forwarding while buffering the same final stdout/stderr into one ToolResult.
patterns_established:
  - Agent event order for a tool turn is reasoning → tool call → zero or more ToolOutputChunkEvent chunks → tool result.
  - Sandbox streaming stays source-aware (`stdout` vs `stderr`) and preserves the non-streaming buffered result shape for existing callers.
observability_surfaces:
  - ToolOutputChunkEvent callback captures, `sandbox.execute_stream` structured logs, and unit assertions over captured event lists / buffered ToolResult payloads.
duration: 1h 44m
verification_result: passed
completed_at: 2026-03-14T21:20:00-07:00
blocker_discovered: false
---

# T01: Add additive streaming events and sandbox execution hooks

**Added typed live-output events, threaded an additive output sink through the agent/tool boundary, and implemented Docker exec streaming that still returns the existing buffered ToolResult contract.**

## What Happened

I extended the typed agent event contract with `ToolOutputChunkEvent` so streamed raw chunks remain callback-safe and distinguish `stdout` from `stderr`. I also exported the new event from `src/oxpwn/agent/__init__.py`.

In `src/oxpwn/agent/react.py`, the agent now emits `ReasoningEvent` whenever the model returns assistant text, including tool-call turns. For tool turns, it now builds an additive per-tool output sink that emits `ToolOutputChunkEvent` with phase, iteration, and tool context. That sink is passed through `ToolRegistry.dispatch(...)` before tool execution so streamed chunks appear between `ToolCallEvent` and `ToolResultEvent`.

In `src/oxpwn/agent/tools.py`, I added optional `output_sink` support to `ToolRegistry.dispatch(...)` while keeping legacy executors working unchanged. The registry only injects `output_sink` into executors whose `run()` signature explicitly accepts it or accepts `**kwargs`, which keeps all existing non-streaming callers and executors compatible.

In `src/oxpwn/sandbox/docker.py`, I added `DockerSandbox.execute_stream(...)` using Docker's low-level exec streaming API. It forwards decoded chunks live, preserves `stdout`/`stderr` source identity, buffers those same chunks into final strings, and returns the same `ToolResult` shape as `execute()`. Timeout and not-running behavior match the existing execution path.

I expanded the three T01 unit suites to assert the new behavior directly:
- `tests/unit/test_react_agent.py` now checks reasoning on tool-call turns, chunk emission, and deterministic event order.
- `tests/unit/test_tool_registry.py` now checks sink forwarding for opt-in executors and no-break behavior for legacy executors.
- `tests/unit/test_docker_sandbox.py` now checks chunk forwarding, buffered/streamed parity, and timeout/not-running behavior for `execute_stream(...)`.

Because this is the first task in S05 and the slice verification contract names additional future test files, I also created placeholder tests for:
- `tests/unit/test_tool_streaming.py`
- `tests/unit/test_cli_streaming.py`
- `tests/unit/test_cli_main.py`
- `tests/integration/test_cli_integration.py`

Those placeholders intentionally fail with explicit “pending T02/T03/T04” messages so later tasks have concrete artifacts to replace.

## Verification

Task-level verification passed:

- `pytest tests/unit/test_docker_sandbox.py tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v`
  - Result: **43 passed**
- `python3 -c "from oxpwn.agent.events import ToolOutputChunkEvent; print('imports ok')"`
  - Result: **imports ok**

Observability-impact verification was covered directly by the targeted unit tests:
- Captured event lists now include `ToolOutputChunkEvent` with `phase`, `iteration`, `tool_name`, and `stream` source.
- Docker streaming tests verify raw chunks are forwarded live and still buffered into the final `ToolResult`.
- Timeout and stopped-container regressions are explicit in `execute_stream(...)` assertions.

Slice-level verification status after T01:

- `pytest tests/unit/test_docker_sandbox.py tests/unit/test_tool_registry.py tests/unit/test_react_agent.py tests/unit/test_tool_streaming.py tests/unit/test_cli_streaming.py tests/unit/test_cli_main.py -v`
  - Result: **43 passed, 3 failed**
  - Failing files are the intentional placeholders for pending T02/T03 work.
- `pytest tests/integration/test_cli_integration.py -m integration -v`
  - Result: **1 failed**
  - Failing file is the intentional placeholder for pending T04 work.
- `pip install -e . && OXPWN_MODEL="${OXPWN_TEST_MODEL:-gemini/gemini-2.5-flash}" 0xpwn scan --target localhost`
  - Exact command failed first because this environment has no `pip` shim.
- `python3 -m pip install -e . && OXPWN_MODEL="${OXPWN_TEST_MODEL:-gemini/gemini-2.5-flash}" 0xpwn scan --target localhost`
  - Install succeeded, but the CLI still fails with `No such option: --target`, which is expected until T03 rewires the real scan command.

## Diagnostics

To inspect this work later:

- Run `pytest tests/unit/test_react_agent.py::TestEventCallbacks::test_events_emitted_in_order -v` to inspect the agent-side streamed event order.
- Run `pytest tests/unit/test_tool_registry.py::TestToolRegistry::test_dispatch_forwards_output_sink_to_opt_in_executor -v` to isolate the dispatch boundary.
- Run `pytest tests/unit/test_docker_sandbox.py::TestExecuteStream -v` to isolate sandbox streaming/buffering behavior.
- Watch `sandbox.execute_stream` structured logs for command, exit code, duration, and container context.
- Inspect `ToolOutputChunkEvent` payloads for missing chunk forwarding, wrong ordering, or stdout/stderr source mixups.

## Deviations

- Created the additional slice verification test files (`test_tool_streaming.py`, `test_cli_streaming.py`, `test_cli_main.py`, `test_cli_integration.py`) as explicit placeholders even though they are owned by later tasks. This was done to satisfy the first-task slice artifact requirement from auto-mode.

## Known Issues

- The five built-in tool executors do not stream live output yet; `ToolRegistry.dispatch(...)` and `DockerSandbox.execute_stream(...)` are ready, but T02 still needs to opt the executors in.
- The CLI streaming renderer and real `scan --target` path are not implemented yet; the placeholder CLI tests intentionally fail until T03/T04 replace them.
- The current installed CLI still rejects `--target`, which is expected pre-T03.

## Files Created/Modified

- `src/oxpwn/agent/events.py` — added `ToolOutputChunkEvent` and the typed stdout/stderr stream surface.
- `src/oxpwn/agent/__init__.py` — exported the new streaming event.
- `src/oxpwn/agent/react.py` — emits reasoning on all assistant-text turns and forwards streamed tool output as agent events.
- `src/oxpwn/agent/tools.py` — added additive optional `output_sink` dispatch with legacy-executor compatibility.
- `src/oxpwn/sandbox/docker.py` — implemented `execute_stream(...)` with live chunk forwarding plus buffered result parity.
- `tests/unit/test_react_agent.py` — added event-order and streamed-chunk assertions.
- `tests/unit/test_tool_registry.py` — added output-sink forwarding and backward-compatibility coverage.
- `tests/unit/test_docker_sandbox.py` — added streaming/buffering parity and live chunk tests.
- `tests/unit/test_tool_streaming.py` — created explicit T02 placeholder coverage file.
- `tests/unit/test_cli_streaming.py` — created explicit T03 placeholder coverage file.
- `tests/unit/test_cli_main.py` — created explicit T03 placeholder coverage file.
- `tests/integration/test_cli_integration.py` — created explicit T04 placeholder integration file.
- `.gsd/DECISIONS.md` — recorded the streaming opt-in boundary decision.
- `.gsd/milestones/M001/slices/S05/S05-PLAN.md` — marked T01 complete.
- `.gsd/STATE.md` — advanced slice state to T02.
