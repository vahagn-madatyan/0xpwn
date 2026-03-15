---
estimated_steps: 4
estimated_files: 5
---

# T02: Add httpx and subfinder executors with compact recon parsers

**Slice:** S04 — Tool Suite Integration
**Milestone:** M001

## Description

Implement the Recon-side tools first because they naturally extend S03’s existing recon/scanning loop and share the same JSONL-first parsing strategy. This task should make `httpx` and `subfinder` feel as boring and reliable as `nmap`: typed executor contract, compact `parsed_output`, raw stdout preserved, and unit tests covering the tricky edge cases.

## Steps

1. Create `src/oxpwn/sandbox/tools/httpx.py` with Pydantic-backed normalization for `httpx -json -silent` output and an executor class that follows the S02 `NmapExecutor` contract while exposing a curated, typed `run(...)` surface instead of raw flags.
2. Create `src/oxpwn/sandbox/tools/subfinder.py` with JSONL parsing for `subfinder -oJ`, compact host/dedupe normalization, and the same graceful parse-failure behavior (`parsed_output=None`, raw stdout/stderr preserved, warning logged).
3. Update `src/oxpwn/sandbox/tools/__init__.py` exports so the new executors/parsers are available to later registry wiring without changing the public contract established in S02.
4. Add `tests/unit/test_httpx_parser.py` and `tests/unit/test_subfinder_parser.py` covering realistic JSONL fixtures, malformed/empty output, executor command construction, and parse-failure degradation.

## Must-Haves

- [ ] `HttpxExecutor` and `SubfinderExecutor` follow the constructor + `async run()` contract from S02
- [ ] `parsed_output` is compact, normalized, and stored as a dict produced from internal Pydantic models
- [ ] Empty or malformed JSONL does not crash the executor path
- [ ] Unit tests assert both parser behavior and sandbox command construction

## Verification

- `pytest tests/unit/test_httpx_parser.py tests/unit/test_subfinder_parser.py -v` — all pass
- `python3 -c "from oxpwn.sandbox.tools import HttpxExecutor, SubfinderExecutor; print('imports ok')"` — no import errors

## Observability Impact

- Signals added/changed: per-tool parse-failure warnings should include truncated stdout/stderr context; executor results expose normalized recon data via `ToolResult.parsed_output`
- How a future agent inspects this: inspect `ToolResult.exit_code`, `stdout`, `stderr`, and `parsed_output`; run the targeted unit tests to localize parser vs command-construction failures
- Failure state exposed: malformed JSONL or unexpected output shape becomes visible as a non-crashing parse warning with `parsed_output=None`

## Inputs

- `src/oxpwn/sandbox/tools/nmap.py` — reference executor/parser pattern from S02
- `src/oxpwn/core/models.py` — `ToolResult.parsed_output` dict contract that must remain stable
- `docker/Dockerfile` — T01-provided image contract ensuring the binaries exist in the sandbox
- S04 research: prefer machine-readable output, avoid raw flag passthrough, and keep observations compact for the S03 4000-character feedback path

## Expected Output

- `src/oxpwn/sandbox/tools/httpx.py` — `httpx` parser + executor
- `src/oxpwn/sandbox/tools/subfinder.py` — `subfinder` parser + executor
- `src/oxpwn/sandbox/tools/__init__.py` — exports for the new recon tools
- `tests/unit/test_httpx_parser.py` — parser/executor unit coverage for `httpx`
- `tests/unit/test_subfinder_parser.py` — parser/executor unit coverage for `subfinder`
