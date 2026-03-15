---
id: S04
parent: M001
milestone: M001
provides:
  - Full five-tool M001 core suite in the sandbox and agent-visible registry: `nmap`, `httpx`, `subfinder`, `nuclei`, `ffuf`
  - Deterministic in-sandbox HTTP proof assets plus real Docker verification for all newly added tools
  - Compact Pydantic-backed recon/scanning `parsed_output` dicts that fit the existing ReAct observation contract
requires:
  - slice: S02
    provides: Docker sandbox lifecycle, `DockerSandbox.execute()`, and the executor contract established by `NmapExecutor`
  - slice: S03
    provides: ReAct tool registry/prompt surfaces and the JSON-first `ToolResult.parsed_output` feedback path
affects:
  - S05
  - S07
  - S08
key_files:
  - docker/Dockerfile
  - tests/conftest.py
  - src/oxpwn/sandbox/tools/httpx.py
  - src/oxpwn/sandbox/tools/subfinder.py
  - src/oxpwn/sandbox/tools/nuclei.py
  - src/oxpwn/sandbox/tools/ffuf.py
  - src/oxpwn/agent/tools.py
  - src/oxpwn/agent/prompts.py
  - tests/integration/test_tool_suite_integration.py
key_decisions:
  - Serve deterministic tool-suite proof assets from `/tmp/oxpwn-tool-suite` on port `18080`, with full `python3` installed beside `python3-minimal`
  - Feed sandbox `httpx` targets over stdin via `sh -lc` heredoc because the Kali `httpx-toolkit` build does not support `-u`
  - Keep default agent-visible registration stable as `nmap`, `httpx`, `subfinder`, `nuclei`, `ffuf`, and treat `subfinder` as the only internet-gated proof with explicit skip behavior
patterns_established:
  - New sandbox tools follow a typed `run(...)` surface and always return `ToolResult` with compact dict-shaped `parsed_output`
  - Recon/scanning tools are forced into machine-readable `jsonl` or `json` modes, then normalized before their outputs re-enter the agent loop
  - Deterministic proof assets are copied into live sandboxes and served entirely inside the container for repeatable integration verification
observability_surfaces:
  - `ToolResult.exit_code`, `ToolResult.stdout`, `ToolResult.stderr`, and `ToolResult.parsed_output`
  - `ToolRegistry.get_schemas()` and `registry.tool_names`
  - `httpx.jsonl_parse_failed`, `subfinder.jsonl_parse_failed`, `nuclei.jsonl_parse_failed`, and `ffuf.json_parse_failed`
  - `tests/fixtures/tool_suite/` and `tests/integration/test_tool_suite_integration.py`
drill_down_paths:
  - .gsd/milestones/M001/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001/slices/S04/tasks/T02-SUMMARY.md
  - .gsd/milestones/M001/slices/S04/tasks/T03-SUMMARY.md
  - .gsd/milestones/M001/slices/S04/tasks/T04-SUMMARY.md
duration: 3h38m
verification_result: passed
completed_at: 2026-03-15T03:44:18Z
---

# S04: Tool Suite Integration

**Expanded the sandbox and agent from a single-tool `nmap` path to a proven five-tool core suite with compact parsers, deterministic proof fixtures, and real Docker execution for `httpx`, `subfinder`, `nuclei`, and `ffuf`.**

## What Happened

This slice finished the M001 tool-suite substrate that S03 was still missing.

First, the sandbox image and test harness were made deterministic for HTTP-driven tooling. The Kali image now contains `nmap`, `httpx-toolkit` (symlinked to `httpx`), `subfinder`, `nuclei`, `ffuf`, `python3-minimal`, and full `python3`. In-repo proof assets were added under `tests/fixtures/tool_suite/`: a tiny site root, a uniquely identifiable `/admin/` page, a tiny ffuf wordlist, and a custom nuclei template. The pytest harness can now copy those assets into a live container under `/tmp/oxpwn-tool-suite`, start `python3 -m http.server` on port `18080`, and tear it down with observable log/PID metadata.

