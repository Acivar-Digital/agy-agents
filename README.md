<div align="center">

# 🌌 antigravity-agents (`agy-agents`)

**Autonomous Deep Research Council & Self-Directed Code Refactoring Agents**  
*Powered by Google's Antigravity Sandbox (`antigravity-preview-09-2026`) via Google Gemini API & LiteRouter Gateway*

[![Release](https://img.shields.io/badge/release-v1.1.0-blue.svg?style=flat-square)](https://github.com/Acivar-Digital/agy-agents/releases)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-brightgreen.svg?style=flat-square)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
[![Dual Engine](https://img.shields.io/badge/Engine-Gemini%20API%20%7C%20LiteRouter-orange.svg?style=flat-square)](https://aistudio.google.com/)
[![MCP Ready](https://img.shields.io/badge/Architecture-MCP%20Ready-purple.svg?style=flat-square)](https://modelcontextprotocol.io/)
[![llms.txt](https://img.shields.io/badge/llms.txt-Standard-green.svg?style=flat-square)](llms.txt)
[![GitIngest](https://img.shields.io/badge/GitIngest-Digest%20Repo-blue.svg?style=flat-square)](https://gitingest.com/Acivar-Digital/agy-agents)

</div>

---

## 🤖 AI & LLM Integration

This repository is optimized for AI assistants, autonomous coding agents, and automated context ingestion:

* **Machine Discovery ([llms.txt](llms.txt))**: Curated Markdown index for LLMs based on the [Answer.AI specification](https://llmstxt.org).
* **Full Context Document ([llms-full.txt](llms-full.txt))**: Aggregated reference manual for large-context models (Claude, ChatGPT, Gemini).
* **System Architecture ([ARCHITECTURE.md](ARCHITECTURE.md))**: Mermaid topology diagrams, execution sequences, and verification primitives.
* **Agent Master Guidelines ([AGENTS.md](AGENTS.md))**: Rules, schema constraints, and endpoint contracts for autonomous agents.
* **Claude Code Config ([CLAUDE.md](CLAUDE.md))**: Direct memory file and development invariants for the Anthropic Claude CLI.

### 📦 Ingestion & Packaging Helpers

- **One-Click Ingestion**: Ingest this repository into Claude or ChatGPT with a single click using [GitIngest](https://gitingest.com/Acivar-Digital/agy-agents).
- **Repomix Packaging**: Package the codebase into an AI-optimized XML context file with token counts:
  ```bash
  # Generate repomix-output.xml using repomix.config.json
  npx repomix
  ```

### 💬 LLM Quickstart Prompt

When working with an AI assistant on this repository, paste this prompt for instant orientation:

> "I am working on the **agy-agents** repository (https://github.com/Acivar-Digital/agy-agents).
> - **Context**: Autonomous multi-persona deep research and automated Python code refactoring connected to Google Antigravity (`antigravity-preview-09-2026`).
> - **Endpoint Contract**: Strictly use `POST /v1beta/interactions` with `{'agent': 'antigravity-preview-09-2026', 'input': '...', 'environment': 'remote'}`. NEVER use `/v1/chat/completions` or `:generateContent`.
> - **Tech Stack**: Python 3.10+, uv, Pydantic V2 (`extra='forbid'`), FastMCP (`agy-mcp`).
> - **Verification**: Run `uv run python -m unittest tests/test_mcp_server.py` before declaring any work complete.
> - **Architecture**: Follow `ARCHITECTURE.md` and `AGENTS.md` for design invariants."

---

## 📖 About `agy-agents`

**`agy-agents`** is an open-source framework of autonomous AI agent workflows designed for institutional-grade intelligence gathering and production-ready code modernization. Built directly on Google's stateful **Antigravity Sandbox** environment (`/v1beta/interactions`), it delivers capabilities beyond standard single-turn LLM chat completions:

1. **🔬 Deep Research (Council Protocol)**: Automatically orchestrates a multi-perspective panel of 5 specialized expert personas (e.g., Quantitative Analyst, Macro Strategist, Systems Architect, Risk Specialist, and Adversarial Skeptic). The council searches live web data, verifies empirical evidence, resolves internal contradictions, and compiles whitepapers natively rendered into **Markdown, HTML, PDF, and Word (.docx)** formats.
2. **🛠️ Autonomous Code Refactoring**: Analyzes real-world codebases to enforce PEP 8 standards, strict type annotations, architectural decoupling, and helper extraction. Operates in two modes: **surgical single-file CLI** or **batch manifest pipelines** with shared reference contexts.
3. **🌐 Dual-Engine Inference**:
   - **Public Community Mode (Default)**: Out-of-the-box connectivity to the Google Gemini API using a standard `GEMINI_API_KEY`.
   - **Self-Hosted Mode**: Direct routing through a private [LiteRouter](https://github.com/gastownhall/literouter) LAN gateway (`http://literouter.lan:7766`) using `LITEROUTER_AUTH_KEY`.
4. **🔌 MCP & Pipeline Ready**: Zero CLI lock-in. Both tools export cleanly decoupled core functions (`execute_research` and `execute_refactor`) ready for integration into custom Python pipelines or [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server tools.

---

## 📦 Packages & Installation

`agy-agents` is designed for rapid installation via `pip` or [uv](https://docs.astral.sh/uv/):

### Option A: Install from Git (Recommended)
```bash
# Using standard pip
pip install git+https://github.com/Acivar-Digital/agy-agents.git

# Using uv
uv pip install git+https://github.com/Acivar-Digital/agy-agents.git
```

Once installed, the CLI tools are available globally in your environment:
```bash
# Run Deep Research
agy-research Quantum_Computing

# Run Code Refactoring
agy-refactor path/to/script.py --prompt "Add type hints and PEP 8"
```

### Option B: Local Developer Clone
```bash
git clone https://github.com/Acivar-Digital/agy-agents.git
cd agy-agents

# Copy environment configuration
cp .env.example .env
```

Install local dependencies:
```bash
pip install -r requirements.txt
# Or run scripts directly with uv (uv automatically handles environment and dependencies)
```

---

## 🚀 Quick Start Guide

### 1. Configure Environment (`.env`)

Add your API credentials to `.env`:

```ini
# --- Option A: Public Community Mode (Google Gemini API) ---
GEMINI_API_KEY=AIzaSy...your_gemini_api_key_here

# --- Option B: Self-Hosted Mode (LiteRouter Gateway) ---
# LITEROUTER_HOST=literouter.lan
# LITEROUTER_PORT=7766
# LITEROUTER_AUTH_KEY=your_literouter_key_here
```

---

### 2. Deep Research Workflow

```bash
# 1. Create a prompt template
cp deep-research/prompts/_template_guide.md deep-research/prompts/Quantum_Computing.md

# 2. Edit Quantum_Computing.md with your research question and 5 tailored personas

# 3. Run the research agent
uv run python deep-research/deep-research.py Quantum_Computing
```

The agent runs live web sprints, aggregates findings, executes supervisor reviews, and compiles four artifact formats in `deep-research/reports/`:
- `Quantum_Computing_YYYYMMDD_HHMM.md`
- `Quantum_Computing_YYYYMMDD_HHMM.html`
- `Quantum_Computing_YYYYMMDD_HHMM.pdf`
- `Quantum_Computing_YYYYMMDD_HHMM.docx`

---

### 3. Autonomous Refactoring Workflow

#### Mode A: Surgical Single-File Execution
```bash
# Refactor and save to path/to/script_refactored.py
uv run python refactor/refactor.py path/to/script.py

# Optional: provide custom inline refactoring prompt
uv run python refactor/refactor.py path/to/script.py --prompt "Refactor to Pydantic v2 schemas and strict async/await"

# Optional: overwrite the target file in-place
uv run python refactor/refactor.py path/to/script.py --inplace
```

#### Mode B: Batch Manifest Pipeline
```bash
# Process all manifests in refactor/manifests/*.json concurrently
uv run python refactor/refactor.py

# Or process a specific manifest
uv run python refactor/refactor.py --manifest refactor/manifests/template.json
```

---

## 🤖 Use Your LLM to Customize Everything

This repository provides an open architecture. **We encourage you to use your favorite LLM (Claude, ChatGPT, Gemini, or OpenCode) to adapt the personas, rules, and manifests to your specific project needs!**

### 💡 Copy-Paste Prompt 1: Tailor Research Personas
> *"I am researching [INSERT TOPIC HERE]. Review `deep-research/prompts/_template_guide.md` and generate a complete prompt file containing 5 distinct, adversarial expert personas (e.g. specialized domain engineer, macro economist, risk quant, contrarian skeptic, and regulatory analyst) with search objectives tailored to this topic."*

### 💡 Copy-Paste Prompt 2: Tailor Refactoring Guidelines
> *"Inspect `refactor/prompt.txt`. Refactor this system prompt to enforce our engineering team's standards: [e.g. enforce Google docstrings, Pydantic v2 data models, zero Any annotations, decoupled repository pattern, and FastAPI route best practices]."*

### 💡 Copy-Paste Prompt 3: Generate Batch Manifests
> *"Review `refactor/manifests/template.json` and my codebase in `src/`. Generate a manifest JSON that targets our database query modules, provides `src/models.py` as a reference context, and refactors all queries to use SQLAlchemy 2.0 select statements."*

---

## 🔌 Model Context Protocol (MCP) Server

`agy-agents` includes a native **Model Context Protocol (MCP)** server (`agy-mcp` via FastMCP) enabling AI assistants across other IDEs and workspaces (OpenCode, Claude Desktop, Cursor, and subagent workpools) to invoke the Deep Research Council and autonomous code refactoring.

### ⚡ Hybrid Architecture (No 60-Second Timeout Drops)
Standard MCP clients enforce a strict 60-second RPC timeout. Because the 5-persona research council conducts 50 live Google searches and sandbox document compilation (taking ~3–8 minutes), `agy-mcp` implements a **hybrid execution protocol**:
- **`prepare_research_prompt`**: (<1s) Dynamically crafts and saves a 5-persona research prompt file in `deep-research/prompts/<stem>.md` and provides the exact CLI command.
- **`start_research`**: (<1s) Spawns an asynchronous background worker and immediately returns a unique `job_id`, preventing client RPC timeout errors.
- **`get_research_status`**: Queries job progress, returns execution elapsed time, and delivers the synthesized executive summary and paths to compiled artifacts (`.md`, `.html`, `.pdf`, `.docx`) upon completion.
- **`refactor_code`**: (5–15s) Synchronous, high-speed code refactoring with AST syntax validation and unified diff preview.
- **`list_research_prompts`**: Discovers available structured prompt templates and active stems.
- **`check_gateway_health`**: Probes the inference gateway (`literouter.lan:7766` or Google Gemini) for reachability and latency.

### 🛠️ Sovereign MCP Tools Overview

| Tool Name | Type | Key Inputs | Description |
| :--- | :--- | :--- | :--- |
| `prepare_research_prompt` | Fast | `topic`, `prompt_stem`, `custom_rubric` | Sculpt tailored 5-persona research council prompt with background CLI execution commands. |
| `start_research` | Async | `prompt_stem_or_topic`, `timeout_seconds` | Non-blocking dispatch returning `job_id` immediately. Avoids client timeout drops. |
| `get_research_status` | Polling | `job_id` | Poll background progress or retrieve executive summary and compiled artifact paths. |
| `refactor_code` | Sync | `code`, `filename`, `instructions` | Autonomously refactor Python code (PEP 8, strict type hints, clean architecture) with diff summary. |
| `list_research_prompts` | Discovery | *(None)* | Scan repository for ready-to-run prompt templates and topics. |
| `check_gateway_health` | Diagnostic | *(None)* | Inspect LiteRouter / Gemini endpoint connectivity and latency. |

### 💻 Client Configurations

The MCP service can be accessed via **Direct Intranet SSE (Recommended for LAN / WireGuard)** or **SSH Stdio (Zero configuration)**:

#### Mode 1: Direct Network SSE (Intranet / WireGuard)

Any client on the LAN or WireGuard mesh can connect directly to the persistent systemd service:
- **SSE Stream URL**: `http://agy-agents.lan:7788/sse` *(or `http://192.168.50.10:7788/sse`)*
- **Streamable HTTP URL**: `http://agy-agents.lan:7788/mcp`

```json
{
  "mcpServers": {
    "agy-agents": {
      "url": "http://agy-agents.lan:7788/sse"
    }
  }
}
```

#### Mode 2: SSH Stdio (Zero-Daemon CLI Subprocess)

##### 1. OpenCode (`opencode.json`)
```json
{
  "mcp": {
    "agy-agents": {
      "type": "local",
      "command": [
        "ssh",
        "-o", "BatchMode=yes",
        "vps466a",
        "/home/vps466a/.local/bin/uv run --directory /home/vps466a/services/agy-agents agy-mcp"
      ]
    }
  }
}
```

##### 2. Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "agy-agents": {
      "command": "ssh",
      "args": [
        "-o", "BatchMode=yes",
        "vps466a",
        "/home/vps466a/.local/bin/uv run --directory /home/vps466a/services/agy-agents agy-mcp"
      ]
    }
  }
}
```

##### 3. Cursor (`.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "agy-agents": {
      "command": "ssh",
      "args": [
        "-o", "BatchMode=yes",
        "vps466a",
        "/home/vps466a/.local/bin/uv run --directory /home/vps466a/services/agy-agents agy-mcp"
      ]
    }
  }
}
```

---

## 🔌 Programmatic Python API

Both agent tools export cleanly modular functions for inclusion in custom Python scripts:

```python
from deep_research import execute_research
from refactor import execute_refactor

# 1. Trigger Deep Research programmatically
research_result = execute_research(
    prompt_content="Analyze impact of liquid cooling in next-gen AI data centers...",
    prompt_stem="data_center_cooling",
)
print("Generated report artifacts:", research_result.extracted_files)

# 2. Trigger Code Refactoring programmatically
refactor_result = execute_refactor(
    code_content="def calculate(data): return [x*2 for x in data if x > 0]",
    prompt="Add complete type hints, Google docstrings, and input validation.",
)
print("Refactored code:\n", refactor_result.refactored_code)
```

---

## 🏷️ Releases & Versioning

### `v1.2.0` — FastMCP Sovereign Server & Hybrid Architecture *(2026-10-07)*
- 🔌 **FastMCP Integration**: Native MCP server (`agy-mcp`) exposing 6 sovereign tools for AI assistants in OpenCode, Claude Desktop, and Cursor.
- ⚡ **Hybrid Execution Engine**: Solves 60s MCP RPC timeout drops via asynchronous background research jobs (`start_research`, `get_research_status`) and dynamic prompt preparation (`prepare_research_prompt`).
- 🛠️ **Synchronous Code Refactoring**: Direct in-turn code modernization (`refactor_code`) with AST syntax validation and unified diff calculation.
- 🌐 **VPS & LiteRouter LAN Deployment**: Validated remote execution over SSH against LiteRouter at `literouter.lan:7766` with zero hardcoded credentials.

### `v1.1.0` — Pydantic V2 Core Modernization *(2026-10-07)*
- 🛡️ **Pydantic V2 Type Contracts**: Full migration to modern Pydantic V2 (`pydantic>=2.10.0`) across all workflows.
- 🔒 **Immutable Provider Configs**: Frozen `ProviderConfig` models for both Deep Research and Refactor engines, validating URLs, placeholders, and headers.
- 📡 **Strict Interaction Schemas**: Validated `InteractionRequest`, `InteractionStep`, and `InteractionResponse` models safeguarding communication with LiteRouter and Google Gemini `/v1beta/interactions`.
- 📋 **Robust Manifest Validation**: Strictly validated `RefactorManifest`, `RefactorExecutionRequest`, and `RefactorExecutionResult` ensuring early detection of malformed configurations.
- 🔄 **100% Backward Compatibility**: Native support for dict-style indexing, tuple unpacking, and existing CLI interfaces with zero breaking changes.

### `v1.0.0` — Official Production Release *(2026-10-07)*
- 🚀 **Initial Stable Release**: First public release of `agy-agents` framework.
- 🔑 **Zero Hardcoded Secrets**: Clean credential design with strict `.gitignore` rules.
- ⚡ **Dual-Engine Auto-Resolution**: Transparent auto-switching between public Google Gemini API (`GEMINI_API_KEY`) and self-hosted LiteRouter gateway (`LITEROUTER_AUTH_KEY`).
- 📦 **Standardized Packaging**: `pyproject.toml` and `requirements.txt` configured with `hatchling` packaging for native `uv` and `pip` installation.
- 🧩 **Modular Python Exports**: Standalone `execute_research()` and `execute_refactor()` APIs ready for Model Context Protocol (MCP) servers.
- 🛠️ **Hybrid Refactoring CLI**: Direct single-file arguments and concurrent manifest processing with automatic markdown code fence stripping.
- 📄 **Sandbox Multi-Format Extraction**: Automatic compilation and extraction of `.md`, `.html`, `.pdf`, and `.docx` report artifacts.

---

## 📁 Repository Structure

```
agy-agents/
├── .env.example                    ← Universal environment template
├── pyproject.toml                  ← PEP 621 package metadata & dependencies
├── requirements.txt                ← Dependencies (python-dotenv, httpx, h2, pydantic)
├── CHANGELOG.md                    ← Keep a Changelog documentation
├── deep_research.py                ← Modular programmatic import shim
├── deep-research/
│   ├── deep-research.py            ← Deep research runner & execute_research()
│   ├── run.sh                      ← Cron-friendly batch runner
│   ├── README.md                   ← Deep research guide
│   ├── prompts/
│   │   ├── _template_guide.md      ← Prompt & 5-persona template
│   │   └── *.md                    ← Topic prompt files
│   └── reports/                    ← Generated reports (.md, .html, .pdf, .docx)
├── refactor/
│   ├── __init__.py                 ← Package exports for programmatic refactoring
│   ├── refactor.py                 ← Dual-engine hybrid refactorer
│   ├── prompt.txt                  ← Default refactoring instructions
│   ├── INSTRUCTIONS.md             ← Manifest workflow documentation
│   ├── manifests/
│   │   └── template.json           ← Manifest reference template
│   └── reports/                    ← Batch reports (gitignored)
├── .opencode/skills/agy-agents/    ← OpenCode / AI Assistant skill definitions
└── README.md                       ← Project documentation
```

---

## 🔍 SEO & Topic Tags

For GitHub repository maintainers, configure the following repository topics:  
`ai-agents` • `deep-research` • `code-refactoring` • `google-gemini` • `antigravity` • `literouter` • `mcp` • `python` • `autonomous-agents` • `llm-tools`

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for full details. Open to the global AI and developer community.
