---
id: T04
parent: S04
milestone: M001
provides:
  - Default agent-visible registration for the full five-tool core suite with stable typed schemas and executor factories
  - Phase guidance that steers Recon toward `subfinder`/`httpx`/`nmap` and Scanning toward `nuclei`/`ffuf`/`nmap`
  - Real Docker proof for `httpx`, `nuclei`, `ffuf`, and `subfinder`, composed with the existing real `nmap` integration proof
key_files:
  - src/oxpwn/agent/tools.py
  - src/oxpwn/agent/prompts.py
  - tests/unit/test_tool_registry.py
  - tests/unit/test_react_agent.py
  - tests/integration/test_tool_suite_integration.py
key_decisions:
  - Keep the default registry order stable as `nmap`, `httpx`, `subfinder`, `nuclei`, `ffuf`, and expose curated typed schemas instead of raw flag passthrough
  - Treat `subfinder` as the only internet-gated real proof and give it an explicit outbound-connectivity preflight plus clean skip messaging
patterns_established:
  - Verify agent-visible tool exposure by inspecting `ToolRegistry.get_schemas()` and asserting the exact schema inventory/order in unit tests
  - Verify prompt guidance through the real `ReactAgent` call path by inspecting the system prompt and `tools=` payload passed to `llm.complete`
  - For internet-gated integration proofs, preflight outbound connectivity first, then skip with an explicit reason only when the runtime failure is network-related
observability_surfaces:
  - `ToolRegistry.get_schemas()` and `registry.tool_names` now expose the full five-tool suite for direct inspection
  - `tests/unit/test_react_agent.py::TestDefaultRegistryPromptWiring` captures the agent-visible prompt text and schema payload passed to the LLM
  - `tests/integration/test_tool_suite_integration.py` localizes real-runtime failures per tool and surfaces explicit skip reasons for the public-domain `subfinder` path
duration: 1h05m
verification_result: passed
completed_at: 2026-03-14 20:40:18 PDT
blocker_discovered: false
---

# T04: Register the full suite and prove real sandbox execution

**Registered the full five-tool suite on the agent side, updated Recon/Scanning guidance, and proved `httpx`/`subfinder`/`nuclei`/`ffuf` in real Docker alongside the existing real `nmap` proof.**

## What Happened

I extended `src/oxpwn/agent/tools.py` so `register_default_tools(...)` now exposes `nmap`, `httpx`, `subfinder`, `nuclei`, and `ffuf` in a stable default order. Each new tool got a curated JSON schema aligned with its executor interface: multi-target tools use typed scalar-or-list inputs, scanning tools keep focused numeric/boolean options, and `ffuf` exposes the deterministic in-sandbox wordlist default rather than free-form flags.

I updated `src/oxpwn/agent/prompts.py` without changing the S03 prompt structure: Recon guidance now explicitly points the agent toward `subfinder` for passive domain enumeration, `httpx` for live HTTP probing, and `nmap` for ports/services; Scanning guidance now points toward `nuclei`, `ffuf`, and targeted `nmap` follow-up.

I expanded the unit coverage in `tests/unit/test_tool_registry.py` and `tests/unit/test_react_agent.py` so the agent-facing contract is locked down. The registry tests now assert the full five-tool inventory, stable order, and per-tool schema surfaces. The React agent tests now assert that the default registry inventory reaches `llm.complete(...)`, that the system prompts contain the new phase-specific tool hints, and that the existing `ToolResult.parsed_output` dict contract still feeds JSON back to the LLM for both `nmap` and a newly registered tool type (`httpx`).

I replaced the scaffold-only integration file with real executor proofs in `tests/integration/test_tool_suite_integration.py`. The file still verifies the seeded fixture assets and in-sandbox HTTP fixture, then proves `httpx`, `nuclei`, and `ffuf` against the deterministic local target and proves `subfinder` against a public domain. Because `subfinder` is inherently internet-gated, the test now preflights outbound connectivity and skips cleanly only when the sandbox cannot reach public passive sources.

## Verification

Passed:

- `python3 -m py_compile src/oxpwn/agent/tools.py src/oxpwn/agent/prompts.py tests/unit/test_tool_registry.py tests/unit/test_react_agent.py tests/integration/test_tool_suite_integration.py`
- `python3 - <<'PY' ... ToolRegistry()/register_default_tools()/get_schemas() ... PY`
  - Confirmed tool inventory: `['nmap', 'httpx', 'subfinder', 'nuclei', 'ffuf']`
- `pytest tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v`
  - Result: `26 passed`
- `docker build -t oxpwn-sandbox:dev docker/ && docker run --rm oxpwn-sandbox:dev sh -lc 'for bin in nmap httpx subfinder nuclei ffuf python3; do command -v "$bin"; done'`
  - Confirmed all six binaries resolve in the sandbox image
- `pytest tests/integration/test_sandbox_integration.py::test_nmap_executor_real_scan tests/integration/test_tool_suite_integration.py -m integration -v`
  - Result: `7 passed`
  - Covered real `nmap`, fixture seeding, fixture HTTP runtime, real `httpx`, real `nuclei`, real `ffuf`, and real `subfinder`
- `pytest tests/unit/test_httpx_parser.py tests/unit/test_subfinder_parser.py tests/unit/test_nuclei_parser.py tests/unit/test_ffuf_parser.py tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v`
  - Result: `50 passed`

## Diagnostics

Future agents can inspect what T04 shipped with:

- `python3 - <<'PY'
from oxpwn.agent.tools import ToolRegistry, register_default_tools
registry = ToolRegistry()
register_default_tools(registry)
print(registry.tool_names)
print([schema['function']['name'] for schema in registry.get_schemas()])
PY`
  - Confirms the agent-visible five-tool inventory and schema order
- `pytest tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v`
  - Localizes registry schema drift vs prompt/dispatch drift
- `pytest tests/integration/test_sandbox_integration.py::test_nmap_executor_real_scan tests/integration/test_tool_suite_integration.py -m integration -v`
  - Localizes real-runtime failures to a specific tool proof
- `tests/integration/test_tool_suite_integration.py::test_subfinder_executor_public_domain_or_skip`
  - Exposes the explicit skip path when outbound connectivity to public passive sources is unavailable
- `ToolResult.exit_code`, `ToolResult.stdout`, `ToolResult.stderr`, and `ToolResult.parsed_output`
  - Continue to be the primary runtime inspection surfaces when a tool proof fails

## Deviations

- None.

## Known Issues

- None.

## Files Created/Modified

- `src/oxpwn/agent/tools.py` — registered the full five-tool suite and added curated agent-facing schemas for `httpx`, `subfinder`, `nuclei`, and `ffuf`
- `src/oxpwn/agent/prompts.py` — updated Recon and Scanning guidance to point the agent toward the phase-appropriate tool subset
- `tests/unit/test_tool_registry.py` — locked down the default five-tool registry inventory, schema order, and per-tool parameter surfaces
- `tests/unit/test_react_agent.py` — added prompt-wiring and non-`nmap` parsed-output contract coverage through the real agent call path
- `tests/integration/test_tool_suite_integration.py` — added real Docker proofs for `httpx`, `nuclei`, `ffuf`, and internet-aware `subfinder`
- `.gsd/DECISIONS.md` — recorded the stable five-tool agent-visible wiring decision for downstream work
- `.gsd/milestones/M001/slices/S04/S04-PLAN.md` — marked T04 complete
- `.gsd/STATE.md` — updated project state to reflect completed S04 work and next-slice readiness
