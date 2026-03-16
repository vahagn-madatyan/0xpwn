---
estimated_steps: 5
estimated_files: 4
---

# T01: Config model, YAML persistence, and env-override resolution

**Slice:** S06 — First-Run Wizard + Config
**Milestone:** M001

## Description

Build the standalone config data layer: a Pydantic model for the config schema, a `ConfigManager` class that handles YAML load/save with XDG path resolution, env-var override logic, and atomic file writes with restrictive permissions. This is the foundation that the wizard (T02) and CLI integration (T02) build on — it must be fully testable without prompts, LLM calls, or Rich output.

## Steps

1. Add `"pyyaml>=6.0"` to `pyproject.toml` dependencies and reinstall the package
2. Create `src/oxpwn/config/__init__.py` exporting `OxpwnConfig` and `ConfigManager`
3. Create `src/oxpwn/config/manager.py` with:
   - `OxpwnConfig` Pydantic model: `model: str | None`, `api_key: str | None`, `base_url: str | None`, `schema_version: int = 1`, with `extra="ignore"` for forward compat
   - `ConfigManager` class:
     - `get_config_path()` → resolves `OXPWN_CONFIG` env var, then `$XDG_CONFIG_HOME/oxpwn/config.yaml`, then `~/.config/oxpwn/config.yaml`
     - `load()` → reads YAML, validates through Pydantic, returns `OxpwnConfig` (returns empty config if file missing)
     - `save(config: OxpwnConfig)` → atomic write (write to `.tmp` sibling, `os.replace()`, `os.chmod(0o600)`), creates parent dirs
     - `delete()` → removes config file if it exists
     - `exists()` → bool
   - `resolve_config()` function: takes CLI options + env vars + YAML config → returns dict with resolved `model`, `api_key`, `base_url` following precedence: CLI > env > YAML
4. Create `tests/unit/test_config_manager.py` with tests covering:
   - Config model construction, validation, `extra="ignore"` forward compat
   - YAML round-trip (save then load produces identical config)
   - Missing config file returns empty/default config
   - Env var override precedence (env beats YAML)
   - CLI option override precedence (CLI beats env beats YAML)
   - Atomic write produces file with 0o600 permissions
   - `OXPWN_CONFIG` env var overrides default path
   - XDG_CONFIG_HOME env var changes default directory
   - Config with `extra` fields loads without error (schema migration safety)
   - `delete()` removes config, `exists()` returns correct state
5. Run full test suite to confirm no regressions

## Must-Haves

- [ ] PyYAML is a direct dependency in `pyproject.toml`
- [ ] `OxpwnConfig` Pydantic model validates and serializes cleanly
- [ ] YAML round-trip preserves all fields including `None` values
- [ ] Config file written with `0o600` permissions via atomic rename
- [ ] `OXPWN_CONFIG` env var overrides default config path
- [ ] Resolution precedence: CLI options > env vars > YAML config
- [ ] Extra/unknown YAML fields don't crash `load()` (forward compat)
- [ ] All existing 160 tests pass unchanged

## Verification

- `pytest tests/unit/test_config_manager.py -v` — all new tests pass
- `pytest tests/ -x -q` — full suite passes (160 existing + new)
- `python3 -c "from oxpwn.config import OxpwnConfig, ConfigManager; print('import ok')"` — module loads

## Observability Impact

- Signals added/changed: `config.loaded` and `config.written` structlog events with path context (never API key values)
- How a future agent inspects this: `ConfigManager().load()` returns current config state; `ConfigManager().get_config_path()` shows resolved path
- Failure state exposed: YAML parse errors logged with file path and error detail; missing file is not an error (returns default config)

## Inputs

- `pyproject.toml` — current dependency list to extend
- `src/oxpwn/core/models.py` — Pydantic v2 patterns (field validators, BaseModel conventions)
- `tests/conftest.py` — fixture factory pattern for test setup
- S06-RESEARCH.md — XDG path resolution, PyYAML coercion pitfalls, atomic write strategy

## Expected Output

- `pyproject.toml` — updated with `pyyaml>=6.0` dependency
- `src/oxpwn/config/__init__.py` — package exports
- `src/oxpwn/config/manager.py` — `OxpwnConfig` model + `ConfigManager` class + `resolve_config()` function
- `tests/unit/test_config_manager.py` — comprehensive unit tests for config persistence and resolution
