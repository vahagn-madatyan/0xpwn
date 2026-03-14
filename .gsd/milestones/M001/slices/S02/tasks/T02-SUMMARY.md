---
id: T02
parent: S02
milestone: M001
provides:
  - parse_nmap_xml() function for structured nmap XML output parsing
  - NmapExecutor class establishing the tool executor pattern for S04
  - docker_sandbox session fixture for integration tests
  - Integration proof that real nmap runs in real container and produces parsed ToolResult
key_files:
  - src/oxpwn/sandbox/tools/__init__.py
  - src/oxpwn/sandbox/tools/nmap.py
  - tests/unit/test_nmap_parser.py
  - tests/integration/test_sandbox_integration.py
  - tests/conftest.py
key_decisions:
  - Tool executor pattern: constructor takes DockerSandbox, async run() returns ToolResult with parsed_output — uniform interface for all S04 tools
patterns_established:
  - Tool executor pattern (NmapExecutor) — S04 replicates for httpx, subfinder, nuclei, ffuf
  - Session-scoped docker_sandbox fixture with skip-if-no-Docker guard
  - XML parse failure graceful degradation (parsed_output=None, log warning, no crash)
observability_surfaces:
  - structlog warning event nmap.xml_parse_failed with stdout_head/stderr_head on parse failure
  - ToolResult.parsed_output carries structured host/port/service/script data from nmap XML
  - ToolResult.tool_name set to "nmap" for all NmapExecutor results
duration: 12m
verification_result: passed
completed_at: 2026-03-13
blocker_discovered: false
---

# T02: Nmap executor, XML parser, and integration test

**Built nmap XML parser, NmapExecutor class with structured ToolResult output, and 4 integration tests proving real nmap in real Docker container — all passing, zero orphan containers.**

## What Happened

Implemented `parse_nmap_xml()` using `xml.etree.ElementTree` to extract hosts, ports, services, and NSE scripts from nmap `-oX -` XML output. Handles empty scans, hosts with no ports, missing service fields, and non-UTF-8 banner characters.

Built `NmapExecutor` as the canonical tool executor pattern: constructor takes `DockerSandbox`, `async run(target, ports, flags)` returns `ToolResult` with `parsed_output` dict. XML parse failures set `parsed_output=None` and log a structured warning — no crash.

Added `docker_sandbox` session fixture to `tests/conftest.py` that builds the image idempotently, creates a container, yields it, and destroys on teardown. Skips all integration tests when Docker is unreachable.

Wrote 10 unit tests (6 parser + 4 executor) and 4 integration tests (echo exec, container labels, real nmap scan, orphan cleanup).

## Verification

- `pytest tests/unit/test_nmap_parser.py -v` → **10 passed** (no Docker needed)
- `pytest tests/unit/test_docker_sandbox.py tests/unit/test_nmap_parser.py -v` → **20 passed** (all unit tests)
- `pytest tests/integration/test_sandbox_integration.py -m integration -v` → **4 passed** (real Docker)
- `docker ps -a --filter label=oxpwn.managed=true --format '{{.Names}}'` → **empty** (no orphans)

### Slice-level verification status (T02 is final task):
- ✅ `pytest tests/unit/test_docker_sandbox.py tests/unit/test_nmap_parser.py -v` — all 20 pass
- ✅ `pytest tests/integration/test_sandbox_integration.py -m integration -v` — all 4 pass
- ✅ `docker build -t oxpwn-sandbox:dev docker/` — builds (image already cached from integration test)
- ✅ `docker ps -a --filter label=oxpwn.managed=true` — empty after test cleanup

## Diagnostics

- **Parser failures:** structlog event `nmap.xml_parse_failed` with first 200 chars of stdout/stderr
- **Parsed output inspection:** `ToolResult.parsed_output["hosts"]` → list of host dicts with address, hostnames, status, ports
- **Port detail:** each port dict has port_id, protocol, state, service_name, service_product, service_version, scripts
- **Container lifecycle:** inherits all DockerSandbox observability from T01

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `src/oxpwn/sandbox/tools/__init__.py` — tools subpackage init exporting NmapExecutor + parse_nmap_xml
- `src/oxpwn/sandbox/tools/nmap.py` — parse_nmap_xml() + NmapExecutor class (~130 lines)
- `tests/unit/test_nmap_parser.py` — 10 unit tests with 5 realistic XML fixtures
- `tests/integration/test_sandbox_integration.py` — 4 integration tests against real Docker
- `tests/conftest.py` — added docker_sandbox session fixture with skip-if-no-Docker guard
- `.gsd/DECISIONS.md` — recorded tool executor pattern decision (#15)
