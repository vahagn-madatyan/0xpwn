---
id: S01
parent: M001
milestone: M001
provides:
  - Python package with src/oxpwn layout, editable install, and `0xpwn` CLI entrypoint
  - Pydantic data models (Phase, Severity, Finding, ToolResult, TokenUsage, LLMResponse, ScanState) with validation
  - Async LLMClient wrapping LiteLLM with tool calling, cost tracking, typed exceptions, and structlog observability
  - pytest framework with conftest fixtures, integration marker, and factory pattern
requires:
  - slice: none
    provides: first slice — no upstream dependencies
affects:
  - S02 (consumes models + LLM client)
  - S03 (consumes models + LLM client)
  - S05 (consumes CLI framework)
  - S06 (consumes LLM client + CLI framework)
key_files:
  - pyproject.toml
  - src/oxpwn/core/models.py
  - src/oxpwn/cli/main.py
  - src/oxpwn/llm/client.py
  - src/oxpwn/llm/exceptions.py
  - tests/conftest.py
  - tests/unit/test_models.py
  - tests/unit/test_llm_client.py
  - tests/integration/test_llm_integration.py
key_decisions:
  - hatchling build backend (lightweight, native src/ layout support)
  - Nested TokenUsage Pydantic model inside LLMResponse (mirrors provider response shapes)
  - ScanState uses mutable methods (add_finding, add_tool_result, advance_phase, record_llm_usage) — pragmatic for mutable scan sessions
  - Severity and Phase as StrEnums (string-serializable, exhaustive)
  - gemini/gemini-2.5-flash used for integration tests (gemini-2.0-flash free tier exhausted)
patterns_established:
  - src/oxpwn layout with core/, cli/, llm/ subpackages
  - Pydantic BaseModel with field validators for domain constraints
  - conftest.py with fixture factories (scan_state_factory) for composable test setup
  - Typed exception hierarchy with model/provider context on every error
  - structlog structured logging per LLM call (model, tokens, cost, latency — never secrets)
observability_surfaces:
  - ScanState tracks total_cost, total_tokens, phases_completed — full scan lifecycle visible
  - All models support JSON round-trip serialization for persistence/debugging
  - "structlog event 'llm.complete' per call: model, tokens_input, tokens_output, cost_usd, latency_ms, has_tool_calls"
  - "Typed exceptions carry model and provider context; LLMRateLimitError includes retry_after"
drill_down_paths:
  - .gsd/milestones/M001/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001/slices/S01/tasks/T02-SUMMARY.md
duration: 30m
verification_result: passed
completed_at: 2026-03-13
---

# S01: Foundation + LLM Client

**Python package scaffolded with 6 Pydantic models, async LLM client with tool calling and cost tracking, CLI entrypoint, and 45 passing tests — proven against real Gemini LLM.**

## What Happened

**T01** stood up the `oxpwn` Python package: `pyproject.toml` with hatchling build backend, src/ layout, all runtime dependencies (pydantic, litellm, typer, rich, structlog, httpx), and dev dependencies (pytest, pytest-asyncio, pytest-mock). Defined 6 Pydantic models in `core/models.py`: `Phase` and `Severity` as StrEnums, `Finding` with CVSS range validation, `ToolResult` with duration non-negative constraint, `TokenUsage` for LLM token breakdown, `LLMResponse` with cost/latency constraints, and `ScanState` with mutation methods for accumulating findings, tool results, phase transitions, and LLM usage. CLI stub uses Typer with `--version` callback and a `scan` command placeholder. 35 unit tests cover construction, validation errors, serialization round-trips, and edge cases.

**T02** built the async `LLMClient` wrapping `litellm.acompletion()`. Accepts any LiteLLM model string, supports tool definitions in OpenAI function calling format, extracts token usage, computes cost via `litellm.completion_cost()`, parses tool calls, and returns `LLMResponse`. Typed exception hierarchy maps litellm errors to `LLMAuthError`, `LLMRateLimitError`, and `LLMToolCallError` — each carrying model/provider context. Every call logged via structlog (model, tokens, cost, latency — never API keys). 8 mocked unit tests plus 2 integration tests proving real tool calling round-trip against Gemini.

## Verification

