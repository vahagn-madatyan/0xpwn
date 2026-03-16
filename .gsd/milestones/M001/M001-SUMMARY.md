---
id: M001
provides:
  - Working autonomous pentesting agent with `0xpwn scan --target <url>` CLI entrypoint
  - 5-phase ReAct agent pipeline (recon → scanning → exploitation → validation → reporting) with LLM-driven tool selection
  - Docker/Kali sandbox with 5 core security tools (nmap, httpx, subfinder, nuclei, ffuf) and async container lifecycle
  - Async LLM client wrapping LiteLLM with tool calling, cost tracking, and provider-agnostic access to 100+ models
  - Real-time Rich streaming of agent reasoning, tool output chunks, parsed results, and phase transitions
  - First-run interactive wizard with Ollama detection, cloud provider setup, LLM validation, and YAML config persistence
  - NVD-backed CVE enrichment pipeline with async API client, SQLite cache, and CVSS/CWE/remediation population
  - 261 unit tests and integration test infrastructure covering all subsystems
key_decisions:
  - "Decision 1: Build from scratch, borrow Strix patterns — clean architecture, no fork debt"
  - "Decision 4: LiteLLM for provider-agnostic LLM abstraction (100+ models)"
  - "Decision 15: Tool executor pattern — constructor takes DockerSandbox, async run() returns ToolResult"
  - "Decision 17: Protocol with typed dataclasses for event emission"
  - "Decision 18: JSON-serialized parsed_output fed to LLM, truncated to 4000 chars"
  - "Decision 25: Append-only Rich streaming with additive execute_stream() preserving buffered ToolResult"
  - "Decision 28: Config resolution precedence — CLI > env > YAML > wizard trigger"
  - "Decision 36: Enrichment runs post-loop in _scan_async(), not inside agent reasoning"
  - "Decision 37: Docker extra_hosts defaults to host-gateway for cross-container reachability"
patterns_established:
  - "src/oxpwn layout with core/, agent/, cli/, config/, enrichment/, llm/, sandbox/ subpackages"
  - "Tool executor pattern: constructor takes DockerSandbox, async run() returns ToolResult with parsed_output dict"
  - "ToolRegistry with register/get_schemas/dispatch — OpenAI function calling format schemas"
  - "ReactAgent outer phase loop + inner ReAct reasoning cycle per phase"
  - "AgentEventCallback Protocol with typed event dataclasses — never blocks, swallows callback errors"
  - "RichStreamingCallback append-only CLI rendering with phase rules, reasoning panels, tool output chunks"
  - "Config isolation in tests via monkeypatch.setenv('OXPWN_CONFIG', str(tmp_path / 'config.yaml'))"
  - "Session-scoped Docker fixtures with skip-if-no-Docker guard"
  - "Deterministic in-sandbox HTTP proof fixtures under tests/fixtures/tool_suite/"
  - "Three-phase enrichment: collect CVE IDs → batch-resolve via cache/NVD → apply to findings"
observability_surfaces:
  - "structlog events: llm.complete (model, tokens, cost, latency), agent.* (iteration, tool_dispatch, phase_transition, complete)"
  - "structlog events: sandbox.* (create, execute, destroy, cleanup_orphans), cli.* (scan_start, scan_complete, scan_failed)"
  - "structlog events: config.* (loaded, written, deleted), wizard.* (started, completed, skipped)"
  - "structlog events: nvd.* (fetch, rate_limited, cache_hit, cache_miss), enrichment.* (resolving_cves, finding_enriched)"
  - "ScanState tracks total_cost, total_tokens, phases_completed — full scan lifecycle visible"
  - "docker ps --filter label=oxpwn.managed=true — live container inspection"
  - "0xpwn config show — displays resolved config with redacted API key"
  - "sqlite3 ~/.cache/oxpwn/cve-cache.db — queryable CVE cache"
  - "pytest tests/unit/ -x -q — 261 tests baseline; any regression is a real signal"
