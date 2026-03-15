"""Unit tests for ffuf JSON parser and FfufExecutor.

All tests run without Docker — sandbox calls are mocked.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from oxpwn.core.models import ToolResult
from oxpwn.sandbox.tools.ffuf import DEFAULT_FFUF_WORDLIST_PATH, FfufExecutor, parse_ffuf_json

FFUF_JSON_TYPICAL = "\n".join(
    [
        "\r\u001b[2K",
        json.dumps(
            {
                "input": {"FFUFHASH": "ZDhmNWIx", "FUZZ": "YWRtaW4="},
                "position": 1,
                "status": 301,
                "length": 0,
                "words": 1,
                "lines": 1,
                "content-type": "",
                "redirectlocation": "/admin/",
                "url": "http://127.0.0.1:18080/admin",
                "duration": 506416,
                "host": "127.0.0.1:18080",
            }
        ),
        json.dumps(
            {
                "input": {"FFUFHASH": "ZDhmNWIy", "FUZZ": "bG9naW4="},
                "position": 2,
                "status": 404,
                "length": 335,
                "words": 84,
                "lines": 14,
                "content-type": "text/html;charset=utf-8",
                "redirectlocation": "",
                "url": "http://127.0.0.1:18080/login",
                "duration": 1037208,
                "host": "127.0.0.1:18080",
            }
        ),
    ]
)


class TestParseFfufJson:
    """Unit tests for parse_ffuf_json()."""

    def test_typical_output_decodes_base64_inputs_and_normalizes_findings(self) -> None:
        result = parse_ffuf_json(FFUF_JSON_TYPICAL)

        assert result["count"] == 2
        assert len(result["findings"]) == 2

        first = result["findings"][0]
        assert first == {
            "position": 1,
            "url": "http://127.0.0.1:18080/admin",
            "status": 301,
            "inputs": {"FUZZ": "admin"},
            "host": "127.0.0.1:18080",
            "redirect_location": "/admin/",
            "content_length": 0,
            "words": 1,
            "lines": 1,
            "duration_ms": 0.506,
        }

        second = result["findings"][1]
        assert second["inputs"] == {"FUZZ": "login"}
        assert second["content_type"] == "text/html;charset=utf-8"
        assert second["duration_ms"] == 1.037

    def test_empty_output_returns_empty_findings(self) -> None:
        assert parse_ffuf_json("") == {"count": 0, "findings": []}
        assert parse_ffuf_json("\r\u001b[2K\n\r\u001b[2K") == {"count": 0, "findings": []}

    def test_invalid_base64_input_falls_back_to_original_value(self) -> None:
        stdout = json.dumps(
            {
                "input": {"FUZZ": "not-base64%%%"},
                "position": 7,
                "status": 200,
                "url": "http://127.0.0.1:18080/not-base64%%%",
            }
        )

        result = parse_ffuf_json(stdout)
        assert result["findings"][0]["inputs"] == {"FUZZ": "not-base64%%%"}

    def test_malformed_json_raises(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            parse_ffuf_json(
                '{"input": {"FUZZ": "YWRtaW4="}, "position": 1, "status": 200, '
                '"url": "http://127.0.0.1:18080/admin"}\nnot-json'
            )


class TestFfufExecutor:
    """Unit tests for FfufExecutor with mocked DockerSandbox."""

    @pytest.fixture()
    def mock_sandbox(self) -> MagicMock:
        sandbox = MagicMock()
        sandbox.execute = AsyncMock(
            return_value=ToolResult(
                tool_name="sandbox",
                command="ffuf ...",
                stdout=FFUF_JSON_TYPICAL,
                stderr="",
                exit_code=0,
                duration_ms=410,
            )
        )
        return sandbox

    async def test_run_builds_curated_command_and_parses_output(
        self,
        mock_sandbox: MagicMock,
    ) -> None:
        executor = FfufExecutor(mock_sandbox)
        result = await executor.run(
            "http://127.0.0.1:18080/FUZZ",
            follow_redirects=True,
            timeout_seconds=15,
            threads=25,
        )

        command = mock_sandbox.execute.call_args[0][0]
        assert command.startswith("ffuf -json -s -noninteractive -mc all")
        assert f"-w {DEFAULT_FFUF_WORDLIST_PATH}" in command
        assert "-u http://127.0.0.1:18080/FUZZ" in command
        assert "-r" in command
        assert "-timeout 15" in command
        assert "-t 25" in command

        assert result.tool_name == "ffuf"
        assert result.parsed_output is not None
        assert result.parsed_output["count"] == 2

    async def test_run_parse_failure_degrades_to_none_and_warns(
        self,
        mock_sandbox: MagicMock,
    ) -> None:
        mock_sandbox.execute.return_value = ToolResult(
            tool_name="sandbox",
            command="ffuf ...",
            stdout='{"status": 200, "url": "http://127.0.0.1:18080/admin"}\nnot-json',
            stderr="flag provided but not defined: -input-cmd",
            exit_code=1,
            duration_ms=35,
        )

        executor = FfufExecutor(mock_sandbox)
        with patch("oxpwn.sandbox.tools.ffuf.logger.warning") as mock_warning:
            result = await executor.run("http://127.0.0.1:18080/FUZZ")

        assert result.tool_name == "ffuf"
        assert result.parsed_output is None
        assert result.exit_code == 1
        mock_warning.assert_called_once()
        args, kwargs = mock_warning.call_args
        assert args == ("ffuf.json_parse_failed",)
        assert kwargs["command"].startswith("ffuf -json -s -noninteractive")
        assert kwargs["stdout_head"].endswith("not-json")
        assert kwargs["stderr_head"] == "flag provided but not defined: -input-cmd"

    async def test_run_requires_fuzz_keyword_in_url(self, mock_sandbox: MagicMock) -> None:
        executor = FfufExecutor(mock_sandbox)
        with pytest.raises(ValueError, match="FUZZ keyword"):
            await executor.run("http://127.0.0.1:18080/admin")
