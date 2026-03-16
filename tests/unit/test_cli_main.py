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
            scan_state.phases_completed = [Phase.recon, Phase.scanning]
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
