"""Unit tests for the interactive first-run wizard."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from oxpwn.cli import wizard
from oxpwn.config import ConfigManager, OxpwnConfig


@pytest.fixture(autouse=True)
def _isolate_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point config at a temp directory for every test."""
    monkeypatch.setenv("OXPWN_CONFIG", str(tmp_path / "config.yaml"))


# ---------------------------------------------------------------------------
# Non-interactive terminal skip
# ---------------------------------------------------------------------------


class TestWizardNonInteractive:
    def test_wizard_skips_non_interactive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Wizard returns None when stdin is not a TTY."""
        monkeypatch.setattr(sys, "stdin", MagicMock(isatty=MagicMock(return_value=False)))
        result = wizard.run_wizard()
        assert result is None

    def test_wizard_skips_non_interactive_with_console(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Wizard returns None even when a Console is passed if stdin is not a TTY."""
        monkeypatch.setattr(sys, "stdin", MagicMock(isatty=MagicMock(return_value=False)))
        console = Console(force_terminal=False)
        result = wizard.run_wizard(console)
        assert result is None


# ---------------------------------------------------------------------------
# Cloud flow
# ---------------------------------------------------------------------------


class TestWizardCloudFlow:
    def test_cloud_flow_openai(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Full cloud wizard flow: no Ollama → openai → validate OK → save."""
        monkeypatch.setattr(sys, "stdin", MagicMock(isatty=MagicMock(return_value=True)))

        # No Ollama
        monkeypatch.setattr(wizard, "_probe_ollama", lambda: [])
        monkeypatch.setattr(wizard, "_is_ollama_running", lambda: False)

        # Mock prompts: provider=openai, api_key=sk-test, model=default
        prompt_responses = iter(["openai", "sk-test-key-1234", "openai/gpt-4o-mini"])
        monkeypatch.setattr(
            "rich.prompt.Prompt.ask",
            lambda *args, **kwargs: next(prompt_responses),
        )

        # Mock validation success
        monkeypatch.setattr(wizard, "_validate_llm", lambda *a, **kw: None)

        console = Console(force_terminal=True, width=120)
        result = wizard.run_wizard(console)

        assert result is not None
        assert result.model == "openai/gpt-4o-mini"
        assert result.api_key == "sk-test-key-1234"

        # Verify config was persisted
        mgr = ConfigManager()
        loaded = mgr.load()
        assert loaded.model == "openai/gpt-4o-mini"
        assert loaded.api_key == "sk-test-key-1234"

    def test_cloud_flow_gemini(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Cloud flow with Gemini provider selection."""
        monkeypatch.setattr(sys, "stdin", MagicMock(isatty=MagicMock(return_value=True)))
        monkeypatch.setattr(wizard, "_probe_ollama", lambda: [])
        monkeypatch.setattr(wizard, "_is_ollama_running", lambda: False)

        prompt_responses = iter(["gemini", "AIza-fake-key-123456", "gemini/gemini-2.5-flash"])
        monkeypatch.setattr(
            "rich.prompt.Prompt.ask",
            lambda *args, **kwargs: next(prompt_responses),
        )
        monkeypatch.setattr(wizard, "_validate_llm", lambda *a, **kw: None)

        result = wizard.run_wizard(Console(force_terminal=True, width=120))

        assert result is not None
        assert result.model == "gemini/gemini-2.5-flash"
        assert result.api_key == "AIza-fake-key-123456"

    def test_cloud_flow_other_with_base_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Cloud flow with 'other' provider includes base URL prompt."""
        monkeypatch.setattr(sys, "stdin", MagicMock(isatty=MagicMock(return_value=True)))
        monkeypatch.setattr(wizard, "_probe_ollama", lambda: [])
        monkeypatch.setattr(wizard, "_is_ollama_running", lambda: False)

        prompt_responses = iter([
            "other",           # provider
            "my-api-key",      # api_key
            "custom/model-v1", # model
            "http://my-proxy:8080",  # base_url
        ])
        monkeypatch.setattr(
            "rich.prompt.Prompt.ask",
            lambda *args, **kwargs: next(prompt_responses),
        )
        monkeypatch.setattr(wizard, "_validate_llm", lambda *a, **kw: None)

        result = wizard.run_wizard(Console(force_terminal=True, width=120))

        assert result is not None
        assert result.model == "custom/model-v1"
        assert result.base_url == "http://my-proxy:8080"


# ---------------------------------------------------------------------------
# Local / Ollama flow
# ---------------------------------------------------------------------------


class TestWizardLocalFlow:
    def test_local_flow_select_model(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ollama detected with models → user selects first model."""
        monkeypatch.setattr(sys, "stdin", MagicMock(isatty=MagicMock(return_value=True)))
        monkeypatch.setattr(wizard, "_probe_ollama", lambda: ["llama3.1:latest", "qwen2.5:7b"])
        monkeypatch.setattr(wizard, "_is_ollama_running", lambda: True)

        # choice: local, then model #1
        prompt_responses = iter(["local", "1"])
        monkeypatch.setattr(
            "rich.prompt.Prompt.ask",
            lambda *args, **kwargs: next(prompt_responses),
        )
        monkeypatch.setattr(wizard, "_validate_llm", lambda *a, **kw: None)

        result = wizard.run_wizard(Console(force_terminal=True, width=120))

        assert result is not None
        assert result.model == "ollama/llama3.1:latest"
        assert result.api_key is None

    def test_local_flow_no_models_enter_custom(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ollama running but no models → user enters custom model name."""
        monkeypatch.setattr(sys, "stdin", MagicMock(isatty=MagicMock(return_value=True)))
        monkeypatch.setattr(wizard, "_probe_ollama", lambda: [])
        monkeypatch.setattr(wizard, "_is_ollama_running", lambda: True)

        # choice: local, then custom model name
        prompt_responses = iter(["local", "mistral:7b"])
        monkeypatch.setattr(
            "rich.prompt.Prompt.ask",
            lambda *args, **kwargs: next(prompt_responses),
        )
        monkeypatch.setattr(wizard, "_validate_llm", lambda *a, **kw: None)

        result = wizard.run_wizard(Console(force_terminal=True, width=120))

        assert result is not None
        assert result.model == "ollama/mistral:7b"


# ---------------------------------------------------------------------------
# Ollama unreachable → falls to cloud
# ---------------------------------------------------------------------------


class TestWizardOllamaUnreachable:
    def test_ollama_unreachable_falls_to_cloud(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When Ollama is not detected, wizard proceeds directly to cloud flow."""
        monkeypatch.setattr(sys, "stdin", MagicMock(isatty=MagicMock(return_value=True)))
        monkeypatch.setattr(wizard, "_probe_ollama", lambda: [])
        monkeypatch.setattr(wizard, "_is_ollama_running", lambda: False)

        prompt_responses = iter(["anthropic", "sk-ant-test", "anthropic/claude-sonnet-4-20250514"])
        monkeypatch.setattr(
            "rich.prompt.Prompt.ask",
            lambda *args, **kwargs: next(prompt_responses),
        )
        monkeypatch.setattr(wizard, "_validate_llm", lambda *a, **kw: None)

        result = wizard.run_wizard(Console(force_terminal=True, width=120))

        assert result is not None
        assert result.model == "anthropic/claude-sonnet-4-20250514"


# ---------------------------------------------------------------------------
# LLM validation failure
# ---------------------------------------------------------------------------


class TestWizardValidationFailure:
    def test_validation_failure_retry_then_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Validation fails once, user retries with new creds, second attempt succeeds."""
        monkeypatch.setattr(sys, "stdin", MagicMock(isatty=MagicMock(return_value=True)))
        monkeypatch.setattr(wizard, "_probe_ollama", lambda: [])
        monkeypatch.setattr(wizard, "_is_ollama_running", lambda: False)

        # First cloud flow, then retry prompt (yes), second cloud flow
        prompt_responses = iter([
            "openai", "bad-key", "openai/gpt-4o-mini",    # first attempt
            "openai", "good-key-12345678", "openai/gpt-4o-mini",  # retry
        ])
        monkeypatch.setattr(
            "rich.prompt.Prompt.ask",
            lambda *args, **kwargs: next(prompt_responses),
        )

        # Confirm.ask → yes for retry
        confirm_responses = iter([True])
        monkeypatch.setattr(
            "rich.prompt.Confirm.ask",
            lambda *args, **kwargs: next(confirm_responses),
        )

        # First call fails, second succeeds
        validate_calls = iter(["Auth failed", None])
        monkeypatch.setattr(
            wizard, "_validate_llm",
            lambda *a, **kw: next(validate_calls),
        )

        result = wizard.run_wizard(Console(force_terminal=True, width=120))

        assert result is not None
        assert result.api_key == "good-key-12345678"

    def test_validation_failure_decline_retry_then_skip(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Validation fails, user declines retry, then saves anyway."""
        monkeypatch.setattr(sys, "stdin", MagicMock(isatty=MagicMock(return_value=True)))
        monkeypatch.setattr(wizard, "_probe_ollama", lambda: [])
        monkeypatch.setattr(wizard, "_is_ollama_running", lambda: False)

        prompt_responses = iter(["openai", "bad-key-xx", "openai/gpt-4o-mini"])
        monkeypatch.setattr(
            "rich.prompt.Prompt.ask",
            lambda *args, **kwargs: next(prompt_responses),
        )

        # Decline retry, then accept save-without-validation
        confirm_responses = iter([False, True])
        monkeypatch.setattr(
            "rich.prompt.Confirm.ask",
            lambda *args, **kwargs: next(confirm_responses),
        )

        monkeypatch.setattr(wizard, "_validate_llm", lambda *a, **kw: "connection refused")

        result = wizard.run_wizard(Console(force_terminal=True, width=120))

        assert result is not None
        assert result.api_key == "bad-key-xx"

    def test_validation_failure_decline_all_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Validation fails, user declines retry AND declines save → None."""
        monkeypatch.setattr(sys, "stdin", MagicMock(isatty=MagicMock(return_value=True)))
        monkeypatch.setattr(wizard, "_probe_ollama", lambda: [])
        monkeypatch.setattr(wizard, "_is_ollama_running", lambda: False)

        prompt_responses = iter(["openai", "bad-key-xx", "openai/gpt-4o-mini"])
        monkeypatch.setattr(
            "rich.prompt.Prompt.ask",
            lambda *args, **kwargs: next(prompt_responses),
        )

        # Decline retry, decline save
        confirm_responses = iter([False, False])
        monkeypatch.setattr(
            "rich.prompt.Confirm.ask",
            lambda *args, **kwargs: next(confirm_responses),
        )

        monkeypatch.setattr(wizard, "_validate_llm", lambda *a, **kw: "timeout")

        result = wizard.run_wizard(Console(force_terminal=True, width=120))

        assert result is None
        # Config should NOT be saved
        mgr = ConfigManager()
        assert not mgr.exists()


# ---------------------------------------------------------------------------
# Config persistence
# ---------------------------------------------------------------------------


class TestWizardSavesConfig:
    def test_wizard_persists_config_via_config_manager(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Wizard writes config that ConfigManager can load back."""
        monkeypatch.setattr(sys, "stdin", MagicMock(isatty=MagicMock(return_value=True)))
        monkeypatch.setattr(wizard, "_probe_ollama", lambda: [])
        monkeypatch.setattr(wizard, "_is_ollama_running", lambda: False)

        prompt_responses = iter(["gemini", "AIza-persist-test", "gemini/gemini-2.5-flash"])
        monkeypatch.setattr(
            "rich.prompt.Prompt.ask",
            lambda *args, **kwargs: next(prompt_responses),
        )
        monkeypatch.setattr(wizard, "_validate_llm", lambda *a, **kw: None)

        wizard.run_wizard(Console(force_terminal=True, width=120))

        mgr = ConfigManager()
        assert mgr.exists()
        loaded = mgr.load()
        assert loaded.model == "gemini/gemini-2.5-flash"
        assert loaded.api_key == "AIza-persist-test"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestWizardHelpers:
    def test_redact_api_key_short(self) -> None:
        assert wizard._redact_api_key("short") == "***"

    def test_redact_api_key_long(self) -> None:
        result = wizard._redact_api_key("sk-1234567890abcdef")
        assert result.startswith("sk-1")
        assert result.endswith("cdef")
        assert "***" in result

    def test_probe_ollama_connection_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """_probe_ollama returns empty list on connection error."""
        def raise_error(*args: Any, **kwargs: Any) -> None:
            raise ConnectionError("refused")

        monkeypatch.setattr("httpx.get", raise_error)
        assert wizard._probe_ollama() == []
