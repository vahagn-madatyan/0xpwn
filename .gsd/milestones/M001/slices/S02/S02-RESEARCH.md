# S02: Docker Sandbox + Tool Execution — Research

**Date:** 2026-03-13

## Summary

S02 builds the Docker sandbox (container lifecycle) and the first tool executor (nmap + parser). The core deliverables are: (1) a `DockerSandbox` class wrapping docker-py that creates, exec's commands in, and destroys ephemeral Kali-based containers with NET_ADMIN/NET_RAW capabilities; (2) an nmap tool executor that runs `nmap -oX -` inside the container and parses XML output into Pydantic models; (3) a Dockerfile for the custom sandbox image; and (4) integration tests proving a container can run nmap against a target on the Docker bridge network and return parsed results.

The key architectural decision is using docker-py (synchronous) wrapped with `asyncio.to_thread()` for non-blocking async integration. This is the standard pattern — docker-py has a 9.9/10 trust score on Context7, is battle-tested, and every serious AI pentesting tool (Strix, PentAGI, PentestAgent) uses it for sandbox management. The alternative `aiodocker` is less mature with a different API and smaller community. The async wrapping approach keeps us on the proven library while maintaining the async contract established in S01's `LLMClient`.

For nmap output, XML parsing via `nmap -oX -` (output to stdout) with stdlib `xml.etree.ElementTree` is the clear winner over regex-based text parsing or the `python-nmap` wrapper library. XML output has a well-defined schema (host/port/service/script elements), is deterministic across nmap versions, and produces structured data directly. The `python-nmap` library adds an unnecessary dependency that wraps nmap invocation — we already handle invocation via the sandbox.

## Recommendation

Build a two-layer architecture: `DockerSandbox` handles container lifecycle (generic), and tool-specific executors handle command construction + output parsing. This separation means S04 can add 4 more tools by writing only new executor classes, reusing the sandbox entirely.

**Container approach:** One long-lived container per scan session. Create on scan start, exec commands into it throughout the scan, destroy on completion. This avoids the overhead of creating a new container per tool invocation (docker create takes ~1-2s each time). The Strix and PentAGI patterns confirm this approach — both keep a container alive for the session.

**Image approach:** Custom Dockerfile based on `kalilinux/kali-rolling` with only nmap installed for S02. The image will be extended in S04 to include httpx, subfinder, nuclei, and ffuf. The Decision #6 specifies eventual publishing to `ghcr.io/0xpwn/sandbox`, but for S02 we'll build locally.

**Async approach:** Wrap all docker-py calls in `asyncio.to_thread()` to maintain the async contract. The `DockerSandbox` methods will be `async def` but internally dispatch sync docker-py calls to a thread pool. This is clean, predictable, and avoids the footguns of `aiodocker`.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Docker container lifecycle | `docker` (docker-py) SDK | 9.9/10 trust score, standard container.create/start/exec_run/stop/remove API, handles networking/capabilities/labels. Every reference project uses it. |
| Nmap XML parsing | `xml.etree.ElementTree` (stdlib) | nmap XML schema is well-defined and stable. No external dep needed. Self-generated output = no XXE risk. |
| Async wrapping of sync SDK | `asyncio.to_thread()` (stdlib) | Built into Python 3.9+, single-line wrapper, no third-party async adapter needed. |
| Container cleanup on crash | `atexit` + context manager | stdlib `atexit` for interpreter exit, `__aenter__/__aexit__` for structured scopes. Strix uses the same pattern. |

## Existing Code and Patterns

