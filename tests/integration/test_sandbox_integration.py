"""Integration tests — real Docker, real nmap, real containers.

These tests require a running Docker daemon and the ``oxpwn-sandbox:dev``
image. They are marked ``@pytest.mark.integration`` and will be skipped
automatically when Docker is unavailable (via the session fixture).
"""

from __future__ import annotations

import docker
import pytest

from oxpwn.sandbox.docker import DockerSandbox
from oxpwn.sandbox.tools.nmap import NmapExecutor


pytestmark = pytest.mark.integration


async def _assert_real_nmap_scan(docker_sandbox: DockerSandbox) -> None:
    """Run nmap in the sandbox and assert the parsed localhost contract."""
    executor = NmapExecutor(docker_sandbox)
    result = await executor.run("localhost", ports="80", flags="-sV")

    assert result.tool_name == "nmap"
    assert result.exit_code == 0
    assert result.parsed_output is not None
    assert "hosts" in result.parsed_output

    hosts = result.parsed_output["hosts"]
    assert len(hosts) >= 1


class TestSandboxBasic:
    """Basic container lifecycle tests."""

    async def test_exec_echo(self, docker_sandbox: DockerSandbox) -> None:
        """Container executes a simple command and returns stdout."""
        result = await docker_sandbox.execute("echo hello")
        assert result.exit_code == 0
        assert result.stdout.strip() == "hello"

    async def test_container_labels(self, docker_sandbox: DockerSandbox) -> None:
        """Container carries the expected management labels."""
        assert docker_sandbox._container is not None
        container = docker_sandbox._container
        container.reload()
        labels = container.labels
        assert labels.get("oxpwn.managed") == "true"
        assert labels.get("oxpwn.scan_id") == "integration-test"


@pytest.mark.asyncio
async def test_nmap_executor_real_scan(docker_sandbox: DockerSandbox) -> None:
    """Module-level alias for the slice verification command's expected node id."""
    await _assert_real_nmap_scan(docker_sandbox)


class TestNmapIntegration:
    """Run real nmap inside the container."""

    async def test_nmap_localhost_scan(self, docker_sandbox: DockerSandbox) -> None:
        """Nmap scan of localhost inside container returns parsed ToolResult."""
        await _assert_real_nmap_scan(docker_sandbox)


class TestCleanup:
    """Orphan container cleanup."""

    async def test_cleanup_orphans(self) -> None:
        """cleanup_orphans removes managed containers.

        Creates a throwaway container, then verifies cleanup removes it.
        """
        try:
            client = docker.from_env()
            client.ping()
        except Exception:  # noqa: BLE001
            pytest.skip("Docker not available")

        sandbox = DockerSandbox("oxpwn-sandbox:dev", scan_id="orphan-test")
        await sandbox.create()
        assert sandbox._container is not None
        orphan_id = sandbox._container.short_id

        count = await DockerSandbox.cleanup_orphans()
        assert count >= 1

        remaining = client.containers.list(
            all=True,
            filters={"label": "oxpwn.managed=true"},
        )
        remaining_ids = [c.short_id for c in remaining]
        assert orphan_id not in remaining_ids
