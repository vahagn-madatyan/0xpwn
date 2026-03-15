---
id: T02
parent: S04
milestone: M001
provides:
  - `HttpxExecutor` and `SubfinderExecutor` that follow the S02 sandbox executor contract with curated typed `run(...)` surfaces
  - Compact Pydantic-backed recon `parsed_output` dicts for `httpx` JSONL and `subfinder` JSONL
  - Unit coverage for recon parser normalization, malformed/empty output handling, command construction, and parse-failure observability
key_files:
  - src/oxpwn/sandbox/tools/httpx.py
  - src/oxpwn/sandbox/tools/subfinder.py
  - src/oxpwn/sandbox/tools/__init__.py
  - tests/unit/test_httpx_parser.py
  - tests/unit/test_subfinder_parser.py
key_decisions:
  - Feed `httpx` targets over stdin via a shell heredoc because the Kali-packaged sandbox build does not support `-u` and positional targets produced no results.
  - Normalize `subfinder` output by deduping on hostname and merging `input`/`source` attribution into compact sorted lists.
patterns_established:
  - Use internal Pydantic raw-record models plus compact normalized models, then persist `model_dump(...)` dicts into `ToolResult.parsed_output`.
  - Treat empty machine-readable output as a valid zero-result scan, but treat malformed JSONL as a parse failure that logs a per-tool warning and returns `parsed_output=None`.
observability_surfaces:
  - `ToolResult.exit_code`, `ToolResult.stdout`, `ToolResult.stderr`, and `ToolResult.parsed_output`
  - `httpx.jsonl_parse_failed` and `subfinder.jsonl_parse_failed` warnings with truncated stdout/stderr heads
  - Targeted unit tests that patch `logger.warning` and assert the parse-failure diagnostic payload
duration: 46m
verification_result: passed
completed_at: 2026-03-15T03:17:36Z
blocker_discovered: false
---

# T02: Add httpx and subfinder executors with compact recon parsers

**Added real `httpx` and `subfinder` sandbox executors with compact JSONL parsers, graceful parse-failure degradation, and full recon-focused unit coverage.**

## What Happened

I created `src/oxpwn/sandbox/tools/httpx.py` with a Pydantic-backed parser for `httpx -json -silent` output and a typed `HttpxExecutor.run(...)` surface centered on the agent’s likely recon choices: targets, optional ports/path, redirect following, tech detection, timeout, and threads. The normalized output is intentionally compact and stored as `{"count": ..., "services": [...]}` with fields such as URL, status code, title, server, technologies, content length, and response time in milliseconds.

While implementing `httpx`, I verified the real sandbox binary behavior and found that the Kali-packaged `httpx-toolkit` build in `oxpwn-sandbox:dev` does **not** support `-u`, and positional targets produced no results. I therefore built the executor around a `sh -lc` heredoc that feeds targets over stdin, which matches the working runtime path I confirmed inside the sandbox image.

I created `src/oxpwn/sandbox/tools/subfinder.py` with JSONL parsing for `subfinder -oJ -silent -cs`. Its normalized output is stored as `{"count": ..., "hosts": [...]}` and dedupes repeated hosts while merging `input` and `source` attribution into compact sorted lists. That keeps recon observations small enough for the S03 JSON-first agent feedback path while still preserving useful provenance.

Both executors follow the S02 constructor + async `run()` contract, set `result.tool_name`, preserve raw stdout/stderr, and degrade to `parsed_output=None` on malformed JSONL with per-tool structlog warnings that include truncated stdout/stderr heads.

I updated `src/oxpwn/sandbox/tools/__init__.py` to export `HttpxExecutor`, `SubfinderExecutor`, `parse_httpx_jsonl`, and `parse_subfinder_jsonl` alongside the existing `nmap` exports, then replaced the temporary scaffold tests with full parser/executor coverage in `tests/unit/test_httpx_parser.py` and `tests/unit/test_subfinder_parser.py`.

## Verification

Task-level verification passed:
- `pytest tests/unit/test_httpx_parser.py tests/unit/test_subfinder_parser.py -v`
  - `12 passed`
- `python3 -c "from oxpwn.sandbox.tools import HttpxExecutor, SubfinderExecutor; print('imports ok')"`
  - `imports ok`

