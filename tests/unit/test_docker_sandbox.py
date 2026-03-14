"""Unit tests for DockerSandbox — all Docker calls are mocked."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from oxpwn.core.models import ToolResult
from oxpwn.sandbox.docker import DockerSandbox
from oxpwn.sandbox.exceptions import (
    ImageNotFoundError,
    SandboxNotRunningError,
    SandboxTimeoutError,
)

SCAN_ID = "test-scan-001"
IMAGE = "oxpwn-sandbox:dev"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_container(
    short_id: str = "abc123",
    status: str = "running",
) -> MagicMock:
    """Build a mock docker Container."""
    container = MagicMock()
    container.short_id = short_id
    container.status = status
    container.start = MagicMock()
    container.stop = MagicMock()
    container.remove = MagicMock()
    container.reload = MagicMock(side_effect=lambda: setattr(container, "status", container.status))
    container.exec_run = MagicMock(
        return_value=(0, (b"scan output", b""))
    )
    return container


def _make_mock_client(container: MagicMock | None = None) -> MagicMock:
    """Build a mock docker.DockerClient."""
    client = MagicMock()
    if container is None:
        container = _make_mock_container()
    client.containers.create.return_value = container
    client.containers.list.return_value = []
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreate:
    """Container creation sets correct config."""

    @patch("oxpwn.sandbox.docker.docker.from_env")
    async def test_create_sets_correct_labels_and_caps(
        self, mock_from_env: MagicMock
    ) -> None:
        container = _make_mock_container()
        client = _make_mock_client(container)
        mock_from_env.return_value = client

        sandbox = DockerSandbox(IMAGE, SCAN_ID)
        await sandbox.create()

        client.containers.create.assert_called_once_with(
            IMAGE,
            command="sleep infinity",
            detach=True,
            cap_add=["NET_ADMIN", "NET_RAW"],
            labels={"oxpwn.managed": "true", "oxpwn.scan_id": SCAN_ID},
            network_mode="bridge",
        )
        container.start.assert_called_once()

    @patch("oxpwn.sandbox.docker.docker.from_env")
    async def test_image_not_found_raises(
        self, mock_from_env: MagicMock
    ) -> None:
        import docker.errors

        client = MagicMock()
        client.containers.create.side_effect = docker.errors.ImageNotFound(
            "not found"
        )
        mock_from_env.return_value = client

        sandbox = DockerSandbox(IMAGE, SCAN_ID)
        with pytest.raises(ImageNotFoundError) as exc_info:
            await sandbox.create()
        assert exc_info.value.image_name == IMAGE


class TestExecute:
    """Command execution returns structured ToolResult."""

    @patch("oxpwn.sandbox.docker.docker.from_env")
    async def test_execute_returns_tool_result(
        self, mock_from_env: MagicMock
    ) -> None:
        container = _make_mock_container()
        container.exec_run.return_value = (0, (b"host is up", b"warning"))
        mock_from_env.return_value = _make_mock_client(container)

        sandbox = DockerSandbox(IMAGE, SCAN_ID)
        await sandbox.create()
        result = await sandbox.execute("nmap -sV target")

        assert isinstance(result, ToolResult)
        assert result.stdout == "host is up"
        assert result.stderr == "warning"
        assert result.exit_code == 0
        assert result.duration_ms >= 0
        container.exec_run.assert_called_once_with("nmap -sV target", demux=True)

    @patch("oxpwn.sandbox.docker.docker.from_env")
    async def test_execute_timeout_raises(
        self, mock_from_env: MagicMock
    ) -> None:
        container = _make_mock_container()
        # Simulate a slow command by making exec_run block
        async def _hang() -> None:
            await asyncio.sleep(10)

        container.exec_run.side_effect = lambda *a, **kw: asyncio.get_event_loop().run_until_complete(_hang())
        mock_from_env.return_value = _make_mock_client(container)

        sandbox = DockerSandbox(IMAGE, SCAN_ID)
        await sandbox.create()

        # Use a very small timeout that we patch into wait_for
        with patch("oxpwn.sandbox.docker.asyncio.wait_for", side_effect=asyncio.TimeoutError):
            with pytest.raises(SandboxTimeoutError) as exc_info:
                await sandbox.execute("nmap -sV target", timeout=1)
            assert exc_info.value.timeout_seconds == 1

    @patch("oxpwn.sandbox.docker.docker.from_env")
    async def test_execute_on_stopped_container_raises(
        self, mock_from_env: MagicMock
    ) -> None:
        container = _make_mock_container(status="exited")
        mock_from_env.return_value = _make_mock_client(container)

        sandbox = DockerSandbox(IMAGE, SCAN_ID)
        await sandbox.create()

        with pytest.raises(SandboxNotRunningError):
            await sandbox.execute("echo hello")

    async def test_execute_without_create_raises(self) -> None:
        sandbox = DockerSandbox(IMAGE, SCAN_ID)
        with pytest.raises(SandboxNotRunningError):
            await sandbox.execute("echo hello")


class TestDestroy:
    """Container teardown."""

    @patch("oxpwn.sandbox.docker.docker.from_env")
    async def test_destroy_calls_stop_and_remove(
        self, mock_from_env: MagicMock
    ) -> None:
        container = _make_mock_container()
        mock_from_env.return_value = _make_mock_client(container)

        sandbox = DockerSandbox(IMAGE, SCAN_ID)
        await sandbox.create()
        await sandbox.destroy()

        container.stop.assert_called_once_with(timeout=5)
        container.remove.assert_called_once_with(force=True)


class TestContextManager:
    """Async context manager lifecycle."""

    @patch("oxpwn.sandbox.docker.docker.from_env")
    async def test_context_manager_create_and_destroy(
        self, mock_from_env: MagicMock
    ) -> None:
        container = _make_mock_container()
        mock_from_env.return_value = _make_mock_client(container)

        async with DockerSandbox(IMAGE, SCAN_ID) as sandbox:
            assert sandbox._container is not None

        container.stop.assert_called_once()
        container.remove.assert_called_once()

    @patch("oxpwn.sandbox.docker.docker.from_env")
    async def test_context_manager_destroy_on_exception(
        self, mock_from_env: MagicMock
    ) -> None:
        container = _make_mock_container()
        mock_from_env.return_value = _make_mock_client(container)

        with pytest.raises(RuntimeError, match="boom"):
            async with DockerSandbox(IMAGE, SCAN_ID):
                raise RuntimeError("boom")

        container.stop.assert_called_once()
        container.remove.assert_called_once()


class TestCleanupOrphans:
    """Orphan container cleanup."""

    @patch("oxpwn.sandbox.docker.docker.from_env")
    async def test_cleanup_orphans_removes_labeled_containers(
        self, mock_from_env: MagicMock
    ) -> None:
        c1 = _make_mock_container(short_id="c1")
        c2 = _make_mock_container(short_id="c2")
        client = MagicMock()
        client.containers.list.return_value = [c1, c2]
        mock_from_env.return_value = client

        count = await DockerSandbox.cleanup_orphans()

        assert count == 2
        client.containers.list.assert_called_once_with(
            all=True,
            filters={"label": "oxpwn.managed=true"},
        )
        for c in (c1, c2):
            c.stop.assert_called_once()
            c.remove.assert_called_once()
