# Project

## What This Is

0xpwn — an autonomous AI pentesting agent that runs a 5-phase security assessment pipeline (Recon → Scanning → Exploitation → Validation → Reporting) inside an isolated Docker/Kali sandbox. Python 3.12+, Apache 2.0, freemium model.

## Core Value

A bug bounty hunter runs `0xpwn scan --target <url>` and watches an AI agent systematically discover, exploit, and verify real vulnerabilities — streaming its reasoning in real-time — for $1 instead of $10K.

## Current State

- **M001 Core Engine complete** (2026-03-15) — all 8 slices done, 261 unit tests passing
- 5 requirements validated: R001 (5-phase pipeline), R002 (Docker sandbox), R004 (streaming), R005 (wizard), R006 (CVE enrichment)
- `pip install -e .` works, `0xpwn --help` responds, `0xpwn scan --target` executes full 5-phase async scan pipeline
- Full subsystem inventory: agent loop, Docker/Kali sandbox (5 tools), LLM client (LiteLLM), streaming CLI (Rich), first-run wizard, NVD CVE enrichment
- 31 source files across 7 subpackages: core/, agent/, cli/, config/, enrichment/, llm/, sandbox/
- Next: M002 (Safety + Persistence) — permissions, budget controls, scope enforcement, SQLite, audit log

## Architecture / Key Patterns

- **Agent engine:** ReactAgent — ReAct loop with outer phase iteration, inner tool dispatch cycle. Composes LLMClient + DockerSandbox + ToolRegistry.
- **Tool registry:** ToolRegistry maps tool names to OpenAI function schemas + async executor factories. `register_default_tools()` now registers the five-tool M001 core suite: `nmap`, `httpx`, `subfinder`, `nuclei`, and `ffuf`.
- **Sandbox:** Docker container running custom Kali image (ghcr.io/0xpwn/sandbox) with NET_ADMIN/NET_RAW capabilities. Async context manager with labeled lifecycle and orphan cleanup plus deterministic in-container HTTP proof fixtures for tool-suite integration.
- **Tool executors:** `NmapExecutor`, `HttpxExecutor`, `SubfinderExecutor`, `NucleiExecutor`, and `FfufExecutor` share the same pattern — constructor takes `DockerSandbox`, async `run()` returns `ToolResult` with compact `parsed_output`.
- **Event protocol:** Typed dataclasses (ReasoningEvent, ToolCallEvent, ToolResultEvent, ToolOutputChunkEvent, PhaseTransitionEvent, ErrorEvent) + AgentEventCallback Protocol. RichStreamingCallback renders append-only Rich output in the CLI.
- **CLI entrypoint:** `0xpwn scan --target <url>` composes ScanState, ToolRegistry, DockerSandbox, LLMClient, and ReactAgent through `asyncio.run(_scan_async(...))`. Config resolves via CLI > env > YAML > wizard trigger.
- **LLM layer:** LiteLLM for provider-agnostic access to 100+ models including Ollama for local
- **CLI:** Typer + Rich for streaming output, Textual for interactive TUI (M004)
- **State:** Pydantic models, SQLite persistence (M002), event-sourced audit log
- **Config:** YAML-based with XDG path conventions, first-run guided wizard for model setup, `0xpwn config show/reset/wizard`
- **Enrichment:** NVD CVE 2.0 API client with rate limiting, SQLite cache (WAL mode, 7-day TTL), batch enrichment populating CVSS/CWE/remediation on findings
- **Package:** `oxpwn` Python package, `0xpwn` CLI entrypoint

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [x] M001: Core Engine — Agent loop, sandbox, CLI, 5 tools, streaming output, CVE enrichment
- [ ] M002: Safety + Persistence — Permissions, budget controls, scope enforcement, SQLite, audit log
- [ ] M003: Validation + Reporting — PoC validation agent, 5 report formats, CVSS scoring, dedup
- [ ] M004: Extensibility + Advanced — MCP, plugins, REST API, TUI, compliance mapping, freemium gating
- [ ] M005: Enterprise + Cloud — ECS/Fargate, Temporal, PostgreSQL, RBAC, SSO, web dashboard
