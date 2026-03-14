"""Tool registry mapping names to OpenAI function schemas and executor factories."""

from __future__ import annotations

import json
from typing import Any, Callable

import structlog

from oxpwn.core.models import ToolResult
from oxpwn.sandbox.docker import DockerSandbox

logger = structlog.get_logger("oxpwn.agent.tools")


# Type alias: factory takes a sandbox and returns an executor instance
ExecutorFactory = Callable[[DockerSandbox], Any]


class ToolRegistry:
    """Maps tool names to OpenAI function call schemas and executor factories.

    Usage::

        registry = ToolRegistry()
        register_default_tools(registry)

        schemas = registry.get_schemas()        # for LLM tools param
        result  = await registry.dispatch("nmap", {"target": "10.0.0.1"}, sandbox)
    """

    def __init__(self) -> None:
        self._tools: dict[str, _ToolEntry] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters_schema: dict[str, Any],
        executor_factory: ExecutorFactory,
    ) -> None:
        """Register a tool with its OpenAI function schema and executor factory.

        Args:
            name: Unique tool name (e.g. ``"nmap"``).
            description: Human-readable description for the LLM.
            parameters_schema: JSON Schema dict for the function parameters.
            executor_factory: Callable ``(sandbox) → executor`` with an async
                ``run(**arguments) → ToolResult`` method.
        """
        self._tools[name] = _ToolEntry(
            name=name,
            description=description,
            parameters_schema=parameters_schema,
            executor_factory=executor_factory,
        )

    def get_schemas(self) -> list[dict[str, Any]]:
        """Return tool definitions in OpenAI function calling format.

        Each entry follows the shape expected by ``LLMClient.complete(tools=...)``.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": entry.name,
                    "description": entry.description,
                    "parameters": entry.parameters_schema,
                },
            }
            for entry in self._tools.values()
        ]

    async def dispatch(
        self,
        name: str,
        arguments: dict[str, Any],
        sandbox: DockerSandbox,
    ) -> ToolResult:
        """Instantiate the executor via its factory and run the tool.

        Args:
            name: Registered tool name.
            arguments: Parsed arguments to pass to ``executor.run()``.
            sandbox: Docker sandbox for command execution.

        Returns:
            ToolResult from the executor.

        Raises:
            KeyError: If the tool name is not registered.
        """
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name!r}")

        entry = self._tools[name]
        executor = entry.executor_factory(sandbox)
        result: ToolResult = await executor.run(**arguments)
        return result

    @property
    def tool_names(self) -> list[str]:
        """List registered tool names."""
        return list(self._tools.keys())


class _ToolEntry:
    """Internal storage for a registered tool."""

    __slots__ = ("name", "description", "parameters_schema", "executor_factory")

    def __init__(
        self,
        name: str,
        description: str,
        parameters_schema: dict[str, Any],
        executor_factory: ExecutorFactory,
    ) -> None:
        self.name = name
        self.description = description
        self.parameters_schema = parameters_schema
        self.executor_factory = executor_factory


# ---------------------------------------------------------------------------
# Default tool registrations
# ---------------------------------------------------------------------------

_NMAP_PARAMETERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "target": {
            "type": "string",
            "description": "Scan target: IP address, hostname, or CIDR range.",
        },
        "ports": {
            "type": "string",
            "description": "Comma-separated port list (e.g. '80,443,8080'). Omit for default top ports.",
        },
        "flags": {
            "type": "string",
            "description": "Additional nmap flags (default '-sV').",
            "default": "-sV",
        },
    },
    "required": ["target"],
}


def register_default_tools(registry: ToolRegistry) -> None:
    """Register the built-in nmap tool (more tools added in S04)."""
    from oxpwn.sandbox.tools.nmap import NmapExecutor

    registry.register(
        name="nmap",
        description=(
            "Run an nmap port scan against a target. Returns structured data about "
            "discovered hosts, open ports, and detected services."
        ),
        parameters_schema=_NMAP_PARAMETERS_SCHEMA,
        executor_factory=lambda sandbox: NmapExecutor(sandbox),
    )


def parse_tool_arguments(raw_arguments: str) -> dict[str, Any]:
    """Parse a JSON arguments string from an LLM tool call.

    Returns an empty dict and logs a warning if parsing fails.
    """
    try:
        parsed = json.loads(raw_arguments)
        if not isinstance(parsed, dict):
            logger.warning("tool.arguments_not_dict", raw=raw_arguments[:200])
            return {}
        return parsed
    except json.JSONDecodeError as exc:
        logger.warning("tool.arguments_parse_error", error=str(exc), raw=raw_arguments[:200])
        return {}
