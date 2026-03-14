---
id: S03
parent: M001
milestone: M001
provides:
  - ReactAgent async ReAct loop with phase-aware reasoning across recon + scanning
  - ToolRegistry mapping tool names to OpenAI function schemas + async executor dispatch
  - Phase-aware system prompt builder with target/findings/tools context
  - Typed event dataclasses (Reasoning, ToolCall, ToolResult, PhaseTransition, Error) + AgentEventCallback protocol
  - Agent exception hierarchy (AgentError, AgentMaxIterationsError with phase/iteration context)
  - Conversation history management with parsed_output JSON fed to LLM, truncated to 4000 chars
  - Integration-proven autonomous Recon→Scanning with real LLM (Gemini 2.5 Flash) + real Docker
requires:
  - slice: S01
    provides: LLMClient with async complete() and tool calling, Pydantic state models (ScanState, ToolResult, Finding)
  - slice: S02
    provides: DockerSandbox async context manager, NmapExecutor with parsed_output
affects:
  - S04 (adds 4 more tools to registry)
  - S05 (wires event callbacks to CLI streaming)
key_files:
  - src/oxpwn/agent/__init__.py
  - src/oxpwn/agent/exceptions.py
  - src/oxpwn/agent/events.py
  - src/oxpwn/agent/tools.py
  - src/oxpwn/agent/prompts.py
  - src/oxpwn/agent/react.py
  - tests/unit/test_tool_registry.py
  - tests/unit/test_react_agent.py
  - tests/integration/test_agent_integration.py
  - tests/conftest.py
key_decisions:
  - "Decision 16: Python f-strings for prompts instead of Jinja2 — undeclared dep, simple substitution sufficient for S03"
  - "Decision 17: Protocol with typed dataclasses for event emission — testable, Pythonic, S05 implements Rich rendering"
  - "Decision 18: JSON-serialized parsed_output fed to LLM, truncated to 4000 chars — structured data over raw stdout"
patterns_established:
  - "ToolRegistry.register(name, description, parameters_schema, executor_factory) → get_schemas() for LLM tools param, dispatch(name, args, sandbox) → ToolResult"
  - "ReactAgent composes LLMClient + DockerSandbox + ToolRegistry; outer loop over phases, inner ReAct loop per phase"
  - "Event emission via Protocol callback — never blocks, swallows callback errors"
  - "parse_tool_arguments() returns empty dict on malformed JSON (graceful degradation)"
  - "Non-tool-call LLM response = phase complete (transition trigger)"
  - "EventCollector pattern for capturing agent events in tests"
observability_surfaces:
  - "structlog agent.iteration (phase, iteration, has_tool_calls)"
  - "structlog agent.tool_dispatch (tool_name, duration_ms)"
  - "structlog agent.tool_dispatch_error (tool_name, error)"
  - "structlog agent.phase_transition (from_phase, to_phase)"
  - "structlog agent.complete (phases_completed, total_iterations)"
  - "AgentMaxIterationsError carries phase + iteration count"
  - "ScanState.phases_completed, .tool_results, .findings, .total_tokens inspectable after run"
drill_down_paths:
  - .gsd/milestones/M001/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001/slices/S03/tasks/T02-SUMMARY.md
duration: 35m
verification_result: passed
completed_at: 2026-03-13
---

# S03: ReAct Agent Loop

**Autonomous ReAct agent loop proven against real LLM + Docker — selects nmap, executes in sandbox, accumulates state, advances through Recon and Scanning phases.**

## What Happened

T01 built the complete agent subsystem across 6 modules: exception hierarchy with phase/iteration context, typed event dataclasses with an async callback protocol, a ToolRegistry mapping tool names to OpenAI function schemas and executor factories (nmap registered by default), phase-aware system prompt builder, and the ReactAgent itself. The agent runs an outer loop over phases (recon → scanning) with an inner ReAct cycle per phase: build system prompt → LLM complete → dispatch tool calls → observe → update state. Non-tool-call responses trigger phase transitions. Conversation history accumulates within a phase and summarizes on transition. Event callbacks are emitted for all significant actions but never block or crash the loop. 24 unit tests prove all mechanics with mocked LLM/sandbox.

