---
id: T01
parent: S02
milestone: M001
provides:
  - DockerSandbox async context manager for container lifecycle
  - Typed sandbox exception hierarchy (SandboxError, SandboxNotRunningError, SandboxTimeoutError, ImageNotFoundError)
  - Kali-based Dockerfile with nmap
  - docker>=7.0 project dependency
key_files:
  - src/oxpwn/sandbox/docker.py
  - src/oxpwn/sandbox/exceptions.py
  - docker/Dockerfile
  - tests/unit/test_docker_sandbox.py
key_decisions:
  - All docker-py calls wrapped in asyncio.to_thread() to keep async event loop unblocked
  - Container labels use oxpwn.managed=true + oxpwn.scan_id for lifecycle tracking
  - execute() returns ToolResult directly (reuses core model, no sandbox-specific result type)
patterns_established:
  - Sandbox exception hierarchy mirrors llm/exceptions.py pattern with context fields (container_id, timeout_seconds, image_name)
  - async context manager pattern for resource cleanup (create on enter, destroy on exit even on exception)
observability_surfaces:
  - structlog events: sandbox.create, sandbox.execute, sandbox.destroy, sandbox.cleanup_orphans
  - docker ps --filter label=oxpwn.managed=true for live container inspection
  - SandboxError subtypes carry container_id for correlation
duration: 8m
verification_result: passed
completed_at: 2026-03-13
blocker_discovered: false
---

# T01: Dockerfile, DockerSandbox class, and sandbox unit tests

**Built Kali-based Dockerfile, async DockerSandbox context manager with labeled container lifecycle, typed exception hierarchy, and 10 mocked unit tests — all passing without Docker.**

## What Happened

Created the container lifecycle substrate for the sandbox subsystem:

1. Added `docker>=7.0` to pyproject.toml and installed.
2. Wrote `docker/Dockerfile` — kali-rolling base, nmap installed in single clean layer, sleep infinity CMD.
3. Created `src/oxpwn/sandbox/exceptions.py` with 4-class hierarchy: `SandboxError` (base, carries container_id), `SandboxNotRunningError`, `SandboxTimeoutError` (adds timeout_seconds), `ImageNotFoundError` (adds image_name). Follows the llm/exceptions.py pattern.
4. Implemented `src/oxpwn/sandbox/docker.py` — `DockerSandbox` class (~160 lines): async context manager with `create()`, `execute()`, `destroy()`, and `cleanup_orphans()` classmethod. All docker-py calls wrapped in `asyncio.to_thread()`. Containers labeled with `oxpwn.managed=true` and `oxpwn.scan_id`. execute() uses `demux=True`, returns `ToolResult` with `duration_ms` via `time.monotonic()`.
5. Wrote 10 unit tests with fully mocked docker-py covering creation config, execute happy path, timeout, stopped container, no-create, destroy, context manager enter/exit, exception on exit, and orphan cleanup.

## Verification

- `python3 -c "from oxpwn.sandbox.docker import DockerSandbox; print('import ok')"` — ✅ no import errors
- `pytest tests/unit/test_docker_sandbox.py -v` — ✅ 10/10 passed in 0.12s, no Docker needed
- Dockerfile syntax valid (FROM, LABEL, RUN, CMD all correct)

### Slice-level verification (partial — T01 only):
- ✅ `pytest tests/unit/test_docker_sandbox.py -v` — all pass
- ⏳ `pytest tests/unit/test_nmap_parser.py -v` — not yet created (T02)
- ⏳ `pytest tests/integration/test_sandbox_integration.py -m integration -v` — not yet created (T02)
- ⏳ `docker build -t oxpwn-sandbox:dev docker/` — Dockerfile written, build requires Docker daemon (verified in T02)

## Diagnostics

- **Live containers:** `docker ps --filter label=oxpwn.managed=true`
- **Orphan cleanup:** `await DockerSandbox.cleanup_orphans()` returns count removed
- **Structured logs:** structlog JSON events with `sandbox.create` (image, scan_id, container_id), `sandbox.execute` (command, exit_code, duration_ms), `sandbox.destroy` (container_id), `sandbox.cleanup_orphans` (count)
- **Error correlation:** All SandboxError subtypes carry `container_id` field

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `pyproject.toml` — added `docker>=7.0` to runtime dependencies
- `docker/Dockerfile` — Kali-based sandbox image (nmap, sleep infinity)
- `src/oxpwn/sandbox/__init__.py` — subpackage init exporting DockerSandbox + exceptions
- `src/oxpwn/sandbox/exceptions.py` — 4-class typed exception hierarchy with context fields
- `src/oxpwn/sandbox/docker.py` — async DockerSandbox class (~160 lines)
- `tests/unit/test_docker_sandbox.py` — 10 unit tests with mocked docker-py
