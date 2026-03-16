---
id: T01
parent: S06
milestone: M001
provides:
  - OxpwnConfig Pydantic model with model/api_key/base_url/schema_version fields and extra="ignore" forward-compat
  - ConfigManager class with YAML load/save, XDG path resolution, atomic writes, delete/exists
  - resolve_config() function implementing CLI > env > YAML precedence
  - PyYAML added as direct dependency
key_files:
  - src/oxpwn/config/__init__.py
  - src/oxpwn/config/manager.py
  - tests/unit/test_config_manager.py
  - pyproject.toml
key_decisions:
  - Used Pydantic BaseModel with extra="ignore" for forward-compat schema migration safety
  - Atomic write strategy: write to .tmp sibling, os.replace(), os.chmod(0o600)
  - resolve_config() accepts explicit env dict for testability (defaults to os.environ)
patterns_established:
  - Config isolation in tests via monkeypatch.setenv("OXPWN_CONFIG", str(tmp_path / "config.yaml"))
observability_surfaces:
  - structlog events: config.loaded (path, source), config.written (path), config.deleted (path)
duration: 15m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Config model, YAML persistence, and env-override resolution

**Built standalone config data layer: Pydantic model, YAML persistence with XDG path resolution, env-override precedence, and atomic writes with 0o600 permissions.**

## What Happened

1. Added `"pyyaml>=6.0"` to `pyproject.toml` dependencies and reinstalled.
2. Created `src/oxpwn/config/__init__.py` exporting `OxpwnConfig`, `ConfigManager`, `resolve_config`.
3. Created `src/oxpwn/config/manager.py` with:
   - `OxpwnConfig` Pydantic model: `model`, `api_key`, `base_url` (all `str | None`), `schema_version: int = 1`, `extra="ignore"` for forward-compat.
   - `ConfigManager` class: `get_config_path()` (OXPWN_CONFIG > XDG_CONFIG_HOME > ~/.config), `load()`, `save()` (atomic write via .tmp + os.replace + chmod 0o600), `delete()`, `exists()`.
   - `resolve_config()` function: merges CLI > env > YAML with testable env dict parameter.
4. Created `tests/unit/test_config_manager.py` with 27 tests covering model construction, extra-field forward-compat, path resolution (default/XDG/OXPWN_CONFIG), YAML round-trip, None preservation, atomic write permissions, delete/exists, corrupt YAML handling, and full precedence chain.

## Verification

- `pytest tests/unit/test_config_manager.py -v` — **27/27 passed**
- `pytest tests/ -x -q -m "not integration"` — **168 passed** (160 existing + 27 new - 19 integration deselected)
- `python3 -c "from oxpwn.config import OxpwnConfig, ConfigManager; print('import ok')"` — **ok**
- Structlog observability: `config.loaded`, `config.written`, `config.deleted` events confirmed with path context

### Slice-level verification (partial — T01 is intermediate):
- ✅ `pytest tests/unit/test_config_manager.py -v` — all pass
- ⏳ `pytest tests/unit/test_wizard.py -v` — not yet created (T02)
- ⏳ `pytest tests/unit/test_cli_main.py -v` — existing tests pass; new config-backed tests in T02
- ✅ `pytest tests/ -x -q` — full non-integration suite passes
- ⏳ `0xpwn config --help` — subcommand not yet wired (T02)

## Diagnostics

- `ConfigManager().load()` returns current config state from YAML or empty defaults
- `ConfigManager().get_config_path()` shows resolved path for the current environment
- YAML parse errors logged with path and error detail via structlog; missing file returns default config (not an error)
- API key values never appear in structlog events

## Deviations

None.

## Known Issues

- Pre-existing Docker integration test failures (stale container `9eb662a1...` not found) — unrelated to this task.

## Files Created/Modified

- `pyproject.toml` — added `pyyaml>=6.0` to dependencies
- `src/oxpwn/config/__init__.py` — new package exporting OxpwnConfig, ConfigManager, resolve_config
- `src/oxpwn/config/manager.py` — config model, YAML persistence, and env-override resolution implementation
- `tests/unit/test_config_manager.py` — 27 unit tests for config data layer
