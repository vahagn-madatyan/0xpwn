---
id: S02
parent: M001
milestone: M001
provides:
  - DockerSandbox async context manager for container lifecycle (create, exec, destroy)
  - Typed sandbox exception hierarchy (SandboxError, SandboxNotRunningError, SandboxTimeoutError, ImageNotFoundError)
  - Kali-based Dockerfile with nmap installed
  - parse_nmap_xml() structured XML parser
  - NmapExecutor tool executor pattern (reference implementation for S04)
  - Orphan container cleanup via oxpwn.managed=true labels
  - docker>=7.0 project dependency
requires:
  - slice: S01
    provides: oxpwn.core.models.ToolResult (output contract), exception pattern from oxpwn.llm.exceptions
affects:
  - S03 (agent loop drives DockerSandbox)
  - S04 (4 more tool executors replicate NmapExecutor pattern)
key_files:
  - docker/Dockerfile
  - src/oxpwn/sandbox/__init__.py
  - src/oxpwn/sandbox/exceptions.py
  - src/oxpwn/sandbox/docker.py
  - src/oxpwn/sandbox/tools/__init__.py
  - src/oxpwn/sandbox/tools/nmap.py
  - tests/unit/test_docker_sandbox.py
  - tests/unit/test_nmap_parser.py
  - tests/integration/test_sandbox_integration.py
  - tests/conftest.py
key_decisions:
  - All docker-py calls wrapped in asyncio.to_thread() to keep async event loop unblocked
  - Container labels use oxpwn.managed=true + oxpwn.scan_id for lifecycle tracking
  - execute() returns ToolResult directly (reuses core model, no sandbox-specific result type)
  - Tool executor pattern — constructor takes DockerSandbox, async run() returns ToolResult with parsed_output
  - XML parse failure graceful degradation (parsed_output=None, log warning, no crash)
patterns_established:
  - Sandbox exception hierarchy mirrors llm/exceptions.py pattern with context fields (container_id, timeout_seconds, image_name)
  - Async context manager pattern for resource cleanup (create on enter, destroy on exit even on exception)
  - Tool executor pattern (NmapExecutor) — S04 replicates for httpx, subfinder, nuclei, ffuf
  - Session-scoped docker_sandbox fixture with skip-if-no-Docker guard
observability_surfaces:
  - structlog events: sandbox.create, sandbox.execute, sandbox.destroy, sandbox.cleanup_orphans
  - structlog warning: nmap.xml_parse_failed with stdout_head/stderr_head on parse failure
  - docker ps --filter label=oxpwn.managed=true for live container inspection
  - DockerSandbox.cleanup_orphans() classmethod returns count removed
  - SandboxError subtypes carry container_id for correlation
  - ToolResult.parsed_output carries structured host/port/service/script data from nmap XML
drill_down_paths:
  - .gsd/milestones/M001/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001/slices/S02/tasks/T02-SUMMARY.md
duration: 20m
verification_result: passed
completed_at: 2026-03-13
---

# S02: Docker Sandbox + Tool Execution

**Kali-based Docker sandbox with async container lifecycle, nmap tool execution producing structured parsed output, and clean teardown — proven by 20 unit tests and 4 integration tests against a real Docker daemon.**

## What Happened

Built the container execution substrate in two tasks:

**T01 — Container lifecycle:** Created `docker/Dockerfile` based on `kalilinux/kali-rolling` with nmap installed and `sleep infinity` CMD. Implemented `DockerSandbox` (~160 lines) as an async context manager with `create()`, `execute(command, timeout)`, `destroy()`, and `cleanup_orphans()` classmethod. All docker-py calls wrapped in `asyncio.to_thread()` to avoid blocking the event loop. Containers are labeled with `oxpwn.managed=true` and `oxpwn.scan_id` for lifecycle tracking and orphan cleanup. Created a 4-class typed exception hierarchy (`SandboxError` → `SandboxNotRunningError`, `SandboxTimeoutError`, `ImageNotFoundError`) mirroring the llm/exceptions.py pattern. 10 unit tests with fully mocked docker-py verify lifecycle, error handling, labels, demux, and timeout enforcement.

**T02 — Tool execution + parsing:** Implemented `parse_nmap_xml()` using `xml.etree.ElementTree` to extract hosts, ports, services, and NSE scripts from nmap `-oX -` XML output. Handles empty scans, hosts with no ports, missing service fields, and non-UTF-8 characters. Built `NmapExecutor` as the canonical tool executor pattern: constructor takes `DockerSandbox`, `async run(target, ports, flags)` returns `ToolResult` with `parsed_output` dict. XML parse failures gracefully degrade — `parsed_output=None`, structured warning logged, no crash. Added session-scoped `docker_sandbox` fixture to conftest.py with skip-if-no-Docker guard. 10 unit tests (6 parser + 4 executor) and 4 integration tests (echo exec, container labels, real nmap scan, orphan cleanup).

