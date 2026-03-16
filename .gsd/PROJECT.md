# Project

## What This Is

0xpwn — an autonomous AI pentesting agent that runs a 5-phase security assessment pipeline (Recon → Scanning → Exploitation → Validation → Reporting) inside an isolated Docker/Kali sandbox. Python 3.12+, Apache 2.0, freemium model.

## Core Value

A bug bounty hunter runs `0xpwn scan --target <url>` and watches an AI agent systematically discover, exploit, and verify real vulnerabilities — streaming its reasoning in real-time — for $1 instead of $10K.

## Current State

- S01 complete: Python package scaffolded, Pydantic models defined, async LLM client proven
- S02 complete: Docker sandbox with Kali image, nmap tool execution + XML parser, clean container lifecycle
- S03 complete: ReAct agent loop with tool registry, phase-aware prompts, event protocol, autonomous Recon→Scanning proven with real LLM + Docker
- S04 complete: Full five-tool core suite (`nmap`, `httpx`, `subfinder`, `nuclei`, `ffuf`) registered for the agent with compact parsers and real Docker proofs
- S05 complete: `0xpwn scan --target <url>` streams agent reasoning, phase transitions, raw tool output, and parsed results in real-time with Rich formatting
- S06 complete: First-run wizard detects Ollama, guides API key setup, validates LLM connectivity, persists config to YAML; `0xpwn config show/reset/wizard` subcommands; config feeds into scan command
- `pip install -e .` works, `0xpwn --help` responds, `0xpwn scan --target` executes real async scan pipeline
- Current test inventory: 192 unit tests passing; integration tests gated on Docker/LLM availability
- "Docker exploitation networking" risk retired (S02)
- "Agent loop quality" risk partially retired — agent autonomously selects tools, executes in Docker, accumulates state, and advances phases (S03)
- "Tool output parsing" risk retired for the five-tool M001 core suite (S04)
- Next: S07 (CVE Enrichment + Finding Quality), S08 (End-to-End Validation)

## Architecture / Key Patterns

- **Agent engine:** ReactAgent — ReAct loop with outer phase iteration, inner tool dispatch cycle. Composes LLMClient + DockerSandbox + ToolRegistry.
- **Tool registry:** ToolRegistry maps tool names to OpenAI function schemas + async executor factories. `register_default_tools()` now registers the five-tool M001 core suite: `nmap`, `httpx`, `subfinder`, `nuclei`, and `ffuf`.
- **Sandbox:** Docker container running custom Kali image (ghcr.io/0xpwn/sandbox) with NET_ADMIN/NET_RAW capabilities. Async context manager with labeled lifecycle and orphan cleanup plus deterministic in-container HTTP proof fixtures for tool-suite integration.
- **Tool executors:** `NmapExecutor`, `HttpxExecutor`, `SubfinderExecutor`, `NucleiExecutor`, and `FfufExecutor` share the same pattern — constructor takes `DockerSandbox`, async `run()` returns `ToolResult` with compact `parsed_output`.
- **Event protocol:** Typed dataclasses (ReasoningEvent, ToolCallEvent, ToolResultEvent, ToolOutputChunkEvent, PhaseTransitionEvent, ErrorEvent) + AgentEventCallback Protocol. RichStreamingCallback renders append-only Rich output in the CLI.
- **CLI entrypoint:** `0xpwn scan --target <url>` composes ScanState, ToolRegistry, DockerSandbox, LLMClient, and ReactAgent through `asyncio.run(_scan_async(...))`. Runtime config is env/option-backed pre-wizard.
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