- `src/oxpwn/core/models.py` — `ToolResult` model is the output contract for tool execution. Fields: `tool_name`, `command`, `stdout`, `stderr`, `exit_code`, `duration_ms`, `parsed_output` (optional dict). The sandbox `execute()` method must return this model.
- `src/oxpwn/llm/client.py` — Established async pattern: public methods are `async def`, internally wrap sync calls, return Pydantic models. `DockerSandbox` should follow the same style.
- `src/oxpwn/llm/exceptions.py` — Typed exception hierarchy pattern with context fields (model, provider). Sandbox exceptions should follow: `SandboxError(message, container_id=)`, `SandboxNotRunningError`, `SandboxTimeoutError`, `ImageNotFoundError`.
- `tests/conftest.py` — Fixture factory pattern (`scan_state_factory`). Sandbox tests should add a `docker_sandbox` fixture that creates/destroys containers with proper cleanup.
- `pyproject.toml` — Dependencies list needs `docker>=7.0` added. No other new runtime deps needed for S02.

## Constraints

- **docker-py is synchronous** — All docker SDK calls block. Must wrap with `asyncio.to_thread()` for every container operation (create, exec, stop, remove). Cannot mix sync docker-py calls into an async event loop directly.
- **Docker Desktop must be running** — Integration tests require a live Docker daemon. Tests must skip gracefully (`pytest.importorskip` or daemon connectivity check) when Docker is unavailable.
- **Kali image is large** — `kalilinux/kali-rolling` base is ~200MB compressed. With nmap installed, expect ~300-400MB. First `docker build` will take time. Tests should reuse the image, not rebuild per test.
- **Bridge networking limitations** — Default bridge networking works for outbound scanning (container → target) but prevents inbound connections (target → container). Reverse shells won't work. This is acceptable for M001 (noted in roadmap as a known limitation). On macOS, containers reach the host via `host.docker.internal`.
- **ToolResult.duration_ms is an int** — S01 defined it as milliseconds (int), not seconds (float). Sandbox timer must convert accordingly.
- **No host filesystem mounts** — Decision #6 and R002 require complete isolation. The sandbox must never mount host paths. All data exchange happens through exec stdout/stderr.
- **Container needs NET_ADMIN + NET_RAW** — nmap requires raw socket access for SYN scanning. Without these capabilities, nmap falls back to slower TCP connect scans. Pass via `cap_add=["NET_ADMIN", "NET_RAW"]` in container creation.

## Common Pitfalls

- **Orphan containers on crash** — If the Python process crashes or is killed (SIGKILL), `atexit` handlers may not run. Mitigate: label all containers with `oxpwn.managed=true` + `oxpwn.scan_id=<uuid>`, and add a `DockerSandbox.cleanup_orphans()` classmethod that finds/removes stale containers by label. Run it on next startup.
- **exec_run blocking forever** — nmap scans can take minutes; `exec_run` blocks until completion. Must enforce a timeout. docker-py `exec_run` doesn't support timeout directly — use `socket=True` or `stream=True` and implement timeout externally via `asyncio.wait_for()` wrapping the `to_thread()` call.
- **Demux stdout/stderr** — `exec_run(demux=True)` returns a tuple `(stdout_bytes, stderr_bytes)`. Without `demux=True`, stdout and stderr are interleaved in a single bytestream. Always use `demux=True` for clean ToolResult population.
- **nmap exit codes** — nmap returns 0 on success but also 0 when hosts are down. Non-zero exit codes indicate runtime errors (bad flags, permission denied). The parser must handle "0 hosts up" gracefully, not treat it as a failure.
- **XML encoding edge cases** — nmap XML output may contain non-UTF8 characters in service banners. Use `errors='replace'` when decoding bytes to str. Also handle empty XML (no hosts found) without crashing.
- **Image build caching** — Docker layer caching means `apt-get update` can serve stale package lists. Use `--no-cache` flag for CI builds, but cache for dev. The Dockerfile should combine `apt-get update && apt-get install` in a single `RUN` to avoid stale index layers.

## Open Risks

