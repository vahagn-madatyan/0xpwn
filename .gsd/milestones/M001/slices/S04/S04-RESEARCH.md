# S04: Tool Suite Integration — Research

**Date:** 2026-03-14

## Requirement Focus

This slice primarily targets the following active requirements:

- **R001 — Autonomous 5-phase pentesting pipeline** *(supporting slice)*
  - S03 proved the ReAct loop with `nmap` across Recon → Scanning.
  - S04 is what makes the agent materially useful by adding the other 4 core tools the loop can choose from.
- **R002 — Isolated Docker/Kali sandbox execution** *(operational dependency, not primary owner)*
  - S02 already owns sandbox execution, but S04 stress-tests that design by requiring 4 additional real tools inside the container.
- **R006 — CVE/NVD enrichment for findings** *(downstream dependency, not owner)*
  - S04 does not do enrichment, but parser fidelity here determines how much structured evidence S07 will have to enrich.

## Summary

The good news: S04 does **not** need new architecture. The repo already has the exact extension seams it needs: `DockerSandbox` executes commands in the Kali container, `NmapExecutor` establishes the tool-executor pattern, `ToolRegistry` exposes OpenAI-function schemas to the LLM, and `ReactAgent` already feeds `parsed_output` back into the loop as JSON. The fastest path is to replicate the `nmap` pattern for `httpx`, `subfinder`, `nuclei`, and `ffuf`.

The actual work is mostly in three places: **container packaging**, **machine-readable parsing**, and **agent guidance**. Packaging is more nuanced than expected because Kali ships all four tools, but `httpx` is packaged as **`httpx-toolkit`** and installs **`/usr/bin/httpx-toolkit`**, not `httpx`. Parsing should avoid human CLI output entirely: all 4 missing tools have JSON/JSONL modes, and those are the right substrate for structured Pydantic parsers. Agent guidance also needs attention: the current prompt text is still nmap-centric, so simply registering new tools is unlikely to make the model use them well.

The biggest constraint is verification, not coding. `httpx`, `nuclei`, and `ffuf` want an HTTP target; `subfinder` wants a public domain and outbound internet. The most reliable proof strategy is: use deterministic machine-readable output for all tools, keep tests mostly local where possible, and treat `subfinder` as the one integration proof that likely remains internet-gated.

## Key Findings / Surprises

- **Kali already packages all 4 missing tools**, so S04 probably does not need custom release-binary install logic.
- The package/binary story is tricky:
  - `subfinder`, `nuclei`, `ffuf` install under their expected binary names.
  - `httpx` is packaged as **`httpx-toolkit`** and exposes **`httpx-toolkit`** as the binary name.
- The current sandbox image has **no trivial HTTP fixture server** available:
  - no `python3`
  - no `busybox httpd`
  - no `nc` / `socat`
- `ffuf`’s JSON output includes an `input` object whose fuzz values are **base64 encoded**.
- `nuclei` JSONL is usable, but it is noisy by default; without `-or` / `-ot`, it includes large request/response and template blobs that would bloat `parsed_output` and degrade S03’s 4000-char LLM feedback loop.
- The agent prompt still explicitly tells the model to use `nmap` in Recon. If S04 does not update prompt guidance, the LLM may simply keep choosing `nmap`.

## Recommendation

Take a **minimal-surface, machine-readable, contract-preserving** approach:

1. **Extend the Docker image, not the runtime.**
   - Add `subfinder`, `nuclei`, `ffuf`, and `httpx-toolkit` to `docker/Dockerfile`.
   - Add a symlink so the internal command can stay `httpx`:
     - `ln -s /usr/bin/httpx-toolkit /usr/local/bin/httpx`
   - Add a tiny HTTP fixture capability for integration tests:
     - best options: `busybox` or `python3-minimal`
   - Add a deterministic wordlist source for `ffuf`:
     - either package `wordlists` / `seclists`
     - or ship a tiny test wordlist fixture in-repo and copy/use it in tests.

2. **Implement tool-specific parser modules using Pydantic internally, but keep `ToolResult.parsed_output` as a dict.**
   - This preserves S02/S03 contracts.
   - Recommended pattern:
     - `parse_httpx_jsonl(...) -> HttpxScanResult`
     - `parse_subfinder_jsonl(...) -> SubfinderScanResult`
     - `parse_nuclei_jsonl(...) -> NucleiScanResult`
     - `parse_ffuf_jsonl(...) -> FfufScanResult`
     - executor stores `result.parsed_output = parsed.model_dump(mode="json")`

