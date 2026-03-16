"""End-to-end integration test — full 5-phase pipeline against OWASP Juice Shop.

Proves the complete ``_scan_async()`` pipeline end-to-end with a real LLM,
real Docker sandbox, and a real target (Juice Shop).

Run with:
    pytest tests/integration/test_e2e_juiceshop.py -m integration -v --timeout=600

Prerequisites:
    - Docker daemon reachable
    - ``bkimminich/juice-shop:latest`` pullable (auto-pulled by fixture)
    - At least one LLM API key exported (GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY)
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Skip helpers — inline availability checks without pulling session fixtures
# ---------------------------------------------------------------------------

_LLM_KEY_ENV_VARS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY")


def _docker_available() -> bool:
    """Return True if Docker daemon is reachable."""
    try:
        import docker as docker_lib

        client = docker_lib.from_env()
        client.ping()
        return True
    except Exception:  # noqa: BLE001
        return False


def _llm_key_available() -> bool:
    """Return True if at least one LLM API key is exported."""
    return any(os.environ.get(k) for k in _LLM_KEY_ENV_VARS)


def _test_model() -> str:
    return os.environ.get("OXPWN_TEST_MODEL", "gemini/gemini-2.5-flash")


_skip_no_docker = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker daemon not reachable — skipping E2E integration tests",
)
_skip_no_llm = pytest.mark.skipif(
    not _llm_key_available(),
    reason="No LLM API key set — skipping E2E integration tests",
)


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


@_skip_no_docker
@_skip_no_llm
@pytest.mark.timeout(600)
@pytest.mark.asyncio
async def test_full_scan_pipeline(juice_shop: str) -> None:
    """Full 5-phase scan against OWASP Juice Shop via ``_scan_async()``.

    Structural assertions (not exact LLM wording):
      a) ``phases_completed`` has at least 3 entries (recon + scanning + more)
      b) ``tool_results`` is non-empty (agent executed at least one tool)
      c) ``findings`` attribute exists (list, may be empty)
      d) Scan completes without raising an exception
      e) ``total_tokens > 0`` (LLM was actually used)
    """
    from oxpwn.cli.main import ScanRuntimeConfig, _scan_async

    config = ScanRuntimeConfig(
        target=juice_shop,
        model=_test_model(),
        max_iterations_per_phase=5,
    )

    # (d) Scan completes without exception — if _scan_async raises, test fails
    final_state = await _scan_async(config)

    # (a) At least 3 phases completed (recon + scanning + at least one more)
    assert len(final_state.phases_completed) >= 3, (
        f"Expected ≥3 phases completed, got {len(final_state.phases_completed)}: "
        f"{[p.value for p in final_state.phases_completed]}"
    )

    # (b) Agent executed at least one tool
    assert len(final_state.tool_results) > 0, (
        "Expected at least one tool result — agent didn't execute any tools"
    )

    # (c) findings attribute exists and is a list (may be empty if LLM
    #     didn't find CVE-bearing vulns — that's OK for structural test)
    assert isinstance(final_state.findings, list), (
        f"Expected findings to be a list, got {type(final_state.findings)}"
    )

    # (e) LLM was used (tokens consumed)
    assert final_state.total_tokens > 0, (
        "Expected total_tokens > 0 — LLM was not used"
    )
