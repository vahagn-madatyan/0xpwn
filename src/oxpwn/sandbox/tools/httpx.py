"""httpx JSONL parser and sandbox executor.

Provides a compact, typed wrapper around ``httpx`` using JSONL output only.
The executor follows the S02 ``NmapExecutor`` contract: constructor takes a
``DockerSandbox`` and ``run()`` returns a ``ToolResult`` with normalized
``parsed_output``.
"""

from __future__ import annotations

import json
import shlex
from collections.abc import Sequence
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

from oxpwn.core.models import ToolResult
from oxpwn.sandbox.docker import DockerSandbox

logger = structlog.get_logger()


class _HttpxRawRecord(BaseModel):
    """Subset of httpx JSONL fields we normalize into compact output."""

    model_config = ConfigDict(extra="ignore")

    input: str | None = None
    host: str | None = None
    url: str
    scheme: str | None = None
    port: int | None = None
    path: str | None = None
    title: str | None = None
    webserver: str | None = None
    technologies: list[str] = Field(default_factory=list)
    content_length: int | None = Field(default=None, alias="content-length")
    status_code: int | None = Field(default=None, alias="status-code")
    location: str | None = None
    response_time: str | None = Field(default=None, alias="response-time")
    failed: bool = False


class HttpxService(BaseModel):
    """Compact normalized httpx service observation."""

    url: str
    input: str | None = None
    host: str | None = None
    scheme: str | None = None
    port: int | None = None
    path: str | None = None
    status_code: int | None = None
    title: str | None = None
    webserver: str | None = None
    technologies: list[str] = Field(default_factory=list)
    content_length: int | None = None
    location: str | None = None
    response_time_ms: float | None = None
    failed: bool = False


class HttpxParsedOutput(BaseModel):
    """Top-level compact parsed output stored on ``ToolResult.parsed_output``."""

    count: int
    services: list[HttpxService]


def _unique_preserving_order(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_values.append(normalized)
    return unique_values


def _parse_duration_ms(value: str | None) -> float | None:
    if not value:
        return None

    suffixes = {
        "ns": 1_000_000,
        "µs": 1_000,
        "us": 1_000,
        "ms": 1,
        "s": 0.001,
        "m": 1 / 60_000,
    }
    for suffix, divisor in suffixes.items():
        if value.endswith(suffix):
            numeric = float(value[: -len(suffix)])
            return round(numeric / divisor, 3)

    return round(float(value), 3)


def parse_httpx_jsonl(stdout: str) -> dict[str, Any]:
    """Parse ``httpx -json -silent`` output into a compact dict.

    Empty output is treated as a valid scan with zero results. Malformed JSONL
    raises, allowing the executor to degrade to ``parsed_output=None`` while
    preserving raw stdout/stderr for diagnostics.
    """

    services: list[HttpxService] = []
    seen_urls: set[str] = set()

    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        raw_record = _HttpxRawRecord.model_validate(json.loads(line))
        if raw_record.url in seen_urls:
            continue
        seen_urls.add(raw_record.url)

        service = HttpxService(
            url=raw_record.url,
            input=raw_record.input.strip() if raw_record.input else None,
            host=raw_record.host.strip().lower() if raw_record.host else None,
            scheme=raw_record.scheme,
            port=raw_record.port,
            path=raw_record.path,
            status_code=raw_record.status_code,
            title=raw_record.title.strip() if raw_record.title else None,
            webserver=raw_record.webserver,
            technologies=_unique_preserving_order(raw_record.technologies),
            content_length=raw_record.content_length,
            location=raw_record.location,
            response_time_ms=_parse_duration_ms(raw_record.response_time),
            failed=raw_record.failed,
        )
        services.append(service)

    parsed = HttpxParsedOutput(count=len(services), services=services)
    return parsed.model_dump(exclude_defaults=True, exclude_none=True)


class HttpxExecutor:
    """Run httpx inside a :class:`DockerSandbox` and return parsed results."""

    def __init__(self, sandbox: DockerSandbox) -> None:
        self.sandbox = sandbox

    async def run(
        self,
        targets: str | Sequence[str],
        *,
        ports: str | Sequence[int] | None = None,
        path: str | None = None,
        follow_redirects: bool = False,
        tech_detect: bool = True,
        timeout_seconds: int = 5,
        threads: int | None = None,
    ) -> ToolResult:
        """Execute httpx and return a :class:`ToolResult` with parsed JSONL."""

        normalized_targets = _normalize_targets(targets)
        command = _build_httpx_command(
            targets=normalized_targets,
            ports=ports,
            path=path,
            follow_redirects=follow_redirects,
            tech_detect=tech_detect,
            timeout_seconds=timeout_seconds,
            threads=threads,
        )

        result = await self.sandbox.execute(command)
        result.tool_name = "httpx"

        try:
            result.parsed_output = parse_httpx_jsonl(result.stdout)
        except Exception:  # noqa: BLE001 - degrade gracefully for agent loop
            logger.warning(
                "httpx.jsonl_parse_failed",
                command=command,
                stdout_head=result.stdout[:200] if result.stdout else "",
                stderr_head=result.stderr[:200] if result.stderr else "",
            )
            result.parsed_output = None

        return result


def _normalize_targets(targets: str | Sequence[str]) -> list[str]:
    if isinstance(targets, str):
        normalized = [targets.strip()]
    else:
        normalized = [target.strip() for target in targets]

    return [target for target in normalized if target]


def _normalize_ports(ports: str | Sequence[int] | None) -> str | None:
    if ports is None:
        return None
    if isinstance(ports, str):
        return ports.strip() or None
    return ",".join(str(port) for port in ports)


def _build_httpx_command(
    *,
    targets: Sequence[str],
    ports: str | Sequence[int] | None,
    path: str | None,
    follow_redirects: bool,
    tech_detect: bool,
    timeout_seconds: int,
    threads: int | None,
) -> str:
    if not targets:
        msg = "httpx requires at least one target"
        raise ValueError(msg)

    parts = [
        "httpx",
        "-json",
        "-silent",
        "-nc",
        "-probe",
        "-status-code",
        "-content-length",
        "-title",
        "-web-server",
        "-timeout",
        str(timeout_seconds),
    ]
    if tech_detect:
        parts.append("-tech-detect")

    normalized_ports = _normalize_ports(ports)
    if normalized_ports:
        parts.extend(["-p", shlex.quote(normalized_ports)])
    if path:
        parts.extend(["-path", shlex.quote(path)])
    if follow_redirects:
        parts.append("-follow-redirects")
    if threads is not None:
        parts.extend(["-threads", str(threads)])

    tool_command = " ".join(parts)
    delimiter = "__OXPWN_HTTPX_TARGETS__"
    stdin_payload = "\n".join(targets)
    shell_script = f"cat <<'{delimiter}' | {tool_command}\n{stdin_payload}\n{delimiter}"
    return f"sh -lc {shlex.quote(shell_script)}"
