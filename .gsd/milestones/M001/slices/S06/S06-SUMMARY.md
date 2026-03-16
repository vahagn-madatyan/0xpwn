---
id: S06
parent: M001
milestone: M001
provides:
  - OxpwnConfig Pydantic model with model/api_key/base_url/schema_version fields and extra="ignore" forward-compat
  - ConfigManager with YAML load/save, XDG path resolution, atomic writes (0o600), delete/exists
  - resolve_config() implementing CLI > env > YAML precedence chain
  - Interactive first-run wizard with Ollama detection, cloud/local provider flows, LLM validation, config persistence
  - Config-backed _build_scan_config() resolution (CLI > env > YAML > wizard trigger)
  - 0xpwn config show/reset/wizard subcommands
  - PyYAML added as direct dependency
requires:
  - slice: S01
    provides: LLMClient init signature, litellm.acompletion for wizard validation
  - slice: S05
    provides: CLI framework (Typer app), _build_scan_config(), ScanRuntimeConfig, Rich patterns
affects:
  - S08
key_files:
  - src/oxpwn/config/__init__.py
  - src/oxpwn/config/manager.py
  - src/oxpwn/cli/wizard.py
  - src/oxpwn/cli/main.py
  - tests/unit/test_config_manager.py
  - tests/unit/test_wizard.py
  - tests/unit/test_cli_main.py
  - pyproject.toml
key_decisions:
  - Config resolution precedence: CLI > env > YAML > wizard trigger (Decision 28)
  - XDG path convention with OXPWN_CONFIG override, atomic writes with 0o600 (Decision 29)
  - Wizard synchronous design with asyncio.run() wrapper for single LLM validation call (Decision 30)
  - Pydantic extra="ignore" for forward-compat schema migration safety
patterns_established:
  - Config isolation in tests via monkeypatch.setenv("OXPWN_CONFIG", str(tmp_path / "config.yaml"))
  - Wizard monkeypatching via rich.prompt.Prompt.ask and Confirm.ask lambdas with iterators for multi-prompt flows
observability_surfaces:
  - structlog events: config.loaded (path, source), config.written (path), config.deleted (path)
  - structlog events: wizard.started, wizard.completed, wizard.skipped
  - 0xpwn config show — displays resolved config with redacted API key (sk-1***cdef format)
drill_down_paths:
  - .gsd/milestones/M001/slices/S06/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001/slices/S06/tasks/T02-SUMMARY.md
duration: 40m
verification_result: passed
completed_at: 2026-03-15
---

# S06: First-Run Wizard + Config

**Interactive first-run wizard with Ollama detection, cloud/local provider selection, LLM validation, YAML config persistence with XDG paths, and `0xpwn config show/reset/wizard` subcommands — wired into the scan command resolution chain.**

## What Happened

**T01 (Config data layer):** Added `pyyaml>=6.0` dependency. Built `OxpwnConfig` Pydantic model with `model`, `api_key`, `base_url`, `schema_version` fields and `extra="ignore"` for forward-compat. Implemented `ConfigManager` with XDG path resolution (`OXPWN_CONFIG` > `XDG_CONFIG_HOME` > `~/.config`), YAML load/save with atomic writes (temp file + `os.replace()` + `chmod 0o600`), delete, and exists. Created `resolve_config()` for CLI > env > YAML precedence with testable env dict parameter. 27 unit tests.

**T02 (Wizard + CLI integration):** Built the full wizard flow: non-interactive detection via `sys.stdin.isatty()`, Ollama probe via `httpx.get()` at `localhost:11434/api/tags`, local flow with model listing/selection, cloud flow with provider selection → masked API key → model string → optional base URL, LLM validation via `asyncio.run(litellm.acompletion())` with retry, and config persistence. Wired config loading into `_build_scan_config()` as a fallback between env vars and `ScanBootstrapError`. Added `config` Typer subapp with `show` (redacted key), `reset` (with confirmation), and `wizard` (re-run flow). 15 wizard tests + 9 new CLI tests.

## Verification

- `pytest tests/unit/test_config_manager.py -v` — **27/27 passed**
- `pytest tests/unit/test_wizard.py -v` — **15/15 passed**
- `pytest tests/unit/test_cli_main.py -v` — **14/14 passed** (5 original + 9 new)
- `pytest tests/ -x -q -m "not integration"` — **192 passed** (168 pre-S06 + 24 new)
- `0xpwn config --help` — shows show/reset/wizard subcommands
- Observability confirmed: `config.loaded`, `config.written`, `config.deleted` structlog events fire with path context
- API key redaction confirmed: `_redact_api_key()` produces `sk-1***cdef` format

## Requirements Advanced

- R005 (First-run guided model setup wizard) — fully implemented: interactive wizard detects Ollama, guides API key setup, validates LLM connectivity, persists to YAML, and feeds into scan command
- R003 (Provider-agnostic LLM support) — wizard supports OpenAI, Anthropic, Gemini, and custom providers; Ollama local models detected and configured automatically

## Requirements Validated

- R005 — proven by 56 unit tests (27 config + 15 wizard + 14 CLI) covering wizard flow (cloud/local/Ollama), config persistence, resolution precedence, non-interactive skip, and config subcommands. Human UAT required for interactive UX quality.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

None — implementation followed the slice plan exactly.

## Known Limitations

- Wizard LLM validation uses `asyncio.run()` wrapper — works for fresh processes but could conflict if called from an already-running event loop (not a concern for CLI usage)
- `config reset` skips confirmation in non-interactive terminals for CI/testing compatibility
- API key is stored as plaintext in YAML with 0o600 permissions — adequate for single-user workstations but not a secrets manager

## Follow-ups

- None — S07 (CVE enrichment) and S08 (end-to-end validation) are the remaining slices

## Files Created/Modified

- `pyproject.toml` — added `pyyaml>=6.0` to dependencies
- `src/oxpwn/config/__init__.py` — new package exporting OxpwnConfig, ConfigManager, resolve_config
- `src/oxpwn/config/manager.py` — config model, YAML persistence, env-override resolution
- `src/oxpwn/cli/wizard.py` — interactive wizard with Ollama detection, provider selection, LLM validation
- `src/oxpwn/cli/main.py` — added config_app subcommand, wired config loading + wizard trigger into _build_scan_config()
- `tests/unit/test_config_manager.py` — 27 unit tests for config data layer
- `tests/unit/test_wizard.py` — 15 unit tests for wizard flows
- `tests/unit/test_cli_main.py` — added 9 tests for config-backed bootstrap and config subcommands

## Forward Intelligence

### What the next slice should know
- `_build_scan_config()` in `main.py` now loads YAML config as a fallback — S08 integration tests should set `OXPWN_CONFIG` to a temp path to avoid wizard trigger
- Config isolation pattern: `monkeypatch.setenv("OXPWN_CONFIG", str(tmp_path / "config.yaml"))` prevents tests from touching real user config

### What's fragile
- Wizard Ollama probe assumes `localhost:11434` — if Ollama runs on a custom port/host, the probe fails silently and falls back to cloud flow (acceptable UX but not configurable)
- `asyncio.run()` in wizard validation — would break if wizard is ever called from async context (not currently possible from CLI)

### Authoritative diagnostics
- `0xpwn config show` — displays current resolved config state with redacted API key
- `config.loaded` structlog event — shows whether config was loaded from file or defaults, with `has_model` field

### What assumptions changed
- None — the S05 boundary (Decision 26) cleanly separated env-backed config from the wizard, and the S06 resolution chain (Decision 28) integrated them without conflict
