---
id: T01
parent: S04
milestone: M001
provides:
  - Deterministic sandbox-local HTTP proof infrastructure for the S04 tool suite
  - A sandbox image contract that includes the core binaries plus a working Python HTTP runtime
key_files:
  - docker/Dockerfile
  - tests/conftest.py
  - tests/integration/test_tool_suite_integration.py
  - tests/fixtures/tool_suite/site/admin/index.html
  - tests/fixtures/tool_suite/nuclei/admin-panel.yaml
key_decisions:
  - Install full `python3` alongside `python3-minimal` because Kali's minimal package could not run the `http.server`/`urllib` proof.
  - Standardize copied proof assets under `/tmp/oxpwn-tool-suite` and serve the deterministic site on port `18080`.
patterns_established:
  - Seed deterministic fixture trees into a live `DockerSandbox` with Docker `put_archive` instead of host-side execution paths.
  - Start background proof services via `sh -lc`, then return a typed handle exposing `port`, `startup_command`, `log_path`, and `pid_path` for teardown/debugging.
observability_surfaces:
  - `SandboxHttpFixture.port`, `SandboxHttpFixture.startup_command`, `SandboxHttpFixture.log_path`, `SandboxHttpFixture.pid_path`
  - `tests/fixtures/tool_suite/` proof assets
  - Immediate missing-binary feedback from the sandbox image verification command
duration: 55m
verification_result: passed
completed_at: 2026-03-15T03:06:14Z
blocker_discovered: false
---

# T01: Expand the sandbox image and deterministic HTTP proof fixtures

**Expanded the sandbox image, added deterministic HTTP proof assets, and taught the test harness to seed and serve those assets entirely inside Docker.**

## What Happened

I updated `docker/Dockerfile` so the dev sandbox now installs `httpx-toolkit`, `subfinder`, `nuclei`, `ffuf`, `nmap`, `python3-minimal`, and a stable `httpx` symlink. During verification I found that Kali's `python3-minimal` alone could not import the stdlib `http` package, which caused `python3 -m http.server` and `urllib.request` to fail inside the container, so I added full `python3` alongside the minimal package and reran the proof successfully.

I added deterministic proof assets under `tests/fixtures/tool_suite/`: a tiny site root, a uniquely identifiable `/admin/` page, a tiny ffuf wordlist, and a custom nuclei template that matches only the fixture page. These are fully in-repo and avoid any dependence on third-party HTTP targets.

I extended `tests/conftest.py` with typed tool-suite helpers that:
- locate the host-side proof assets,
- copy them into the live sandbox container at `/tmp/oxpwn-tool-suite`,
- start `python3 -m http.server` via `sh -lc` on port `18080`,
- verify readiness from inside the sandbox,
- expose `port`, `startup_command`, `log_path`, and PID metadata for teardown/debugging.

I added `tests/integration/test_tool_suite_integration.py` to prove the new fixture path works through the real pytest sandbox fixture, and I added a module-level `test_nmap_executor_real_scan` alias in `tests/integration/test_sandbox_integration.py` so the slice verification command now resolves the expected node id.

Because this is the first task in the slice, I also created the missing parser test files for `httpx`, `subfinder`, `nuclei`, and `ffuf` as initial module-existence scaffolds. They intentionally fail until T02/T03 land, which keeps slice-level verification failures focused on missing implementation instead of missing files.

## Verification

Task-level/runtime verification passed:
- `docker build -t oxpwn-sandbox:dev docker/`
- `docker run --rm oxpwn-sandbox:dev sh -lc 'for bin in nmap httpx subfinder nuclei ffuf python3; do command -v "$bin"; done'`
  - Resolved: `nmap`, `httpx`, `subfinder`, `nuclei`, `ffuf`, `python3`
- `docker run --rm -v "$PWD/tests/fixtures/tool_suite/site:/srv/site:ro" oxpwn-sandbox:dev sh -lc 'cd /srv/site && python3 -m http.server 8000 >/tmp/http.log 2>&1 & pid=$!; ... urllib.request.urlopen("http://127.0.0.1:8000/admin/") ...'`
  - Passed after adding full `python3`
