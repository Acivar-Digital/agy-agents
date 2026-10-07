# agy-agents — Agent Instructions

This repository contains standalone agentic workflows that run against the Google Antigravity sandbox (`antigravity-preview-09-2026`) via the `/v1beta/interactions` endpoint.

It supports dual-engine inference:
1. **Direct Google Gemini API (Default for Community)**: `https://generativelanguage.googleapis.com/v1beta/interactions` using `GEMINI_API_KEY`.
2. **Self-Hosted Gateway (LiteRouter)**: `http://{LITEROUTER_HOST}:{LITEROUTER_PORT}/v1beta/interactions` using `LITEROUTER_AUTH_KEY`.

> **⚠️ DO NOT use `/v1/chat/completions` (OpenAI format).** Antigravity uses the `/v1beta/interactions` endpoint with a specialized payload and response schema.

## Endpoint contract

- **Payload:** `{"agent": "antigravity-preview-09-2026", "input": "...", "environment": "remote"}` (supports optional `previous_interaction_id` for stateful multi-turn continuation).
- **Response:** An interaction object with `object: "interaction"`, `status: "completed"`, an optional `environment_id` for downloading generated sandbox artifacts (.tar), and a `steps` array containing `thought` and `model_output` entries.

## Available Agents

### 1. Deep Research (Council Protocol)

A multi-persona research council workflow that leverages Antigravity's live web-search and sandbox execution capabilities to produce heavily cited whitepapers compiled natively into Markdown, HTML, PDF, and DOCX.

**Input:** A prompt file in `deep-research/prompts/` defining the topic and 5 specialized research personas.
**Output:** Structured reports saved in `deep-research/reports/`.
**Python Export:** `from deep_research import execute_research`

**Workflow:**
1. Configure credentials in `.env` (`GEMINI_API_KEY` or `LITEROUTER_AUTH_KEY`).
2. Create or edit a prompt file in `deep-research/prompts/` using `_template_guide.md` as the template.
   *(Tip: Ask your LLM to generate domain-tailored personas!)*
3. Run: `uv run python deep-research/deep-research.py PromptName`
4. Inspect the generated reports in `deep-research/reports/`.

### 2. Refactor (Autonomous Auto-Refactoring Pipeline)

An autonomous agent pipeline that reads Python files, enforces PEP 8, strict type hints, and clean architecture, and writes the refactored code to disk.

**Input:** A single Python file (`path/to/script.py`) OR batch manifests (`refactor/manifests/*.json`).
**Output:** Refactored `_refactored.py` files (or in-place), plus batch reports in `refactor/reports/`.
**Python Export:** `from refactor import execute_refactor`

**Workflow:**
1. Configure credentials in `.env`.
2. (Optional) Edit `refactor/prompt.txt` to customize refactoring rules for your team.
3. Run single file: `uv run python refactor/refactor.py path/to/script.py`
4. Run batch manifests: `uv run python refactor/refactor.py`
5. Review the diff with `git diff`.

**Agent Workflow Rules for Refactoring:**
- Always read the file first — do not send a file you haven't read.
- Output only raw code — remove Markdown fences and conversational text.
- Verify the output is valid Python — check for syntax errors before writing.
- Never delete required logic — only restructure, rename, and add type hints.
- Show the diff — run `git diff` after writing and present it to the user.
- Run tests if available — if `pytest` or `unittest` is present, run the relevant tests and fix any failures before finalizing.

## Key Files

- `deep-research/deep-research.py` — Deep research execution script (dual-engine + modular export)
- `deep-research/run.sh` — Batch runner for research prompts
- `deep-research/prompts/_template_guide.md` — Template for creating research prompts
- `refactor/prompt.txt` — System prompt (editable instructions for the agent)
- `refactor/refactor.py` — Dual-engine hybrid refactor script (CLI file arg + manifests + modular export)
- `refactor/INSTRUCTIONS.md` — Detailed multi-agent refactoring guide
- `.env.example` — Unified environment variables template

## Agent Workflow Rules

- When the user asks to "research a topic" or "conduct deep research," use the Deep Research agent.
- When the user asks to "refactor code" or "improve code quality," use the Refactor agent.
- Do not run research or refactoring scripts in the background without checking output.
- Always encourage tailoring personas and prompts to match specific domain needs.
