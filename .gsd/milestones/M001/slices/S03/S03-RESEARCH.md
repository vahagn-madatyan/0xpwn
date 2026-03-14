# S03: ReAct Agent Loop — Research

**Date:** 2026-03-13

## Summary

The upstream contracts from S01 and S02 are clean and narrow — this slice has a solid foundation. `LLMClient.complete(messages, tools)` returns `LLMResponse` with tool calls in OpenAI format. `DockerSandbox.execute()` returns `ToolResult`. `ScanState` has mutation methods ready for the loop to drive. The main work is: (1) a tool registry mapping OpenAI function schemas to executor callables, (2) the ReAct loop itself — iterating LLM call → tool dispatch → observe → repeat, (3) phase-aware system prompts, and (4) an event emission interface for S05 to hook into later.

The spec prescribes a per-phase loop with max 20 iterations and stuck detection at 3 repeats, but S03's scope is proving the agent can autonomously reason through Recon and Scanning — not full safety controls. Stuck detection (R024) is owned by M002/S06. Budget enforcement (R008) is M002/S02. Permission tiers (R007) are M002/S01. S03 should implement basic iteration limits and phase transitions, but skip the safety mechanisms that have their own slices.

The trickiest design question is conversation history management. Each ReAct iteration appends assistant + tool messages. A 20-iteration phase with nmap output could easily blow past context windows on smaller models. The spec says "summarize completed phase results, keep current phase in full detail" — implementing a phase summary on transition keeps things bounded.

## Recommendation

Build a `ReactAgent` class in `src/oxpwn/agent/react.py` with:

- **Tool registry** (`src/oxpwn/agent/tools.py`) — maps tool names to OpenAI function schemas + async executor callables. Only nmap registered in S03; S04 adds the rest. The registry provides the `tools` list for `LLMClient.complete()` and the dispatch lookup for executing calls.
- **System prompts** — Python string templates (not Jinja2 — see rationale below) in `src/oxpwn/agent/prompts.py`. Phase-specific context, available tools, accumulated findings summary, and target info injected at each iteration.
- **ReAct loop** — `async run(scan_state)` iterates: build messages → `llm.complete(messages, tools)` → if no tool call, check for phase transition or completion → if tool call, dispatch via registry → append result → update state → repeat. Max iterations per phase as a safety valve.
- **Event protocol** — a simple callback/protocol interface (`AgentEvent`) that S05 will use to stream reasoning, tool calls, results, and phase transitions. Designed now, consumed later.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Tool calling format | LiteLLM OpenAI format | Already proven in S01 — `LLMClient.complete()` accepts `tools` param and returns parsed `tool_calls` |
| Tool dispatch | S02's `NmapExecutor` pattern | Constructor takes sandbox, `run()` returns `ToolResult` — uniform interface to wrap |
| State accumulation | `ScanState` mutation methods | `add_finding()`, `add_tool_result()`, `advance_phase()`, `record_llm_usage()` already exist |
| JSON argument parsing | `json.loads()` | LiteLLM returns `tool_call.function.arguments` as a JSON string — standard stdlib parse |

## Existing Code and Patterns

- `src/oxpwn/llm/client.py` — `LLMClient.complete(messages, tools)` → `LLMResponse`. Tool calls returned as `list[dict]` with `id`, `type`, `function.name`, `function.arguments` (JSON string). The agent loop must: (1) pass tool schemas as the `tools` param, (2) parse `function.arguments` from JSON string, (3) feed results back as `role: "tool"` messages with matching `tool_call_id`.
- `src/oxpwn/sandbox/tools/nmap.py` — `NmapExecutor(sandbox).run(target, ports, flags)` → `ToolResult`. The agent needs to translate LLM tool call arguments into executor method arguments. The `run()` signature (`target`, `ports`, `flags`) must be mirrored in the OpenAI function schema.
- `src/oxpwn/core/models.py` — `Phase` StrEnum defines all 5 phases in order. `ScanState.advance_phase()` appends current to `phases_completed` and sets `current_phase`. The loop uses this to track progression.
- `src/oxpwn/llm/exceptions.py` — Exception hierarchy pattern to follow for agent-specific errors (`AgentError`, `AgentStuckError`, `AgentMaxIterationsError`).
- `tests/conftest.py` — Session-scoped `docker_sandbox` fixture with skip-if-no-Docker guard. Agent integration tests will compose this with an LLM client fixture.

## Constraints

- **Only nmap is available in S03** — the Dockerfile only installs nmap. Agent integration tests can only prove Recon/Scanning with nmap. S04 adds the other 4 tools.
- **Tool call argument format** — LiteLLM returns `function.arguments` as a JSON string, not a parsed dict. The agent must `json.loads()` it before passing to executors.
- **Tool result feedback format** — results must go back as `{"role": "tool", "tool_call_id": "<id>", "name": "<tool_name>", "content": "<stringified result>"}`. The `tool_call_id` must match the original call's `id` field.
- **LLMResponse.tool_calls structure** — S01's `_parse_tool_calls()` returns `list[dict]` with keys `id`, `type`, `function` (containing `name` and `arguments`). The loop indexes into this shape.
- **Context window limits** — nmap `-sV` output can be 500+ lines for large scans. Raw stdout in tool messages will consume context fast. Summarize or truncate tool output before feeding back.
- **Async throughout** — `LLMClient.complete()` and `DockerSandbox.execute()` are both async. The agent loop must be async too.
- **`asyncio_mode = "auto"` in pytest** — tests can use `async def` directly, no manual event loop management needed.

