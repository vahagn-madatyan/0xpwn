---
estimated_steps: 5
estimated_files: 5
---

# T04: Register the full suite and prove real sandbox execution

**Slice:** S04 — Tool Suite Integration
**Milestone:** M001

## Description

Close the slice by wiring the new executors into the agent-facing surfaces and proving the composed runtime path. S03 already proved the ReAct loop mechanics; this task makes the new tools selectable by that loop and adds the real Docker evidence that the suite works against deterministic targets rather than only in mocked unit tests.

## Steps

1. Update `src/oxpwn/agent/tools.py` so the default registry exposes `httpx`, `subfinder`, `nuclei`, and `ffuf` alongside `nmap`, each with curated typed schemas and executor factories that align with the new executor interfaces.
2. Update `src/oxpwn/agent/prompts.py` so phase guidance clearly points Recon toward `subfinder`/`httpx`/`nmap` and Scanning toward `nuclei`/`ffuf`/`nmap`, without regressing the S03 prompt structure.
3. Extend `tests/unit/test_tool_registry.py` and `tests/unit/test_react_agent.py` to assert that the default registry exposes the full 5-tool suite and that the agent-facing dispatch/prompt path still works with the unchanged `ToolResult.parsed_output` dict contract.
4. Create `tests/integration/test_tool_suite_integration.py` that uses the T01 fixture helpers to prove `httpx`, `nuclei`, and `ffuf` against the local HTTP fixture and `subfinder` against a public domain with clean skip behavior when outbound connectivity is unavailable.
5. Run the targeted unit and integration commands, treating S02’s existing real `nmap` integration test as part of the slice-level proof so the full 5-tool core suite is covered.

## Must-Haves

- [ ] Default tool registration exposes all 5 core tools with stable schemas
- [ ] Prompt guidance is updated so the ReAct agent has phase-appropriate tool hints beyond `nmap`
- [ ] Unit coverage proves registry/prompt wiring did not break the S03 agent contract
- [ ] Integration proof exists for the four new tools, and the slice verification explicitly reuses the real `nmap` proof from S02

## Verification

- `pytest tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v` — all pass
- `pytest tests/integration/test_sandbox_integration.py::test_nmap_executor_real_scan tests/integration/test_tool_suite_integration.py -m integration -v` — real Docker proofs pass or skip cleanly for the internet-gated subfinder case

## Observability Impact

- Signals added/changed: registry schema inventory and updated prompt text become inspectable agent-facing surfaces; integration tests expose per-tool real-runtime failures instead of parser-only failures
- How a future agent inspects this: call `ToolRegistry.get_schemas()`, inspect prompt output in unit tests, and run the integration file to isolate image/fixture/network issues per tool
- Failure state exposed: wrong schema wiring, prompt drift, or runtime execution failure becomes localized to registry tests, prompt assertions, or a specific integration test case

## Inputs

- `src/oxpwn/agent/tools.py` — default tool registration seam from S03
- `src/oxpwn/agent/prompts.py` — phase guidance seam from S03
- `src/oxpwn/sandbox/tools/httpx.py` — recon executor from T02
- `src/oxpwn/sandbox/tools/subfinder.py` — recon executor from T02
- `src/oxpwn/sandbox/tools/nuclei.py` — scanning executor from T03
- `src/oxpwn/sandbox/tools/ffuf.py` — scanning executor from T03
- `tests/conftest.py` — T01 fixture helpers for local HTTP proof targets
- `tests/integration/test_sandbox_integration.py` — existing real `nmap` proof reused for slice-level verification

## Expected Output

- `src/oxpwn/agent/tools.py` — default registry includes all 5 core tools
- `src/oxpwn/agent/prompts.py` — phase guidance reflects the full tool suite
- `tests/unit/test_tool_registry.py` — unit coverage for full-suite registration
- `tests/unit/test_react_agent.py` — unit coverage for prompt/dispatch compatibility
- `tests/integration/test_tool_suite_integration.py` — real Docker proof for `httpx`, `subfinder`, `nuclei`, and `ffuf`
