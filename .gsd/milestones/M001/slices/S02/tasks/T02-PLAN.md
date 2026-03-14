---
estimated_steps: 4
estimated_files: 5
---

# T02: Nmap executor, XML parser, and integration test

**Slice:** S02 — Docker Sandbox + Tool Execution
**Milestone:** M001

## Description

Build the nmap-specific layer: XML output parser and `NmapExecutor` class that runs nmap in the sandbox and returns structured `ToolResult`. Then write the integration test that proves the full stack against a real Docker daemon — the key proof that retires the "Docker exploitation networking" risk. This task also establishes the tool executor pattern that S04 will replicate for httpx, subfinder, nuclei, and ffuf.

## Steps

1. **Implement `src/oxpwn/sandbox/tools/nmap.py`** — nmap XML parser + executor:
   - `parse_nmap_xml(xml_string: str) -> dict`: Parse nmap `-oX -` XML output using `xml.etree.ElementTree`. Extract into structured dict with keys: `hosts` (list of dicts with `address`, `hostnames`, `status`, `ports`), each port as dict with `port_id`, `protocol`, `state`, `service_name`, `service_product`, `service_version`, `scripts` (list of script id + output). Handle empty scans (no hosts), hosts with no open ports, missing service info. Decode with `errors='replace'` for non-UTF8 banners.
   - `NmapExecutor` class: `__init__(sandbox: DockerSandbox)`. Method `async run(target: str, ports: str | None = None, flags: str = "-sV") -> ToolResult`. Builds command: `nmap {flags} -oX - {-p ports if ports} {target}`. Calls `sandbox.execute(command)`. Parses stdout XML into `parsed_output` via `parse_nmap_xml()`. If XML parsing fails (non-XML output on error), set `parsed_output` to None and log warning. Returns the enriched `ToolResult`.

2. **Write `tests/unit/test_nmap_parser.py`** — unit tests for XML parsing with fixture data:
   - Test parse XML with typical scan (2 hosts, multiple ports, services) — verify host count, port data, service names
   - Test parse XML with empty scan (0 hosts up) — verify empty hosts list, no crash
   - Test parse XML with host but no open ports — verify host present, ports list empty
   - Test parse XML with service scripts (e.g., http-title, ssl-cert) — verify script data extracted
   - Test parse XML with non-UTF8 characters in banner — verify no crash, replacement char used
   - Test NmapExecutor.run() with mocked sandbox — verify command construction, parsed_output populated
   - Include realistic nmap XML fixture strings as constants in the test file

3. **Add `docker_sandbox` fixture to `tests/conftest.py`** for integration tests:
   - Factory fixture that builds the image (idempotent — skip if exists), creates `DockerSandbox`, yields it, and destroys on teardown
   - Mark with `@pytest.fixture(scope="session")` to reuse container across integration tests
   - Skip entire fixture if Docker daemon is not reachable (`docker.from_env()` fails → `pytest.skip`)

4. **Write `tests/integration/test_sandbox_integration.py`** — real Docker integration tests:
   - `@pytest.mark.integration` on all tests
   - Test 1: sandbox creates container, execs `echo hello`, gets stdout="hello", exit_code=0, destroys cleanly
   - Test 2: nmap executor runs `nmap -sV -p 80 localhost` inside container, gets ToolResult with parsed_output containing hosts/ports data (localhost port 80 will likely be closed, that's fine — the parser must handle it)
   - Test 3: container labels are set correctly (`oxpwn.managed=true`)
   - Test 4: cleanup_orphans removes the test container if still running
   - Verify no containers with `oxpwn.managed=true` label remain after test session

## Must-Haves

- [ ] `parse_nmap_xml()` handles: open ports, closed ports, empty scan, services, scripts, non-UTF8
- [ ] `NmapExecutor.run()` returns `ToolResult` with `parsed_output` dict containing hosts/ports
- [ ] Integration test runs real nmap in real container against real Docker daemon
- [ ] Integration tests skip gracefully when Docker is unavailable
- [ ] No orphan containers after test teardown
- [ ] Tool executor pattern established for S04 to follow (constructor takes sandbox, `run()` returns `ToolResult`)

## Verification

- `pytest tests/unit/test_nmap_parser.py -v` — all XML parser tests pass without Docker
- `pytest tests/integration/test_sandbox_integration.py -m integration -v` — passes with Docker, skips without
- `docker ps -a --filter label=oxpwn.managed=true --format '{{.Names}}'` — empty after tests complete

## Inputs

- `src/oxpwn/sandbox/docker.py` — `DockerSandbox` class from T01
- `src/oxpwn/sandbox/exceptions.py` — exception types from T01
- `src/oxpwn/core/models.py` — `ToolResult` model (output contract)
- `docker/Dockerfile` — image definition from T01

## Expected Output

- `src/oxpwn/sandbox/tools/__init__.py` — tools subpackage init
- `src/oxpwn/sandbox/tools/nmap.py` — `parse_nmap_xml()` + `NmapExecutor` class (~120 lines)
- `tests/unit/test_nmap_parser.py` — ~7 unit tests with XML fixture data
- `tests/integration/test_sandbox_integration.py` — ~4 integration tests against real Docker
- `tests/conftest.py` — updated with `docker_sandbox` session fixture
