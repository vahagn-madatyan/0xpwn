# Requirements

This file is the explicit capability and coverage contract for 0xpwn.

## Active

### R001 — Autonomous 5-phase pentesting pipeline
- Class: core-capability
- Status: active
- Description: Agent executes Recon → Scanning → Exploitation → Validation → Reporting phases autonomously with a ReAct reasoning loop
- Why it matters: This is the core product — without autonomous multi-phase execution, it's just a tool wrapper
- Source: user
- Primary owning slice: M001/S03
- Supporting slices: M001/S04, M001/S08
- Validation: unmapped
- Notes: Must handle phase transitions, state accumulation, and re-planning on failure

### R002 — Isolated Docker/Kali sandbox execution
- Class: core-capability
- Status: active
- Description: All security tools run inside a Docker container with a custom Kali-based image, isolated from the host system
- Why it matters: Safety — pentesting tools must never run on the host. Reproducibility — consistent tool versions across environments
- Source: user
- Primary owning slice: M001/S02
- Supporting slices: M001/S08
- Validation: unmapped
- Notes: Container gets NET_ADMIN/NET_RAW capabilities, published to ghcr.io/0xpwn/sandbox

### R003 — Provider-agnostic LLM support (100+ via LiteLLM)
- Class: core-capability
- Status: active
- Description: Any LiteLLM-supported model works — OpenAI, Anthropic, Ollama (local), Bedrock, VertexAI, etc. with async completion and tool calling
- Why it matters: Users bring their own keys; local-only users need Ollama support with zero cloud dependency
- Source: user
- Primary owning slice: M001/S01
- Supporting slices: M001/S06
- Validation: unmapped
- Notes: Cost tracking via LiteLLM's completion_cost(), async via acompletion()

### R004 — Real-time agent reasoning stream
- Class: primary-user-loop
- Status: active
- Description: Agent's thinking, tool selection, raw tool output, and parsed results stream to terminal in real-time with visible phase transitions
- Why it matters: Bug bounty hunters identified "watching the AI operate" as the key selling moment — transparency builds trust and is the hook
- Source: user
- Primary owning slice: M001/S05
- Supporting slices: M001/S08
- Validation: unmapped
- Notes: Rich-based terminal output with color-coded phases, thinking blocks, and tool results

### R005 — First-run guided model setup wizard
- Class: launchability
- Status: active
- Description: Interactive wizard on first run detects available models, guides API key setup or Ollama configuration, persists to YAML config
- Why it matters: Zero-friction onboarding — user should go from `pip install` to first scan in under 2 minutes
- Source: user
- Primary owning slice: M001/S06
- Supporting slices: none
- Validation: unmapped
- Notes: Adaptive flow: "Have an API key? → configure. No? → set up Ollama."

### R006 — CVE/NVD enrichment for findings
- Class: differentiator
- Status: active
- Description: Findings are enriched with CVE IDs, CVSS scores, CWE classification, and remediation guidance from NVD
- Why it matters: Raw tool output isn't enough for bug bounty reports — enriched findings save report-writing time
- Source: user
- Primary owning slice: M001/S07
- Supporting slices: none
- Validation: unmapped
- Notes: NVD API (api.nvd.nist.gov) is free but rate-limited; cache responses locally

### R007 — Tiered permission model (auto/prompt/always-ask)
- Class: compliance/security
- Status: active
- Description: Tools are categorized by risk: recon tools auto-approve, scanning tools prompt once, exploitation tools always require confirmation
- Why it matters: Prevents accidental damage to production systems; required for professional use
- Source: user
- Primary owning slice: M002/S01
- Supporting slices: none
- Validation: unmapped
- Notes: Inspired by Strix gap analysis — Strix lacks this entirely

### R008 — Budget controls with early-stopping
- Class: differentiator
- Status: active
- Description: Track token usage and cost per scan; enforce budget caps; stop scan gracefully when budget is exhausted
- Why it matters: Bug bounty economics — users need to know a scan costs $0.47, not $47
- Source: user/research
- Primary owning slice: M002/S02
- Supporting slices: none
- Validation: unmapped
- Notes: LiteLLM BudgetManager provides the primitives