Next, the four missing executors were implemented on top of the S02 `NmapExecutor` contract. `HttpxExecutor` and `SubfinderExecutor` provide compact recon outputs from JSONL. `NucleiExecutor` and `FfufExecutor` provide compact scanning findings from low-noise machine-readable modes. All four preserve raw stdout/stderr for auditability, dump normalized Pydantic-backed data into `ToolResult.parsed_output`, and degrade to `parsed_output=None` with per-tool warning events when parsing fails instead of crashing the agent loop.

The agent-facing wiring was then completed. `register_default_tools(...)` now exposes the full suite in a stable order — `nmap`, `httpx`, `subfinder`, `nuclei`, `ffuf` — with curated typed schemas rather than raw flag passthrough. Recon guidance now explicitly points the ReAct loop toward `subfinder`/`httpx`/`nmap`, while Scanning guidance points it toward `nuclei`/`ffuf`/targeted `nmap` follow-up. Unit coverage was expanded to lock down the schema inventory, stable ordering, prompt hints, and the existing JSON-first parsed-output handoff back into the LLM.

Finally, the slice was closed with real Docker proofs. The deterministic local fixture proves `httpx`, `nuclei`, and `ffuf` end to end inside the sandbox. `subfinder` is proven against a public domain with an outbound-connectivity preflight so the test can skip cleanly only when network access is unavailable. Together with the existing real `nmap` proof, S04 now provides runtime evidence for the complete five-tool M001 suite.

## Verification

Passed all slice-level verification defined in the plan:

- `docker build -t oxpwn-sandbox:dev docker/ && docker run --rm oxpwn-sandbox:dev sh -lc 'command -v nmap httpx subfinder nuclei ffuf python3'`
  - Image built successfully and resolved sandbox binaries.
- `pytest tests/unit/test_httpx_parser.py tests/unit/test_subfinder_parser.py tests/unit/test_nuclei_parser.py tests/unit/test_ffuf_parser.py tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v`
  - Result: `50 passed`
- `pytest tests/integration/test_sandbox_integration.py::test_nmap_executor_real_scan tests/integration/test_tool_suite_integration.py -m integration -v`
  - Result: `7 passed`

Confirmed observability/diagnostic surfaces from the slice plan:

- `python3 - <<'PY' ... ToolRegistry()/register_default_tools()/get_schemas() ... PY`
  - Confirmed `registry.tool_names == ['nmap', 'httpx', 'subfinder', 'nuclei', 'ffuf']`
- `find tests/fixtures/tool_suite -type f | sort`
  - Confirmed deterministic fixture inventory exists in-repo
- `pytest ...test_run_parse_failure_degrades_to_none_and_warns ... -v`
  - Result: `4 passed`, confirming the parse-failure warning paths for `httpx`, `subfinder`, `nuclei`, and `ffuf`

## Requirements Advanced

- R001 — The ReAct agent now has real access to the full five-tool core suite for Recon and Scanning, with structured outputs it can consume through the existing JSON-first observation path.

## Requirements Validated

- R002 — Real Docker verification now covers the M001 core tool suite (`nmap`, `httpx`, `subfinder`, `nuclei`, `ffuf`) inside the custom Kali sandbox image, which is sufficient evidence to mark isolated sandbox execution validated for the current milestone scope.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- Installed full `python3` alongside `python3-minimal` because Kali's minimal package could not run the `http.server`/`urllib` proof path required by the deterministic HTTP fixture.

## Known Limitations

- `subfinder` remains the one internet-gated S04 proof; when outbound passive-source access is unavailable, the integration test may skip instead of producing a local deterministic result.
- This slice proves only the five-tool M001 core suite, not the later 25+ tool expansion planned for M004/S07.
- Streaming CLI output, first-run model setup, CVE enrichment, and full end-to-end scan acceptance remain in S05–S08.

## Follow-ups

- S05 should render the richer five-tool phase guidance and parsed tool summaries through the existing event stream without overwhelming terminal output.
- S07 should consume the normalized nuclei/ffuf/httpx/subfinder findings cleanly when enriching findings with CVE/NVD metadata.

## Files Created/Modified

