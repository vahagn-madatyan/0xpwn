"""Async LLM client wrapping LiteLLM with tool calling and cost tracking."""

from __future__ import annotations

import time
from typing import Any

import litellm
import structlog

from oxpwn.core.models import LLMResponse, TokenUsage
from oxpwn.llm.exceptions import (
    LLMAuthError,
    LLMError,
    LLMRateLimitError,
    LLMToolCallError,
)

logger = structlog.get_logger("oxpwn.llm")


class LLMClient:
    """Provider-agnostic async LLM client with tool calling and cost tracking.

    Wraps LiteLLM's ``acompletion`` to provide:
    - Structured ``LLMResponse`` return values
    - Token and cost tracking via ``litellm.completion_cost``
    - Tool/function calling in OpenAI format
    - Typed exceptions with model/provider context
    - structlog logging per call (no secrets)
    """

    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Send a completion request and return a structured ``LLMResponse``.

        Args:
            messages: Chat messages in OpenAI format.
            tools: Optional tool definitions in OpenAI function calling format.
            temperature: Sampling temperature.

        Returns:
            Populated ``LLMResponse`` with content, tokens, cost, and tool calls.

        Raises:
            LLMAuthError: Invalid or missing API key.
            LLMRateLimitError: Provider rate limit exceeded.
            LLMToolCallError: Failed to parse tool calls from response.
            LLMError: Any other LLM-related failure.
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if self.api_key is not None:
            kwargs["api_key"] = self.api_key
        if self.base_url is not None:
            kwargs["api_base"] = self.base_url
        if tools is not None:
            kwargs["tools"] = tools

        t0 = time.monotonic()
        try:
            response = await litellm.acompletion(**kwargs)
        except litellm.AuthenticationError as exc:
            raise LLMAuthError(
                str(exc),
                model=self.model,
                provider=self._provider,
            ) from exc
        except litellm.RateLimitError as exc:
            retry_after = _extract_retry_after(exc)
            raise LLMRateLimitError(
                str(exc),
                model=self.model,
                provider=self._provider,
                retry_after=retry_after,
            ) from exc
        except litellm.exceptions.APIError as exc:
            raise LLMError(
                str(exc),
                model=self.model,
                provider=self._provider,
            ) from exc
        except Exception as exc:
            raise LLMError(
                str(exc),
                model=self.model,
                provider=self._provider,
            ) from exc

        latency_ms = int((time.monotonic() - t0) * 1000)

        # Extract token usage
        usage = response.usage or {}
        token_usage = TokenUsage(
            input=getattr(usage, "prompt_tokens", 0) or 0,
            output=getattr(usage, "completion_tokens", 0) or 0,
            total=getattr(usage, "total_tokens", 0) or 0,
        )

        # Compute cost
        try:
            cost = litellm.completion_cost(completion_response=response)
        except Exception:
            cost = 0.0

        # Extract content and tool calls
        choice = response.choices[0] if response.choices else None
        message = choice.message if choice else None
        content = (message.content or "") if message else ""

        tool_calls = _parse_tool_calls(message, model=self.model, provider=self._provider)

        # Determine actual model from response (may differ from request)
        response_model = getattr(response, "model", self.model) or self.model

        llm_response = LLMResponse(
            content=content,
            model=response_model,
            tokens_used=token_usage,
            cost=cost,
            latency_ms=latency_ms,
            tool_calls=tool_calls,
            raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
        )

        logger.info(
            "llm.complete",
            model=response_model,
            tokens_input=token_usage.input,
            tokens_output=token_usage.output,
            cost_usd=cost,
            latency_ms=latency_ms,
            has_tool_calls=bool(tool_calls),
        )

        return llm_response

    @property
    def _provider(self) -> str:
        """Extract provider name from model string (e.g., 'openai' from 'gpt-4o')."""
        if "/" in self.model:
            return self.model.split("/", 1)[0]
        return "openai"


def _parse_tool_calls(
    message: Any,
    *,
    model: str,
    provider: str,
) -> list[dict[str, Any]] | None:
    """Parse tool calls from a response message.

    Returns None if no tool calls are present. Raises LLMToolCallError
    if tool calls exist but can't be parsed.
    """
    if message is None:
        return None

    raw_tool_calls = getattr(message, "tool_calls", None)
    if not raw_tool_calls:
        return None

    try:
        parsed = []
        for tc in raw_tool_calls:
            entry: dict[str, Any] = {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            parsed.append(entry)
        return parsed
    except (AttributeError, TypeError) as exc:
        raise LLMToolCallError(
            f"Failed to parse tool calls from response: {exc}",
            model=model,
            provider=provider,
        ) from exc


def _extract_retry_after(exc: Exception) -> float | None:
    """Try to pull a retry-after value from a rate limit exception."""
    # LiteLLM may include headers or attributes with retry info
    for attr in ("retry_after", "headers"):
        val = getattr(exc, attr, None)
        if val is not None:
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, dict):
                ra = val.get("retry-after") or val.get("Retry-After")
                if ra is not None:
                    try:
                        return float(ra)
                    except (ValueError, TypeError):
                        pass
    return None
