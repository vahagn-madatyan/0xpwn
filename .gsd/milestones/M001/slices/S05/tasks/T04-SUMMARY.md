---
id: T04
parent: S05
milestone: M001
provides:
  - CLI-level integration coverage exercising the real Typer entrypoint with Docker/LLM skip gating
  - Operational smoke proof that the installed 0xpwn command streams Rich output incrementally
key_files:
  - tests/integration/test_cli_integration.py
key_decisions:
  - Keep integration skip logic self-contained in the test file (inline _docker_available/_llm_key_available helpers) rather than adding shared conftest helpers, keeping the test as close as possible to the real user command path
patterns_established:
  - CLI integration tests use lightweight inline availability checks (not session-scoped fixtures) to skip gracefully when Docker or LLM keys are unavailable, avoiding fixture dependency chains
  - Non-gated boundary tests (bootstrap error, version flag) always run, ensuring entrypoint wiring is proved even without external services
observability_surfaces:
  - CLI integration test output becomes a first-class proof surface for phase order, streamed tool chunks, and terminal-visible failures
  - Smoke command (0xpwn scan --target localhost) prints incremental Rich panels: header → config → phase rule → reasoning/tool blocks → summary/error panel
duration: 12 minutes
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T04: Prove the terminal streaming path at the real CLI boundary

**Replaced the placeholder integration test with real CLI-path coverage that exercises the Typer entrypoint, skips cleanly without Docker/LLM, and proved the installed `0xpwn` command streams Rich output incrementally.**

## What Happened

1. Wrote `tests/integration/test_cli_integration.py` with five integration tests exercising the real Typer app through `CliRunner`:
   - `test_cli_scan_entrypoint_streams_real_output` — asserts header, phase rules, reasoning/tool blocks, summary, and ordering (Docker+LLM gated)
   - `test_cli_scan_streams_tool_output_chunks` — asserts streamed `stdout │` / `stderr │` chunk markers appear (Docker+LLM gated)
   - `test_cli_scan_output_contains_target_and_model_config` — verifies config panel content (Docker+LLM gated)
   - `test_cli_scan_skips_gracefully_without_model` — proves bootstrap error without `OXPWN_MODEL` (always runs)
   - `test_cli_scan_version_flag` — proves `--version` works (always runs)

2. No conftest.py changes needed — skip logic is self-contained with inline `_docker_available()` and `_llm_key_available()` helpers.

3. Ran the installed `0xpwn scan --target localhost` smoke command — confirmed Rich panels stream incrementally: scan header → config panel → phase rule → structlog lines → error panel (LLM auth failure expected without API key; Docker sandbox creation/destruction worked).

## Verification

- `python3 -m pytest tests/unit/test_docker_sandbox.py tests/unit/test_tool_registry.py tests/unit/test_react_agent.py tests/unit/test_tool_streaming.py tests/unit/test_cli_streaming.py tests/unit/test_cli_main.py -v` → **64 passed**
- `python3 -m pytest tests/integration/test_cli_integration.py -m integration -v` → **2 passed, 3 skipped** (Docker/LLM gated tests skip cleanly)
- Full slice verification: `python3 -m pytest tests/unit/... tests/integration/test_cli_integration.py -v` → **66 passed, 3 skipped**
- `pip3 install -e . && 0xpwn --version` → `0xpwn 0.1.0`
- `OXPWN_MODEL="gemini/gemini-2.5-flash" 0xpwn scan --target localhost` → Rich output streams incrementally (header → config → phase rule → error panel)

### Slice-level verification status (final task — all must pass):
- ✅ Unit test suite (64/64 passed)
- ✅ Integration test collection and non-gated tests (2 passed)
- ✅ Integration test skip gating (3 skipped cleanly)
- ✅ Installed CLI smoke command shows incremental streaming output
- ⏭️ Full Docker+LLM integration tests require external services (skip with clear reason)

## Diagnostics

- Run `pytest tests/integration/test_cli_integration.py -m integration -v` for automated CLI integration proof
- Run `pip install -e . && OXPWN_MODEL=... 0xpwn scan --target localhost` for terminal behavior / Rich formatting inspection
- With Docker + LLM API key present, the three skipped tests will exercise the full streaming path end-to-end

## Deviations

- Removed `mix_stderr=False` from `CliRunner()` — Typer's CliRunner doesn't support this Click parameter

## Known Issues

None

## Files Created/Modified

- `tests/integration/test_cli_integration.py` — Real CLI integration tests replacing the placeholder, with Docker/LLM skip gating
