# Open-Source AI Pentesting Agents: Comprehensive Landscape Analysis

**Strix is the strongest fork candidate for your planned architecture.** Among 20+ repositories analyzed, Strix (Apache 2.0, Python, LiteLLM, Docker sandbox, Textual TUI) aligns with your planned stack on every dimension — and it has **20.5k stars** with 24 contributors and active development. However, building from scratch using extractable components from multiple projects may yield a more tailored result. CAI offers the best extensibility model but its non-commercial license is a dealbreaker. PentAGI has the most sophisticated Docker sandbox architecture but is written in Go. The landscape is maturing rapidly — six of the top projects launched or underwent major rewrites in 2025-2026.

---

## The competitive landscape at a glance

The table below captures every significant open-source AI pentesting agent, scored against your planned architecture (Python CLI, LiteLLM, Docker sandbox, ReAct loop, Typer/Textual TUI, freemium model).

| Project | Stars | License | Language | Architecture | LLM Layer | Docker Sandbox | UI | State | Active | Arch. Match |
|---------|-------|---------|----------|-------------|-----------|---------------|-----|-------|--------|-------------|
| **Strix** | 20.5k | Apache 2.0 ✅ | Python ✅ | Multi-agent coord. graph | LiteLLM ✅ | Kali Docker ✅ | Textual TUI ✅ | File-based | Very active | **⭐⭐⭐⭐⭐** |
| **Shannon** | 10.6k+ | AGPL-3.0 ❌ | TypeScript ❌ | 5-phase pipeline + Temporal | Claude SDK only | Docker ✅ | Bash CLI | Temporal + filesystem | Very active | ⭐⭐ |
| **PentestGPT** | 12k | MIT ✅ | Python ✅ | Custom agentic (v1.0) | Claude Code (custom) | Docker ✅ | Textual TUI ✅ | File-based | Active | ⭐⭐⭐ |
| **CAI** | 7.3k | Non-commercial ❌ | Python ✅ | ReACT + multi-pattern | LiteLLM ✅ | Host (no sandbox) | CLI/REPL | JSONL files | Very active | ⭐⭐⭐ (license kills it) |
| **HexStrike AI** | 7.1k | MIT ✅ | Python ✅ | MCP tool server (not agent) | None (external) | None ❌ | Server only | In-memory | Moderate | ⭐⭐ |
| **PentestAgent** | 532 | MIT ✅ | Python ✅ | Single + crew mode | LiteLLM ✅ | Docker (Kali) ✅ | Textual TUI ✅ | Notes + Shadow Graph | Active | **⭐⭐⭐⭐** |
| **PentAGI** | 900 | MIT* (AGPL cloud) | Go ❌ | Multi-agent delegation | LangChainGo fork | Kali Docker ✅ | React Web UI | PostgreSQL + pgvector | Very active | ⭐⭐ |
| **RedAmon** | 1.3k | MIT ✅ | Python ✅ | LangGraph ReAct ✅ | LangGraph (OpenAI) | Docker + MCP ✅ | Web dashboard | Neo4j graph | Active (new) | ⭐⭐⭐⭐ |
| **hackingBuddyGPT** | 951 | MIT ✅ | Python ✅ | Modular use-cases | OpenAI direct | SSH/local shell | CLI | SQLite | Active | ⭐⭐⭐ |
| **Pentest Copilot** | 233 | MIT ✅ | JavaScript ❌ | Agentic + CoT + RAG | GPT-4 Turbo | Docker + SSH | Browser UI | Database | Active (enterprise) | ⭐⭐ |
| **MAPTA** | 86 | MIT ✅ | Python ✅ | 3-role multi-agent | OpenAI GPT-5 only | Docker ✅ | Script only | Ephemeral | Inactive (2 commits) | ⭐⭐ |
| **Nebula** | 872 | Unknown | Python ✅ | CLI assistant | OpenAI + Ollama | Docker available | CLI panels | Engagement-based | Active | ⭐⭐ |

