# S05: Streaming CLI + Real-time Output

**Goal:** Expose the existing scan runtime through `0xpwn scan --target <url>` and stream agent reasoning, raw tool output, parsed tool summaries, and color-coded phase transitions in real time with Rich.
**Demo:** Running `0xpwn scan --target localhost` with model/Docker prerequisites already configured prints append-only Rich output as the agent moves through Recon and Scanning, shows reasoning before tool use, streams tool stdout/stderr chunks live, renders parsed result summaries, and exits with a final scan summary.

This slice is grouped around the main truthfulness gap in R004. T01 and T02 close the data path first: without tool-call reasoning and live tool chunks, a CLI renderer would only pretty-print buffered summaries after the fact. T03 then builds the append-only Rich renderer and real Typer entrypoint on top of that stable event surface. T04 closes the loop at the actual command boundary so the slice ends with a runnable `0xpwn scan --target ...` path, not just helper classes.

## Requirement Coverage

- R004 — Real-time agent reasoning stream (owned): T01–T04 add the missing event/streaming plumbing, Rich rendering, CLI wiring, and terminal proof for reasoning, tool selection, raw tool output, parsed results, and phase transitions.

S05 also establishes the CLI surface that S06 will plug its wizard/config bootstrap into later, but formal ownership for R005 remains with S06.

## Must-Haves

- `0xpwn scan` accepts `--target` and executes the real async scan composition via `asyncio.run(...)`
- Scan output is append-only Rich output, not a full-screen dashboard, with distinct styling for scan header, phase transitions, reasoning, tool dispatch, raw stdout/stderr chunks, parsed result summaries, errors, and final summary
- Agent emits reasoning text on tool-call turns as well as completion turns so the CLI can show intent before action
- Sandbox/tool execution can stream raw stdout/stderr chunks live without breaking the existing buffered `ToolResult` parsing contract
- All five default tool executors can opt into live output streaming and still return the same parsed `ToolResult` shape on completion
- CLI surfaces pre-wizard model/runtime errors clearly and exits non-zero without echoing secrets
- Unit coverage exists for sandbox streaming, event emission/order, renderer formatting, and Typer command behavior
- Integration and terminal proof exercise the real `0xpwn scan --target` entrypoint rather than a stub or helper-only path

## Proof Level

- This slice proves: operational
- Real runtime required: yes
- Human/UAT required: yes

## Verification

- `pytest tests/unit/test_docker_sandbox.py tests/unit/test_tool_registry.py tests/unit/test_react_agent.py tests/unit/test_tool_streaming.py tests/unit/test_cli_streaming.py tests/unit/test_cli_main.py -v`
- `pytest tests/integration/test_cli_integration.py -m integration -v`
- `pip install -e . && OXPWN_MODEL="${OXPWN_TEST_MODEL:-gemini/gemini-2.5-flash}" 0xpwn scan --target localhost` — with Docker running and a compatible provider key already exported, the terminal shows incremental phase/tool/reasoning output instead of a buffered post-run dump

## Observability / Diagnostics

- Runtime signals: existing `agent.*`, `sandbox.*`, and `llm.complete` logs plus new streamed output events that identify phase, iteration, tool, and stdout vs stderr chunk source
- Inspection surfaces: `CliRunner`-captured output in CLI tests, Rich renderer unit tests, `ToolResult` buffers after run, and the real `0xpwn scan` terminal output
- Failure visibility: friendly CLI error panels for missing model/env/Docker failures, raw stderr chunks before tool failure, and phase/tool context on non-zero exits
- Redaction constraints: never print API keys or credential-bearing URLs; raw tool output may include target data but must not leak config secrets

## Integration Closure

- Upstream surfaces consumed: `src/oxpwn/cli/main.py`, `src/oxpwn/agent/events.py`, `src/oxpwn/agent/react.py`, `src/oxpwn/agent/tools.py`, `src/oxpwn/sandbox/docker.py`, all five S04 tool executors, `ScanState`, and `LLMClient`
- New wiring introduced: additive raw-output streaming from Docker sandbox → tool executor → agent callback → Rich renderer, plus the Typer `scan --target` command composing the real runtime
- What remains before the milestone is truly usable end-to-end: S06 first-run wizard/config, S07 CVE enrichment, and S08 full five-phase + Juice Shop validation

## Tasks

- [x] **T01: Add additive streaming events and sandbox execution hooks** `est:45m`
  - Why: R004 cannot be met honestly with the current contracts because reasoning is hidden on tool-call turns and sandbox output only appears after command completion.
  - Files: `src/oxpwn/agent/events.py`, `src/oxpwn/agent/react.py`, `src/oxpwn/agent/tools.py`, `src/oxpwn/sandbox/docker.py`, `tests/unit/test_react_agent.py`, `tests/unit/test_tool_registry.py`, `tests/unit/test_docker_sandbox.py`
  - Do: Add a typed raw-output event for stdout/stderr chunks, emit reasoning whenever the model returns assistant text, pass an optional output sink through tool dispatch, and implement an additive `DockerSandbox.execute_stream(...)` path that forwards decoded chunks live while still returning the same buffered `ToolResult` shape and preserving timeout/not-running behavior.
  - Verify: `pytest tests/unit/test_docker_sandbox.py tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v`
  - Done when: The agent callback receives reasoning and raw output events in deterministic order, and the sandbox still provides the existing buffered result contract for non-streaming callers.
