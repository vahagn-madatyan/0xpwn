"""Typed exception hierarchy for agent errors."""

from __future__ import annotations


class AgentError(Exception):
    """Base exception for all agent errors.

    Carries optional phase and iteration context for diagnostics.
    """

    def __init__(
        self,
        message: str,
        *,
        phase: str | None = None,
        iteration: int | None = None,
    ) -> None:
        self.phase = phase
        self.iteration = iteration
        super().__init__(message)


class AgentMaxIterationsError(AgentError):
    """Raised when a phase exhausts its iteration budget."""
