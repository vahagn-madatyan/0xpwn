"""Unit tests for the real 0xpwn scan command."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pytest
from rich.console import Console
from typer.testing import CliRunner

from oxpwn.agent.events import ReasoningEvent
from oxpwn.cli import main
from oxpwn.core.models import Phase, ScanState
from oxpwn.llm.exceptions import LLMAuthError

runner = CliRunner()


def test_scan_command_runs_real_async_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    async def fake_scan_async(config: main.ScanRuntimeConfig, *, console: Console | None = None, **_: Any) -> ScanState:
        assert console is not None
        captured["config"] = config
        console.print("fake runtime ok")
        return ScanState(target=config.target)

    monkeypatch.setattr(main, "_scan_async", fake_scan_async)

    result = runner.invoke(
        main.app,
        [
            "scan",
            "--target",
            "https://example.com",
            "--model",
            "gemini/gemini-2.5-flash",
            "--sandbox-image",
            "custom-sandbox:latest",
            "--network-mode",
            "host",
            "--max-iterations-per-phase",
            "7",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "fake runtime ok" in result.output

    config = captured["config"]
    assert config.target == "https://example.com"
    assert config.model == "gemini/gemini-2.5-flash"
    assert config.sandbox_image == "custom-sandbox:latest"
    assert config.network_mode == "host"
    assert config.max_iterations_per_phase == 7
    assert config.scan_id.startswith("scan-")


def test_scan_command_exits_non_zero_when_model_config_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OXPWN_MODEL", raising=False)

    result = runner.invoke(main.app, ["scan", "--target", "localhost"])

    assert result.exit_code == 1
    assert "Scan bootstrap error" in result.output
    assert "Missing model configuration" in result.output


def test_scan_command_runtime_failures_are_secret_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "sk-secret-value"
    monkeypatch.setenv("OXPWN_API_KEY", secret)

    async def fake_scan_async(config: main.ScanRuntimeConfig, *, console: Console | None = None, **_: Any) -> ScanState:
        raise LLMAuthError(
            f"bad key: {secret}",
            model=config.model,
            provider="gemini",
        )

    monkeypatch.setattr(main, "_scan_async", fake_scan_async)

    result = runner.invoke(
        main.app,
        ["scan", "--target", "localhost", "--model", "gemini/gemini-2.5-flash"],
    )

    assert result.exit_code == 1
    assert "LLM authentication failed" in result.output
    assert "GEMINI_API_KEY" in result.output
    assert secret not in result.output


@pytest.mark.asyncio
async def test_scan_async_composes_runtime_with_fake_dependencies() -> None:
    captured: dict[str, Any] = {}
    console = Console(record=True, width=120, color_system=None, force_terminal=False)

    @dataclass
    class FakeLLMClient:
        model: str
        api_key: str | None = None
        base_url: str | None = None

        def __post_init__(self) -> None:
            captured["llm_init"] = {
                "model": self.model,
                "api_key": self.api_key,
                "base_url": self.base_url,
            }

    class FakeSandbox:
        def __init__(self, image: str, scan_id: str, *, network_mode: str) -> None:
            captured["sandbox_init"] = {
                "image": image,
                "scan_id": scan_id,
                "network_mode": network_mode,
            }

        async def __aenter__(self) -> "FakeSandbox":
            captured["sandbox_entered"] = True
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
            captured["sandbox_exited"] = True

    class FakeAgent:
        def __init__(
            self,
            llm_client: FakeLLMClient,
            sandbox: FakeSandbox,
            registry,
            *,
            max_iterations_per_phase: int,
            event_callback,
        ) -> None:
            captured["agent_init"] = {
                "llm_client": llm_client,
                "sandbox": sandbox,
                "tool_names": registry.tool_names,
                "max_iterations_per_phase": max_iterations_per_phase,
                "event_callback": event_callback,
            }
            self._event_callback = event_callback

        async def run(self, scan_state: ScanState) -> ScanState:
            await self._event_callback.on_event(
                ReasoningEvent(
                    content="Kick off recon.",
                    phase="recon",
                    iteration=1,
                )
            )
            scan_state.phases_completed = [
                Phase.recon, Phase.scanning, Phase.exploitation,
                Phase.validation, Phase.reporting,
            ]
            scan_state.total_tokens = 42
            scan_state.total_cost = 0.12
            return scan_state

    config = main.ScanRuntimeConfig(
        target="localhost",
        model="gemini/gemini-2.5-flash",
        sandbox_image="oxpwn-sandbox:test",
        network_mode="host",
        max_iterations_per_phase=4,
        api_key="api-key-placeholder",
        base_url="https://llm.example.test",
        scan_id="scan-test-1234",
    )

    result = await main._scan_async(
        config,
        console=console,
        llm_client_factory=FakeLLMClient,
        sandbox_factory=FakeSandbox,
        agent_factory=FakeAgent,
    )

    assert result.target == "localhost"
    assert result.metadata["scan_id"] == "scan-test-1234"
    assert result.end_time is not None

    assert captured["llm_init"] == {
        "model": "gemini/gemini-2.5-flash",
        "api_key": "api-key-placeholder",
        "base_url": "https://llm.example.test",
    }
    assert captured["sandbox_init"] == {
        "image": "oxpwn-sandbox:test",
        "scan_id": "scan-test-1234",
        "network_mode": "host",
    }
    assert captured["sandbox_entered"] is True
    assert captured["sandbox_exited"] is True
    assert captured["agent_init"]["max_iterations_per_phase"] == 4
    assert captured["agent_init"]["tool_names"] == ["nmap", "httpx", "subfinder", "nuclei", "ffuf"]

    output = console.export_text()
    assert "0xpwn scan" in output
    assert "Scan ID: scan-test-1234" in output
    assert "Reasoning · Recon · iter 1" in output
    assert "Scan summary" in output
    assert "Tool executions: 0" in output


def test_module_run_entrypoint_calls_typer_app(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, bool] = {"value": False}

    def fake_app() -> None:
        called["value"] = True

    monkeypatch.setattr(main, "app", fake_app)

    main.run()

    assert called["value"] is True


# ---------------------------------------------------------------------------
# Config-backed bootstrap and config subcommands (T02)
# ---------------------------------------------------------------------------


def test_build_scan_config_loads_from_yaml(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """_build_scan_config() uses YAML config when model not provided via CLI/env."""
    config_file = tmp_path / "config.yaml"
    monkeypatch.setenv("OXPWN_CONFIG", str(config_file))
    monkeypatch.delenv("OXPWN_MODEL", raising=False)
    monkeypatch.delenv("OXPWN_API_KEY", raising=False)
    monkeypatch.delenv("OXPWN_LLM_BASE_URL", raising=False)

    from oxpwn.config import ConfigManager, OxpwnConfig

    mgr = ConfigManager()
    mgr.save(OxpwnConfig(model="gemini/gemini-2.5-flash", api_key="yaml-key-123"))

    config = main._build_scan_config(
        target="https://example.com",
        model=None,
        llm_base_url=None,
        sandbox_image="oxpwn-sandbox:dev",
        network_mode="bridge",
        max_iterations_per_phase=10,
    )
    assert config.model == "gemini/gemini-2.5-flash"
    assert config.api_key == "yaml-key-123"


def test_build_scan_config_triggers_wizard_interactive(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """_build_scan_config() calls wizard when no config and terminal is interactive."""
    config_file = tmp_path / "config.yaml"
    monkeypatch.setenv("OXPWN_CONFIG", str(config_file))
    monkeypatch.delenv("OXPWN_MODEL", raising=False)
    monkeypatch.delenv("OXPWN_API_KEY", raising=False)

    import sys
    from unittest.mock import MagicMock

    monkeypatch.setattr(sys, "stdin", MagicMock(isatty=MagicMock(return_value=True)))

    wizard_called = {"value": False}

    def fake_wizard(console=None):
        wizard_called["value"] = True
        from oxpwn.config import OxpwnConfig, ConfigManager

        cfg = OxpwnConfig(model="wizard/model", api_key="wiz-key")
        ConfigManager().save(cfg)
        return cfg

    monkeypatch.setattr(main, "run_wizard", fake_wizard)

    config = main._build_scan_config(
        target="localhost",
        model=None,
        llm_base_url=None,
        sandbox_image="oxpwn-sandbox:dev",
        network_mode="bridge",
        max_iterations_per_phase=10,
    )
    assert wizard_called["value"] is True
    assert config.model == "wizard/model"
    assert config.api_key == "wiz-key"


def test_build_scan_config_raises_when_non_interactive_no_config(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """_build_scan_config() raises ScanBootstrapError in non-interactive with no config."""
    config_file = tmp_path / "config.yaml"
    monkeypatch.setenv("OXPWN_CONFIG", str(config_file))
    monkeypatch.delenv("OXPWN_MODEL", raising=False)
    monkeypatch.delenv("OXPWN_API_KEY", raising=False)

    import sys
    from unittest.mock import MagicMock

    monkeypatch.setattr(sys, "stdin", MagicMock(isatty=MagicMock(return_value=False)))

    with pytest.raises(main.ScanBootstrapError, match="Missing model configuration"):
        main._build_scan_config(
            target="localhost",
            model=None,
            llm_base_url=None,
            sandbox_image="oxpwn-sandbox:dev",
            network_mode="bridge",
            max_iterations_per_phase=10,
        )


def test_config_show_displays_redacted_config(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """config show displays config with redacted API key."""
    config_file = tmp_path / "config.yaml"
    monkeypatch.setenv("OXPWN_CONFIG", str(config_file))

    from oxpwn.config import ConfigManager, OxpwnConfig

    mgr = ConfigManager()
    mgr.save(OxpwnConfig(model="openai/gpt-4o", api_key="sk-1234567890abcdef"))

    result = runner.invoke(main.app, ["config", "show"])

    assert result.exit_code == 0
    assert "openai/gpt-4o" in result.output
    assert "sk-1234567890abcdef" not in result.output
    assert "sk-1***cdef" in result.output


def test_config_show_no_config(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """config show works when no config file exists."""
    config_file = tmp_path / "config.yaml"
    monkeypatch.setenv("OXPWN_CONFIG", str(config_file))

    result = runner.invoke(main.app, ["config", "show"])

    assert result.exit_code == 0
    assert "(not set)" in result.output


def test_config_reset_deletes_config(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """config reset deletes the config file."""
    config_file = tmp_path / "config.yaml"
    monkeypatch.setenv("OXPWN_CONFIG", str(config_file))

    from oxpwn.config import ConfigManager, OxpwnConfig

    mgr = ConfigManager()
    mgr.save(OxpwnConfig(model="test"))
    assert mgr.exists()

    # CliRunner is non-interactive, so confirmation is skipped
    result = runner.invoke(main.app, ["config", "reset"])

    assert result.exit_code == 0
    assert not mgr.exists()


def test_config_reset_no_config(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """config reset with no config file is a no-op."""
    config_file = tmp_path / "config.yaml"
    monkeypatch.setenv("OXPWN_CONFIG", str(config_file))

    result = runner.invoke(main.app, ["config", "reset"])

    assert result.exit_code == 0
    assert "Nothing to reset" in result.output


def test_config_wizard_subcommand(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """config wizard invokes the wizard flow."""
    config_file = tmp_path / "config.yaml"
    monkeypatch.setenv("OXPWN_CONFIG", str(config_file))

    wizard_called = {"value": False}

    def fake_wizard(console=None):
        wizard_called["value"] = True
        from oxpwn.config import OxpwnConfig

        return OxpwnConfig(model="wizard/test-model")

    monkeypatch.setattr(main, "run_wizard", fake_wizard)

    result = runner.invoke(main.app, ["config", "wizard"])

    assert wizard_called["value"] is True
    assert result.exit_code == 0


def test_config_help_shows_subcommands() -> None:
    """0xpwn config --help lists show, reset, wizard subcommands."""
    result = runner.invoke(main.app, ["config", "--help"])

    assert result.exit_code == 0
    assert "show" in result.output
    assert "reset" in result.output
    assert "wizard" in result.output


# ---------------------------------------------------------------------------
# S08: Enrichment wiring tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scan_async_calls_enrichment_after_agent_run() -> None:
    """_scan_async() invokes findings_from_tool_results and enrich_findings."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from oxpwn.core.models import Finding, Severity, ToolResult

    console = Console(record=True, width=120, color_system=None, force_terminal=False)

    class FakeLLMClient:
        def __init__(self, model, *, api_key=None, base_url=None):
            pass

    class FakeSandbox:
        def __init__(self, image, scan_id, *, network_mode):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class FakeAgent:
        def __init__(self, llm, sandbox, registry, *, max_iterations_per_phase, event_callback):
            self._cb = event_callback

        async def run(self, scan_state):
            await self._cb.on_event(
                ReasoningEvent(content="Starting.", phase="recon", iteration=1)
            )
            scan_state.phases_completed = [
                Phase.recon, Phase.scanning, Phase.exploitation,
                Phase.validation, Phase.reporting,
            ]
            # Add a tool result so enrichment has something to work with
            scan_state.add_tool_result(ToolResult(
                tool_name="nuclei",
                command="nuclei -t cves/ -u http://target",
                stdout="",
                stderr="",
                exit_code=0,
                duration_ms=100,
                parsed_output={"findings": [{"template_id": "CVE-2021-44228", "name": "Log4Shell", "severity": "critical", "matched_at": "http://target"}]},
            ))
            return scan_state

    config = main.ScanRuntimeConfig(
        target="localhost",
        model="test/model",
        scan_id="scan-enrich-test",
    )

    # Patch enrichment functions to track calls
    mock_enrich = AsyncMock(return_value=[])
    mock_extract = MagicMock(return_value=[
        Finding(title="Log4Shell", severity=Severity.critical, tool_name="nuclei", cve_id="CVE-2021-44228", description="RCE via Log4j", url="http://target", evidence="CVE-2021-44228"),
    ])

    with patch("oxpwn.cli.main.findings_from_tool_results", mock_extract), \
         patch("oxpwn.cli.main.enrich_findings", mock_enrich), \
         patch("oxpwn.cli.main.NvdClient") as mock_nvd_cls, \
         patch("oxpwn.cli.main.CveCache") as mock_cache_cls:
        mock_nvd_instance = MagicMock()
        mock_nvd_instance.close = AsyncMock()
        mock_nvd_cls.return_value = mock_nvd_instance
        mock_cache_instance = MagicMock()
        mock_cache_cls.return_value = mock_cache_instance

        result = await main._scan_async(
            config,
            console=console,
            llm_client_factory=FakeLLMClient,
            sandbox_factory=FakeSandbox,
            agent_factory=FakeAgent,
        )

    # Enrichment was called
    mock_extract.assert_called_once()
    mock_enrich.assert_called_once()
    # NVD client and cache were closed
    mock_nvd_instance.close.assert_called_once()
    mock_cache_instance.close.assert_called_once()
    # Findings were assigned to state
    assert len(result.findings) == 1
    assert result.findings[0].title == "Log4Shell"


