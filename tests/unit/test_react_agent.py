"""Unit tests for ReactAgent with mocked LLMClient and DockerSandbox."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from oxpwn.agent.events import (
    AgentEvent,
    ErrorEvent,
    PhaseTransitionEvent,
    ReasoningEvent,
    ToolCallEvent,
    ToolOutputChunkEvent,
    ToolResultEvent,
)
from oxpwn.agent.exceptions import AgentMaxIterationsError
from oxpwn.agent.react import ReactAgent
from oxpwn.agent.tools import ToolRegistry, register_default_tools
from oxpwn.core.models import LLMResponse, Phase, ScanState, TokenUsage, ToolResult


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _token_usage() -> TokenUsage:
    return TokenUsage(input=100, output=50, total=150)


def _llm_response(
    content: str = "",
    tool_calls: list[dict[str, Any]] | None = None,
) -> LLMResponse:
    """Build a minimal LLMResponse for testing."""
    return LLMResponse(
        content=content,
        model="test-model",
        tokens_used=_token_usage(),
        cost=0.001,
        latency_ms=200,
        tool_calls=tool_calls,
    )


def _tool_call(
    name: str,
    arguments: dict[str, Any],
    call_id: str = "call_1",
) -> dict[str, Any]:
    """Build a tool call dict in OpenAI format."""
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(arguments),
        },
    }


def _tool_result(**overrides) -> ToolResult:
    defaults = {
        "tool_name": "nmap",
        "command": "nmap -sV 10.0.0.1",
        "stdout": "PORT 80/tcp open http",
        "stderr": "",
        "exit_code": 0,
        "duration_ms": 500,
        "parsed_output": {"hosts": [{"address": "10.0.0.1", "ports": [{"port_id": 80}]}]},
    }
    defaults.update(overrides)
    return ToolResult(**defaults)


def _make_scan_state(target: str = "10.0.0.1") -> ScanState:
    return ScanState(target=target, current_phase=Phase.recon)


EXPECTED_DEFAULT_TOOLS = ["nmap", "httpx", "subfinder", "nuclei", "ffuf"]


def _make_registry() -> ToolRegistry:
    """Registry with a mock nmap tool."""
    registry = ToolRegistry()

    class MockNmapExecutor:
        def __init__(self, sandbox):
            self.sandbox = sandbox

        async def run(self, target: str, ports: str | None = None, flags: str = "-sV") -> ToolResult:
            return _tool_result(command=f"nmap {flags} {target}")

    registry.register(
        name="nmap",
        description="Run nmap scan.",
        parameters_schema={
            "type": "object",
            "properties": {"target": {"type": "string"}},
            "required": ["target"],
        },
        executor_factory=lambda s: MockNmapExecutor(s),
    )
    return registry


def _make_streaming_registry() -> ToolRegistry:
    """Registry with a mock nmap tool that emits live stdout/stderr chunks."""
    registry = ToolRegistry()

    class MockStreamingNmapExecutor:
        def __init__(self, sandbox):
            self.sandbox = sandbox

        async def run(
            self,
            target: str,
            ports: str | None = None,
            flags: str = "-sV",
            *,
            output_sink=None,
        ) -> ToolResult:
            if output_sink is not None:
                await output_sink(chunk="chunk stdout", stream="stdout")
                await output_sink(chunk="chunk stderr", stream="stderr")

            return _tool_result(
                command=f"nmap {flags} {target}",
                stdout="chunk stdout",
                stderr="chunk stderr",
            )

    registry.register(
        name="nmap",
        description="Run nmap scan.",
        parameters_schema={
            "type": "object",
            "properties": {"target": {"type": "string"}},
            "required": ["target"],
        },
        executor_factory=lambda s: MockStreamingNmapExecutor(s),
    )
    return registry


def _make_httpx_registry() -> ToolRegistry:
    """Registry with a mock httpx tool for parsed_output contract tests."""
    registry = ToolRegistry()

    class MockHttpxExecutor:
        def __init__(self, sandbox):
            self.sandbox = sandbox

        async def run(
            self,
            targets: str,
            path: str | None = None,
            follow_redirects: bool = False,
        ) -> ToolResult:
            path_suffix = path or ""
            redirect_flag = " --follow-redirects" if follow_redirects else ""
            return _tool_result(
                tool_name="httpx",
                command=f"httpx {targets}{path_suffix}{redirect_flag}",
                stdout="httpx raw stdout that should not be sent back to the LLM",
                parsed_output={
                    "count": 1,
                    "services": [
                        {
                            "url": f"http://{targets}{path_suffix}",
                            "status_code": 200,
                            "title": "Mock Admin",
                        },
                    ],
                },
            )

    registry.register(
        name="httpx",
        description="Probe HTTP services.",
        parameters_schema={
            "type": "object",
            "properties": {"targets": {"type": "string"}},
            "required": ["targets"],
        },
        executor_factory=lambda s: MockHttpxExecutor(s),
    )
    return registry


class EventCollector:
    """Collects events for assertion."""

    def __init__(self):
        self.events: list[AgentEvent] = []

    async def on_event(self, event: AgentEvent) -> None:
        self.events.append(event)

    def of_type(self, cls: type[Any]) -> list[Any]:
        return [e for e in self.events if isinstance(e, cls)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestReactAgentToolDispatch:
    """Agent calls LLM, dispatches tool, feeds result back."""

    @pytest.mark.asyncio
    async def test_tool_call_then_phase_complete(self):
        """Iteration 1: tool call → dispatch → result. Iteration 2: no tool call → phase done."""
        llm = AsyncMock()
        llm.complete = AsyncMock(side_effect=[
            # Recon iter 1: call nmap
            _llm_response(
                content="Let me scan the target.",
                tool_calls=[_tool_call("nmap", {"target": "10.0.0.1"})],
            ),
            # Recon iter 2: no tool call = phase complete
            _llm_response(content="Recon complete. Found port 80 open."),
            # Scanning iter 1: no tool call = phase complete immediately
            _llm_response(content="No further scanning needed."),
            # Exploitation: phase complete
            _llm_response(content="Exploitation done."),
            # Validation: phase complete
            _llm_response(content="Validation done."),
            # Reporting: phase complete
            _llm_response(content="Reporting done."),
        ])

        sandbox = MagicMock()
        state = _make_scan_state()
        agent = ReactAgent(llm, sandbox, _make_registry(), max_iterations_per_phase=5)

        result = await agent.run(state)

        # LLM was called: 2 for recon + 1 for scanning + 3 for remaining = 6
        assert llm.complete.call_count == 6

        # Tool result was accumulated
        assert len(result.tool_results) == 1
        assert result.tool_results[0].tool_name == "nmap"

        # All phases completed
        assert Phase.recon in result.phases_completed
        assert Phase.scanning in result.phases_completed
        assert Phase.exploitation in result.phases_completed
        assert Phase.validation in result.phases_completed
        assert Phase.reporting in result.phases_completed

    @pytest.mark.asyncio
    async def test_tool_call_messages_have_matching_ids(self):
        """The tool result message must carry the same tool_call_id as the assistant's tool call."""
        llm = AsyncMock()
        call_id = "call_abc123"

        responses = [
            _llm_response(
                content="Scanning.",
                tool_calls=[_tool_call("nmap", {"target": "10.0.0.1"}, call_id=call_id)],
            ),
            _llm_response(content="Recon done."),
            _llm_response(content="Scanning done."),
            _llm_response(content="Exploitation done."),
            _llm_response(content="Validation done."),
            _llm_response(content="Reporting done."),
        ]
        llm.complete = AsyncMock(side_effect=responses)

        sandbox = MagicMock()
        agent = ReactAgent(llm, sandbox, _make_registry(), max_iterations_per_phase=5)
        await agent.run(_make_scan_state())

        # Second call to LLM (recon iter 2) should have the tool result in messages
        second_call_messages = llm.complete.call_args_list[1][0][0]

        tool_msgs = [m for m in second_call_messages if m.get("role") == "tool"]
        assert len(tool_msgs) == 1
        assert tool_msgs[0]["tool_call_id"] == call_id
        assert tool_msgs[0]["name"] == "nmap"


