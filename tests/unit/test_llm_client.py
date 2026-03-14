"""Unit tests for LLMClient — mocked, no real LLM calls."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import structlog

from oxpwn.llm.client import LLMClient
from oxpwn.llm.exceptions import LLMAuthError, LLMRateLimitError


# ---------------------------------------------------------------------------
# Helpers — fake litellm response objects
# ---------------------------------------------------------------------------


def _make_usage(prompt: int = 100, completion: int = 50, total: int = 150):
    return SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total)


def _make_tool_call(
    call_id: str = "call_abc123",
    name: str = "get_weather",
    arguments: dict | None = None,
):
    args = arguments or {"location": "Seattle"}
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=json.dumps(args)),
    )


def _make_response(
    content: str = "Hello!",
    model: str = "gpt-4o-mini",
    usage: SimpleNamespace | None = None,
    tool_calls: list | None = None,
):
    """Build a fake litellm response matching the ModelResponse interface."""
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    resp = SimpleNamespace(
        choices=[choice],
        usage=usage or _make_usage(),
        model=model,
    )
    resp.model_dump = lambda: {"id": "fake", "model": model}
    return resp


# ---------------------------------------------------------------------------
# Tests — basic completion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_returns_llm_response():
    """LLMClient.complete() returns a populated LLMResponse."""
    client = LLMClient("gpt-4o-mini")
    fake_resp = _make_response(content="Test answer", model="gpt-4o-mini")

    with (
        patch("litellm.acompletion", new_callable=AsyncMock, return_value=fake_resp),
        patch("litellm.completion_cost", return_value=0.00042),
    ):
        result = await client.complete([{"role": "user", "content": "Hi"}])

    assert result.content == "Test answer"
    assert result.model == "gpt-4o-mini"
    assert result.tokens_used.input == 100
    assert result.tokens_used.output == 50
    assert result.tokens_used.total == 150
    assert result.cost == pytest.approx(0.00042)
    assert result.latency_ms >= 0
    assert result.tool_calls is None


@pytest.mark.asyncio
async def test_complete_with_tool_calls():
    """When the model invokes a tool, tool_calls is populated."""
    client = LLMClient("gpt-4o-mini")
    tc = _make_tool_call(name="get_weather", arguments={"location": "NYC"})
    fake_resp = _make_response(content="", tool_calls=[tc])

    with (
        patch("litellm.acompletion", new_callable=AsyncMock, return_value=fake_resp),
        patch("litellm.completion_cost", return_value=0.001),
    ):
        result = await client.complete(
            [{"role": "user", "content": "Weather in NYC?"}],
            tools=[{
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                        "required": ["location"],
                    },
                },
            }],
        )

    assert result.tool_calls is not None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["function"]["name"] == "get_weather"
    assert json.loads(result.tool_calls[0]["function"]["arguments"]) == {"location": "NYC"}
    assert result.tool_calls[0]["id"] == "call_abc123"


@pytest.mark.asyncio
async def test_complete_passes_tools_to_litellm():
    """Tool definitions are forwarded to litellm.acompletion."""
    client = LLMClient("gpt-4o-mini")
    fake_resp = _make_response()
    tools = [{"type": "function", "function": {"name": "noop", "parameters": {}}}]

    mock_acompletion = AsyncMock(return_value=fake_resp)
    with (
        patch("litellm.acompletion", mock_acompletion),
        patch("litellm.completion_cost", return_value=0.0),
    ):
        await client.complete([{"role": "user", "content": "x"}], tools=tools)

    call_kwargs = mock_acompletion.call_args
    assert call_kwargs.kwargs.get("tools") == tools or call_kwargs[1].get("tools") == tools


# ---------------------------------------------------------------------------
# Tests — error mapping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_error_mapped():
    """litellm.AuthenticationError → LLMAuthError."""
    import litellm as _litellm

    client = LLMClient("gpt-4o-mini", api_key="bad-key")

    exc = _litellm.AuthenticationError(
        message="Invalid API key",
        llm_provider="openai",
        model="gpt-4o-mini",
    )
    with patch("litellm.acompletion", new_callable=AsyncMock, side_effect=exc):
        with pytest.raises(LLMAuthError) as exc_info:
            await client.complete([{"role": "user", "content": "Hi"}])

    assert exc_info.value.model == "gpt-4o-mini"
    assert exc_info.value.provider == "openai"


@pytest.mark.asyncio
async def test_rate_limit_error_mapped():
    """litellm.RateLimitError → LLMRateLimitError."""
    import litellm as _litellm

    client = LLMClient("gpt-4o-mini")

    exc = _litellm.RateLimitError(
        message="Rate limit exceeded",
        llm_provider="openai",
        model="gpt-4o-mini",
    )
    with patch("litellm.acompletion", new_callable=AsyncMock, side_effect=exc):
        with pytest.raises(LLMRateLimitError) as exc_info:
            await client.complete([{"role": "user", "content": "Hi"}])

    assert exc_info.value.model == "gpt-4o-mini"


# ---------------------------------------------------------------------------
# Tests — structlog output
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_structlog_logs_model_and_cost_not_api_key(capsys):
    """Structlog emits model/cost/tokens/latency but never the API key."""
    # Capture structlog output
    captured_events: list[dict] = []

    def capture_processor(logger, method_name, event_dict):
        captured_events.append(event_dict.copy())
        raise structlog.DropEvent

    old_config = structlog.get_config()
    structlog.configure(
        processors=[capture_processor],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        cache_logger_on_first_use=False,
    )

    try:
        client = LLMClient("gpt-4o-mini", api_key="sk-secret-key-12345")
        fake_resp = _make_response()

        with (
            patch("litellm.acompletion", new_callable=AsyncMock, return_value=fake_resp),
            patch("litellm.completion_cost", return_value=0.005),
        ):
            await client.complete([{"role": "user", "content": "Hi"}])
    finally:
        structlog.configure(**old_config)

    # Should have logged an event
    assert len(captured_events) >= 1
    event = captured_events[-1]

    # Must include model and cost
    assert event["model"] == "gpt-4o-mini"
    assert "cost_usd" in event
    assert "latency_ms" in event
    assert "tokens_input" in event

    # Must NOT include api_key anywhere
    event_str = str(event)
    assert "sk-secret-key-12345" not in event_str


# ---------------------------------------------------------------------------
# Tests — provider extraction
# ---------------------------------------------------------------------------


def test_provider_extraction_slash():
    """Model with '/' prefix extracts provider name."""
    client = LLMClient("anthropic/claude-3-haiku")
    assert client._provider == "anthropic"


def test_provider_extraction_no_slash():
    """Model without '/' defaults to 'openai'."""
    client = LLMClient("gpt-4o")
    assert client._provider == "openai"
