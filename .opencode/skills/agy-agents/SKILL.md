---
name: agy-agents
description: Use the agy-agents toolkit — run the Deep Research agent, create prompts, transform results, auto-refactor Python code, or connect via FastMCP server with async job polling and live HTTP artifact delivery. Supports Google Gemini API directly or via self-hosted LiteRouter.
compatibility: Requires Python 3.10+, uv or pip, and GEMINI_API_KEY (or LiteRouter gateway).
license: MIT
metadata:
  version: "1.3.0"
  author: Acivar Digital
---

# agy-agents — Agent Toolkit Skill

This skill teaches agents how to use the **agy-agents** project: a collection of standalone agentic workflows and a sovereign FastMCP server connecting to Google's Antigravity sandbox (`antigravity-preview-09-2026`) via `/v1beta/interactions`.

It supports dual-engine inference:
1. **Direct Google Gemini API (Default for Community)**: `GEMINI_API_KEY`
2. **Self-Hosted Gateway (LiteRouter)**: `LITEROUTER_AUTH_KEY` + `LITEROUTER_HOST` (`http://literouter.lan:7766` or `127.0.0.1:7766`)

---

## Architecture & Interfaces

The toolkit provides two primary operational interfaces:
1. **Model Context Protocol (FastMCP Server)**: Seamless integration into agent harnesses (`omp`, OpenCode, Claude Desktop, Cursor) with asynchronous background job polling to eliminate 60s client timeouts.
2. **Direct Python CLI / Scripts**: Direct execution of research council sprints and Python code refactoring pipelines.

---

## Sovereign MCP Tools (`agy-mcp`)

The MCP server runs via `agy-mcp` (or `uv run python mcp_server.py`) and is hosted on `vps466a` (port `7788`, DNS `agy-agents.lan`). It implements **dual transport** (Streamable HTTP `POST /sse` / `POST /mcp` for `omp` and legacy SSE `GET /sse`).

### 1. `check_gateway_health`
Probes connectivity, latency, and authorization against the active inference gateway (`literouter` or `gemini`).
- **When to use**: Before initiating long runs or diagnosing connection drops.
- **Output**: HTTP status, response time in ms, resolved endpoint URL, and status message.

### 2. `list_research_prompts`
Discovers all available institutional prompt stems in `deep-research/prompts/`.
- **When to use**: To inspect existing templates (e.g. `Direction_of_JPY`) or discover topic stems for research.

### 3. `prepare_research_prompt`
Generates a Citi-grade institutional 5-persona research prompt file.
- **Parameters**: `topic` (str), `stem` (optional str).
- **Output**: Path to saved prompt (`deep-research/prompts/<stem>.md`), preview, and ready-to-run CLI invocation.

### 4. `start_research`
Launches an autonomous 5-persona deep research council in the background.
- **Parameters**: `topic_or_stem` (str).
- **Behavior**: Returns immediately with a unique `job_id` (`job_xxxxxxxx`) to prevent 60-second client-side RPC disconnects.

### 5. `get_research_status`
Polls the execution state of an asynchronous research job or retrieves a finished report.
- **Parameters**: `job_id` (str — accepts either `job_xxxxxxxx` or a prompt stem like `Direction_of_JPY`).
- **Return Content**:
  - `status`: `"running"`, `"completed"`, or `"failed"`.
  - `#### Executive Summary`: High-level synthesis, committee consensus, and core findings.
  - `#### Full Markdown Report`: **In-band delivery** of the complete whitepaper directly into the LLM context window.
  - `#### Artifacts & Downloads`: Local filesystem paths and live LAN HTTP URLs (`http://agy-agents.lan:7788/reports/<file>.md|.pdf|.docx`).

### 6. `refactor_code`
Autonomously modernizes and cleans Python code enforcing strict type hints, docstrings, and PEP 8 standards. Fast synchronous tool (5-15s).
- **Parameters**: `code` (str), `instructions` (optional str).
- **Output**: Syntactically validated cleaned Python code and unified diff summary.

---

## Report Delivery & Artifact Consumption

When consuming deep research results, client LLMs have three pickup channels:

| Channel | Method | Use Case |
|---|---|---|
| **In-Band MCP Context** | `get_research_status(job_id)` | Primary: LLM immediately ingests `#### Full Markdown Report` without external file reads. |
| **LAN HTTP Static Route** | `http://agy-agents.lan:7788/reports/{filename}` | Direct browser or LLM URL fetch for `.md`, `.html`, `.pdf`, and `.docx` artifacts. |
| **Host Filesystem** | `deep-research/reports/{filename}` | Local filesystem access on the server hosting `agy-agents`. |

---

## Client MCP Configuration

### oh-my-pi (`omp`)
`omp` imports servers from OpenCode via `enabledProviders: [opencode]` in `~/.omp/agent/config.yml`. Because OpenCode configures servers as `"enabled": false` by default, `agy-agents` must be force-enabled in `~/.omp/agent/mcp.json`:

```json
{
  "enabledServers": [
    "agy-agents"
  ]
}
```

In `~/.config/opencode/opencode.json`:
```json
{
  "mcpServers": {
    "agy-agents": {
      "type": "remote",
      "url": "http://192.168.50.10:7788/sse",
      "enabled": false
    }
  }
}
```

### Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "agy-agents": {
      "url": "http://192.168.50.10:7788/sse"
    }
  }
}
```

---

## Direct CLI Usage

### Deep Research Council

```bash
# Run research on an existing prompt stem
uv run python deep-research/deep-research.py Direction_of_JPY

# Results saved to deep-research/reports/:
# - Direction_of_JPY_YYYYMMDD_HHMM.md (Full whitepaper)
# - Direction_of_JPY_YYYYMMDD_HHMM.pdf / .html / .docx
# - Direction_of_JPY_YYYYMMDD_HHMM_raw.json (Sandbox steps)
```

### Python Code Refactor

```bash
# Single file direct refactor
uv run python refactor/refactor.py path/to/script.py

# Custom prompt
uv run python refactor/refactor.py path/to/script.py --prompt "Migrate to Pydantic v2 schemas and strict typing"

# Overwrite in-place
uv run python refactor/refactor.py path/to/script.py --inplace

# Batch processing via manifests
uv run python refactor/refactor.py
```

### Refactoring Safety Guidelines

When executing code refactoring:
1. **Read before edit**: Always inspect existing code and invariants first.
2. **Strict Python syntax**: Verify AST syntax before writing back to disk.
3. **Preserve business logic**: Refactor structure, type annotations, and docstrings; do not alter functional guarantees.
4. **Present unified diffs**: Always review diffs after refactoring.
5. **Run test suites**: Run unit and integration tests (`uv run python -m unittest`) to prove zero regressions.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(empty)* | Google Gemini API key (Public community mode) |
| `LITEROUTER_HOST` | `literouter.lan` | Host of the LiteRouter gateway |
| `LITEROUTER_PORT` | `7766` | Port of the LiteRouter gateway |
| `LITEROUTER_AUTH_KEY` | *(empty)* | LiteRouter authorization key (Self-hosted mode) |
| `AGENT_MODEL` | `antigravity-preview-09-2026` | Agent model / profile name |
| `MCP_HOST` | `0.0.0.0` | Bind host for FastMCP server |
| `MCP_PORT` | `7788` | Bind port for FastMCP server |
