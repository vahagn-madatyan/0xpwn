# S04: Tool Suite Integration

**Goal:** Agent-visible support for the full 5-tool core suite by adding `httpx`, `subfinder`, `nuclei`, and `ffuf` executors on top of the existing `nmap` pattern, with compact structured parsers and real sandbox proof targets.
**Demo:** Real-Docker verification shows `nmap`, `httpx`, `subfinder`, `nuclei`, and `ffuf` all execute inside the sandbox and return structured `parsed_output`; the default tool registry and prompts expose the full suite to the ReAct agent.

This slice is grouped by shared risk, not one task per file: T01 removes the biggest verification blocker by making the sandbox image and HTTP proof target deterministic; T02 and T03 then add the new executors along the natural Recon vs Scanning split; T04 closes the loop by wiring the suite into the agent-facing registry/prompt surfaces and proving the real runtime path. That order keeps parser work from stalling on environment issues and makes the final integration failure surface much narrower.

## Requirement Coverage

- R001 — Autonomous 5-phase pentesting pipeline (supporting): this slice makes the S03 agent materially capable of Recon and Scanning by exposing the full 5-tool core suite with structured outputs the loop can consume

## Must-Haves

- Sandbox image installs `httpx-toolkit`, `subfinder`, `nuclei`, `ffuf`, and a minimal HTTP fixture runtime, with `httpx` available as the in-container command name
- Deterministic in-repo proof assets exist for HTTP-driven tools: tiny site fixture, tiny ffuf wordlist, and a custom nuclei template
- `httpx`, `subfinder`, `nuclei`, and `ffuf` each follow the S02 executor contract: constructor takes `DockerSandbox`, `async run(...)` returns `ToolResult`
- Each new executor parses machine-readable output into compact Pydantic-backed data that is dumped to `ToolResult.parsed_output` as a dict, while preserving raw stdout/stderr for audit/debug
- Parse failures degrade gracefully to `parsed_output=None` with per-tool diagnostics instead of crashing the agent loop
- Default tool registration exposes all 5 core tools with curated typed schemas rather than raw flag passthrough
- Phase guidance steers Recon toward `subfinder`/`httpx`/`nmap` and Scanning toward `nuclei`/`ffuf`/`nmap`
- Unit tests cover parser normalization, malformed/empty output handling, and executor command construction for all 4 new tools
- Integration proof exercises real sandbox execution for the 4 new tools plus the existing real `nmap` proof, giving slice-level evidence for the full 5-tool suite

## Proof Level

- This slice proves: integration
- Real runtime required: yes
- Human/UAT required: no

## Verification

- `docker build -t oxpwn-sandbox:dev docker/ && docker run --rm oxpwn-sandbox:dev sh -lc 'command -v nmap httpx subfinder nuclei ffuf python3'` — image contains the full tool suite and the HTTP-fixture runtime
- `pytest tests/unit/test_httpx_parser.py tests/unit/test_subfinder_parser.py tests/unit/test_nuclei_parser.py tests/unit/test_ffuf_parser.py tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v` — parser, executor, registry, and prompt-facing unit coverage passes
- `pytest tests/integration/test_sandbox_integration.py::test_nmap_executor_real_scan tests/integration/test_tool_suite_integration.py -m integration -v` — real Docker proof covers the existing `nmap` contract plus the four new tools against real targets

## Observability / Diagnostics

- Runtime signals: existing `sandbox.*` structlog events plus per-tool parse-failure warnings (`httpx.*`, `subfinder.*`, `nuclei.*`, `ffuf.*`) when JSON/JSONL normalization fails
- Inspection surfaces: `ToolResult.exit_code`, `ToolResult.stdout`, `ToolResult.stderr`, and `ToolResult.parsed_output`; `ToolRegistry.get_schemas()` for agent-visible tool exposure; deterministic fixture paths under `tests/fixtures/tool_suite/`
- Failure visibility: missing binary errors from the image check, parse warnings with truncated stdout/stderr heads, fixture-server startup failures, and explicit skip reasons when subfinder cannot be proven due to missing outbound connectivity
- Redaction constraints: never log provider credentials if subfinder is configured with API-backed providers; keep outputs limited to public target data and local test fixtures

