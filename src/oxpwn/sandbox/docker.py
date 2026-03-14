"""Async Docker sandbox for isolated security tool execution."""

from __future__ import annotations

import asyncio
import time
from typing import Self

import docker
import docker.errors
import structlog

from oxpwn.core.models import ToolResult
from oxpwn.sandbox.exceptions import (
    ImageNotFoundError,
    SandboxError,
    SandboxNotRunningError,
    SandboxTimeoutError,
)

logger = structlog.get_logger()


class DockerSandbox:
    """Async context manager wrapping a Docker container for tool execution.

    Usage::

        async with DockerSandbox("oxpwn-sandbox:dev", scan_id) as sandbox:
            result = await sandbox.execute("nmap -sV target")
    """

    def __init__(
        self,
        image: str,
        scan_id: str,
        *,
        network_mode: str = "bridge",
    ) -> None:
        self.image = image
        self.scan_id = scan_id
        self.network_mode = network_mode
        self.labels = {
            "oxpwn.managed": "true",
            "oxpwn.scan_id": scan_id,
        }
        self._container: docker.models.containers.Container | None = None
        self._client: docker.DockerClient | None = None

    # -- Async context manager ------------------------------------------------

    async def __aenter__(self) -> Self:
        await self.create()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        await self.destroy()

    # -- Lifecycle ------------------------------------------------------------

    async def create(self) -> None:
        """Create and start the sandbox container."""

        def _create() -> docker.models.containers.Container:
            client = docker.from_env()
            self._client = client
            container = client.containers.create(
                self.image,
                command="sleep infinity",
                detach=True,
                cap_add=["NET_ADMIN", "NET_RAW"],
                labels=self.labels,
                network_mode=self.network_mode,
            )
            container.start()
            return container

        try:
            self._container = await asyncio.to_thread(_create)
        except docker.errors.ImageNotFound as exc:
            raise ImageNotFoundError(
                f"Docker image '{self.image}' not found",
                image_name=self.image,
            ) from exc
        except docker.errors.APIError as exc:
            raise SandboxError(f"Failed to create container: {exc}") from exc

        container_id = self._container.short_id
        logger.info(
            "sandbox.create",
            image=self.image,
            scan_id=self.scan_id,
            container_id=container_id,
        )

    async def execute(self, command: str, timeout: int = 300) -> ToolResult:
        """Execute a command inside the sandbox container.

        Args:
            command: Shell command string to run.
            timeout: Maximum seconds to wait (default 300).

        Returns:
            ToolResult with stdout, stderr, exit_code, and duration_ms.

        Raises:
            SandboxNotRunningError: Container is not running.
            SandboxTimeoutError: Command exceeded timeout.
        """
        if self._container is None:
            raise SandboxNotRunningError(
                "No container available — call create() first"
            )

        container_id = self._container.short_id

        # Refresh status to verify container is running
        def _reload_status() -> str:
            assert self._container is not None  # noqa: S101
            self._container.reload()
            return self._container.status

        status = await asyncio.to_thread(_reload_status)
        if status != "running":
            raise SandboxNotRunningError(
                f"Container {container_id} is not running (status={status})",
                container_id=container_id,
            )

        def _exec() -> tuple[int, bytes | None, bytes | None]:
            assert self._container is not None  # noqa: S101
            exit_code, (out, err) = self._container.exec_run(
                command, demux=True
            )
            return exit_code, out, err

        t0 = time.monotonic()
        try:
            exit_code, raw_stdout, raw_stderr = await asyncio.wait_for(
                asyncio.to_thread(_exec),
                timeout=timeout,
            )
        except asyncio.TimeoutError as exc:
            raise SandboxTimeoutError(
                f"Command timed out after {timeout}s: {command}",
                container_id=container_id,
                timeout_seconds=timeout,
            ) from exc

        duration_ms = int((time.monotonic() - t0) * 1000)
        stdout = raw_stdout.decode("utf-8", errors="replace") if raw_stdout else ""
        stderr = raw_stderr.decode("utf-8", errors="replace") if raw_stderr else ""

        logger.info(
            "sandbox.execute",
            command=command,
            exit_code=exit_code,
            duration_ms=duration_ms,
            container_id=container_id,
        )

        return ToolResult(
            tool_name="sandbox",
            command=command,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration_ms=duration_ms,
        )

    async def destroy(self) -> None:
        """Stop and remove the container (best-effort)."""
        if self._container is None:
            return

        container_id = self._container.short_id

        def _destroy() -> None:
            assert self._container is not None  # noqa: S101
            try:
                self._container.stop(timeout=5)
            except Exception:  # noqa: BLE001
                pass
            try:
                self._container.remove(force=True)
            except Exception:  # noqa: BLE001
                pass

        try:
            await asyncio.to_thread(_destroy)
        except Exception:  # noqa: BLE001
            pass

        logger.info("sandbox.destroy", container_id=container_id)
        self._container = None

    # -- Class-level utilities ------------------------------------------------

    @classmethod
    async def cleanup_orphans(cls) -> int:
        """Find and remove containers labeled ``oxpwn.managed=true``.

        Returns:
            Number of containers removed.
        """

        def _cleanup() -> int:
            client = docker.from_env()
            containers = client.containers.list(
                all=True,
                filters={"label": "oxpwn.managed=true"},
            )
            removed = 0
            for container in containers:
                try:
                    container.stop(timeout=5)
                except Exception:  # noqa: BLE001
                    pass
                try:
                    container.remove(force=True)
                    removed += 1
                except Exception:  # noqa: BLE001
                    pass
            return removed

        count = await asyncio.to_thread(_cleanup)
        logger.info("sandbox.cleanup_orphans", count=count)
        return count
