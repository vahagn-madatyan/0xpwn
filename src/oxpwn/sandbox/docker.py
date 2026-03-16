"""Async Docker sandbox for isolated security tool execution."""

from __future__ import annotations

import asyncio
import codecs
import inspect
import time
from typing import Literal, Protocol, Self

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

ToolOutputStream = Literal["stdout", "stderr"]


class SandboxOutputSink(Protocol):
    """Optional callback for forwarding decoded stdout/stderr chunks live."""

    def __call__(self, *, chunk: str, stream: ToolOutputStream) -> object: ...  # pragma: no cover


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
        container_id = await self._require_running_container()

        def _exec() -> tuple[int, bytes | None, bytes | None]:
            assert self._container is not None  # noqa: S101
            exit_code, (out, err) = self._container.exec_run(command, demux=True)
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
        stdout = _decode_output(raw_stdout)
        stderr = _decode_output(raw_stderr)

        logger.info(
            "sandbox.execute",
            command=command,
            exit_code=exit_code,
            duration_ms=duration_ms,
            container_id=container_id,
        )

        return _build_tool_result(
            command=command,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
        )

    async def execute_stream(
        self,
        command: str,
        timeout: int = 300,
        *,
        output_sink: SandboxOutputSink | None = None,
    ) -> ToolResult:
        """Execute a command and stream decoded stdout/stderr chunks live.

        The final return value preserves the buffered ``ToolResult`` contract used
        by :meth:`execute`, while optionally forwarding incremental output to
        ``output_sink`` for real-time rendering.
        """
        container_id = await self._require_running_container()

        t0 = time.monotonic()
        try:
            exit_code, stdout, stderr = await asyncio.wait_for(
                self._execute_stream_inner(command, output_sink=output_sink),
                timeout=timeout,
            )
        except asyncio.TimeoutError as exc:
            raise SandboxTimeoutError(
                f"Command timed out after {timeout}s: {command}",
                container_id=container_id,
                timeout_seconds=timeout,
            ) from exc

        duration_ms = int((time.monotonic() - t0) * 1000)
        logger.info(
            "sandbox.execute_stream",
            command=command,
            exit_code=exit_code,
            duration_ms=duration_ms,
            container_id=container_id,
        )

        return _build_tool_result(
            command=command,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
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

    async def _require_running_container(self) -> str:
        if self._container is None or self._client is None:
            raise SandboxNotRunningError(
                "No container available — call create() first",
            )

        container_id = self._container.short_id

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

        return container_id

    async def _execute_stream_inner(
        self,
        command: str,
        *,
        output_sink: SandboxOutputSink | None,
    ) -> tuple[int, str, str]:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[tuple[ToolOutputStream, str] | None] = asyncio.Queue()
        exec_task = asyncio.create_task(
            asyncio.to_thread(self._stream_exec_worker, command, loop, queue),
        )

        try:
            while True:
                item = await queue.get()
                if item is None:
                    break

                stream, chunk = item
                if output_sink is None:
                    continue

                maybe_awaitable = output_sink(chunk=chunk, stream=stream)
                if inspect.isawaitable(maybe_awaitable):
                    await maybe_awaitable

            return await exec_task
        finally:
            if not exec_task.done():
                exec_task.cancel()

    def _stream_exec_worker(
        self,
        command: str,
        loop: asyncio.AbstractEventLoop,
        queue: asyncio.Queue[tuple[ToolOutputStream, str] | None],
    ) -> tuple[int, str, str]:
        assert self._container is not None  # noqa: S101
        assert self._client is not None  # noqa: S101

        api = self._client.api
        exec_created = api.exec_create(self._container.id, command)
        exec_id = exec_created["Id"] if isinstance(exec_created, dict) else exec_created

        stdout_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        stderr_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []

        try:
            for stdout_chunk, stderr_chunk in api.exec_start(exec_id, stream=True, demux=True):
                _append_stream_chunk(
                    loop=loop,
                    queue=queue,
                    stream="stdout",
                    raw_chunk=stdout_chunk,
                    decoder=stdout_decoder,
                    parts=stdout_parts,
                )
                _append_stream_chunk(
                    loop=loop,
                    queue=queue,
                    stream="stderr",
                    raw_chunk=stderr_chunk,
                    decoder=stderr_decoder,
                    parts=stderr_parts,
                )

            _flush_stream_decoder(
                loop=loop,
                queue=queue,
                stream="stdout",
                decoder=stdout_decoder,
                parts=stdout_parts,
            )
            _flush_stream_decoder(
                loop=loop,
                queue=queue,
                stream="stderr",
                decoder=stderr_decoder,
                parts=stderr_parts,
            )

            inspect_result = api.exec_inspect(exec_id)
            exit_code = int(inspect_result.get("ExitCode") or 0)
            return exit_code, "".join(stdout_parts), "".join(stderr_parts)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)


def _decode_output(raw_output: bytes | None) -> str:
    return raw_output.decode("utf-8", errors="replace") if raw_output else ""


def _build_tool_result(
    *,
    command: str,
    exit_code: int,
    stdout: str,
    stderr: str,
    duration_ms: int,
) -> ToolResult:
    return ToolResult(
        tool_name="sandbox",
        command=command,
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        duration_ms=duration_ms,
    )


def _append_stream_chunk(
    *,
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue[tuple[ToolOutputStream, str] | None],
    stream: ToolOutputStream,
    raw_chunk: bytes | None,
    decoder: codecs.IncrementalDecoder,
    parts: list[str],
) -> None:
    if not raw_chunk:
        return

    decoded = decoder.decode(raw_chunk, final=False)
    if not decoded:
        return

    parts.append(decoded)
    loop.call_soon_threadsafe(queue.put_nowait, (stream, decoded))


def _flush_stream_decoder(
    *,
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue[tuple[ToolOutputStream, str] | None],
    stream: ToolOutputStream,
    decoder: codecs.IncrementalDecoder,
    parts: list[str],
) -> None:
    decoded = decoder.decode(b"", final=True)
    if not decoded:
        return

    parts.append(decoded)
    loop.call_soon_threadsafe(queue.put_nowait, (stream, decoded))
