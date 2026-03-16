"""Nmap XML parser and sandbox executor.

Establishes the tool executor pattern: constructor takes ``DockerSandbox``,
``run()`` returns ``ToolResult`` with ``parsed_output``.  S04 tools
(httpx, subfinder, nuclei, ffuf) will follow this same contract.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import structlog

from oxpwn.core.models import ToolResult
from oxpwn.sandbox.docker import DockerSandbox, SandboxOutputSink

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# XML parsing
# ---------------------------------------------------------------------------


def parse_nmap_xml(xml_string: str) -> dict:
    """Parse nmap ``-oX -`` XML output into a structured dict.

    Returns::

        {
            "hosts": [
                {
                    "address": "192.168.1.1",
                    "hostnames": ["example.com"],
                    "status": "up",
                    "ports": [
                        {
                            "port_id": 80,
                            "protocol": "tcp",
                            "state": "open",
                            "service_name": "http",
                            "service_product": "nginx",
                            "service_version": "1.24",
                            "scripts": [
                                {"id": "http-title", "output": "Welcome"}
                            ],
                        }
                    ],
                }
            ]
        }

    Handles empty scans (no hosts), hosts with no open ports, missing
    service info, and non-UTF-8 banner bytes (caller should decode with
    ``errors='replace'`` before passing in).
    """
    root = ET.fromstring(xml_string)  # noqa: S314 — trusted nmap output
    hosts: list[dict] = []

    for host_el in root.findall("host"):
        # -- address --
        addr_el = host_el.find("address")
        address = addr_el.get("addr", "") if addr_el is not None else ""

        # -- hostnames --
        hostnames: list[str] = []
        hostnames_el = host_el.find("hostnames")
        if hostnames_el is not None:
            for hn in hostnames_el.findall("hostname"):
                name = hn.get("name")
                if name:
                    hostnames.append(name)

        # -- status --
        status_el = host_el.find("status")
        status = status_el.get("state", "unknown") if status_el is not None else "unknown"

        # -- ports --
        ports: list[dict] = []
        ports_el = host_el.find("ports")
        if ports_el is not None:
            for port_el in ports_el.findall("port"):
                port_id_raw = port_el.get("portid", "0")
                protocol = port_el.get("protocol", "")

                state_el = port_el.find("state")
                state = state_el.get("state", "unknown") if state_el is not None else "unknown"

                service_el = port_el.find("service")
                service_name = ""
                service_product = ""
                service_version = ""
                if service_el is not None:
                    service_name = service_el.get("name", "")
                    service_product = service_el.get("product", "")
                    service_version = service_el.get("version", "")

                # -- scripts --
                scripts: list[dict] = []
                for script_el in port_el.findall("script"):
                    scripts.append(
                        {
                            "id": script_el.get("id", ""),
                            "output": script_el.get("output", ""),
                        }
                    )

                ports.append(
                    {
                        "port_id": int(port_id_raw),
                        "protocol": protocol,
                        "state": state,
                        "service_name": service_name,
                        "service_product": service_product,
                        "service_version": service_version,
                        "scripts": scripts,
                    }
                )

        hosts.append(
            {
                "address": address,
                "hostnames": hostnames,
                "status": status,
                "ports": ports,
            }
        )

    return {"hosts": hosts}


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


class NmapExecutor:
    """Run nmap inside a :class:`DockerSandbox` and return parsed results.

    This class establishes the tool-executor pattern that all S04 tools
    will follow:

    * Constructor takes a ``DockerSandbox`` instance.
    * ``run()`` is async, returns ``ToolResult`` with ``parsed_output``.
    """

    def __init__(self, sandbox: DockerSandbox) -> None:
        self.sandbox = sandbox

    async def run(
        self,
        target: str,
        ports: str | None = None,
        flags: str = "-sV",
        *,
        output_sink: SandboxOutputSink | None = None,
    ) -> ToolResult:
        """Execute nmap and return a :class:`ToolResult` with parsed XML.

        Args:
            target: Scan target (IP, hostname, CIDR).
            ports: Comma-separated port list (``-p`` argument). ``None``
                   lets nmap use its default top-ports.
            flags: Additional nmap flags (default ``-sV``).

        Returns:
            ``ToolResult`` whose ``parsed_output`` is the dict produced by
            :func:`parse_nmap_xml`, or ``None`` if XML parsing failed.
        """
        parts = ["nmap", flags, "-oX", "-"]
        if ports is not None:
            parts.extend(["-p", ports])
        parts.append(target)
        command = " ".join(parts)

        result = (
            await self.sandbox.execute_stream(command, output_sink=output_sink)
            if output_sink is not None
            else await self.sandbox.execute(command)
        )

        # Enrich with tool name
        result.tool_name = "nmap"

        # Parse XML output
        try:
            result.parsed_output = parse_nmap_xml(result.stdout)
        except ET.ParseError:
            logger.warning(
                "nmap.xml_parse_failed",
                command=command,
                stdout_head=result.stdout[:200] if result.stdout else "",
                stderr_head=result.stderr[:200] if result.stderr else "",
            )
            result.parsed_output = None

        return result
