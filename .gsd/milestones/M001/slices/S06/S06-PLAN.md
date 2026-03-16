# S06: First-Run Wizard + Config

**Goal:** First-time user runs `0xpwn` and gets an interactive wizard that detects Ollama, guides API key setup, validates connectivity, and persists config to YAML — with config resolution feeding into the existing scan command.
**Demo:** `0xpwn scan --target <url>` works without `--model` or env vars after the wizard runs once; `0xpwn config show` displays the persisted config; fresh install with no config triggers the wizard automatically.

## Must-Haves

- Pydantic config model with `model`, `api_key`, `base_url` fields and schema version
- YAML config persisted to `$XDG_CONFIG_HOME/oxpwn/config.yaml` (default `~/.config/oxpwn/config.yaml`) with `OXPWN_CONFIG` env override
- Atomic file writes with `0o600` permissions for API key safety
- Config resolution precedence: CLI options > env vars > YAML config > wizard trigger
- Interactive wizard: detect Ollama → choose provider → collect credentials → validate LLM connectivity → write config
- Non-interactive terminal detection — skip wizard gracefully, fall back to existing env-based behavior
- `0xpwn config show` / `0xpwn config reset` / `0xpwn config wizard` subcommands
- Wizard uses Rich prompts consistent with existing CLI styling
- Existing 160 tests pass unchanged
- PyYAML added as direct dependency in `pyproject.toml`

## Proof Level

- This slice proves: operational (wizard runs interactively, config persists and feeds into real scan command)
- Real runtime required: no (wizard validation uses mocked LLM; persistence tested with tmp_path)
- Human/UAT required: yes (wizard UX review — interactive flow quality)

## Verification

- `pytest tests/unit/test_config_manager.py -v` — config model, YAML round-trip, env override, atomic write, path resolution
- `pytest tests/unit/test_wizard.py -v` — wizard flow with mocked prompts, Ollama detection, provider selection, non-interactive skip
- `pytest tests/unit/test_cli_main.py -v` — existing + new tests for config-backed bootstrap, wizard trigger on missing config, `config` subcommand
- `pytest tests/ -x -q` — full suite passes (160 existing + new tests)
- `0xpwn config --help` — shows show/reset/wizard subcommands

## Observability / Diagnostics

- Runtime signals: `config.loaded` / `config.written` / `wizard.started` / `wizard.completed` / `wizard.skipped` structlog events
- Inspection surfaces: `0xpwn config show` displays current resolved config (redacted API key); config file path printed on write
- Failure visibility: wizard validation errors re-prompt with clear Rich error messages; config load failures logged with path and parse error
- Redaction constraints: API keys displayed as `sk-***...***` in `config show` and logs; never written to structlog or Rich output in full

## Integration Closure

- Upstream surfaces consumed: `src/oxpwn/cli/main.py` (`_build_scan_config()`, `ScanRuntimeConfig`, `ScanBootstrapError`), `src/oxpwn/cli/streaming.py` (Rich patterns), `src/oxpwn/llm/client.py` (`LLMClient` init signature)
- New wiring introduced in this slice: config loading injected into `_build_scan_config()` resolution chain; wizard triggered when no model configured and terminal is interactive; `config` subcommand added to Typer app
- What remains before the milestone is truly usable end-to-end: S07 (CVE enrichment), S08 (end-to-end validation)

## Tasks

- [x] **T01: Config model, YAML persistence, and env-override resolution** `est:45m`
  - Why: The config manager is the standalone data layer that the wizard and CLI integration build on — it must exist and be tested before any interactive flows
  - Files: `src/oxpwn/config/__init__.py`, `src/oxpwn/config/manager.py`, `tests/unit/test_config_manager.py`, `pyproject.toml`
  - Do: Add `pyyaml>=6.0` to pyproject.toml. Create Pydantic config model (`OxpwnConfig`) with `model`, `api_key`, `base_url`, `schema_version` fields. Implement `ConfigManager` with `load() → OxpwnConfig`, `save(config)`, `get_config_path() → Path`, `resolve(cli_options, env_vars, yaml_config) → ScanRuntimeConfig fields`. Use atomic write (temp file + rename) with `os.chmod(0o600)`. XDG path resolution with `OXPWN_CONFIG` env override. Pydantic `model_validate` with `extra="ignore"` for forward compat.
  - Verify: `pytest tests/unit/test_config_manager.py -v` — all pass; `pytest tests/ -x -q` — existing 160 tests unbroken
  - Done when: Config model validates, YAML round-trips correctly, env overrides take precedence, atomic writes produce 0o600 files, and all tests pass

- [x] **T02: Interactive wizard, CLI integration, and config subcommand** `est:1h`
  - Why: Delivers the user-facing R005 experience — first-run wizard guides model setup, persists config, and the scan command uses it without `--model` or env vars
  - Files: `src/oxpwn/cli/wizard.py`, `src/oxpwn/cli/main.py`, `tests/unit/test_wizard.py`, `tests/unit/test_cli_main.py`
  - Do: Create wizard with Rich prompts: (1) detect Ollama via `httpx.get("http://localhost:11434/api/tags")`, (2) offer local/cloud choice, (3) for cloud: select provider → enter API key (masked) → enter model string, (4) for Ollama: list available models or guide `ollama pull`, (5) validate via `litellm.acompletion()` with `max_tokens=5` and 30s timeout, (6) save config. Detect non-interactive terminal (`sys.stdin.isatty()`) and skip wizard. Wire config loading into `_build_scan_config()`: after env var check, before `ScanBootstrapError`, try loading YAML config; if no config and interactive, launch wizard. Add `config` Typer subapp with `show` (display config with redacted key), `reset` (delete config file), `wizard` (re-run wizard). Update existing CLI tests; add wizard flow tests with monkeypatched prompts.
  - Verify: `pytest tests/unit/test_wizard.py tests/unit/test_cli_main.py -v` — all pass; `pytest tests/ -x -q` — full suite passes; `0xpwn config --help` shows subcommands
  - Done when: Wizard completes with mocked prompts in tests, config persists and feeds into scan command, `config show/reset/wizard` work, non-interactive terminals skip wizard gracefully, and all 160+ tests pass

## Files Likely Touched

- `pyproject.toml`
- `src/oxpwn/config/__init__.py`
- `src/oxpwn/config/manager.py`
- `src/oxpwn/cli/wizard.py`
- `src/oxpwn/cli/main.py`
- `tests/unit/test_config_manager.py`
- `tests/unit/test_wizard.py`
- `tests/unit/test_cli_main.py`
