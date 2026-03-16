"""nuclei JSONL parser and sandbox executor.

Provides a compact, typed wrapper around ``nuclei`` using JSONL output only.
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
from oxpwn.sandbox.docker import DockerSandbox, SandboxOutputSink

logger = structlog.get_logger()


class _NucleiRawInfo(BaseModel):
    """Subset of nuclei info metadata we normalize into compact output."""

    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    severity: str | None = None
    description: str | None = None


class _NucleiRawRecord(BaseModel):
    """Subset of nuclei JSONL fields we normalize into compact findings."""

    model_config = ConfigDict(extra="ignore")

    template_id: str = Field(default="", alias="template-id")
    template_path: str | None = Field(default=None, alias="template-path")
    info: _NucleiRawInfo = Field(default_factory=_NucleiRawInfo)
    type: str | None = None
    host: str | None = None
    port: str | None = None
    scheme: str | None = None
    url: str | None = None
    matched_at: str | None = Field(default=None, alias="matched-at")
    ip: str | None = None


class NucleiFinding(BaseModel):
    """Compact normalized nuclei finding."""

    template_id: str
    name: str | None = None
    severity: str | None = None
    type: str | None = None
    matched_at: str | None = None
    host: str | None = None
    ip: str | None = None
    port: int | None = None
    scheme: str | None = None
    url: str | None = None
    description: str | None = None


class NucleiParsedOutput(BaseModel):
    """Top-level compact parsed output stored on ``ToolResult.parsed_output``."""

    count: int
    findings: list[NucleiFinding]


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    return int(value)


def parse_nuclei_jsonl(stdout: str) -> dict[str, Any]:
    """Parse ``nuclei -jsonl -silent`` output into a compact dict.

    Empty output is treated as a valid scan with zero results. Malformed JSONL
    raises, allowing the executor to degrade to ``parsed_output=None`` while
    preserving raw stdout/stderr for diagnostics.
    """

    findings: list[NucleiFinding] = []
    seen_findings: set[tuple[str, str]] = set()

    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        raw_record = _NucleiRawRecord.model_validate(json.loads(line))
        dedupe_key = (raw_record.template_id, raw_record.matched_at or raw_record.url or "")
        if dedupe_key in seen_findings:
            continue
        seen_findings.add(dedupe_key)

        findings.append(
            NucleiFinding(
                template_id=raw_record.template_id,
                name=raw_record.info.name.strip() if raw_record.info.name else None,
                severity=raw_record.info.severity,
                type=raw_record.type,
                matched_at=raw_record.matched_at,
                host=raw_record.host,
                ip=raw_record.ip,
                port=_parse_int(raw_record.port),
                scheme=raw_record.scheme,
                url=raw_record.url,
                description=raw_record.info.description.strip() if raw_record.info.description else None,
            )
        )

    parsed = NucleiParsedOutput(count=len(findings), findings=findings)
    return parsed.model_dump(exclude_defaults=True, exclude_none=True)


class NucleiExecutor:
    """Run nuclei inside a :class:`DockerSandbox` and return parsed results."""

    def __init__(self, sandbox: DockerSandbox) -> None:
        self.sandbox = sandbox

    async def run(
        self,
        targets: str | Sequence[str],
        *,
        templates: str | Sequence[str],
        follow_redirects: bool = False,
        timeout_seconds: int = 10,
        retries: int = 1,
        rate_limit: int | None = None,
        output_sink: SandboxOutputSink | None = None,
    ) -> ToolResult:
        """Execute nuclei and return a :class:`ToolResult` with parsed JSONL."""

        normalized_targets = _normalize_values(targets)
        normalized_templates = _normalize_values(templates)
        command = _build_nuclei_command(
            targets=normalized_targets,
            templates=normalized_templates,
            follow_redirects=follow_redirects,
            timeout_seconds=timeout_seconds,
            retries=retries,
            rate_limit=rate_limit,
        )

        result = (
            await self.sandbox.execute_stream(command, output_sink=output_sink)
            if output_sink is not None
            else await self.sandbox.execute(command)
        )
        result.tool_name = "nuclei"

        try:
            result.parsed_output = parse_nuclei_jsonl(result.stdout)
        except Exception:  # noqa: BLE001 - degrade gracefully for agent loop
            logger.warning(
                "nuclei.jsonl_parse_failed",
                command=command,
                stdout_head=result.stdout[:200] if result.stdout else "",
                stderr_head=result.stderr[:200] if result.stderr else "",
            )
            result.parsed_output = None

        return result


def _normalize_values(values: str | Sequence[str]) -> list[str]:
    if isinstance(values, str):
        normalized = [values.strip()]
    else:
        normalized = [value.strip() for value in values]

    return [value for value in normalized if value]


def _build_nuclei_command(
    *,
    targets: Sequence[str],
    templates: Sequence[str],
    follow_redirects: bool,
    timeout_seconds: int,
    retries: int,
    rate_limit: int | None,
) -> str:
    if not targets:
        msg = "nuclei requires at least one target"
        raise ValueError(msg)
    if not templates:
        msg = "nuclei requires at least one template"
        raise ValueError(msg)

    parts = [
        "nuclei",
        "-jsonl",
        "-silent",
        "-nc",
        "-duc",
        "-omit-raw",
        "-omit-template",
        "-timeout",
        str(timeout_seconds),
        "-retries",
        str(retries),
    ]
    for target in targets:
        parts.extend(["-u", shlex.quote(target)])
    for template in templates:
        parts.extend(["-t", shlex.quote(template)])
    if follow_redirects:
        parts.append("-fr")
    if rate_limit is not None:
        parts.extend(["-rl", str(rate_limit)])

    return " ".join(parts)
