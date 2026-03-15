"""Unit tests for subfinder JSONL parser and SubfinderExecutor.

All tests run without Docker — sandbox calls are mocked.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from oxpwn.core.models import ToolResult
from oxpwn.sandbox.tools.subfinder import SubfinderExecutor, parse_subfinder_jsonl

SUBFINDER_JSONL_TYPICAL = "\n".join(
    [
        json.dumps({"host": "Api.Example.com", "input": "example.com", "source": "crtsh"}),
        json.dumps({"host": "api.example.com.", "input": "example.com", "sources": ["github", "crtsh"]}),
        json.dumps({"host": "www.example.com", "input": "example.com", "source": "waybackarchive"}),
    ]
)


class TestParseSubfinderJsonl:
    """Unit tests for parse_subfinder_jsonl()."""

    def test_typical_output_dedupes_hosts_and_merges_sources(self) -> None:
        result = parse_subfinder_jsonl(SUBFINDER_JSONL_TYPICAL)

        assert result["count"] == 2
        assert len(result["hosts"]) == 2

        api = result["hosts"][0]
        assert api == {
            "host": "api.example.com",
            "inputs": ["example.com"],
            "sources": ["crtsh", "github"],
        }

        www = result["hosts"][1]
        assert www == {
            "host": "www.example.com",
            "inputs": ["example.com"],
            "sources": ["waybackarchive"],
        }

    def test_empty_output_returns_empty_hosts(self) -> None:
        assert parse_subfinder_jsonl("") == {"count": 0, "hosts": []}
        assert parse_subfinder_jsonl("\n\n") == {"count": 0, "hosts": []}

    def test_malformed_json_raises(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            parse_subfinder_jsonl('{"host": "api.example.com"}\nnot-json')


class TestSubfinderExecutor:
    """Unit tests for SubfinderExecutor with mocked DockerSandbox."""

    @pytest.fixture()
    def mock_sandbox(self) -> MagicMock:
        sandbox = MagicMock()
        sandbox.execute = AsyncMock(
            return_value=ToolResult(
                tool_name="sandbox",
                command="subfinder ...",
                stdout=SUBFINDER_JSONL_TYPICAL,
                stderr="",
                exit_code=0,
                duration_ms=1800,
            )
        )
        return sandbox

    async def test_run_builds_curated_command_and_parses_output(
        self,
        mock_sandbox: MagicMock,
    ) -> None:
        executor = SubfinderExecutor(mock_sandbox)
        result = await executor.run(
            ["example.com", "example.org"],
            all_sources=True,
            recursive=True,
            timeout_seconds=15,
            max_time_minutes=2,
        )

        command = mock_sandbox.execute.call_args[0][0]
        assert command.startswith("subfinder -oJ -silent -nc -duc -cs")
        assert "-d example.com" in command
        assert "-d example.org" in command
        assert "-all" in command
        assert "-recursive" in command
        assert "-timeout 15" in command
        assert "-max-time 2" in command

        assert result.tool_name == "subfinder"
        assert result.parsed_output is not None
        assert result.parsed_output["count"] == 2

    async def test_run_parse_failure_degrades_to_none_and_warns(
        self,
        mock_sandbox: MagicMock,
    ) -> None:
        mock_sandbox.execute.return_value = ToolResult(
            tool_name="sandbox",
            command="subfinder ...",
            stdout='{"host": "api.example.com"}\nnot-json',
            stderr="[ERR] invalid provider config",
            exit_code=1,
            duration_ms=40,
        )

        executor = SubfinderExecutor(mock_sandbox)
        with patch("oxpwn.sandbox.tools.subfinder.logger.warning") as mock_warning:
            result = await executor.run("example.com")

        assert result.tool_name == "subfinder"
        assert result.parsed_output is None
        assert result.exit_code == 1
        mock_warning.assert_called_once()
        args, kwargs = mock_warning.call_args
        assert args == ("subfinder.jsonl_parse_failed",)
        assert kwargs["command"].startswith("subfinder -oJ -silent")
        assert kwargs["stdout_head"].endswith("not-json")
        assert kwargs["stderr_head"] == "[ERR] invalid provider config"
