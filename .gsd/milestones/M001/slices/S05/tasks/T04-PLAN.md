---
estimated_steps: 3
estimated_files: 2
---

# T04: Prove the terminal streaming path at the real CLI boundary

**Slice:** S05 — Streaming CLI + Real-time Output
**Milestone:** M001

## Description

Close the slice at the actual entrypoint, not just helper classes. This task adds CLI-level integration coverage and a live smoke proof so S05 ends with a runnable installed command that demonstrates real-time terminal output on the real scan path.

## Steps

1. Add `tests/integration/test_cli_integration.py` that invokes the Typer app through `CliRunner`, uses the same Docker/LLM availability gating as the existing integration suite, and asserts the real `scan --target` path prints phase transitions, reasoning/tool blocks, and completion text instead of stub output.
2. Extend `tests/conftest.py` only if needed with small shared helpers for CLI env setup or integration skip logic, keeping the test as close as possible to the real user command path.
3. Execute the slice smoke command (`pip install -e . && OXPWN_MODEL=... 0xpwn scan --target localhost`) and confirm the terminal output appears incrementally during the run rather than as a single buffered dump at completion.

## Must-Haves

- [ ] Integration coverage exercises the real Typer entrypoint, not direct internal helpers
- [ ] Integration test skips cleanly when Docker or LLM credentials are unavailable
- [ ] Operational smoke proof uses the installed `0xpwn` command and shows visible streaming in the terminal

## Verification

- `pytest tests/integration/test_cli_integration.py -m integration -v`
- `pip install -e . && OXPWN_MODEL="${OXPWN_TEST_MODEL:-gemini/gemini-2.5-flash}" 0xpwn scan --target localhost`

## Observability Impact

- Signals added/changed: CLI integration output becomes a first-class proof surface for phase order, streamed tool chunks, and terminal-visible failures
- How a future agent inspects this: rerun the CLI integration test for automated proof, then use the installed-command smoke run when debugging terminal behavior or Rich formatting regressions
- Failure state exposed: entrypoint wiring mistakes, missing prerequisites, or non-streaming terminal regressions surface at the exact user boundary rather than only in lower-level unit tests

## Inputs

- `src/oxpwn/cli/main.py` — real Typer entrypoint from T03
- `tests/conftest.py` — existing Docker/LLM integration helpers and skip patterns
- T03 summary — CLI command and Rich renderer are now ready for boundary-level proof

## Expected Output

- `tests/integration/test_cli_integration.py` — real CLI-path integration coverage
- `tests/conftest.py` — any minimal shared helper additions needed for CLI integration setup
