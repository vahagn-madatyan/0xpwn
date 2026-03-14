# Decisions Register

<!-- Append-only. Never edit or remove existing rows.
     To reverse a decision, add a new row that supersedes it.
     Read this file at the start of any planning or research phase. -->

| # | When | Scope | Decision | Choice | Rationale | Revisable? |
|---|------|-------|----------|--------|-----------|------------|
| 1 | 2026-03-12 | project | Build fresh vs fork Strix | Build from scratch, borrow patterns | Strix lacks tiered permissions, validation agent, and freemium model; forking would carry debt and constrain architecture | no |
| 2 | 2026-03-12 | project | License | Apache 2.0 | Maximum adoption + commercial flexibility; matches Strix's license | no |
| 3 | 2026-03-12 | project | Python package name | `oxpwn` (package) / `0xpwn` (CLI) | Python identifiers can't start with digit; `oxpwn` is valid, `0xpwn` is the brand CLI command | no |
| 4 | 2026-03-12 | project | LLM abstraction | LiteLLM | Provider-agnostic (100+ models), built-in cost tracking, async, tool calling — no custom wrapper needed | yes |
| 5 | 2026-03-12 | project | Default model onboarding | Guided first-run wizard | Adaptive: detect Ollama → offer local, or guide API key setup. Lower barrier than requiring config | yes |
| 6 | 2026-03-12 | project | Docker sandbox image | Custom published image (ghcr.io/0xpwn/sandbox) | Baked-in tools for reproducibility and fast cold start vs installing at runtime | yes |
| 7 | 2026-03-12 | project | Agent output verbosity | Full reasoning stream by default | Bug bounty hunters identified "watching the AI operate" as the selling moment; transparency > cleanliness | yes |
| 8 | 2026-03-12 | project | External data sources in M001 | Include NVD/CVE enrichment | Enriched findings significantly more useful for bug bounty reports; worth the added slice | yes |
| 9 | 2026-03-12 | project | Target user for launch | Bug bounty hunters | Speed-obsessed, cost-sensitive, value PoC quality — best fit for autonomous agent value prop | yes |
| 10 | 2026-03-12 | project | CLI framework | Typer + Rich | Typer for CLI structure, Rich for streaming output and formatting — well-supported, fast to build | yes |
| 11 | 2026-03-12 | S01 | Build backend | hatchling | Lightweight, native src/ layout support, no setup.py needed — simplest option for pure-Python packages | yes |
| 12 | 2026-03-12 | S01 | Token tracking model | Nested `TokenUsage` Pydantic model | Separate input/output/total as a dedicated model rather than flat fields — mirrors provider response shapes, cleaner composition | yes |
| 13 | 2026-03-12 | S01 | ScanState mutation strategy | Mutable methods (add_finding, advance_phase, etc.) | Scan sessions are inherently mutable lifecycle objects; immutable updates would add ceremony without benefit here | yes |
| 14 | 2026-03-13 | S01 | Integration test LLM provider | `gemini/gemini-2.5-flash` via GEMINI_API_KEY | Available key, free tier; gemini-2.0-flash quota exhausted. Proves provider-agnostic design by using non-default provider. Override via `OXPWN_TEST_MODEL` env var | yes |