- [x] **T02: Teach the five tool executors to forward live output without breaking parsing** `est:45m`
  - Why: The new streaming hook only matters if real tools use it; this task makes the S04 core suite emit truthful live output while preserving their parser contracts.
  - Files: `src/oxpwn/sandbox/tools/nmap.py`, `src/oxpwn/sandbox/tools/httpx.py`, `src/oxpwn/sandbox/tools/subfinder.py`, `src/oxpwn/sandbox/tools/nuclei.py`, `src/oxpwn/sandbox/tools/ffuf.py`, `tests/unit/test_tool_streaming.py`
  - Do: Update each built-in executor to accept an optional output callback and prefer the new sandbox streaming path when present, while keeping command construction, final buffered stdout/stderr, parsed-output normalization, and graceful parse-failure behavior unchanged for existing call sites.
  - Verify: `pytest tests/unit/test_tool_streaming.py tests/unit/test_httpx_parser.py tests/unit/test_subfinder_parser.py tests/unit/test_nuclei_parser.py tests/unit/test_ffuf_parser.py -v`
  - Done when: All five built-in executors can stream chunks live for the CLI yet still return the same compact `ToolResult` payloads that S03/S04 expect.
- [x] **T03: Wire a Rich streaming callback into the real `0xpwn scan --target` command** `est:50m`
  - Why: Once the event surface is truthful, the slice needs the actual user-facing command and renderer that turn those events into the visible selling moment.
  - Files: `src/oxpwn/cli/main.py`, `src/oxpwn/cli/streaming.py`, `tests/unit/test_cli_streaming.py`, `tests/unit/test_cli_main.py`
  - Do: Create an append-only `RichStreamingCallback` for scan header, phases, reasoning, tool calls, raw stdout/stderr chunks, results, errors, and final summary; replace the scan stub with `scan --target` calling `asyncio.run(_scan_async(...))`; compose `ScanState`, `ToolRegistry`, `DockerSandbox`, `LLMClient`, and `ReactAgent`; and expose only minimal env/option-backed runtime inputs needed before S06 so the wizard can plug in later without another CLI rewrite.
  - Verify: `pytest tests/unit/test_cli_streaming.py tests/unit/test_cli_main.py -v`
  - Done when: `CliRunner` shows phase/tool/reasoning streaming through the real command surface, and the scan command no longer prints a stub response.
- [x] **T04: Prove the terminal streaming path at the real CLI boundary** `est:35m`
  - Why: S05 is only finished when the installed `0xpwn` entrypoint itself is exercised with real scan behavior, not just renderer helpers or mocked callbacks.
  - Files: `tests/integration/test_cli_integration.py`, `tests/conftest.py`
  - Do: Add a CLI-focused integration test that invokes the Typer app through `CliRunner`, reuses the existing Docker/LLM availability gating, and asserts the captured output contains real phase transitions, reasoning/tool blocks, and completion text. Then run the installed `0xpwn scan --target ...` command as the slice smoke proof to confirm incremental terminal output.
  - Verify: `pytest tests/integration/test_cli_integration.py -m integration -v && pip install -e . && OXPWN_MODEL="${OXPWN_TEST_MODEL:-gemini/gemini-2.5-flash}" 0xpwn scan --target localhost`
  - Done when: The Typer entrypoint has integration coverage and a live terminal run shows streaming scan output from the actual installed CLI.

## Files Likely Touched

- `src/oxpwn/agent/events.py`
- `src/oxpwn/agent/react.py`
- `src/oxpwn/agent/tools.py`
- `src/oxpwn/sandbox/docker.py`
- `src/oxpwn/sandbox/tools/nmap.py`
- `src/oxpwn/sandbox/tools/httpx.py`
- `src/oxpwn/sandbox/tools/subfinder.py`
- `src/oxpwn/sandbox/tools/nuclei.py`
- `src/oxpwn/sandbox/tools/ffuf.py`
- `src/oxpwn/cli/main.py`
- `src/oxpwn/cli/streaming.py`
- `tests/unit/test_docker_sandbox.py`
- `tests/unit/test_tool_registry.py`
- `tests/unit/test_react_agent.py`
- `tests/unit/test_tool_streaming.py`
- `tests/unit/test_cli_streaming.py`
- `tests/unit/test_cli_main.py`
- `tests/integration/test_cli_integration.py`
- `tests/conftest.py`
