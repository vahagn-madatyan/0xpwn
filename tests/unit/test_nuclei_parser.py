"""Unit tests for nuclei JSONL parser and NucleiExecutor.

All tests run without Docker — sandbox calls are mocked.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from oxpwn.core.models import ToolResult
from oxpwn.sandbox.tools.nuclei import NucleiExecutor, parse_nuclei_jsonl

NUCLEI_JSONL_TYPICAL = "\n".join(
    [
        json.dumps(
            {
                "template-id": "deterministic-admin-panel",
                "template-path": "/tmp/oxpwn-tool-suite/nuclei/admin-panel.yaml",
                "info": {
                    "name": "Deterministic Admin Panel Fixture",
                    "severity": "info",
                    "description": "Matches the in-repo sandbox fixture served from /admin/.",
                },
                "type": "http",
                "host": "127.0.0.1",
                "port": "18080",
                "scheme": "http",
                "url": "http://127.0.0.1:18080",
                "matched-at": "http://127.0.0.1:18080/admin/",
                "ip": "127.0.0.1",
            }
        ),
        json.dumps(
            {
                "template-id": "deterministic-admin-panel",
                "template-path": "/tmp/oxpwn-tool-suite/nuclei/admin-panel.yaml",
                "info": {
                    "name": "Deterministic Admin Panel Fixture",
                    "severity": "info",
                    "description": "Matches the in-repo sandbox fixture served from /admin/.",
                },
                "type": "http",
                "host": "127.0.0.1",
                "port": "18080",
                "scheme": "http",
                "url": "http://127.0.0.1:18080",
                "matched-at": "http://127.0.0.1:18080/admin/",
                "ip": "127.0.0.1",
            }
        ),
    ]
)


class TestParseNucleiJsonl:
    """Unit tests for parse_nuclei_jsonl()."""

    def test_typical_output_normalizes_compact_findings(self) -> None:
        result = parse_nuclei_jsonl(NUCLEI_JSONL_TYPICAL)

        assert result["count"] == 1
        assert len(result["findings"]) == 1
        finding = result["findings"][0]
        assert finding == {
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
            "description": "Matches the in-repo sandbox fixture served from /admin/.",
        }

    def test_empty_output_returns_empty_findings(self) -> None:
        assert parse_nuclei_jsonl("") == {"count": 0, "findings": []}
        assert parse_nuclei_jsonl("\n\n") == {"count": 0, "findings": []}

    def test_malformed_json_raises(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            parse_nuclei_jsonl('{"template-id": "deterministic-admin-panel"}\nnot-json')


class TestNucleiExecutor:
    """Unit tests for NucleiExecutor with mocked DockerSandbox."""

    @pytest.fixture()
    def mock_sandbox(self) -> MagicMock:
        sandbox = MagicMock()
        sandbox.execute = AsyncMock(
            return_value=ToolResult(
                tool_name="sandbox",
                command="nuclei ...",
                stdout=NUCLEI_JSONL_TYPICAL,
                stderr="",
                exit_code=0,
                duration_ms=325,
            )
        )
        return sandbox

    async def test_run_builds_curated_command_and_parses_output(
        self,
        mock_sandbox: MagicMock,
    ) -> None:
        executor = NucleiExecutor(mock_sandbox)
        result = await executor.run(
            ["http://127.0.0.1:18080", "http://127.0.0.1:18081"],
            templates=["/tmp/oxpwn-tool-suite/nuclei/admin-panel.yaml"],
            follow_redirects=True,
            timeout_seconds=15,
            retries=2,
            rate_limit=25,
        )

        command = mock_sandbox.execute.call_args[0][0]
        assert command.startswith("nuclei -jsonl -silent -nc -duc -omit-raw -omit-template")
        assert "-u http://127.0.0.1:18080" in command
        assert "-u http://127.0.0.1:18081" in command
        assert "-t /tmp/oxpwn-tool-suite/nuclei/admin-panel.yaml" in command
        assert "-fr" in command
        assert "-timeout 15" in command
        assert "-retries 2" in command
        assert "-rl 25" in command

        assert result.tool_name == "nuclei"
        assert result.parsed_output is not None
        assert result.parsed_output["count"] == 1

    async def test_run_parse_failure_degrades_to_none_and_warns(
        self,
        mock_sandbox: MagicMock,
    ) -> None:
        mock_sandbox.execute.return_value = ToolResult(
            tool_name="sandbox",
            command="nuclei ...",
            stdout='{"template-id": "deterministic-admin-panel"}\nnot-json',
            stderr="[ERR] invalid template catalog",
            exit_code=1,
            duration_ms=40,
        )

        executor = NucleiExecutor(mock_sandbox)
        with patch("oxpwn.sandbox.tools.nuclei.logger.warning") as mock_warning:
            result = await executor.run(
                "http://127.0.0.1:18080",
                templates="/tmp/oxpwn-tool-suite/nuclei/admin-panel.yaml",
            )

        assert result.tool_name == "nuclei"
        assert result.parsed_output is None
        assert result.exit_code == 1
        mock_warning.assert_called_once()
        args, kwargs = mock_warning.call_args
        assert args == ("nuclei.jsonl_parse_failed",)
        assert kwargs["command"].startswith("nuclei -jsonl -silent")
        assert kwargs["stdout_head"].endswith("not-json")
        assert kwargs["stderr_head"] == "[ERR] invalid template catalog"
