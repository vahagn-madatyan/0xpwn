---
estimated_steps: 8
estimated_files: 8
---

# T01: Build ReAct agent core with tool registry, prompts, loop, and events

**Slice:** S03 — ReAct Agent Loop
**Milestone:** M001

## Description

Build all agent subsystem components — exceptions, events, tool registry, system prompts, and the ReAct loop — in a single task because they're tightly coupled. The registry feeds tool schemas and dispatch to the loop, prompts are built and consumed by the loop each iteration, events are emitted by the loop. Unit tests with mocked LLM and sandbox prove the mechanics work before T02 hits real runtime.

## Steps

1. Create `src/oxpwn/agent/exceptions.py` — `AgentError(Exception)` base with optional `phase` and `iteration` context fields. `AgentMaxIterationsError(AgentError)` raised when a phase exhausts its iteration budget.

2. Create `src/oxpwn/agent/events.py` — Dataclass event types: `ReasoningEvent(content, phase, iteration)`, `ToolCallEvent(tool_name, arguments, phase, iteration)`, `ToolResultEvent(tool_name, result_summary, duration_ms, phase, iteration)`, `PhaseTransitionEvent(from_phase, to_phase, summary)`, `ErrorEvent(error, phase, iteration)`. Define `AgentEventCallback` as a `Protocol` with `async on_event(event: AgentEvent)` where `AgentEvent` is a Union of the event types.

3. Create `src/oxpwn/agent/tools.py` — `ToolRegistry` class. `register(name, description, parameters_schema, executor_factory)` stores the OpenAI function schema and a callable `(sandbox) → executor_instance`. `get_schemas()` returns `list[dict]` in OpenAI tool format for `LLMClient.complete(tools=...)`. `dispatch(name, arguments, sandbox)` instantiates the executor via factory, calls `await executor.run(**arguments)`, returns `ToolResult`. Register nmap: schema mirrors `NmapExecutor.run(target, ports, flags)` signature with proper JSON Schema types and descriptions. Handle `KeyError` for unknown tools, `json.JSONDecodeError` for malformed arguments.

4. Create `src/oxpwn/agent/prompts.py` — `build_system_prompt(phase, target, available_tools, findings_summary)` returns the system message string. Phase-specific guidance: recon phase tells agent to enumerate services/ports, scanning phase tells agent to probe discovered services. `build_phase_summary(phase, tool_results, findings)` returns a condensed text summary of what was learned in a phase, for conversation history management on phase transition.

5. Create `src/oxpwn/agent/react.py` — `ReactAgent` class:
   - Constructor: `(llm_client, sandbox, tool_registry, max_iterations_per_phase=10, event_callback=None)`
   - `async run(scan_state) → ScanState`: outer loop iterates phases (only recon+scanning for S03 scope), inner loop is the ReAct cycle
   - Inner loop per iteration: build system prompt → append to conversation history → `await llm_client.complete(messages, tools=registry.get_schemas())` → `scan_state.record_llm_usage(response)` → if no tool_calls: emit PhaseTransitionEvent, summarize phase, advance_phase, break → if tool_calls: for each call, parse arguments with `json.loads()`, dispatch via registry, append tool result message with matching `tool_call_id`, update scan_state, emit events
   - Conversation history: system message rebuilt each iteration (fresh findings summary), assistant+tool messages accumulate within a phase, cleared on phase transition (replaced by phase summary)
   - Tool result message format: `{"role": "tool", "tool_call_id": id, "name": name, "content": truncated_json}`
   - Tool output for LLM: serialize `parsed_output` as JSON if available, else truncate stdout to 4000 chars
   - Emit events through callback if provided, never block on missing callback
   - Raise `AgentMaxIterationsError` if inner loop hits limit

6. Create `src/oxpwn/agent/__init__.py` — export `ReactAgent`, `ToolRegistry`, `AgentEventCallback`, event types, exceptions.

7. Write `tests/unit/test_tool_registry.py` — test register + get_schemas returns valid OpenAI format, dispatch calls executor and returns ToolResult, dispatch unknown tool raises KeyError, nmap schema is registered by default factory helper.

8. Write `tests/unit/test_react_agent.py` — mock LLMClient and DockerSandbox. Test: (a) agent calls LLM with tool schemas, dispatches tool call, feeds result back, calls LLM again; (b) non-tool-call response triggers phase transition; (c) max iterations raises AgentMaxIterationsError; (d) multiple tool calls in one response handled sequentially; (e) malformed tool call arguments logged and skipped gracefully; (f) event callback receives events in order; (g) scan_state accumulates tool_results and advances phase.

## Must-Haves

- [ ] ToolRegistry maps names to OpenAI schemas + executor factories, dispatch returns ToolResult
- [ ] ReactAgent.run() iterates LLM→dispatch→observe loop with proper message format
- [ ] tool_call_id matching between assistant tool_call and tool result message
- [ ] Non-tool-call response = phase complete (spec rule)
- [ ] Max iterations per phase raises AgentMaxIterationsError
- [ ] parsed_output JSON fed to LLM (not raw stdout)
- [ ] Event protocol defined with typed dataclasses
- [ ] All unit tests pass with mocked dependencies

## Verification

- `pytest tests/unit/test_tool_registry.py -v` — all pass
- `pytest tests/unit/test_react_agent.py -v` — all pass
- `python3 -c "from oxpwn.agent import ReactAgent, ToolRegistry; print('imports ok')"` — no import errors

## Observability Impact

- Signals added: structlog events `agent.iteration` (phase, iteration, has_tool_calls), `agent.tool_dispatch` (tool_name, duration_ms), `agent.tool_dispatch_error` (tool_name, error), `agent.phase_transition` (from_phase, to_phase), `agent.complete` (phases_completed, total_iterations)
- How a future agent inspects this: grep structlog output for `agent.*` events; inspect ScanState model after run
- Failure state exposed: AgentMaxIterationsError carries phase + iteration count; AgentError carries phase context

## Inputs

- `src/oxpwn/llm/client.py` — LLMClient.complete(messages, tools) → LLMResponse with tool_calls
- `src/oxpwn/sandbox/docker.py` — DockerSandbox for executor construction
- `src/oxpwn/sandbox/tools/nmap.py` — NmapExecutor pattern (constructor takes sandbox, run() returns ToolResult)
- `src/oxpwn/core/models.py` — ScanState mutation methods, Phase enum, ToolResult, LLMResponse
- `src/oxpwn/llm/exceptions.py` — Exception pattern to follow

## Expected Output

- `src/oxpwn/agent/__init__.py` — subpackage with clean exports
- `src/oxpwn/agent/exceptions.py` — AgentError hierarchy
- `src/oxpwn/agent/events.py` — typed event dataclasses + callback Protocol
- `src/oxpwn/agent/tools.py` — ToolRegistry with nmap registered
- `src/oxpwn/agent/prompts.py` — phase-aware system prompt builder
- `src/oxpwn/agent/react.py` — ReactAgent with async ReAct loop
- `tests/unit/test_tool_registry.py` — registry unit tests
- `tests/unit/test_react_agent.py` — agent loop unit tests with mocked deps
