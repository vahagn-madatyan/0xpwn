"""Tool registry mapping names to OpenAI function schemas and executor factories."""

from __future__ import annotations

import json
from typing import Any, Callable

import structlog

from oxpwn.core.models import ToolResult
from oxpwn.sandbox.docker import DockerSandbox
from oxpwn.sandbox.tools.ffuf import DEFAULT_FFUF_WORDLIST_PATH

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


def _string_or_list_schema(description: str) -> dict[str, Any]:
    return {
        "description": description,
        "oneOf": [
            {"type": "string"},
            {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            },
        ],
    }


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

_HTTPX_PARAMETERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "targets": _string_or_list_schema(
            "One hostname/URL or a list of targets to probe for live HTTP(S) services.",
        ),
        "ports": {
            "type": "string",
            "description": "Optional comma-separated port list for HTTP probing (e.g. '80,443,8080').",
        },
        "path": {
            "type": "string",
            "description": "Optional request path to probe on every target (for example '/admin/').",
        },
        "follow_redirects": {
            "type": "boolean",
            "description": "Follow HTTP redirects before reporting the final response.",
            "default": False,
        },
        "tech_detect": {
            "type": "boolean",
            "description": "Enable lightweight technology detection in the structured output.",
            "default": True,
        },
        "timeout_seconds": {
            "type": "integer",
            "description": "Per-request timeout in seconds.",
            "default": 5,
            "minimum": 1,
        },
        "threads": {
            "type": "integer",
            "description": "Optional concurrent thread count for larger batches.",
            "minimum": 1,
        },
    },
    "required": ["targets"],
}

_SUBFINDER_PARAMETERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "domains": _string_or_list_schema(
            "One root domain or a list of root domains to enumerate for passive subdomains.",
        ),
        "all_sources": {
            "type": "boolean",
            "description": "Use all configured passive sources instead of the default subset.",
            "default": False,
        },
        "recursive": {
            "type": "boolean",
            "description": "Enable recursive subdomain discovery where supported by the source.",
            "default": False,
        },
        "timeout_seconds": {
            "type": "integer",
            "description": "Per-source timeout in seconds.",
            "default": 30,
            "minimum": 1,
        },
        "max_time_minutes": {
            "type": "integer",
            "description": "Maximum wall-clock runtime in minutes.",
            "default": 10,
            "minimum": 1,
        },
    },
    "required": ["domains"],
}

_NUCLEI_PARAMETERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "targets": _string_or_list_schema(
            "One target URL/host or a list of targets to scan with nuclei templates.",
        ),
        "templates": _string_or_list_schema(
            "One nuclei template path or a list of template paths to run.",
        ),
        "follow_redirects": {
            "type": "boolean",
            "description": "Follow HTTP redirects during template execution.",
            "default": False,
        },
        "timeout_seconds": {
            "type": "integer",
            "description": "Per-request timeout in seconds.",
            "default": 10,
            "minimum": 1,
        },
        "retries": {
            "type": "integer",
            "description": "Retry count for transient request failures.",
            "default": 1,
            "minimum": 0,
        },
        "rate_limit": {
            "type": "integer",
            "description": "Optional per-second request rate limit for gentler scans.",
            "minimum": 1,
        },
    },
    "required": ["targets", "templates"],
}

_FFUF_PARAMETERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "url": {
            "type": "string",
            "description": "Target URL containing the FUZZ keyword (for example 'http://host/FUZZ/').",
        },
        "wordlist_path": {
            "type": "string",
            "description": "Wordlist path inside the sandbox. Defaults to the deterministic integration-test wordlist.",
            "default": DEFAULT_FFUF_WORDLIST_PATH,
        },
        "follow_redirects": {
            "type": "boolean",
            "description": "Follow redirects while fuzzing.",
            "default": False,
        },
        "match_status": {
            "type": "string",
            "description": "HTTP status matcher passed to ffuf (for example '200' or '200,204,301').",
            "default": "all",
        },
        "timeout_seconds": {
            "type": "integer",
            "description": "Per-request timeout in seconds.",
            "default": 10,
            "minimum": 1,
        },
        "threads": {
            "type": "integer",
            "description": "Optional concurrent worker count.",
            "minimum": 1,
        },
    },
    "required": ["url"],
}


def register_default_tools(registry: ToolRegistry) -> None:
    """Register the built-in five-tool core suite for the agent."""
    from oxpwn.sandbox.tools import (
        FfufExecutor,
        HttpxExecutor,
        NmapExecutor,
        NucleiExecutor,
        SubfinderExecutor,
    )

    registry.register(
        name="nmap",
        description=(
            "Run an nmap port scan against a target. Returns structured data about "
            "discovered hosts, open ports, and detected services."
        ),
        parameters_schema=_NMAP_PARAMETERS_SCHEMA,
        executor_factory=lambda sandbox: NmapExecutor(sandbox),
    )
    registry.register(
        name="httpx",
        description=(
            "Probe one or more HTTP(S) targets and return structured live-service "
            "metadata such as URLs, status codes, titles, and technologies."
        ),
        parameters_schema=_HTTPX_PARAMETERS_SCHEMA,
        executor_factory=lambda sandbox: HttpxExecutor(sandbox),
    )
    registry.register(
        name="subfinder",
        description=(
            "Enumerate passive subdomains for one or more root domains and return "
            "deduplicated hostnames with source attribution."
        ),
        parameters_schema=_SUBFINDER_PARAMETERS_SCHEMA,
        executor_factory=lambda sandbox: SubfinderExecutor(sandbox),
    )
    registry.register(
        name="nuclei",
        description=(
            "Run focused nuclei templates against one or more targets and return "
            "compact structured findings."
        ),
        parameters_schema=_NUCLEI_PARAMETERS_SCHEMA,
        executor_factory=lambda sandbox: NucleiExecutor(sandbox),
    )
    registry.register(
        name="ffuf",
        description=(
            "Fuzz a web path containing FUZZ and return compact structured findings "
            "for discovered routes."
        ),
        parameters_schema=_FFUF_PARAMETERS_SCHEMA,
        executor_factory=lambda sandbox: FfufExecutor(sandbox),
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
