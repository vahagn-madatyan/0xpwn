---
id: T02
parent: S05
milestone: M001
provides:
  - Live-output opt-in across all five built-in executors while preserving buffered stdout/stderr and parsed_output contracts
key_files:
  - src/oxpwn/sandbox/tools/nmap.py
  - src/oxpwn/sandbox/tools/httpx.py
  - src/oxpwn/sandbox/tools/subfinder.py
  - src/oxpwn/sandbox/tools/nuclei.py
  - src/oxpwn/sandbox/tools/ffuf.py
  - tests/unit/test_tool_streaming.py
key_decisions:
  - Keep streaming adoption executor-local by branching only at the sandbox call site; all parsing and parse-failure logging still operate on the final buffered stdout/stderr after command completion
  - Cover the full five-tool suite with one fake-sandbox regression file so missed streaming adoption and buffer/parity regressions fail deterministically in one place
patterns_established:
  - Built-in executors accept an internal kw-only `output_sink` opt-in without changing their user-facing typed scan arguments or schemas
  - Streaming remains additive: `execute_stream(...)` forwards live chunks for the CLI, then the executor parses the same buffered stdout into the existing compact `parsed_output` shape
observability_surfaces:
  - tests/unit/test_tool_streaming.py
  - executor `logger.warning(...)` parse-failure events (`*.jsonl_parse_failed`, `ffuf.json_parse_failed`, `nmap.xml_parse_failed`)
  - buffered `ToolResult.stdout`, `ToolResult.stderr`, and `ToolResult.parsed_output`
duration: 1h
verification_result: passed
completed_at: 2026-03-14 21:27:00 PDT
blocker_discovered: false
---

# T02: Teach the five tool executors to forward live output without breaking parsing

**Added additive streaming opt-in to `nmap`, `httpx`, `subfinder`, `nuclei`, and `ffuf`, and proved with one suite-wide regression file that live chunk forwarding preserves buffered results plus graceful parse-failure behavior.**

## What Happened

I updated all five built-in executors to accept an optional kw-only `output_sink` and to call `sandbox.execute_stream(..., output_sink=...)` only when that sink is supplied. Legacy callers still use `sandbox.execute(...)`, so the non-streaming path and the existing tool schemas/typed scan arguments remain unchanged.

I kept command construction and parser behavior stable. Each executor still sets `result.tool_name`, parses only the final buffered `stdout`, and degrades to `parsed_output=None` with the existing warning log fields when parsing fails.

I replaced the placeholder `tests/unit/test_tool_streaming.py` file with fake-sandbox coverage across the whole five-tool suite. The new tests prove three things for every executor: streamed opt-in chooses `execute_stream(...)`, legacy calls still choose `execute(...)`, and streamed parse failures preserve raw stdout/stderr while emitting the same diagnostics shape.

## Verification

Passed:
- `pytest tests/unit/test_tool_streaming.py tests/unit/test_httpx_parser.py tests/unit/test_subfinder_parser.py tests/unit/test_nuclei_parser.py tests/unit/test_ffuf_parser.py -v`
- `python3 -c "from oxpwn.sandbox.tools import NmapExecutor, HttpxExecutor, SubfinderExecutor, NucleiExecutor, FfufExecutor; print('imports ok')"`
- `pytest tests/unit/test_nmap_parser.py -v` (extra regression because T02 also touched `nmap`)

Slice-level verification status recorded during this task:
- `pytest tests/unit/test_docker_sandbox.py tests/unit/test_tool_registry.py tests/unit/test_react_agent.py tests/unit/test_tool_streaming.py tests/unit/test_cli_streaming.py tests/unit/test_cli_main.py -v` → partial pass; all T01/T02 coverage passed, while the two intentional T03 placeholder tests still fail
- `pytest tests/integration/test_cli_integration.py -m integration -v` → expected failure on the intentional T04 placeholder test
- `pip install -e . && OXPWN_MODEL="${OXPWN_TEST_MODEL:-gemini/gemini-2.5-flash}" 0xpwn scan --target localhost` → could not run as written in this shell because `pip` is not on PATH (`/bin/bash: pip: command not found`)

## Diagnostics

To inspect this work later:
- Run `pytest tests/unit/test_tool_streaming.py -v` to isolate executor adoption, buffer parity, and parse-failure degradation across the full suite
- Inspect executor warning events for `nmap.xml_parse_failed`, `httpx.jsonl_parse_failed`, `subfinder.jsonl_parse_failed`, `nuclei.jsonl_parse_failed`, and `ffuf.json_parse_failed`
- Inspect returned `ToolResult.stdout`, `ToolResult.stderr`, and `ToolResult.parsed_output` to confirm streaming stayed display-only while buffered parsing stayed authoritative

## Deviations

None.

## Known Issues

- Remaining slice-level CLI verification is still blocked by the intentional T03/T04 placeholder tests (`tests/unit/test_cli_streaming.py`, `tests/unit/test_cli_main.py`, `tests/integration/test_cli_integration.py`)
- The exact slice smoke command currently cannot start in this shell because `pip` is not on PATH

## Files Created/Modified

- `src/oxpwn/sandbox/tools/nmap.py` — added optional `output_sink` support and streaming-path opt-in while keeping XML parsing/logging behavior unchanged
- `src/oxpwn/sandbox/tools/httpx.py` — added optional `output_sink` support and streaming-path opt-in while keeping JSONL parsing/logging behavior unchanged
- `src/oxpwn/sandbox/tools/subfinder.py` — added optional `output_sink` support and streaming-path opt-in while keeping JSONL parsing/logging behavior unchanged
- `src/oxpwn/sandbox/tools/nuclei.py` — added optional `output_sink` support and streaming-path opt-in while keeping JSONL parsing/logging behavior unchanged
- `src/oxpwn/sandbox/tools/ffuf.py` — added optional `output_sink` support and streaming-path opt-in while keeping JSON parsing/logging behavior unchanged
- `tests/unit/test_tool_streaming.py` — replaced the placeholder with suite-wide fake-sandbox coverage for streaming adoption, buffered parity, and parse-failure diagnostics
- `.gsd/milestones/M001/slices/S05/S05-PLAN.md` — marked T02 complete
- `.gsd/STATE.md` — advanced the next action to T03
