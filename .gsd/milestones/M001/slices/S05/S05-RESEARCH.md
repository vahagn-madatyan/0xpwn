# S05: Streaming CLI + Real-time Output — Research

**Date:** 2026-03-14

## Summary

S05 directly owns **R004 — Real-time agent reasoning stream**. In practice it also supports the user-visible delivery of **R001** by making phase progress observable, and it creates the CLI surface that **S06/R005** will plug into later, but the formal traceability target for this slice is R004. The good news: the codebase already has the right seams. The `0xpwn` Typer entrypoint exists, `ReactAgent` already emits typed events through an async callback protocol, and `typer` / `rich` are already first-class dependencies. This slice is primarily wiring and rendering work, not a greenfield architecture exercise.

The surprise is that “real-time output” is only partially supported today. `DockerSandbox.execute()` buffers tool output until command completion, `LLMClient.complete()` waits for a full model response, and `ReactAgent` only emits `ReasoningEvent` on turns without tool calls. That means S05 can deliver **real-time-by-step streaming** immediately — phase changes, tool dispatches, tool completion summaries, errors, final summaries — but **literal raw line-by-line tool output** and **token-by-token reasoning** require deeper interface changes across the sandbox, agent, and LLM client.

## Recommendation

Implement `0xpwn scan --target <url>` as a synchronous Typer command that calls `asyncio.run(_scan_async(...))`. Inside `_scan_async`, compose `ScanState`, `ToolRegistry`, `DockerSandbox`, and `ReactAgent`, and pass a `RichStreamingCallback` that implements `AgentEventCallback`. Render append-only output with `Console.print()`, `Rule`, `Panel`, and styled `Text`; avoid building a full-screen dashboard in this slice.

Treat streaming as two layers:

1. **Required now for S05:** event-boundary streaming from existing agent events — scan header, phase rules, reasoning blocks, tool call announcements, tool completion summaries, errors, and a final summary.
2. **Only if acceptance demands literal raw output streaming:** add `DockerSandbox.execute_stream(..., stream=True, demux=True)` and a new `ToolOutputChunkEvent` so the CLI can print tool stdout/stderr incrementally while preserving the existing buffered `ToolResult` path for parsers.

This keeps S05 small, honest, and compatible with S03/S04 while leaving a clean extension path if R004 is interpreted strictly.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI command surface and tests | Typer + `typer.testing.CliRunner` | Already chosen in Decision #10, already installed, and provides stable command parsing plus test ergonomics without custom argparse glue. |
| Terminal formatting and phase visualization | Rich `Console`, `Rule`, `Panel`, `Text`, optional `status()` | Already in dependencies and sufficient for color-coded append-only streaming without building a TUI. |
| Incremental container exec transport | Docker SDK `container.exec_run(stream=True|socket=True, demux=True)` | Current stack can support chunk streaming if needed; no reason to shell out to `docker exec` or replace docker-py. |
| Token / response streaming from the model | LiteLLM `acompletion(..., stream=True)` | If token-level reasoning becomes necessary, extend the existing LLM client instead of adding provider-specific SDK branches. |

## Existing Code and Patterns

- `pyproject.toml` — already exposes the `0xpwn` console script and includes `typer`, `rich`, `litellm`, `docker`, and `structlog`; S05 is wiring work, not dependency work.
- `src/oxpwn/cli/main.py` — existing Typer app with version callback and a stub `scan(target)` command. Extend this file in place; don’t replace the entrypoint shape.
- `src/oxpwn/agent/events.py` — authoritative streaming contract today. `RichStreamingCallback` should implement `async on_event(event)` against these typed dataclasses.
- `src/oxpwn/agent/react.py` — already emits `ToolCallEvent`, `ToolResultEvent`, `PhaseTransitionEvent`, `ErrorEvent`, and completion-side `ReasoningEvent`. Callback failures are swallowed, so renderer bugs shouldn’t kill scans.
- `src/oxpwn/sandbox/docker.py` — `execute()` currently wraps `container.exec_run(..., demux=True)` and returns only after command completion. Add a parallel streaming API instead of mutating this contract if raw tool chunks are required.
- `tests/unit/test_react_agent.py` — `EventCollector` proves event ordering and is the pattern to mirror for renderer and CLI tests.
- `tests/integration/test_agent_integration.py` — shows the minimum viable composition for S05: real `LLMClient` + `DockerSandbox` + `ToolRegistry` + `ReactAgent(event_callback=...)`.
- `tests/conftest.py` — already contains the sandbox/LLM fixture composition and deterministic test patterns S05 can reuse.

## Constraints