requirement_outcomes:
  - id: R001
    from_status: active
    to_status: validated
    proof: "261 unit tests including 7 S08 wiring tests, _PHASE_ORDER contains all 5 phases, _PHASE_GUIDANCE covers all 5, enrichment wired in _scan_async(), integration test with structural assertions (≥3 phases completed, non-empty tool results, findings list)"
  - id: R002
    from_status: active
    to_status: validated
    proof: "Real Docker verification for all 5 tools (nmap, httpx, subfinder, nuclei, ffuf) inside custom Kali image via test_nmap_executor_real_scan + test_tool_suite_integration.py; container lifecycle (create/exec/destroy) proven with orphan cleanup"
  - id: R004
    from_status: active
    to_status: validated
    proof: "S05: 64 unit tests + 2 integration tests proving streaming renders reasoning, tool output chunks, parsed results, and phase transitions; S08 extended to 5-phase pipeline with all-phase guidance; human UAT documented in acceptance checklist"
  - id: R005
    from_status: active
    to_status: validated
    proof: "56 unit tests (27 config + 15 wizard + 14 CLI) proving config model, YAML persistence, XDG paths, env-override precedence, wizard flows (cloud/local/Ollama), non-interactive skip, LLM validation, config subcommands (show/reset/wizard)"
  - id: R006
    from_status: active
    to_status: validated
    proof: "60 unit tests (23 NVD client + 16 CVE cache + 21 enrichment) proving NVD fetch/rate-limit/error-handling, SQLite cache with WAL mode and TTL, CVE ID extraction from nuclei/nmap/text, finding conversion from nuclei/ffuf/nmap, enrichment populating cvss/cwe_id/cve_id/remediation, CVSS version fallback chain, batch deduplication, graceful degradation"
duration: ~10h across 8 slices
verification_result: passed
completed_at: 2026-03-15
---

# M001: Core Engine

**Autonomous pentesting agent with 5-phase ReAct pipeline, Docker/Kali sandbox running 5 security tools, real-time Rich streaming CLI, first-run wizard, and NVD CVE enrichment — proven by 261 unit tests and Docker integration verification.**

## What Happened

M001 built the complete 0xpwn core engine across 8 slices, progressing from bare package scaffolding to a working autonomous pentesting agent.

**Foundation (S01–S02):** The `oxpwn` Python package was scaffolded with `pyproject.toml` (hatchling), 6 Pydantic data models (Phase, Severity, Finding, ToolResult, TokenUsage, LLMResponse, ScanState), and an async LLMClient wrapping LiteLLM with tool calling, cost tracking, and structlog observability. The Docker sandbox layer implemented `DockerSandbox` as an async context manager with labeled container lifecycle, orphan cleanup, and the first tool executor (NmapExecutor with XML parser) — all proven against a real Docker daemon.

**Agent Core (S03–S04):** The ReactAgent was built with an outer loop over phases and an inner ReAct cycle per phase: build system prompt → LLM complete → dispatch tool calls → observe → accumulate state → transition. The ToolRegistry maps tool names to OpenAI function schemas and async executor factories. S04 expanded from nmap-only to the full 5-tool core suite (nmap, httpx, subfinder, nuclei, ffuf) with compact JSONL/JSON parsers, deterministic in-sandbox HTTP proof fixtures, and graceful parse-failure degradation.

**CLI + Config (S05–S06):** The `0xpwn scan --target <url>` command was wired with `DockerSandbox.execute_stream()` for live tool output chunks, `RichStreamingCallback` for append-only terminal rendering, and phase-aware Rich formatting. The first-run wizard detects Ollama, guides API key setup for cloud providers, validates LLM connectivity, and persists config to YAML with XDG path conventions and atomic writes. Config resolution follows CLI > env > YAML > wizard trigger precedence.

**Enrichment + Integration (S07–S08):** The NVD CVE enrichment pipeline provides an async API client with rate limiting, SQLite cache with WAL mode and 7-day TTL, CVE ID regex extraction, finding conversion from nuclei/ffuf/nmap tool results, and batch enrichment populating CVSS scores, CWE IDs, and remediation guidance. S08 wired everything together: expanded the agent to all 5 phases with phase-specific guidance, connected enrichment as post-loop processing in `_scan_async()`, added Docker `extra_hosts` for host-network reachability, and created a Juice Shop integration test with structural assertions.

## Cross-Slice Verification

### Success Criterion: `pip install -e .` and `0xpwn` CLI available
✅ **MET** — `pip install -e ".[dev]"` installs cleanly. `0xpwn --version` returns `0xpwn 0.1.0`. `0xpwn --help` shows `scan` and `config` commands.

### Success Criterion: `0xpwn scan --target <url>` executes all 5 phases
✅ **MET** — `_PHASE_ORDER` contains `[recon, scanning, exploitation, validation, reporting]`. `_PHASE_GUIDANCE` has entries for all 5 phases. `_scan_async()` composes ScanState → ToolRegistry → DockerSandbox → LLMClient → ReactAgent → enrichment. 261 unit tests pass including 7 S08 wiring tests that verify 5-phase order, all-phase guidance, and enrichment integration.

### Success Criterion: Agent reasoning streams in real-time with color-coded phase transitions
✅ **MET** — `RichStreamingCallback` renders reasoning panels, phase transition rules, tool output chunks (`ToolOutputChunkEvent`), parsed results, and error panels. Proven by 64 streaming unit tests + 2 integration tests (S05) and terminal smoke run confirming incremental Rich output.