class TestPhaseTransition:
    """Non-tool-call response signals phase completion."""

    @pytest.mark.asyncio
    async def test_no_tool_call_triggers_transition(self):
        llm = AsyncMock()
        llm.complete = AsyncMock(side_effect=[
            # Recon: immediate phase complete
            _llm_response(content="Nothing to scan."),
            # Scanning: immediate phase complete
            _llm_response(content="Done."),
            # Exploitation: immediate phase complete
            _llm_response(content="Done."),
            # Validation: immediate phase complete
            _llm_response(content="Done."),
            # Reporting: immediate phase complete
            _llm_response(content="Done."),
        ])

        sandbox = MagicMock()
        state = _make_scan_state()
        agent = ReactAgent(llm, sandbox, _make_registry(), max_iterations_per_phase=5)

        result = await agent.run(state)

        assert Phase.recon in result.phases_completed
        assert Phase.scanning in result.phases_completed
        assert Phase.exploitation in result.phases_completed
        assert Phase.validation in result.phases_completed
        assert Phase.reporting in result.phases_completed
        # No tool results since no tools were called
        assert len(result.tool_results) == 0

    @pytest.mark.asyncio
    async def test_scan_state_advances_phase(self):
        llm = AsyncMock()
        llm.complete = AsyncMock(side_effect=[
            _llm_response(content="Recon done."),
            _llm_response(content="Scanning done."),
            _llm_response(content="Exploitation done."),
            _llm_response(content="Validation done."),
            _llm_response(content="Reporting done."),
        ])

        sandbox = MagicMock()
        state = _make_scan_state()
        agent = ReactAgent(llm, sandbox, _make_registry())

        await agent.run(state)

        # All phases should be completed
        assert state.phases_completed == [
            Phase.recon, Phase.scanning, Phase.exploitation,
            Phase.validation, Phase.reporting,
        ]


