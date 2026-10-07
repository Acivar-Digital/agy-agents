# agy-agents — LLM Orientation & Agent Instructions

`agy-agents` is an autonomous AI agent framework designed for institutional-grade intelligence gathering and production-ready code modernization. It operates against the Google Antigravity Sandbox (`antigravity-preview-09-2026`) via the stateful `/v1beta/interactions` API.

---

## 🧭 Repository At-A-Glance

| Component | Primary Entrypoint | Description |
| :--- | :--- | :--- |
| **FastMCP Server** | `mcp_server.py` (`agy-mcp`) | 6 sovereign tools with a hybrid async architecture (solves 60s client timeouts). |
| **Deep Research Council** | `deep_research.py` / `deep-research/` | 5-persona research panel, 50 web searches, multi-format export (.md, .html, .pdf, .docx). |
| **Code Refactoring** | `refactor/` (`agy-refactor`) | Autonomous PEP 8, strict type hints, and clean architecture (single-file or batch manifests). |
| **Pydantic V2 Contracts** | Core schemas across all modules | Strict data contracts (`pydantic>=2.10.0`) for requests, responses, manifests, and jobs. |

---

## ⚡ Inference Architecture & Dual-Engine Routing

Inference targets the stateful Google Antigravity endpoint (`POST /v1beta/interactions`):
> **⚠️ NEVER use `/v1/chat/completions` (OpenAI format).** Antigravity uses `/v1beta/interactions` with `{"agent": "antigravity-preview-09-2026", "input": "...", "environment": "remote"}` and returns `steps` + sandbox `environment_id`.

Resolution order in `get_provider_config("auto")`:
1. `PROVIDER=literouter` (in `.env`) or `LITEROUTER_AUTH_KEY` → routes to **LiteRouter gateway** (`http://literouter.lan:7766` or `http://127.0.0.1:7766`).
2. `PROVIDER=gemini` or `GEMINI_API_KEY` → routes directly to **Google Gemini API** (`https://generativelanguage.googleapis.com/v1beta/interactions`).

---

## 🔌 Model Context Protocol (FastMCP Server)

The MCP server is implemented in `mcp_server.py` and exposed via the `agy-mcp` CLI command.

### Hybrid Async Architecture
Standard MCP clients (Claude Desktop, Cursor, OpenCode) enforce a **hard 60-second RPC timeout**. Deep research takes 3–8 minutes. The MCP server solves this via non-blocking job coordination:

1. **`prepare_research_prompt`** (Fast Sync, `<1s`):
   - Generates a tailored 5-persona research prompt file in `deep-research/prompts/<stem>.md`.
   - Returns file path, preview, and the exact background CLI command.
2. **`start_research`** (Async Background, `<1s`):
   - Spawns background worker executing the research council.
   - Immediately returns a unique `job_id` (`job_xxxxxxxx`), preventing timeout drops.
3. **`get_research_status`** (Polling, `<50ms`):
   - Reads `.jobs/<job_id>.json`.
   - While running: returns `status: "running"` and elapsed seconds.
   - When finished: returns `status: "completed"`, executive summary, and paths to `.md`, `.html`, `.pdf`, `.docx`.
4. **`refactor_code`** (Fast Sync, `5–15s`):
   - Autonomously refactors Python code, validates AST syntax, and outputs clean code + unified diff.
5. **`list_research_prompts`** (Discovery, `<50ms`):
   - Scans `deep-research/prompts/*.md` and returns available templates and ready-to-run topics.
6. **`check_gateway_health`** (Diagnostic, `<50ms`):
   - Probes `literouter.lan:7766` or Gemini base URL for latency and reachability.

### Client Configuration (OpenCode, Claude Desktop, Cursor)

**Intranet SSE / HTTP (`http://agy-agents.lan:7788/sse` or `/mcp`):**
```json
{
  "mcpServers": {
    "agy-agents": {
      "url": "http://agy-agents.lan:7788/sse"
    }
  }
}
```

**SSH Stdio Transport (`opencode.json`):**
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

---

## 🔬 Deep Research Council Workflow

A 5-persona research panel that executes 50 live Google searches and synthesizes institutional-grade whitepapers.

