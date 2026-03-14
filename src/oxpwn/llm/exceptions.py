"""Typed exception hierarchy for LLM client errors."""

from __future__ import annotations


class LLMError(Exception):
    """Base exception for all LLM client errors.

    Carries model and provider context for diagnostics.
    """

    def __init__(
        self,
        message: str,
        *,
        model: str | None = None,
        provider: str | None = None,
    ) -> None:
        self.model = model
        self.provider = provider
        super().__init__(message)


class LLMAuthError(LLMError):
    """Raised when the API key is invalid or missing."""


class LLMRateLimitError(LLMError):
    """Raised when the provider rate limit is hit."""

    def __init__(
        self,
        message: str,
        *,
        model: str | None = None,
        provider: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, model=model, provider=provider)


class LLMToolCallError(LLMError):
    """Raised when tool call parsing fails."""
