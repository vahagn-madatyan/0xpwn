---
estimated_steps: 4
estimated_files: 7
---

# T01: Add additive streaming events and sandbox execution hooks

**Slice:** S05 — Streaming CLI + Real-time Output
**Milestone:** M001

## Description

Close the core honesty gap in S05 before touching CLI formatting. Today the agent only emits reasoning on non-tool turns and the sandbox only returns buffered output after command completion. This task adds typed events and an additive streaming execution path that future CLI code can consume without breaking the buffered `ToolResult` contract established in S02/S03.

## Steps

1. Extend `src/oxpwn/agent/events.py` with a typed raw-output event for stdout/stderr chunks and any small event-shape additions needed for Rich rendering, while keeping the callback protocol type-safe.
2. Update `src/oxpwn/agent/react.py` and `src/oxpwn/agent/tools.py` so assistant reasoning text is emitted whenever present, an optional output sink can be passed through tool dispatch, and streamed chunks become agent events with phase/iteration/tool context.
3. Add `DockerSandbox.execute_stream(...)` in `src/oxpwn/sandbox/docker.py` using Docker’s streaming exec path so stdout/stderr chunks are forwarded live, buffered into a final `ToolResult`, and kept under the same timeout/not-running semantics as `execute()`.
4. Expand `tests/unit/test_react_agent.py`, `tests/unit/test_tool_registry.py`, and `tests/unit/test_docker_sandbox.py` to assert event ordering, chunk forwarding, and parity between streamed and buffered execution paths.

## Must-Haves

- [ ] New event types remain typed and usable through the existing callback protocol
- [ ] `execute_stream(...)` returns the same final buffered `ToolResult` shape as `execute()`
- [ ] Stdout and stderr chunks stay distinguishable for later CLI styling
- [ ] Existing non-streaming callers keep working without code changes

## Verification

- `pytest tests/unit/test_docker_sandbox.py tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v`
- `python3 -c "from oxpwn.agent.events import ToolOutputChunkEvent; print('imports ok')"`

## Observability Impact

- Signals added/changed: streamed output events carrying phase, iteration, tool name, and stdout/stderr source; sandbox streaming logs alongside existing `sandbox.execute`
- How a future agent inspects this: run the targeted unit tests and inspect captured event lists / buffered `ToolResult` payloads to localize agent-vs-sandbox failures
- Failure state exposed: missing chunk forwarding, wrong event ordering, or timeout/not-running regressions become explicit in unit assertions instead of silently degrading to post-hoc output only

## Inputs

- `src/oxpwn/agent/events.py` — current typed callback contract from S03
- `src/oxpwn/agent/react.py` — current event-emission points and iteration/phase context
- `src/oxpwn/agent/tools.py` — current dispatch boundary between agent and executors
- `src/oxpwn/sandbox/docker.py` — buffered execution contract from S02 that must remain intact
- S05 research — current gap is reasoning-on-tool-turns plus buffered-only sandbox output

## Expected Output

- `src/oxpwn/agent/events.py` — extended event contract including raw-output chunks
- `src/oxpwn/agent/react.py` — richer event emission and output-sink wiring
- `src/oxpwn/agent/tools.py` — dispatch support for optional streamed tool output
- `src/oxpwn/sandbox/docker.py` — additive streaming execution path returning buffered results
- `tests/unit/test_react_agent.py` — event-order and reasoning/tool-stream assertions
- `tests/unit/test_tool_registry.py` — dispatch contract coverage for optional output sinks
- `tests/unit/test_docker_sandbox.py` — streaming sandbox contract coverage