class TestMaxIterations:
    """Exceeding iteration budget raises AgentMaxIterationsError."""

    @pytest.mark.asyncio
    async def test_raises_on_budget_exhaustion(self):
        llm = AsyncMock()
        # Always return tool calls, never complete the phase
        llm.complete = AsyncMock(
            return_value=_llm_response(
                content="Scanning more.",
                tool_calls=[_tool_call("nmap", {"target": "10.0.0.1"})],
            ),
        )

        sandbox = MagicMock()
        agent = ReactAgent(llm, sandbox, _make_registry(), max_iterations_per_phase=3)

        with pytest.raises(AgentMaxIterationsError) as exc_info:
            await agent.run(_make_scan_state())

        assert exc_info.value.phase == "recon"
        assert exc_info.value.iteration == 3


class TestMultipleToolCalls:
    """Multiple tool calls in a single LLM response."""

    @pytest.mark.asyncio
    async def test_sequential_dispatch(self):
        llm = AsyncMock()
        llm.complete = AsyncMock(side_effect=[
            # Two tool calls in one response
            _llm_response(
                content="Running two scans.",
                tool_calls=[
                    _tool_call("nmap", {"target": "10.0.0.1"}, call_id="call_1"),
                    _tool_call("nmap", {"target": "10.0.0.2"}, call_id="call_2"),
                ],
            ),
            _llm_response(content="Recon done."),
            _llm_response(content="Scanning done."),
            _llm_response(content="Exploitation done."),
            _llm_response(content="Validation done."),
            _llm_response(content="Reporting done."),
        ])

        sandbox = MagicMock()
        state = _make_scan_state()
        agent = ReactAgent(llm, sandbox, _make_registry(), max_iterations_per_phase=5)

        await agent.run(state)

        # Both tool calls were dispatched
        assert len(state.tool_results) == 2

        # Both tool result messages in next LLM call
        second_call_messages = llm.complete.call_args_list[1][0][0]
        tool_msgs = [m for m in second_call_messages if m.get("role") == "tool"]
        assert len(tool_msgs) == 2
        assert {m["tool_call_id"] for m in tool_msgs} == {"call_1", "call_2"}


