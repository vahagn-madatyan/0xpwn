"""ffuf JSON parser and sandbox executor.

Provides a compact, typed wrapper around ``ffuf`` using machine-readable JSON
output only. The executor follows the S02 ``NmapExecutor`` contract:
constructor takes a ``DockerSandbox`` and ``run()`` returns a ``ToolResult``
with normalized ``parsed_output``.
"""

from __future__ import annotations

import base64
import json
import re
import shlex
from collections.abc import Mapping
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

from oxpwn.core.models import ToolResult
from oxpwn.sandbox.docker import DockerSandbox

logger = structlog.get_logger()

DEFAULT_FFUF_WORDLIST_PATH = "/tmp/oxpwn-tool-suite/ffuf-wordlist.txt"
_ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


class _FfufRawRecord(BaseModel):
    """Subset of ffuf JSON fields we normalize into compact findings."""

    model_config = ConfigDict(extra="ignore")

    input: dict[str, str] = Field(default_factory=dict)
    position: int
    status: int
    length: int | None = None
    words: int | None = None
    lines: int | None = None
    content_type: str | None = Field(default=None, alias="content-type")
    redirect_location: str | None = Field(default=None, alias="redirectlocation")
    url: str
    duration: int | None = None
    host: str | None = None


class FfufFinding(BaseModel):
    """Compact normalized ffuf finding."""

    position: int
    url: str
    status: int
    inputs: dict[str, str] = Field(default_factory=dict)
    host: str | None = None
    redirect_location: str | None = None
    content_type: str | None = None
    content_length: int | None = None
    words: int | None = None
    lines: int | None = None
    duration_ms: float | None = None


class FfufParsedOutput(BaseModel):
    """Top-level compact parsed output stored on ``ToolResult.parsed_output``."""

    count: int
    findings: list[FfufFinding]


def _strip_terminal_noise(stdout: str) -> str:
    cleaned = _ANSI_ESCAPE_RE.sub("", stdout)
    return cleaned.replace("\r", "")


def _decode_ffuf_input(value: str) -> str:
    padded = value + "=" * (-len(value) % 4)
    try:
        decoded = base64.b64decode(padded, validate=True)
    except Exception:  # noqa: BLE001 - fallback to the original token if not base64
        return value

    try:
        return decoded.decode("utf-8")
    except UnicodeDecodeError:
        return decoded.decode("utf-8", errors="replace")


def _normalize_inputs(values: Mapping[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in sorted(values.items()):
        if key == "FFUFHASH":
            continue
        normalized[key] = _decode_ffuf_input(value)
    return normalized


def _duration_ns_to_ms(value: int | None) -> float | None:
    if value is None:
        return None
    return round(value / 1_000_000, 3)


def parse_ffuf_json(stdout: str) -> dict[str, Any]:
    """Parse ``ffuf -json`` output into a compact dict.

    Empty output is treated as a valid scan with zero results. Malformed JSON
    raises, allowing the executor to degrade to ``parsed_output=None`` while
    preserving raw stdout/stderr for diagnostics.
    """

    findings: list[FfufFinding] = []

    cleaned_stdout = _strip_terminal_noise(stdout)
    for raw_line in cleaned_stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        raw_record = _FfufRawRecord.model_validate(json.loads(line))
        findings.append(
            FfufFinding(
                position=raw_record.position,
                url=raw_record.url,
                status=raw_record.status,
                inputs=_normalize_inputs(raw_record.input),
                host=raw_record.host,
                redirect_location=raw_record.redirect_location or None,
                content_type=raw_record.content_type or None,
                content_length=raw_record.length,
                words=raw_record.words,
                lines=raw_record.lines,
                duration_ms=_duration_ns_to_ms(raw_record.duration),
            )
        )

    findings.sort(key=lambda finding: finding.position)
    parsed = FfufParsedOutput(count=len(findings), findings=findings)
    return parsed.model_dump(exclude_defaults=True, exclude_none=True)


class FfufExecutor:
    """Run ffuf inside a :class:`DockerSandbox` and return parsed results."""

    def __init__(self, sandbox: DockerSandbox) -> None:
        self.sandbox = sandbox

    async def run(
        self,
        url: str,
        *,
        wordlist_path: str = DEFAULT_FFUF_WORDLIST_PATH,
        follow_redirects: bool = False,
        match_status: str = "all",
        timeout_seconds: int = 10,
        threads: int | None = None,
    ) -> ToolResult:
        """Execute ffuf and return a :class:`ToolResult` with parsed JSON."""

        command = _build_ffuf_command(
            url=url,
            wordlist_path=wordlist_path,
            follow_redirects=follow_redirects,
            match_status=match_status,
            timeout_seconds=timeout_seconds,
            threads=threads,
        )

        result = await self.sandbox.execute(command)
        result.tool_name = "ffuf"

        try:
            result.parsed_output = parse_ffuf_json(result.stdout)
        except Exception:  # noqa: BLE001 - degrade gracefully for agent loop
            logger.warning(
                "ffuf.json_parse_failed",
                command=command,
                stdout_head=result.stdout[:200] if result.stdout else "",
                stderr_head=result.stderr[:200] if result.stderr else "",
            )
            result.parsed_output = None

        return result


def _build_ffuf_command(
    *,
    url: str,
    wordlist_path: str,
    follow_redirects: bool,
    match_status: str,
    timeout_seconds: int,
    threads: int | None,
) -> str:
    normalized_url = url.strip()
    if not normalized_url:
        msg = "ffuf requires a target url"
        raise ValueError(msg)
    if "FUZZ" not in normalized_url:
        msg = "ffuf requires the target url to contain the FUZZ keyword"
        raise ValueError(msg)

    normalized_wordlist = wordlist_path.strip()
    if not normalized_wordlist:
        msg = "ffuf requires a wordlist path"
        raise ValueError(msg)

    parts = [
        "ffuf",
        "-json",
        "-s",
        "-noninteractive",
        "-mc",
        shlex.quote(match_status),
        "-w",
        shlex.quote(normalized_wordlist),
        "-u",
        shlex.quote(normalized_url),
        "-timeout",
        str(timeout_seconds),
    ]
    if follow_redirects:
        parts.append("-r")
    if threads is not None:
        parts.extend(["-t", str(threads)])

    return " ".join(parts)