3. **Normalize and shrink outputs before feeding them back to the LLM.**
   - Keep raw tool stdout in `ToolResult.stdout` for audit/debug.
   - Keep `parsed_output` compact and agent-useful.
   - Especially for `nuclei`, do not dump the full upstream JSON record into `parsed_output`.

4. **Register the new tools and update prompt guidance together.**
   - `subfinder` + `httpx` belong in Recon.
   - `nuclei` + `ffuf` belong in Scanning.
   - `nmap` remains useful in both.
   - If prompt guidance is not updated, S04 may technically add tools but fail to improve autonomous behavior.

5. **Do not blindly copy `nmap`’s free-form `flags: str` schema to every tool.**
   - S03 already identified tool-calling quality as fragile.
   - Prefer **curated, small, typed schemas** over “raw flags” pass-through where possible.
   - Follow the executor pattern, not necessarily the exact nmap argument surface.

## Don’t Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|-------------------|------------|
| Parsing human `httpx` terminal output | `httpx -json -silent` (with packaged binary symlinked from `httpx-toolkit`) | JSONL is stable and avoids scraping colored/status text. |
| Parsing human `subfinder` output | `subfinder -oJ` | Emits one JSON object per result; easy to group/dedupe by host. |
| Parsing human `nuclei` findings text | `nuclei -j -silent -or -ot -duc -ni` | JSONL is machine-readable, quieter, and avoids raw/template bloat. |
| Scraping `ffuf` terminal results | `ffuf -json -s` | Emits newline-delimited JSON matches; parser can ignore stderr progress noise. |
| Depending on live nuclei template corpus for proof | Use a tiny deterministic custom nuclei template in tests | Still proves real nuclei execution, but removes upstream template/update drift. |
| Stuffing full upstream JSON into `parsed_output` | Normalize with Pydantic and keep only agent-relevant fields | Protects the S03 prompt loop from oversized tool observations. |

## Existing Code and Patterns

- `src/oxpwn/sandbox/tools/nmap.py` — The authoritative executor/parser template. Follow its structure: parser function + executor class + graceful parse failure (`parsed_output=None`, no crash).
- `src/oxpwn/agent/tools.py` — `ToolRegistry.register(...)` and `register_default_tools(...)` are the integration seam for the new tools. Add new schemas here.
- `src/oxpwn/agent/prompts.py` — Current phase guidance is still `nmap`-only. S04 should update this or the LLM will underuse the new tools.
- `src/oxpwn/agent/react.py` — The agent serializes `parsed_output` to JSON and truncates it to **4000 chars** before feeding it back to the LLM. This constrains parser output size.
- `src/oxpwn/core/models.py` — `ToolResult.parsed_output` is currently `dict[str, Any] | None`; changing that type would ripple into S02/S03 tests.
- `docker/Dockerfile` — Only installs `nmap` today. S04 must expand the image.
- `tests/unit/test_nmap_parser.py` — Good unit-test pattern to copy: realistic fixtures, parser edge cases, mocked sandbox executor tests.
- `tests/integration/test_sandbox_integration.py` — Good real-Docker proof pattern to extend.
- `tests/conftest.py` — The integration fixture already auto-builds `oxpwn-sandbox:dev`; S04 can lean on that instead of inventing new setup flows.

## Constraints

- **Contract constraint:** `ToolResult.parsed_output` is a dict today. Use Pydantic parsers internally, then dump to dict.
- **Prompt constraint:** `build_system_prompt()` currently nudges the model toward `nmap`, not the full tool suite.
- **Phase constraint:** `ReactAgent` still only iterates `recon` + `scanning` in `_PHASE_ORDER`. S04 supports R001 but does not complete the 5-phase pipeline alone.
- **Naming constraint:** `pyproject.toml` already depends on Python `httpx`, while the security tool is packaged as `httpx-toolkit`. Docs, imports, and command naming need to stay explicit.
- **Binary constraint:** packaged Kali binary name is `httpx-toolkit`, not `httpx`.
- **Fixture constraint:** the current sandbox image has no built-in way to host a tiny local HTTP target.
- **Wordlist constraint:** `ffuf` requires a wordlist, and the repo currently provisions none.
- **Network constraint:** `subfinder` is the least deterministic tool to prove because it requires outbound internet and a public domain; `localhost` is not a meaningful target for it.
- **Shell constraint:** `DockerSandbox.execute()` runs the provided command directly. Anything needing pipes, redirection, or backgrounding must explicitly use `sh -lc '...'`.
- **Version drift constraint:** Kali-packaged versions may lag upstream docs, so S04 should prefer flags confirmed against installed binaries, not only README examples.