class TestMalformedToolCall:
    """Malformed tool call arguments are handled gracefully."""

    @pytest.mark.asyncio
    async def test_bad_arguments_skipped(self):
        """Malformed args should not crash the agent — dispatch with empty dict."""
        llm = AsyncMock()
        llm.complete = AsyncMock(side_effect=[
            _llm_response(
                content="Trying tool.",
                tool_calls=[{
                    "id": "call_bad",
                    "type": "function",
                    "function": {
                        "name": "nmap",
                        "arguments": "not valid json {{{",
                    },
                }],
            ),
            _llm_response(content="Recon done."),
            _llm_response(content="Scanning done."),
            _llm_response(content="Exploitation done."),
            _llm_response(content="Validation done."),
            _llm_response(content="Reporting done."),
        ])

        sandbox = MagicMock()
        state = _make_scan_state()

        # Mock executor that handles missing target gracefully
        registry = ToolRegistry()

        class LenientExecutor:
            def __init__(self, sandbox):
                pass

            async def run(self, **kwargs) -> ToolResult:
                return _tool_result(tool_name="nmap")

        registry.register("nmap", "Nmap.", {"type": "object", "properties": {}}, lambda s: LenientExecutor(s))

        agent = ReactAgent(llm, sandbox, registry, max_iterations_per_phase=5)
        result = await agent.run(state)

        # Agent completed without crashing
        assert Phase.recon in result.phases_completed


class TestEventCallbacks:
    """Event callback receives events in proper order."""

    @pytest.mark.asyncio
    async def test_events_emitted_in_order(self):
        llm = AsyncMock()
        llm.complete = AsyncMock(side_effect=[
            _llm_response(
                content="Running nmap.",
                tool_calls=[_tool_call("nmap", {"target": "10.0.0.1"})],
            ),
            _llm_response(content="Recon complete."),
            _llm_response(content="Scanning complete."),
            _llm_response(content="Exploitation complete."),
            _llm_response(content="Validation complete."),
            _llm_response(content="Reporting complete."),
        ])

        sandbox = MagicMock()
        collector = EventCollector()
        agent = ReactAgent(
            llm,
            sandbox,
            _make_streaming_registry(),
            max_iterations_per_phase=5,
            event_callback=collector,
        )
        await agent.run(_make_scan_state())

        reasoning_events = collector.of_type(ReasoningEvent)
        chunk_events = collector.of_type(ToolOutputChunkEvent)

        assert len(reasoning_events) == 6
        assert reasoning_events[0].content == "Running nmap."
        assert len(collector.of_type(ToolCallEvent)) >= 1
        assert len(collector.of_type(ToolResultEvent)) >= 1
        assert len(collector.of_type(PhaseTransitionEvent)) >= 1
        assert [(event.stream, event.chunk) for event in chunk_events] == [
            ("stdout", "chunk stdout"),
            ("stderr", "chunk stderr"),
        ]
        assert all(event.tool_name == "nmap" for event in chunk_events)
        assert all(event.phase == "recon" for event in chunk_events)
        assert all(event.iteration == 1 for event in chunk_events)

        # First tool-turn ordering is deterministic: reasoning -> dispatch -> streamed chunks -> result.
        assert [type(event) for event in collector.events[:5]] == [
            ReasoningEvent,
            ToolCallEvent,
            ToolOutputChunkEvent,
            ToolOutputChunkEvent,
            ToolResultEvent,
        ]

    @pytest.mark.asyncio
    async def test_no_callback_does_not_crash(self):
        """Agent works fine without an event callback."""
        llm = AsyncMock()
        llm.complete = AsyncMock(side_effect=[
            _llm_response(content="Done."),
            _llm_response(content="Done."),
            _llm_response(content="Done."),
            _llm_response(content="Done."),
            _llm_response(content="Done."),
        ])

        sandbox = MagicMock()
        agent = ReactAgent(llm, sandbox, _make_registry(), event_callback=None)
        result = await agent.run(_make_scan_state())

        assert Phase.recon in result.phases_completed

    @pytest.mark.asyncio
    async def test_broken_callback_does_not_crash_agent(self):
        """If the callback raises, the agent continues."""

        class BrokenCallback:
            async def on_event(self, event):
                raise RuntimeError("callback exploded")

        llm = AsyncMock()
        llm.complete = AsyncMock(side_effect=[
            _llm_response(content="Done."),
            _llm_response(content="Done."),
            _llm_response(content="Done."),
            _llm_response(content="Done."),
            _llm_response(content="Done."),
        ])

        sandbox = MagicMock()
        agent = ReactAgent(llm, sandbox, _make_registry(), event_callback=BrokenCallback())
        # Should complete without raising
        result = await agent.run(_make_scan_state())
        assert Phase.recon in result.phases_completed


