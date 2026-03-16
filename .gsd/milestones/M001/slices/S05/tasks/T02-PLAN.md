---
estimated_steps: 3
estimated_files: 6
---

# T02: Teach the five tool executors to forward live output without breaking parsing

**Slice:** S05 — Streaming CLI + Real-time Output
**Milestone:** M001

## Description

Once the core streaming hook exists, make it reachable from real tools. This task teaches the S04 five-tool suite to opt into live chunk forwarding when the agent asks for it, while preserving the buffered stdout/stderr and parsed-output behavior that the current agent loop already relies on.

## Steps

1. Update each built-in executor (`nmap`, `httpx`, `subfinder`, `nuclei`, `ffuf`) to accept an optional output callback alongside their existing typed arguments and to use the new sandbox streaming path only when that callback is supplied.
2. Keep command construction and parser behavior stable: live chunks are display-only, while final `parsed_output` must still be derived from the complete buffered stdout and degrade gracefully to `None` on parse failures.
3. Add `tests/unit/test_tool_streaming.py` with fake-sandbox coverage proving each executor selects the streaming path when requested and still returns buffered stdout/stderr plus compact parsed output; run the existing parser tests as regression coverage.

## Must-Haves

- [ ] All five built-in executors can stream output without changing their typed user-facing arguments
- [ ] Final buffered stdout/stderr and parsed-output contracts remain unchanged for existing callers
- [ ] Parse-failure degradation (`parsed_output=None` + diagnostics) still holds on the streaming path
- [ ] A single regression test file covers streaming-path adoption across the full built-in suite

## Verification

- `pytest tests/unit/test_tool_streaming.py tests/unit/test_httpx_parser.py tests/unit/test_subfinder_parser.py tests/unit/test_nuclei_parser.py tests/unit/test_ffuf_parser.py -v`
- `python3 -c "from oxpwn.sandbox.tools import NmapExecutor, HttpxExecutor, SubfinderExecutor, NucleiExecutor, FfufExecutor; print('imports ok')"`

## Observability Impact

- Signals added/changed: real tool executors now surface stdout/stderr chunks while preserving existing parse-failure warnings and buffered `ToolResult` inspection surfaces
- How a future agent inspects this: use `tests/unit/test_tool_streaming.py` to isolate executor adoption failures, then inspect executor return values and parse warnings for a specific tool
- Failure state exposed: executors that forget to opt into streaming or that lose parser/buffer parity fail deterministically in unit coverage

## Inputs

- `src/oxpwn/sandbox/tools/nmap.py` — S02 reference executor contract
- `src/oxpwn/sandbox/tools/httpx.py` — recon JSONL executor from S04
- `src/oxpwn/sandbox/tools/subfinder.py` — recon JSONL executor from S04
- `src/oxpwn/sandbox/tools/nuclei.py` — scanning JSONL executor from S04
- `src/oxpwn/sandbox/tools/ffuf.py` — scanning JSON executor from S04
- T01 summary — optional output sink + sandbox streaming contract now exist and must be adopted uniformly

## Expected Output

- `src/oxpwn/sandbox/tools/nmap.py` — optional live-output forwarding for `nmap`
- `src/oxpwn/sandbox/tools/httpx.py` — optional live-output forwarding for `httpx`
- `src/oxpwn/sandbox/tools/subfinder.py` — optional live-output forwarding for `subfinder`
- `src/oxpwn/sandbox/tools/nuclei.py` — optional live-output forwarding for `nuclei`
- `src/oxpwn/sandbox/tools/ffuf.py` — optional live-output forwarding for `ffuf`
- `tests/unit/test_tool_streaming.py` — suite-wide streaming regression coverage for built-in executors
