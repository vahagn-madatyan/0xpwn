# S08: End-to-End Validation — Research

**Date:** 2026-03-15

## Summary

S08 is the final integration slice for M001. It must prove that `0xpwn scan --target <url>` runs all 5 phases against OWASP Juice Shop, finds real vulnerabilities with PoC evidence, streams reasoning in real-time, and produces enriched findings with CVE/CVSS/CWE data. Research uncovered five critical integration gaps that must be closed before end-to-end validation can pass:

1. **Agent only runs 2 of 5 phases** — `_PHASE_ORDER` in `react.py` is hardcoded to `[Phase.recon, Phase.scanning]`. The exploitation, validation, and reporting phases are defined in the `Phase` enum but never executed.
2. **Enrichment is completely unwired** — `enrich_findings()` and `findings_from_tool_results()` exist in `src/oxpwn/enrichment/` but are never called from the agent loop or CLI. The agent accumulates `ToolResult` objects but never converts them to `Finding` objects or enriches them.
3. **No phase guidance prompts** for exploitation, validation, or reporting — `_PHASE_GUIDANCE` in `prompts.py` only covers recon and scanning; the other 3 phases fall through to a generic default.
4. **Docker networking gap** — the sandbox container cannot reach `localhost:3000` (Juice Shop on host) without `extra_hosts` or `host` network mode. `host.docker.internal` resolves on Docker Desktop but isn't configured in `DockerSandbox.create()`.
5. **No Juice Shop test infrastructure** — no docker-compose, fixture, or test helper exists for starting/stopping Juice Shop as a target.

The primary recommendation is to treat S08 as a wiring + validation slice: close the 5 integration gaps with minimal code changes, then prove the system end-to-end with both automated integration tests and a documented manual acceptance run.

## Recommendation

Close integration gaps in this order, then validate:

1. **Expand `_PHASE_ORDER`** to all 5 phases and add phase guidance prompts for exploitation, validation, and reporting. This is a ~20-line change in `react.py` and `prompts.py`.
2. **Wire enrichment into `_scan_async()`** in `main.py` — after `agent.run()` returns, call `findings_from_tool_results()` on the final state's tool_results, then `enrich_findings()` with an `NvdClient` and `CveCache`, and add the resulting findings to `scan_state`. This keeps enrichment out of the hot loop and runs once at the end.
3. **Fix Docker networking** — use `extra_hosts={"host.docker.internal": "host-gateway"}` in container creation so the sandbox can always reach the host, regardless of platform. The agent's target URL will use `host.docker.internal:3000` to reach Juice Shop.
4. **Write integration tests** that start Juice Shop in Docker, run a full scan, and assert structural properties of the output (phases completed, findings present, enrichment fields populated). Use generous timeouts and structural assertions (not exact LLM output).
5. **Document manual acceptance** checklist for human verification of streaming quality, finding accuracy, and UX.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CVE enrichment | `oxpwn.enrichment.enrich_findings()` + `findings_from_tool_results()` | Fully built and tested in S07 with 60 unit tests; just needs wiring |
| Juice Shop target | `bkimminich/juice-shop` Docker image | Official OWASP image, well-known vulns, used by every pentesting tool for testing |
| Container networking | Docker `extra_hosts` with `host-gateway` | Docker's built-in host resolution; no custom networking code needed |
| Streaming CLI rendering | `RichStreamingCallback` from S05 | Already handles all 5 phase labels and styles; just needs the agent to reach those phases |

## Existing Code and Patterns

- `src/oxpwn/agent/react.py:30` — `_PHASE_ORDER = [Phase.recon, Phase.scanning]` — **must expand** to include exploitation, validation, reporting
- `src/oxpwn/agent/prompts.py:84-102` — `_PHASE_GUIDANCE` dict only has recon/scanning entries — **must add** exploitation, validation, reporting guidance
- `src/oxpwn/cli/main.py:249-327` — `_scan_async()` is the composition point where enrichment should be wired in, between `agent.run()` return and `render_final_summary()`
- `src/oxpwn/enrichment/enrichment.py:165-190` — `findings_from_tool_results()` dispatches to nuclei/ffuf/nmap converters — ready to consume tool_results from agent
- `src/oxpwn/enrichment/enrichment.py:198-297` — `enrich_findings()` is async, takes findings + NvdClient + CveCache — ready for await
- `src/oxpwn/sandbox/docker.py:77-110` — `create()` passes `network_mode` but no `extra_hosts` — needs `extra_hosts` param for host resolution
- `src/oxpwn/cli/streaming.py:28-43` — `_PHASE_LABELS` and `_PHASE_STYLES` already have entries for all 5 phases — no streaming changes needed
- `tests/integration/test_cli_integration.py` — pattern for CLI integration tests with Docker/LLM skip gating — follow for S08 tests
- `tests/conftest.py:266-299` — session-scoped `docker_sandbox` fixture pattern — extend for Juice Shop lifecycle

## Constraints