Observability verification passed directly in unit tests:
- `tests/unit/test_httpx_parser.py::TestHttpxExecutor::test_run_parse_failure_degrades_to_none_and_warns`
- `tests/unit/test_subfinder_parser.py::TestSubfinderExecutor::test_run_parse_failure_degrades_to_none_and_warns`
  - Both patch `logger.warning` and assert the per-tool warning event name plus truncated stdout/stderr diagnostic fields.

Slice-level verification status after T02:
- `docker build -t oxpwn-sandbox:dev docker/ && docker run --rm oxpwn-sandbox:dev sh -lc 'command -v nmap httpx subfinder nuclei ffuf python3'`
  - Build reused cache and completed successfully.
  - The exact shell form still only echoes the first resolved path on this environment, which is the same quirk noted in T01; it did not reveal a new image regression caused by T02.
- `pytest tests/unit/test_httpx_parser.py tests/unit/test_subfinder_parser.py tests/unit/test_nuclei_parser.py tests/unit/test_ffuf_parser.py tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v`
  - `36 passed, 2 failed`
  - The only failures are the expected T03 scaffolds: missing `oxpwn.sandbox.tools.nuclei` and `oxpwn.sandbox.tools.ffuf` modules.
- `pytest tests/integration/test_sandbox_integration.py::test_nmap_executor_real_scan tests/integration/test_tool_suite_integration.py -m integration -v`
  - `3 passed`
  - Existing slice integration substrate remains green after T02.

## Diagnostics

Future agents can inspect or localize failures with:
- `pytest tests/unit/test_httpx_parser.py tests/unit/test_subfinder_parser.py -v`
- `python3 -c "from oxpwn.sandbox.tools import HttpxExecutor, SubfinderExecutor; print('imports ok')"`
- `pytest tests/unit/test_httpx_parser.py -k parse_failure -v`
- `pytest tests/unit/test_subfinder_parser.py -k parse_failure -v`

Runtime inspection surfaces added by this task:
- `ToolResult.exit_code` for the underlying sandbox command status
- `ToolResult.stdout` / `ToolResult.stderr` for raw machine output and CLI diagnostics
- `ToolResult.parsed_output` for normalized recon data
- `httpx.jsonl_parse_failed` / `subfinder.jsonl_parse_failed` warning events with `command`, `stdout_head`, and `stderr_head`

If `httpx` behavior looks wrong in later integration work, check whether the invocation path is still stdin-fed via the shell heredoc. The sandbox build tested here did not support `-u`, so switching back to a direct flag-based target argument is likely to fail silently.

## Deviations

- None.

## Known Issues

- The slice-level unit bundle remains red until T03 creates `src/oxpwn/sandbox/tools/nuclei.py` and `src/oxpwn/sandbox/tools/ffuf.py`; the current failures are exactly the two expected scaffold tests.
- The exact slice-plan image verification command still only prints the first resolved binary path in this shell form, so per-binary visibility still relies on the more explicit loop documented in T01 when deeper diagnostics are needed.
- Real `subfinder` proof is still deferred to later slice integration work and remains internet/provider dependent by design.

## Files Created/Modified

- `src/oxpwn/sandbox/tools/httpx.py` — adds the Pydantic-backed `httpx` JSONL parser and typed sandbox executor with stdin-fed command assembly.
- `src/oxpwn/sandbox/tools/subfinder.py` — adds the Pydantic-backed `subfinder` JSONL parser and typed sandbox executor with host/source dedupe normalization.
- `src/oxpwn/sandbox/tools/__init__.py` — exports the new recon executors and parser helpers.
- `tests/unit/test_httpx_parser.py` — replaces the scaffold with parser normalization, malformed/empty output, command construction, and warning-path coverage.
- `tests/unit/test_subfinder_parser.py` — replaces the scaffold with parser normalization, malformed/empty output, command construction, and warning-path coverage.
- `.gsd/DECISIONS.md` — records the stdin-fed `httpx` invocation choice for the sandbox image.
- `.gsd/milestones/M001/slices/S04/S04-PLAN.md` — marks T02 complete.
- `.gsd/STATE.md` — advances the slice state to T03.