## Integration Closure

- Upstream surfaces consumed: `docker/Dockerfile`, `oxpwn.sandbox.docker.DockerSandbox.execute()`, `oxpwn.sandbox.tools.nmap.NmapExecutor`, `ToolResult.parsed_output` dict contract, `src/oxpwn/agent/tools.py`, `src/oxpwn/agent/prompts.py`, and the existing real `nmap` integration test from S02
- New wiring introduced: sandbox image now packages the full core suite; test fixtures seed a deterministic HTTP target/wordlist/template into the sandbox; default tool registration and prompt guidance expose all 5 tools to the ReAct agent
- What remains before the milestone is truly usable end-to-end: S05 CLI streaming, S06 first-run config, S07 CVE enrichment, and S08 full scan validation

## Tasks

- [x] **T01: Expand the sandbox image and deterministic HTTP proof fixtures** `est:35m`
  - Why: Every new tool proof depends on the image containing the right binaries and on having a stable HTTP target inside the sandbox; solving that first removes the main source of flaky downstream work.
  - Files: `docker/Dockerfile`, `tests/conftest.py`, `tests/fixtures/tool_suite/site/index.html`, `tests/fixtures/tool_suite/site/admin/index.html`, `tests/fixtures/tool_suite/ffuf-wordlist.txt`, `tests/fixtures/tool_suite/nuclei/admin-panel.yaml`
  - Do: Update the Kali image to install `httpx-toolkit`, `subfinder`, `nuclei`, `ffuf`, and `python3-minimal`, then symlink `httpx-toolkit` to `httpx`. Add a tiny deterministic site fixture with a uniquely identifiable `/admin` page, a tiny ffuf wordlist, and a custom nuclei template matched to that fixture. Extend test support so integration tests can copy those assets into the sandbox and launch `python3 -m http.server` via `sh -lc` on a known port with cleanup.
  - Verify: `docker build -t oxpwn-sandbox:dev docker/ && docker run --rm oxpwn-sandbox:dev sh -lc 'command -v nmap httpx subfinder nuclei ffuf python3' && docker run --rm -v "$PWD/tests/fixtures/tool_suite/site:/srv/site:ro" oxpwn-sandbox:dev sh -lc 'cd /srv/site && python3 -m http.server 8000 >/tmp/http.log 2>&1 & pid=$!; python3 - <<"PY"
import urllib.request
body = urllib.request.urlopen("http://127.0.0.1:8000/admin/").read().decode()
assert "admin" in body.lower()
PY
kill $pid'`
  - Done when: The dev sandbox image exposes all required binaries and the test harness can stand up a deterministic HTTP target entirely inside the container.
- [x] **T02: Add httpx and subfinder executors with compact recon parsers** `est:40m`
  - Why: Recon is the first place the agent benefits from the wider suite, and these two tools share the same JSONL-first parsing approach with small, agent-usable summaries.
  - Files: `src/oxpwn/sandbox/tools/httpx.py`, `src/oxpwn/sandbox/tools/subfinder.py`, `src/oxpwn/sandbox/tools/__init__.py`, `tests/unit/test_httpx_parser.py`, `tests/unit/test_subfinder_parser.py`
  - Do: Implement Pydantic-backed parser/executor modules for `httpx` and `subfinder` using machine-readable modes only. Keep the run interfaces curated and typed around the agent’s likely choices instead of exposing free-form flags. Normalize output to compact dicts, preserve raw stdout/stderr, and degrade to `parsed_output=None` on parse failure with diagnostics. Add unit tests for happy-path parsing, empty/malformed output, dedupe/normalization, and executor command construction.
  - Verify: `pytest tests/unit/test_httpx_parser.py tests/unit/test_subfinder_parser.py -v`
  - Done when: Both recon executors return stable structured `parsed_output` dicts from JSONL and their parser/executor edge cases are covered by unit tests.
