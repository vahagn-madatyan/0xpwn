---
id: T02
parent: S01
milestone: M001
provides:
  - Async LLMClient wrapping LiteLLM with tool calling, cost tracking, and typed exceptions
  - Integration test proving provider-agnostic LLM support (R003 proof point)
key_files:
  - src/oxpwn/llm/client.py
  - src/oxpwn/llm/exceptions.py
  - src/oxpwn/llm/__init__.py
  - tests/unit/test_llm_client.py
  - tests/integration/test_llm_integration.py
key_decisions:
  - Used gemini/gemini-2.5-flash for integration tests (gemini-2.0-flash free tier quota exhausted)
patterns_established:
  - Typed exception hierarchy with model/provider context on every error
  - structlog structured logging per LLM call (model, tokens, cost, latency — never secrets)
  - _provider property extracts provider from model string (slash prefix or default openai)
observability_surfaces:
  - "structlog event 'llm.complete' per call: model, tokens_input, tokens_output, cost_usd, latency_ms, has_tool_calls"
  - "Typed exceptions carry model and provider context; LLMRateLimitError includes retry_after"
duration: 15m
verification_result: passed
completed_at: 2026-03-13
blocker_discovered: false
---

# T02: Implement LiteLLM async client with tool calling and integration test

**Built async LLMClient with tool calling, cost tracking via litellm.completion_cost(), typed exceptions, and structlog observability — proven against Gemini via integration test.**

## What Happened

All implementation was already in place from a prior run. Verified the existing code against all must-haves:

1. **exceptions.py** — `LLMError` base with model/provider context, `LLMAuthError`, `LLMRateLimitError` (with retry_after), `LLMToolCallError`.
2. **client.py** — `LLMClient` with async `complete()` method wrapping `litellm.acompletion()`. Passes tools in OpenAI function calling format. Extracts token usage, computes cost via `litellm.completion_cost()`, parses tool calls, returns `LLMResponse`. Maps litellm exceptions to typed hierarchy. Logs each call via structlog with model, tokens, cost, latency (never API keys).
3. **__init__.py** — Exports `LLMClient` and all exception types.
4. **Unit tests** — 8 tests covering: basic completion response mapping, tool call parsing, tool forwarding to litellm, AuthenticationError→LLMAuthError mapping, RateLimitError→LLMRateLimitError mapping, structlog output verification (includes model/cost, excludes api_key), provider extraction from model string.
5. **Integration tests** — 2 tests against real Gemini LLM: tool calling round-trip (get_weather tool invoked, arguments parsed, tokens/cost/latency populated) and basic completion without tools.

## Verification

- `pytest tests/unit/test_llm_client.py -v` — **8/8 passed**
- `pytest tests/unit/ -v` — **43/43 passed** (8 LLM client + 35 model tests)
- `OXPWN_TEST_MODEL="gemini/gemini-2.5-flash" pytest tests/integration/ -m integration -v` — **2/2 passed**
- `0xpwn --help` — CLI entrypoint responds
- Slice verification (final task): all 3 checks pass ✅

## Diagnostics

- `grep "llm.complete" <structlog output>` — inspect per-call LLM telemetry
- `LLMResponse` fields: `model`, `tokens_used.{input,output,total}`, `cost`, `latency_ms`, `tool_calls`
- Exception inspection: `exc.model`, `exc.provider` on any `LLMError`; `exc.retry_after` on `LLMRateLimitError`
- Integration test run: `OXPWN_TEST_MODEL="gemini/gemini-2.5-flash" pytest tests/integration/ -m integration -v`

## Deviations

- Default integration test model `gpt-4o-mini` requires an OpenAI key. Used `OXPWN_TEST_MODEL=gemini/gemini-2.5-flash` with existing Gemini key instead. The `gemini-2.0-flash` model had exhausted its free tier quota (limit: 0), but `gemini-2.5-flash` worked. This proves provider-agnostic support as designed.

## Known Issues

- `gemini-2.0-flash` free tier quota is fully exhausted on the current Gemini API key. Use `gemini-2.5-flash` or set an `OPENAI_API_KEY` for integration tests.

## Files Created/Modified

- `src/oxpwn/llm/client.py` — Async LLMClient with tool calling, cost tracking, error mapping, structlog
- `src/oxpwn/llm/exceptions.py` — Typed exception hierarchy (LLMError, LLMAuthError, LLMRateLimitError, LLMToolCallError)
- `src/oxpwn/llm/__init__.py` — Public exports for llm subpackage
- `tests/unit/test_llm_client.py` — 8 mocked unit tests for client behavior
- `tests/integration/test_llm_integration.py` — 2 integration tests against real LLM with tool calling