- **Prompt Location:** `deep-research/prompts/<PromptName>.md` (Template: `_template_guide.md`).
- **Generated Reports:** `deep-research/reports/<PromptName>_<timestamp>/` containing:
  - `report.md`, `report.html`, `report.pdf`, `report.docx`
  - Raw JSON execution log: `<PromptName>_<timestamp>_raw.json`
- **CLI Commands:**
  ```bash
  # Foreground execution
  uv run python deep-research/deep-research.py PromptName

  # Background execution (recommended for long runs)
  nohup uv run agy-research PromptName > PromptName.log 2>&1 &
  ```
- **Python Import:**
  ```python
  from deep_research import execute_research
  result = execute_research(prompt_content="...", prompt_stem="my_topic")
  print("Artifacts:", result.extracted_files)
  ```

---

## 🛠️ Autonomous Code Refactoring Workflow

Enforces clean architecture, PEP 8, and strict typing without conversational fluff.

- **CLI Single File:**
  ```bash
  # Refactor to script_refactored.py
  uv run agy-refactor path/to/script.py

  # Refactor in place
  uv run agy-refactor path/to/script.py --inplace
  ```
- **Batch Manifest Mode:**
  Processes all manifests defined in `refactor/manifests/*.json`:
  ```bash
  uv run python refactor/refactor.py
  ```
- **Python Import:**
  ```python
  from refactor import execute_refactor
  result = execute_refactor(code_content="def add(a, b): return a + b", prompt="Add type hints")
  print(result.refactored_code)
  ```

---

## 🖥️ VPS Deployment Topology (`vps466a`)

- **Host & Path:** `vps466a:/home/vps466a/services/agy-agents`
- **Intranet MCP Endpoint:** `http://agy-agents.lan:7788/sse` (SSE) / `http://agy-agents.lan:7788/mcp` (Streamable HTTP), bound to `0.0.0.0:7788` (`192.168.50.10:7788`).
- **Active Gateway:** Local LiteRouter gateway at `http://literouter.lan:7766` (`127.0.0.1:7766`).
- **Remote Environment:** Python managed via `/home/vps466a/.local/bin/uv`.
- **Sync Command from Local:**
  ```bash
  rsync -avz --exclude='.git' --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.jobs' ./ vps466a:services/agy-agents/
  ```

---

## 📂 Key Files & Directories

```
agy-agents/
├── AGENTS.md                       ← This master orientation document
├── README.md                       ← Public developer & user documentation
├── CHANGELOG.md                    ← Release history (v1.2.0 FastMCP)
├── pyproject.toml                  ← Build targets, deps, CLI scripts (agy-research, agy-refactor, agy-mcp)
├── mcp_server.py                   ← FastMCP server implementation (6 tools, async job manager)
├── tests/
│   └── test_mcp_server.py          ← Test suite for MCP contracts, tools, and execution
├── deep_research.py                ← Root import shim for execute_research()
├── deep-research/
│   ├── deep-research.py            ← Deep research runner & sandbox extractor
│   ├── prompts/                    ← Prompt library (*.md) and _template_guide.md
│   └── reports/                    ← Generated whitepapers & artifact tarballs (gitignored)
├── refactor/
│   ├── __init__.py                 ← Package exports for execute_refactor()
│   ├── refactor.py                 ← Dual-engine single-file & batch refactorer
│   ├── prompt.txt                  ← System prompt for refactoring standards
│   └── manifests/                  ← Batch refactoring manifests
└── .jobs/                          ← Background job state registry (.jobs/<id>.json, gitignored)
```

---

## 🎯 LLM Instructions When Operating in This Repo

1. **Do Not Re-scan the Codebase:** This document provides the complete architecture and entrypoints.
2. **For Deep Research:** Use `prepare_research_prompt` to generate prompt files, or run via `start_research` (MCP) / `nohup uv run agy-research <stem> &` (CLI).
3. **For Code Refactoring:** Use `refactor_code` (MCP) or `uv run agy-refactor <file>` (CLI).
4. **For Gateway Diagnostics:** Check LiteRouter health via `check_gateway_health` or probe `http://literouter.lan:7766/health`.
5. **Git Rules:** Local-only by default; never run git push without explicit user instruction.
