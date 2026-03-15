---
id: T03
parent: S04
milestone: M001
provides:
  - `NucleiExecutor` with compact JSONL parsing, quiet machine-readable command assembly, and graceful parse-failure degradation
  - `FfufExecutor` with stdout-JSON parsing, base64 fuzz-input decoding, ANSI-noise stripping, and a deterministic in-sandbox wordlist default
  - Unit coverage for scanning parser normalization, malformed/empty output handling, command construction, and parse-failure observability
key_files:
  - src/oxpwn/sandbox/tools/nuclei.py
  - src/oxpwn/sandbox/tools/ffuf.py
  - src/oxpwn/sandbox/tools/__init__.py
  - tests/unit/test_nuclei_parser.py
  - tests/unit/test_ffuf_parser.py
key_decisions:
  - Run `nuclei` with `-jsonl -silent -nc -duc -omit-raw -omit-template` so findings stay machine-readable without raw request/response or template bloat.
  - Run `ffuf` in stdout `-json` mode, strip terminal control sequences before parsing, and default to `/tmp/oxpwn-tool-suite/ffuf-wordlist.txt` so the executor stays deterministic in the sandbox proof path.
patterns_established:
  - Normalize scanning tools into a shared `{"count": ..., "findings": [...]}` shape using internal Pydantic raw-record models plus compact finding models dumped into `ToolResult.parsed_output`.
  - Treat empty machine-readable output as a valid zero-result scan, but degrade any JSON/JSONL/schema drift to `parsed_output=None` with per-tool warning events and truncated stdout/stderr heads.
  - Decode ffuf’s base64-encoded fuzz inputs into agent-usable strings while intentionally dropping `FFUFHASH` from normalized findings to keep observations compact.
observability_surfaces:
  - `ToolResult.exit_code`, `ToolResult.stdout`, `ToolResult.stderr`, and `ToolResult.parsed_output`
  - `nuclei.jsonl_parse_failed` and `ffuf.json_parse_failed` warnings with truncated stdout/stderr heads
  - Targeted unit tests that patch `logger.warning` and assert the parse-failure diagnostic payload
  - A real Docker runtime spot-check proving both executors return structured `parsed_output` against the deterministic HTTP fixture
duration: 52m
verification_result: passed
completed_at: 2026-03-15T03:28:25Z
blocker_discovered: false
---

# T03: Add nuclei and ffuf executors with normalized scanning findings

**Added real `nuclei` and `ffuf` sandbox executors with compact scanning findings, base64-aware ffuf normalization, graceful parse-failure degradation, and verified runtime behavior against the deterministic sandbox fixture.**

## What Happened

I created `src/oxpwn/sandbox/tools/nuclei.py` with a Pydantic-backed parser for `nuclei` JSONL output and a typed `NucleiExecutor.run(...)` surface centered on the agent’s likely scanning choices: one or more targets, one or more template paths, optional redirect following, timeout, retries, and rate limiting. The executor forces machine-readable low-noise flags (`-jsonl -silent -nc -duc -omit-raw -omit-template`) so nuclei findings do not balloon with raw request/response pairs or encoded template payloads before they reach the S03 observation path. The normalized output is stored as `{"count": ..., "findings": [...]}` with compact fields such as template ID, finding name, severity, matched URL, host/IP, scheme, port, and description.

I created `src/oxpwn/sandbox/tools/ffuf.py` with a compact parser for ffuf’s stdout `-json` mode and a typed `FfufExecutor.run(...)` surface built around deterministic wordlist-driven path fuzzing. The executor defaults `wordlist_path` to `/tmp/oxpwn-tool-suite/ffuf-wordlist.txt`, requires the target URL to contain the `FUZZ` keyword, and runs ffuf with `-json -s -noninteractive` so stdout stays machine-readable. Because the real ffuf stdout format still includes terminal clear-line control sequences and base64-encodes `input` values, the parser strips ANSI noise, decodes base64 fuzz inputs into agent-usable strings, drops `FFUFHASH`, converts durations from nanoseconds to milliseconds, and normalizes findings into the same compact `{"count": ..., "findings": [...]}` top-level shape used for nuclei.

Both executors follow the established S02 sandbox contract: constructor takes `DockerSandbox`, async `run()` returns `ToolResult`, `tool_name` is rewritten to the concrete tool, raw stdout/stderr are preserved for audit/debug, and parse failures degrade to `parsed_output=None` with per-tool structlog warnings carrying the command and truncated stdout/stderr heads.

I updated `src/oxpwn/sandbox/tools/__init__.py` to export `NucleiExecutor`, `FfufExecutor`, `parse_nuclei_jsonl`, and `parse_ffuf_json`, then replaced the T03 scaffolds with full parser/executor coverage in `tests/unit/test_nuclei_parser.py` and `tests/unit/test_ffuf_parser.py`.

