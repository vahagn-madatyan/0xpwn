"""Unit tests for ToolRegistry: schema generation, dispatch, error handling."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from oxpwn.agent.tools import ToolRegistry, parse_tool_arguments, register_default_tools
from oxpwn.core.models import ToolResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sandbox() -> MagicMock:
    return MagicMock()


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
    """Nmap is registered by the default factory helper."""

    def test_nmap_registered(self):
        registry = ToolRegistry()
        register_default_tools(registry)

        assert "nmap" in registry.tool_names
        schemas = registry.get_schemas()
        nmap_schema = schemas[0]["function"]
        assert nmap_schema["name"] == "nmap"
        assert "target" in nmap_schema["parameters"]["properties"]
        assert "target" in nmap_schema["parameters"]["required"]

    def test_nmap_schema_properties(self):
        registry = ToolRegistry()
        register_default_tools(registry)

        props = registry.get_schemas()[0]["function"]["parameters"]["properties"]
        assert "target" in props
        assert "ports" in props
        assert "flags" in props
        assert props["target"]["type"] == "string"


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
