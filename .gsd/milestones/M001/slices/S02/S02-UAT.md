# S02: Docker Sandbox + Tool Execution — UAT

**Milestone:** M001
**Written:** 2026-03-13

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: The slice's core claim is real container lifecycle + real tool execution. This requires Docker daemon interaction, not just artifact inspection.

## Preconditions

- Docker daemon running (`docker info` succeeds)
- `pip install -e .` completed in project root
- `oxpwn-sandbox:dev` image built (`docker build -t oxpwn-sandbox:dev docker/`)

## Smoke Test

Run `pytest tests/integration/test_sandbox_integration.py -m integration -v` — all 4 tests pass, proving container create → nmap exec → parse → destroy works end-to-end.

## Test Cases

### 1. Container lifecycle (create → exec → destroy)

1. Run `python3 -c "import asyncio; from oxpwn.sandbox.docker import DockerSandbox; sb = DockerSandbox('oxpwn-sandbox:dev', 'test-uat'); asyncio.run(sb.create()); print(asyncio.run(sb.execute('echo hello', timeout=10))); asyncio.run(sb.destroy())"`
2. **Expected:** ToolResult printed with raw_output containing "hello", exit_code=0
3. Run `docker ps -a --filter label=oxpwn.managed=true`
4. **Expected:** No containers listed (container destroyed)

### 2. Nmap execution with parsed output

1. Run `pytest tests/integration/test_sandbox_integration.py::TestNmapIntegration::test_nmap_localhost_scan -v`
2. **Expected:** Test passes — ToolResult has parsed_output with hosts list, tool_name="nmap", exit_code=0

### 3. Orphan cleanup

1. Run `pytest tests/integration/test_sandbox_integration.py::TestCleanup::test_cleanup_orphans -v`
2. **Expected:** Test passes — orphan container created and cleaned up, final count shows 0 orphans

### 4. Unit tests pass without Docker

1. Stop Docker daemon (or run on a machine without Docker)
2. Run `pytest tests/unit/test_docker_sandbox.py tests/unit/test_nmap_parser.py -v`
3. **Expected:** All 20 tests pass (mocked docker-py, no real Docker needed)

## Edge Cases

### Container not started before exec

1. Create DockerSandbox but don't call create()
2. Call execute()
3. **Expected:** `SandboxNotRunningError` raised with descriptive message

### Image not found

1. Create DockerSandbox with `image="nonexistent:latest"`
2. Call create()
3. **Expected:** `ImageNotFoundError` raised with image_name in exception

### Nmap XML parse failure

1. Run nmap executor where command returns non-XML output
2. **Expected:** ToolResult returned with `parsed_output=None`, no crash, structlog warning emitted

## Failure Signals

- `docker ps -a --filter label=oxpwn.managed=true` shows containers after tests complete
- Integration tests fail with connection errors (Docker not running)
- ToolResult.parsed_output is None when valid XML was expected
- SandboxTimeoutError on commands that should complete quickly

## Requirements Proved By This UAT

- R002 (Isolated Docker/Kali sandbox execution) — Container runs from Kali image, nmap executes inside it, results return to host, container destroys cleanly

## Not Proven By This UAT

- R002 full validation — sandbox used in the complete 5-phase pipeline (deferred to S08)
- Network isolation hardening — no verification of host-to-container boundary beyond Docker defaults
- All 5 tools working in sandbox — only nmap proven (S04 adds the rest)

## Notes for Tester

- Integration tests take ~11 seconds due to container creation and nmap execution
- The `docker_sandbox` fixture is session-scoped — it creates one container for all integration tests
- If Docker is not running, integration tests skip automatically (not fail)
- The Dockerfile uses `kalilinux/kali-rolling` which may need initial pull (~500MB)
