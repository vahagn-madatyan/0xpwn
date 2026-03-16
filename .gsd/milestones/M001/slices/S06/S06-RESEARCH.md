# S06: First-Run Wizard + Config — Research

**Date:** 2026-03-15

## Summary

S06 adds two tightly coupled capabilities: a **YAML-backed config manager** that persists user preferences to `~/.config/oxpwn/config.yaml`, and an **interactive first-run wizard** that detects Ollama, guides API key setup for cloud providers, validates connectivity, and writes the initial config. The config manager feeds into the existing `_build_scan_config()` resolution chain so that `0xpwn scan --target <url>` works without `--model` or env vars after the wizard runs once.

The implementation surface is clean: no config module exists yet (`src/oxpwn/config/` is new), the CLI `_build_scan_config()` in `main.py` already raises `ScanBootstrapError` on missing model — that's the natural injection point for wizard triggering. Rich's `Prompt.ask()` and `Confirm.ask()` give styled prompts consistent with the existing Rich CLI. Ollama detection is straightforward via `httpx.get("http://localhost:11434/api/tags")`. LiteLLM provides `validate_environment()` and `supports_function_calling()` for provider validation, plus `acompletion()` for a live connectivity check.

The main risk is PyYAML: it's currently available only as a transitive optional dependency from `litellm[proxy]`, not a core dep. We must add `pyyaml>=6.0` to `pyproject.toml` to make config persistence reliable.

## Recommendation

Build three components in this order:

1. **Config model + manager** (`src/oxpwn/config/`) — Pydantic model for config schema, YAML load/save with XDG path resolution, env-override merge logic. Standalone, fully testable without prompts or LLM.
2. **Wizard** (`src/oxpwn/cli/wizard.py`) — Interactive flow using Rich prompts: detect Ollama → choose provider → collect credentials → validate → write config. Sync function callable from Typer.
3. **CLI integration** — Wire config loading into `_build_scan_config()` as a fallback before the `ScanBootstrapError` raise. Add `0xpwn config` subcommand for `show`/`reset`/`wizard` operations.

This order allows each layer to be tested independently and avoids circular dependencies.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| YAML serialization | `pyyaml` (already transitively available, add as direct dep) | Standard, well-tested, Pydantic's `.model_dump()` produces YAML-friendly dicts |
| Interactive prompts | `rich.prompt.Prompt` / `rich.prompt.Confirm` | Already a dependency, styled consistently with existing Rich CLI output |
| Ollama detection | `httpx` sync client (already a dependency) | `httpx.get("http://localhost:11434/api/tags")` returns model list, no new deps |
| Provider env var detection | `litellm.validate_environment(model)` | Returns `missing_keys` list per model — avoids hardcoding provider→env mappings |
| Config path resolution | `pathlib.Path` + `XDG_CONFIG_HOME` env | Standard library, no need for `platformdirs` (adds a dep for one path) |
| LLM connectivity check | `litellm.acompletion()` with minimal prompt | Already the abstraction layer; validates both auth and model availability in one call |

## Existing Code and Patterns

- `src/oxpwn/cli/main.py` — `_build_scan_config()` resolves CLI options + env vars into `ScanRuntimeConfig`. This is the injection point: check YAML config before raising `ScanBootstrapError`. The `ScanRuntimeConfig` dataclass defines the fields config must provide: `model`, `sandbox_image`, `network_mode`, `max_iterations_per_phase`, `api_key`, `base_url`.
- `src/oxpwn/cli/streaming.py` — `RichStreamingCallback` and `render_error_panel()` establish the Rich styling patterns (Panel, Rule, Console). The wizard should use the same `Console` and panel patterns for visual consistency.
- `src/oxpwn/llm/client.py` — `LLMClient.__init__` accepts `model`, `api_key`, `base_url`. The config must produce these three values. The `_provider` property splits model string on `/` — config should store the full LiteLLM model string (e.g., `ollama/llama3.1`, `gemini/gemini-2.5-flash`).
- `src/oxpwn/llm/exceptions.py` — `LLMAuthError` is what fails when API key is wrong. The wizard should catch this during validation and re-prompt.
- `src/oxpwn/core/models.py` — Pydantic v2 patterns with `field_validator`, `Field(default=...)`. Config model should follow the same conventions.
- `tests/conftest.py` — `scan_state_factory` fixture pattern. Config tests should follow the same factory approach.
- `tests/unit/test_cli_main.py` — Uses `CliRunner` with `monkeypatch` to test CLI commands. Config/wizard tests should use the same pattern plus `tmp_path` for config file isolation.

## Constraints

