---
id: T03
parent: S05
milestone: M001
provides:
  - A real `0xpwn scan --target` command that composes the existing scan runtime and streams append-only Rich output
key_files:
  - src/oxpwn/cli/streaming.py
  - src/oxpwn/cli/main.py
  - tests/unit/test_cli_streaming.py
  - tests/unit/test_cli_main.py
  - src/oxpwn/cli/__init__.py
key_decisions:
  - Keep pre-wizard scan bootstrap narrow and env-first: `--target` is required, advanced runtime knobs stay option/env-backed, and secrets stay env-only
  - Render failures with explicit Rich error panels and provider/sandbox context, but never print raw auth exception text or credential-bearing URLs
patterns_established:
  - The CLI now funnels all real scan execution through `asyncio.run(_scan_async(...))`, with `_scan_async` owning runtime composition and `RichStreamingCallback` owning append-only event rendering
  - Renderer output is append-only and phase-aware: scan header → phase rules → reasoning/tool/chunk/result/error blocks → final summary
observability_surfaces:
  - `tests/unit/test_cli_streaming.py` for exact Rich output ordering/content
  - `tests/unit/test_cli_main.py` for `CliRunner` command behavior, bootstrap failures, and secret-safe error output
  - `cli.scan_start`, `cli.scan_complete`, and `cli.scan_failed` structured logs
  - Rich CLI error panels for bootstrap, Docker, LLM, and agent/runtime failures
duration: 1h 10m
verification_result: passed
completed_at: 2026-03-14 23:45:13 PDT
blocker_discovered: false
---

# T03: Wire a Rich streaming callback into the real `0xpwn scan --target` command

**Replaced the CLI stub with the real `scan --target` runtime, added an append-only Rich streaming renderer, and covered both rendering/order and command/bootstrap failure paths with unit tests.**

## What Happened

I created `src/oxpwn/cli/streaming.py` with a `RichStreamingCallback` that implements the existing agent callback protocol and renders scan headers, phase rules, reasoning panels, tool dispatch panels, raw stdout/stderr chunk lines, tool result panels, error panels, and a final summary. The renderer is append-only and uses `Console.print()` plus `Rule`/`Panel` primitives instead of any `Live` dashboard surface.

I replaced the stub `scan(target)` command in `src/oxpwn/cli/main.py` with the real `scan --target` path. The command now resolves a minimal pre-wizard runtime config from options/env, builds `ScanState`, `ToolRegistry`, `DockerSandbox`, `LLMClient`, and `ReactAgent`, and runs the real async composition through `asyncio.run(_scan_async(...))`. I also added a `run()` module entrypoint so `python3 -m oxpwn.cli.main scan --help` exercises the same command surface.

I kept the runtime surface narrow and wizard-compatible: `--target` is the required user-facing input, while `--model`, `--llm-base-url`, `--sandbox-image`, `--network-mode`, and `--max-iterations-per-phase` stay option/env-backed. Secrets remain env-only through provider env vars or `OXPWN_API_KEY`.

Failure handling is now user-facing and secret-safe. Missing model config raises a bootstrap error panel, Docker image/daemon issues raise sandbox panels, LLM auth/rate-limit/runtime failures show provider/model guidance without echoing raw exception text, and agent/runtime exceptions surface phase/iteration context when available. I also redacted credential-bearing URLs in display-bound header/tool-argument output and removed an eager package import in `src/oxpwn/cli/__init__.py` so `python -m oxpwn.cli.main ...` no longer emits the runpy warning.

I replaced the two placeholder unit files with real coverage. `tests/unit/test_cli_streaming.py` asserts append-only ordering plus redaction in exported Rich text. `tests/unit/test_cli_main.py` covers `--target` parsing and async runtime execution through `CliRunner`, non-zero exit on missing model config, secret-safe runtime failure rendering, `_scan_async` composition against fake runtime dependencies, and the module `run()` entrypoint.

## Verification

Passed:
- `pytest tests/unit/test_cli_streaming.py tests/unit/test_cli_main.py -v`
- `python3 -m oxpwn.cli.main scan --help`
- `pytest tests/unit/test_docker_sandbox.py tests/unit/test_tool_registry.py tests/unit/test_react_agent.py tests/unit/test_tool_streaming.py tests/unit/test_cli_streaming.py tests/unit/test_cli_main.py -v`

Slice-level verification status recorded during this task:
- `pytest tests/integration/test_cli_integration.py -m integration -v` → expected failure on the intentional T04 placeholder test (`Pending S05/T04: add the real CLI integration proof for streaming scan output.`)
- `pip install -e . && OXPWN_MODEL="${OXPWN_TEST_MODEL:-gemini/gemini-2.5-flash}" 0xpwn scan --target localhost` → not run in this task because no LLM API key env vars were present in this shell (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OXPWN_API_KEY` all absent); preflight confirmed `python3 -m pip` is available and Docker is reachable

## Diagnostics

To inspect this work later:
- Run `pytest tests/unit/test_cli_streaming.py -v` to capture exact append-only renderer ordering/content via `Console(record=True).export_text()`
- Run `pytest tests/unit/test_cli_main.py -v` to inspect `CliRunner` command behavior, fake-runtime composition, and secret-safe failure output
- Inspect `cli.scan_start`, `cli.scan_complete`, and `cli.scan_failed` structured logs for scan ID, model, sandbox image, and failure class without credential leakage
- Trigger bootstrap/runtime failures via `0xpwn scan --target ...` without `OXPWN_MODEL`, with a missing sandbox image, or with bad provider auth to see the new Rich error panels

## Deviations

None.

## Known Issues

- `tests/integration/test_cli_integration.py` is still the intentional T04 placeholder and continues to fail until the real CLI integration proof is added
- The live smoke command still needs an exported LLM API key before it can be run end-to-end from this shell

## Files Created/Modified

- `src/oxpwn/cli/streaming.py` — added the append-only Rich renderer, shared error-panel helper, and display-time credential-bearing URL redaction helpers
- `src/oxpwn/cli/main.py` — replaced the stub scan command with the real async runtime composition, env/option-backed config, secret-safe error handling, and a `python -m` entrypoint
- `src/oxpwn/cli/__init__.py` — removed the eager import of `main` so `python -m oxpwn.cli.main ...` runs without the runpy warning
- `tests/unit/test_cli_streaming.py` — replaced the placeholder with Rich renderer ordering/redaction coverage
- `tests/unit/test_cli_main.py` — replaced the placeholder with command parsing, bootstrap failure, secret-safe runtime failure, fake-runtime composition, and module-entrypoint coverage
- `.gsd/milestones/M001/slices/S05/S05-PLAN.md` — marked T03 complete
- `.gsd/milestones/M001/slices/S05/tasks/T03-SUMMARY.md` — recorded implementation, verification, and remaining slice-level gaps
- `.gsd/STATE.md` — advanced the next action to T04