### R009 — Scope enforcement (block out-of-scope targets)
- Class: compliance/security
- Status: active
- Description: User defines scope (domains, IPs, CIDR ranges); agent refuses to scan anything outside scope
- Why it matters: Legal liability — scanning out-of-scope targets can be criminal
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: none
- Validation: unmapped
- Notes: Must be enforced at the sandbox/tool level, not just LLM instruction

### R010 — Session persistence and resume (SQLite)
- Class: continuity
- Status: active
- Description: Scan state persists to SQLite; interrupted scans can be resumed from last checkpoint
- Why it matters: Long scans (30+ minutes) should survive disconnects and crashes
- Source: user
- Primary owning slice: M002/S04
- Supporting slices: none
- Validation: unmapped
- Notes: none

### R011 — Event-sourced audit log
- Class: compliance/security
- Status: active
- Description: Every agent action, tool invocation, and decision is logged immutably with timestamps
- Why it matters: Professional pentesters need audit trails for client deliverables and legal protection
- Source: user
- Primary owning slice: M002/S05
- Supporting slices: none
- Validation: unmapped
- Notes: Append-only log, queryable for report generation

### R012 — Independent PoC validation agent
- Class: differentiator
- Status: active
- Description: Separate validation agent independently re-exploits findings to confirm they're real, not false positives
- Why it matters: Zero false positives claim — the key differentiator vs every other tool
- Source: user/research
- Primary owning slice: M003/S01
- Supporting slices: none
- Validation: unmapped
- Notes: MAPTA-inspired approach; ARTEMIS achieved 82% valid submission rate

### R013 — Multi-format reporting (JSON/SARIF/MD/HTML/PDF)
- Class: primary-user-loop
- Status: active
- Description: Generate reports in JSON (machine), SARIF 2.1.0 (GitHub Security), Markdown (free), HTML + PDF (pro tier)
- Why it matters: Different consumers need different formats — CI/CD needs SARIF, clients need PDF
- Source: user
- Primary owning slice: M003/S02
- Supporting slices: M003/S03
- Validation: unmapped
- Notes: SARIF must be valid for GitHub upload-sarif action; HTML/PDF gated to pro tier

### R014 — Finding deduplication (LLM-based)
- Class: quality-attribute
- Status: active
- Description: LLM-powered deduplication to collapse duplicate/overlapping findings into single entries
- Why it matters: Multiple tools often find the same vulnerability — duplicates waste reviewer time
- Source: research
- Primary owning slice: M003/S04
- Supporting slices: none
- Validation: unmapped
- Notes: none