## Verification

- `pytest tests/unit/test_docker_sandbox.py tests/unit/test_nmap_parser.py -v` — **20/20 passed** (0.16s, no Docker needed)
- `pytest tests/integration/test_sandbox_integration.py -m integration -v` — **4/4 passed** (10.98s, real Docker daemon)
- `docker build -t oxpwn-sandbox:dev docker/` — builds successfully (image cached)
- `docker ps -a --filter label=oxpwn.managed=true` — empty after test cleanup (no orphans)

**Risk retired:** "Docker exploitation networking" — proven a container can run nmap against a target on the Docker bridge network and return structured results.

## Requirements Advanced

- R002 (Isolated Docker/Kali sandbox execution) — Docker container created from Kali image with NET_ADMIN/NET_RAW caps, real nmap execution proven, clean teardown verified, orphan cleanup implemented

## Requirements Validated

- None — R002 is advanced but not fully validated until S08 proves end-to-end scan with sandbox in the full pipeline

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

None.

## Known Limitations

- Dockerfile installs only nmap — S04 will add httpx, subfinder, nuclei, ffuf
- No network isolation between sandbox container and host beyond Docker defaults
- No resource limits (CPU/memory) on sandbox containers yet — acceptable for M001, may need for M002+
- `sleep infinity` CMD means containers must be explicitly destroyed (handled by context manager, but dangling containers possible if process killed without cleanup)

## Follow-ups

- S04 will add 4 more tool executors (httpx, subfinder, nuclei, ffuf) replicating the NmapExecutor pattern
- S03 will wire DockerSandbox into the agent loop for autonomous tool dispatch
- Consider adding container resource limits in M002 for safety/budget controls

## Files Created/Modified

- `docker/Dockerfile` — Kali-based sandbox image (nmap, sleep infinity)
- `pyproject.toml` — added `docker>=7.0` to runtime dependencies
- `src/oxpwn/sandbox/__init__.py` — subpackage init exporting DockerSandbox + exceptions
- `src/oxpwn/sandbox/exceptions.py` — 4-class typed exception hierarchy with context fields
- `src/oxpwn/sandbox/docker.py` — async DockerSandbox class (~160 lines)
- `src/oxpwn/sandbox/tools/__init__.py` — tools subpackage init exporting NmapExecutor + parse_nmap_xml
- `src/oxpwn/sandbox/tools/nmap.py` — parse_nmap_xml() + NmapExecutor class (~130 lines)
- `tests/unit/test_docker_sandbox.py` — 10 unit tests with mocked docker-py
- `tests/unit/test_nmap_parser.py` — 10 unit tests with 5 realistic XML fixtures
- `tests/integration/test_sandbox_integration.py` — 4 integration tests against real Docker
- `tests/conftest.py` — added docker_sandbox session fixture with skip-if-no-Docker guard

## Forward Intelligence

### What the next slice should know
- `DockerSandbox` is an async context manager — use `async with DockerSandbox(image, scan_id) as sb:` then `await sb.execute(cmd, timeout)`. Returns `ToolResult` directly.
- The `NmapExecutor` pattern is the template for all S04 tool executors: constructor takes sandbox, `async run()` returns `ToolResult` with `parsed_output`.
- Image must be built before sandbox use — `docker build -t oxpwn-sandbox:dev docker/`. Integration tests handle this in the fixture.
- `conftest.py` has a session-scoped `docker_sandbox` fixture that skips when Docker is unreachable.

### What's fragile
- `parse_nmap_xml()` handles common nmap output but hasn't been tested against all nmap scan types (UDP, OS detection, aggressive scans) — S04 may surface edge cases
- The `sleep infinity` CMD keeps containers alive until explicit destroy — if the Python process is killed (SIGKILL), orphan containers remain until `cleanup_orphans()` is called

### Authoritative diagnostics
- `docker ps --filter label=oxpwn.managed=true` — shows any running managed containers, should be empty between scans
- `ToolResult.exit_code` + `ToolResult.raw_output` — first place to look when tool execution fails
- structlog events with `sandbox.*` namespace — full lifecycle trace

### What assumptions changed
- No assumptions changed — implementation matched the plan exactly
