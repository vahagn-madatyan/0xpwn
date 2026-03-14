"""CLI entrypoint for 0xpwn."""

from __future__ import annotations

from typing import Optional

import typer

from oxpwn import __version__

app = typer.Typer(
    name="0xpwn",
    help="AI-powered penetration testing engine.",
    no_args_is_help=True,
)


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
    target: str = typer.Argument(..., help="Target URL or IP to scan."),
) -> None:
    """Run a penetration test against a target."""
    typer.echo(f"Not implemented yet (target: {target})")
