"""Shared pytest fixtures and configuration for 0xpwn tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from oxpwn.core.models import (
    Finding,
    Phase,
    ScanState,
    Severity,
    TokenUsage,
    ToolResult,
)


@pytest.fixture()
def sample_finding() -> Finding:
    """A representative security finding for tests."""
    return Finding(
        title="SQL Injection in login",
        severity=Severity.critical,
        description="The login endpoint is vulnerable to SQL injection via the username parameter.",
        url="https://example.com/login",
        evidence="' OR 1=1 --",
        cve_id="CVE-2024-1234",
        cvss=9.8,
        cwe_id="CWE-89",
        remediation="Use parameterized queries.",
        tool_name="sqlmap",
    )


@pytest.fixture()
def sample_tool_result() -> ToolResult:
    """A representative tool execution result for tests."""
    return ToolResult(
        tool_name="nmap",
        command="nmap -sV -p 80,443 example.com",
        stdout="PORT   STATE SERVICE VERSION\n80/tcp open  http    nginx 1.24\n443/tcp open  ssl/http nginx 1.24",
        stderr="",
        exit_code=0,
        duration_ms=5200,
        timestamp=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture()
def sample_token_usage() -> TokenUsage:
    """A representative token usage breakdown."""
    return TokenUsage(input=150, output=80, total=230)


@pytest.fixture()
def scan_state_factory():
    """Factory for creating ScanState instances with sensible defaults."""

    def _create(
        target: str = "https://example.com",
        current_phase: Phase = Phase.recon,
        **kwargs,
    ) -> ScanState:
        return ScanState(target=target, current_phase=current_phase, **kwargs)

    return _create