---

## Strix emerges as the clear fork candidate

**Strix checks every box in your planned architecture.** It uses Python with a Textual-based TUI, LiteLLM for provider-agnostic model support (including Ollama), a Docker sandbox built on Kali Linux with proper capability management, and a multi-agent coordination graph that functions as a sophisticated agent loop. At **20.5k stars**, it has the largest community of any project here. The Apache 2.0 license explicitly permits commercial use and derivative works — ideal for a freemium product.

The architecture is cleanly layered into extractable components. The **DockerRuntime** (338 lines) implements an `AbstractRuntime` interface with NET_ADMIN/NET_RAW capabilities, self-signed CA certificate injection for HTTPS interception, and a FastAPI-based tool server running inside the sandbox on port 48081 with bearer token authentication. Each agent gets isolated terminal sessions, Python instances, and browser contexts via `ContextVar`. The **LLM layer** wraps LiteLLM in 326 lines with request queuing, rate limiting, and memory compression. The **agent graph** uses metaclass-based `BaseAgent` with an `agent_loop()` cycle of message checking → LLM generation → tool execution → state transitions, and agents communicate via XML-structured inter-agent messages.

Strix also already operates as a freemium business: the open-source CLI is free, while app.strix.ai offers managed scanning, team dashboards, Jira/Slack integrations, and a paid LLM proxy ("Strix Router" at models.strix.ai with $10 free credit). This validates your planned business model.

**Key weaknesses to evaluate before forking:** Strix is pre-1.0 (v0.8.2), so the API may still change. It lacks formal benchmark publications — unlike Shannon's 96.15% XBOW score. Docker container networking prevents reverse shells and inbound callbacks. There is no built-in cost tracking, and no SQLite/PostgreSQL persistence — state is purely file-based in `strix_runs/`. The PostHog telemetry integration may concern some users.

---

## Three projects with extractable components worth studying

Even if you fork Strix or build from scratch, several projects offer architectural innovations worth borrowing:

**CAI's extensibility model is best-in-class.** Its `@function_tool` decorator converts any Python function into an agent tool in one line. The 8-pillar architecture (Agents, Tools, Handoffs, Patterns, Turns, Tracing, Guardrails, HITL) provides a formal taxonomy for agent system design. The **LLM Council** — where multiple models independently answer, rank each other, then a chairman synthesizes — is a novel approach to reducing hallucinations. CAI supports **300+ models via LiteLLM** and has the most mature Ollama integration. The four-layer guardrail system (pattern matching, Unicode analysis, AI-powered detection, command filtering) addresses prompt injection. Unfortunately, **Alias Robotics licenses `src/cai` components as non-commercial research-only** — you cannot use this code in a freemium product without paying €350/month for CAI PRO.

**PentAGI's Docker sandbox is the most sophisticated.** It runs ephemeral containers from a purpose-built `vxcontrol/kali-linux` image with **200+ CLI tools**, automatically selecting between Debian and Kali images based on task type. The worker node architecture supports distributed and air-gapped execution with TLS-secured Docker API access, dynamic port allocation (28000-30000) for out-of-band techniques, and Docker-in-Docker for nested operations. The **reflector pattern** — automatically redirecting agents from text responses back to tool calls — solves a common failure mode. PentAGI persists everything to **PostgreSQL with pgvector** for semantic search, plus an optional **Neo4j knowledge graph** via Graphiti. The catch: it is written in Go with a custom LangChainGo fork, making component extraction into a Python project non-trivial. The MIT license also has an exception: VXControl Cloud SDK components fall under AGPL-3.0 for forks.

