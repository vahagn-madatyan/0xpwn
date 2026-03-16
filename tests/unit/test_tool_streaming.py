"""Unit tests for executor-level live output streaming adoption.

These tests use a fake sandbox to prove the five built-in executors:
- opt into ``execute_stream(...)`` when an ``output_sink`` is supplied,
- keep using buffered ``execute(...)`` for legacy callers, and
- preserve buffered stdout/stderr plus graceful parser degradation.
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import pytest

from oxpwn.core.models import ToolResult
from oxpwn.sandbox.tools import (
    FfufExecutor,
    HttpxExecutor,
    NmapExecutor,
    NucleiExecutor,
    SubfinderExecutor,
)


NMAP_XML_SUCCESS = """\
<?xml version="1.0" encoding="UTF-8"?>
<nmaprun>
  <host>
    <status state="up"/>
    <address addr="127.0.0.1" addrtype="ipv4"/>
    <hostnames/>
    <ports>
      <port protocol="tcp" portid="80">
        <state state="open"/>
        <service name="http"/>
      </port>
    </ports>
  </host>
</nmaprun>
"""

HTTPX_JSONL_SUCCESS = json.dumps(
    {
        "url": "https://app.example.com",
        "input": "app.example.com",
        "status-code": 200,
        "technologies": ["React"],
    }
)

SUBFINDER_JSONL_SUCCESS = json.dumps(
    {
        "host": "api.example.com",
        "input": "example.com",
        "source": "crtsh",
    }
)

NUCLEI_JSONL_SUCCESS = json.dumps(
    {
        "template-id": "deterministic-admin-panel",
        "info": {
            "name": "Deterministic Admin Panel Fixture",
            "severity": "info",
            "description": "Matches the fixture.",
        },
        "type": "http",
        "host": "127.0.0.1",
        "port": "18080",
        "scheme": "http",
        "url": "http://127.0.0.1:18080",
        "matched-at": "http://127.0.0.1:18080/admin/",
        "ip": "127.0.0.1",
    }
)

FFUF_JSON_SUCCESS = json.dumps(
    {
        "input": {"FUZZ": "YWRtaW4="},
        "position": 1,
        "status": 200,
        "url": "http://127.0.0.1:18080/admin",
    }
)


@dataclass(frozen=True)
class StreamingCase:
    tool_name: str
    executor_cls: type[Any]
    run_kwargs: dict[str, Any]
    success_result: ToolResult
    expected_parsed_output: dict[str, Any]
    malformed_result: ToolResult
    warning_patch: str
    warning_event: str
    command_contains: str


class FakeSandbox:
    """Sandbox stub that records which execution path an executor chooses."""

    def __init__(self, result: ToolResult) -> None:
        self._result = result
        self.execute_calls: list[str] = []
        self.execute_stream_calls: list[tuple[str, Any]] = []

    async def execute(self, command: str) -> ToolResult:
        self.execute_calls.append(command)
        return self._result.model_copy(deep=True)

    async def execute_stream(self, command: str, *, output_sink=None) -> ToolResult:
        self.execute_stream_calls.append((command, output_sink))
        if output_sink is not None:
            if self._result.stdout:
                maybe_awaitable = output_sink(chunk=self._result.stdout, stream="stdout")
                if inspect.isawaitable(maybe_awaitable):
                    await maybe_awaitable
            if self._result.stderr:
                maybe_awaitable = output_sink(chunk=self._result.stderr, stream="stderr")
                if inspect.isawaitable(maybe_awaitable):
                    await maybe_awaitable
        return self._result.model_copy(deep=True)


STREAMING_CASES = [
    StreamingCase(
        tool_name="nmap",
        executor_cls=NmapExecutor,
        run_kwargs={"target": "127.0.0.1", "ports": "80", "flags": "-sV"},
        success_result=ToolResult(
            tool_name="sandbox",
            command="ignored",
            stdout=NMAP_XML_SUCCESS,
            stderr="nmap stderr note",
            exit_code=0,
            duration_ms=25,
        ),
        expected_parsed_output={
            "hosts": [
                {
                    "address": "127.0.0.1",
                    "hostnames": [],
                    "status": "up",
                    "ports": [
                        {
                            "port_id": 80,
                            "protocol": "tcp",
                            "state": "open",
                            "service_name": "http",
                            "service_product": "",
                            "service_version": "",
                            "scripts": [],
                        }
                    ],
                }
            ]
        },
        malformed_result=ToolResult(
            tool_name="sandbox",
            command="ignored",
            stdout="not xml at all",
            stderr="failed to resolve target",
            exit_code=1,
            duration_ms=10,
        ),
        warning_patch="oxpwn.sandbox.tools.nmap.logger.warning",
        warning_event="nmap.xml_parse_failed",
        command_contains="nmap -sV -oX - -p 80 127.0.0.1",
    ),
    StreamingCase(
        tool_name="httpx",
        executor_cls=HttpxExecutor,
        run_kwargs={
            "targets": ["https://app.example.com", "https://www.example.com"],
            "ports": [80, 443],
            "path": "/admin",
            "follow_redirects": True,
            "threads": 10,
        },
        success_result=ToolResult(
            tool_name="sandbox",
            command="ignored",
            stdout=HTTPX_JSONL_SUCCESS,
            stderr="httpx stderr note",
            exit_code=0,
            duration_ms=25,
        ),
        expected_parsed_output={
            "count": 1,
            "services": [
                {
                    "url": "https://app.example.com",
                    "input": "app.example.com",
                    "status_code": 200,
                    "technologies": ["React"],
                }
            ],
        },
        malformed_result=ToolResult(
            tool_name="sandbox",
            command="ignored",
            stdout='{"url": "https://app.example.com"}\nnot-json',
            stderr="flag provided but not defined: -u",
            exit_code=1,
            duration_ms=10,
        ),
        warning_patch="oxpwn.sandbox.tools.httpx.logger.warning",
        warning_event="httpx.jsonl_parse_failed",
        command_contains="httpx -json -silent -nc -probe -status-code -content-length -title -web-server",
    ),
    StreamingCase(
        tool_name="subfinder",
        executor_cls=SubfinderExecutor,
        run_kwargs={
            "domains": ["example.com", "example.org"],
            "all_sources": True,
            "recursive": True,
            "timeout_seconds": 15,
            "max_time_minutes": 2,
        },
        success_result=ToolResult(
            tool_name="sandbox",
            command="ignored",
            stdout=SUBFINDER_JSONL_SUCCESS,
            stderr="subfinder stderr note",
            exit_code=0,
            duration_ms=25,
        ),
        expected_parsed_output={
            "count": 1,
            "hosts": [
                {
                    "host": "api.example.com",
                    "inputs": ["example.com"],
                    "sources": ["crtsh"],
                }
            ],
        },
        malformed_result=ToolResult(
            tool_name="sandbox",
            command="ignored",
            stdout='{"host": "api.example.com"}\nnot-json',
            stderr="[ERR] invalid provider config",
            exit_code=1,
            duration_ms=10,
        ),
        warning_patch="oxpwn.sandbox.tools.subfinder.logger.warning",
        warning_event="subfinder.jsonl_parse_failed",
        command_contains="subfinder -oJ -silent -nc -duc -cs",
    ),
    StreamingCase(
        tool_name="nuclei",
        executor_cls=NucleiExecutor,
        run_kwargs={
            "targets": ["http://127.0.0.1:18080"],
            "templates": ["/tmp/oxpwn-tool-suite/nuclei/admin-panel.yaml"],
            "follow_redirects": True,
            "timeout_seconds": 15,
            "retries": 2,
            "rate_limit": 25,
        },
        success_result=ToolResult(
            tool_name="sandbox",
            command="ignored",
            stdout=NUCLEI_JSONL_SUCCESS,
            stderr="nuclei stderr note",
            exit_code=0,
            duration_ms=25,
        ),
        expected_parsed_output={
            "count": 1,
            "findings": [
                {
                    "template_id": "deterministic-admin-panel",
                    "name": "Deterministic Admin Panel Fixture",
                    "severity": "info",
                    "type": "http",
                    "matched_at": "http://127.0.0.1:18080/admin/",
                    "host": "127.0.0.1",
                    "ip": "127.0.0.1",
                    "port": 18080,
                    "scheme": "http",
                    "url": "http://127.0.0.1:18080",
                    "description": "Matches the fixture.",
                }
            ],
        },
        malformed_result=ToolResult(
            tool_name="sandbox",
            command="ignored",
            stdout='{"template-id": "deterministic-admin-panel"}\nnot-json',
            stderr="[ERR] invalid template catalog",
            exit_code=1,
            duration_ms=10,
        ),
        warning_patch="oxpwn.sandbox.tools.nuclei.logger.warning",
        warning_event="nuclei.jsonl_parse_failed",
        command_contains="nuclei -jsonl -silent -nc -duc -omit-raw -omit-template",
    ),
    StreamingCase(
        tool_name="ffuf",
        executor_cls=FfufExecutor,
        run_kwargs={
            "url": "http://127.0.0.1:18080/FUZZ",
            "follow_redirects": True,
            "timeout_seconds": 15,
            "threads": 25,
        },
        success_result=ToolResult(
            tool_name="sandbox",
            command="ignored",
            stdout=FFUF_JSON_SUCCESS,
            stderr="ffuf stderr note",
            exit_code=0,
            duration_ms=25,
        ),
        expected_parsed_output={
            "count": 1,
            "findings": [
                {
                    "position": 1,
                    "url": "http://127.0.0.1:18080/admin",
                    "status": 200,
                    "inputs": {"FUZZ": "admin"},
                }
            ],
        },
        malformed_result=ToolResult(
            tool_name="sandbox",
            command="ignored",
            stdout='{"position": 1, "status": 200, "url": "http://127.0.0.1:18080/admin"}\nnot-json',
            stderr="flag provided but not defined: -input-cmd",
            exit_code=1,
            duration_ms=10,
        ),
        warning_patch="oxpwn.sandbox.tools.ffuf.logger.warning",
        warning_event="ffuf.json_parse_failed",
        command_contains="ffuf -json -s -noninteractive -mc all",
    ),
]


@pytest.mark.parametrize("case", STREAMING_CASES, ids=[case.tool_name for case in STREAMING_CASES])
async def test_executors_use_streaming_path_when_output_sink_is_supplied(case: StreamingCase) -> None:
    sandbox = FakeSandbox(case.success_result)
    executor = case.executor_cls(sandbox)
    streamed_chunks: list[tuple[str, str]] = []

    async def output_sink(*, chunk: str, stream: str) -> None:
        streamed_chunks.append((stream, chunk))

    result = await executor.run(output_sink=output_sink, **case.run_kwargs)

    assert sandbox.execute_calls == []
    assert len(sandbox.execute_stream_calls) == 1

    command, forwarded_sink = sandbox.execute_stream_calls[0]
    assert forwarded_sink is output_sink
    assert case.command_contains in command

    assert result.tool_name == case.tool_name
    assert result.stdout == case.success_result.stdout
    assert result.stderr == case.success_result.stderr
    assert result.parsed_output == case.expected_parsed_output
    assert streamed_chunks == [
        ("stdout", case.success_result.stdout),
        ("stderr", case.success_result.stderr),
    ]


@pytest.mark.parametrize("case", STREAMING_CASES, ids=[case.tool_name for case in STREAMING_CASES])
async def test_executors_keep_buffered_execute_path_without_output_sink(case: StreamingCase) -> None:
    sandbox = FakeSandbox(case.success_result)
    executor = case.executor_cls(sandbox)

    result = await executor.run(**case.run_kwargs)

    assert len(sandbox.execute_calls) == 1
    assert sandbox.execute_stream_calls == []
    assert case.command_contains in sandbox.execute_calls[0]
    assert result.tool_name == case.tool_name
    assert result.stdout == case.success_result.stdout
    assert result.stderr == case.success_result.stderr
    assert result.parsed_output == case.expected_parsed_output


@pytest.mark.parametrize("case", STREAMING_CASES, ids=[case.tool_name for case in STREAMING_CASES])
async def test_streaming_path_parse_failures_degrade_to_none_with_diagnostics(case: StreamingCase) -> None:
    sandbox = FakeSandbox(case.malformed_result)
    executor = case.executor_cls(sandbox)
    streamed_chunks: list[tuple[str, str]] = []

    async def output_sink(*, chunk: str, stream: str) -> None:
        streamed_chunks.append((stream, chunk))

    with patch(case.warning_patch) as mock_warning:
        result = await executor.run(output_sink=output_sink, **case.run_kwargs)

    assert sandbox.execute_calls == []
    assert len(sandbox.execute_stream_calls) == 1
    command, forwarded_sink = sandbox.execute_stream_calls[0]
    assert forwarded_sink is output_sink
    assert case.command_contains in command

    assert result.tool_name == case.tool_name
    assert result.stdout == case.malformed_result.stdout
    assert result.stderr == case.malformed_result.stderr
    assert result.parsed_output is None
    assert result.exit_code == case.malformed_result.exit_code
    assert streamed_chunks == [
        ("stdout", case.malformed_result.stdout),
        ("stderr", case.malformed_result.stderr),
    ]

    mock_warning.assert_called_once()
    args, kwargs = mock_warning.call_args
    assert args == (case.warning_event,)
    assert case.command_contains in kwargs["command"]
    assert kwargs["stdout_head"] == case.malformed_result.stdout[:200]
    assert kwargs["stderr_head"] == case.malformed_result.stderr[:200]
