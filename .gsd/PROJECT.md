# Project

## What This Is

0xpwn — an autonomous AI pentesting agent that runs a 5-phase security assessment pipeline (Recon → Scanning → Exploitation → Validation → Reporting) inside an isolated Docker/Kali sandbox. Python 3.12+, Apache 2.0, freemium model. Currently pre-code — planning documents, brand kit, competitive research, and gap analysis exist but no implementation yet.

## Core Value

A bug bounty hunter runs `0xpwn scan --target <url>` and watches an AI agent systematically discover, exploit, and verify real vulnerabilities — streaming its reasoning in real-time — for $1 instead of $10K.

## Current State

- 2 git commits (init only), no source code
- Planning artifacts: research.md (20+ tool landscape), 0xpwn-spec.jsx (full architecture), strix-gap-analysis.jsx (feature comparison), 0xpwn-brand-kit.jsx (identity/CLI mockups)
- GSD milestone M001 planned, not started

## Architecture / Key Patterns

- **Agent engine:** ReAct loop with multi-agent coordination (Planner, Executor, Perceptor, Validator, Reporter)
- **Sandbox:** Docker container running custom Kali image (ghcr.io/0xpwn/sandbox) with NET_ADMIN/NET_RAW capabilities
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