## Common Pitfalls

- **Copying `flags: str` blindly to every tool** — That maximizes CLI surface area and invites hallucinated flags. Prefer smaller typed schemas.
- **Forgetting to update prompt guidance** — The tool registry can be perfect and the agent will still mostly use `nmap` if the phase instructions stay nmap-centric.
- **Keeping raw upstream JSON in `parsed_output`** — `nuclei` especially will balloon the observation size and weaken the reasoning loop.
- **Assuming `ffuf` JSON `input` values are plain text** — They are base64 encoded in real output; decode or preserve clearly.
- **Assuming `subfinder` can be proven against local targets** — It cannot; proof needs a public domain and internet access.
- **Treating stderr progress noise as parse input** — `ffuf` and other CLIs may emit progress/control sequences; parse stdout only.
- **Relying on auto-updating external assets during tests** — `nuclei` template updates and large wordlist packages can make proof flaky and slow.

## Open Risks

- **Subfinder proof remains the weakest integration story.** A public domain like `projectdiscovery.io` works in ad hoc probing, but it is still internet/provider dependent.
- **HTTP-target proof strategy is undecided in code.** S04 needs either:
  - a tiny HTTP fixture server in the sandbox image, or
  - a sibling target container/network fixture, or
  - internet-dependent targets for `httpx` / `ffuf` / `nuclei`.
- **Agent quality may not improve automatically after tool registration.** Tool descriptions + prompt guidance are likely the deciding factor.
- **Overly rich parsed outputs may hurt S03 behavior.** Bigger structured records are not always better if they exceed the agent’s observation budget.

## Skills Discovered

No directly relevant skill was already installed in `<available_skills>`.

| Technology | Skill | Status |
|------------|-------|--------|
| Docker / image work | `sickn33/antigravity-awesome-skills@docker-expert` | available — `npx skills add sickn33/antigravity-awesome-skills@docker-expert` |
| Docker image optimization | `github/awesome-copilot@multi-stage-dockerfile` | available — `npx skills add github/awesome-copilot@multi-stage-dockerfile` |
| ProjectDiscovery suite | `laurigates/claude-plugins@project-discovery` | available, low-signal (46 installs) — `npx skills add laurigates/claude-plugins@project-discovery` |
| ffuf | `jthack/ffuf_claude_skill@ffuf-web-fuzzing` | available — `npx skills add jthack/ffuf_claude_skill@ffuf-web-fuzzing` |
| subfinder | none found | none found |

## Sources

- Tool executor pattern, registry seam, prompt guidance, phase order, and parsed-output truncation were verified from local code:
  - `src/oxpwn/sandbox/tools/nmap.py`
  - `src/oxpwn/agent/tools.py`
  - `src/oxpwn/agent/prompts.py`
  - `src/oxpwn/agent/react.py`
  - `src/oxpwn/core/models.py`
  - `docker/Dockerfile`
  - `tests/unit/test_nmap_parser.py`
  - `tests/integration/test_sandbox_integration.py`
  - `tests/conftest.py`
- `subfinder` JSON output mode, provider/config flags, and passive-enumeration behavior (source: [Subfinder README](https://github.com/projectdiscovery/subfinder/blob/dev/README.md))
- `nuclei` JSONL flags, template handling, update flags, and headless/runtime options (source: [Nuclei README](https://github.com/projectdiscovery/nuclei/blob/dev/README.md))
- `ffuf` JSON output and file output modes (source: [ffuf README](https://github.com/ffuf/ffuf/blob/master/README.md), [ffuf Wiki](https://github.com/ffuf/ffuf/wiki/Home))
- `httpx` JSON output patterns and available machine-readable fields (source: [ProjectDiscovery httpx docs via Context7](https://context7.com/projectdiscovery/httpx/llms.txt))
- Local package and runtime probes against `kalilinux/kali-rolling` / `oxpwn-sandbox:dev` confirmed:
  - Kali packages exist for `subfinder`, `nuclei`, `ffuf`, and `httpx-toolkit`
  - `httpx-toolkit` installs `/usr/bin/httpx-toolkit`
  - current `oxpwn-sandbox:dev` contains `nmap` only
  - current `oxpwn-sandbox:dev` lacks `python3`, `busybox`, `nc`, and `socat`
  - real JSON/JSONL outputs were observed from:
    - `httpx-toolkit` against `example.com`
    - `subfinder` against `projectdiscovery.io`
    - `ffuf` against `https://httpbin.org/FUZZ`
    - `nuclei` against `https://example.com` using a custom deterministic template
