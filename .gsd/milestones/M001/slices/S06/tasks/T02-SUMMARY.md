---
id: T02
parent: S06
milestone: M001
provides:
  - Interactive first-run wizard with Ollama detection, cloud/local provider flows, LLM validation, and config persistence
  - Config-backed `_build_scan_config()` resolution chain (CLI > env > YAML > wizard)
  - `0xpwn config show/reset/wizard` subcommands
key_files:
  - src/oxpwn/cli/wizard.py
  - src/oxpwn/cli/main.py
  - tests/unit/test_wizard.py
  - tests/unit/test_cli_main.py
key_decisions:
  - Wizard is synchronous (Rich prompts + httpx sync for Ollama probe); LLM validation uses asyncio.run(litellm.acompletion()) for the single connectivity check
  - config_reset skips confirmation in non-interactive terminals (CliRunner), allows reset without TTY in CI
  - _build_scan_config uses resolve_config() for unified precedence then falls back to wizard only when interactive
patterns_established:
  - Wizard monkeypatching via `rich.prompt.Prompt.ask` and `rich.prompt.Confirm.ask` lambdas with iterators for multi-prompt flows
  - Config isolation in tests via monkeypatch.setenv("OXPWN_CONFIG", str(tmp_path / "config.yaml"))
observability_surfaces:
  - wizard.started / wizard.completed / wizard.skipped structlog events
  - config.loaded structlog event on scan bootstrap
  - 0xpwn config show for inspecting current config state with redacted API key
duration: 25m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Interactive wizard, CLI integration, and config subcommand

**Built the interactive first-run wizard, wired config loading into the scan command resolution chain, and added `0xpwn config show/reset/wizard` subcommands.**

## What Happened

Created `src/oxpwn/cli/wizard.py` with the full wizard flow:
1. Non-interactive detection via `sys.stdin.isatty()` — returns None immediately
2. Ollama probe via `httpx.get()` at `localhost:11434/api/tags` with 3s timeout
3. Local flow: lists detected Ollama models with numbered selection or custom entry, prefixes with `ollama/`
4. Cloud flow: provider selection (openai/anthropic/gemini/other) → masked API key → model string with provider-appropriate defaults → optional base URL for "other"
5. LLM validation via `asyncio.run(litellm.acompletion())` with `max_tokens=5` and 30s timeout, up to 2 retries on failure
6. Config persistence via `ConfigManager().save()` with path display

Modified `_build_scan_config()` in `main.py` to:
- Load YAML config via `ConfigManager().load()` as fallback
- Use `resolve_config()` for unified CLI > env > YAML precedence
- Trigger wizard when model still empty and terminal is interactive
- Only raise `ScanBootstrapError` after wizard is skipped/declined/failed (message updated to suggest `0xpwn config wizard`)

Added `config_app` Typer subcommand with three commands:
- `show`: displays config with redacted API key (`sk-1***cdef` format)
- `reset`: deletes config file with confirmation (skips confirm in non-interactive)
- `wizard`: re-runs the wizard flow

## Verification

- `pytest tests/unit/test_wizard.py -v` — 15 tests pass (non-interactive skip, cloud flow with 3 providers, local flow with/without models, Ollama unreachable fallback, validation retry/decline/skip, config persistence, helper functions)
- `pytest tests/unit/test_cli_main.py -v` — 14 tests pass (5 original unchanged + 9 new: YAML-backed bootstrap, wizard trigger, non-interactive error, config show with redaction, config show no config, config reset, config reset no-op, config wizard subcommand, config help)
- `pytest tests/unit/test_config_manager.py -v` — 27 tests pass (T01 tests unchanged)
- `pytest tests/unit/ -x -q` — 192 passed (168 original + 24 new)
- `0xpwn config --help` — shows show/reset/wizard subcommands

### Slice-level verification status (final task):
- ✅ `pytest tests/unit/test_config_manager.py -v` — 27 passed
- ✅ `pytest tests/unit/test_wizard.py -v` — 15 passed
- ✅ `pytest tests/unit/test_cli_main.py -v` — 14 passed
- ✅ `pytest tests/ -x -q` — 192 passed (full unit suite; integration test skipped due to Docker NotFound)
- ✅ `0xpwn config --help` — shows show/reset/wizard subcommands

## Diagnostics

- `0xpwn config show` — displays current config state with redacted API key
- `wizard.started` / `wizard.completed` / `wizard.skipped` structlog events for flow tracing
- `config.loaded` structlog event on scan bootstrap with `has_model` field
- Wizard validation errors displayed as Rich panels with retry/skip options
- `ScanBootstrapError` message now suggests `0xpwn config wizard` as recovery action

## Deviations

None — implementation followed the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `src/oxpwn/cli/wizard.py` — new: interactive first-run wizard with Ollama detection, provider selection, LLM validation, config persistence
- `src/oxpwn/cli/main.py` — modified: added config_app subcommand (show/reset/wizard), wired config loading + wizard trigger into _build_scan_config(), added Panel/Confirm/sys imports
- `tests/unit/test_wizard.py` — new: 15 tests covering all wizard flows (non-interactive, cloud providers, local/Ollama, validation failures, config persistence, helpers)
- `tests/unit/test_cli_main.py` — modified: added 9 tests for config-backed bootstrap, wizard trigger, config subcommands
- `.gsd/milestones/M001/slices/S06/S06-PLAN.md` — marked T02 as done
