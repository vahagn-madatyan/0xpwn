"""Agent subsystem: ReAct loop, tool registry, events, and prompts."""

from oxpwn.agent.events import (
    AgentEvent,
    AgentEventCallback,
    ErrorEvent,
    PhaseTransitionEvent,
    ReasoningEvent,
    ToolCallEvent,
    ToolOutputChunkEvent,
    ToolResultEvent,
)
from oxpwn.agent.exceptions import AgentError, AgentMaxIterationsError
from oxpwn.agent.react import ReactAgent
from oxpwn.agent.tools import ToolRegistry

__all__ = [
    "AgentError",
    "AgentEvent",
    "AgentEventCallback",
    "AgentMaxIterationsError",
    "ErrorEvent",
    "PhaseTransitionEvent",
    "ReactAgent",
    "ReasoningEvent",
    "ToolCallEvent",
    "ToolOutputChunkEvent",
    "ToolRegistry",
    "ToolResultEvent",
]
