"""ReAct agent loop: Reason → Act → Observe over LLM tool calls."""

from __future__ import annotations

import json
from typing import Any

import structlog

from oxpwn.agent.events import (
    AgentEventCallback,
    ErrorEvent,
    PhaseTransitionEvent,
    ReasoningEvent,
    ToolCallEvent,
    ToolOutputChunkEvent,
    ToolOutputStream,
    ToolResultEvent,
)
from oxpwn.agent.exceptions import AgentMaxIterationsError
from oxpwn.agent.prompts import build_phase_summary, build_system_prompt
from oxpwn.agent.tools import ToolOutputSink, ToolRegistry, parse_tool_arguments
from oxpwn.core.models import Phase, ScanState
from oxpwn.llm.client import LLMClient
from oxpwn.sandbox.docker import DockerSandbox

logger = structlog.get_logger("oxpwn.agent")

# Phases the agent iterates through (S03 scope: recon + scanning only)
_PHASE_ORDER: list[Phase] = [Phase.recon, Phase.scanning]

# Max chars of tool output to feed back to the LLM
_MAX_TOOL_OUTPUT_CHARS = 4000


class ReactAgent:
    """Autonomous ReAct agent that iterates LLM → dispatch → observe.

    The outer loop walks through phases; the inner loop runs the ReAct cycle
    within each phase until the LLM responds without a tool call (signalling
    phase completion) or the iteration budget is exhausted.

    Usage::

        agent = ReactAgent(llm_client, sandbox, registry)
        final_state = await agent.run(scan_state)
    """

    def __init__(
        self,
        llm_client: LLMClient,
        sandbox: DockerSandbox,
        tool_registry: ToolRegistry,
        *,
        max_iterations_per_phase: int = 10,
        event_callback: AgentEventCallback | None = None,
    ) -> None:
        self._llm = llm_client
        self._sandbox = sandbox
        self._registry = tool_registry
        self._max_iterations = max_iterations_per_phase
        self._callback = event_callback

    async def run(self, scan_state: ScanState) -> ScanState:
        """Execute the agent loop across all phases.

        Args:
            scan_state: Mutable scan state to accumulate results into.

        Returns:
            The same ``ScanState`` instance, mutated with tool results,
            findings, LLM usage, and phase progression.
        """
        total_iterations = 0

        for phase_idx, phase in enumerate(_PHASE_ORDER):
            # Ensure state reflects current phase
            if scan_state.current_phase != phase:
                scan_state.current_phase = phase

            iterations = await self._run_phase(scan_state, phase)
            total_iterations += iterations

            # After the phase loop, advance to next phase if there is one
            if phase_idx < len(_PHASE_ORDER) - 1:
                next_phase = _PHASE_ORDER[phase_idx + 1]
                scan_state.advance_phase(next_phase)

        # Mark final phase as completed
        if scan_state.current_phase not in scan_state.phases_completed:
            scan_state.phases_completed.append(scan_state.current_phase)

        logger.info(
            "agent.complete",
            phases_completed=[p.value for p in scan_state.phases_completed],
            total_iterations=total_iterations,
        )
        return scan_state

    async def _run_phase(self, scan_state: ScanState, phase: Phase) -> int:
        """Run the ReAct inner loop for a single phase.

        Returns the number of iterations consumed.
        """
        conversation: list[dict[str, Any]] = []
        phase_tool_results = []

        for iteration in range(1, self._max_iterations + 1):
            # Build system prompt fresh each iteration (updated findings)
            findings_summary = self._build_findings_summary(scan_state)
            system_msg = build_system_prompt(
                phase=phase,
                target=scan_state.target,
                available_tools=self._registry.tool_names,
                findings_summary=findings_summary,
            )

            # Assemble messages: system + conversation history
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": system_msg},
                *conversation,
            ]

            # Call LLM
            response = await self._llm.complete(
                messages,
                tools=self._registry.get_schemas(),
            )
            scan_state.record_llm_usage(response)

            has_tool_calls = bool(response.tool_calls)
            logger.info(
                "agent.iteration",
                phase=phase.value,
                iteration=iteration,
                has_tool_calls=has_tool_calls,
            )

            if response.content:
                await self._emit(
                    ReasoningEvent(
                        content=response.content,
                        phase=phase.value,
                        iteration=iteration,
                    )
                )

            if not has_tool_calls:
                # No tool calls = phase complete
                findings_dicts = [f.model_dump() for f in scan_state.findings]
                summary = build_phase_summary(phase, phase_tool_results, findings_dicts)

                next_phase_name = self._next_phase_name(phase)
                await self._emit(
                    PhaseTransitionEvent(
                        from_phase=phase.value,
                        to_phase=next_phase_name,
                        summary=summary,
                    )
                )

                logger.info(
                    "agent.phase_transition",
                    from_phase=phase.value,
                    to_phase=next_phase_name,
                )
                return iteration

            # Append assistant message with tool calls
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": response.content or ""}
            if response.tool_calls:
                assistant_msg["tool_calls"] = response.tool_calls
            conversation.append(assistant_msg)

            # Process each tool call sequentially
            for tc in response.tool_calls:
                tool_name = tc["function"]["name"]
                raw_args = tc["function"]["arguments"]
                tool_call_id = tc["id"]

                arguments = parse_tool_arguments(raw_args)

                await self._emit(
                    ToolCallEvent(
                        tool_name=tool_name,
                        arguments=arguments,
                        phase=phase.value,
                        iteration=iteration,
                    )
                )

                try:
                    result = await self._registry.dispatch(
                        tool_name,
                        arguments,
                        self._sandbox,
                        output_sink=self._build_tool_output_sink(
                            tool_name=tool_name,
                            phase=phase.value,
                            iteration=iteration,
                        ),
                    )

                    scan_state.add_tool_result(result)
                    phase_tool_results.append(result)

                    # Format output for LLM: prefer parsed_output, fallback to truncated stdout
                    tool_output = _format_tool_output(result)

                    logger.info(
                        "agent.tool_dispatch",
                        tool_name=tool_name,
                        duration_ms=result.duration_ms,
                    )

                    await self._emit(
                        ToolResultEvent(
                            tool_name=tool_name,
                            result_summary=tool_output[:200],
                            duration_ms=result.duration_ms,
                            phase=phase.value,
                            iteration=iteration,
                        )
                    )

                except KeyError:
                    error_msg = f"Unknown tool: {tool_name!r}"
                    tool_output = json.dumps({"error": error_msg})
                    logger.warning(
                        "agent.tool_dispatch_error",
                        tool_name=tool_name,
                        error=error_msg,
                    )
                    await self._emit(
                        ErrorEvent(
                            error=error_msg,
                            phase=phase.value,
                            iteration=iteration,
                        )
                    )

                except Exception as exc:
                    error_msg = f"Tool execution failed: {exc}"
                    tool_output = json.dumps({"error": error_msg})
                    logger.warning(
                        "agent.tool_dispatch_error",
                        tool_name=tool_name,
                        error=str(exc),
                    )
                    await self._emit(
                        ErrorEvent(
                            error=error_msg,
                            phase=phase.value,
                            iteration=iteration,
                        )
                    )

                # Append tool result message with matching tool_call_id
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": tool_output,
                    }
                )

        # Exhausted iteration budget
        raise AgentMaxIterationsError(
            f"Phase {phase.value!r} exceeded {self._max_iterations} iterations",
            phase=phase.value,
            iteration=self._max_iterations,
        )

    def _build_findings_summary(self, scan_state: ScanState) -> str:
        """Build a condensed summary of current findings for the system prompt."""
        if not scan_state.tool_results and not scan_state.findings:
            return ""

        parts = []
        if scan_state.tool_results:
            parts.append(f"Tools run: {len(scan_state.tool_results)}")
            for tr in scan_state.tool_results[-5:]:  # Last 5 to keep prompt manageable
                status = "ok" if tr.exit_code == 0 else f"exit={tr.exit_code}"
                parts.append(f"  - {tr.tool_name}: {status}")
                if tr.parsed_output:
                    # Include key parsed data
                    summary = json.dumps(tr.parsed_output, default=str)[:300]
                    parts.append(f"    output: {summary}")

        if scan_state.findings:
            parts.append(f"\nFindings: {len(scan_state.findings)}")
            for f in scan_state.findings:
                parts.append(f"  - [{f.severity}] {f.title}")

        return "\n".join(parts)

    def _next_phase_name(self, current: Phase) -> str:
        """Get the name of the next phase, or 'complete' if this is the last."""
        try:
            idx = _PHASE_ORDER.index(current)
            if idx < len(_PHASE_ORDER) - 1:
                return _PHASE_ORDER[idx + 1].value
        except ValueError:
            pass
        return "complete"

    def _build_tool_output_sink(
        self,
        *,
        tool_name: str,
        phase: str,
        iteration: int,
    ) -> ToolOutputSink:
        async def _sink(*, chunk: str, stream: ToolOutputStream) -> None:
            if not chunk:
                return
            await self._emit(
                ToolOutputChunkEvent(
                    tool_name=tool_name,
                    stream=stream,
                    chunk=chunk,
                    phase=phase,
                    iteration=iteration,
                )
            )

        return _sink

    async def _emit(self, event: Any) -> None:
        """Emit an event through the callback, if one is set. Never blocks."""
        if self._callback is not None:
            try:
                await self._callback.on_event(event)
            except Exception:
                # Event callbacks must never break the agent loop
                logger.warning("agent.event_callback_error", event_type=type(event).__name__)


def _format_tool_output(result: Any) -> str:
    """Format a ToolResult's output for feeding back to the LLM.

    Prefers ``parsed_output`` as JSON; falls back to truncated stdout.
    """
    if result.parsed_output is not None:
        return json.dumps(result.parsed_output, default=str)[:_MAX_TOOL_OUTPUT_CHARS]

    stdout = result.stdout or ""
    if len(stdout) > _MAX_TOOL_OUTPUT_CHARS:
        return stdout[:_MAX_TOOL_OUTPUT_CHARS] + "\n... [truncated]"
    return stdout
