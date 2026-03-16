---
estimated_steps: 4
estimated_files: 4
---

# T03: Wire a Rich streaming callback into the real `0xpwn scan --target` command

**Slice:** S05 — Streaming CLI + Real-time Output
**Milestone:** M001

## Description

With truthful event surfaces in place, replace the CLI stub with the actual user-facing command. This task builds an append-only Rich renderer, composes the real scan runtime behind `scan --target`, and keeps the pre-wizard configuration surface narrow so S06 can plug in without another CLI rewrite.

## Steps

1. Create `src/oxpwn/cli/streaming.py` with a `RichStreamingCallback` implementing `AgentEventCallback` and rendering scan header, phase rules, reasoning blocks, tool dispatch/results, raw stdout/stderr chunks, errors, and final summary using `Console.print()`/`Rule`/`Panel` primitives instead of a full-screen dashboard.
2. Replace the stub in `src/oxpwn/cli/main.py` with `scan --target` calling `asyncio.run(_scan_async(...))`, building `ScanState`, `ToolRegistry`, `DockerSandbox`, `LLMClient`, and `ReactAgent` from minimal env/option-backed runtime inputs that are compatible with later S06 config loading.
3. Add user-friendly error handling for missing model config, Docker failures, and agent/runtime exceptions so the CLI exits non-zero with diagnostic context but never echoes secrets.
4. Add `tests/unit/test_cli_streaming.py` and `tests/unit/test_cli_main.py` covering renderer formatting/order, `--target` parsing, fake-runtime command execution, and non-zero exits on bootstrap/runtime failures.

## Must-Haves

- [ ] `0xpwn scan --target <url>` is the primary command surface
- [ ] Renderer is append-only Rich output, not a `Live`/dashboard-style TUI
- [ ] CLI can be driven by environment/options now without blocking S06 wizard integration later
- [ ] Failure output is actionable and secret-safe

## Verification

- `pytest tests/unit/test_cli_streaming.py tests/unit/test_cli_main.py -v`
- `python3 -m oxpwn.cli.main scan --help`

## Observability Impact

- Signals added/changed: CLI-visible phase/rich blocks for reasoning, tool chunks, results, and errors; optional scan-start/scan-finish diagnostics around command execution
- How a future agent inspects this: use `CliRunner`-based tests to capture exact terminal output and assert ordering/content without needing a live terminal
- Failure state exposed: missing env/model config, Docker startup errors, and agent exceptions now surface as explicit CLI diagnostics instead of silent tracebacks or stub text

## Inputs

- `src/oxpwn/cli/main.py` — existing Typer app and stub `scan` command
- `src/oxpwn/agent/events.py` — event types the Rich callback must render
- `src/oxpwn/agent/react.py` — real runtime entrypoint emitting scan events
- T01/T02 summaries — live reasoning and tool-output events now exist and are ready for presentation
- S05 research — append-only Rich output is preferred over a full-screen dashboard in this slice

## Expected Output

- `src/oxpwn/cli/streaming.py` — Rich renderer implementing the agent callback protocol
- `src/oxpwn/cli/main.py` — real `scan --target` command and async runtime composition
- `tests/unit/test_cli_streaming.py` — renderer formatting/order coverage
- `tests/unit/test_cli_main.py` — Typer command behavior and failure-path coverage
