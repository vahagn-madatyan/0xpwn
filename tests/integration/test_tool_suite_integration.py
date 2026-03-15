"""Integration tests for the deterministic sandbox-local tool-suite proof assets and executors."""

from __future__ import annotations

import shlex

import pytest

from oxpwn.sandbox.docker import DockerSandbox
from oxpwn.sandbox.tools import FfufExecutor, HttpxExecutor, NucleiExecutor, SubfinderExecutor

pytestmark = pytest.mark.integration

_PUBLIC_SUBFINDER_DOMAIN = "hackerone.com"
_CONNECTIVITY_FAILURE_MARKERS = (
    "network is unreachable",
    "no such host",
    "temporary failure in name resolution",
    "dial tcp",
    "i/o timeout",
    "timed out",
    "tls handshake timeout",
    "connection refused",
)


def _tool_failure_details(result) -> str:
    return (
        f"command={result.command}\n"
        f"exit_code={result.exit_code}\n"
        f"stdout={result.stdout[:800]}\n"
        f"stderr={result.stderr[:800]}"
    )


def _looks_like_connectivity_failure(output: str) -> bool:
    lowered = output.lower()
    return any(marker in lowered for marker in _CONNECTIVITY_FAILURE_MARKERS)


async def _sandbox_can_reach_public_https(docker_sandbox: DockerSandbox) -> bool:
    script = (
        "python3 - <<'PY'\n"
        "import socket\n"
        "sock = socket.create_connection(('crt.sh', 443), timeout=5)\n"
        "sock.close()\n"
        "PY"
    )
    result = await docker_sandbox.execute(f"sh -lc {shlex.quote(script)}", timeout=15)
    return result.exit_code == 0


@pytest.mark.asyncio
async def test_tool_suite_assets_are_seeded_in_sandbox(
    docker_sandbox,
    sandbox_tool_suite_assets,
) -> None:
    """Fixture assets are copied into the running sandbox container."""
    result = await docker_sandbox.execute(
        "sh -lc "
        + shlex.quote(
            " && ".join(
                [
                    f"test -f {shlex.quote(f'{sandbox_tool_suite_assets.site_root}/index.html')}",
                    f"test -f {shlex.quote(f'{sandbox_tool_suite_assets.site_root}/admin/index.html')}",
                    f"test -f {shlex.quote(sandbox_tool_suite_assets.ffuf_wordlist)}",
                    f"test -f {shlex.quote(sandbox_tool_suite_assets.nuclei_template)}",
                ]
            )
        )
    )
    assert result.exit_code == 0, result.stderr or result.stdout


@pytest.mark.asyncio
async def test_sandbox_http_fixture_serves_admin_fixture(
    docker_sandbox,
    sandbox_http_fixture,
) -> None:
    """The sandbox-local Python HTTP server returns the deterministic /admin page."""
    result = await docker_sandbox.execute(
        "sh -lc "
        + shlex.quote(
            f"python3 - <<'PY'\n"
            f"import urllib.request\n"
            f"body = urllib.request.urlopen('{sandbox_http_fixture.base_url}/admin/', timeout=5).read().decode()\n"
            f"assert '0xpwn deterministic admin panel fixture' in body.lower()\n"
            f"PY"
        )
    )

    assert sandbox_http_fixture.port == 18080
    assert sandbox_http_fixture.startup_command.startswith("sh -lc ")
    assert sandbox_http_fixture.log_path.endswith("http-fixture.log")
    assert result.exit_code == 0, (
        f"stdout={result.stdout}\n"
        f"stderr={result.stderr}\n"
        f"startup_command={sandbox_http_fixture.startup_command}\n"
        f"log_path={sandbox_http_fixture.log_path}"
    )


