"""CLI entrypoint for 0xpwn."""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import structlog
import typer
from rich.console import Console

from oxpwn import __version__
from oxpwn.agent.exceptions import AgentError
from oxpwn.agent.react import ReactAgent
from oxpwn.agent.tools import ToolRegistry, register_default_tools
from oxpwn.cli.streaming import RichStreamingCallback, redact_string, render_error_panel
from oxpwn.core.models import ScanState
from oxpwn.llm.client import LLMClient
from oxpwn.llm.exceptions import LLMAuthError, LLMError, LLMRateLimitError, LLMToolCallError
from oxpwn.sandbox.docker import DockerSandbox
from oxpwn.sandbox.exceptions import ImageNotFoundError, SandboxError

DEFAULT_SANDBOX_IMAGE = "oxpwn-sandbox:dev"
DEFAULT_NETWORK_MODE = "bridge"
DEFAULT_MAX_ITERATIONS_PER_PHASE = 10

logger = structlog.get_logger("oxpwn.cli")

app = typer.Typer(
    name="0xpwn",
    help="AI-powered penetration testing engine.",
    no_args_is_help=True,
)


@dataclass(frozen=True)
class ScanRuntimeConfig:
    """Minimal runtime config for the pre-wizard scan command."""

    target: str
    model: str
    sandbox_image: str = DEFAULT_SANDBOX_IMAGE
    network_mode: str = DEFAULT_NETWORK_MODE
    max_iterations_per_phase: int = DEFAULT_MAX_ITERATIONS_PER_PHASE
    api_key: str | None = None
    base_url: str | None = None
    scan_id: str = field(default_factory=lambda: f"scan-{uuid.uuid4().hex[:8]}")


class ScanBootstrapError(Exception):
    """Raised when the CLI is missing required runtime configuration."""


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"0xpwn {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(  # noqa: UP007
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """AI-powered penetration testing engine."""


@app.command()
def scan(
    target: str = typer.Option(
        ...,
        "--target",
        help="Target URL, hostname, IP address, or CIDR to scan.",
    ),
    model: Optional[str] = typer.Option(  # noqa: UP007
        None,
        "--model",
        envvar="OXPWN_MODEL",
        help="LLM model to use (for example 'gemini/gemini-2.5-flash').",
    ),
    llm_base_url: Optional[str] = typer.Option(  # noqa: UP007
        None,
        "--llm-base-url",
        envvar="OXPWN_LLM_BASE_URL",
        help="Override the LiteLLM base URL for self-hosted or proxy providers.",
    ),
    sandbox_image: str = typer.Option(
        DEFAULT_SANDBOX_IMAGE,
        "--sandbox-image",
        envvar="OXPWN_SANDBOX_IMAGE",
        help="Docker image used for the scan sandbox.",
    ),
    network_mode: str = typer.Option(
        DEFAULT_NETWORK_MODE,
        "--network-mode",
        envvar="OXPWN_SANDBOX_NETWORK_MODE",
        help="Docker network mode for the sandbox container.",
    ),
    max_iterations_per_phase: int = typer.Option(
        DEFAULT_MAX_ITERATIONS_PER_PHASE,
        "--max-iterations-per-phase",
        envvar="OXPWN_MAX_ITERATIONS_PER_PHASE",
        min=1,
        help="Maximum ReAct iterations per phase before aborting.",
    ),
) -> None:
    """Run a penetration test against a target."""
    console = Console()

    try:
        config = _build_scan_config(
            target=target,
            model=model,
            llm_base_url=llm_base_url,
            sandbox_image=sandbox_image,
            network_mode=network_mode,
            max_iterations_per_phase=max_iterations_per_phase,
        )
    except ScanBootstrapError as exc:
        render_error_panel(
            console,
            title="Scan bootstrap error",
            message=str(exc),
        )
        raise typer.Exit(code=1) from exc

    try:
        asyncio.run(_scan_async(config, console=console))
    except ImageNotFoundError as exc:
        _log_scan_failure(event="docker_image_missing", config=config, exc=exc)
        render_error_panel(
            console,
            title="Docker sandbox error",
            message=f"Sandbox image '{exc.image_name or config.sandbox_image}' was not found.",
            details=[
                "Build or pull the sandbox image first.",
                f"Configured image: {config.sandbox_image}",
            ],
        )
        raise typer.Exit(code=1) from exc
    except SandboxError as exc:
        _log_scan_failure(event="docker_sandbox_error", config=config, exc=exc)
        details = []
        if exc.container_id:
            details.append(f"Container: {exc.container_id}")
        details.append("Check that the Docker daemon is running and reachable.")
        render_error_panel(
            console,
            title="Docker sandbox error",
            message=str(exc),
            details=details,
        )
        raise typer.Exit(code=1) from exc
    except LLMAuthError as exc:
        _log_scan_failure(event="llm_auth_error", config=config, exc=exc)
        provider = exc.provider or "configured"
        model_name = exc.model or config.model
        render_error_panel(
            console,
            title="LLM authentication failed",
            message=(
                f"Authentication failed for provider '{provider}' using model '{model_name}'."
            ),
            details=[
                "Export the provider API key (for example GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, or OXPWN_API_KEY) and retry.",
            ],
        )
        raise typer.Exit(code=1) from exc
    except LLMRateLimitError as exc:
        _log_scan_failure(event="llm_rate_limited", config=config, exc=exc)
        details = []
        if exc.retry_after is not None:
            details.append(f"Retry after: {exc.retry_after:.1f}s")
        details.append("Wait and retry, or switch to a model/provider with more quota.")
        render_error_panel(
            console,
            title="LLM rate limited",
            message=f"Provider '{exc.provider or 'configured'}' rate limited model '{exc.model or config.model}'.",
            details=details,
        )
        raise typer.Exit(code=1) from exc
    except LLMToolCallError as exc:
        _log_scan_failure(event="llm_tool_call_error", config=config, exc=exc)
        render_error_panel(
            console,
            title="LLM response error",
            message=(
                f"The provider returned an invalid tool-call payload for model '{exc.model or config.model}'."
            ),
            details=["Retry the scan. If it persists, switch models or inspect llm.complete logs."],
        )
        raise typer.Exit(code=1) from exc
    except LLMError as exc:
        _log_scan_failure(event="llm_runtime_error", config=config, exc=exc)
        render_error_panel(
            console,
            title="LLM runtime error",
            message=f"The model '{exc.model or config.model}' failed before the scan could complete.",
            details=["Inspect llm.complete logs for provider-side diagnostics."],
        )
        raise typer.Exit(code=1) from exc
    except AgentError as exc:
        _log_scan_failure(event="agent_runtime_error", config=config, exc=exc)
        details = []
        if exc.phase is not None:
            details.append(f"Phase: {exc.phase}")
        if exc.iteration is not None:
            details.append(f"Iteration: {exc.iteration}")
        render_error_panel(
            console,
            title="Agent runtime error",
            message=str(exc),
            details=details or ["Inspect agent.* logs for the surrounding event sequence."],
        )
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # noqa: BLE001
        _log_scan_failure(event="unexpected_runtime_error", config=config, exc=exc)
        render_error_panel(
            console,
            title="Scan failed",
            message=f"Unexpected runtime error: {type(exc).__name__}.",
            details=["Inspect structlog output for the full traceback and context."],
        )
        raise typer.Exit(code=1) from exc


