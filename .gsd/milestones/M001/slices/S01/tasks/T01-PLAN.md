---
estimated_steps: 5
estimated_files: 8
---

# T01: Scaffold Python package with Pydantic state models and test framework

**Slice:** S01 — Foundation + LLM Client
**Milestone:** M001

## Description

Stand up the `oxpwn` Python package with `src/` layout, define the Pydantic data models that every downstream slice imports, create a minimal CLI stub proving the entrypoint works, and establish the pytest framework with fixtures and markers.

## Steps

1. Create `pyproject.toml` with `src/` layout, dependencies (pydantic, litellm, typer, rich, structlog, httpx), dev dependencies (pytest, pytest-asyncio, pytest-mock), `[project.scripts]` mapping `0xpwn = "oxpwn.cli.main:app"`, and project metadata (name, version 0.1.0, description, license Apache-2.0, python >=3.11).
2. Create package structure: `src/oxpwn/__init__.py`, `src/oxpwn/core/__init__.py`, `src/oxpwn/cli/__init__.py`. Define Pydantic models in `src/oxpwn/core/models.py`: `Phase` (StrEnum: recon, scanning, exploitation, validation, reporting), `Severity` (StrEnum: critical, high, medium, low, info), `Finding` (title, severity, description, url, evidence, cve_id optional, cvss optional, cwe_id optional, remediation optional, raw_output optional, tool_name), `ToolResult` (tool_name, command, stdout, stderr, exit_code, parsed_output optional dict, duration_ms, timestamp), `LLMResponse` (content, model, tokens_used with input/output/total, cost, latency_ms, tool_calls optional list, raw_response optional dict), `ScanState` (target, phases_completed list, current_phase, findings list, tool_results list, start_time, end_time optional, total_cost, total_tokens, metadata dict).
3. Create `src/oxpwn/cli/main.py` with minimal Typer app: `app = typer.Typer()` with a `scan` command stub that prints "Not implemented yet" and a `--version` callback. Import and re-export `app` in `src/oxpwn/cli/__init__.py`.
4. Create `tests/conftest.py` with pytest markers (`integration`), `pytest.ini` / pyproject.toml pytest config to register markers, and shared fixtures (sample Finding, sample ToolResult, sample ScanState factory).
5. Write `tests/unit/test_models.py`: test construction of each model with valid data, test validation errors (missing required fields, invalid enum values, negative cost), test JSON serialization round-trip, test ScanState accumulation (add findings, add tool results, advance phase), test edge cases (empty findings list, zero cost, long stdout in ToolResult).

## Must-Haves

- [ ] `pyproject.toml` is valid and `pip install -e .` succeeds
- [ ] `0xpwn --help` outputs usage info after install
- [ ] All 5 Pydantic models defined with field validation
- [ ] `Phase` and `Severity` are StrEnums with correct members
- [ ] `ScanState` tracks accumulated findings, tool results, cost, and tokens
- [ ] `tests/conftest.py` registers `integration` marker and provides model fixtures
- [ ] All model unit tests pass

## Verification

- `pip install -e . && 0xpwn --help` — exits 0 with usage output
- `pytest tests/unit/test_models.py -v` — all tests pass
- `python -c "from oxpwn.core.models import ScanState, Finding, Phase; print('imports ok')"` — no import errors

## Inputs

- (none — first task in first slice)

## Expected Output

- `pyproject.toml` — complete package definition with deps and entrypoint
- `src/oxpwn/` — package with `core/models.py` (Pydantic models) and `cli/main.py` (Typer stub)
- `tests/conftest.py` — pytest config with fixtures and markers
- `tests/unit/test_models.py` — model unit tests
