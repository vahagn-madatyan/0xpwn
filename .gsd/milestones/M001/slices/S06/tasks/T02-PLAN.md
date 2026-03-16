---
estimated_steps: 5
estimated_files: 5
---

# T02: Interactive wizard, CLI integration, and config subcommand

**Slice:** S06 — First-Run Wizard + Config
**Milestone:** M001

## Description

Build the interactive first-run wizard that detects Ollama, guides provider/model setup, validates LLM connectivity, and writes config via the T01 `ConfigManager`. Wire config loading into the existing `_build_scan_config()` resolution chain so that `0xpwn scan --target <url>` works without `--model` or env vars after the wizard runs once. Add `0xpwn config show/reset/wizard` subcommands.

## Steps

1. Create `src/oxpwn/cli/wizard.py` with `run_wizard(console: Console) -> OxpwnConfig | None`:
   - Detect non-interactive terminal (`sys.stdin.isatty()`) — return `None` immediately
   - Probe Ollama at `http://localhost:11434/api/tags` via `httpx.get()` with 3s timeout
   - If Ollama detected with models: offer local vs cloud choice via `Prompt.ask(choices=["local", "cloud"])`
   - If Ollama detected but no models: show guidance for `ollama pull`, still offer choice
   - If no Ollama: proceed to cloud provider flow
   - Cloud flow: select provider from list (openai, anthropic, gemini, other) → enter API key via `Prompt.ask(password=True)` → enter model string with provider-appropriate default
   - Local flow: select from detected Ollama models or enter custom model string → set model to `ollama/<model_name>`
   - Validate LLM connectivity via `asyncio.run(litellm.acompletion())` with `max_tokens=5` and 30s timeout — on failure, re-prompt or allow skip
   - Save config via `ConfigManager().save()` — print success with config path
   - Return the saved `OxpwnConfig`
2. Modify `src/oxpwn/cli/main.py`:
   - Import `ConfigManager`, `resolve_config` from `oxpwn.config`
   - In `_build_scan_config()`: after CLI/env resolution, if model is still empty, try `ConfigManager().load()` for YAML-backed defaults; if still no model and `sys.stdin.isatty()`, call `run_wizard()`; only raise `ScanBootstrapError` if wizard was skipped/declined/failed
   - Add `config_app = typer.Typer(name="config", help="Manage 0xpwn configuration.")` with subcommands:
     - `show`: load and display config with redacted API key
     - `reset`: delete config file with confirmation
     - `wizard`: re-run wizard
   - Register `config_app` on main `app` via `app.add_typer(config_app)`
3. Create `tests/unit/test_wizard.py` with tests covering:
   - Wizard completes full cloud flow with monkeypatched `Prompt.ask` and mocked `litellm.acompletion`
   - Wizard completes local/Ollama flow with mocked httpx response
   - Wizard skips on non-interactive terminal (monkeypatch `sys.stdin.isatty` → False)
   - Wizard handles Ollama unreachable gracefully (falls to cloud flow)
   - Wizard handles LLM validation failure with re-prompt or skip
   - Wizard saves config via ConfigManager
4. Update `tests/unit/test_cli_main.py` with additional tests:
   - `_build_scan_config()` loads from YAML config when model not in CLI/env
   - `_build_scan_config()` triggers wizard when no config and interactive terminal
   - `_build_scan_config()` raises `ScanBootstrapError` when no config and non-interactive
   - `config show` displays redacted config
   - `config reset` deletes config file
   - `config wizard` invokes wizard flow
5. Run full test suite to confirm all pass

## Must-Haves

- [ ] Wizard detects Ollama via HTTP probe and lists available models
- [ ] Wizard collects API key with masked input for cloud providers
- [ ] Wizard validates LLM connectivity with a real (mocked in tests) completion call
- [ ] Non-interactive terminals skip wizard and fall through to `ScanBootstrapError`
- [ ] Config loads into `_build_scan_config()` as fallback after CLI/env options
- [ ] `0xpwn config show` displays config with redacted API key
- [ ] `0xpwn config reset` deletes the config file
- [ ] `0xpwn config wizard` re-runs the wizard
- [ ] Rich prompt styling is consistent with existing CLI panels
- [ ] All existing 160 tests pass unchanged; new tests all pass

## Verification

- `pytest tests/unit/test_wizard.py -v` — all wizard flow tests pass
- `pytest tests/unit/test_cli_main.py -v` — existing + new CLI tests pass
- `pytest tests/ -x -q` — full suite passes
- `0xpwn config --help` — shows show/reset/wizard subcommands

## Observability Impact

- Signals added/changed: `wizard.started`, `wizard.completed`, `wizard.skipped` structlog events; `config.loaded` on scan bootstrap
- How a future agent inspects this: `0xpwn config show` for current config state; structlog events for wizard flow tracing
- Failure state exposed: wizard validation errors displayed as Rich panels; `ScanBootstrapError` message updated to suggest running `0xpwn config wizard`

## Inputs

- `src/oxpwn/config/manager.py` — `OxpwnConfig`, `ConfigManager`, `resolve_config` from T01
- `src/oxpwn/cli/main.py` — existing `_build_scan_config()`, `ScanBootstrapError`, `ScanRuntimeConfig`
- `src/oxpwn/cli/streaming.py` — `render_error_panel()`, Rich Console patterns for visual consistency
- `src/oxpwn/llm/client.py` — `LLMClient` init signature (model, api_key, base_url)
- S06-RESEARCH.md — Ollama API shape, LiteLLM validation approach, non-interactive detection

## Expected Output

- `src/oxpwn/cli/wizard.py` — interactive wizard with Ollama detection, provider selection, validation, and config save
- `src/oxpwn/cli/main.py` — config loading wired into `_build_scan_config()`, `config` subcommand with show/reset/wizard
- `tests/unit/test_wizard.py` — wizard flow tests with mocked prompts/LLM
- `tests/unit/test_cli_main.py` — updated with config-backed bootstrap and subcommand tests
