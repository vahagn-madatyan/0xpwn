"""Append-only Rich rendering for the streaming 0xpwn CLI."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

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
from oxpwn.core.models import Phase, ScanState

_PHASE_LABELS: dict[str, str] = {
    Phase.recon.value: "Recon",
    Phase.scanning.value: "Scanning",
    Phase.exploitation.value: "Exploitation",
    Phase.validation.value: "Validation",
    Phase.reporting.value: "Reporting",
    "complete": "Complete",
}

_PHASE_STYLES: dict[str, str] = {
    Phase.recon.value: "cyan",
    Phase.scanning.value: "magenta",
    Phase.exploitation.value: "yellow",
    Phase.validation.value: "green",
    Phase.reporting.value: "blue",
    "complete": "bright_green",
}


class RichStreamingCallback(AgentEventCallback):
    """Render agent events as append-only Rich output."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self._active_phase: str | None = None

    def render_scan_start(
        self,
        *,
        target: str,
        model: str,
        sandbox_image: str,
        network_mode: str,
        max_iterations_per_phase: int,
        scan_id: str,
        initial_phase: str = Phase.recon.value,
    ) -> None:
        """Print the scan header and initial phase rule."""
        self.console.print(Rule(title="0xpwn scan", style="bold blue"))
        header = "\n".join(
            [
                f"Target: {redact_string(target)}",
                f"Model: {model}",
                f"Sandbox image: {sandbox_image}",
                f"Network mode: {network_mode}",
                f"Max iterations/phase: {max_iterations_per_phase}",
                f"Scan ID: {scan_id}",
            ]
        )
        self.console.print(Panel(header, title="Scan configuration", border_style="blue"))
        self._print_phase_rule(initial_phase)

    def render_final_summary(self, scan_state: ScanState) -> None:
        """Print the final scan summary panel."""
        end_time = scan_state.end_time or datetime.now(timezone.utc)
        duration_s = max((end_time - scan_state.start_time).total_seconds(), 0.0)
        phases_completed = ", ".join(_phase_name(phase) for phase in scan_state.phases_completed) or "none"

        summary = "\n".join(
            [
                f"Target: {redact_string(scan_state.target)}",
                f"Phases completed: {phases_completed}",
                f"Tool executions: {len(scan_state.tool_results)}",
                f"Findings: {len(scan_state.findings)}",
                f"Tokens used: {scan_state.total_tokens}",
                f"Cost (USD): ${scan_state.total_cost:.4f}",
                f"Duration: {duration_s:.1f}s",
            ]
        )

        self.console.print(Rule(title="Scan summary", style="bold green"))
        self.console.print(Panel(summary, title="Completed", border_style="green"))

    async def on_event(self, event: AgentEvent) -> None:
        """Render one agent event."""
        if isinstance(event, ReasoningEvent):
            self._ensure_phase(event.phase)
            self.console.print(
                Panel(
                    event.content,
                    title=f"Reasoning · {_phase_name(event.phase)} · iter {event.iteration}",
                    border_style="blue",
                )
            )
            return

        if isinstance(event, ToolCallEvent):
            self._ensure_phase(event.phase)
            arguments = json.dumps(redact_value(event.arguments), indent=2, sort_keys=True)
            self.console.print(
                Panel(
                    arguments,
                    title=f"Tool dispatch · {event.tool_name}",
                    subtitle=f"{_phase_name(event.phase)} · iter {event.iteration}",
                    border_style="cyan",
                )
            )
            return

        if isinstance(event, ToolOutputChunkEvent):
            self._ensure_phase(event.phase)
            self._render_chunk(event)
            return

        if isinstance(event, ToolResultEvent):
            self._ensure_phase(event.phase)
            summary = event.result_summary or "(no summary)"
            self.console.print(
                Panel(
                    summary,
                    title=f"Tool result · {event.tool_name} · {event.duration_ms}ms",
                    subtitle=f"{_phase_name(event.phase)} · iter {event.iteration}",
                    border_style="green",
                )
            )
            return

        if isinstance(event, PhaseTransitionEvent):
            self.console.print(
                Rule(
                    title=(
                        f"Phase complete · {_phase_name(event.from_phase)} → "
                        f"{_phase_name(event.to_phase)}"
                    ),
                    style="bold magenta",
                )
            )
            self.console.print(
                Panel(
                    event.summary,
                    title="Phase summary",
                    border_style="magenta",
                )
            )
            if event.to_phase != "complete":
                self._print_phase_rule(event.to_phase)
            else:
                self._active_phase = event.to_phase
            return

        if isinstance(event, ErrorEvent):
            self._ensure_phase(event.phase)
            render_error_panel(
                self.console,
                title=f"Error · {_phase_name(event.phase)} · iter {event.iteration}",
                message=event.error,
            )
            return

    def _ensure_phase(self, phase: str) -> None:
        if phase != self._active_phase:
            self._print_phase_rule(phase)

    def _print_phase_rule(self, phase: str) -> None:
        self.console.print(
            Rule(
                title=f"Phase: {_phase_name(phase)}",
                style=f"bold {_PHASE_STYLES.get(phase, 'white')}",
            )
        )
        self._active_phase = phase

    def _render_chunk(self, event: ToolOutputChunkEvent) -> None:
        stream_style = "green" if event.stream == "stdout" else "red"
        lines = event.chunk.splitlines() or [event.chunk]
        for line in lines:
            text = Text()
            text.append(f"{event.tool_name} {event.stream} │ ", style=f"bold {stream_style}")
            text.append(line)
            self.console.print(text, soft_wrap=True)


def render_error_panel(
    console: Console,
    *,
    title: str,
    message: str,
    details: Iterable[str] | None = None,
) -> None:
    """Render a standardized CLI error panel."""
    body = [message]
    if details:
        body.extend(f"- {detail}" for detail in details)
    console.print(Panel("\n".join(body), title=title, border_style="red"))


def redact_value(value: Any) -> Any:
    """Recursively redact credential-bearing URLs in display-bound values."""
    if isinstance(value, str):
        return redact_string(value)
    if isinstance(value, dict):
        return {key: redact_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    return value


def redact_string(value: str) -> str:
    """Remove username/password components from URLs before display."""
    if "://" not in value:
        return value

    split = urlsplit(value)
    if split.username is None and split.password is None:
        return value

    netloc = split.hostname or ""
    if split.port is not None:
        netloc = f"{netloc}:{split.port}"

    return urlunsplit((split.scheme, netloc, split.path, split.query, split.fragment))


def _phase_name(value: str | Phase) -> str:
    phase_value = value.value if isinstance(value, Phase) else value
    return _PHASE_LABELS.get(phase_value, phase_value.replace("_", " ").title())
