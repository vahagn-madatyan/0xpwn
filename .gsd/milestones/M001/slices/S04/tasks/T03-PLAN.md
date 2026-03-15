---
estimated_steps: 4
estimated_files: 5
---

# T03: Add nuclei and ffuf executors with normalized scanning findings

**Slice:** S04 — Tool Suite Integration
**Milestone:** M001

## Description

Implement the Scanning-side tools with extra emphasis on output control. `nuclei` and `ffuf` are the most likely to flood the agent with noisy data, so this task exists to force machine-readable modes, strip the results down to agent-useful findings, and keep the S03 observation budget intact before these tools are exposed to the ReAct loop.

## Steps

1. Create `src/oxpwn/sandbox/tools/nuclei.py` with compact JSONL parsing and an executor that uses quiet machine-readable flags to avoid request/response and template bloat while still preserving raw stdout/stderr for audit.
2. Create `src/oxpwn/sandbox/tools/ffuf.py` with JSON parsing, base64 fuzz-input decoding, deterministic wordlist handling, and the same graceful parse-failure behavior used by the other executors.
3. Update `src/oxpwn/sandbox/tools/__init__.py` exports so the scanning executors are available to the registry layer without changing the established sandbox contract.
4. Add `tests/unit/test_nuclei_parser.py` and `tests/unit/test_ffuf_parser.py` covering realistic outputs, malformed/empty output, compact normalization, and executor command assembly against the deterministic fixture assets from T01.

## Must-Haves

- [ ] `NucleiExecutor` and `FfufExecutor` use machine-readable output only and keep `parsed_output` compact
- [ ] `ffuf` normalization decodes base64 fuzz inputs clearly enough for agent reasoning and later reporting
- [ ] Parse failures degrade to `parsed_output=None` instead of breaking the tool execution path
- [ ] Unit tests prove the parsers stay within the intended compact finding shape

## Verification

- `pytest tests/unit/test_nuclei_parser.py tests/unit/test_ffuf_parser.py -v` — all pass
- `python3 -c "from oxpwn.sandbox.tools import NucleiExecutor, FfufExecutor; print('imports ok')"` — no import errors

## Observability Impact

- Signals added/changed: per-tool parse-failure warnings for nuclei/ffuf should carry enough stdout/stderr context to diagnose output drift; normalized findings stay inspectable in `ToolResult.parsed_output`
- How a future agent inspects this: inspect the targeted parser tests and the resulting `ToolResult` models to distinguish noisy CLI output from normalization bugs
- Failure state exposed: oversized/unexpected tool output becomes a contained parse failure rather than a broken agent observation path

## Inputs

- `src/oxpwn/sandbox/tools/nmap.py` — executor/parser contract to replicate
- `tests/fixtures/tool_suite/ffuf-wordlist.txt` — deterministic wordlist from T01
- `tests/fixtures/tool_suite/nuclei/admin-panel.yaml` — deterministic nuclei template from T01
- S04 research: `nuclei` output must be shrunk before it reaches the agent, and `ffuf` JSON `input` values are base64 encoded in real output

## Expected Output

- `src/oxpwn/sandbox/tools/nuclei.py` — `nuclei` parser + executor
- `src/oxpwn/sandbox/tools/ffuf.py` — `ffuf` parser + executor
- `src/oxpwn/sandbox/tools/__init__.py` — exports for the full sandbox tool suite
- `tests/unit/test_nuclei_parser.py` — parser/executor unit coverage for `nuclei`
- `tests/unit/test_ffuf_parser.py` — parser/executor unit coverage for `ffuf`
