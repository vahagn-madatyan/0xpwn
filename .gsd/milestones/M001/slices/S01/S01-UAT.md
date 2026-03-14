# S01: Foundation + LLM Client — UAT

**Milestone:** M001
**Written:** 2026-03-13

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S01 is a foundation slice — no user-facing features beyond CLI stub. All contracts are proven by unit tests (model validation) and integration tests (real LLM round-trip). No UI, no streaming, no interactive flows to test.

## Preconditions

- Python 3.12+ installed
- `pip install -e ".[dev]"` succeeds
- For integration tests: `GEMINI_API_KEY` (or `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`) set in environment

## Smoke Test

Run `0xpwn --help` — should display usage with `scan` command and `--version` option, exit 0.

## Test Cases

### 1. Package installs and CLI responds

1. `pip install -e ".[dev]"`
2. `0xpwn --help`
3. `0xpwn --version`
4. **Expected:** Install succeeds without errors. `--help` shows usage with `scan` command. `--version` prints `0xpwn 0.1.0`.

### 2. All unit tests pass

1. `pytest tests/unit/ -v`
2. **Expected:** 43/43 tests pass — 35 model tests + 8 LLM client tests.

### 3. Integration tests pass against real LLM

1. `export GEMINI_API_KEY=<key>` (or set OPENAI_API_KEY)
2. `OXPWN_TEST_MODEL="gemini/gemini-2.5-flash" pytest tests/integration/ -m integration -v`
3. **Expected:** 2/2 tests pass. Tool calling test verifies `get_weather` tool invoked with location argument, tokens > 0, cost >= 0, latency > 0. Basic completion test verifies text response containing "hello".

### 4. Models import and serialize correctly

1. `python3 -c "from oxpwn.core.models import ScanState, Finding, Phase, Severity; print('OK')"`
2. `python3 -c "from oxpwn.core.models import ScanState; s = ScanState(target='http://x.com'); print(s.model_dump_json()[:80])"`
3. **Expected:** Imports succeed. ScanState serializes to JSON with target, current_phase, findings, etc.

## Edge Cases

### Missing API key skips integration tests gracefully

1. `unset OPENAI_API_KEY ANTHROPIC_API_KEY GEMINI_API_KEY`
2. `pytest tests/integration/ -m integration -v`
3. **Expected:** Tests skip with message "No LLM API key set — skipping integration tests". No errors.

### Invalid model validation

1. `python3 -c "from oxpwn.core.models import Finding; Finding(title='x', severity='invalid', description='d', url='http://x', evidence='e', tool_name='t')"`
2. **Expected:** `ValidationError` raised for invalid severity value.

## Failure Signals

- `pip install -e .` fails — broken pyproject.toml or missing dependencies
- `0xpwn --help` not found — entrypoint not registered in pyproject.toml scripts
- Import errors from `oxpwn.core.models` or `oxpwn.llm.client` — broken package structure
- Integration tests return `cost: 0` — litellm.completion_cost() may not support the model (acceptable for local models, should be > 0 for cloud)
- Unit tests fail on model validation — Pydantic schema changed without updating tests

## Requirements Proved By This UAT

- R003 (Provider-agnostic LLM support) — integration test proves LLMClient works against Gemini via LiteLLM with tool calling and cost tracking. Provider-agnostic design confirmed by using a non-default provider.

## Not Proven By This UAT

- R003 Ollama/local model support — deferred to S06 wizard integration
- R001 agent loop — S03
- R002 Docker sandbox — S02
- R004 streaming output — S05
- R005 first-run wizard — S06
- R006 CVE enrichment — S07

## Notes for Tester

- `gemini-2.0-flash` free tier is exhausted on the current key. Use `gemini-2.5-flash` for integration tests.
- The `scan` command is a stub — running `0xpwn scan --target http://example.com` will just print a placeholder message. Full wiring happens in S05.
- LiteLLM may emit deprecation warnings — these are upstream and don't affect functionality.