- **PyYAML must become a direct dependency** — Currently only available via `litellm[proxy]` optional extra. Config persistence requires it unconditionally. Add `"pyyaml>=6.0"` to `pyproject.toml` dependencies.
- **Wizard must be synchronous** — It runs inside a Typer command callback (sync). Use `httpx` sync client for Ollama detection, `asyncio.run()` for the single LiteLLM validation call.
- **Config resolution must not break existing env-backed behavior** — CLI options > env vars > YAML config > wizard trigger. Existing `OXPWN_MODEL`, `OXPWN_API_KEY`, `OXPWN_LLM_BASE_URL` env vars must keep working and take precedence over YAML.
- **No config file = wizard trigger, not an error** — The `ScanBootstrapError("Missing model configuration")` currently raised when model is absent should only fire after the wizard is declined or fails; first-run should silently launch the wizard.
- **Config file path is XDG-compliant** — `$XDG_CONFIG_HOME/oxpwn/config.yaml` (default `~/.config/oxpwn/config.yaml`), with `OXPWN_CONFIG` env override for explicit path.
- **Existing 64 unit + 2 integration tests must pass unchanged** — Config integration must be purely additive.

## Common Pitfalls

- **Testing interactive prompts** — Rich `Prompt.ask()` reads from stdin. Tests must inject a `Console` with a `StringIO` input stream or monkeypatch the prompt functions. Using `typer.testing.CliRunner` with `input=` parameter handles stdin injection for CLI-level tests.
- **YAML type coercion surprises** — PyYAML's `yaml.safe_load()` coerces strings like `"true"`, `"null"`, `"3.1"` to Python booleans/None/floats. API keys and model strings must be read as strings explicitly. Use Pydantic model validation after loading to enforce types.
- **Ollama running but no models** — Ollama server responding at `:11434` doesn't mean models are available (confirmed: this machine has Ollama running with zero models). The wizard must handle this case: offer to pull a recommended model or guide to `ollama pull`.
- **LiteLLM `validate_environment` quirk for Ollama** — `litellm.validate_environment("ollama/llama3.1")` reports `missing_keys: ['OLLAMA_API_BASE']` even though LiteLLM defaults to `http://localhost:11434`. Don't use this as the sole Ollama detection mechanism; use direct HTTP probe instead.
- **Config file permissions** — API keys in YAML should be written with restrictive file permissions (`0o600`). Avoid creating world-readable config files.
- **CliRunner and `monkeypatch.delenv` interaction** — Typer's CliRunner doesn't support `mix_stderr=False` (discovered in S05). Test env var manipulation must use `monkeypatch.setenv` / `monkeypatch.delenv` before invoking the runner.
- **Wizard re-entry** — If wizard is interrupted (Ctrl+C), the config file should either not exist or be in a valid state. Write atomically (write to temp file, then rename).

## Open Risks

- **Ollama model recommendation accuracy** — The wizard will recommend specific Ollama models for tool-calling pentesting (e.g., `qwen2.5:72b`, `llama3.1:70b`). These recommendations may become stale as new models release. Mitigate: keep the model list in a constant that's easy to update; don't hardcode into prompts.
- **LLM validation latency** — The connectivity check sends a real LLM completion request. For cloud providers this takes 1-3s; for Ollama with a cold model it could take 30s+ on first load. Need a timeout and clear progress feedback.
- **Non-interactive environments** — The wizard uses Rich prompts which require a TTY. In CI/Docker/piped contexts, the wizard should be skippable and config should work purely from env vars. Detect non-interactive terminal and skip wizard gracefully.
- **Config schema migration** — If the config schema changes in later milestones, existing config files need to load without crashing. Pydantic's `model_validate` with `extra="ignore"` handles unknown fields; missing required fields need sensible defaults or re-wizard.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer CLI | tambo-ai/tambo@cli | available (92 installs) — not directly relevant, wizard is custom |
| Ollama | jeremylongshore/claude-code-plugins-plus-skills@ollama-setup | available (34 installs) — too generic, our Ollama integration is LiteLLM-specific |
| Rich prompts | — | none found — Rich prompt patterns are well-documented in existing code |

No skills installed — the work maps cleanly to existing project patterns and standard library capabilities.

## Sources

- Ollama API endpoint returns model list at `/api/tags` with `{models: [{name, ...}]}` shape (source: live probe against local Ollama instance)
- `litellm.validate_environment(model)` returns `{keys_in_environment: bool, missing_keys: list}` (source: live Python REPL tests)
- `litellm.supports_function_calling(model)` returns `True` for `ollama/llama3.1`, `gpt-4o-mini`, `gemini/gemini-2.5-flash` (source: live Python REPL tests)
- `litellm.acompletion()` with `max_tokens=5` validates both auth and model availability — confirmed working for Gemini (source: live validation test)
- PyYAML is only in `litellm[proxy]` optional extra, not a core litellm dependency (source: `importlib.metadata` inspection of litellm distribution)
- Rich `Prompt.ask()` accepts `choices`, `password`, `console`, `default` parameters for interactive input (source: Rich library introspection)
- XDG Base Directory Specification: `$XDG_CONFIG_HOME` defaults to `$HOME/.config` (source: project convention, confirmed via `pathlib` resolution)