class TestScanStateAccumulation:
    """ScanState accumulates tool results and records LLM usage."""

    @pytest.mark.asyncio
    async def test_llm_usage_accumulated(self):
        llm = AsyncMock()
        llm.complete = AsyncMock(side_effect=[
            _llm_response(content="Done."),
            _llm_response(content="Done."),
            _llm_response(content="Done."),
            _llm_response(content="Done."),
            _llm_response(content="Done."),
        ])

        sandbox = MagicMock()
        state = _make_scan_state()
        agent = ReactAgent(llm, sandbox, _make_registry())
        await agent.run(state)

        # 5 LLM calls × 0.001 cost each
        assert state.total_cost == pytest.approx(0.005)
        # 5 LLM calls × 150 tokens each
        assert state.total_tokens == 750

    @pytest.mark.asyncio
    async def test_parsed_output_fed_to_llm(self):
        """Tool output sent to LLM should be JSON from parsed_output, not raw stdout."""
        llm = AsyncMock()
        llm.complete = AsyncMock(side_effect=[
            _llm_response(
                content="Scanning.",
                tool_calls=[_tool_call("nmap", {"target": "10.0.0.1"})],
            ),
            _llm_response(content="Recon done."),
            _llm_response(content="Scanning done."),
            _llm_response(content="Exploitation done."),
            _llm_response(content="Validation done."),
            _llm_response(content="Reporting done."),
        ])

        sandbox = MagicMock()
        agent = ReactAgent(llm, sandbox, _make_registry(), max_iterations_per_phase=5)
        await agent.run(_make_scan_state())

        # Check the tool result message content in the second LLM call
        second_call_messages = llm.complete.call_args_list[1][0][0]
        tool_msg = next(m for m in second_call_messages if m.get("role") == "tool")

        # Content should be JSON (parsed_output), not raw stdout
        parsed = json.loads(tool_msg["content"])
        assert "hosts" in parsed

    @pytest.mark.asyncio
    async def test_non_nmap_parsed_output_fed_to_llm(self):
        """The parsed_output dict contract should hold for the newly registered tool types too."""
        llm = AsyncMock()
        llm.complete = AsyncMock(side_effect=[
            _llm_response(
                content="Probe the web service.",
                tool_calls=[_tool_call("httpx", {"targets": "127.0.0.1:18080", "path": "/admin/"})],
            ),
            _llm_response(content="Recon done."),
            _llm_response(content="Scanning done."),
            _llm_response(content="Exploitation done."),
            _llm_response(content="Validation done."),
            _llm_response(content="Reporting done."),
        ])

        sandbox = MagicMock()
        agent = ReactAgent(llm, sandbox, _make_httpx_registry(), max_iterations_per_phase=5)
        await agent.run(_make_scan_state(target="127.0.0.1:18080"))

        second_call_messages = llm.complete.call_args_list[1][0][0]
        tool_msg = next(m for m in second_call_messages if m.get("role") == "tool")

        parsed = json.loads(tool_msg["content"])
        assert parsed["count"] == 1
        assert parsed["services"][0]["status_code"] == 200
        assert tool_msg["name"] == "httpx"
        assert "raw stdout" not in tool_msg["content"]