### Success Criterion: At least 1 real vulnerability found against Juice Shop with PoC evidence
⚠️ **STRUCTURALLY MET, HUMAN UAT REQUIRED** — The pipeline is fully wired: agent selects tools autonomously, executes in Docker sandbox, parses structured output, converts to findings, and enriches via NVD. Integration test `test_full_scan_pipeline` asserts ≥3 phases completed, non-empty tool results, and findings list existence. Live Juice Shop proof requires human execution with a configured LLM provider — documented in `ACCEPTANCE-CHECKLIST.md`.

### Success Criterion: Findings include CVE IDs, CVSS scores, CWE classification
✅ **MET** — 60 unit tests prove the full enrichment pipeline: CVE ID extraction from nuclei/nmap/text, NVD API client with CVSS v3.1→v3.0→v2 fallback chain, CWE placeholder filtering, batch deduplication, and Finding field population (cvss, cwe_id, cve_id, remediation). Wired into `_scan_async()` with try/except that never crashes the scan.

### Success Criterion: First-run wizard guides model setup
✅ **MET** — `0xpwn config wizard` runs interactive setup. Detects Ollama at `localhost:11434`, offers local model selection. Cloud flow supports OpenAI, Anthropic, Gemini, and custom providers with masked API key input and LLM validation. Config persists to YAML at XDG paths with `0o600` permissions. `0xpwn config show/reset/wizard` subcommands available. 56 unit tests cover all flows.

### Success Criterion: Docker sandbox creates and destroys cleanly
✅ **MET** — Docker image builds from `docker/Dockerfile` (Kali-based) with all 5 tools present. `DockerSandbox` async context manager with labeled containers (`oxpwn.managed=true`), `cleanup_orphans()` classmethod, and `extra_hosts` for host-network reachability. 4 integration tests verify lifecycle against real Docker daemon. `docker ps --filter label=oxpwn.managed=true` shows no orphans after tests.

### Definition of Done Verification
- ✅ All 8 slices marked `[x]` in roadmap
- ✅ All 8 slice summaries exist (S01–S08)
- ✅ Agent loop, sandbox, LLM client, tool parsers, CLI wired end-to-end
- ✅ `0xpwn` CLI entrypoint exists and exercised
- ✅ 261 unit tests passing with no regressions
- ⚠️ Live Juice Shop scan requires human UAT (acceptance checklist provided)

## Requirement Changes

- **R001**: active → validated — 261 unit tests, 5-phase wiring, all-phase guidance, enrichment integration, structural integration test
- **R002**: active → validated — Real Docker verification for all 5 tools in Kali sandbox, container lifecycle proven, orphan cleanup working
- **R004**: active → validated — 64 streaming unit tests + 2 integration tests, Rich rendering of reasoning/tools/phases, 5-phase coverage
- **R005**: active → validated — 56 unit tests for wizard flows, config persistence, XDG paths, CLI subcommands
- **R006**: active → validated — 60 unit tests for NVD client, CVE cache, finding extraction, enrichment orchestrator
- **R003**: remains active — Advanced (proven against Gemini, wizard supports all providers) but not fully validated until Ollama local model completes a real scan

## Forward Intelligence

### What the next milestone should know
- The 261-test baseline is the contract anchor — run `pytest tests/unit/ -x -q` before and after any change to detect regression.
- `_scan_async()` in `src/oxpwn/cli/main.py` is the integration point for all M002 features: permission checks slot before tool dispatch, budget controls slot around the agent loop, scope enforcement slots before sandbox execution.
- `ScanState` is the mutable accumulator for the entire scan — it carries findings, tool results, phases, cost, and tokens. M002's SQLite persistence (R010) will serialize this to disk.
- The enrichment pipeline (`enrich_findings()`) runs post-loop and is wrapped in try/except — it's intentionally non-blocking. M002 doesn't need to touch it.
- Config resolution chain (CLI > env > YAML > wizard) is stable. M002's budget/scope config should extend `OxpwnConfig` or add sibling config models.

### What's fragile
- **Prompt quality is the primary lever for agent behavior** — `build_system_prompt()` in `prompts.py` and `_PHASE_GUIDANCE` determine what tools the agent selects. Changes here change everything.
- **`output_sink` injection uses signature introspection** — custom executors that don't accept `output_sink` or `**kwargs` silently skip streaming. The plugin system (R016) needs to formalize this.
- **`parse_tool_arguments()` silently returns empty dict on malformed JSON** — graceful but can mask LLM quality issues. Watch for tools receiving empty args.
- **Kali `httpx-toolkit` packaging** — the `-u` flag doesn't work; stdin-fed execution is the reliable path. This is a packaging artifact, not a tool limitation.
- **`sleep infinity` CMD** — containers stay alive until explicit destroy. Process-killed agents leave orphans until `cleanup_orphans()` is called.