- `pip install -e ".[dev]"` — installs cleanly ✅
- `0xpwn --help` — exits 0, shows usage with `scan` command ✅
- `0xpwn --version` — prints `0xpwn 0.1.0` ✅
- `pytest tests/unit/ -v` — **43/43 passed** (35 model + 8 LLM client) ✅
- `pytest tests/integration/ -m integration -v` — **2/2 passed** (tool calling + basic completion against gemini-2.5-flash) ✅
- Observability: ScanState total_cost/total_tokens/phases_completed tracked, JSON round-trip verified, LLMResponse fields populated with real data ✅

## Requirements Advanced

- R003 (Provider-agnostic LLM support) — LLMClient wraps LiteLLM with any model string, proven against Gemini; cost tracking via completion_cost() working

## Requirements Validated

- none — R003 advanced but not fully validated until Ollama local model also proven (S06)

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- Added `Severity` StrEnum — not explicitly listed in the plan's model enumeration but required as the typed field for `Finding.severity`.
- Added `TokenUsage` as a separate nested model — plan described `tokens_used` with input/output/total fields; extracted to dedicated model for cleaner composition.
- Used `gemini/gemini-2.5-flash` instead of default `gpt-4o-mini` for integration tests — Gemini key was available, OpenAI key was not. This actually strengthens the provider-agnostic proof.

## Known Limitations

- Integration tests require `GEMINI_API_KEY` env var (or `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`) — tests skip without one.
- `gemini-2.0-flash` free tier quota is exhausted on the current key; use `gemini-2.5-flash` or set a different provider key.
- CLI `scan` command is a stub — just prints placeholder message. Wired up in S05.

## Follow-ups

- none — all planned work completed as specified.

## Files Created/Modified

- `pyproject.toml` — package definition with deps, scripts, pytest config
- `src/oxpwn/__init__.py` — package root with version
- `src/oxpwn/core/__init__.py` — core subpackage init
- `src/oxpwn/core/models.py` — 6 Pydantic models with validators
- `src/oxpwn/cli/__init__.py` — CLI subpackage, re-exports app
- `src/oxpwn/cli/main.py` — Typer CLI with --version and scan stub
- `src/oxpwn/llm/__init__.py` — LLM subpackage exports
- `src/oxpwn/llm/client.py` — async LLMClient with tool calling, cost tracking, structlog
- `src/oxpwn/llm/exceptions.py` — typed exception hierarchy
- `tests/__init__.py` — test package init
- `tests/conftest.py` — shared fixtures, markers, scan_state_factory
- `tests/unit/__init__.py` — unit test package init
- `tests/unit/test_models.py` — 35 model unit tests
- `tests/unit/test_llm_client.py` — 8 mocked LLM client tests
- `tests/integration/__init__.py` — integration test package init
- `tests/integration/test_llm_integration.py` — 2 real LLM integration tests

## Forward Intelligence

### What the next slice should know
- LLMClient accepts any LiteLLM model string — `LLMClient("ollama/llama3")` would work for local. The `complete()` method takes `messages` (list of dicts) and optional `tools` (OpenAI format).
- ScanState mutation methods: `add_finding(Finding)`, `add_tool_result(ToolResult)`, `advance_phase(Phase)`, `record_llm_usage(LLMResponse)` — the agent loop in S03 will call these.
- Tool results go through `ToolResult` model with `tool_name`, `command`, `stdout`, `stderr`, `exit_code`, `duration_seconds`, and optional `parsed_output` dict.

### What's fragile
- `litellm.completion_cost()` returns 0.0 for some models/providers — cost tracking may show $0 for Ollama/local models. Not a bug, just the nature of local inference.
- The `_provider` property extracts provider from model string by splitting on `/` — works for `gemini/gemini-2.5-flash`, `openai/gpt-4o`, `ollama/llama3` but would fail for model strings without a slash (defaults to "openai").

### Authoritative diagnostics
- `pytest tests/unit/ -v` — 43 tests cover all model and client contracts
- `0xpwn --help` — confirms CLI entrypoint wiring
- `python3 -c "from oxpwn.core.models import ScanState; print(ScanState.model_json_schema())"` — inspect model schema

### What assumptions changed
- Plan assumed `gpt-4o-mini` as default integration test model — actual testing used `gemini/gemini-2.5-flash` due to available API keys. Provider-agnostic design validated by this switch.