**MAPTA's validation architecture solves the false-positive problem.** Its three-role design — Coordinator (strategy), Sandbox Agents (execution), Validation Agent (PoC verification) — enforces that every finding must be proven exploitable by concrete execution before reporting. This "proof-by-exploitation" methodology achieved **76.9% on XBOW at a median cost of $0.073 per challenge** — extraordinarily cost-efficient. The paper (arXiv:2508.20816) is the most detailed public description of multi-agent pentesting coordination. The codebase itself is minimal (2 files, 2 commits), but the architecture is MIT-licensed and well-documented enough to reimplement. The early-stopping insight — that ~40 tool calls or $0.30 predicts success/failure — is directly applicable to cost management.

---

## License compatibility narrows the field dramatically

Your requirement for MIT or Apache 2.0 eliminates several major players:

- **CAI**: Non-commercial research license on core `src/cai` components. Commercial use requires €350/month license from Alias Robotics. **Eliminated.**
- **Shannon**: AGPL-3.0 requires all derivative works to be open-sourced under AGPL. Incompatible with a freemium model where you may want proprietary server-side components. **Eliminated.**
- **PentAGI**: Core is MIT but VXControl Cloud SDK integration falls under AGPL-3.0 for forks. You could use the MIT-licensed portions, but the cloud integration (which enables the commercial features) cannot be freely forked. **Partially eliminated.**

The remaining license-compatible projects with significant traction are **Strix** (Apache 2.0, 20.5k stars), **PentestGPT** (MIT, 12k stars), **HexStrike AI** (MIT, 7.1k stars), **hackingBuddyGPT** (MIT, 951 stars), **RedAmon** (MIT, 1.3k stars), and **PentestAgent GH05TCREW** (MIT, 532 stars).

---

## Benchmark performance reveals what actually works

Three projects publish rigorous benchmark data against the **XBOW 104-challenge web security benchmark**, providing the clearest comparison of autonomous pentesting capability:

| Project | XBOW Score | Median Cost/Challenge | Median Time | Model Used |
|---------|-----------|----------------------|-------------|------------|
| **Shannon** | 96.15% (100/104) | ~$50 total run | 1-1.5 hours | Claude Sonnet 4.5 |
| **PentestGPT** | 86.5% (90/104) | $0.42 median | 3.3 min median | Claude Code |
| **MAPTA** | 76.9% (80/104) | $0.073 median | 96.1s median | GPT-5 |
| **Cyber-AutoAgent** | 85% (archived) | Not published | Not published | AWS Bedrock |

Shannon dominates on accuracy but requires source code access (white-box only) and costs ~$50 per run with Claude 4.5. PentestGPT achieves strong results at reasonable cost. MAPTA is remarkably cost-efficient but only tested with GPT-5. These benchmarks reveal that **model quality matters more than agent architecture** — all three use fundamentally different designs but achieve broadly similar results.

---

## The MCP ecosystem is an emerging force multiplier

Three projects in the ecosystem specifically provide **Model Context Protocol (MCP) servers** for pentesting — these are tool bridges, not agents, and they can plug into any MCP-compatible agent:

**HexStrike AI** (7.1k stars, MIT) wraps **150+ security tools** as MCP-callable functions across network, web, binary, cloud, and forensics categories. It is now available via `sudo apt install hexstrike-ai` in Kali Linux. The architecture is a Flask API backend with a FastMCP protocol adapter. The critical limitation: **no sandboxing** — tools execute directly on the host. Check Point researchers documented threat actors using HexStrike to exploit zero-day CVEs.

**pentestMCP** exposes 20+ tools (Nmap, Nuclei, ZAP, SQLMap, Gobuster) with async scan patterns and semaphore-based concurrency control, all running in Docker. **burp-ai-agent** bridges AI into Burp Suite with 53 MCP tools, 62 vulnerability classes, and three privacy redaction modes.

For your architecture, **MCP compatibility should be a first-class feature**. It allows your agent to leverage HexStrike's 150+ tool wrappers, pentestMCP's Docker-containerized tools, or Burp Suite integration without writing custom integrations. CAI, PentestAgent, RedAmon, and Decepticon all already support MCP client connections.

---

## Emerging projects to watch

