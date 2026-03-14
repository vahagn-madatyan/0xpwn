---
id: T01
parent: S03
milestone: M001
provides:
  - Agent exception hierarchy (AgentError, AgentMaxIterationsError)
  - Typed event dataclasses and AgentEventCallback protocol
  - ToolRegistry with OpenAI schema generation and async dispatch
  - Phase-aware system prompt builder
  - ReactAgent async ReAct loop across recon + scanning phases
  - 24 unit tests covering registry, loop, events, error handling
key_files:
  - src/oxpwn/agent/__init__.py
  - src/oxpwn/agent/exceptions.py
  - src/oxpwn/agent/events.py
  - src/oxpwn/agent/tools.py
  - src/oxpwn/agent/prompts.py
  - src/oxpwn/agent/react.py
  - tests/unit/test_tool_registry.py
  - tests/unit/test_react_agent.py
key_decisions:
  - None beyond pre-existing S03 planning decisions (16-18 in DECISIONS.md)
patterns_established:
  - ToolRegistry.register(name, description, parameters_schema, executor_factory) → get_schemas() for LLM, dispatch(name, args, sandbox) → ToolResult
  - ReactAgent composes LLMClient + DockerSandbox + ToolRegistry; outer loop over phases, inner ReAct loop per phase
  - Event emission via Protocol callback — never blocks, swallows callback errors
  - parse_tool_arguments() returns empty dict on malformed JSON (graceful degradation)
observability_surfaces:
  - structlog agent.iteration (phase, iteration, has_tool_calls)
  - structlog agent.tool_dispatch (tool_name, duration_ms)
  - structlog agent.tool_dispatch_error (tool_name, error)
  - structlog agent.phase_transition (from_phase, to_phase)
  - structlog agent.complete (phases_completed, total_iterations)
  - AgentMaxIterationsError carries phase + iteration count
duration: 20m
verification_result: passed
completed_at: 2026-03-13
blocker_discovered: false
---

# T01: Build ReAct agent core with tool registry, prompts, loop, and events

**Built the complete agent subsystem: exceptions, events, tool registry, prompts, and ReAct loop with 24 passing unit tests.**

## What Happened

Created 6 source modules in `src/oxpwn/agent/` and 2 test files. The ToolRegistry maps tool names to OpenAI function schemas and executor factories; `register_default_tools()` registers nmap. The ReactAgent runs an outer loop over phases (recon → scanning) with an inner ReAct cycle: build system prompt → LLM complete → dispatch tool calls → observe → update state. Non-tool-call responses trigger phase transitions. Conversation history is rebuilt each iteration with a fresh system prompt and accumulated within a phase, then summarized on transition. Event callbacks are emitted for all significant actions but never block or crash the loop.

## Verification

- `pytest tests/unit/test_tool_registry.py -v` — **12/12 passed**: register, get_schemas (OpenAI format), dispatch, unknown tool KeyError, nmap default registration, parse_tool_arguments edge cases
- `pytest tests/unit/test_react_agent.py -v` — **12/12 passed**: tool call dispatch + result feedback, tool_call_id matching, phase transitions, max iterations error, multiple tool calls, malformed arguments, event ordering, broken callback resilience, LLM usage accumulation, parsed_output fed to LLM
- `python3 -c "from oxpwn.agent import ReactAgent, ToolRegistry; print('imports ok')"` — no import errors

### Slice-level verification
- ✅ `pytest tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v` — 24/24 passed
- ⏳ `pytest tests/integration/test_agent_integration.py -m integration -v` — T02 deliverable (not yet created)

## Diagnostics

- grep structlog output for `agent.*` events to trace loop behavior
- Inspect `ScanState.phases_completed`, `.tool_results`, `.findings` after a run
- `AgentMaxIterationsError` includes `.phase` and `.iteration` attributes for diagnosis
- Event callback receives typed dataclasses — can be inspected in tests via `EventCollector` pattern

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `src/oxpwn/agent/__init__.py` — package exports for ReactAgent, ToolRegistry, events, exceptions
- `src/oxpwn/agent/exceptions.py` — AgentError base with phase/iteration context, AgentMaxIterationsError
- `src/oxpwn/agent/events.py` — 5 event dataclasses + AgentEventCallback protocol
- `src/oxpwn/agent/tools.py` — ToolRegistry with register/get_schemas/dispatch, nmap default registration, parse_tool_arguments
- `src/oxpwn/agent/prompts.py` — build_system_prompt (phase-aware) and build_phase_summary
- `src/oxpwn/agent/react.py` — ReactAgent with async ReAct loop, phase iteration, event emission, structlog observability
- `tests/unit/test_tool_registry.py` — 12 tests for registry behavior
- `tests/unit/test_react_agent.py` — 12 tests for agent loop with mocked LLM/sandbox
