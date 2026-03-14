"""Phase-aware system prompt builder for the ReAct agent."""

from __future__ import annotations

from typing import Any

from oxpwn.core.models import Phase, ToolResult


def build_system_prompt(
    phase: Phase,
    target: str,
    available_tools: list[str],
    findings_summary: str,
) -> str:
    """Build the system message for the current agent iteration.

    Args:
        phase: Current penetration testing phase.
        target: Scan target (IP, hostname, URL).
        available_tools: Names of tools the agent can call.
        findings_summary: Condensed text of what has been learned so far.
    """
    tools_list = ", ".join(available_tools) if available_tools else "none"

    phase_guidance = _PHASE_GUIDANCE.get(phase, _DEFAULT_GUIDANCE)

    parts = [
        "You are 0xpwn, an autonomous penetration testing agent.",
        f"Target: {target}",
        f"Current phase: {phase.value}",
        f"Available tools: {tools_list}",
        "",
        "## Phase Guidance",
        phase_guidance,
        "",
        "## Rules",
        "- Call exactly one tool per reasoning step. Explain your reasoning before each call.",
        "- When the current phase is complete, respond with a text summary (no tool call) to signal phase transition.",
        "- Never fabricate scan results. Only report what tools return.",
        "- Operate only against the designated target.",
    ]

    if findings_summary:
        parts.extend(["", "## Findings So Far", findings_summary])

    return "\n".join(parts)


def build_phase_summary(
    phase: Phase,
    tool_results: list[ToolResult],
    findings: list[dict[str, Any]],
) -> str:
    """Produce a condensed summary of a completed phase.

    Used to replace the full conversation history when transitioning phases,
    keeping context size manageable.
    """
    parts = [f"## {phase.value.title()} Phase Summary"]

    if tool_results:
        parts.append(f"\nTools executed: {len(tool_results)}")
        for tr in tool_results:
            status = "success" if tr.exit_code == 0 else f"exit_code={tr.exit_code}"
            parts.append(f"- {tr.tool_name}: {tr.command} ({status}, {tr.duration_ms}ms)")
    else:
        parts.append("\nNo tools were executed.")

    if findings:
        parts.append(f"\nFindings: {len(findings)}")
        for f in findings:
            parts.append(f"- [{f.get('severity', '?')}] {f.get('title', 'untitled')}")
    else:
        parts.append("\nNo findings recorded.")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Phase-specific guidance text
# ---------------------------------------------------------------------------

_PHASE_GUIDANCE: dict[Phase, str] = {
    Phase.recon: (
        "Enumerate the target's attack surface. Discover open ports, running "
        "services, and their versions. Use nmap with service detection (-sV). "
        "Consider scanning common port ranges first, then expanding if needed. "
        "Once you have a clear picture of exposed services, summarize your "
        "findings and move to the next phase."
    ),
    Phase.scanning: (
        "Probe the services discovered during recon for vulnerabilities. "
        "Use targeted scans with appropriate flags and scripts. Focus on "
        "high-value services (HTTP, SSH, databases). Look for version-specific "
        "vulnerabilities, misconfigurations, and default credentials. "
        "Summarize confirmed vulnerabilities when scanning is complete."
    ),
}

_DEFAULT_GUIDANCE = (
    "Continue with the current phase objectives. Use the available tools "
    "to gather information and report findings."
)
