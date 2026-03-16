# S05: Streaming CLI + Real-time Output — UAT

**Milestone:** M001
**Written:** 2026-03-15

## UAT Type

- UAT mode: mixed (artifact-driven + live-runtime)
- Why this mode is sufficient: The streaming CLI is both testable via captured output (CliRunner) and requires live visual verification of Rich formatting, incremental rendering, and terminal behavior that automated tests cannot fully capture.

## Preconditions

- `pip install -e .` completed successfully in the project directory
- `0xpwn --version` responds with `0xpwn 0.1.0`
- Docker daemon is running and reachable
- An LLM API key is exported (e.g., `GEMINI_API_KEY` for Gemini, `OPENAI_API_KEY` for OpenAI)
- `OXPWN_MODEL` is set (e.g., `gemini/gemini-2.5-flash`)

## Smoke Test

Run `OXPWN_MODEL="gemini/gemini-2.5-flash" 0xpwn scan --target localhost` and confirm the terminal shows Rich-formatted output that appears incrementally (not buffered until the end). You should see at minimum a scan header panel, a config display, and a phase transition rule before any error or completion.

## Test Cases

### 1. Incremental streaming output

1. Run `OXPWN_MODEL="gemini/gemini-2.5-flash" 0xpwn scan --target localhost`
2. Watch the terminal as the scan progresses
3. **Expected:** Output appears incrementally — scan header first, then phase rules, then reasoning/tool blocks as they happen, not all at once after completion. The visual impression should be "watching the AI work" rather than "waiting for a batch dump."

### 2. Phase transitions are visually distinct

1. Run a scan that progresses through at least Recon and Scanning phases
2. **Expected:** Each phase change renders a Rich `Rule` with the phase name (e.g., `── Phase: RECON ──`, `── Phase: SCANNING ──`). Phases appear in sequence.

### 3. Tool output chunks stream live

1. During a scan, watch for tool execution (e.g., nmap)
2. **Expected:** Raw stdout/stderr from the tool appears as prefixed lines (`stdout │ ...`, `stderr │ ...`) while the tool is running, before the parsed result summary appears.

### 4. Bootstrap error without model config

1. Unset `OXPWN_MODEL` and any provider API key env vars
2. Run `0xpwn scan --target localhost`
3. **Expected:** A Rich error panel appears with guidance about setting `OXPWN_MODEL`, exit code is non-zero, and no secrets or credential URLs appear in the output.

### 5. Version flag works

1. Run `0xpwn --version`
2. **Expected:** Prints `0xpwn 0.1.0` and exits cleanly.

## Edge Cases

### Missing Docker daemon

1. Stop the Docker daemon
2. Run `OXPWN_MODEL="gemini/gemini-2.5-flash" 0xpwn scan --target localhost`
3. **Expected:** A Rich error panel appears mentioning Docker/sandbox, exit code is non-zero.

### Invalid LLM API key

1. Set `OXPWN_MODEL="gemini/gemini-2.5-flash"` and `GEMINI_API_KEY="invalid-key"`
2. Run `0xpwn scan --target localhost`
3. **Expected:** Scan starts, Docker sandbox creates, but an LLM error panel appears when the agent tries to reason. The error panel shows provider/model guidance without echoing the invalid key value.

## Failure Signals

- Output appears all at once after the scan finishes (streaming broken)
- No phase transition rules visible (event emission or rendering broken)
- Raw API keys or credential-bearing URLs appear in error output (redaction broken)
- `0xpwn scan --target` not recognized or shows "No such option" (CLI wiring broken)
- Tests show 0 collected or unexpected failures when running `pytest tests/unit/test_cli_main.py -v`

## Requirements Proved By This UAT

- R004 — Real-time agent reasoning stream: This UAT proves the streaming CLI renders reasoning, tool selection, raw output, parsed results, and phase transitions incrementally in the terminal. Full five-phase validation with real findings is deferred to S08.

## Not Proven By This UAT

- R004 full validation — a complete five-phase scan against a real target (Juice Shop) with actual vulnerability findings streaming end-to-end. This requires S07 (CVE enrichment) and S08 (end-to-end validation).
- R005 — First-run wizard is not yet integrated; model config is env/option-only until S06.
- Streaming behavior under very large tool outputs (multi-MB nmap results) is untested.

## Notes for Tester

- If Docker or LLM keys are unavailable, test cases 1–3 cannot be fully exercised. Focus on test case 4 (bootstrap error) and test case 5 (version flag) — these always work.
- The scan may fail during the LLM reasoning step if the model/key combination isn't valid. This is acceptable — the UAT goal is to verify that output streams incrementally up to the failure point, and that the failure itself renders as a clean Rich error panel.
- The `localhost` target won't have real services running in most test environments. The important observation is the streaming behavior, not whether vulnerabilities are found.