- `pytest tests/integration/test_tool_suite_integration.py -m integration -v`
  - `2 passed`

Slice-level verification status after T01:
- `pytest tests/integration/test_sandbox_integration.py::test_nmap_executor_real_scan tests/integration/test_tool_suite_integration.py -m integration -v`
  - `3 passed`
- `pytest tests/unit/test_httpx_parser.py tests/unit/test_subfinder_parser.py tests/unit/test_nuclei_parser.py tests/unit/test_ffuf_parser.py tests/unit/test_tool_registry.py tests/unit/test_react_agent.py -v`
  - Existing `test_tool_registry.py` and `test_react_agent.py` coverage passed.
  - The four new parser scaffold files failed exactly as intended because `oxpwn.sandbox.tools.httpx`, `subfinder`, `nuclei`, and `ffuf` do not exist yet. This is expected until T02/T03.

## Diagnostics

Future agents can inspect this substrate with:
- `docker build -t oxpwn-sandbox:dev docker/ && docker run --rm oxpwn-sandbox:dev sh -lc 'for bin in nmap httpx subfinder nuclei ffuf python3; do command -v "$bin"; done'`
- `pytest tests/integration/test_tool_suite_integration.py -m integration -v`

When the in-sandbox HTTP fixture fails, inspect the `SandboxHttpFixture` values from `tests/conftest.py`:
- `port`
- `startup_command`
- `log_path`
- `pid_path`

The sandbox helper writes its server log to `/tmp/oxpwn-tool-suite/http-fixture.log` inside the container, and startup failures surface with the command, log path, and log tail in the raised error.

## Deviations

- The written task plan said to add `python3-minimal`; in practice that package alone was insufficient for the required `http.server` + `urllib` proof on Kali, so I installed full `python3` alongside it.
- I added a module-level `test_nmap_executor_real_scan` alias and initial parser scaffold test files so the slice verification commands now resolve cleanly and fail for implementation reasons rather than missing files.

## Known Issues

- `src/oxpwn/sandbox/tools/httpx.py`, `subfinder.py`, `nuclei.py`, and `ffuf.py` are still unimplemented, so the slice-level unit verification command remains red on the four scaffold tests until T02/T03.
- The exact plan command `sh -lc 'command -v nmap httpx subfinder nuclei ffuf python3'` is not a reliable per-binary display on this shell, so I used an explicit loop to verify all six paths.

## Files Created/Modified

- `docker/Dockerfile` — installs the full tool/runtime set and creates the stable `httpx` symlink.
- `tests/conftest.py` — adds typed asset-copy and in-sandbox HTTP fixture helpers with observable startup metadata.
- `tests/fixtures/tool_suite/site/index.html` — deterministic site root for sandbox-local HTTP proofs.
- `tests/fixtures/tool_suite/site/admin/index.html` — uniquely identifiable admin page for `httpx`/`nuclei`/`ffuf` proofs.
- `tests/fixtures/tool_suite/ffuf-wordlist.txt` — tiny wordlist that can discover `/admin`.
- `tests/fixtures/tool_suite/nuclei/admin-panel.yaml` — custom nuclei template for deterministic local matching.
- `tests/integration/test_tool_suite_integration.py` — real Docker tests for asset seeding and sandbox-local HTTP serving.
- `tests/integration/test_sandbox_integration.py` — adds the slice verification node id expected by the plan.
- `tests/unit/test_httpx_parser.py` — initial T02 scaffold test.
- `tests/unit/test_subfinder_parser.py` — initial T02 scaffold test.
- `tests/unit/test_nuclei_parser.py` — initial T03 scaffold test.
- `tests/unit/test_ffuf_parser.py` — initial T03 scaffold test.
- `.gsd/DECISIONS.md` — records the deterministic HTTP fixture runtime contract.
- `.gsd/milestones/M001/slices/S04/S04-PLAN.md` — marks T01 complete.
- `.gsd/STATE.md` — advances the slice state to T02.
