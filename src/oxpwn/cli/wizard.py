"""Interactive first-run wizard for 0xpwn configuration."""

from __future__ import annotations

import asyncio
import sys
from typing import Any

import httpx
import structlog
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule

from oxpwn.config import ConfigManager, OxpwnConfig

logger = structlog.get_logger("oxpwn.cli.wizard")

_OLLAMA_URL = "http://localhost:11434/api/tags"
_OLLAMA_TIMEOUT = 3.0
_LLM_VALIDATE_TIMEOUT = 30.0

_CLOUD_PROVIDERS: dict[str, dict[str, str]] = {
    "openai": {"default_model": "openai/gpt-4o-mini", "env_hint": "OPENAI_API_KEY"},
    "anthropic": {"default_model": "anthropic/claude-sonnet-4-20250514", "env_hint": "ANTHROPIC_API_KEY"},
    "gemini": {"default_model": "gemini/gemini-2.5-flash", "env_hint": "GEMINI_API_KEY"},
    "other": {"default_model": "", "env_hint": ""},
}

_MAX_VALIDATION_RETRIES = 2


def _probe_ollama() -> list[str]:
    """Probe local Ollama for available models. Returns model names or empty list."""
    try:
        resp = httpx.get(_OLLAMA_URL, timeout=_OLLAMA_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return [m["name"] for m in data.get("models", [])]
    except Exception:  # noqa: BLE001
        return []


def _redact_api_key(key: str) -> str:
    """Redact an API key for display: show first 4 and last 4 chars."""
    if len(key) <= 10:
        return "***"
    return f"{key[:4]}***{key[-4:]}"


def _validate_llm(model: str, api_key: str | None, base_url: str | None) -> str | None:
    """Validate LLM connectivity. Returns None on success, error message on failure."""
    try:
        import litellm  # noqa: PLC0415

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": "Say OK"}],
            "max_tokens": 5,
            "timeout": _LLM_VALIDATE_TIMEOUT,
        }
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url

        asyncio.run(litellm.acompletion(**kwargs))
        return None
    except Exception as exc:  # noqa: BLE001
        return str(exc)


def _run_local_flow(console: Console, ollama_models: list[str]) -> OxpwnConfig:
    """Collect config for local Ollama provider."""
    if ollama_models:
        console.print("\n[bold]Available Ollama models:[/bold]")
        for i, name in enumerate(ollama_models, 1):
            console.print(f"  {i}. {name}")
        console.print(f"  {len(ollama_models) + 1}. Enter custom model name")

        choice = Prompt.ask(
            "Select model number",
            default="1",
            console=console,
        )
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(ollama_models):
                model_name = ollama_models[idx]
            else:
                model_name = Prompt.ask("Enter Ollama model name", console=console)
        except ValueError:
            model_name = Prompt.ask("Enter Ollama model name", console=console)
    else:
        model_name = Prompt.ask(
            "Enter Ollama model name (e.g. llama3.1, qwen2.5)",
            console=console,
        )

    return OxpwnConfig(model=f"ollama/{model_name}")


def _run_cloud_flow(console: Console) -> OxpwnConfig:
    """Collect config for a cloud LLM provider."""
    provider_names = list(_CLOUD_PROVIDERS.keys())
    provider = Prompt.ask(
        "Select provider",
        choices=provider_names,
        default="openai",
        console=console,
    )

    provider_info = _CLOUD_PROVIDERS[provider]

    api_key = Prompt.ask("Enter API key", password=True, console=console)

    default_model = provider_info["default_model"]
    if default_model:
        model = Prompt.ask(
            "Enter model",
            default=default_model,
            console=console,
        )
    else:
        model = Prompt.ask(
            "Enter model (e.g. provider/model-name)",
            console=console,
        )

    base_url = None
    if provider == "other":
        base_url_input = Prompt.ask(
            "Enter base URL (leave empty for default)",
            default="",
            console=console,
        )
        if base_url_input.strip():
            base_url = base_url_input.strip()

    return OxpwnConfig(model=model, api_key=api_key, base_url=base_url)


