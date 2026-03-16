# S08 Acceptance Checklist — End-to-End Validation

**Milestone:** M001
**Slice:** S08 — End-to-End Validation

This checklist documents the manual verification steps a human must perform to confirm the full 0xpwn pipeline meets acceptance criteria. These are subjective / quality checks that automated tests cannot fully cover.

---

## Prerequisites

- Docker daemon running
- OWASP Juice Shop available: `docker run -d -p 3000:3000 bkimminich/juice-shop:latest`
- At least one LLM API key exported (e.g. `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`)
- 0xpwn installed in development mode: `pip install -e .`

## Run Command

```bash
0xpwn scan --target http://host.docker.internal:3000 --model <model>
```

Replace `<model>` with your configured model (e.g. `gemini/gemini-2.5-flash`).

---

## Verification Steps

### (a) Phase Transitions

- [ ] All 5 phase transitions render in Rich output:
  - `Phase: Recon`
  - `Phase: Scanning`
  - `Phase: Exploitation`
  - `Phase: Validation`
  - `Phase: Reporting`
- [ ] Phases appear in the correct order (recon → scanning → exploitation → validation → reporting)
- [ ] Each phase transition is visually distinct (Rich rule/panel separator)

### (b) Agent Reasoning

- [ ] Agent reasoning panels show tool selection rationale (why a tool was chosen)
- [ ] Reasoning is contextual to the current phase (not generic boilerplate)
- [ ] Reasoning references the target or prior findings where appropriate

### (c) Streaming Output

- [ ] Tool output streams incrementally (stdout/stderr chunks appear as they arrive, not in a single block)
- [ ] Streamed chunk markers (`stdout │` or `stderr │`) are visible during tool execution
- [ ] No long silent periods where the terminal appears frozen (activity indicator or output within ~30s)

### (d) Scan Summary

- [ ] Scan summary panel appears at the end of the scan
- [ ] Summary includes:
  - Total findings count
  - Total cost (or $0.00 if free model)
  - Total duration
  - Phases completed count
  - Tool results count

### (e) Container Cleanup

- [ ] No orphan Docker containers remain after scan completes:
  ```bash
  docker ps --filter label=oxpwn.managed=true
  ```
  Should return no running containers with the `oxpwn.managed=true` label.
- [ ] No orphan Juice Shop containers (if started manually, stop it separately)

### (f) Enrichment Fields

- [ ] If CVE-bearing vulnerabilities were found, findings include enrichment fields:
  - CVSS score (numeric)
  - CWE ID (e.g. `CWE-89`)
- [ ] If no CVE-bearing vulns were found, scan still completes successfully (enrichment is best-effort)
- [ ] `cli.scan_complete` structlog event includes `enriched_findings` count

### (g) Clean Teardown

- [ ] Scan exits with code 0 on successful completion
- [ ] No Python tracebacks in terminal output
- [ ] Docker sandbox container is destroyed after scan:
  ```bash
  docker ps -a --filter label=oxpwn.managed=true
  ```
  Should return no containers (running or stopped).

---

## Pass Criteria

All items above must be checked for the milestone to be considered accepted. Items (f) depend on LLM behavior — if the LLM doesn't identify CVE-bearing vulnerabilities against Juice Shop, the enrichment checks may show zero enriched findings, which is acceptable for M001 (the enrichment *pipeline* is wired; finding accuracy is a quality-over-time concern).

## Notes

- Different LLM models may produce different tool selections and finding counts — this is expected
- Scan duration varies significantly by model (30s to 10min) — the 600s timeout in automated tests accommodates this
- If `host.docker.internal` doesn't resolve (Linux without Docker Desktop), use `172.17.0.1` or the Docker bridge IP instead
