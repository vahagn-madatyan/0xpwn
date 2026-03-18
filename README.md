# 0xpwn

AI-powered penetration testing engine. Point it at a target and let a ReAct agent drive reconnaissance, scanning, and vulnerability discovery — all tools run inside a Docker sandbox so nothing touches the host.

**Input:** Target URL, hostname, IP, or CIDR via CLI
**Output:** Structured findings with CVE enrichment, phase-by-phase execution logs

```text
  CLI  ──▶  ReAct Agent  ──▶  Docker Sandbox  ──▶  Target
  (Typer)   (LLM-driven       (Kali + nmap,       (your scope)
             tool selection)    nuclei, ffuf,
                                httpx, subfinder)
```

---

## Installation

### Option 1: Install from PyPI (recommended)

```bash
pip install 0xpwn
```

### Option 2: Install with pipx (isolated environment)

```bash
pipx install 0xpwn
```

### Verify installation

```bash
0xpwn --help
```

---

## Setup

### 1. Build the Sandbox Image

All scan tools run inside a Docker container based on Kali Linux:

```bash
docker build -t oxpwn-sandbox:dev docker/
```

### 2. Configure an LLM Provider

0xpwn uses [LiteLLM](https://docs.litellm.ai/) — any supported provider works:

```bash
# Google Gemini
export GEMINI_API_KEY=your_key_here

# OpenAI
export OPENAI_API_KEY=your_key_here

# Anthropic
export ANTHROPIC_API_KEY=your_key_here

# Or use the generic key
export OXPWN_API_KEY=your_key_here
```

### 3. Run the Setup Wizard (optional)

```bash
0xpwn config wizard
```

Saves model and API key preferences to `~/.config/oxpwn/config.yaml`.

---

## Usage

### Run a scan

```bash
# Basic scan with model specified
0xpwn scan --target example.com --model gemini/gemini-2.5-flash

# Use environment variable for model
export OXPWN_MODEL=gemini/gemini-2.5-flash
0xpwn scan --target 192.168.1.0/24

# Custom sandbox settings
0xpwn scan --target example.com \
  --model openai/gpt-4o \
  --sandbox-image oxpwn-sandbox:dev \
  --network-mode bridge \
  --max-iterations-per-phase 15
```

If no model is configured, the interactive wizard runs automatically.

### Manage configuration

```bash
# Show current config
0xpwn config show

# Run setup wizard
0xpwn config wizard

# Reset configuration
0xpwn config reset
```

---

## Available Tools

The ReAct agent selects tools autonomously based on the scan phase. All tools execute inside the Docker sandbox:

| Tool | What it does |
|------|--------------|
| `nmap` | Port scanning and service detection |
| `subfinder` | Subdomain enumeration |
| `httpx` | HTTP probing and technology detection |
| `nuclei` | Vulnerability scanning with templates |
| `ffuf` | Web fuzzing and directory discovery |

---

## How It Works

0xpwn uses a **ReAct (Reasoning + Acting) agent** that plans and executes penetration testing in phases:

1. **Reconnaissance** — Subdomain enumeration, port scanning, service fingerprinting
2. **Scanning** — Vulnerability detection, web probing, directory fuzzing
3. **Analysis** — CVE enrichment via NVD, finding correlation, risk assessment

Each phase runs up to N iterations (default 10). The agent decides which tool to run, parses the output, and feeds results into the next decision. Findings are enriched with CVE data from the National Vulnerability Database.

---

## Scan Options

| Flag | Description | Default |
|------|-------------|---------|
| `--target` | Target URL, hostname, IP, or CIDR | Required |
| `--model` | LLM model identifier (LiteLLM format) | `OXPWN_MODEL` env / config |
| `--llm-base-url` | Override LiteLLM base URL | None |
| `--sandbox-image` | Docker image for the sandbox | `oxpwn-sandbox:dev` |
| `--network-mode` | Docker network mode | `bridge` |
| `--max-iterations-per-phase` | Max ReAct iterations per phase | `10` |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OXPWN_MODEL` | Default LLM model |
| `OXPWN_API_KEY` | Generic API key (fallback) |
| `OXPWN_LLM_BASE_URL` | Override LiteLLM base URL |
| `OXPWN_SANDBOX_IMAGE` | Default sandbox Docker image |
| `OXPWN_SANDBOX_NETWORK_MODE` | Default Docker network mode |
| `OXPWN_MAX_ITERATIONS_PER_PHASE` | Default max iterations |
| `GEMINI_API_KEY` | Google Gemini API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |

---

## Architecture

```text
src/oxpwn/
├── cli/                  # Typer CLI, Rich streaming output, setup wizard
├── agent/                # ReAct agent loop, tool dispatch, event system
├── llm/                  # LiteLLM client wrapper with error taxonomy
├── sandbox/              # Docker container lifecycle management
│   └── tools/            # Tool parsers (nmap, nuclei, httpx, ffuf, subfinder)
├── enrichment/           # NVD CVE lookup, caching, finding extraction
├── config/               # YAML config manager with env/CLI precedence
└── core/                 # Data models (ScanState, Finding, ToolResult)

docker/
└── Dockerfile            # Kali-based sandbox with pre-installed tools
```

**Key design decisions:**
- **Docker isolation** — all offensive tools run in a sandboxed container, never on the host
- **LiteLLM abstraction** — swap LLM providers without code changes
- **Structured error taxonomy** — every failure mode has a typed exception with actionable CLI output
- **Phase-based execution** — the agent progresses through recon → scanning → analysis with bounded iterations

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Sandbox image 'oxpwn-sandbox:dev' was not found` | Run `docker build -t oxpwn-sandbox:dev docker/` |
| `Docker sandbox error` | Verify Docker daemon is running: `docker ps` |
| `LLM authentication failed` | Export the correct API key for your provider |
| `LLM rate limited` | Wait and retry, or switch to a provider with more quota |
| `Missing model configuration` | Pass `--model`, set `OXPWN_MODEL`, or run `0xpwn config wizard` |

---

## Contributing

### Build from source

```bash
git clone https://github.com/vahagn-madatyan/0xpwn.git
cd 0xpwn

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Build the sandbox image
docker build -t oxpwn-sandbox:dev docker/

# Run from source
0xpwn --help
```

### Run tests

```bash
# Unit tests only
pytest tests/unit/ -v --tb=short

# All tests (requires Docker + running services)
pytest tests/ -v

# Specific test file
pytest tests/unit/test_react_agent.py -v
```

### Making a release

Releases are published to PyPI automatically via GitHub Actions when a version tag is pushed:

```bash
# Update version in pyproject.toml and src/oxpwn/__init__.py
# Commit the version bump
git tag v0.2.0
git push origin v0.2.0
```

The CI pipeline builds the distribution, runs tests, publishes to TestPyPI on every push, and publishes to PyPI on tags matching `v*`.

---

## License

[Apache License 2.0](LICENSE)
