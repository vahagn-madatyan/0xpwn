# M001: Core Engine

**Vision:** A working autonomous pentesting agent — `0xpwn scan --target <url>` runs a 5-phase pipeline inside a Docker sandbox, streaming reasoning in real-time, producing enriched findings.

## Success Criteria

- User runs `pip install -e .` and the `0xpwn` CLI is available
- `0xpwn scan --target <url>` executes all 5 phases (Recon → Scanning → Exploitation → Validation → Reporting)
- Agent reasoning, tool selection, and results stream in real-time with color-coded phase transitions
- At least 1 real vulnerability found against OWASP Juice Shop with PoC evidence
- Findings include CVE IDs, CVSS scores, CWE classification from NVD enrichment
- First-run wizard guides model setup (Ollama local or cloud API key)
- Docker sandbox creates and destroys cleanly with no host exposure

## Key Risks / Unknowns

- **Agent loop quality** — ReAct reasoning for multi-phase pentesting is unproven; agent may hallucinate tool flags, loop without progress, or fail to connect findings across phases
- **Tool output parsing** — nmap/nuclei/ffuf output formats are complex and inconsistent; parsers may miss edge cases or break on unexpected output
- **Docker exploitation networking** — bridge networking may prevent certain exploitation techniques; reverse shells and SSRF require specific container↔target connectivity
- **Ollama tool calling quality** — local models may not handle function/tool calling reliably enough for autonomous operation

## Proof Strategy

- **Agent loop quality** → retire in S03 by proving the agent can autonomously reason through at least 2 phases, select appropriate tools, and accumulate state across tool results
- **Tool output parsing** → retire in S04 by proving all 5 tools produce structured Pydantic output from real scan results (not mocked)
- **Docker exploitation networking** → retire in S02 by proving a container can run nmap against a target on the Docker bridge network and return results
- **Ollama tool calling quality** → retire in S06 by proving at least one Ollama model completes the wizard and executes a basic scan

## Verification Classes

- Contract verification: pytest unit tests for agent loop, tool parsers, LLM client, sandbox lifecycle, config manager
- Integration verification: agent executes real tools in real Docker container against real target
- Operational verification: full scan lifecycle from CLI invocation to findings output, clean container teardown
- UAT / human verification: human reviews streaming output quality, finding accuracy, and UX of first-run wizard

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 8 slices are complete with their individual verification passing
- Agent loop, sandbox, LLM client, tool parsers, and CLI are wired together end-to-end
- `0xpwn` CLI entrypoint exists and is exercised via `pip install -e .`
- Success criteria are re-checked against a live Juice Shop scan, not just unit tests
- Final integrated acceptance passes: real scan with real findings, streaming output, CVE enrichment

## Requirement Coverage

- Covers: R001, R002, R003, R004, R005, R006
- Partially covers: none
- Leaves for later: R007–R024 (M002–M004), R025–R033 (deferred)
- Orphan risks: none

## Slices

- [x] **S01: Foundation + LLM Client** `risk:high` `depends:[]`
  > After this: Python package scaffolded with pyproject.toml, Pydantic state models defined, LiteLLM async client sends prompts with tool calling to any provider and returns structured responses with cost data — proven by integration test against a real LLM

- [x] **S02: Docker Sandbox + Tool Execution** `risk:high` `depends:[S01]`
  > After this: Docker container spawns from custom Kali base image, executes nmap inside it, returns structured parsed output, and tears down cleanly — proven by integration test against a real Docker daemon

- [x] **S03: ReAct Agent Loop** `risk:high` `depends:[S01,S02]`
  > After this: Agent autonomously reasons through at least Recon and Scanning phases, selects tools, executes them in the sandbox, parses results, accumulates state, and transitions between phases — proven by integration test with real LLM and Docker

- [ ] **S04: Tool Suite Integration** `risk:medium` `depends:[S02,S03]`
  > After this: Agent uses all 5 core tools (nmap, httpx, subfinder, nuclei, ffuf) with structured Pydantic output parsers, each tool proven against real targets inside the sandbox

- [ ] **S05: Streaming CLI + Real-time Output** `risk:medium` `depends:[S03]`
  > After this: `0xpwn scan --target <url>` CLI command exists, agent reasoning and tool output stream in real-time with Rich formatting and color-coded phase transitions — proven by running a scan from the terminal

- [ ] **S06: First-Run Wizard + Config** `risk:low` `depends:[S01,S05]`
  > After this: First-time user runs `0xpwn` and gets interactive wizard that detects Ollama, guides API key setup, validates connectivity, and persists config to YAML — proven by fresh config test

- [ ] **S07: CVE Enrichment + Finding Quality** `risk:medium` `depends:[S04]`
  > After this: Findings include CVE IDs, CVSS scores, CWE classification, and remediation guidance from NVD API with local caching — proven by enriching real scan findings

- [ ] **S08: End-to-End Validation** `risk:low` `depends:[S01,S02,S03,S04,S05,S06,S07]`
  > After this: Full scan against OWASP Juice Shop runs all 5 phases, finds real vulnerabilities with PoC evidence, streams reasoning in real-time, and produces enriched findings — proving the complete M001 outcome

## Boundary Map

### S01 → S02

Produces:
- `oxpwn.core.models` — Pydantic models: ScanState, Finding, Phase, ToolResult, LLMResponse
- `oxpwn.llm.client` — async LLM client with tool calling, cost tracking, and provider abstraction
- `pyproject.toml` — package metadata with `[project.scripts]` entrypoint

Consumes:
- nothing (first slice)

### S01 → S03

Produces:
- `oxpwn.core.models` — state models the agent loop will manage
- `oxpwn.llm.client` — LLM client the agent will use for reasoning

### S02 → S03

Produces:
- `oxpwn.sandbox.docker` — container lifecycle manager (create, exec, destroy)
- `oxpwn.sandbox.tools.nmap` — tool executor + output parser (reference implementation)

### S02 → S04

Produces:
- `oxpwn.sandbox.docker` — container lifecycle for tool execution
- Tool executor pattern from nmap parser as template for other tools

### S03 → S04

Produces:
- `oxpwn.agent.react` — ReAct loop with tool dispatch interface
- Tool registration pattern (how tools expose their schema to the agent)

### S03 → S05

Produces:
- `oxpwn.agent.react` — agent loop with event emission interface for streaming
- Phase transition events the CLI will render

### S04 → S07

Produces:
- `oxpwn.core.models.Finding` — structured findings that CVE enrichment will augment
- 5 working tool parsers producing findings

### S01, S05 → S06

Produces:
- `oxpwn.llm.client` — client that config will initialize
- `oxpwn.cli` — CLI framework the wizard will plug into

### All → S08

Produces:
- Complete wired system for end-to-end integration testing
