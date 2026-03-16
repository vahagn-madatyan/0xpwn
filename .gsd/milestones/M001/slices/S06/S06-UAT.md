# S06: First-Run Wizard + Config — UAT

**Milestone:** M001
**Written:** 2026-03-15

## UAT Type

- UAT mode: human-experience
- Why this mode is sufficient: The wizard is an interactive terminal flow — automated tests cover logic and state, but UX quality (prompt clarity, flow pacing, error recovery) requires human evaluation

## Preconditions

- `pip install -e .` completed — `0xpwn` CLI is available
- No existing config at `~/.config/oxpwn/config.yaml` (or `$OXPWN_CONFIG` path) — delete if present
- At least one of: Ollama running locally, or a cloud API key (OpenAI/Anthropic/Gemini) available

## Smoke Test

Run `0xpwn config show` — should display "No configuration file found" message. Then run `0xpwn config wizard` — should launch the interactive setup flow.

## Test Cases

### 1. Fresh wizard with cloud provider

1. Delete config: `0xpwn config reset`
2. Run `0xpwn config wizard`
3. If Ollama detected: select "Cloud API" when prompted for local vs cloud
4. Select a provider (e.g., OpenAI)
5. Enter API key when prompted (displayed masked)
6. Accept or customize the default model string
7. Wait for LLM validation (should show success)
8. **Expected:** Config saved message with file path; `0xpwn config show` displays model, redacted key (`sk-1***xxxx`), and provider

### 2. Fresh wizard with Ollama (local)

1. Ensure Ollama is running (`ollama serve`)
2. Delete config: `0xpwn config reset`
3. Run `0xpwn config wizard`
4. Select "Local (Ollama)" when prompted
5. Select a model from the detected list (or enter custom)
6. Wait for LLM validation
7. **Expected:** Config saved with `ollama/` prefixed model; `0xpwn config show` displays model with no API key

### 3. Config feeds into scan command

1. Complete wizard (test case 1 or 2)
2. Run `0xpwn scan --target http://example.com` (will fail on target, but should not fail on missing model config)
3. **Expected:** Scan attempts to start (may fail on Docker/target) but does NOT show "No model configured" error

### 4. Config show with redaction

1. Complete wizard with a cloud provider
2. Run `0xpwn config show`
3. **Expected:** Model displayed in full; API key displayed as `sk-1***xxxx` (first 4 + last 4 chars visible); base_url shown if set

### 5. Config reset flow

1. Run `0xpwn config reset`
2. Confirm deletion when prompted
3. **Expected:** "Configuration deleted" message; `0xpwn config show` shows "No configuration file found"

## Edge Cases

### Non-interactive terminal skip

1. Run `echo "" | 0xpwn config wizard` (piped stdin)
2. **Expected:** Wizard skips gracefully with a message, does not crash or hang

### Validation failure recovery

1. Run `0xpwn config wizard`
2. Enter an invalid API key (e.g., `sk-invalid123`)
3. **Expected:** Validation fails with clear error message; prompted to retry or skip; retry with valid key succeeds

### Config subcommand help

1. Run `0xpwn config --help`
2. **Expected:** Shows `show`, `reset`, `wizard` subcommands with descriptions

## Failure Signals

- Wizard hangs or crashes on any prompt
- API key displayed in full (not redacted) in `config show` or terminal output
- Wizard fails to detect running Ollama instance
- Config file written with permissions other than 0o600
- `0xpwn scan` still shows "No model configured" after successful wizard completion
- Wizard crashes in non-interactive terminal instead of skipping gracefully

## Requirements Proved By This UAT

- R005 — First-run guided model setup wizard: interactive wizard detects Ollama, guides API key setup, validates connectivity, persists config, and feeds into scan command

## Not Proven By This UAT

- R003 full validation — provider-agnostic LLM support is proven by S01 integration tests, not this wizard UAT
- Live scan completion — S08 will prove the wizard-configured model actually completes a full scan
- Ollama tool calling quality — the milestone risk note; wizard proves connectivity only, not autonomous operation quality

## Notes for Tester

- The wizard validation step makes a real LLM API call (`max_tokens=5`, ~$0.001 cost) — have a valid API key or running Ollama ready
- If testing both local and cloud flows, run `0xpwn config reset` between tests
- Config file location: check `~/.config/oxpwn/config.yaml` (or `$OXPWN_CONFIG`) to verify file permissions are `0o600`
- The wizard Rich prompts use color and formatting — test in a terminal that supports ANSI colors for the intended UX