### R015 — MCP protocol support (server + client)
- Class: integration
- Status: active
- Description: Expose 0xpwn tools as MCP server; consume external MCP tool servers (e.g., HexStrike's 150+ tools)
- Why it matters: Ecosystem integration — other AI agents can use 0xpwn, and 0xpwn can use other tool servers
- Source: user
- Primary owning slice: M004/S01
- Supporting slices: none
- Validation: unmapped
- Notes: none

### R016 — Plugin system (@tool decorator)
- Class: integration
- Status: active
- Description: Users extend 0xpwn by writing Python functions with @tool decorator that auto-register as agent capabilities
- Why it matters: Extensibility without forking — community-contributed tools
- Source: user
- Primary owning slice: M004/S02
- Supporting slices: none
- Validation: unmapped
- Notes: none

### R017 — REST API server mode (FastAPI)
- Class: integration
- Status: active
- Description: Run 0xpwn as a FastAPI server with REST API + WebSocket for programmatic access
- Why it matters: Enables integration into security orchestration platforms and custom workflows
- Source: user
- Primary owning slice: M004/S03
- Supporting slices: none
- Validation: unmapped
- Notes: none

### R018 — Textual TUI dashboard
- Class: primary-user-loop
- Status: active
- Description: Interactive terminal dashboard (Textual) showing agent state, findings, tool output, and scan controls
- Why it matters: Power users want a persistent dashboard, not just streaming output
- Source: user
- Primary owning slice: M004/S04
- Supporting slices: none
- Validation: unmapped
- Notes: none

### R019 — Compliance framework mapping (PCI/DORA/NIS2/SOC2)
- Class: compliance/security
- Status: active
- Description: Map findings to compliance framework requirements (PCI DSS 4.0, DORA, NIS2, SOC 2)
- Why it matters: Corporate pentesters need compliance evidence for audit reports
- Source: user
- Primary owning slice: M004/S05
- Supporting slices: none
- Validation: unmapped
- Notes: PCI DSS 4.0 Req 11.4 specifically requires pentest methodology documentation

### R020 — Freemium feature gating
- Class: constraint
- Status: active
- Description: Feature flags enforce Free/Pro ($49/mo)/Enterprise tier boundaries
- Why it matters: Business model — free tier drives adoption, pro tier drives revenue
- Source: user
- Primary owning slice: M004/S06
- Supporting slices: none
- Validation: unmapped
- Notes: Free: 3 scans/day, MD reports. Pro: unlimited, HTML/PDF, compliance mapping

### R021 — Full 25+ tool suite
- Class: core-capability
- Status: active
- Description: Support all 25+ security tools in the sandbox image (sqlmap, gobuster, nikto, whatweb, wapiti, etc.)
- Why it matters: Comprehensive coverage — different tools find different vulnerability classes
- Source: user
- Primary owning slice: M004/S07
- Supporting slices: none
- Validation: unmapped
- Notes: M001 ships with 5 core tools; M004 expands to full suite

### R022 — Multi-model orchestration (route by phase)
- Class: differentiator
- Status: active
- Description: Route different phases to different models — cheap model for recon, strong model for exploitation reasoning
- Why it matters: Cost optimization — not every phase needs GPT-4 quality
- Source: user
- Primary owning slice: M004/S08
- Supporting slices: none
- Validation: unmapped
- Notes: none

### R023 — GitHub Actions CI/CD integration
- Class: integration
- Status: active
- Description: GitHub Action that runs 0xpwn in CI, uploads SARIF to Security tab, fails build on critical findings
- Why it matters: Shift-left security — catch vulns before merge
- Source: user
- Primary owning slice: M004/S09
- Supporting slices: none
- Validation: unmapped
- Notes: none

### R024 — Stuck detection and recovery
- Class: quality-attribute
- Status: active
- Description: Agent detects when it's looping or making no progress, triggers re-planning or escalation
- Why it matters: Autonomous agents get stuck — without detection, scans hang indefinitely burning budget
- Source: research
- Primary owning slice: M002/S06
- Supporting slices: none
- Validation: unmapped
- Notes: Strix implements this; pattern from research survey

## Validated

(none yet)

## Deferred

### R025 — Cloud-hosted sessions (ECS/Fargate)
- Class: operability
- Status: deferred
- Description: Run sandbox containers on AWS ECS/Fargate for cloud-hosted scanning
- Why it matters: Removes Docker requirement for end users; enables SaaS model
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Deferred to M005 — requires significant infra work

### R026 — Temporal workflow orchestration
- Class: operability
- Status: deferred
- Description: Use Temporal for reliable, resumable, distributed scan orchestration
- Why it matters: Cloud scans need durable execution guarantees
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Deferred to M005

### R027 — PostgreSQL + pgvector cloud persistence
- Class: operability
- Status: deferred
- Description: Replace SQLite with PostgreSQL for multi-tenant cloud deployments; pgvector for semantic search
- Why it matters: SQLite doesn't scale to concurrent cloud workloads
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Deferred to M005

### R028 — Team RBAC + SSO (SAML/OIDC)
- Class: admin/support
- Status: deferred
- Description: Role-based access control and single sign-on for enterprise teams
- Why it matters: Enterprise sales requirement
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Deferred to M005

### R029 — Web dashboard
- Class: primary-user-loop
- Status: deferred
- Description: Browser-based dashboard for scan management, findings review, and team collaboration
- Why it matters: Not everyone wants a terminal — web UI broadens the market
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Deferred to M005

### R030 — Knowledge graph (Neo4j)
- Class: differentiator
- Status: deferred
- Description: Graph database for mapping relationships between hosts, services, vulnerabilities, and attack paths
- Why it matters: Enables attack path visualization and cross-scan intelligence
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Deferred to M005+

### R031 — Post-exploitation modules
- Class: core-capability
- Status: deferred
- Description: Privilege escalation, lateral movement, data exfiltration modules
- Why it matters: Full pentest lifecycle — finding a vuln is step 1, demonstrating impact is step 2
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Deferred to M006+ — significant scope and safety concerns

### R032 — AD/internal network pentesting
- Class: core-capability
- Status: deferred
- Description: Active Directory enumeration, Kerberos attacks, internal network scanning
- Why it matters: Enterprise pentests are primarily internal/AD focused
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Deferred to M006+

### R033 — Cloud infra pentesting (AWS/GCP/Azure)
- Class: core-capability
- Status: deferred
- Description: Cloud misconfiguration scanning, IAM analysis, storage bucket enumeration
- Why it matters: Cloud is the dominant deployment model — misconfigs are the #1 finding
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Deferred to M006+

## Out of Scope

### R034 — Mobile app testing
- Class: anti-feature
- Status: out-of-scope
- Description: iOS/Android app security testing (binary analysis, API interception)
- Why it matters: Prevents scope creep — mobile testing is a fundamentally different toolchain
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Different tools, different sandbox requirements

### R035 — Social engineering
- Class: anti-feature
- Status: out-of-scope
- Description: Phishing, pretexting, or any social engineering attack simulation
- Why it matters: Ethical and legal concerns; not a technical assessment
- Source: inferred
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Out of scope for all milestones

### R036 — Business logic testing
- Class: constraint
- Status: out-of-scope
- Description: Application-specific business logic vulnerability testing (price manipulation, workflow bypass)
- Why it matters: Requires domain knowledge the agent can't have — manual pentest territory
- Source: inferred
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Agent can find technical vulns but not business logic flaws

### R037 — Physical security testing
- Class: anti-feature
- Status: out-of-scope
- Description: Physical access testing, badge cloning, lock picking
- Why it matters: Obviously not software
- Source: inferred
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: none

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| R001 | core-capability | active | M001/S03 | M001/S04, M001/S08 | unmapped |
| R002 | core-capability | active | M001/S02 | M001/S08 | unmapped |
| R003 | core-capability | active | M001/S01 | M001/S06 | unmapped |
| R004 | primary-user-loop | active | M001/S05 | M001/S08 | unmapped |
| R005 | launchability | active | M001/S06 | none | unmapped |
| R006 | differentiator | active | M001/S07 | none | unmapped |
| R007 | compliance/security | active | M002/S01 | none | unmapped |
| R008 | differentiator | active | M002/S02 | none | unmapped |
| R009 | compliance/security | active | M002/S03 | none | unmapped |
| R010 | continuity | active | M002/S04 | none | unmapped |
| R011 | compliance/security | active | M002/S05 | none | unmapped |
| R012 | differentiator | active | M003/S01 | none | unmapped |
| R013 | primary-user-loop | active | M003/S02 | M003/S03 | unmapped |
| R014 | quality-attribute | active | M003/S04 | none | unmapped |
| R015 | integration | active | M004/S01 | none | unmapped |
| R016 | integration | active | M004/S02 | none | unmapped |
| R017 | integration | active | M004/S03 | none | unmapped |
| R018 | primary-user-loop | active | M004/S04 | none | unmapped |
| R019 | compliance/security | active | M004/S05 | none | unmapped |
| R020 | constraint | active | M004/S06 | none | unmapped |
| R021 | core-capability | active | M004/S07 | none | unmapped |
| R022 | differentiator | active | M004/S08 | none | unmapped |
| R023 | integration | active | M004/S09 | none | unmapped |
| R024 | quality-attribute | active | M002/S06 | none | unmapped |
| R025 | operability | deferred | none | none | unmapped |
| R026 | operability | deferred | none | none | unmapped |
| R027 | operability | deferred | none | none | unmapped |
| R028 | admin/support | deferred | none | none | unmapped |
| R029 | primary-user-loop | deferred | none | none | unmapped |
| R030 | differentiator | deferred | none | none | unmapped |
| R031 | core-capability | deferred | none | none | unmapped |
| R032 | core-capability | deferred | none | none | unmapped |
| R033 | core-capability | deferred | none | none | unmapped |
| R034 | anti-feature | out-of-scope | none | none | n/a |
| R035 | anti-feature | out-of-scope | none | none | n/a |
| R036 | constraint | out-of-scope | none | none | n/a |
| R037 | anti-feature | out-of-scope | none | none | n/a |

## Coverage Summary

- Active requirements: 24
- Mapped to slices: 24
- Validated: 0
- Unmapped active requirements: 0
