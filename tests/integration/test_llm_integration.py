"""Integration tests for LLMClient against a real LLM provider.

Requires an API key in the environment for the chosen provider.
Set OXPWN_TEST_MODEL to override the default model (gpt-4o-mini).

Run with: pytest tests/integration/ -m integration -v
"""

from __future__ import annotations

import json
import os

import pytest

from oxpwn.llm.client import LLMClient

# Skip entire module if no API key is available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not any(os.environ.get(k) for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY")),
        reason="No LLM API key set — skipping integration tests",
    ),
]

MODEL = os.environ.get("OXPWN_TEST_MODEL", "gpt-4o-mini")


@pytest.fixture()
def client() -> LLMClient:
    return LLMClient(MODEL)


WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather for a location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name, e.g. 'Seattle, WA'",
                },
            },
            "required": ["location"],
        },
    },
}


@pytest.mark.asyncio
async def test_tool_calling(client: LLMClient):
    """Send a prompt with a tool schema and verify the model invokes it."""
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant. Use the get_weather tool when asked about weather.",
        },
        {"role": "user", "content": "What's the weather like in Seattle?"},
    ]

    result = await client.complete(messages, tools=[WEATHER_TOOL])

    # The model should invoke the tool
    assert result.tool_calls is not None, "Expected model to invoke get_weather tool"
    assert len(result.tool_calls) >= 1

    tc = result.tool_calls[0]
    assert tc["function"]["name"] == "get_weather"

    args = json.loads(tc["function"]["arguments"])
    assert "location" in args

    # Token and cost tracking
    assert result.tokens_used.total > 0
    assert result.cost >= 0
    assert result.latency_ms > 0
    assert result.model  # should have a model string


@pytest.mark.asyncio
async def test_basic_completion(client: LLMClient):
    """A simple completion without tools returns content."""
    messages = [{"role": "user", "content": "Say 'hello' and nothing else."}]

    result = await client.complete(messages, temperature=0.0)

    assert result.content  # should have text content
    assert "hello" in result.content.lower()
    assert result.tokens_used.total > 0
    assert result.cost >= 0
    assert result.latency_ms > 0
    assert result.tool_calls is None
