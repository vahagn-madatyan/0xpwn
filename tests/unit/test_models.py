"""Unit tests for 0xpwn core Pydantic models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from oxpwn.core.models import (
    Finding,
    LLMResponse,
    Phase,
    ScanState,
    Severity,
    TokenUsage,
    ToolResult,
)


# ---------------------------------------------------------------------------
# Phase and Severity StrEnums
# ---------------------------------------------------------------------------


class TestPhase:
    def test_members(self):
        assert set(Phase) == {
            Phase.recon,
            Phase.scanning,
            Phase.exploitation,
            Phase.validation,
            Phase.reporting,
        }

    def test_string_values(self):
        for p in Phase:
            assert isinstance(p, str)
            assert p == p.value

    def test_invalid_phase(self):
        with pytest.raises(ValueError):
            Phase("hacking")


class TestSeverity:
    def test_members(self):
        assert set(Severity) == {
            Severity.critical,
            Severity.high,
            Severity.medium,
            Severity.low,
            Severity.info,
        }

    def test_string_values(self):
        for s in Severity:
            assert isinstance(s, str)
            assert s == s.value

    def test_invalid_severity(self):
        with pytest.raises(ValueError):
            Severity("catastrophic")


# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------


class TestFinding:
    def test_valid_construction(self, sample_finding: Finding):
        assert sample_finding.title == "SQL Injection in login"
        assert sample_finding.severity == Severity.critical
        assert sample_finding.cvss == 9.8
        assert sample_finding.cve_id == "CVE-2024-1234"

    def test_minimal_construction(self):
        f = Finding(
            title="XSS",
            severity=Severity.medium,
            description="Reflected XSS",
            url="https://example.com/search",
            evidence="<script>alert(1)</script>",
            tool_name="zap",
        )
        assert f.cve_id is None
        assert f.cvss is None
        assert f.remediation is None

    def test_missing_required_field(self):
        with pytest.raises(ValidationError) as exc_info:
            Finding(
                title="Missing fields",
                severity=Severity.high,
                # missing description, url, evidence, tool_name
            )
        errors = exc_info.value.errors()
        missing_fields = {e["loc"][0] for e in errors}
        assert {"description", "url", "evidence", "tool_name"} <= missing_fields

    def test_invalid_severity_value(self):
        with pytest.raises(ValidationError):
            Finding(
                title="Bad severity",
                severity="catastrophic",
                description="test",
                url="https://example.com",
                evidence="test",
                tool_name="test",
            )

    def test_cvss_out_of_range(self):
        with pytest.raises(ValidationError, match="CVSS"):
            Finding(
                title="Bad CVSS",
                severity=Severity.high,
                description="test",
                url="https://example.com",
                evidence="test",
                tool_name="test",
                cvss=11.0,
            )

    def test_cvss_negative(self):
        with pytest.raises(ValidationError, match="CVSS"):
            Finding(
                title="Negative CVSS",
                severity=Severity.low,
                description="test",
                url="https://example.com",
                evidence="test",
                tool_name="test",
                cvss=-1.0,
            )

    def test_json_round_trip(self, sample_finding: Finding):
        json_str = sample_finding.model_dump_json()
        restored = Finding.model_validate_json(json_str)
        assert restored == sample_finding


# ---------------------------------------------------------------------------
# ToolResult
# ---------------------------------------------------------------------------


class TestToolResult:
    def test_valid_construction(self, sample_tool_result: ToolResult):
        assert sample_tool_result.tool_name == "nmap"
        assert sample_tool_result.exit_code == 0
        assert sample_tool_result.duration_ms == 5200

    def test_negative_duration(self):
        with pytest.raises(ValidationError, match="duration_ms"):
            ToolResult(
                tool_name="nmap",
                command="nmap example.com",
                stdout="",
                stderr="",
                exit_code=0,
                duration_ms=-100,
            )

    def test_long_stdout(self):
        big_output = "A" * 100_000
        result = ToolResult(
            tool_name="dirb",
            command="dirb https://example.com",
            stdout=big_output,
            stderr="",
            exit_code=0,
            duration_ms=30000,
        )
        assert len(result.stdout) == 100_000

    def test_default_timestamp(self):
        result = ToolResult(
            tool_name="test",
            command="echo hi",
            stdout="hi",
            stderr="",
            exit_code=0,
            duration_ms=10,
        )
        assert result.timestamp.tzinfo is not None

    def test_json_round_trip(self, sample_tool_result: ToolResult):
        json_str = sample_tool_result.model_dump_json()
        restored = ToolResult.model_validate_json(json_str)
        assert restored == sample_tool_result


# ---------------------------------------------------------------------------
# LLMResponse
# ---------------------------------------------------------------------------


class TestLLMResponse:
    def test_valid_construction(self, sample_token_usage: TokenUsage):
        resp = LLMResponse(
            content="Found SQL injection vulnerability.",
            model="gpt-4o",
            tokens_used=sample_token_usage,
            cost=0.0025,
            latency_ms=1200,
        )
        assert resp.model == "gpt-4o"
        assert resp.tokens_used.total == 230
        assert resp.tool_calls is None

    def test_with_tool_calls(self, sample_token_usage: TokenUsage):
        resp = LLMResponse(
            content="",
            model="gpt-4o",
            tokens_used=sample_token_usage,
            cost=0.003,
            latency_ms=800,
            tool_calls=[{"name": "run_nmap", "arguments": {"target": "example.com"}}],
        )
        assert len(resp.tool_calls) == 1

    def test_negative_cost(self):
        with pytest.raises(ValidationError):
            LLMResponse(
                content="test",
                model="gpt-4o",
                tokens_used=TokenUsage(input=10, output=5, total=15),
                cost=-0.01,
                latency_ms=100,
            )

    def test_negative_tokens(self):
        with pytest.raises(ValidationError):
            TokenUsage(input=-1, output=5, total=4)

    def test_json_round_trip(self, sample_token_usage: TokenUsage):
        resp = LLMResponse(
            content="Analysis complete.",
            model="claude-3-opus",
            tokens_used=sample_token_usage,
            cost=0.05,
            latency_ms=3000,
            raw_response={"id": "msg_123", "type": "message"},
        )
        json_str = resp.model_dump_json()
        restored = LLMResponse.model_validate_json(json_str)
        assert restored == resp


# ---------------------------------------------------------------------------
# ScanState
# ---------------------------------------------------------------------------


class TestScanState:
    def test_valid_construction(self, scan_state_factory):
        state = scan_state_factory()
        assert state.target == "https://example.com"
        assert state.current_phase == Phase.recon
        assert state.findings == []
        assert state.tool_results == []
        assert state.total_cost == 0.0
        assert state.total_tokens == 0

    def test_add_finding(self, scan_state_factory, sample_finding: Finding):
        state = scan_state_factory()
        state.add_finding(sample_finding)
        assert len(state.findings) == 1
        assert state.findings[0].title == "SQL Injection in login"

    def test_add_tool_result(self, scan_state_factory, sample_tool_result: ToolResult):
        state = scan_state_factory()
        state.add_tool_result(sample_tool_result)
        assert len(state.tool_results) == 1
        assert state.tool_results[0].tool_name == "nmap"

    def test_advance_phase(self, scan_state_factory):
        state = scan_state_factory()
        assert state.current_phase == Phase.recon
        state.advance_phase(Phase.scanning)
        assert state.current_phase == Phase.scanning
        assert Phase.recon in state.phases_completed

    def test_advance_phase_multiple(self, scan_state_factory):
        state = scan_state_factory()
        state.advance_phase(Phase.scanning)
        state.advance_phase(Phase.exploitation)
        state.advance_phase(Phase.validation)
        assert state.current_phase == Phase.validation
        assert state.phases_completed == [Phase.recon, Phase.scanning, Phase.exploitation]

    def test_record_llm_usage(self, scan_state_factory, sample_token_usage: TokenUsage):
        state = scan_state_factory()
        resp = LLMResponse(
            content="test",
            model="gpt-4o",
            tokens_used=sample_token_usage,
            cost=0.005,
            latency_ms=500,
        )
        state.record_llm_usage(resp)
        assert state.total_cost == pytest.approx(0.005)
        assert state.total_tokens == 230

        # accumulate a second call
        state.record_llm_usage(resp)
        assert state.total_cost == pytest.approx(0.010)
        assert state.total_tokens == 460

    def test_accumulation_scenario(
        self, scan_state_factory, sample_finding, sample_tool_result, sample_token_usage
    ):
        """Full lifecycle: add results, advance phases, record costs."""
        state = scan_state_factory()

        # Recon phase
        state.add_tool_result(sample_tool_result)
        resp = LLMResponse(
            content="Analysis",
            model="gpt-4o",
            tokens_used=sample_token_usage,
            cost=0.003,
            latency_ms=400,
        )
        state.record_llm_usage(resp)
        state.advance_phase(Phase.scanning)

        # Scanning phase
        state.add_finding(sample_finding)
        state.add_tool_result(sample_tool_result)
        state.record_llm_usage(resp)
        state.advance_phase(Phase.exploitation)

        assert len(state.findings) == 1
        assert len(state.tool_results) == 2
        assert state.total_cost == pytest.approx(0.006)
        assert state.total_tokens == 460
        assert state.current_phase == Phase.exploitation
        assert state.phases_completed == [Phase.recon, Phase.scanning]

    def test_empty_findings_list(self, scan_state_factory):
        state = scan_state_factory()
        assert state.findings == []
        assert len(state.findings) == 0

    def test_zero_cost(self, scan_state_factory):
        state = scan_state_factory(total_cost=0.0, total_tokens=0)
        assert state.total_cost == 0.0
        assert state.total_tokens == 0

    def test_negative_cost_rejected(self):
        with pytest.raises(ValidationError):
            ScanState(target="https://example.com", total_cost=-1.0)

    def test_json_round_trip(self, scan_state_factory, sample_finding, sample_tool_result):
        state = scan_state_factory()
        state.add_finding(sample_finding)
        state.add_tool_result(sample_tool_result)
        state.advance_phase(Phase.scanning)

        json_str = state.model_dump_json()
        restored = ScanState.model_validate_json(json_str)
        assert restored.target == state.target
        assert len(restored.findings) == 1
        assert len(restored.tool_results) == 1
        assert restored.current_phase == Phase.scanning

    def test_default_start_time(self, scan_state_factory):
        state = scan_state_factory()
        assert state.start_time is not None
        assert state.start_time.tzinfo is not None
        assert state.end_time is None
