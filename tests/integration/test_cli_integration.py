"""Integration tests — real CLI entrypoint with real LLM + real Docker.

Proves the ``0xpwn scan --target`` command prints streaming Rich output
(phase transitions, reasoning/tool blocks, completion text) through the
real Typer entrypoint, not through internal helpers.

Run with:
    pytest tests/integration/test_cli_integration.py -m integration -v

Prerequisites:
    - Docker daemon reachable and ``oxpwn-sandbox:dev`` image available
    - At least one LLM API key exported (GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY)
"""

from __future__ import annotations

import os

import pytest
from typer.testing import CliRunner

from oxpwn.cli.main import app

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Skip helpers — mirrors conftest.py gating without pulling in session fixtures
# ---------------------------------------------------------------------------

_LLM_KEY_ENV_VARS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY")


def _docker_available() -> bool:
    """Return True if Docker daemon is reachable."""
    try:
        import docker as docker_lib

        client = docker_lib.from_env()
        client.ping()
        return True
    except Exception:  # noqa: BLE001
        return False


def _llm_key_available() -> bool:
    """Return True if at least one LLM API key is exported."""
    return any(os.environ.get(k) for k in _LLM_KEY_ENV_VARS)


def _test_model() -> str:
    return os.environ.get("OXPWN_TEST_MODEL", "gemini/gemini-2.5-flash")


_skip_no_docker = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker daemon not reachable — skipping CLI integration tests",
)
_skip_no_llm = pytest.mark.skipif(
    not _llm_key_available(),
    reason="No LLM API key set — skipping CLI integration tests",
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@_skip_no_docker
@_skip_no_llm
@pytest.mark.timeout(300)
def test_cli_scan_entrypoint_streams_real_output() -> None:
    """Real ``0xpwn scan --target localhost`` prints streaming Rich output.

    Structural assertions (not exact LLM wording):
      a) Scan header and configuration panel appear
      b) At least one phase rule is printed
      c) At least one reasoning block is printed
      d) At least one tool dispatch or tool result block appears
      e) Scan summary is printed at the end
      f) Output ordering is header → phase → reasoning/tool → summary
    """
    model = _test_model()

    result = runner.invoke(
        app,
        ["scan", "--target", "localhost", "--model", model],
    )

    output = result.output

    # --- (a) Header ---
    assert "0xpwn scan" in output, (
        f"Expected '0xpwn scan' header in output. Exit code: {result.exit_code}\n"
        f"Output head:\n{output[:500]}"
    )
    assert "Scan configuration" in output, "Expected 'Scan configuration' panel"

    # --- (b) Phase rule ---
    assert "Phase: Recon" in output, (
        f"Expected 'Phase: Recon' rule in output.\nOutput head:\n{output[:1000]}"
    )

    # --- (c) Reasoning block ---
    assert "Reasoning" in output, (
        f"Expected at least one 'Reasoning' panel.\nOutput:\n{output[:2000]}"
    )

    # --- (d) Tool dispatch or result ---
    has_tool_dispatch = "Tool dispatch" in output
    has_tool_result = "Tool result" in output
    assert has_tool_dispatch or has_tool_result, (
        f"Expected at least one 'Tool dispatch' or 'Tool result' panel.\n"
        f"Output:\n{output[:2000]}"
    )

    # --- (e) Scan summary ---
    assert "Scan summary" in output, (
        f"Expected 'Scan summary' at end of output.\nOutput tail:\n{output[-500:]}"
    )

    # --- (f) Ordering: header before phase before summary ---
    header_idx = output.index("0xpwn scan")
    phase_idx = output.index("Phase: Recon")
    summary_idx = output.index("Scan summary")
    assert header_idx < phase_idx < summary_idx, (
        f"Output ordering violated: header@{header_idx}, phase@{phase_idx}, summary@{summary_idx}"
    )

    # --- Exit code ---
    assert result.exit_code == 0, (
        f"Expected exit code 0, got {result.exit_code}.\n"
        f"Output tail:\n{output[-500:]}"
    )


@_skip_no_docker
@_skip_no_llm
@pytest.mark.timeout(300)
def test_cli_scan_streams_tool_output_chunks() -> None:
    """Streamed tool output chunks appear between dispatch and result.

    When the agent calls a tool (e.g. nmap), the Rich renderer should print
    ``<tool> stdout │`` or ``<tool> stderr │`` chunk lines between the
    tool dispatch panel and the tool result panel.
    """
    model = _test_model()

    result = runner.invoke(
        app,
        ["scan", "--target", "localhost", "--model", model],
    )

    output = result.output

    # Must complete successfully
    assert result.exit_code == 0, (
        f"Expected exit code 0, got {result.exit_code}.\nOutput tail:\n{output[-500:]}"
    )

    # Look for streamed chunk markers (stdout │ or stderr │)
    has_stdout_chunk = "stdout │" in output
    has_stderr_chunk = "stderr │" in output
    assert has_stdout_chunk or has_stderr_chunk, (
        f"Expected at least one streamed chunk line ('stdout │' or 'stderr │').\n"
        f"Output:\n{output[:2000]}"
    )


@_skip_no_docker
@_skip_no_llm
@pytest.mark.timeout(300)
def test_cli_scan_output_contains_target_and_model_config() -> None:
    """Scan configuration panel shows the target and model passed on the CLI."""
    model = _test_model()

    result = runner.invoke(
        app,
        ["scan", "--target", "localhost", "--model", model],
    )

    output = result.output
    assert result.exit_code == 0, f"Exit code {result.exit_code}.\nOutput:\n{output[-500:]}"

    assert "Target: localhost" in output
    assert f"Model: {model}" in output
    assert "Scan ID: scan-" in output


def test_cli_scan_skips_gracefully_without_model() -> None:
    """Without ``--model`` or ``OXPWN_MODEL`` the command fails with a clear error, not a crash."""
    # Unset OXPWN_MODEL if it happens to be set
    env = {k: v for k, v in os.environ.items() if k != "OXPWN_MODEL"}

    result = runner.invoke(
        app,
        ["scan", "--target", "localhost"],
        env=env,
    )

    assert result.exit_code == 1
    assert "Scan bootstrap error" in result.output
    assert "Missing model configuration" in result.output


def test_cli_scan_version_flag() -> None:
    """``0xpwn --version`` prints the version and exits cleanly."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0xpwn" in result.output