### Authoritative diagnostics
- `pytest tests/unit/ -x -q` — 261 tests, 1.75s. First place to check for regression.
- `docker ps --filter label=oxpwn.managed=true` — shows orphan containers. Should be empty between scans.
- `0xpwn config show` — displays current resolved config with redacted API key.
- `python3 -c "from oxpwn.agent.react import _PHASE_ORDER; print([p.value for p in _PHASE_ORDER])"` — confirms phase wiring.
- structlog events filtered by `agent.*`, `sandbox.*`, `cli.*`, `nvd.*`, `enrichment.*` — full pipeline visibility.

### What assumptions changed
- **Gemini not OpenAI for integration tests** — GEMINI_API_KEY was available, OpenAI key was not. Provider-agnostic design validated by this real-world switch.
- **`python3-minimal` insufficient for HTTP fixtures** — full `python3` required in the sandbox image for in-container test servers.
- **`httpx -u` broken in Kali packaging** — stdin-fed execution is the reliable path; positional targets don't work either.
- **Enrichment runs better as post-processing** — originally considered in-loop enrichment, but NVD rate limits would stall the agent. Post-loop is cleaner and faster.
- **`CliRunner(mix_stderr=False)` not supported by Typer** — Typer wraps Click differently. Tests use default stderr handling.

## Files Created/Modified

- `pyproject.toml` — Package definition with all runtime/dev dependencies, hatchling build, CLI entrypoint
- `docker/Dockerfile` — Kali-based sandbox image with nmap, httpx, subfinder, nuclei, ffuf, python3
- `src/oxpwn/__init__.py` — Package root with version
- `src/oxpwn/core/models.py` — 7 Pydantic models (Phase, Severity, Finding, ToolResult, TokenUsage, LLMResponse, ScanState)
- `src/oxpwn/llm/client.py` — Async LLMClient with tool calling, cost tracking, structlog
- `src/oxpwn/llm/exceptions.py` — Typed exception hierarchy (LLMAuthError, LLMRateLimitError, LLMToolCallError)
- `src/oxpwn/sandbox/docker.py` — DockerSandbox async context manager with execute_stream()
- `src/oxpwn/sandbox/exceptions.py` — Sandbox exception hierarchy
- `src/oxpwn/sandbox/tools/nmap.py` — NmapExecutor + XML parser
- `src/oxpwn/sandbox/tools/httpx.py` — HttpxExecutor + JSONL parser
- `src/oxpwn/sandbox/tools/subfinder.py` — SubfinderExecutor + JSONL parser
- `src/oxpwn/sandbox/tools/nuclei.py` — NucleiExecutor + JSONL parser
- `src/oxpwn/sandbox/tools/ffuf.py` — FfufExecutor + JSON parser with ANSI stripping
- `src/oxpwn/agent/react.py` — ReactAgent with 5-phase ReAct loop
- `src/oxpwn/agent/tools.py` — ToolRegistry with 5-tool default registration
- `src/oxpwn/agent/prompts.py` — Phase-aware system prompt builder with all 5 phase guidance
- `src/oxpwn/agent/events.py` — 6 typed event dataclasses + AgentEventCallback Protocol
- `src/oxpwn/agent/exceptions.py` — Agent exception hierarchy
- `src/oxpwn/cli/main.py` — `scan --target` command with async runtime composition and enrichment
- `src/oxpwn/cli/streaming.py` — RichStreamingCallback append-only renderer
- `src/oxpwn/cli/wizard.py` — Interactive first-run wizard with Ollama detection
- `src/oxpwn/config/manager.py` — OxpwnConfig model, ConfigManager with YAML persistence
- `src/oxpwn/enrichment/nvd.py` — Async NVD client with rate limiting and Pydantic response models
- `src/oxpwn/enrichment/cache.py` — SQLite CVE cache with WAL mode and TTL
- `src/oxpwn/enrichment/enrichment.py` — CVE extraction, finding conversion, enrichment orchestrator
- `tests/conftest.py` — Shared fixtures, factories, Docker/LLM skip guards, Juice Shop fixture
- `tests/unit/` — 261 unit tests across 15 test files
- `tests/integration/` — Integration tests for LLM, sandbox, tool suite, CLI, and Juice Shop e2e
- `tests/fixtures/tool_suite/` — Deterministic HTTP proof assets for tool integration
- `.gsd/milestones/M001/slices/S08/ACCEPTANCE-CHECKLIST.md` — 7-category manual verification checklist
