"""Typed event dataclasses and callback protocol for the agent loop."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol, Union


ToolOutputStream = Literal["stdout", "stderr"]


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReasoningEvent:
    """LLM produced reasoning text for the current turn."""

    content: str
    phase: str
    iteration: int


@dataclass(frozen=True)
class ToolCallEvent:
    """Agent is about to dispatch a tool call."""

    tool_name: str
    arguments: dict[str, Any]
    phase: str
    iteration: int


@dataclass(frozen=True)
class ToolOutputChunkEvent:
    """A raw stdout/stderr chunk streamed from a running tool."""

    tool_name: str
    stream: ToolOutputStream
    chunk: str
    phase: str
    iteration: int


@dataclass(frozen=True)
class ToolResultEvent:
    """A tool execution completed."""

    tool_name: str
    result_summary: str
    duration_ms: int
    phase: str
    iteration: int


@dataclass(frozen=True)
class PhaseTransitionEvent:
    """Agent is moving from one phase to the next."""

    from_phase: str
    to_phase: str
    summary: str


@dataclass(frozen=True)
class ErrorEvent:
    """An error occurred during the agent loop."""

    error: str
    phase: str
    iteration: int


AgentEvent = Union[
    ReasoningEvent,
    ToolCallEvent,
    ToolOutputChunkEvent,
    ToolResultEvent,
    PhaseTransitionEvent,
    ErrorEvent,
]


# ---------------------------------------------------------------------------
# Callback protocol
# ---------------------------------------------------------------------------


class AgentEventCallback(Protocol):
    """Protocol for receiving agent events."""

    async def on_event(self, event: AgentEvent) -> None: ...  # pragma: no cover
