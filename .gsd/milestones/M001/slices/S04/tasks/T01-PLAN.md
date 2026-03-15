---
estimated_steps: 4
estimated_files: 6
---

# T01: Expand the sandbox image and deterministic HTTP proof fixtures

**Slice:** S04 — Tool Suite Integration
**Milestone:** M001

## Description

Build the shared runtime substrate for the whole slice before touching any parser code. The new tools are only worth integrating if the sandbox actually contains their binaries and the integration tests have a deterministic HTTP target they can hit without depending on third-party sites. This task makes the image and proof assets stable so later failures are about parser logic, not environment drift.

## Steps

1. Update `docker/Dockerfile` to install `httpx-toolkit`, `subfinder`, `nuclei`, `ffuf`, and `python3-minimal` alongside the existing `nmap` install, then create a stable `httpx` symlink that points at the packaged `httpx-toolkit` binary.
2. Add deterministic proof assets under `tests/fixtures/tool_suite/`: a tiny site fixture with a uniquely identifiable `/admin` page, a tiny ffuf wordlist that can discover that path, and a custom nuclei template that matches the fixture without needing upstream template downloads.
3. Extend `tests/conftest.py` with helper fixtures/utilities that copy the proof assets into the sandbox and launch `python3 -m http.server` via `sh -lc` on a known port, returning enough state for tests to cleanly stop the server and debug startup failures.
4. Verify the image/runtime contract by rebuilding `oxpwn-sandbox:dev` and checking that all required binaries are present before any tool-executor work begins.

## Must-Haves

- [ ] `oxpwn-sandbox:dev` contains `nmap`, `httpx`, `subfinder`, `nuclei`, `ffuf`, and `python3`
- [ ] Deterministic fixture assets exist in-repo for the HTTP-driven integration proofs
- [ ] Test support can launch and tear down a local HTTP server inside the sandbox without host-side dependencies
- [ ] No host execution path is introduced; proofs still run entirely inside Docker

## Verification

- `docker build -t oxpwn-sandbox:dev docker/ && docker run --rm oxpwn-sandbox:dev sh -lc 'command -v nmap httpx subfinder nuclei ffuf python3'` — all binaries resolve
- `docker run --rm -v "$PWD/tests/fixtures/tool_suite/site:/srv/site:ro" oxpwn-sandbox:dev sh -lc 'cd /srv/site && python3 -m http.server 8000 >/tmp/http.log 2>&1 & pid=$!; python3 - <<"PY"
import urllib.request
body = urllib.request.urlopen("http://127.0.0.1:8000/admin/").read().decode()
assert "admin" in body.lower()
PY
kill $pid'` — the deterministic site fixture can be served and fetched entirely inside the sandbox image

## Observability Impact

- Signals added/changed: fixture server helper should expose the chosen port, startup command, and failure log path; missing-binary failures surface immediately from the image verification command
- How a future agent inspects this: rebuild the image and run the `command -v` check; inspect fixture helper return values and sandbox-side log files when the HTTP server fails to start
- Failure state exposed: missing package/symlink, HTTP server startup failure, or asset-copy failure becomes visible before parser work starts

## Inputs

- `docker/Dockerfile` — current Kali image with only `nmap` installed from S02
- `tests/conftest.py` — existing Docker sandbox fixture to extend without changing its core contract
- S04 research: `httpx-toolkit` is the packaged binary name, current image lacks a trivial HTTP server, and deterministic fixtures are preferred over internet-only proof targets

## Expected Output

- `docker/Dockerfile` — full core tool suite plus minimal HTTP fixture runtime
- `tests/conftest.py` — helper fixtures/utilities for seeding assets and running a local HTTP fixture inside the sandbox
- `tests/fixtures/tool_suite/site/index.html` — deterministic site root fixture
- `tests/fixtures/tool_suite/site/admin/index.html` — deterministic admin-path fixture
- `tests/fixtures/tool_suite/ffuf-wordlist.txt` — tiny wordlist for ffuf proof
- `tests/fixtures/tool_suite/nuclei/admin-panel.yaml` — custom nuclei template for deterministic matching
