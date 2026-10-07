---
name: agy-agents
description: Use the agy-agents toolkit — run the Deep Research agent, prepare prompts, collect Markdown (.md) reports, or auto-refactor Python code via CLI and FastMCP instruction wrapper. Supports Google Gemini API directly or via self-hosted LiteRouter.
compatibility: Requires Python 3.10+, uv or pip, and GEMINI_API_KEY (or LiteRouter gateway).
license: MIT
metadata:
  version: "1.3.0"
  author: Acivar Digital
---

# agy-agents — Agent Toolkit Skill

This skill teaches agents how to use the **agy-agents** project: a collection of standalone agentic workflows and a FastMCP instruction wrapper connecting to Google's Antigravity sandbox (`antigravity-preview-09-2026`) via `/v1beta/interactions`.

It supports dual-engine inference:
1. **Direct Google Gemini API (Default for Community)**: `GEMINI_API_KEY`
2. **Self-Hosted Gateway (LiteRouter)**: `LITEROUTER_AUTH_KEY` + `LITEROUTER_HOST` (`http://literouter.lan:7766` or `127.0.0.1:7766`)

---

## How Deep Research Works (Simplified CLI-Trigger Workflow)

1. **Prepare or Select Prompt**: Prompts live in `deep-research/prompts/<stem>.md`. Use `prepare_research_prompt` or `start_research` (or create the `.md` prompt directly) to prepare the 5-persona research council prompt.
2. **Trigger the CLI Directly**: Run the CLI script via your `bash` tool (do **NOT** use `&` or `nohup`; set `timeout: 600`):
   ```bash
   uv run python deep-research/deep-research.py <stem> --provider literouter
   ```
3. **Wake Up on Exit Code `0` & Collect `.md` Report**:
   - The CLI runs the 5-persona research sprint and synthesizes the report **only in Markdown (`.md`) format** (no slow HTML/PDF/DOCX compilation).
   - When finished, the script exits with **exit code `0`** (which automatically wakes the LLM up if backgrounded by the harness) and prints verbose output telling the LLM the exact path to collect the `.md` report:
     ```text
     ==================================================================
     ✅ DEEP RESEARCH COMPLETE (EXIT CODE: 0)
     ==================================================================
     ⏱️  ELAPSED TIME:               <seconds> seconds
     📄 COLLECT MARKDOWN REPORT AT: /path/to/deep-research/reports/<stem>_<YYYYMMDD_HHMM>.md
     💾 RAW INTERACTION JSON:       /path/to/deep-research/reports/<stem>_<YYYYMMDD_HHMM>_raw.json
     ==================================================================
     👉 LLM ACTION REQUIRED: Read the Markdown report at `<path>.md` to consume the full research findings.
     ```
   - Read that `.md` file directly (or call `get_research_status(job_id="<stem>")`) to consume the report.

---

## Sovereign MCP Tools (`agy-mcp`)

The MCP server (`mcp_server.py`) acts as an instruction & prompt-preparation wrapper on port `7788` (`http://agy-agents.lan:7788/sse`). All tool inputs enforce `ConfigDict(extra="forbid", validate_assignment=True)`.

### 1. `check_gateway_health`
Probes connectivity, latency, and authorization against the active inference gateway (`literouter` or `gemini`).
- **Parameters**: None.

### 2. `list_research_prompts`
Lists all available structured research prompt templates and stems in `deep-research/prompts/`.
- **Parameters**: None.

### 3. `prepare_research_prompt`
Generates and validates an institutional 5-persona research prompt file in `deep-research/prompts/<prompt_stem>.md`, explains how the workflow operates, and returns the exact CLI command to trigger.
- **Parameters**:
  - `topic` (`str`, required): Core research subject or question for the 5-persona research council.
  - `prompt_stem` (`str`, default `"custom_research"`): File stem for the generated prompt file (e.g. `"Direction_of_JPY"`).
  - `custom_rubric` (`str | None`, default `None`): Optional specific research guidelines, scope limits, or focus domains.

### 4. `start_research`
Instruction wrapper that prepares `deep-research/prompts/<prompt_stem>.md` (if not already present) and returns step-by-step instructions telling the LLM how the workflow operates and the exact CLI command (`uv run python deep-research/deep-research.py <stem>`) to trigger so it wakes up on exit code `0` to collect the `.md` report.
- **Parameters**:
  - `prompt_stem_or_topic` (`str`, required): Existing prompt stem (e.g. `"Direction_of_JPY"`) or a research topic to sculpt dynamically.
  - `prompt_stem` (`str`, default `"custom_research"`): File stem to use if a new prompt is sculpted from a topic.
  - `custom_rubric` (`str | None`, default `None`): Optional specific rubric or focus if creating a new prompt dynamically.
  - `timeout_seconds` (`float`, default `600.0`): Recommended CLI timeout in seconds.

### 5. `get_research_status`
Retrieves the latest completed Markdown (`.md`) report for a prompt stem or `job_id`, returning the `.md` file path, LAN HTTP link (`http://agy-agents.lan:7788/reports/<file>.md`), executive summary, and full in-band Markdown report content.
- **Parameters**:
  - `job_id` (`str`, required): Prompt stem (e.g. `"Direction_of_JPY"`) or job ID returned by `start_research`.

### 6. `refactor_code`
Autonomously modernizes and cleans Python code enforcing strict type hints, docstrings, and PEP 8 standards. Fast synchronous tool (5–15s).
- **Parameters**:
  - `code` (`str`, required): Python source code to refactor.
  - `filename` (`str`, default `"target.py"`): Target filename hint used for structural context.
  - `instructions` (`str | None`, default `None`): Custom refactoring instructions.

---

## Direct CLI Usage

### Deep Research Council (`.md` Output Only)

```bash
# Run research on a prompt stem via LiteRouter
uv run python deep-research/deep-research.py Direction_of_JPY --provider literouter
```

### Python Code Refactor

```bash
# Single file direct refactor
uv run python refactor/refactor.py path/to/script.py

# Custom prompt
uv run python refactor/refactor.py path/to/script.py --prompt "Migrate to Pydantic v2 schemas and strict typing"

# Overwrite in-place
uv run python refactor/refactor.py path/to/script.py --inplace
```

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