class TestDefaultRegistryPromptWiring:
    """The default registry inventory and prompt guidance stay agent-visible."""

    @pytest.mark.asyncio
    async def test_default_registry_tools_and_phase_hints_reach_the_llm(self):
        llm = AsyncMock()
        llm.complete = AsyncMock(side_effect=[
            _llm_response(content="Recon done."),
            _llm_response(content="Scanning done."),
            _llm_response(content="Exploitation done."),
            _llm_response(content="Validation done."),
            _llm_response(content="Reporting done."),
        ])

        sandbox = MagicMock()
        registry = ToolRegistry()
        register_default_tools(registry)
        agent = ReactAgent(llm, sandbox, registry, max_iterations_per_phase=5)

        await agent.run(_make_scan_state(target="https://example.com"))

        first_call = llm.complete.call_args_list[0]
        second_call = llm.complete.call_args_list[1]

        recon_system_prompt = first_call.args[0][0]["content"]
        scanning_system_prompt = second_call.args[0][0]["content"]
        tool_names = [schema["function"]["name"] for schema in first_call.kwargs["tools"]]

        assert tool_names == EXPECTED_DEFAULT_TOOLS
        assert "Available tools: nmap, httpx, subfinder, nuclei, ffuf" in recon_system_prompt
        assert all(tool in recon_system_prompt for tool in ("subfinder", "httpx", "nmap"))
        assert all(tool in scanning_system_prompt for tool in ("nuclei", "ffuf", "nmap"))


# ---------------------------------------------------------------------------
# S08: Phase order and guidance coverage tests
# ---------------------------------------------------------------------------


class TestPhaseOrderComplete:
    """Verify _PHASE_ORDER contains all 5 phases in the correct order."""

    def test_phase_order_has_five_phases(self):
        from oxpwn.agent.react import _PHASE_ORDER

        assert _PHASE_ORDER == [
            Phase.recon,
            Phase.scanning,
            Phase.exploitation,
            Phase.validation,
            Phase.reporting,
        ]

    def test_phase_order_matches_all_enum_members(self):
        from oxpwn.agent.react import _PHASE_ORDER

        assert set(_PHASE_ORDER) == set(Phase)
        assert len(_PHASE_ORDER) == len(Phase)


class TestPhaseGuidanceCoverage:
    """Verify _PHASE_GUIDANCE has entries for all 5 phases."""

    def test_all_phases_have_guidance(self):
        from oxpwn.agent.prompts import _PHASE_GUIDANCE

        for phase in Phase:
            assert phase in _PHASE_GUIDANCE, f"Missing guidance for {phase.value}"

    def test_no_phase_falls_through_to_default(self):
        from oxpwn.agent.prompts import _DEFAULT_GUIDANCE, _PHASE_GUIDANCE

        for phase in Phase:
            guidance = _PHASE_GUIDANCE.get(phase)
            assert guidance is not None, f"Phase {phase.value} has no guidance entry"
            assert guidance != _DEFAULT_GUIDANCE, f"Phase {phase.value} uses default guidance"

    def test_exploitation_guidance_content(self):
        from oxpwn.agent.prompts import _PHASE_GUIDANCE

        guidance = _PHASE_GUIDANCE[Phase.exploitation]
        assert "exploitation" in guidance.lower() or "exploit" in guidance.lower()

    def test_validation_guidance_content(self):
        from oxpwn.agent.prompts import _PHASE_GUIDANCE

        guidance = _PHASE_GUIDANCE[Phase.validation]
        assert "false positive" in guidance.lower() or "confirm" in guidance.lower()

    def test_reporting_guidance_content(self):
        from oxpwn.agent.prompts import _PHASE_GUIDANCE

        guidance = _PHASE_GUIDANCE[Phase.reporting]
        assert "summary" in guidance.lower() or "report" in guidance.lower()
