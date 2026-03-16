"""Unit tests for ToolRegistry: schema generation, dispatch, error handling."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from oxpwn.agent.tools import ToolRegistry, parse_tool_arguments, register_default_tools
from oxpwn.core.models import ToolResult
from oxpwn.sandbox.tools.ffuf import DEFAULT_FFUF_WORDLIST_PATH


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sandbox() -> MagicMock:
    return MagicMock()


EXPECTED_DEFAULT_TOOLS = ["nmap", "httpx", "subfinder", "nuclei", "ffuf"]


def _make_tool_result(**overrides) -> ToolResult:
    defaults = {
        "tool_name": "test_tool",
        "command": "echo hello",
        "stdout": "hello",
        "stderr": "",
        "exit_code": 0,
        "duration_ms": 100,
    }
    defaults.update(overrides)
    return ToolResult(**defaults)


class FakeExecutor:
    """Executor stub for registry tests."""

    def __init__(self, sandbox):
        self.sandbox = sandbox

    async def run(self, target: str, mode: str = "fast") -> ToolResult:
        return _make_tool_result(
            tool_name="fake",
            command=f"fake --mode {mode} {target}",
        )


class FakeStreamingExecutor:
    """Executor stub that opts into additive live-output streaming."""

    def __init__(self, sandbox):
        self.sandbox = sandbox

    async def run(self, target: str, *, output_sink=None) -> ToolResult:
        if output_sink is not None:
            await output_sink(chunk="partial stdout", stream="stdout")
            await output_sink(chunk="partial stderr", stream="stderr")

        return _make_tool_result(
            tool_name="fake-streaming",
            command=f"fake-streaming {target}",
            stdout="partial stdout",
            stderr="partial stderr",
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestToolRegistry:
    """ToolRegistry core behavior."""

    def test_register_and_get_schemas(self):
        registry = ToolRegistry()
        registry.register(
            name="fake",
            description="A fake tool for testing.",
            parameters_schema={
                "type": "object",
                "properties": {"target": {"type": "string"}},
                "required": ["target"],
            },
            executor_factory=lambda s: FakeExecutor(s),
        )

        schemas = registry.get_schemas()
        assert len(schemas) == 1

        schema = schemas[0]
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "fake"
        assert schema["function"]["description"] == "A fake tool for testing."
        assert "target" in schema["function"]["parameters"]["properties"]

    def test_get_schemas_openai_format(self):
        """Schemas match the shape LLMClient.complete(tools=...) expects."""
        registry = ToolRegistry()
        registry.register(
            name="scanner",
            description="Scans things.",
            parameters_schema={"type": "object", "properties": {}},
            executor_factory=lambda s: None,
        )

        schema = registry.get_schemas()[0]
        # Must have type + function keys at top level
        assert set(schema.keys()) == {"type", "function"}
        assert set(schema["function"].keys()) == {"name", "description", "parameters"}

    @pytest.mark.asyncio
    async def test_dispatch_calls_executor(self):
        registry = ToolRegistry()
        registry.register(
            name="fake",
            description="Fake.",
            parameters_schema={"type": "object", "properties": {}},
            executor_factory=lambda s: FakeExecutor(s),
        )

        sandbox = _make_sandbox()
        result = await registry.dispatch("fake", {"target": "10.0.0.1"}, sandbox)

        assert isinstance(result, ToolResult)
        assert result.tool_name == "fake"
        assert "10.0.0.1" in result.command

    @pytest.mark.asyncio
    async def test_dispatch_forwards_output_sink_to_opt_in_executor(self):
        registry = ToolRegistry()
        registry.register(
            name="fake-streaming",
            description="Fake streaming.",
            parameters_schema={"type": "object", "properties": {}},
            executor_factory=lambda s: FakeStreamingExecutor(s),
        )

        streamed_chunks: list[tuple[str, str]] = []

        async def output_sink(*, chunk: str, stream: str) -> None:
            streamed_chunks.append((stream, chunk))

        result = await registry.dispatch(
            "fake-streaming",
            {"target": "10.0.0.1"},
            _make_sandbox(),
            output_sink=output_sink,
        )

        assert result.tool_name == "fake-streaming"
        assert streamed_chunks == [
            ("stdout", "partial stdout"),
            ("stderr", "partial stderr"),
        ]

    @pytest.mark.asyncio
    async def test_dispatch_with_output_sink_keeps_legacy_executors_working(self):
        registry = ToolRegistry()
        registry.register(
            name="fake",
            description="Fake.",
            parameters_schema={"type": "object", "properties": {}},
            executor_factory=lambda s: FakeExecutor(s),
        )

        async def output_sink(*, chunk: str, stream: str) -> None:  # pragma: no cover - should never be called
            raise AssertionError(f"Legacy executor unexpectedly streamed {stream}: {chunk}")

        result = await registry.dispatch(
            "fake",
            {"target": "10.0.0.1"},
            _make_sandbox(),
            output_sink=output_sink,
        )

        assert isinstance(result, ToolResult)
        assert result.tool_name == "fake"
        assert "10.0.0.1" in result.command

    @pytest.mark.asyncio
    async def test_dispatch_unknown_tool_raises_key_error(self):
        registry = ToolRegistry()

        with pytest.raises(KeyError, match="Unknown tool"):
            await registry.dispatch("nonexistent", {}, _make_sandbox())

    def test_tool_names_property(self):
        registry = ToolRegistry()
        registry.register("a", "Tool A", {}, lambda s: None)
        registry.register("b", "Tool B", {}, lambda s: None)

        assert set(registry.tool_names) == {"a", "b"}

    def test_empty_registry_schemas(self):
        registry = ToolRegistry()
        assert registry.get_schemas() == []


class TestRegisterDefaultTools:
    """The default helper exposes the full five-tool core suite."""

    def test_full_suite_registered_in_stable_order(self):
        registry = ToolRegistry()
        register_default_tools(registry)

        assert registry.tool_names == EXPECTED_DEFAULT_TOOLS
        schema_names = [schema["function"]["name"] for schema in registry.get_schemas()]
        assert schema_names == EXPECTED_DEFAULT_TOOLS

    def test_default_tool_schemas_have_expected_parameters(self):
        registry = ToolRegistry()
        register_default_tools(registry)

        schemas = {
            schema["function"]["name"]: schema["function"]["parameters"]
            for schema in registry.get_schemas()
        }

        assert schemas["nmap"]["required"] == ["target"]
        assert set(schemas["nmap"]["properties"]) == {"target", "ports", "flags"}

        assert schemas["httpx"]["required"] == ["targets"]
        assert set(schemas["httpx"]["properties"]) == {
            "targets",
            "ports",
            "path",
            "follow_redirects",
            "tech_detect",
            "timeout_seconds",
            "threads",
        }
        assert schemas["httpx"]["properties"]["targets"]["oneOf"][0]["type"] == "string"
        assert schemas["httpx"]["properties"]["targets"]["oneOf"][1]["type"] == "array"

        assert schemas["subfinder"]["required"] == ["domains"]
        assert set(schemas["subfinder"]["properties"]) == {
            "domains",
            "all_sources",
            "recursive",
            "timeout_seconds",
            "max_time_minutes",
        }
        assert schemas["subfinder"]["properties"]["domains"]["oneOf"][1]["items"]["type"] == "string"

        assert schemas["nuclei"]["required"] == ["targets", "templates"]
        assert set(schemas["nuclei"]["properties"]) == {
            "targets",
            "templates",
            "follow_redirects",
            "timeout_seconds",
            "retries",
            "rate_limit",
        }
        assert schemas["nuclei"]["properties"]["templates"]["oneOf"][0]["type"] == "string"

        assert schemas["ffuf"]["required"] == ["url"]
        assert set(schemas["ffuf"]["properties"]) == {
            "url",
            "wordlist_path",
            "follow_redirects",
            "match_status",
            "timeout_seconds",
            "threads",
        }
        assert schemas["ffuf"]["properties"]["wordlist_path"]["default"] == DEFAULT_FFUF_WORDLIST_PATH
        assert "FUZZ" in schemas["ffuf"]["properties"]["url"]["description"]


class TestParseToolArguments:
    """parse_tool_arguments handles valid and malformed JSON."""

    def test_valid_json(self):
        result = parse_tool_arguments('{"target": "10.0.0.1", "ports": "80"}')
        assert result == {"target": "10.0.0.1", "ports": "80"}

    def test_invalid_json_returns_empty(self):
        result = parse_tool_arguments("not json at all")
        assert result == {}

    def test_non_dict_json_returns_empty(self):
        result = parse_tool_arguments("[1, 2, 3]")
        assert result == {}

    def test_empty_string_returns_empty(self):
        result = parse_tool_arguments("")
        assert result == {}