@pytest.mark.asyncio
async def test_httpx_executor_real_http_fixture(
    docker_sandbox: DockerSandbox,
    sandbox_http_fixture,
) -> None:
    """httpx returns structured service metadata from the deterministic fixture."""
    executor = HttpxExecutor(docker_sandbox)
    result = await executor.run(
        targets=sandbox_http_fixture.base_url,
        path="/admin/",
        timeout_seconds=5,
    )

    assert result.tool_name == "httpx"
    assert result.exit_code == 0, _tool_failure_details(result)
    assert result.parsed_output is not None, _tool_failure_details(result)

    services = result.parsed_output["services"]
    assert result.parsed_output["count"] >= 1
    assert any(service["url"].endswith("/admin/") for service in services)
    assert any(service.get("status_code") == 200 for service in services)
    assert any(service.get("title") == "0xpwn Deterministic Admin Panel" for service in services)


@pytest.mark.asyncio
async def test_nuclei_executor_real_http_fixture(
    docker_sandbox: DockerSandbox,
    sandbox_http_fixture,
) -> None:
    """nuclei matches the deterministic in-repo template against the fixture."""
    executor = NucleiExecutor(docker_sandbox)
    result = await executor.run(
        targets=sandbox_http_fixture.base_url,
        templates=sandbox_http_fixture.assets.nuclei_template,
        timeout_seconds=5,
    )

    assert result.tool_name == "nuclei"
    assert result.exit_code == 0, _tool_failure_details(result)
    assert result.parsed_output is not None, _tool_failure_details(result)
    assert result.parsed_output["count"] == 1

    finding = result.parsed_output["findings"][0]
    assert finding["template_id"] == "deterministic-admin-panel"
    assert finding["severity"] == "info"
    assert finding["matched_at"].endswith("/admin/")


@pytest.mark.asyncio
async def test_ffuf_executor_real_http_fixture(
    docker_sandbox: DockerSandbox,
    sandbox_http_fixture,
) -> None:
    """ffuf finds the deterministic /admin/ path with the in-sandbox wordlist."""
    executor = FfufExecutor(docker_sandbox)
    result = await executor.run(
        url=f"{sandbox_http_fixture.base_url}/FUZZ/",
        wordlist_path=sandbox_http_fixture.assets.ffuf_wordlist,
        match_status="200",
        timeout_seconds=5,
    )

    assert result.tool_name == "ffuf"
    assert result.exit_code == 0, _tool_failure_details(result)
    assert result.parsed_output is not None, _tool_failure_details(result)
    assert result.parsed_output["count"] == 1

    finding = result.parsed_output["findings"][0]
    assert finding["status"] == 200
    assert finding["url"].endswith("/admin/")
    assert finding["inputs"]["FUZZ"] == "admin"


@pytest.mark.asyncio
async def test_subfinder_executor_public_domain_or_skip(
    docker_sandbox: DockerSandbox,
) -> None:
    """subfinder proves real public-domain execution or skips cleanly when egress is unavailable."""
    if not await _sandbox_can_reach_public_https(docker_sandbox):
        pytest.skip("Sandbox cannot reach crt.sh:443, so the public-domain subfinder proof is skipped")

    executor = SubfinderExecutor(docker_sandbox)
    result = await executor.run(
        domains=_PUBLIC_SUBFINDER_DOMAIN,
        timeout_seconds=10,
        max_time_minutes=1,
    )

    combined_output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    if (result.exit_code != 0 or result.parsed_output is None) and _looks_like_connectivity_failure(combined_output):
        pytest.skip(
            "Subfinder could not reach passive sources from inside the sandbox: "
            f"{combined_output[:400]}"
        )

    assert result.tool_name == "subfinder"
    assert result.exit_code == 0, _tool_failure_details(result)
    assert result.parsed_output is not None, _tool_failure_details(result)
    assert result.parsed_output["count"] == len(result.parsed_output["hosts"])
    assert all(
        host["host"] == _PUBLIC_SUBFINDER_DOMAIN or host["host"].endswith(f".{_PUBLIC_SUBFINDER_DOMAIN}")
        for host in result.parsed_output["hosts"]
    )
