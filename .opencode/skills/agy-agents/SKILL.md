---
name: agy-agents
description: Use the agy-agents toolkit — run the Deep Research agent, create prompts, transform results, or auto-refactor Python code. Supports Google Gemini API directly or via self-hosted LiteRouter.
compatibility: Requires Python 3.10+, uv or pip, and GEMINI_API_KEY (or LiteRouter gateway).
license: MIT
metadata:
  version: "1.1.0"
  author: Acivar Digital
---

# agy-agents — Agent Toolkit Skill

This skill teaches agents how to use the **agy-agents** project: a collection of standalone agentic workflows that run against Google's Antigravity sandbox (`antigravity-preview-09-2026`) via the `/v1beta/interactions` endpoint.

It supports dual-engine execution:
1. **Direct Google Gemini API (Default for Community)**: `GEMINI_API_KEY`
2. **Self-Hosted Gateway (LiteRouter)**: `LITEROUTER_AUTH_KEY` + `LITEROUTER_HOST`

## Available Agents

### 1. Deep Research (Council Protocol)

A multi-persona research council workflow that leverages Antigravity's live web-search and sandbox execution to produce heavily cited, institutional-grade whitepapers compiled natively into Markdown, HTML, PDF, and DOCX.

### 2. Refactor (Autonomous Auto-Refactoring Pipeline)

An autonomous agent pipeline that reads Python files, sends them to Antigravity for clean refactoring (PEP 8, type hints, docstrings, clean architecture), and writes the results back to disk. Supports both direct CLI execution and manifest-driven batch processing.

## How to Use — Deep Research

### Prerequisites

Configure credentials in `.env`:
```bash
cp .env.example .env
# Set GEMINI_API_KEY (or LITEROUTER_AUTH_KEY)
```

### Create a Research Prompt

Prompts live in `deep-research/prompts/`. Each prompt defines a topic and a 5-persona research council.

To create a new prompt:
1. Copy `deep-research/prompts/_template_guide.md` to a new file in `deep-research/prompts/` (e.g., `deep-research/prompts/My_Topic.md`).
2. Fill in the topic, customize the 5 personas, and set the rubric target.
3. *Tip for users & agents:* Use an LLM to generate domain-tailored adversarial personas.

### Run the Deep Research Agent

```bash
uv run python deep-research/deep-research.py My_Topic
```

The agent will:
- Run a 50-source research sprint across 5 personas
- Aggregate findings
- Perform supervisor review with revision cycles
- Output Markdown, HTML, PDF, and DOCX files in `deep-research/reports/`

**Important:** Do not run the agent in the background (`&`). Wait for it to finish and verify output.

### Review Results

Reports are saved in `deep-research/reports/`:
- `My_Topic_YYYYMMDD_HHMM.md` — Markdown whitepaper
- `My_Topic_YYYYMMDD_HHMM.html` / `.pdf` / `.docx` — Compiled report formats
- `My_Topic_YYYYMMDD_HHMM_raw.json` — Raw interaction log

## How to Use — Refactor

### Mode 1: Single File Direct CLI

```bash
# Refactors the file into path/to/script_refactored.py
uv run python refactor/refactor.py path/to/script.py

# Optional: provide custom prompt on the fly
uv run python refactor/refactor.py path/to/script.py --prompt "Refactor to Pydantic v2 schemas and strict typing"

# Optional: overwrite in-place
uv run python refactor/refactor.py path/to/script.py --inplace
```

### Mode 2: Batch Processing via Manifests

```bash
# Run all manifests in refactor/manifests/*.json
uv run python refactor/refactor.py

# Or run a specific manifest
uv run python refactor/refactor.py --manifest refactor/manifests/my_task.json
```

### Safety Rules for Refactoring

When a user asks to "refactor code" or "improve code quality":
1. **Always read the file first** — do not send a file you haven't read.
2. **Output only raw code** — remove Markdown fences and conversational text.
3. **Verify the output is valid Python** — check for syntax errors before writing.
4. **Never delete required logic** — only restructure, rename, and add type hints.
5. **Show the diff** — run `git diff` after writing and present it to the user.
6. **Run tests if available** — if `pytest` or `unittest` is present, run the relevant tests.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(empty)* | Google Gemini API key (Public community mode) |
| `LITEROUTER_HOST` | `literouter.lan` | Host of the LiteRouter gateway |
| `LITEROUTER_PORT` | `7766` | Port of the LiteRouter gateway |
| `LITEROUTER_AUTH_KEY` | *(empty)* | LiteRouter authorization key (Self-hosted mode) |
| `AGENT_MODEL` | `antigravity-preview-09-2026` | Agent model / profile name |