**RedAmon** (1.3k stars, MIT, February 2026) is the most interesting newcomer. It uses **LangGraph-based ReACT** with a **Neo4j "EvoGraph"** for persistent cross-session knowledge — the only project with a true evolutionary knowledge system. Its 6-phase scanning pipeline runs end-to-end with a CypherFix triage agent and can auto-generate GitHub PRs with vulnerability fixes. At just one month old with 107 commits, it is growing rapidly but unproven at scale.

**PentestAgent by GH05TCREW** (532 stars, MIT) is architecturally close to your planned design: Python, LiteLLM, Textual TUI, Docker with Kali, MCP client, single-agent and multi-agent crew modes, and a "Shadow Graph" knowledge graph built from session notes. It also has prebuilt attack playbooks and real-time token/memory tracking — features directly relevant to a freemium cost model.

**Decepticon by PurpleAILAB** implements "Vibe Hacking" — fully autonomous red teaming using LangGraph multi-agent systems with MCP tool loading and phase-based agent specialization in Kali Docker containers. Still experimental but architecturally clean.

---

## Fork versus build: the strategic recommendation

**Recommended approach: fork Strix as a starting point, then selectively integrate patterns from other projects.** Here is the reasoning:

Strix provides the strongest foundation because it matches your stack exactly (Python, LiteLLM, Docker/Kali sandbox, Textual TUI, Apache 2.0) and has the community momentum to attract contributors. Its `AbstractRuntime` interface allows swapping Docker for other execution backends. The agent graph coordination system is sophisticated yet modular enough to extend.

However, **Strix has gaps you will need to fill from other sources:**

- **Extensibility**: Adopt CAI's `@function_tool` decorator pattern (reimplemented, not copied — license incompatible). Also add MCP client support following PentestAgent's approach.
- **Database persistence**: Replace Strix's file-based state with PostgreSQL+pgvector following PentAGI's schema design. This enables semantic search over past findings and cross-session learning.
- **Validation agent**: Implement MAPTA's proof-by-exploitation pattern where a dedicated validation agent must reproduce every finding before it enters the report.
- **Cost management**: Integrate MAPTA's early-stopping thresholds (~40 tool calls / $0.30 budget cap) and CAI's `COST_TRACKER` pattern for real-time token monitoring.
- **Guardrails**: Reimplement CAI's four-layer prompt injection defense (pattern matching, Unicode analysis, AI detection, command filtering).
- **Reporting**: Add structured output formats. No project does this well — SARIF, JSON, PDF, and HTML reporting is a gap across the entire ecosystem.

**Building from scratch is justified only if** Strix's agent graph architecture fundamentally conflicts with your ReAct loop preference. Strix uses a custom coordination graph (not pure ReAct), though it could be adapted. If you need a strict ReAct implementation, consider forking **PentestAgent GH05TCREW** instead — it is smaller (532 stars) but uses LiteLLM, Textual, Docker, and MCP with a cleaner single-agent ReAct baseline that would be easier to extend.

The one scenario where building from scratch wins: if you want a **LangGraph-based architecture** for native support of complex agent topologies, conditional branching, and persistence. RedAmon proves this approach works for pentesting, and LangGraph's ecosystem is maturing quickly. But you would sacrifice Strix's 20k-star community.

---

## Conclusion

The AI pentesting agent landscape has exploded in 2025-2026, with **Strix, Shannon, CAI, PentestGPT, and HexStrike AI** leading in community adoption. Your planned architecture (Python, LiteLLM, Docker sandbox, ReAct, Textual TUI, freemium) directly mirrors Strix's design — making it the optimal fork target. The critical insight from this analysis is that **no single project excels at everything**: Strix has the best developer experience and community, CAI has the best extensibility and model support, PentAGI has the best sandbox isolation, Shannon has the best benchmark scores, and MAPTA has the best validation methodology. A winning strategy combines Strix's foundation with selective architectural patterns from across the ecosystem, filling the universal gaps in structured reporting, database persistence, and cost management that no current project adequately addresses.