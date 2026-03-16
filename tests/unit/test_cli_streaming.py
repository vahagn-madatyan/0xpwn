"""Unit tests for Rich streaming callback rendering."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from rich.console import Console

from oxpwn.agent.events import (
    ErrorEvent,
    PhaseTransitionEvent,
    ReasoningEvent,
    ToolCallEvent,
    ToolOutputChunkEvent,
    ToolResultEvent,
)
from oxpwn.cli.streaming import RichStreamingCallback
from oxpwn.core.models import Phase, ScanState


@pytest.mark.asyncio
async def test_rich_streaming_callback_renders_agent_events_in_order() -> None:
    console = Console(record=True, width=120, color_system=None, force_terminal=False)
    callback = RichStreamingCallback(console)

    start_time = datetime(2026, 3, 14, 21, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(seconds=6)
    state = ScanState(
        target="https://alice:secret@example.com/app",
        current_phase=Phase.scanning,
        phases_completed=[Phase.recon, Phase.scanning],
        total_tokens=321,
        total_cost=0.0421,
        start_time=start_time,
        end_time=end_time,
    )

    callback.render_scan_start(
        target=state.target,
        model="gemini/gemini-2.5-flash",
        sandbox_image="oxpwn-sandbox:dev",
        network_mode="bridge",
        max_iterations_per_phase=8,
        scan_id="scan-test-01",
    )

    await callback.on_event(
        ReasoningEvent(
            content="Start with service discovery before deeper probing.",
            phase="recon",
            iteration=1,
        )
    )
    await callback.on_event(
        ToolCallEvent(
            tool_name="httpx",
            arguments={"targets": ["https://alice:secret@example.com/app"], "path": "/admin"},
            phase="recon",
            iteration=1,
        )
    )
    await callback.on_event(
        ToolOutputChunkEvent(
            tool_name="httpx",
            stream="stdout",
            chunk="https://example.com/app/admin [200]\nsecond line",
            phase="recon",
            iteration=1,
        )
    )
    await callback.on_event(
        ToolOutputChunkEvent(
            tool_name="httpx",
            stream="stderr",
            chunk="warning: response body truncated",
            phase="recon",
            iteration=1,
        )
    )
    await callback.on_event(
        ToolResultEvent(
            tool_name="httpx",
            result_summary='{"count": 1, "services": [{"url": "https://example.com/app/admin", "status_code": 200}]}',
            duration_ms=187,
            phase="recon",
            iteration=1,
        )
    )
    await callback.on_event(
        PhaseTransitionEvent(
            from_phase="recon",
            to_phase="scanning",
            summary="Recon complete with one live admin surface.",
        )
    )
    await callback.on_event(
        ErrorEvent(
            error="nuclei exceeded its template budget",
            phase="scanning",
            iteration=2,
        )
    )

    callback.render_final_summary(state)

    output = console.export_text()

    assert "0xpwn scan" in output
    assert "Scan configuration" in output
    assert "Phase: Recon" in output
    assert "Reasoning · Recon · iter 1" in output
    assert "Tool dispatch · httpx" in output
    assert "httpx stdout │ https://example.com/app/admin [200]" in output
    assert "httpx stdout │ second line" in output
    assert "httpx stderr │ warning: response body truncated" in output
    assert "Tool result · httpx · 187ms" in output
    assert "Phase complete · Recon → Scanning" in output
    assert "Recon complete with one live admin surface." in output
    assert "Error · Scanning · iter 2" in output
    assert "Scan summary" in output
    assert "Phases completed: Recon, Scanning" in output
    assert "Duration: 6.0s" in output

    assert output.index("Reasoning · Recon · iter 1") < output.index("Tool dispatch · httpx")
    assert output.index("Tool dispatch · httpx") < output.index("httpx stdout │ https://example.com/app/admin [200]")
    assert output.index("httpx stderr │ warning: response body truncated") < output.index("Tool result · httpx · 187ms")
    assert output.index("Tool result · httpx · 187ms") < output.index("Phase complete · Recon → Scanning")
    assert output.index("Phase complete · Recon → Scanning") < output.index("Error · Scanning · iter 2")
    assert output.index("Error · Scanning · iter 2") < output.index("Scan summary")

    assert "alice:secret@" not in output
    assert "secret" not in output
