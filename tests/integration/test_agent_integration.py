"""Integration tests — real LLM + real Docker agent loop.

Proves the ReAct agent autonomously reasons through the Recon phase:
selects nmap, executes it in Docker, and accumulates state.  This is the
primary risk-retirement proof for "agent loop quality".

Run with: pytest tests/integration/test_agent_integration.py -m integration -v
"""

from __future__ import annotations

import pytest

from oxpwn.agent.events import AgentEventCallback, ToolCallEvent, ToolResultEvent
from oxpwn.agent.react import ReactAgent
from oxpwn.agent.tools import ToolRegistry, register_default_tools
from oxpwn.core.models import Phase, ScanState

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Event collector for test introspection
# ---------------------------------------------------------------------------


class _EventCollector:
    """Collect agent events for post-run assertions."""

    def __init__(self) -> None:
        self.events: list = []

    async def on_event(self, event) -> None:  # noqa: ANN001
        self.events.append(event)


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


@pytest.mark.timeout(180)
@pytest.mark.asyncio
async def test_agent_recon_phase_with_real_llm(llm_client, docker_sandbox):
    """Agent autonomously runs nmap during Recon via real LLM reasoning.

    Structural assertions (not exact LLM output):
      a) At least one tool_result with tool_name="nmap"
      b) That tool_result has parsed_output (not None)
      c) phases_completed contains Phase.recon  OR  current_phase advanced past recon
      d) total_tokens > 0 (LLM was actually called)
    """
    # Build a fresh agent with event collector for this test
    collector = _EventCollector()
    registry = ToolRegistry()
    register_default_tools(registry)
    agent = ReactAgent(
        llm_client,
        docker_sandbox,
        registry,
        max_iterations_per_phase=8,
        event_callback=collector,
    )

    # Use localhost inside the container — nmap runs in the sandbox,
    # so "localhost" refers to the container's own loopback.
    # Port 80 won't be open, but nmap will still produce structured XML.
    scan_state = ScanState(target="localhost", current_phase=Phase.recon)

    # Run only the recon phase by limiting _PHASE_ORDER temporarily is not
    # clean; instead just run the full agent and check recon happened.
    result = await agent.run(scan_state)

    # --- Assertion (a): at least one nmap tool_result ---
    nmap_results = [tr for tr in result.tool_results if tr.tool_name == "nmap"]
    assert len(nmap_results) >= 1, (
        f"Expected at least one nmap tool_result, got {len(nmap_results)}. "
        f"All tool_results: {[tr.tool_name for tr in result.tool_results]}"
    )

    # --- Assertion (b): parsed_output present ---
    nmap_with_parsed = [tr for tr in nmap_results if tr.parsed_output is not None]
    assert len(nmap_with_parsed) >= 1, (
        "Expected at least one nmap result with parsed_output. "
        f"Exit codes: {[tr.exit_code for tr in nmap_results]}, "
        f"stdout snippets: {[tr.stdout[:100] for tr in nmap_results]}"
    )

    # --- Assertion (c): recon phase completed ---
    recon_completed = Phase.recon in result.phases_completed
    past_recon = result.current_phase != Phase.recon
    assert recon_completed or past_recon, (
        f"Recon phase not completed. "
        f"phases_completed={result.phases_completed}, "
        f"current_phase={result.current_phase}"
    )

    # --- Assertion (d): LLM was actually called ---
    assert result.total_tokens > 0, (
        f"Expected total_tokens > 0, got {result.total_tokens}"
    )

    # --- Bonus: event collector received tool events ---
    tool_call_events = [e for e in collector.events if isinstance(e, ToolCallEvent)]
    tool_result_events = [e for e in collector.events if isinstance(e, ToolResultEvent)]
    assert len(tool_call_events) >= 1, "Expected at least one ToolCallEvent"
    assert len(tool_result_events) >= 1, "Expected at least one ToolResultEvent"