## Common Pitfalls

- **Not matching tool_call_id** — if the tool result message's `tool_call_id` doesn't match the assistant's tool call `id`, the LLM provider rejects the request or hallucinates. Must be exact.
- **Treating arguments as dict when it's a string** — `tool_call["function"]["arguments"]` is a JSON string from LiteLLM, not a dict. Forgetting `json.loads()` causes executor argument errors.
- **Unbounded conversation history** — each iteration adds 2+ messages (assistant + tool result). After 10 iterations, that's 20+ messages with potentially large tool output. Need truncation or summarization strategy.
- **Phase transition ambiguity** — if the LLM doesn't call a tool AND doesn't explicitly say "phase complete", the loop needs a heuristic. The spec's flow says `TOOL? → No → DONE (Phase Complete)` — so a non-tool-call response signals phase completion.
- **Parallel tool calls** — LiteLLM can return multiple tool calls in one response. The loop must handle all of them, executing sequentially (tools share the sandbox) and appending all results before the next LLM call.
- **Model differences in tool calling** — some models (especially Ollama) may not support `tool_choice="auto"` or may return malformed arguments. The loop needs graceful handling of `json.JSONDecodeError` on argument parsing.

## Open Risks

- **Agent reasoning quality** — this is the primary risk from the roadmap. The LLM may hallucinate nmap flags, fail to interpret results, or loop without making progress. The integration test is the proof point — it must show the agent making sensible tool calls and interpreting results.
- **Context window exhaustion on smaller models** — Ollama models (8B-70B) have 4K-128K context windows. A multi-phase scan with verbose nmap output could exhaust context. Mitigation: truncate tool output to first N characters in messages, keep full output in `ToolResult.stdout`.
- **Phase transition reliability** — the LLM must decide when recon is "done enough" to move to scanning. If it transitions too early, scanning misses targets. If too late, it wastes iterations. The system prompt must give clear guidance on transition criteria.
- **Integration test flakiness** — real LLM + real Docker means slow tests (~30-60s) and potential LLM non-determinism. Tests should assert structural properties (tool was called, result was parsed, phase advanced) not exact output content.

## Design Decisions to Make During Planning

1. **Jinja2 vs Python string templates for prompts** — the spec says Jinja2 but it's not in `pyproject.toml` dependencies. Jinja2 is available as a transitive dep (via other packages) but undeclared. For S03, Python f-strings/str.format are sufficient — prompts have simple variable substitution (target, phase, findings summary, tools list). Add Jinja2 as an explicit dep only when templates need conditionals/loops (likely S05 or S06). Avoids adding a dependency for no immediate benefit.

2. **Event emission pattern** — the agent needs to emit events (reasoning, tool_call, tool_result, phase_transition, error) that S05 will render. Options: (a) callback function, (b) Protocol/ABC with typed methods, (c) async generator yielding events. Recommendation: typed Protocol with async methods — most Pythonic, testable with a mock, and S05 can implement it with Rich rendering. Define event dataclasses now.

3. **Tool output truncation** — nmap output can be large. Options: (a) truncate stdout to N chars in the LLM message, keep full in ToolResult, (b) only feed parsed_output (structured dict) to LLM, not raw stdout. Recommendation: feed JSON-serialized `parsed_output` when available, fall back to truncated stdout. Structured data is smaller and more useful for reasoning.

4. **Max iterations** — spec says 20 per phase. For S03, 10 is likely sufficient (only 1 tool). Make it configurable with a sensible default.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| ReAct agent loop | — | none found — custom domain, no applicable skills |
| LiteLLM tool calling | — | none found — docs from Context7 are sufficient |
| Docker sandbox | — | none found — already implemented in S02 |

## Sources

- LiteLLM tool calling format uses OpenAI standard: `tools` param with `type: "function"`, results fed back as `role: "tool"` messages (source: Context7 /berriai/litellm docs)
- Spec defines ReAct loop flow: PLAN → TOOL? → EXEC → PARSE → STUCK? → UPDATE → ITER?, max 20 iter/phase, stuck detect @ 3 repeats (source: `0xpwn-spec.jsx` line 733-748)
- Prompt engineering rules from spec: Jinja2 templates, parse tool output → JSON before feeding LLM, running findings_summary, include phase + remaining budget + what tools already ran (source: `0xpwn-spec.jsx` line 556)
- Phase transition logic: non-tool-call response = phase complete, then advance to next phase (source: `0xpwn-spec.jsx` line 737)
- S01 Forward Intelligence: `LLMClient.complete()` takes `messages` + optional `tools`, returns `LLMResponse`; ScanState mutation methods are `add_finding`, `add_tool_result`, `advance_phase`, `record_llm_usage`
- S02 Forward Intelligence: `DockerSandbox` is async context manager; `NmapExecutor` pattern is the template for all tool executors
