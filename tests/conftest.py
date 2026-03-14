"""Shared pytest fixtures and configuration for 0xpwn tests."""

from __future__ import annotations

import asyncio
import os
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


# ---------------------------------------------------------------------------
# Docker sandbox session fixture (integration tests)
# ---------------------------------------------------------------------------

_SANDBOX_IMAGE = "oxpwn-sandbox:dev"


@pytest.fixture(scope="session")
def docker_sandbox(tmp_path_factory):
    """Provide a running :class:`DockerSandbox` for integration tests.

    * Builds the image idempotently (skips if already present).
    * Skips the entire test session if Docker is unreachable.
    * Creates the container once, yields it, destroys on teardown.
    """
    import docker as docker_lib

    try:
        client = docker_lib.from_env()
        client.ping()
    except Exception:  # noqa: BLE001
        pytest.skip("Docker daemon not reachable — skipping integration tests")

    # Build image if missing
    try:
        client.images.get(_SANDBOX_IMAGE)
    except docker_lib.errors.ImageNotFound:
        import pathlib

        dockerfile_dir = pathlib.Path(__file__).resolve().parent.parent / "docker"
        client.images.build(path=str(dockerfile_dir), tag=_SANDBOX_IMAGE, rm=True)

    # Create sandbox via asyncio
    from oxpwn.sandbox.docker import DockerSandbox

    sandbox = DockerSandbox(_SANDBOX_IMAGE, scan_id="integration-test")
    loop = asyncio.new_event_loop()
    loop.run_until_complete(sandbox.create())

    yield sandbox

    loop.run_until_complete(sandbox.destroy())
    loop.close()


# ---------------------------------------------------------------------------
# LLM client fixture (integration tests)
# ---------------------------------------------------------------------------

_LLM_KEY_ENV_VARS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY")


@pytest.fixture(scope="session")
def llm_client():
    """Provide an :class:`LLMClient` for integration tests.

    Uses ``OXPWN_TEST_MODEL`` or defaults to ``gemini/gemini-2.5-flash``.
    Skips if no API key is found in the environment.
    """
    if not any(os.environ.get(k) for k in _LLM_KEY_ENV_VARS):
        pytest.skip("No LLM API key set — skipping LLM integration tests")

    from oxpwn.llm.client import LLMClient

    model = os.environ.get("OXPWN_TEST_MODEL", "gemini/gemini-2.5-flash")
    return LLMClient(model)


# ---------------------------------------------------------------------------
# ReactAgent fixture (integration tests — requires both LLM + Docker)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def react_agent(llm_client, docker_sandbox):
    """Provide a :class:`ReactAgent` with real LLM + Docker sandbox.

    Registers the default nmap tool.  Skips if either Docker or LLM
    credentials are unavailable (inherited from fixture dependencies).
    """
    from oxpwn.agent.react import ReactAgent
    from oxpwn.agent.tools import ToolRegistry, register_default_tools

    registry = ToolRegistry()
    register_default_tools(registry)
    return ReactAgent(llm_client, docker_sandbox, registry, max_iterations_per_phase=5)
