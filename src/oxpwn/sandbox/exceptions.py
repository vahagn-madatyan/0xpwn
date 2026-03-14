"""Typed exception hierarchy for Docker sandbox errors."""

from __future__ import annotations


class SandboxError(Exception):
    """Base exception for all sandbox errors.

    Carries container_id context for diagnostics.
    """

    def __init__(
        self,
        message: str,
        *,
        container_id: str | None = None,
    ) -> None:
        self.container_id = container_id
        super().__init__(message)


class SandboxNotRunningError(SandboxError):
    """Raised when executing a command against a stopped container."""


class SandboxTimeoutError(SandboxError):
    """Raised when a command exceeds the allowed timeout.

    Carries the timeout_seconds that was exceeded.
    """

    def __init__(
        self,
        message: str,
        *,
        container_id: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(message, container_id=container_id)


class ImageNotFoundError(SandboxError):
    """Raised when the requested Docker image is not available.

    Carries the image_name that was not found.
    """

    def __init__(
        self,
        message: str,
        *,
        container_id: str | None = None,
        image_name: str | None = None,
    ) -> None:
        self.image_name = image_name
        super().__init__(message, container_id=container_id)