async def _scan_async(
    config: ScanRuntimeConfig,
    *,
    console: Console | None = None,
    llm_client_factory: Callable[..., Any] = LLMClient,
    sandbox_factory: Callable[..., Any] = DockerSandbox,
    agent_factory: Callable[..., Any] = ReactAgent,
    callback_factory: Callable[[Console], RichStreamingCallback] = RichStreamingCallback,
    registry_factory: Callable[[], ToolRegistry] | None = None,
    scan_state_factory: Callable[..., ScanState] = ScanState,
) -> ScanState:
    """Compose the real runtime and execute a scan."""
    runtime_console = console or Console()
    callback = callback_factory(runtime_console)
    scan_state = scan_state_factory(target=config.target)
    scan_state.metadata.update(
        {
            "scan_id": config.scan_id,
            "model": config.model,
            "sandbox_image": config.sandbox_image,
            "network_mode": config.network_mode,
        }
    )

    callback.render_scan_start(
        target=config.target,
        model=config.model,
        sandbox_image=config.sandbox_image,
        network_mode=config.network_mode,
        max_iterations_per_phase=config.max_iterations_per_phase,
        scan_id=config.scan_id,
        initial_phase=scan_state.current_phase.value,
    )

    logger.info(
        "cli.scan_start",
        scan_id=config.scan_id,
        target=redact_string(config.target),
        model=config.model,
        sandbox_image=config.sandbox_image,
        network_mode=config.network_mode,
        max_iterations_per_phase=config.max_iterations_per_phase,
    )

    registry = (registry_factory or _build_tool_registry)()
    llm_client = llm_client_factory(
        config.model,
        api_key=config.api_key,
        base_url=config.base_url,
    )

    async with sandbox_factory(
        config.sandbox_image,
        scan_id=config.scan_id,
        network_mode=config.network_mode,
    ) as sandbox:
        agent = agent_factory(
            llm_client,
            sandbox,
            registry,
            max_iterations_per_phase=config.max_iterations_per_phase,
            event_callback=callback,
        )
        final_state = await agent.run(scan_state)

    final_state.end_time = datetime.now(timezone.utc)
    callback.render_final_summary(final_state)

    logger.info(
        "cli.scan_complete",
        scan_id=config.scan_id,
        target=redact_string(config.target),
        phases_completed=[phase.value for phase in final_state.phases_completed],
        tool_results=len(final_state.tool_results),
        findings=len(final_state.findings),
        total_tokens=final_state.total_tokens,
        total_cost=final_state.total_cost,
    )
    return final_state


def _build_scan_config(
    *,
    target: str,
    model: str | None,
    llm_base_url: str | None,
    sandbox_image: str,
    network_mode: str,
    max_iterations_per_phase: int,
) -> ScanRuntimeConfig:
    """Resolve CLI inputs and env-backed defaults into a runtime config."""
    normalized_target = target.strip()
    if not normalized_target:
        raise ScanBootstrapError("Target cannot be empty.")

    resolved_model = (model or "").strip()
    if not resolved_model:
        raise ScanBootstrapError("Missing model configuration. Pass --model or set OXPWN_MODEL.")

    return ScanRuntimeConfig(
        target=normalized_target,
        model=resolved_model,
        sandbox_image=sandbox_image,
        network_mode=network_mode,
        max_iterations_per_phase=max_iterations_per_phase,
        api_key=os.environ.get("OXPWN_API_KEY"),
        base_url=llm_base_url,
    )


def _build_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    register_default_tools(registry)
    return registry


def _log_scan_failure(*, event: str, config: ScanRuntimeConfig, exc: Exception) -> None:
    logger.warning(
        "cli.scan_failed",
        failure_event=event,
        scan_id=config.scan_id,
        target=redact_string(config.target),
        model=config.model,
        sandbox_image=config.sandbox_image,
        error_type=type(exc).__name__,
    )


def run() -> None:
    """Module entrypoint for `python -m oxpwn.cli.main`."""
    app()


if __name__ == "__main__":
    run()
