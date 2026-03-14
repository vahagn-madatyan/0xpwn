# Project

## What This Is

0xpwn — an autonomous AI pentesting agent that runs a 5-phase security assessment pipeline (Recon → Scanning → Exploitation → Validation → Reporting) inside an isolated Docker/Kali sandbox. Python 3.12+, Apache 2.0, freemium model.

## Core Value

A bug bounty hunter runs `0xpwn scan --target <url>` and watches an AI agent systematically discover, exploit, and verify real vulnerabilities — streaming its reasoning in real-time — for $1 instead of $10K.

## Current State

- S01 complete: Python package scaffolded, Pydantic models defined, async LLM client proven
- S02 complete: Docker sandbox with Kali image, nmap tool execution + XML parser, clean container lifecycle
- S03 complete: ReAct agent loop with tool registry, phase-aware prompts, event protocol, autonomous Recon→Scanning proven with real LLM + Docker
- `pip install -e .` works, `0xpwn --help` responds
- Total: 43 S01 unit + 2 S01 integration + 20 S02 unit + 4 S02 integration + 24 S03 unit + 1 S03 integration = 94 tests
- "Docker exploitation networking" risk retired (S02)
- "Agent loop quality" risk partially retired — agent autonomously selects nmap, executes in Docker, accumulates state, advances phases (S03)
- Next: S04 (Tool Suite Integration — httpx, subfinder, nuclei, ffuf)

## Architecture / Key Patterns

- **Agent engine:** ReactAgent — ReAct loop with outer phase iteration, inner tool dispatch cycle. Composes LLMClient + DockerSandbox + ToolRegistry.
- **Tool registry:** ToolRegistry maps tool names to OpenAI function schemas + async executor factories. `register_default_tools()` registers nmap; S04 adds 4 more.
- **Sandbox:** Docker container running custom Kali image (ghcr.io/0xpwn/sandbox) with NET_ADMIN/NET_RAW capabilities. Async context manager with labeled lifecycle and orphan cleanup.
- **Tool executors:** NmapExecutor pattern — constructor takes DockerSandbox, async run() returns ToolResult with parsed_output. S04 replicates for 4 more tools.
- **Event protocol:** Typed dataclasses (ReasoningEvent, ToolCallEvent, ToolResultEvent, PhaseTransitionEvent, ErrorEvent) + AgentEventCallback Protocol. S05 implements with Rich rendering.
- **LLM layer:** LiteLLM for provider-agnostic access to 100+ models including Ollama for local
- **CLI:** Typer + Rich for streaming output, Textual for interactive TUI (M004)
- **State:** Pydantic models, SQLite persistence (M002), event-sourced audit log
- **Package:** `oxpwn` Python package, `0xpwn` CLI entrypoint
- **Config:** YAML-based, first-run guided wizard for model setup

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [ ] M001: Core Engine — Agent loop, sandbox, CLI, 5 tools, streaming output, CVE enrichment
- [ ] M002: Safety + Persistence — Permissions, budget controls, scope enforcement, SQLite, audit log
- [ ] M003: Validation + Reporting — PoC validation agent, 5 report formats, CVSS scoring, dedup
- [ ] M004: Extensibility + Advanced — MCP, plugins, REST API, TUI, compliance mapping, freemium gating
- [ ] M005: Enterprise + Cloud — ECS/Fargate, Temporal, PostgreSQL, RBAC, SSO, web dashboard
