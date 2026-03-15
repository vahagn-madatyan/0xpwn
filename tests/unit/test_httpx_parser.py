"""Unit tests for httpx JSONL parser and HttpxExecutor.

All tests run without Docker — sandbox calls are mocked.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from oxpwn.core.models import ToolResult
from oxpwn.sandbox.tools.httpx import HttpxExecutor, parse_httpx_jsonl

HTTPX_JSONL_TYPICAL = "\n".join(
    [
        json.dumps(
            {
                "timestamp": "2026-03-15T03:10:51.692131758Z",
                "scheme": "https",
                "port": "443",
                "path": "/",
                "url": "https://app.example.com",
                "input": "app.example.com",
                "title": "ACME Portal",
                "webserver": "nginx",
                "content-length": 512,
                "status-code": 200,
                "response-time": "123.456ms",
                "technologies": ["Next.js", "React", "React"],
                "failed": False,
            }
        ),
        json.dumps(
            {
                "timestamp": "2026-03-15T03:10:52.692131758Z",
                "scheme": "http",
                "port": "8080",
                "path": "/admin",
                "url": "http://app.example.com:8080/admin",
                "input": "app.example.com",
                "host": "app.example.com",
                "title": "Admin Login",
                "webserver": "Caddy",
                "content-length": 128,
                "status-code": 302,
                "location": "https://app.example.com/login",
                "response-time": "1.5s",
                "technologies": ["Caddy"],
                "failed": False,
            }
        ),
    ]
)


class TestParseHttpxJsonl:
    """Unit tests for parse_httpx_jsonl()."""

    def test_typical_scan_normalizes_compact_services(self) -> None:
        result = parse_httpx_jsonl(HTTPX_JSONL_TYPICAL)

        assert result["count"] == 2
        assert len(result["services"]) == 2

        first = result["services"][0]
        assert first["url"] == "https://app.example.com"
        assert first["input"] == "app.example.com"
        assert first["status_code"] == 200
        assert first["title"] == "ACME Portal"
        assert first["webserver"] == "nginx"
        assert first["content_length"] == 512
        assert first["response_time_ms"] == 123.456
        assert first["technologies"] == ["Next.js", "React"]
        assert "failed" not in first

        second = result["services"][1]
        assert second["url"] == "http://app.example.com:8080/admin"
        assert second["host"] == "app.example.com"
        assert second["path"] == "/admin"
        assert second["status_code"] == 302
        assert second["location"] == "https://app.example.com/login"
        assert second["response_time_ms"] == 1500.0

    def test_empty_output_returns_empty_services(self) -> None:
        assert parse_httpx_jsonl("") == {"count": 0, "services": []}
        assert parse_httpx_jsonl("\n\n") == {"count": 0, "services": []}

    def test_duplicate_urls_are_deduped(self) -> None:
        duplicate_output = "\n".join([HTTPX_JSONL_TYPICAL.splitlines()[0], HTTPX_JSONL_TYPICAL.splitlines()[0]])
        result = parse_httpx_jsonl(duplicate_output)

        assert result == {"count": 1, "services": [result["services"][0]]}
        assert result["services"][0]["url"] == "https://app.example.com"

    def test_malformed_json_raises(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            parse_httpx_jsonl('{"url": "https://app.example.com"}\nnot-json')


class TestHttpxExecutor:
    """Unit tests for HttpxExecutor with mocked DockerSandbox."""

    @pytest.fixture()
    def mock_sandbox(self) -> MagicMock:
        sandbox = MagicMock()
        sandbox.execute = AsyncMock(
            return_value=ToolResult(
                tool_name="sandbox",
                command="httpx ...",
                stdout=HTTPX_JSONL_TYPICAL,
                stderr="",
                exit_code=0,
                duration_ms=250,
            )
        )
        return sandbox

    async def test_run_builds_shell_wrapped_command_and_parses_output(
        self,
        mock_sandbox: MagicMock,
    ) -> None:
        executor = HttpxExecutor(mock_sandbox)
        result = await executor.run(
            ["https://app.example.com", "http://app.example.com:8080"],
            ports=[80, 443, 8080],
            path="/admin",
            follow_redirects=True,
            timeout_seconds=10,
            threads=25,
        )

        command = mock_sandbox.execute.call_args[0][0]
        assert command.startswith("sh -lc ")
        assert "httpx -json -silent -nc -probe -status-code -content-length -title -web-server" in command
        assert "-tech-detect" in command
        assert "-p 80,443,8080" in command
        assert "-path /admin" in command
        assert "-follow-redirects" in command
        assert "-timeout 10" in command
        assert "-threads 25" in command
        assert "https://app.example.com" in command
        assert "http://app.example.com:8080" in command

        assert result.tool_name == "httpx"
        assert result.parsed_output is not None
        assert result.parsed_output["count"] == 2

    async def test_run_can_disable_tech_detect(self, mock_sandbox: MagicMock) -> None:
        executor = HttpxExecutor(mock_sandbox)
        await executor.run("https://app.example.com", tech_detect=False)

        command = mock_sandbox.execute.call_args[0][0]
        assert "-tech-detect" not in command

    async def test_run_parse_failure_degrades_to_none_and_warns(
        self,
        mock_sandbox: MagicMock,
    ) -> None:
        mock_sandbox.execute.return_value = ToolResult(
            tool_name="sandbox",
            command="httpx ...",
            stdout='{"url": "https://app.example.com"}\nnot-json',
            stderr="flag provided but not defined: -u",
            exit_code=1,
            duration_ms=50,
        )

        executor = HttpxExecutor(mock_sandbox)
        with patch("oxpwn.sandbox.tools.httpx.logger.warning") as mock_warning:
            result = await executor.run("https://app.example.com")

        assert result.tool_name == "httpx"
        assert result.parsed_output is None
        assert result.exit_code == 1
        mock_warning.assert_called_once()
        args, kwargs = mock_warning.call_args
        assert args == ("httpx.jsonl_parse_failed",)
        assert "httpx -json -silent" in kwargs["command"]
        assert kwargs["stdout_head"].endswith("not-json")
        assert kwargs["stderr_head"] == "flag provided but not defined: -u"
