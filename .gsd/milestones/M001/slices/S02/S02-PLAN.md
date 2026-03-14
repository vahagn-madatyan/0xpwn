# S02: Docker Sandbox + Tool Execution

**Goal:** Docker container spawns from custom Kali base image, executes nmap inside it, returns structured parsed output, and tears down cleanly.
**Demo:** Integration test creates a container, runs nmap, gets parsed `ToolResult` with XML-derived `parsed_output`, and destroys the container — all async, with orphan cleanup on failure.

## Must-Haves

- Custom Dockerfile based on `kalilinux/kali-rolling` with nmap installed
- `DockerSandbox` async context manager: create container with labels + NET_ADMIN/NET_RAW, exec commands, destroy on exit
- Orphan container cleanup via `oxpwn.managed=true` labels
- Typed exception hierarchy: `SandboxError`, `SandboxNotRunningError`, `SandboxTimeoutError`, `ImageNotFoundError`
- Nmap XML output parser producing structured dict for `ToolResult.parsed_output`
- `NmapExecutor` that builds nmap commands, runs via sandbox, parses XML, returns `ToolResult`
- `docker>=7.0` added to pyproject.toml dependencies
- Unit tests for sandbox lifecycle (mocked docker-py) and nmap XML parsing (fixture data)
- Integration test proving real nmap in real container against real Docker daemon

## Proof Level

- This slice proves: integration (real Docker daemon, real nmap binary, real XML output)
- Real runtime required: yes (Docker daemon for integration tests)
- Human/UAT required: no

## Verification

- `pytest tests/unit/test_docker_sandbox.py tests/unit/test_nmap_parser.py -v` — all pass (mocked, no Docker needed)
- `pytest tests/integration/test_sandbox_integration.py -m integration -v` — passes with Docker running, skips without
- `docker build -t oxpwn-sandbox:dev docker/` — builds successfully
- Verify no orphan containers: `docker ps -a --filter label=oxpwn.managed=true` shows none after test cleanup

## Observability / Diagnostics

- Runtime signals: structlog events for container create/exec/destroy with container_id, command, exit_code, duration_ms
- Inspection surfaces: `docker ps --filter label=oxpwn.managed=true` shows any managed containers; `DockerSandbox.cleanup_orphans()` classmethod
- Failure visibility: `SandboxError` subtypes carry container_id; `ToolResult` captures stderr + exit_code
- Redaction constraints: none (no secrets in sandbox layer)

## Integration Closure

- Upstream surfaces consumed: `oxpwn.core.models.ToolResult` (output contract), exception pattern from `oxpwn.llm.exceptions`
- New wiring introduced: `oxpwn.sandbox.docker.DockerSandbox` + `oxpwn.sandbox.tools.nmap.NmapExecutor` — new subpackage
- What remains before milestone is usable: S03 (agent loop to drive the sandbox), S04 (4 more tool executors), S05 (CLI wiring)

## Tasks

- [x] **T01: Dockerfile, DockerSandbox class, and sandbox unit tests** `est:35m`
  - Why: Establishes the container lifecycle substrate — image, async class, exceptions, orphan cleanup. Everything in T02 depends on this.
  - Files: `docker/Dockerfile`, `pyproject.toml`, `src/oxpwn/sandbox/__init__.py`, `src/oxpwn/sandbox/exceptions.py`, `src/oxpwn/sandbox/docker.py`, `tests/unit/test_docker_sandbox.py`
  - Do: Write Dockerfile (kali-rolling + nmap + sleep infinity CMD). Add `docker>=7.0` dep. Create sandbox exception hierarchy mirroring llm/exceptions.py pattern. Implement `DockerSandbox` with async context manager, `create()`, `execute(command, timeout)`, `destroy()`, `cleanup_orphans()` classmethod. All docker-py calls wrapped in `asyncio.to_thread()`. Label containers with `oxpwn.managed=true` + `oxpwn.scan_id`. Unit tests mock `docker.from_env()` to verify lifecycle, error handling, label application, demux, and timeout enforcement.
  - Verify: `pytest tests/unit/test_docker_sandbox.py -v` — all pass without Docker
  - Done when: DockerSandbox creates/exec/destroys containers via mocked docker-py, exceptions carry context, Dockerfile builds

- [x] **T02: Nmap executor, XML parser, and integration test** `est:30m`
  - Why: Proves the full stack — real nmap in real container produces parsed `ToolResult`. Retires the "Docker exploitation networking" risk from the roadmap.
  - Files: `src/oxpwn/sandbox/tools/__init__.py`, `src/oxpwn/sandbox/tools/nmap.py`, `tests/unit/test_nmap_parser.py`, `tests/integration/test_sandbox_integration.py`, `tests/conftest.py`
  - Do: Implement `NmapExecutor` with `run(target, ports, flags)` → `ToolResult`. Parse nmap XML (`-oX -`) with `xml.etree.ElementTree` into structured dict (hosts, ports, services, scripts). Unit tests cover XML parsing with fixture data (open ports, closed ports, empty scan, service detection). Integration test: build image, create sandbox, exec nmap against container localhost, parse output, verify ToolResult fields, destroy container. Add `docker_sandbox` fixture to conftest.py.
  - Verify: `pytest tests/unit/test_nmap_parser.py tests/integration/test_sandbox_integration.py -v -m "not integration or integration"` — unit tests always pass, integration tests pass with Docker
  - Done when: `ToolResult` from real nmap execution has `parsed_output` dict with host/port data, container cleans up, no orphans remain

## Files Likely Touched

- `docker/Dockerfile`
- `pyproject.toml`
- `src/oxpwn/sandbox/__init__.py`
- `src/oxpwn/sandbox/exceptions.py`
- `src/oxpwn/sandbox/docker.py`
- `src/oxpwn/sandbox/tools/__init__.py`
- `src/oxpwn/sandbox/tools/nmap.py`
- `tests/conftest.py`
- `tests/unit/test_docker_sandbox.py`
- `tests/unit/test_nmap_parser.py`
- `tests/integration/test_sandbox_integration.py`
