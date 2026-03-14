# S01: Foundation + LLM Client

**Goal:** Python package scaffolded, Pydantic state models defined, LiteLLM async client proven with tool calling and cost tracking against a real LLM.
**Demo:** `pip install -e .` installs the package; `pytest tests/unit/` passes model and client unit tests; `pytest tests/integration/ -m integration` proves real LLM tool calling returns structured responses with cost data.

## Must-Haves

- `pyproject.toml` with `[project.scripts]` entrypoint for `0xpwn` CLI stub
- `pip install -e .` succeeds and `0xpwn --help` runs
- Pydantic models: `Phase`, `Finding`, `ToolResult`, `ScanState`, `LLMResponse` with validation
- Async LLM client wrapping LiteLLM `acompletion()` with tool/function calling support
- Cost tracking via `litellm.completion_cost()`
- Provider-agnostic — any LiteLLM-supported model string works
- Integration test proving tool calling round-trip against a real LLM

## Proof Level

- This slice proves: contract (models serialize/validate correctly) + integration (LLM client works against real provider)
- Real runtime required: yes (integration test hits a real LLM API)
- Human/UAT required: no

## Verification

- `pip install -e . && 0xpwn --help` — package installs and CLI stub responds
- `pytest tests/unit/ -v` — model validation and mocked client tests pass
- `pytest tests/integration/ -m integration -v` — real LLM tool calling test passes (requires API key in env)

## Observability / Diagnostics

- Runtime signals: LLM client logs model, token count, cost, and latency per call via `structlog`
- Inspection surfaces: `LLMResponse` includes `model`, `tokens_used`, `cost`, `latency_ms`, `tool_calls` fields
- Failure visibility: Client raises typed exceptions (`LLMError`, `LLMAuthError`, `LLMRateLimitError`) with model/provider context
- Redaction constraints: API keys never logged; only provider name and model string appear in logs/errors

## Integration Closure

- Upstream surfaces consumed: none (first slice)
- New wiring introduced in this slice: `oxpwn.core.models` and `oxpwn.llm.client` — the foundational contracts S02, S03, S05, S06 all consume
- What remains before the milestone is truly usable end-to-end: sandbox (S02), agent loop (S03), tools (S04), CLI streaming (S05), wizard (S06), CVE enrichment (S07), integration (S08)

## Tasks

- [x] **T01: Scaffold Python package with Pydantic state models and test framework** `est:45m`
  - Why: Every subsequent slice imports `oxpwn.core.models` — this must exist first with validated contracts. Also establishes the test framework all slices will use.
  - Files: `pyproject.toml`, `src/oxpwn/__init__.py`, `src/oxpwn/core/__init__.py`, `src/oxpwn/core/models.py`, `src/oxpwn/cli/__init__.py`, `src/oxpwn/cli/main.py`, `tests/conftest.py`, `tests/unit/test_models.py`
  - Do: Create `src/` layout with `pyproject.toml` (pydantic, litellm, typer, rich, structlog, pytest deps). Define Phase enum (recon/scanning/exploitation/validation/reporting), Finding, ToolResult, ScanState, LLMResponse as Pydantic models with field validation. Add minimal Typer CLI stub (`0xpwn --help`). Set up pytest with `conftest.py` and unit marker. Write model unit tests covering construction, validation errors, serialization, and edge cases.
  - Verify: `pip install -e . && 0xpwn --help && pytest tests/unit/test_models.py -v`
  - Done when: Package installs cleanly, CLI stub responds, all model unit tests pass
- [x] **T02: Implement LiteLLM async client with tool calling and integration test** `est:1h`
  - Why: The LLM client is the highest-risk component in this slice — tool calling behavior varies across providers, and cost tracking must be proven real, not assumed. This is the R003 proof.
  - Files: `src/oxpwn/llm/__init__.py`, `src/oxpwn/llm/client.py`, `src/oxpwn/llm/exceptions.py`, `tests/unit/test_llm_client.py`, `tests/integration/test_llm_integration.py`, `tests/conftest.py`
  - Do: Build async `LLMClient` class wrapping `litellm.acompletion()`. Accept model string + optional api_key. Support tool definitions (OpenAI function calling format). Return `LLMResponse` with token counts, cost, latency, and parsed tool calls. Add typed exceptions for auth, rate limit, and generic LLM errors. Log calls via structlog (model, tokens, cost, latency — never keys). Write unit tests with mocked litellm. Write integration test (`@pytest.mark.integration`) that sends a real prompt with a dummy tool schema to a real LLM and asserts structured response with cost > 0.
  - Verify: `pytest tests/unit/test_llm_client.py -v && pytest tests/integration/test_llm_integration.py -m integration -v`
  - Done when: Mocked unit tests pass, integration test proves real tool calling round-trip with cost data against a live LLM

## Files Likely Touched

- `pyproject.toml`
- `src/oxpwn/__init__.py`
- `src/oxpwn/core/__init__.py`
- `src/oxpwn/core/models.py`
- `src/oxpwn/cli/__init__.py`
- `src/oxpwn/cli/main.py`
- `src/oxpwn/llm/__init__.py`
- `src/oxpwn/llm/client.py`
- `src/oxpwn/llm/exceptions.py`
- `tests/conftest.py`
- `tests/unit/test_models.py`
- `tests/unit/test_llm_client.py`
- `tests/integration/test_llm_integration.py`