- [x] **T03: Add nuclei and ffuf executors with normalized scanning findings** `est:45m`
  - Why: These scanning tools complete the core suite and are the highest risk for oversized or noisy output, so they need dedicated normalization before they hit the agent loop.
  - Files: `src/oxpwn/sandbox/tools/nuclei.py`, `src/oxpwn/sandbox/tools/ffuf.py`, `src/oxpwn/sandbox/tools/__init__.py`, `tests/unit/test_nuclei_parser.py`, `tests/unit/test_ffuf_parser.py`
  - Do: Implement `nuclei` and `ffuf` executor/parser modules that force machine-readable output and strip observations down to agent-useful findings. For `nuclei`, use quiet JSONL flags that avoid template/request-response bloat; for `ffuf`, parse JSON output, decode base64 fuzz inputs, and require the deterministic wordlist path used by tests. Preserve the S02 graceful-degradation behavior and add unit tests for compact normalization, malformed/empty output, and command assembly.
  - Verify: `pytest tests/unit/test_nuclei_parser.py tests/unit/test_ffuf_parser.py -v`
  - Done when: Both scanning executors produce compact structured findings that fit the S03 observation contract and the parsers are resilient to real-world output edge cases.
- [x] **T04: Register the full suite and prove real sandbox execution** `est:45m`
  - Why: The slice is only done once the new executors are agent-visible and the real Docker proof shows the suite works as a composed system, not just as isolated parser modules.
  - Files: `src/oxpwn/agent/tools.py`, `src/oxpwn/agent/prompts.py`, `tests/unit/test_tool_registry.py`, `tests/unit/test_react_agent.py`, `tests/integration/test_tool_suite_integration.py`
  - Do: Extend default tool registration to include `httpx`, `subfinder`, `nuclei`, and `ffuf` with curated typed schemas and executor factories. Update phase guidance so Recon explicitly suggests `subfinder`/`httpx`/`nmap` and Scanning suggests `nuclei`/`ffuf`/`nmap`. Expand unit coverage to assert the default registry exposes the full suite and the agent-facing prompt/dispatch path remains compatible with the existing `ToolResult.parsed_output` contract. Add a real-Docker integration file that proves `httpx`, `subfinder`, `nuclei`, and `ffuf` against the deterministic target strategy, while the slice verification reuses S02’s real `nmap` proof to cover all 5 tools.
  - Verify: `pytest tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v && pytest tests/integration/test_sandbox_integration.py::test_nmap_executor_real_scan tests/integration/test_tool_suite_integration.py -m integration -v`
  - Done when: The default registry and prompts expose all 5 tools to the agent, and real integration proof exists for the four new tools plus the existing real `nmap` proof.

## Files Likely Touched

- `docker/Dockerfile`
- `src/oxpwn/sandbox/tools/__init__.py`
- `src/oxpwn/sandbox/tools/httpx.py`
- `src/oxpwn/sandbox/tools/subfinder.py`
- `src/oxpwn/sandbox/tools/nuclei.py`
- `src/oxpwn/sandbox/tools/ffuf.py`
- `src/oxpwn/agent/tools.py`
- `src/oxpwn/agent/prompts.py`
- `tests/conftest.py`
- `tests/unit/test_httpx_parser.py`
- `tests/unit/test_subfinder_parser.py`
- `tests/unit/test_nuclei_parser.py`
- `tests/unit/test_ffuf_parser.py`
- `tests/unit/test_tool_registry.py`
- `tests/unit/test_react_agent.py`
- `tests/integration/test_tool_suite_integration.py`
- `tests/fixtures/tool_suite/site/index.html`
- `tests/fixtures/tool_suite/site/admin/index.html`
- `tests/fixtures/tool_suite/ffuf-wordlist.txt`
- `tests/fixtures/tool_suite/nuclei/admin-panel.yaml`