- `docker/Dockerfile` — installs the full five-tool runtime and the Python HTTP fixture runtime, including the stable `httpx` symlink.
- `tests/conftest.py` — adds deterministic tool-suite asset seeding and in-sandbox HTTP fixture helpers.
- `tests/fixtures/tool_suite/site/index.html` — deterministic site root for sandbox-local HTTP proofs.
- `tests/fixtures/tool_suite/site/admin/index.html` — deterministic `/admin/` page used by `httpx`, `nuclei`, and `ffuf` proofs.
- `tests/fixtures/tool_suite/ffuf-wordlist.txt` — tiny deterministic wordlist for path fuzzing proofs.
- `tests/fixtures/tool_suite/nuclei/admin-panel.yaml` — custom nuclei template that matches the fixture admin page.
- `src/oxpwn/sandbox/tools/httpx.py` — adds the `httpx` executor and JSONL parser.
- `src/oxpwn/sandbox/tools/subfinder.py` — adds the `subfinder` executor and JSONL parser.
- `src/oxpwn/sandbox/tools/nuclei.py` — adds the `nuclei` executor and compact JSONL finding parser.
- `src/oxpwn/sandbox/tools/ffuf.py` — adds the `ffuf` executor, stdout-JSON parser, ANSI stripping, and base64 input decoding.
- `src/oxpwn/sandbox/tools/__init__.py` — exports the four new executors and parser helpers.
- `src/oxpwn/agent/tools.py` — registers the five-tool suite with curated typed schemas.
- `src/oxpwn/agent/prompts.py` — updates Recon and Scanning guidance to point the agent toward the appropriate tool subset.
- `tests/unit/test_httpx_parser.py` — covers parser normalization, command construction, and parse-failure degradation for `httpx`.
- `tests/unit/test_subfinder_parser.py` — covers parser normalization, command construction, and parse-failure degradation for `subfinder`.
- `tests/unit/test_nuclei_parser.py` — covers parser normalization, command construction, and parse-failure degradation for `nuclei`.
- `tests/unit/test_ffuf_parser.py` — covers parser normalization, command construction, and parse-failure degradation for `ffuf`.
- `tests/unit/test_tool_registry.py` — locks down the full default tool inventory, order, and schema surfaces.
- `tests/unit/test_react_agent.py` — verifies prompt hints and parsed-output dispatch through the real agent call path.
- `tests/integration/test_tool_suite_integration.py` — proves fixture seeding plus real sandbox execution for `httpx`, `subfinder`, `nuclei`, and `ffuf`.

## Forward Intelligence

### What the next slice should know
- The default tool inventory and order are now a contract: `nmap`, `httpx`, `subfinder`, `nuclei`, `ffuf`.
- The agent now receives compact, stable top-level parsed shapes: `{"count": ..., "services": [...]}` for `httpx`, `{"count": ..., "hosts": [...]}` for `subfinder`, and `{"count": ..., "findings": [...]}` for `nuclei`/`ffuf`.
- The deterministic fixture stack under `tests/fixtures/tool_suite/` is the fastest trustworthy way to debug any future regression in HTTP-oriented tool execution.

### What's fragile
- `subfinder` external runtime dependency — it is the only slice proof that can legitimately skip when outbound passive-source access is blocked.
- Kali `httpx-toolkit` packaging — reverting to `-u` or positional-target invocation is likely to silently break sandbox scans.
- `ffuf` machine-readable stdout — it still emits ANSI noise and base64-encoded fuzz inputs, so the parser contract should not be simplified casually.

### Authoritative diagnostics
- `pytest tests/integration/test_sandbox_integration.py::test_nmap_executor_real_scan tests/integration/test_tool_suite_integration.py -m integration -v` — authoritative runtime proof for the sandboxed five-tool path.
- `pytest tests/unit/test_httpx_parser.py tests/unit/test_subfinder_parser.py tests/unit/test_nuclei_parser.py tests/unit/test_ffuf_parser.py -v` — authoritative parser and command-assembly coverage.
- `python3 - <<'PY' ... register_default_tools(...) ... PY` — quickest check for schema/order drift before debugging deeper agent behavior.

### What assumptions changed
- `python3-minimal` would be enough for the HTTP fixture runtime — actually false on this Kali base; full `python3` is required.
- `httpx` would accept direct target flags inside the sandbox image — actually false for this packaged build; stdin-fed execution is the reliable path.
- All five tools could be proven against deterministic local targets — actually false because `subfinder` inherently depends on public passive sources.