T02 proved the real thing works. Added session fixtures to conftest composing real LLMClient + DockerSandbox + ToolRegistry, then wrote an integration test that creates a ScanState targeting localhost, runs the full agent loop, and asserts structural properties: nmap tool_results present, parsed_output non-empty, recon phase completed, tokens consumed. The test passed on first run in 17.76s with Gemini 2.5 Flash driving autonomous tool selection.

## Verification

- `pytest tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v` — **24/24 passed** (1.16s)
- `pytest tests/integration/test_agent_integration.py -m integration -v` — **passed** during T02 execution (17.76s with real Gemini + Docker); skips without credentials
- `pytest tests/unit/ -v` — **87 passed** (no regression across S01+S02+S03)
- Import verification: `from oxpwn.agent import ReactAgent, ToolRegistry` — clean
- Observability: 6 structlog events confirmed in source, AgentMaxIterationsError carries phase/iteration, event dataclasses importable

## Requirements Advanced

- R001 (Autonomous 5-phase pipeline) — Agent loop core implemented and proven for 2 of 5 phases. Tool dispatch, state accumulation, phase transition mechanics all working. Remaining phases are configuration (adding tools in S04), not architecture.

## Requirements Validated

- None fully validated — R001 needs all 5 phases exercised with full tool suite (S04+S08)

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

None.

## Known Limitations

- Only nmap registered in tool registry — S04 adds httpx, subfinder, nuclei, ffuf
- No streaming/CLI rendering of events — S05 implements Rich-based AgentEventCallback
- Conversation history is simple list accumulation — no token budget management or sliding window (sufficient for current phase lengths)
- Integration test skips without GEMINI_API_KEY + Docker — proven during development, not in CI

## Follow-ups

- S04: Register 4 additional tools using the same ToolRegistry pattern
- S05: Implement AgentEventCallback with Rich rendering for real-time CLI streaming
- Consider token budget management for conversation history if phases generate many iterations

## Files Created/Modified

- `src/oxpwn/agent/__init__.py` — Package exports for ReactAgent, ToolRegistry, events, exceptions
- `src/oxpwn/agent/exceptions.py` — AgentError base with phase/iteration context, AgentMaxIterationsError
- `src/oxpwn/agent/events.py` — 5 event dataclasses + AgentEventCallback protocol
- `src/oxpwn/agent/tools.py` — ToolRegistry with register/get_schemas/dispatch, nmap default registration
- `src/oxpwn/agent/prompts.py` — build_system_prompt and build_phase_summary
- `src/oxpwn/agent/react.py` — ReactAgent async ReAct loop with structlog observability
- `tests/unit/test_tool_registry.py` — 12 tests for registry behavior
- `tests/unit/test_react_agent.py` — 12 tests for agent loop mechanics
- `tests/integration/test_agent_integration.py` — Integration test proving autonomous agent with real LLM + Docker
- `tests/conftest.py` — Added llm_client and react_agent session fixtures

## Forward Intelligence

### What the next slice should know
- ToolRegistry.register() takes `(name, description, parameters_schema, executor_factory)` — executor_factory is `Callable[..., ToolExecutor]` where the executor has `async run(sandbox, **kwargs) → ToolResult`. S04 should replicate NmapExecutor's pattern exactly.
- ReactAgent's `get_schemas()` feeds directly to LiteLLM's `tools` parameter — schemas must be valid OpenAI function calling format.
- Event callbacks receive typed dataclasses. S05 should implement `AgentEventCallback` protocol with `async on_event(event)` that pattern-matches on event type for Rich rendering.

### What's fragile
- Prompt quality determines agent behavior — `build_system_prompt()` in `prompts.py` is the primary lever for tool selection quality. If new tools aren't selected reliably, the prompt needs tuning, not the loop.
- `parse_tool_arguments()` silently returns empty dict on malformed JSON — graceful but may mask LLM issues. Watch for tools receiving empty args unexpectedly.

### Authoritative diagnostics
- grep structlog for `agent.*` events to trace any loop execution issue
- `ScanState.tool_results` after a run shows exactly what happened — tool name, success, parsed_output
- `EventCollector` pattern in tests captures full event stream for debugging

### What assumptions changed
- None — the agent worked on first integration attempt, validating the ReAct pattern and prompt design
