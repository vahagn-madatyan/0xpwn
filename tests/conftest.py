"""Shared pytest fixtures and configuration for 0xpwn tests."""

from __future__ import annotations

import asyncio
import io
import os
import shlex
import tarfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

from oxpwn.core.models import (
    Finding,
    Phase,
    ScanState,
    Severity,
    TokenUsage,
    ToolResult,
)


@pytest.fixture()
def sample_finding() -> Finding:
    """A representative security finding for tests."""
    return Finding(
        title="SQL Injection in login",
        severity=Severity.critical,
        description="The login endpoint is vulnerable to SQL injection via the username parameter.",
        url="https://example.com/login",
        evidence="' OR 1=1 --",
        cve_id="CVE-2024-1234",
        cvss=9.8,
        cwe_id="CWE-89",
        remediation="Use parameterized queries.",
        tool_name="sqlmap",
    )


@pytest.fixture()
def sample_tool_result() -> ToolResult:
    """A representative tool execution result for tests."""
    return ToolResult(
        tool_name="nmap",
        command="nmap -sV -p 80,443 example.com",
        stdout="PORT   STATE SERVICE VERSION\n80/tcp open  http    nginx 1.24\n443/tcp open  ssl/http nginx 1.24",
        stderr="",
        exit_code=0,
        duration_ms=5200,
        timestamp=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture()
def sample_token_usage() -> TokenUsage:
    """A representative token usage breakdown."""
    return TokenUsage(input=150, output=80, total=230)


@pytest.fixture()
def scan_state_factory():
    """Factory for creating ScanState instances with sensible defaults."""

    def _create(
        target: str = "https://example.com",
        current_phase: Phase = Phase.recon,
        **kwargs,
    ) -> ScanState:
        return ScanState(target=target, current_phase=current_phase, **kwargs)

    return _create


# ---------------------------------------------------------------------------
# Docker sandbox session fixture (integration tests)
# ---------------------------------------------------------------------------

_SANDBOX_IMAGE = "oxpwn-sandbox:dev"
_TOOL_SUITE_FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures" / "tool_suite"
_TOOL_SUITE_CONTAINER_ROOT = "/tmp/oxpwn-tool-suite"
_TOOL_SUITE_HTTP_PORT = 18080


@dataclass(frozen=True)
class ToolSuiteFixtureAssets:
    """Host-side deterministic assets for tool-suite integration tests."""

    host_root: Path
    site_root: Path
    ffuf_wordlist: Path
    nuclei_template: Path


@dataclass(frozen=True)
class SandboxToolSuiteAssets:
    """Container paths for deterministic tool-suite assets copied into Docker."""

    container_root: str
    site_root: str
    ffuf_wordlist: str
    nuclei_template: str


@dataclass(frozen=True)
class SandboxHttpFixture:
    """Running in-sandbox HTTP fixture details for integration proofs."""

    assets: SandboxToolSuiteAssets
    port: int
    base_url: str
    startup_command: str
    log_path: str
    pid_path: str
    pid: int


async def _exec_or_raise(
    sandbox,
    command: str,
    *,
    timeout: int = 30,
    detail: str,
) -> ToolResult:
    """Run a sandbox command and raise a debuggable error on non-zero exit."""
    result = await sandbox.execute(command, timeout=timeout)
    if result.exit_code == 0:
        return result

    stdout_head = result.stdout.strip()[:400]
    stderr_head = result.stderr.strip()[:400]
    raise RuntimeError(
        f"{detail} failed (exit_code={result.exit_code})\n"
        f"command: {command}\n"
        f"stdout: {stdout_head}\n"
        f"stderr: {stderr_head}"
    )


def _build_tool_suite_archive(source_dir: Path) -> bytes:
    """Create a tar archive for Docker put_archive from a fixture directory."""
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w") as tar:
        for path in sorted(source_dir.rglob("*")):
            tar.add(path, arcname=str(path.relative_to(source_dir)))
    archive.seek(0)
    return archive.getvalue()


async def _copy_tool_suite_assets_to_sandbox(sandbox, source_dir: Path, container_root: str) -> None:
    """Copy the deterministic tool-suite fixture tree into the sandbox container."""
    await _exec_or_raise(
        sandbox,
        f"sh -lc {shlex.quote(f'rm -rf {shlex.quote(container_root)} && mkdir -p {shlex.quote(container_root)}')}",
        detail="prepare tool suite fixture directory",
    )

    archive = _build_tool_suite_archive(source_dir)

    def _put_archive() -> None:
        assert sandbox._container is not None  # noqa: S101
        ok = sandbox._container.put_archive(container_root, archive)
        if not ok:
            raise RuntimeError(f"Docker put_archive returned false for {container_root}")

    await asyncio.to_thread(_put_archive)


async def _stop_sandbox_http_fixture(sandbox, pid_path: str) -> None:
    """Best-effort stop for the background python http.server process."""
    stop_script = f"""
set +e
if [ -f {shlex.quote(pid_path)} ]; then
  pid=$(cat {shlex.quote(pid_path)})
  if [ -n "$pid" ]; then
    kill "$pid" 2>/dev/null || true
    for _ in 1 2 3 4 5; do
      if ! kill -0 "$pid" 2>/dev/null; then
        break
      fi
      sleep 0.2
    done
    kill -9 "$pid" 2>/dev/null || true
  fi
  rm -f {shlex.quote(pid_path)}
fi
exit 0
""".strip()
    await sandbox.execute(f"sh -lc {shlex.quote(stop_script)}", timeout=10)


async def _start_sandbox_http_fixture(
    sandbox,
    assets: SandboxToolSuiteAssets,
    *,
    port: int,
) -> SandboxHttpFixture:
    """Start a deterministic HTTP server inside the sandbox and verify readiness."""
    log_path = f"{assets.container_root}/http-fixture.log"
    pid_path = f"{assets.container_root}/http-fixture.pid"
    await _stop_sandbox_http_fixture(sandbox, pid_path)

    startup_script = f"""
set -eu
cd {shlex.quote(assets.site_root)}
: > {shlex.quote(log_path)}
rm -f {shlex.quote(pid_path)}
python3 -m http.server {port} > {shlex.quote(log_path)} 2>&1 &
pid=$!
echo "$pid" > {shlex.quote(pid_path)}
attempt=0
until python3 - <<'PY'
import sys
import urllib.request
body = urllib.request.urlopen("http://127.0.0.1:{port}/admin/", timeout=1).read().decode()
sys.exit(0 if "0xpwn deterministic admin panel fixture" in body.lower() else 1)
PY
do
  attempt=$((attempt+1))
  if [ "$attempt" -ge 20 ]; then
    exit 1
  fi
  sleep 0.25
done
""".strip()
    startup_command = f"sh -lc {shlex.quote(startup_script)}"
    startup_result = await sandbox.execute(startup_command, timeout=30)
    if startup_result.exit_code != 0:
        log_result = await sandbox.execute(
            "sh -lc "
            + shlex.quote(
                f"if [ -f {shlex.quote(log_path)} ]; then tail -n 50 {shlex.quote(log_path)}; "
                f"else echo '(missing fixture log: {log_path})'; fi"
            ),
            timeout=10,
        )
        raise RuntimeError(
            "sandbox HTTP fixture failed to start\n"
            f"port: {port}\n"
            f"command: {startup_command}\n"
            f"log_path: {log_path}\n"
            f"stdout: {startup_result.stdout.strip()[:400]}\n"
            f"stderr: {startup_result.stderr.strip()[:400]}\n"
            f"log_tail: {log_result.stdout.strip()[:600]}"
        )

    pid_result = await _exec_or_raise(
        sandbox,
        f"sh -lc 'cat {shlex.quote(pid_path)}'",
        detail="read sandbox HTTP fixture pid",
    )

    return SandboxHttpFixture(
        assets=assets,
        port=port,
        base_url=f"http://127.0.0.1:{port}",
        startup_command=startup_command,
        log_path=log_path,
        pid_path=pid_path,
        pid=int(pid_result.stdout.strip()),
    )


@pytest.fixture(scope="session")
def docker_sandbox(tmp_path_factory):
    """Provide a running :class:`DockerSandbox` for integration tests.

    * Builds the image idempotently (skips if already present).
    * Skips the entire test session if Docker is unreachable.
    * Creates the container once, yields it, destroys on teardown.
    """
    import docker as docker_lib

    try:
        client = docker_lib.from_env()
        client.ping()
    except Exception:  # noqa: BLE001
        pytest.skip("Docker daemon not reachable — skipping integration tests")

    # Build image if missing
    try:
        client.images.get(_SANDBOX_IMAGE)
    except docker_lib.errors.ImageNotFound:
        dockerfile_dir = Path(__file__).resolve().parent.parent / "docker"
        client.images.build(path=str(dockerfile_dir), tag=_SANDBOX_IMAGE, rm=True)

    # Create sandbox via asyncio
    from oxpwn.sandbox.docker import DockerSandbox

    sandbox = DockerSandbox(_SANDBOX_IMAGE, scan_id="integration-test")
    loop = asyncio.new_event_loop()
    loop.run_until_complete(sandbox.create())

    yield sandbox

    loop.run_until_complete(sandbox.destroy())
    loop.close()


@pytest.fixture(scope="session")
def tool_suite_fixture_assets() -> ToolSuiteFixtureAssets:
    """Return host-side paths for deterministic tool-suite proof assets."""
    assets = ToolSuiteFixtureAssets(
        host_root=_TOOL_SUITE_FIXTURES_ROOT,
        site_root=_TOOL_SUITE_FIXTURES_ROOT / "site",
        ffuf_wordlist=_TOOL_SUITE_FIXTURES_ROOT / "ffuf-wordlist.txt",
        nuclei_template=_TOOL_SUITE_FIXTURES_ROOT / "nuclei" / "admin-panel.yaml",
    )
    missing = [str(path) for path in assets.__dict__.values() if not Path(path).exists()]
    if missing:
        raise RuntimeError(f"Missing tool suite fixture assets: {missing}")
    return assets


@pytest.fixture()
async def sandbox_tool_suite_assets(
    docker_sandbox,
    tool_suite_fixture_assets: ToolSuiteFixtureAssets,
) -> SandboxToolSuiteAssets:
    """Copy deterministic tool-suite assets into the Docker sandbox."""
    await _copy_tool_suite_assets_to_sandbox(
        docker_sandbox,
        tool_suite_fixture_assets.host_root,
        _TOOL_SUITE_CONTAINER_ROOT,
    )
    assets = SandboxToolSuiteAssets(
        container_root=_TOOL_SUITE_CONTAINER_ROOT,
        site_root=f"{_TOOL_SUITE_CONTAINER_ROOT}/site",
        ffuf_wordlist=f"{_TOOL_SUITE_CONTAINER_ROOT}/ffuf-wordlist.txt",
        nuclei_template=f"{_TOOL_SUITE_CONTAINER_ROOT}/nuclei/admin-panel.yaml",
    )
    await _exec_or_raise(
        docker_sandbox,
        "sh -lc "
        + shlex.quote(
            " && ".join(
                [
                    f"test -f {shlex.quote(f'{assets.site_root}/index.html')}",
                    f"test -f {shlex.quote(f'{assets.site_root}/admin/index.html')}",
                    f"test -f {shlex.quote(assets.ffuf_wordlist)}",
                    f"test -f {shlex.quote(assets.nuclei_template)}",
                ]
            )
        ),
        detail="verify copied tool suite assets",
    )
    return assets


@pytest.fixture()
async def sandbox_http_fixture(
    docker_sandbox,
    sandbox_tool_suite_assets: SandboxToolSuiteAssets,
) -> SandboxHttpFixture:
    """Run the deterministic HTTP fixture inside the Docker sandbox."""
    fixture = await _start_sandbox_http_fixture(
        docker_sandbox,
        sandbox_tool_suite_assets,
        port=_TOOL_SUITE_HTTP_PORT,
    )
    try:
        yield fixture
    finally:
        await _stop_sandbox_http_fixture(docker_sandbox, fixture.pid_path)


# ---------------------------------------------------------------------------
# LLM client fixture (integration tests)
# ---------------------------------------------------------------------------

_LLM_KEY_ENV_VARS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY")


@pytest.fixture(scope="session")
def llm_client():
    """Provide an :class:`LLMClient` for integration tests.

    Uses ``OXPWN_TEST_MODEL`` or defaults to ``gemini/gemini-2.5-flash``.
    Skips if no API key is found in the environment.
    """
    if not any(os.environ.get(k) for k in _LLM_KEY_ENV_VARS):
        pytest.skip("No LLM API key set — skipping LLM integration tests")

    from oxpwn.llm.client import LLMClient

    model = os.environ.get("OXPWN_TEST_MODEL", "gemini/gemini-2.5-flash")
    return LLMClient(model)


# ---------------------------------------------------------------------------
# ReactAgent fixture (integration tests — requires both LLM + Docker)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def react_agent(llm_client, docker_sandbox):
    """Provide a :class:`ReactAgent` with real LLM + Docker sandbox.

    Registers the default nmap tool.  Skips if either Docker or LLM
    credentials are unavailable (inherited from fixture dependencies).
    """
    from oxpwn.agent.react import ReactAgent
    from oxpwn.agent.tools import ToolRegistry, register_default_tools

    registry = ToolRegistry()
    register_default_tools(registry)
    return ReactAgent(llm_client, docker_sandbox, registry, max_iterations_per_phase=5)
