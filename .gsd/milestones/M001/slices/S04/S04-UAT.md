# S04: Tool Suite Integration — UAT

**Milestone:** M001
**Written:** 2026-03-14 20:44:18 PDT

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S04 is a non-UI infrastructure slice whose acceptance is defined by deterministic unit coverage plus real Docker execution against controlled targets.

## Preconditions

- Docker daemon/Desktop is running locally.
- Project dependencies are installed so `pytest` and the `oxpwn` package import cleanly.
- For the `subfinder` happy-path proof, the sandbox must have outbound internet access to public passive sources. If not, a clean skip is acceptable for that one test.

## Smoke Test

Run:

- `pytest tests/integration/test_sandbox_integration.py::test_nmap_executor_real_scan tests/integration/test_tool_suite_integration.py -m integration -v`

Expected:

- `nmap`, `httpx`, `nuclei`, and `ffuf` pass against real Docker targets.
- `subfinder` either passes against a public domain or skips with an explicit outbound-connectivity reason.

## Test Cases

### 1. Sandbox image exposes the full five-tool suite

1. Run `docker build -t oxpwn-sandbox:dev docker/`.
2. Run `docker run --rm oxpwn-sandbox:dev sh -lc 'command -v nmap httpx subfinder nuclei ffuf python3'`.
3. **Expected:** the custom Kali image builds successfully and resolves the full binary set inside the container.

### 2. Deterministic local HTTP fixture drives HTTP-oriented tools end to end

1. Run `pytest tests/integration/test_tool_suite_integration.py::test_tool_suite_assets_are_seeded_in_sandbox tests/integration/test_tool_suite_integration.py::test_sandbox_http_fixture_serves_admin_fixture tests/integration/test_tool_suite_integration.py::test_httpx_executor_real_http_fixture tests/integration/test_tool_suite_integration.py::test_nuclei_executor_real_http_fixture tests/integration/test_tool_suite_integration.py::test_ffuf_executor_real_http_fixture -m integration -v`.
2. Inspect failures, if any, through `ToolResult.exit_code`, `stdout`, `stderr`, and `parsed_output`.
3. **Expected:** the fixture assets seed into `/tmp/oxpwn-tool-suite`, the in-sandbox HTTP server responds on port `18080`, and `httpx`/`nuclei`/`ffuf` all return structured parsed output.

### 3. Agent-visible registry and prompt wiring expose the entire suite

1. Run `python3 - <<'PY'
from oxpwn.agent.tools import ToolRegistry, register_default_tools
registry = ToolRegistry()
register_default_tools(registry)
print(registry.tool_names)
print([schema['function']['name'] for schema in registry.get_schemas()])
PY`.
2. Run `pytest tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v`.
3. **Expected:** both printed inventories are `['nmap', 'httpx', 'subfinder', 'nuclei', 'ffuf']`, registry/prompt tests pass, and Recon/Scanning hints mention the expanded tool subset.

## Edge Cases

### `subfinder` without outbound connectivity

1. Run `pytest tests/integration/test_tool_suite_integration.py::test_subfinder_executor_public_domain_or_skip -m integration -v`.
2. **Expected:** the test either passes with public-domain results or skips cleanly with an explicit outbound-connectivity explanation; it should not hard-fail for a network-gated environment.

### Parse-failure observability remains intact

1. Run `pytest tests/unit/test_httpx_parser.py::TestHttpxExecutor::test_run_parse_failure_degrades_to_none_and_warns tests/unit/test_subfinder_parser.py::TestSubfinderExecutor::test_run_parse_failure_degrades_to_none_and_warns tests/unit/test_nuclei_parser.py::TestNucleiExecutor::test_run_parse_failure_degrades_to_none_and_warns tests/unit/test_ffuf_parser.py::TestFfufExecutor::test_run_parse_failure_degrades_to_none_and_warns -v`.
2. **Expected:** all tests pass and confirm the per-tool warning events that accompany graceful parse degradation.

## Failure Signals

- The sandbox image no longer resolves one of `nmap`, `httpx`, `subfinder`, `nuclei`, `ffuf`, or `python3`.
- The deterministic fixture server does not start or `/admin/` is not reachable from inside the container.
- `parsed_output` unexpectedly becomes `None` for a happy-path integration proof.
- Registry order drifts, schemas disappear, or Recon/Scanning prompt hints stop mentioning the new tools.
- `subfinder` fails noisily instead of producing a result or a clean network-related skip.

## Requirements Proved By This UAT

- R002 — Confirms that the M001 core security tools run inside the custom Docker/Kali sandbox rather than on the host, with real execution proofs for all five tools.

## Not Proven By This UAT

- R001 — Does not prove the full five-phase autonomous pipeline; it only proves the expanded tool-suite substrate that supports Recon and Scanning.
- R004 — Does not prove real-time CLI streaming or terminal UX.
- R005 — Does not prove first-run model setup.
- R006 — Does not prove CVE/NVD enrichment.
- Full Juice Shop end-to-end acceptance remains for S08.

## Notes for Tester

- The fastest trustworthy runtime signal is the integration command used in the smoke test.
- For local debugging of HTTP-oriented regressions, inspect `tests/fixtures/tool_suite/` and `tests/integration/test_tool_suite_integration.py` first.
- If only `subfinder` is problematic, check outbound connectivity before assuming a parser or executor regression.
