---
id: T01
parent: S01
milestone: M001
provides:
  - Python package with src/ layout, editable install, and CLI entrypoint
  - Pydantic data models (Phase, Severity, Finding, ToolResult, LLMResponse, ScanState)
  - pytest framework with conftest fixtures and integration marker
key_files:
  - pyproject.toml
  - src/oxpwn/core/models.py
  - src/oxpwn/cli/main.py
  - tests/conftest.py
  - tests/unit/test_models.py
key_decisions:
  - Used hatchling as build backend (lightweight, supports src/ layout natively)
  - TokenUsage as a separate nested model inside LLMResponse (cleaner than flat fields, mirrors provider response shapes)
  - ScanState has mutation methods (add_finding, add_tool_result, advance_phase, record_llm_usage) rather than pure immutable updates — pragmatic for a mutable scan session
patterns_established:
  - src/oxpwn layout with core/, cli/ subpackages
  - Pydantic BaseModel with field validators for domain constraints
  - conftest.py with fixture factories (scan_state_factory) for composable test setup
  - StrEnum for Phase and Severity (string-serializable, exhaustive)
observability_surfaces:
  - ScanState tracks total_cost, total_tokens, phases_completed — full scan lifecycle visible
  - All models support JSON round-trip serialization for persistence/debugging
duration: 15m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T01: Scaffold Python package with Pydantic state models and test framework

**Stood up the `oxpwn` Python package with 6 Pydantic models, CLI entrypoint, and 35 passing unit tests.**

## What Happened

Created the full package structure: `pyproject.toml` with hatchling build backend, src/ layout, all dependencies (pydantic, litellm, typer, rich, structlog, httpx), and dev dependencies (pytest, pytest-asyncio, pytest-mock). The `[project.scripts]` mapping wires `0xpwn` to the Typer app.

Defined 6 Pydantic models in `core/models.py`: `Phase` and `Severity` as StrEnums, `Finding` with CVSS range validation, `ToolResult` with duration non-negative constraint, `TokenUsage` for LLM token breakdown, `LLMResponse` with cost/latency constraints, and `ScanState` with mutation methods for accumulating findings, tool results, phase transitions, and LLM usage.

CLI stub uses Typer with `--version` callback and a `scan` command placeholder. Test framework has `conftest.py` with shared fixtures and a `scan_state_factory` for composable test setup.

## Verification

- `pip install -e ".[dev]"` — installed successfully with all deps
- `0xpwn --help` — exits 0, shows usage with `scan` command and `--version` option
- `0xpwn --version` — prints `0xpwn 0.1.0`
- `python -c "from oxpwn.core.models import ScanState, Finding, Phase; print('imports ok')"` — no import errors
- `pytest tests/unit/test_models.py -v` — **35/35 passed** in 0.04s
- Slice-level: `pip install -e . && 0xpwn --help` ✅ | `pytest tests/unit/ -v` ✅ | `pytest tests/integration/ -m integration -v` — not yet (T02)

## Diagnostics

- `0xpwn --help` — verify CLI entrypoint works
- `python -c "from oxpwn.core.models import ScanState; print(ScanState.model_json_schema())"` — inspect model schema
- `pytest tests/unit/test_models.py -v` — run model validation suite

## Deviations

- Added `Severity` StrEnum (critical/high/medium/low/info) — not explicitly listed in the plan's model list but referenced as `Finding.severity` type. Needed as a proper enum rather than a plain string.
- Added `TokenUsage` as a separate model — the plan described `tokens_used` with input/output/total fields; extracted to a dedicated model for cleaner nesting.

## Known Issues

None.

## Files Created/Modified

- `pyproject.toml` — package definition with deps, scripts, pytest config
- `src/oxpwn/__init__.py` — package root with version
- `src/oxpwn/core/__init__.py` — core subpackage init
- `src/oxpwn/core/models.py` — 6 Pydantic models with validators
- `src/oxpwn/cli/__init__.py` — CLI subpackage, re-exports app
- `src/oxpwn/cli/main.py` — Typer CLI with --version and scan stub
- `tests/__init__.py` — test package init
- `tests/conftest.py` — shared fixtures and markers
- `tests/unit/__init__.py` — unit test package init
- `tests/unit/test_models.py` — 35 model unit tests