- **`_PHASE_ORDER` is the sole phase gate** — the agent loop is structurally sound for N phases; expanding the list is the only change needed in the loop itself
- **Agent never calls `add_finding()`** — findings are currently only created by tests. The enrichment module's `findings_from_tool_results()` creates Finding objects, but this must be called explicitly after the agent finishes
- **NVD API rate limit** — free tier is 5 requests per 30 seconds. Scans finding many CVEs will be slow. The `NvdClient` already implements rate limiting; `CveCache` avoids redundant lookups. Acceptable for M001.
- **Juice Shop must be running on host** — integration tests need `bkimminich/juice-shop:latest` running on port 3000. Tests should start/stop it in a session fixture or skip cleanly.
- **Docker Desktop on macOS** — `host.docker.internal` resolves natively. On Linux, `extra_hosts={"host.docker.internal": "host-gateway"}` is required. The `extra_hosts` approach works on both.
- **LLM quality variance** — the agent's ability to find real vulns depends on the LLM. Integration tests must use structural assertions (e.g., "at least N tool_results", "phases_completed includes exploitation") not semantic ones ("found SQL injection").
- **Integration test timeout** — a full 5-phase scan can take 3-10 minutes depending on LLM speed and tool execution. Tests need 600s+ timeouts.
- **Exploitation phase has no dedicated tools** — the current 5-tool suite is recon/scanning focused. For M001, the exploitation phase will rely on the LLM reasoning about scan findings and potentially using nmap scripts or nuclei templates for targeted exploitation validation. Full exploitation tooling (sqlmap, etc.) is M004 scope.

## Common Pitfalls

- **Juice Shop port conflict** — if port 3000 is in use, Juice Shop won't start. Use a configurable port or skip the test with a clear message.
- **LLM loops in exploitation phase** — without dedicated exploitation tools, the LLM may loop calling the same scanning tools repeatedly. Phase guidance must be clear: "summarize findings and move on if no exploitation tools are available."
- **NVD API downtime** — NVD has documented outages. Enrichment must degrade gracefully (unenriched findings are acceptable, not a test failure). Integration test should assert enrichment was attempted, not that it succeeded.
- **Stale Docker image** — if `oxpwn-sandbox:dev` is outdated, tool binaries may be missing. The conftest already handles this with build-if-missing, but Juice Shop image needs the same treatment.
- **Container target address** — the agent sees `host.docker.internal:3000` as the target, not `localhost:3000`. The scan state target must use this address so tools inside the sandbox can reach Juice Shop.
- **Bridge network DNS** — on Docker bridge networks, `host.docker.internal` requires the `extra_hosts` mapping to work. Without it, DNS resolution fails silently and all tools produce empty results.

## Open Risks

- **Agent may not find real vulns** — the LLM may not craft effective nuclei templates or nmap scripts to detect Juice Shop's known vulnerabilities (XSS, SQLi, information disclosure). This is an LLM quality risk, not a code bug. Mitigation: the integration test asserts tool execution happened and phases completed, not specific vulnerability classes. The manual acceptance step validates finding quality.
- **Exploitation phase may be hollow** — with only 5 recon/scanning tools, the "exploitation" phase may just produce a summary of scanning findings rather than actual exploitation attempts. This is acceptable for M001 and explicitly called out in the roadmap (full exploitation tooling is M004/S07).
- **NVD enrichment may be empty** — if tools don't find CVE-bearing vulnerabilities, enrichment has nothing to enrich. The pipeline runs but produces no CVSS/CWE data. Integration test should assert the pipeline ran, not specific enrichment results.
- **Test flakiness from LLM non-determinism** — the same scan may find different things on different runs. Use generous assertions and allow for variance.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Docker testing | `peteonrails/voxtype@docker-test` | available (21 installs) — not needed, existing patterns sufficient |
| OWASP testing | `manastalukdar/claude-devstudio@owasp-check` | available (4 installs) — too low relevance |
| Pentesting | None with high install count | none found |

No skills installed — existing codebase patterns and S01-S07 summaries provide sufficient guidance.

## Sources

- Agent loop limited to 2 phases (source: `src/oxpwn/agent/react.py:30` — `_PHASE_ORDER = [Phase.recon, Phase.scanning]`)
- Enrichment module completely unwired from agent/CLI (source: `grep -rn` across `src/oxpwn/cli/` and `src/oxpwn/agent/` returns zero hits for enrichment imports)
- Phase guidance only covers recon/scanning (source: `src/oxpwn/agent/prompts.py:84-102` — `_PHASE_GUIDANCE` dict)
- Docker `host.docker.internal` resolves on this macOS Docker Desktop (source: `docker run --rm alpine ping -c 1 host.docker.internal` — verified live)
- `extra_hosts` with `host-gateway` works cross-platform (source: Docker documentation for `--add-host` flag)
- Streaming callback already handles all 5 phases (source: `src/oxpwn/cli/streaming.py:28-43` — all phase labels/styles defined)
- 252 unit tests passing (source: `pytest tests/unit/ -x -q` — run during research)