- S05 formally owns **R004**. It also improves the user-visible delivery of **R001**, but that support is indirect and not yet separately trace-mapped.
- `ReactAgent._PHASE_ORDER` is still only `[recon, scanning]`. The CLI can style all 5 phases, but today’s live execution only covers 2 phases.
- `LLMClient.complete()` does not use LiteLLM streaming. Reasoning can only appear after a full assistant turn finishes, not token-by-token.
- `ReactAgent` only emits `ReasoningEvent` when the model returns **no tool calls**. Tool-call turns expose tool name and arguments, but not the model’s accompanying explanatory text.
- `DockerSandbox.execute()` buffers stdout/stderr to completion, so current tool visibility is post-hoc, not live raw output.
- Tool executors parse after command completion. Streaming raw chunks would need a dual-path design: live text for the CLI, final buffered output for parsers and `ToolResult`.
- There are currently **no CLI tests**. S05 needs both Typer command tests and renderer unit tests to protect user-visible behavior.

## Common Pitfalls

- **Building a TUI instead of a streaming CLI** — S05 should stay append-only Rich output. Full-screen dashboards belong to M004/R018.
- **Over-using `Live` for log-style output** — append-only event printing with `Console.print()` and `Rule` is simpler and less flickery. Use `Live` only for a small status region if needed.
- **Changing `DockerSandbox.execute()` in place** — existing tools and tests depend on the buffered `ToolResult` contract. Add `execute_stream()` instead of rewriting the current API.
- **Claiming raw tool streaming without new plumbing** — with the current interfaces, S05 can stream phase and tool lifecycle events, not literal line-by-line tool stdout.
- **Blocking the CLI with ad-hoc async management** — keep Typer command functions synchronous and funnel async work through one `asyncio.run()` wrapper.
- **Letting renderer failures break scans** — rely on the existing callback isolation in `ReactAgent`; keep rendering side effects out of the agent core.

## Open Risks

- **Acceptance ambiguity on R004** — if “raw tool output stream” is interpreted literally, S05 expands beyond CLI wiring into sandbox and event model changes.
- **Reasoning visibility gap** — the most compelling “watch the AI think” moment is often on tool-call turns, but those thoughts are not emitted today.
- **Thin final summaries for now** — the agent accumulates `tool_results`, but findings are not yet populated end-to-end. Final scan output may feel sparse until later slices.
- **Long-tool output noise** — if raw chunk streaming is added, `nmap` / `nuclei` output may need line buffering, truncation, or verbosity controls to keep the terminal readable.
- **Future wizard integration** — S06 will need to plug into the same CLI surface. S05 should keep app/context structure simple enough to add config/bootstrap logic later without rewiring commands.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | `narumiruna/agent-skills@python-cli-typer` | available — install with `npx skills add narumiruna/agent-skills@python-cli-typer` |
| Rich | `autumnsgrove/groveengine@rich-terminal-output` | available — install with `npx skills add autumnsgrove/groveengine@rich-terminal-output` |
| CLI patterns (general) | `0xdarkmatter/claude-mods@python-cli-patterns` | available — install with `npx skills add 0xdarkmatter/claude-mods@python-cli-patterns` |
| LiteLLM | none found | no directly relevant skill found via `npx skills find "litellm"` |
| Installed skills in current environment | none directly relevant | `frontend-design`, `debug-like-expert`, and the other installed skills are not core to S05’s Typer/Rich/streaming implementation |

## Sources

- `0xpwn` console script already exists, and `scan()` is still a stub (source: `pyproject.toml`, `src/oxpwn/cli/main.py`)
- Typed agent events and callback protocol are already present for S05 to consume (source: `src/oxpwn/agent/events.py`)
- Current agent event emission omits reasoning on tool-call turns and only provides post-tool summaries (source: `src/oxpwn/agent/react.py`)
- Container execution is currently buffered, but Docker SDK supports `exec_run(..., stream=True|socket=True, demux=True)` for additive streaming work (source: `src/oxpwn/sandbox/docker.py`; [Docker SDK for Python exec_run docs](https://github.com/docker/docker-py/blob/main/docs/containers.md))
- Rich already provides the needed building blocks for styled append-only terminal output and optional live/status regions (source: [Rich console docs](https://github.com/textualize/rich/blob/master/docs/source/console.rst), [Rich live docs](https://github.com/textualize/rich/blob/master/docs/source/live.rst))
- Typer’s `CliRunner` is the right way to test the new CLI surface (source: [Typer testing docs](https://typer.tiangolo.com/tutorial/testing/))
- LiteLLM supports async streaming via `acompletion(..., stream=True)`, but the current client only exposes buffered completions (source: `src/oxpwn/llm/client.py`; [LiteLLM streaming docs](https://docs.litellm.ai/docs/completion/stream))
- Existing integration composition for a real scan path is already proven in tests and can be reused by the CLI (source: `tests/integration/test_agent_integration.py`, `tests/conftest.py`)