- **Kali package availability** — `kalilinux/kali-rolling` package repos may not always have the exact tool versions expected. nmap is stable, but httpx-toolkit / subfinder / nuclei (needed in S04) are Go binaries that Kali packages lag behind on. May need direct GitHub release downloads in Dockerfile for S04.
- **Docker Desktop vs Docker Engine** — Docker Desktop on macOS runs Linux containers in a VM. Networking behavior (especially DNS resolution, `host.docker.internal`) differs from native Linux Docker Engine. Integration tests must account for both environments.
- **Container startup time** — First exec after container start may be slow (~1-2s for init). If tests are time-sensitive, add a warmup exec or readiness check.
- **exec_run timeout enforcement** — No native timeout in docker-py's `exec_run`. The planned approach (`asyncio.wait_for` + `to_thread`) will timeout the Python-side wait, but the command keeps running inside the container. May need `exec_inspect` + process kill for full cleanup.
- **nmap privileged scanning** — SYN scans (`-sS`) require root inside the container (default) + NET_RAW capability. If the container runs as non-root (security hardening in future), nmap falls back to connect scans. For M001, running as root inside the container is acceptable.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Docker | `github/awesome-copilot@multi-stage-dockerfile` (7.4K installs) | available — useful for Dockerfile optimization |
| Docker | `sickn33/antigravity-awesome-skills@docker-expert` (5.8K installs) | available — general Docker best practices |
| Security/Pentest | `proffesor-for-testing/agentic-qe@pentest-validation` (46 installs) | available — low installs, niche |
| Security/Pentest | `duck4nh/antigravity-kit@pentest-expert` (39 installs) | available — low installs, niche |

No skills installed for this slice. The Docker skills have reasonable install counts and could help with Dockerfile best practices, but the scope here is narrow enough (one Dockerfile, one container manager) that they're not essential.

## Requirements Coverage

### Primary owner
- **R002 — Isolated Docker/Kali sandbox execution** — This slice directly implements the sandbox. Container lifecycle (create/exec/destroy), Kali-based image, NET_ADMIN/NET_RAW capabilities, no host filesystem exposure. The integration test proving nmap runs inside the container and returns results is the key verification.

### Supporting
- **R001 — Autonomous 5-phase pentesting pipeline** — S02 provides the execution substrate. Without a sandbox, the agent loop (S03) has nowhere to run tools. The tool executor + parser pattern established here becomes the template for all 5 tools.

## Key Design Decisions for Planning

1. **docker-py (sync) + asyncio.to_thread** over aiodocker — proven library, same pattern as Strix/PentAGI, simpler debugging
2. **One container per scan session** over container-per-exec — avoids 1-2s creation overhead per tool call, matches reference architectures
3. **nmap -oX - (XML to stdout)** over text parsing or python-nmap — deterministic schema, no extra dependencies, Pydantic-native
4. **stdlib xml.etree.ElementTree** over defusedxml — self-generated output = no XXE risk, zero new dependencies
5. **Kali-rolling base + selective install** over full Kali or minimal Alpine — Kali package manager handles security tool dependencies, reasonable image size
6. **Labels for orphan detection** — `oxpwn.managed=true` on every container for crash-safe cleanup
7. **Async context manager** (`async with DockerSandbox(...) as sandbox:`) — ensures cleanup even on exceptions

## Sources

- Docker SDK for Python API: container create/exec_run/remove lifecycle, cap_add parameter, demux, stream modes (source: Context7 /docker/docker-py, trust 9.9/10)
- Strix DockerRuntime: 338-line implementation with AbstractRuntime interface, NET_ADMIN/NET_RAW, health checks, FastAPI tool server (source: research.md landscape analysis)
- PentAGI sandbox: ephemeral containers from vxcontrol/kali-linux with 200+ CLI tools, dynamic port allocation (source: research.md)
- nmap XML output format: well-defined schema with host/port/service/script elements, `-oX -` flag for stdout output (source: nmap documentation)
- Docker daemon available: Docker Desktop v29.2.1 on macOS with bridge/host/none networks (source: local `docker info`)
