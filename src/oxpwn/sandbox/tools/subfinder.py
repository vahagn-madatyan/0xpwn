"""subfinder JSONL parser and sandbox executor.

Provides a compact, typed wrapper around ``subfinder`` using JSONL output only.
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


class _SubfinderRawRecord(BaseModel):
    """Subset of subfinder JSONL fields we normalize into compact output."""

    model_config = ConfigDict(extra="ignore")

    host: str
    input: str | None = None
    source: str | None = None
    sources: list[str] = Field(default_factory=list)


class SubfinderHost(BaseModel):
    """Compact normalized subfinder host observation."""

    host: str
    inputs: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class SubfinderParsedOutput(BaseModel):
    """Top-level compact parsed output stored on ``ToolResult.parsed_output``."""

    count: int
    hosts: list[SubfinderHost]


def _normalize_hostname(value: str) -> str:
    return value.strip().rstrip(".").lower()


def _unique_sorted(values: Sequence[str]) -> list[str]:
    normalized = {_normalize_hostname(value) for value in values if value.strip()}
    return sorted(normalized)


def parse_subfinder_jsonl(stdout: str) -> dict[str, Any]:
    """Parse ``subfinder -oJ`` output into a compact dict.

    Empty output is treated as a valid scan with zero results. Malformed JSONL
    raises, allowing the executor to degrade to ``parsed_output=None`` while
    preserving raw stdout/stderr for diagnostics.
    """

    aggregated: dict[str, dict[str, list[str]]] = {}

    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        raw_record = _SubfinderRawRecord.model_validate(json.loads(line))
        host = _normalize_hostname(raw_record.host)
        bucket = aggregated.setdefault(host, {"inputs": [], "sources": []})

        if raw_record.input:
            bucket["inputs"].append(raw_record.input)
        if raw_record.source:
            bucket["sources"].append(raw_record.source)
        bucket["sources"].extend(raw_record.sources)

    hosts = [
        SubfinderHost(
            host=host,
            inputs=_unique_sorted(values["inputs"]),
            sources=_unique_sorted(values["sources"]),
        )
        for host, values in sorted(aggregated.items())
    ]

    parsed = SubfinderParsedOutput(count=len(hosts), hosts=hosts)
    return parsed.model_dump(exclude_defaults=True, exclude_none=True)


class SubfinderExecutor:
    """Run subfinder inside a :class:`DockerSandbox` and return parsed results."""

    def __init__(self, sandbox: DockerSandbox) -> None:
        self.sandbox = sandbox

    async def run(
        self,
        domains: str | Sequence[str],
        *,
        all_sources: bool = False,
        recursive: bool = False,
        timeout_seconds: int = 30,
        max_time_minutes: int = 10,
    ) -> ToolResult:
        """Execute subfinder and return a :class:`ToolResult` with parsed JSONL."""

        normalized_domains = _normalize_domains(domains)
        command = _build_subfinder_command(
            domains=normalized_domains,
            all_sources=all_sources,
            recursive=recursive,
            timeout_seconds=timeout_seconds,
            max_time_minutes=max_time_minutes,
        )

        result = await self.sandbox.execute(command)
        result.tool_name = "subfinder"

        try:
            result.parsed_output = parse_subfinder_jsonl(result.stdout)
        except Exception:  # noqa: BLE001 - degrade gracefully for agent loop
            logger.warning(
                "subfinder.jsonl_parse_failed",
                command=command,
                stdout_head=result.stdout[:200] if result.stdout else "",
                stderr_head=result.stderr[:200] if result.stderr else "",
            )
            result.parsed_output = None

        return result


def _normalize_domains(domains: str | Sequence[str]) -> list[str]:
    if isinstance(domains, str):
        normalized = [domains.strip()]
    else:
        normalized = [domain.strip() for domain in domains]

    return [domain for domain in normalized if domain]


def _build_subfinder_command(
    *,
    domains: Sequence[str],
    all_sources: bool,
    recursive: bool,
    timeout_seconds: int,
    max_time_minutes: int,
) -> str:
    if not domains:
        msg = "subfinder requires at least one domain"
        raise ValueError(msg)

    parts = ["subfinder", "-oJ", "-silent", "-nc", "-duc", "-cs"]
    for domain in domains:
        parts.extend(["-d", shlex.quote(domain)])
    if all_sources:
        parts.append("-all")
    if recursive:
        parts.append("-recursive")
    parts.extend(["-timeout", str(timeout_seconds), "-max-time", str(max_time_minutes)])
    return " ".join(parts)