@pytest.mark.asyncio
async def test_scan_async_enrichment_failure_does_not_crash() -> None:
    """Enrichment errors are caught and logged, never crash the scan."""
    from unittest.mock import MagicMock, patch

    console = Console(record=True, width=120, color_system=None, force_terminal=False)

    class FakeLLMClient:
        def __init__(self, model, *, api_key=None, base_url=None):
            pass

    class FakeSandbox:
        def __init__(self, image, scan_id, *, network_mode):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class FakeAgent:
        def __init__(self, llm, sandbox, registry, *, max_iterations_per_phase, event_callback):
            self._cb = event_callback

        async def run(self, scan_state):
            await self._cb.on_event(
                ReasoningEvent(content="Starting.", phase="recon", iteration=1)
            )
            scan_state.phases_completed = [
                Phase.recon, Phase.scanning, Phase.exploitation,
                Phase.validation, Phase.reporting,
            ]
            return scan_state

    config = main.ScanRuntimeConfig(
        target="localhost",
        model="test/model",
        scan_id="scan-enrich-fail",
    )

    # Make findings_from_tool_results raise to test the try/except
    mock_extract = MagicMock(side_effect=RuntimeError("enrichment boom"))

    with patch("oxpwn.cli.main.findings_from_tool_results", mock_extract):
        # Should NOT raise — enrichment failure is caught
        result = await main._scan_async(
            config,
            console=console,
            llm_client_factory=FakeLLMClient,
            sandbox_factory=FakeSandbox,
            agent_factory=FakeAgent,
        )

    # Scan completed despite enrichment failure
    assert result.target == "localhost"
    assert result.end_time is not None
