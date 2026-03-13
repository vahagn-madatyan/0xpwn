# M001: Core Engine — Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

## Project Description

0xpwn is an autonomous AI pentesting agent. M001 builds the foundational engine: ReAct agent loop, Docker/Kali sandbox, LiteLLM integration, 5 core security tools, streaming CLI, first-run wizard, and CVE enrichment. At the end, a user can run a real scan against a target and watch the AI find vulnerabilities.

## Why This Milestone

Everything else depends on a working agent engine. Without the core loop (reason → select tool → execute in sandbox → parse results → reason again), there's nothing to add permissions to (M002), validate (M003), or extend (M004). This is the foundation and the demo — the thing that makes people go "oh, this actually works."

## User-Visible Outcome

### When this milestone is complete, the user can:

- Run `pip install -e .` and `0xpwn scan --target <url>` to execute a full 5-phase security assessment
- Watch the agent's reasoning, tool selection, and results stream in real-time with color-coded phase transitions
- Get structured findings with CVE IDs, CVSS scores, and remediation guidance
- Configure their preferred LLM provider through a guided first-run wizard

### Entry point / environment

- Entry point: `0xpwn` CLI command (Typer)
- Environment: local dev — macOS/Linux with Docker installed
- Live dependencies involved: Docker daemon, LLM provider (Ollama or cloud API), NVD API

## Completion Class

- Contract complete means: unit tests pass for agent loop, sandbox lifecycle, tool parsing, LLM client; CLI entrypoint works
- Integration complete means: agent can orchestrate a multi-phase scan inside a real Docker container using a real LLM
- Operational complete means: full scan against OWASP Juice Shop produces real findings with evidence

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- `0xpwn scan --target http://localhost:3000` (Juice Shop) runs all 5 phases and produces findings with PoC evidence
- Agent reasoning streams in real-time with visible phase transitions (Recon → Scanning → Exploitation → Validation → Reporting)
- At least one real vulnerability is found with CVE enrichment (CVE ID, CVSS score, CWE)
- First-run wizard successfully configures at least Ollama and one cloud provider (OpenAI or Anthropic)
- Docker sandbox creates and destroys cleanly with no host filesystem exposure

## Risks and Unknowns

- **Agent loop quality** — ReAct reasoning for pentesting is unproven at this depth; the agent may get stuck, hallucinate tool flags, or fail to connect findings across phases. This is the highest risk.
- **Tool output parsing reliability** — nmap, nuclei, etc. have complex and inconsistent output formats; parsers may miss edge cases.
- **Docker networking for exploitation** — some exploitation techniques (reverse shells, SSRF) require specific network configurations between container and target.
- **LLM tool calling compatibility** — not all LiteLLM-supported models handle tool/function calling equally well; Ollama models may underperform.
- **NVD API rate limits** — free tier is 5 requests/30 seconds; may need caching strategy for scans with many findings.

## Existing Codebase / Prior Art

- `research.md` — landscape analysis of 20+ AI pentesting tools; patterns and anti-patterns identified
- `0xpwn-spec.jsx` — full architecture spec with agent pipeline, Mermaid diagrams, tech stack decisions
- `strix-gap-analysis.jsx` — detailed feature comparison with effort/priority estimates
- `0xpwn-brand-kit.jsx` — brand identity, CLI preview mockups, color system, README template
- No existing source code — building from zero

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R001 — Autonomous 5-phase pentesting pipeline (primary)
- R002 — Isolated Docker/Kali sandbox execution (primary)
- R003 — Provider-agnostic LLM support via LiteLLM (primary)
- R004 — Real-time agent reasoning stream (primary)
- R005 — First-run guided model setup wizard (primary)
- R006 — CVE/NVD enrichment for findings (primary)

## Scope

### In Scope

- ReAct agent loop with multi-phase state management
- Docker container lifecycle (create, exec, destroy) with custom Kali image
- LiteLLM async client with tool calling and cost tracking
- 5 core tools: nmap, httpx, subfinder, nuclei, ffuf
- Structured tool output parsers (JSON/XML → Pydantic models)
- Typer CLI with Rich streaming output
- First-run model configuration wizard
- NVD/CVE enrichment for findings
- Pydantic state models (ScanState, Finding, Phase, ToolResult)
- Basic error handling and graceful degradation
- Dockerfile for custom sandbox image

### Out of Scope / Non-Goals

- Permission tiers (M002)
- Budget controls / cost caps (M002)
- Session persistence / SQLite (M002)
- PoC validation agent (M003)
- Report generation beyond terminal output (M003)
- TUI dashboard (M004)
- Plugin system (M004)
- REST API (M004)
- MCP protocol (M004)
- Freemium gating (M004)

## Technical Constraints

- Python 3.12+ (for modern typing, TaskGroup, ExceptionGroup)
- Docker must be installed and running on the host
- LiteLLM for LLM abstraction (Decision #4)
- Typer + Rich for CLI (Decision #10)
- Pydantic v2 for all data models
- async/await throughout (acompletion, async Docker ops where possible)
- `src/oxpwn/` package layout with `0xpwn` CLI entrypoint

## Integration Points

- **Docker daemon** — container create/exec/destroy via docker-py SDK
- **LLM providers** — completion/tool-calling via LiteLLM (OpenAI, Anthropic, Ollama, etc.)
- **NVD API** — CVE/CVSS lookup via api.nvd.nist.gov REST API
- **Security tools** — nmap, httpx, subfinder, nuclei, ffuf running inside Docker container

## Open Questions

- **Ollama model quality** — Which Ollama models are good enough for tool calling in pentesting context? May need to test several and recommend specific ones. Current thinking: test Llama 3.1 70B, Qwen 2.5 72B, Mistral Large.
- **Agent context window management** — Long scans accumulate lots of tool output. How to manage context without losing important findings? Current thinking: summarize completed phase results, keep current phase in full detail.
- **Sandbox networking mode** — Docker bridge vs host networking for the sandbox container. Bridge is safer but may complicate some exploitation scenarios. Current thinking: start with bridge, add host mode as explicit opt-in flag.
