---
estimated_steps: 5
estimated_files: 7
---

# T01: Dockerfile, DockerSandbox class, and sandbox unit tests

**Slice:** S02 — Docker Sandbox + Tool Execution
**Milestone:** M001

## Description

Build the container lifecycle substrate: a Kali-based Dockerfile with nmap, the `DockerSandbox` async context manager class, and typed exceptions. This task produces the generic sandbox infrastructure — no tool-specific parsing yet. Unit tests use mocked docker-py to verify lifecycle correctness without requiring Docker.

## Steps

1. **Add `docker>=7.0` to pyproject.toml** runtime dependencies. Re-run `pip install -e ".[dev]"` to pick it up.

2. **Write `docker/Dockerfile`** based on `kalilinux/kali-rolling`:
   - `RUN apt-get update && apt-get install -y --no-install-recommends nmap && rm -rf /var/lib/apt/lists/*` (single layer, clean cache)
   - `CMD ["sleep", "infinity"]` — keeps container alive for exec
   - Add `LABEL maintainer="0xpwn"` for identification

3. **Create `src/oxpwn/sandbox/exceptions.py`** with typed exception hierarchy following the `llm/exceptions.py` pattern:
   - `SandboxError(message, container_id=None)` — base
   - `SandboxNotRunningError(SandboxError)` — exec into stopped container
   - `SandboxTimeoutError(SandboxError)` — command exceeded timeout, include `timeout_seconds` field
   - `ImageNotFoundError(SandboxError)` — image not built/pulled, include `image_name` field

4. **Implement `src/oxpwn/sandbox/docker.py`** — `DockerSandbox` class:
   - Constructor: `__init__(image, scan_id, network_mode="bridge")`. Store image name, scan_id (uuid), generate container labels `{"oxpwn.managed": "true", "oxpwn.scan_id": scan_id}`.
   - `async __aenter__` / `async __aexit__`: create container on enter, destroy on exit (even on exception).
   - `async create()`: `docker.from_env()`, `client.containers.create(image, command="sleep infinity", detach=True, cap_add=["NET_ADMIN", "NET_RAW"], labels=labels, network_mode=network_mode)`, then `container.start()`. Wrap in `asyncio.to_thread()`. Handle `docker.errors.ImageNotFound` → `ImageNotFoundError`. Log via structlog.
   - `async execute(command: str, timeout: int = 300) -> ToolResult`: `container.exec_run(command, demux=True)` wrapped in `to_thread()`, then wrapped in `asyncio.wait_for(timeout=timeout)`. Decode stdout/stderr with `errors='replace'`. Build `ToolResult` with timing via `time.monotonic()`. Handle `asyncio.TimeoutError` → `SandboxTimeoutError`. Raise `SandboxNotRunningError` if container isn't running.
   - `async destroy()`: `container.stop(timeout=5)`, `container.remove(force=True)`. Swallow errors (best-effort cleanup). Log.
   - `@classmethod async def cleanup_orphans()`: Find containers by label `oxpwn.managed=true`, stop and remove each. Swallow individual errors. Return count removed.

5. **Write `tests/unit/test_docker_sandbox.py`** — unit tests with mocked docker-py:
   - Test create sets correct labels, capabilities, command
   - Test execute returns ToolResult with stdout/stderr/exit_code/duration_ms
   - Test execute timeout raises SandboxTimeoutError
   - Test destroy calls stop + remove
   - Test context manager calls create on enter, destroy on exit
   - Test context manager destroy on exception
   - Test ImageNotFound raises ImageNotFoundError
   - Test execute on stopped container raises SandboxNotRunningError
   - Test cleanup_orphans finds and removes labeled containers

## Must-Haves

- [ ] Dockerfile builds with `docker build -t oxpwn-sandbox:dev docker/`
- [ ] `DockerSandbox` is an async context manager (`async with`)
- [ ] All docker-py calls wrapped in `asyncio.to_thread()` — no sync calls in async methods
- [ ] Containers labeled with `oxpwn.managed=true` and `oxpwn.scan_id=<uuid>`
- [ ] `execute()` returns `ToolResult` with `duration_ms` (int, milliseconds)
- [ ] `execute()` uses `demux=True` for separate stdout/stderr
- [ ] `cleanup_orphans()` classmethod finds containers by label
- [ ] Exception hierarchy carries `container_id` context
- [ ] Unit tests pass without Docker installed

## Verification

- `docker build -t oxpwn-sandbox:dev docker/` completes successfully
- `pytest tests/unit/test_docker_sandbox.py -v` — all tests pass, no Docker needed
- `python3 -c "from oxpwn.sandbox.docker import DockerSandbox; print('import ok')"` — no import errors

## Observability Impact

- Signals added: structlog events `sandbox.create` (image, scan_id, container_id), `sandbox.execute` (command, exit_code, duration_ms), `sandbox.destroy` (container_id), `sandbox.cleanup_orphans` (count)
- How a future agent inspects this: `docker ps --filter label=oxpwn.managed=true` for live containers; structlog JSON for lifecycle events
- Failure state exposed: SandboxError subtypes with container_id; ToolResult.stderr + exit_code for command failures

## Inputs

- `src/oxpwn/core/models.py` — `ToolResult` model is the output contract for `execute()`
- `src/oxpwn/llm/exceptions.py` — pattern for typed exception hierarchy with context fields
- `pyproject.toml` — add `docker>=7.0` dependency

## Expected Output

- `docker/Dockerfile` — Kali + nmap sandbox image definition
- `src/oxpwn/sandbox/__init__.py` — subpackage init exporting DockerSandbox
- `src/oxpwn/sandbox/exceptions.py` — 4 exception classes with context
- `src/oxpwn/sandbox/docker.py` — async DockerSandbox class (~150 lines)
- `tests/unit/test_docker_sandbox.py` — ~9 unit tests with mocked docker-py
- `pyproject.toml` — updated with docker dependency
