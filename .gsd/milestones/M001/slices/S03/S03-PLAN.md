# S03: ReAct Agent Loop

**Goal:** Agent autonomously reasons through Recon and Scanning phases, selecting tools, executing them in the sandbox, parsing results, accumulating state, and transitioning between phases.
**Demo:** Integration test proves the agent calls nmap via the sandbox, incorporates results into state, and advances from Recon to Scanning — driven by a real LLM and real Docker.

## Must-Haves

- Tool registry mapping tool names to OpenAI function schemas + async executor callables
- Phase-aware system prompts with target, findings summary, and available tools
- Async ReAct loop: build messages → LLM complete → dispatch tool calls → observe → update state → repeat
- Phase transition on non-tool-call LLM response (spec: no tool call = phase complete)
- Configurable max iterations per phase as safety valve
- Event protocol (typed dataclasses + callback interface) for S05 streaming hookup
- Agent exception hierarchy (AgentError, AgentMaxIterationsError)
- Conversation history management: feed `parsed_output` JSON to LLM (not raw stdout), summarize on phase transition
- Unit tests with mocked LLM/Docker proving loop mechanics, dispatch, phase transitions, error handling
- Integration test proving autonomous Recon→Scanning with real LLM + real Docker

## Proof Level

- This slice proves: integration (agent + LLM + sandbox working as a system)
- Real runtime required: yes (LLM API + Docker daemon for integration test)
- Human/UAT required: no

## Verification

- `pytest tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v` — all unit tests pass (mocked, no external deps)
- `pytest tests/integration/test_agent_integration.py -m integration -v` — agent completes Recon phase with real LLM + Docker, calls nmap, accumulates state

## Observability / Diagnostics

- Runtime signals: structlog events `agent.iteration`, `agent.tool_dispatch`, `agent.phase_transition`, `agent.complete` with phase, iteration count, tool name, duration
- Inspection surfaces: `ScanState.phases_completed`, `ScanState.tool_results`, `ScanState.findings` — full scan lifecycle inspectable via model serialization
- Failure visibility: `AgentMaxIterationsError` carries phase and iteration count; structlog `agent.tool_dispatch_error` with tool name and error detail
- Redaction constraints: LLM API keys never logged (inherited from S01's LLMClient)

## Integration Closure

- Upstream surfaces consumed: `oxpwn.llm.client.LLMClient.complete()`, `oxpwn.sandbox.docker.DockerSandbox`, `oxpwn.sandbox.tools.nmap.NmapExecutor`, `oxpwn.core.models.ScanState` mutation methods
- New wiring introduced: `ReactAgent` composes LLMClient + DockerSandbox + ToolRegistry into an autonomous loop; tool registry maps OpenAI schemas to executors
- What remains: S04 adds 4 more tools to registry, S05 wires event callbacks to CLI streaming, S06-S08 complete the milestone

## Tasks

- [x] **T01: Build ReAct agent core with tool registry, prompts, loop, and events** `est:45m`
  - Why: All agent components are tightly coupled — registry feeds the loop, prompts are consumed by the loop, events are emitted by the loop. Building them together with unit tests proves the mechanics work before hitting real runtime.
  - Files: `src/oxpwn/agent/__init__.py`, `src/oxpwn/agent/tools.py`, `src/oxpwn/agent/prompts.py`, `src/oxpwn/agent/react.py`, `src/oxpwn/agent/events.py`, `src/oxpwn/agent/exceptions.py`, `tests/unit/test_tool_registry.py`, `tests/unit/test_react_agent.py`
  - Do: (1) Create `agent/exceptions.py` with `AgentError` base and `AgentMaxIterationsError` carrying phase+iteration context. (2) Create `agent/events.py` with event dataclasses (`ReasoningEvent`, `ToolCallEvent`, `ToolResultEvent`, `PhaseTransitionEvent`, `ErrorEvent`) and an `AgentEventCallback` Protocol with async methods. (3) Create `agent/tools.py` with `ToolRegistry` class — `register(name, schema, executor_factory)`, `get_schemas()` → list for LLM tools param, `dispatch(name, arguments, sandbox)` → ToolResult. Register nmap with schema matching NmapExecutor.run() signature. (4) Create `agent/prompts.py` with `build_system_prompt(phase, target, tools_summary, findings_summary)` and `build_phase_transition_summary(phase, tool_results, findings)` using Python f-strings. (5) Create `agent/react.py` with `ReactAgent(llm_client, sandbox, registry, max_iterations_per_phase, event_callback)`. Implement `async run(scan_state)` — outer loop over phases, inner ReAct loop per phase. Handle parallel tool calls (execute sequentially, append all results). Feed `parsed_output` JSON to LLM messages, truncate to 4000 chars. Summarize phase on transition. Non-tool-call response = phase complete. (6) Unit tests: tool registry CRUD, dispatch, schema generation; agent loop with mocked LLM returning tool calls then text, phase transition, max iterations error, parallel tool calls, malformed arguments handling.
  - Verify: `pytest tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v` — all pass
  - Done when: Agent loop mechanics proven with mocks — tool dispatch, state accumulation, phase transitions, error handling all exercised

- [x] **T02: Integration test proving autonomous Recon→Scanning with real LLM and Docker** `est:30m`
  - Why: The primary risk from the roadmap is "agent loop quality" — unit tests with mocked LLM can't prove the agent actually reasons well. This task writes and runs the integration proof against real runtime.
  - Files: `tests/integration/test_agent_integration.py`, `tests/conftest.py`
  - Do: (1) Add `react_agent` fixture to conftest composing real LLMClient + docker_sandbox + ToolRegistry with nmap registered. (2) Write integration test: create ScanState with a scannable target (localhost/Docker bridge), run agent for Recon phase only (1 phase, not full scan), assert: nmap was called (tool_results non-empty), ScanState.phases_completed contains recon, parsed_output is not None. Assert structural properties — not exact output content (LLM non-determinism). (3) Use reasonable timeout (120s) and skip markers for missing Docker/LLM credentials. (4) Debug and iterate if the LLM doesn't call nmap as expected — adjust system prompt, tool schema, or test assertions until the proof passes.
  - Verify: `pytest tests/integration/test_agent_integration.py -m integration -v` — passes with real LLM + Docker
  - Done when: Agent autonomously selects and runs nmap in Docker, incorporates results into scan state — the roadmap risk "agent loop quality" is partially retired

## Files Likely Touched

- `src/oxpwn/agent/__init__.py`
- `src/oxpwn/agent/exceptions.py`
- `src/oxpwn/agent/events.py`
- `src/oxpwn/agent/tools.py`
- `src/oxpwn/agent/prompts.py`
- `src/oxpwn/agent/react.py`
- `tests/unit/test_tool_registry.py`
- `tests/unit/test_react_agent.py`
- `tests/integration/test_agent_integration.py`
- `tests/conftest.py`
