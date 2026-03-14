"""Pydantic data models shared across all 0xpwn subsystems."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Phase(StrEnum):
    """Penetration testing workflow phases."""

    recon = "recon"
    scanning = "scanning"
    exploitation = "exploitation"
    validation = "validation"
    reporting = "reporting"


class Severity(StrEnum):
    """Finding severity levels."""

    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class Finding(BaseModel):
    """A single security finding produced during a scan."""

    title: str
    severity: Severity
    description: str
    url: str
    evidence: str
    cve_id: str | None = None
    cvss: float | None = None
    cwe_id: str | None = None
    remediation: str | None = None
    raw_output: str | None = None
    tool_name: str

    @field_validator("cvss")
    @classmethod
    def cvss_in_range(cls, v: float | None) -> float | None:
        if v is not None and (v < 0.0 or v > 10.0):
            msg = "CVSS score must be between 0.0 and 10.0"
            raise ValueError(msg)
        return v


class ToolResult(BaseModel):
    """Result of running an external security tool."""

    tool_name: str
    command: str
    stdout: str
    stderr: str
    exit_code: int
    parsed_output: dict[str, Any] | None = None
    duration_ms: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("duration_ms")
    @classmethod
    def duration_non_negative(cls, v: int) -> int:
        if v < 0:
            msg = "duration_ms must be non-negative"
            raise ValueError(msg)
        return v


class TokenUsage(BaseModel):
    """Token consumption breakdown for an LLM call."""

    input: int = Field(ge=0)
    output: int = Field(ge=0)
    total: int = Field(ge=0)


class LLMResponse(BaseModel):
    """Response from an LLM provider via LiteLLM."""

    content: str
    model: str
    tokens_used: TokenUsage
    cost: float = Field(ge=0.0)
    latency_ms: int = Field(ge=0)
    tool_calls: list[dict[str, Any]] | None = None
    raw_response: dict[str, Any] | None = None


class ScanState(BaseModel):
    """Mutable state tracking a full penetration test run."""

    target: str
    phases_completed: list[Phase] = Field(default_factory=list)
    current_phase: Phase = Phase.recon
    findings: list[Finding] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = None
    total_cost: float = Field(default=0.0, ge=0.0)
    total_tokens: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_finding(self, finding: Finding) -> None:
        """Append a finding to the scan."""
        self.findings.append(finding)

    def add_tool_result(self, result: ToolResult) -> None:
        """Append a tool result to the scan."""
        self.tool_results.append(result)

    def advance_phase(self, next_phase: Phase) -> None:
        """Mark current phase complete and move to the next."""
        if self.current_phase not in self.phases_completed:
            self.phases_completed.append(self.current_phase)
        self.current_phase = next_phase

    def record_llm_usage(self, response: LLMResponse) -> None:
        """Accumulate cost and token usage from an LLM call."""
        self.total_cost += response.cost
        self.total_tokens += response.tokens_used.total
