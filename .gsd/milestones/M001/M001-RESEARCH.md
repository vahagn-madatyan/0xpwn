# M001: Core Engine — Research

**Completed:** 2026-03-12

## Landscape Analysis

Reviewed 20+ open-source AI pentesting agents. Key findings:

### Top References

| Project | Stars | License | Key Pattern | Relevance |
|---|---|---|---|---|
| Strix | 20.5K | Apache 2.0 | Multi-agent graph, Docker/Kali, Textual TUI, thinking block chaining | Primary reference — borrowing patterns, not forking |
| Shannon | — | AGPL | Multi-agent, agentic | Architecture patterns |
| PentestGPT | — | MIT | GPT-guided pentesting | UX reference |
| CAI | — | Non-commercial | Computer-Aided Intelligence | Validation approach |
| MAPTA | — | — | Multi-agent pentest, PoC validation | Validation agent concept |
| HexStrike AI | — | MIT | 150+ MCP tools | Tool ecosystem reference |
| PentAGI | — | — | Multi-agent orchestration | Agent coordination patterns |

### Key Patterns Identified

1. **ReAct loop** — most successful agents use Reason-Act-Observe cycles, not chain-of-thought
2. **Docker isolation** — all serious tools sandbox execution; Kali-based images are standard
3. **Tool grounding** — agents that call real tools (nmap, nuclei) outperform prompt-only approaches
4. **Multi-agent coordination** — Planner/Executor/Validator separation improves reliability
5. **Stuck detection** — Strix implements loop detection + re-planning; critical for autonomous operation
6. **Thinking block chaining** — Strix chains Claude's extended thinking across turns for continuity

### Anti-Patterns to Avoid

1. Wrapper-only tools (just send prompts to GPT, no tool execution)
2. Single-model dependency (no provider lock-in)
3. No sandbox (running tools on host)
4. No output parsing (passing raw text to LLM without structure)

## Technology Validation

### LiteLLM

- **async completion:** `acompletion()` — fully async, required for streaming
- **tool calling:** standard OpenAI format, works across providers
- **cost tracking:** `completion_cost()` per-call, `BudgetManager` for caps
- **provider coverage:** 100+ providers including Ollama for local inference
- **verdict:** confirmed as the right abstraction layer

### Docker SDK (docker-py)

- **container lifecycle:** create → start → exec_run → stop → remove
- **exec_run:** supports streaming, demux (separate stdout/stderr), working directory
- **networking:** create_networking_config for custom networks, endpoint config for IPs/aliases
- **capabilities:** NET_ADMIN, NET_RAW available via host_config
- **verdict:** sufficient for sandbox requirements

### Textual (M004, scouted early)

- **trust score:** 9.4/10
- **capabilities:** full TUI framework with CSS styling, async, widgets
- **verdict:** confirmed for M004 TUI dashboard

## SARIF Research

- GitHub Security tab accepts SARIF 2.1.0 format
- `upload-sarif` GitHub Action for CI integration
- `security-severity` property maps to CVSS for GitHub severity display
- Python SARIF libraries available for generation

## Compliance Research (PCI DSS 4.0)

- PCI DSS 4.0 fully effective 2025
- Requirement 11.4 covers penetration testing requirements
- Required report elements: scope, methodology, vulnerability list, risk assessment, remediation recommendations, retest outcomes
- Relevant for M003 report generation and M004 compliance mapping

## NVD/CVE API

- Endpoint: api.nvd.nist.gov/rest/json/cves/2.0
- Free tier: 5 requests per 30 seconds (no API key), 50/30s with key
- Returns: CVE ID, CVSS v3.1 scores, CWE classification, references, description
- Strategy: local SQLite cache, batch lookups, rate limiting

## Strix Gap Analysis Summary

### Features to Borrow (with adaptation)

| Feature | Strix Status | 0xpwn Approach | Effort |
|---|---|---|---|
| Multi-agent coordination | Graph-based | Simplified Planner/Executor/Perceptor | M |
| Docker/Kali sandbox | Full implementation | Similar, custom image | M |
| Thinking block chaining | Claude-specific | Provider-agnostic reasoning chain | S |
| Sub-agent spawning | Supported | Phase-based sub-agents | M |
| Textual TUI | Full dashboard | Defer to M004 | — |

### Key Gaps (0xpwn innovations)

| Gap | Impact | Milestone |
|---|---|---|
| Tiered permission model | Safety for real targets | M002 |
| Validation agent (PoC verify) | Zero false positives | M003 |
| Freemium gating | Revenue model | M004 |
| Multi-model routing by phase | Cost optimization | M004 |
| Compliance mapping | Enterprise sales | M004 |
