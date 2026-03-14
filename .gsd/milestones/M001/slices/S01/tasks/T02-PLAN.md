---
estimated_steps: 5
estimated_files: 5
---

# T02: Implement LiteLLM async client with tool calling and integration test

**Slice:** S01 — Foundation + LLM Client
**Milestone:** M001

## Description

Build the async LLM client that wraps LiteLLM, handles tool/function calling, tracks cost and tokens, and raises typed exceptions. Prove it works against a real LLM provider via integration test. This is the R003 proof point — if this passes, we've proven provider-agnostic LLM support with tool calling.

## Steps

1. Create `src/oxpwn/llm/exceptions.py` with typed exception hierarchy: `LLMError` (base, includes model and provider context), `LLMAuthError` (invalid/missing API key), `LLMRateLimitError` (rate limit hit, includes retry_after if available), `LLMToolCallError` (tool call parsing failure).
2. Create `src/oxpwn/llm/client.py` with `LLMClient` class: constructor takes `model: str`, optional `api_key`, optional `base_url`. Async method `complete(messages, tools=None, temperature=0.7)` that calls `litellm.acompletion()`, measures latency, extracts token usage, computes cost via `litellm.completion_cost()`, parses tool calls from response, returns `LLMResponse`. Catch litellm exceptions and re-raise as typed `LLMError` subtypes. Log each call via structlog with model, tokens, cost, latency (never API keys).
3. Create `src/oxpwn/llm/__init__.py` exporting `LLMClient` and exceptions.
4. Write `tests/unit/test_llm_client.py`: mock `litellm.acompletion` to return a fake completion response (with and without tool calls). Test that `LLMResponse` is correctly populated (content, tokens, cost, tool_calls). Test error mapping: mock litellm raising `AuthenticationError` → `LLMAuthError`, `RateLimitError` → `LLMRateLimitError`. Test that structlog output includes model and cost but not api_key.
5. Write `tests/integration/test_llm_integration.py`: mark with `@pytest.mark.integration`. Use `OXPWN_TEST_MODEL` env var (default `gpt-4o-mini`) and expect API key in env. Send a prompt with a simple tool schema (e.g., `get_weather(location: str) -> str`). Assert response has content or tool_calls, tokens_used > 0, cost >= 0, latency_ms > 0. Test a second call without tools to prove basic completion works too.

## Must-Haves

- [ ] `LLMClient.complete()` is async and returns `LLMResponse`
- [ ] Tool definitions passed through to LiteLLM in OpenAI function calling format
- [ ] `LLMResponse.tool_calls` populated when model invokes a tool
- [ ] `LLMResponse.cost` populated via `litellm.completion_cost()`
- [ ] `LLMResponse.tokens_used` includes input, output, and total
- [ ] Typed exceptions: `LLMAuthError`, `LLMRateLimitError`, `LLMToolCallError`
- [ ] structlog logging per call (model, tokens, cost, latency — no secrets)
- [ ] Integration test passes against real LLM with tool calling

## Verification

- `pytest tests/unit/test_llm_client.py -v` — all mocked tests pass
- `pytest tests/integration/test_llm_integration.py -m integration -v` — real LLM test passes (needs API key)

## Observability Impact

- Signals added: structlog entry per `LLMClient.complete()` call with `model`, `tokens_input`, `tokens_output`, `cost_usd`, `latency_ms`, `has_tool_calls`
- How a future agent inspects this: grep structlog output for `llm.complete` events; inspect `LLMResponse` fields programmatically
- Failure state exposed: typed exceptions carry `model`, `provider` context; rate limit errors include `retry_after`

## Inputs

- `src/oxpwn/core/models.py` — `LLMResponse` model from T01
- `tests/conftest.py` — pytest fixtures and marker registration from T01

## Expected Output

- `src/oxpwn/llm/client.py` — async LLM client with tool calling and cost tracking
- `src/oxpwn/llm/exceptions.py` — typed exception hierarchy
- `tests/unit/test_llm_client.py` — mocked unit tests for client behavior
- `tests/integration/test_llm_integration.py` — real LLM integration test proving R003