## Verification

Task-level verification passed:
- `pytest tests/unit/test_nuclei_parser.py tests/unit/test_ffuf_parser.py -v`
  - `12 passed`
- `python3 -c "from oxpwn.sandbox.tools import NucleiExecutor, FfufExecutor; print('imports ok')"`
  - `imports ok`

Observability verification passed directly in unit tests:
- `tests/unit/test_nuclei_parser.py::TestNucleiExecutor::test_run_parse_failure_degrades_to_none_and_warns`
- `tests/unit/test_ffuf_parser.py::TestFfufExecutor::test_run_parse_failure_degrades_to_none_and_warns`
  - Both patch `logger.warning` and assert the per-tool warning event name plus truncated stdout/stderr diagnostic fields.

Real runtime spot-check passed against the deterministic Docker fixture:
- `python3 - <<'PY' ...` (creates `DockerSandbox`, copies `tests/fixtures/tool_suite/`, starts the in-sandbox HTTP fixture, runs `NucleiExecutor` and `FfufExecutor`, prints `parsed_output`)
  - `NucleiExecutor` returned `exit_code=0` with `{"count": 1, "findings": [...]}` for the deterministic admin template.
  - `FfufExecutor` returned `exit_code=0` with decoded fuzz inputs like `{"FUZZ": "admin"}` / `{"FUZZ": "login"}` / `{"FUZZ": "health"}`.

Slice-level verification status after T03:
- `docker build -t oxpwn-sandbox:dev docker/ && docker run --rm oxpwn-sandbox:dev sh -lc 'for bin in nmap httpx subfinder nuclei ffuf python3; do command -v "$bin"; done'`
  - Passed; all six binaries resolved inside the sandbox image.
- `pytest tests/unit/test_httpx_parser.py tests/unit/test_subfinder_parser.py tests/unit/test_nuclei_parser.py tests/unit/test_ffuf_parser.py tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v`
  - `48 passed`
- `pytest tests/integration/test_sandbox_integration.py::test_nmap_executor_real_scan tests/integration/test_tool_suite_integration.py -m integration -v`
  - `3 passed`
  - Current integration coverage remains the existing nmap + fixture substrate proof; T04 still needs to add the real tool-suite execution cases for `httpx`, `subfinder`, `nuclei`, and `ffuf`.

## Diagnostics

Future agents can inspect or localize failures with:
- `pytest tests/unit/test_nuclei_parser.py tests/unit/test_ffuf_parser.py -v`
- `python3 -c "from oxpwn.sandbox.tools import NucleiExecutor, FfufExecutor; print('imports ok')"`
- `pytest tests/unit/test_nuclei_parser.py -k parse_failure -v`
- `pytest tests/unit/test_ffuf_parser.py -k parse_failure -v`

Runtime inspection surfaces added by this task:
- `ToolResult.exit_code` for the underlying sandbox command status
- `ToolResult.stdout` / `ToolResult.stderr` for raw machine output and CLI diagnostics
- `ToolResult.parsed_output` for normalized scanning findings
- `nuclei.jsonl_parse_failed` / `ffuf.json_parse_failed` warning events with `command`, `stdout_head`, and `stderr_head`

If ffuf parsing drifts later, first check whether stdout still comes from `-json` mode and whether control-sequence stripping still matches the emitted terminal noise. If nuclei output becomes too large later, confirm the executor still uses `-omit-raw -omit-template` before changing the parser.

## Deviations

- None.

## Known Issues

- Full real integration proof for the new executors still belongs to T04; the current slice integration file only proves the deterministic fixture substrate and the pre-existing real `nmap` path.
- `ffuf`’s stdout machine-readable mode still emits terminal clear-line control sequences in practice, so later work should preserve the parser’s ANSI stripping unless the command mode changes.

## Files Created/Modified

- `src/oxpwn/sandbox/tools/nuclei.py` — adds the Pydantic-backed nuclei JSONL parser and typed sandbox executor with low-noise machine-readable flags.
- `src/oxpwn/sandbox/tools/ffuf.py` — adds the ffuf stdout-JSON parser, base64 input decoding, ANSI stripping, deterministic wordlist default, and typed sandbox executor.
- `src/oxpwn/sandbox/tools/__init__.py` — exports the new scanning executors and parser helpers.
- `tests/unit/test_nuclei_parser.py` — adds nuclei parser normalization, malformed/empty output, command construction, and warning-path coverage.
- `tests/unit/test_ffuf_parser.py` — adds ffuf parser normalization, base64 decoding, malformed/empty output, command construction, and warning-path coverage.
- `.gsd/DECISIONS.md` — records the low-noise nuclei/ffuf output-control contract for downstream T04 work.
- `.gsd/milestones/M001/slices/S04/S04-PLAN.md` — marks T03 complete.
- `.gsd/STATE.md` — advances the slice state to T04.