def run_wizard(console: Console | None = None) -> OxpwnConfig | None:
    """Run the interactive first-run configuration wizard.

    Returns the saved ``OxpwnConfig`` on success, or ``None`` if the wizard
    was skipped (non-interactive terminal) or the user declined.
    """
    if not sys.stdin.isatty():
        logger.debug("wizard.skipped", reason="non_interactive_terminal")
        return None

    console = console or Console()

    logger.debug("wizard.started")
    console.print(Rule(title="0xpwn Setup Wizard", style="bold blue"))
    console.print(
        Panel(
            "Welcome! Let's configure your LLM provider so 0xpwn can run scans.\n"
            "You can re-run this wizard anytime with: [bold]0xpwn config wizard[/bold]",
            border_style="blue",
        )
    )

    # Probe Ollama
    console.print("\n[dim]Checking for local Ollama instance...[/dim]")
    ollama_models = _probe_ollama()

    if ollama_models:
        console.print(
            f"[green]✓[/green] Ollama detected with {len(ollama_models)} model(s) available."
        )
        provider_type = Prompt.ask(
            "Use local Ollama or cloud provider?",
            choices=["local", "cloud"],
            default="local",
            console=console,
        )
    elif _is_ollama_running():
        console.print(
            "[yellow]![/yellow] Ollama is running but has no models pulled.\n"
            "  Tip: Run [bold]ollama pull llama3.1[/bold] to download a model."
        )
        provider_type = Prompt.ask(
            "Use local Ollama or cloud provider?",
            choices=["local", "cloud"],
            default="cloud",
            console=console,
        )
    else:
        console.print("[dim]No local Ollama detected — proceeding with cloud setup.[/dim]")
        provider_type = "cloud"

    # Collect provider config
    if provider_type == "local":
        config = _run_local_flow(console, ollama_models)
    else:
        config = _run_cloud_flow(console)

    # Validate LLM connectivity
    validated = False
    for attempt in range(_MAX_VALIDATION_RETRIES + 1):
        console.print(f"\n[dim]Validating LLM connectivity for {config.model}...[/dim]")
        error = _validate_llm(config.model, config.api_key, config.base_url)

        if error is None:
            console.print("[green]✓[/green] LLM connection validated successfully!")
            validated = True
            break

        console.print(
            Panel(
                f"Validation failed: {error}",
                title="Connection error",
                border_style="red",
            )
        )

        if attempt < _MAX_VALIDATION_RETRIES:
            retry = Confirm.ask("Would you like to retry with different settings?", console=console)
            if not retry:
                break
            # Re-collect config
            if provider_type == "local":
                config = _run_local_flow(console, ollama_models)
            else:
                config = _run_cloud_flow(console)

    if not validated:
        skip = Confirm.ask(
            "Save configuration anyway (without validation)?",
            default=False,
            console=console,
        )
        if not skip:
            logger.debug("wizard.completed", outcome="declined")
            console.print("[dim]Wizard cancelled. No configuration saved.[/dim]")
            return None

    # Save config
    mgr = ConfigManager()
    path = mgr.save(config)

    console.print(
        Panel(
            f"Configuration saved to: [bold]{path}[/bold]\n"
            f"Model: [bold]{config.model}[/bold]\n"
            f"API key: [bold]{_redact_api_key(config.api_key) if config.api_key else '(not set)'}[/bold]",
            title="Setup complete",
            border_style="green",
        )
    )
    logger.debug("wizard.completed", outcome="saved", config_path=str(path))
    return config


def _is_ollama_running() -> bool:
    """Check if Ollama server is reachable (even with no models)."""
    try:
        resp = httpx.get(_OLLAMA_URL, timeout=_OLLAMA_TIMEOUT)
        return resp.status_code == 200
    except Exception:  # noqa: BLE001
        return False
