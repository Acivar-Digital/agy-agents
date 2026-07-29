# agy-agents — Agent Instructions

This repository contains standalone agentic workflows and tools designed to run against the LiteRouter API Gateway using Google's Antigravity sandbox (`antigravity-preview-05-2026`).

## Available Agents

### 1. Deep Research (Institutional Protocol)

A multi-persona research council workflow that leverages Antigravity's web-search and sandbox execution capabilities to produce heavily cited, institutional-grade whitepapers.

**Input:** A prompt file in `deep-research/prompts/` defining the topic and 5 research personas.
**Output:** A structured Markdown whitepaper saved in `deep-research/reports/`.

**Workflow:**
1. Ensure the LiteRouter gateway is running on port 7766.
2. Create or edit a prompt file in `deep-research/prompts/` using `_template_guide.md` as the structural template.
3. Run: `uv run python deep-research/deep-research.py PromptName`
4. Verify the report was generated in `deep-research/reports/`.

### 2. Refactor (Auto-Refactoring Pipeline)

An autonomous agent pipeline that reads Python files, sends them to the Antigravity agent for PEP 8 refactoring, type hints, and clean architecture improvements, and writes the results back to disk.

**Input:** A Python file path or directory path.
**Output:** Refactored `_refactored.py` files alongside originals, plus a batch report in `refactor/reports/`.

**Workflow:**
1. Ensure the LiteRouter gateway is running on port 7766.
2. Run: `uv run python refactor/refactor.py <path>`
3. Review the diff with `git diff`.
4. Commit the refactored files if satisfied.

**Agent Workflow Rules for Refactoring:**
- Always read the file first — do not send a file you haven't read.
- Output only raw code — remove Markdown fences and conversational text.
- Verify the output is valid Python — check for syntax errors before writing.
- Never delete required logic — only restructure, rename, and add type hints.
- Show the diff — run `git diff` after writing and present it to the user.
- Run tests if available — if `pytest` or `unittest` is present, run the relevant tests and fix any failures before finalizing.

## Key Files

- `deep-research/deep-research.py` — Deep research execution script
- `deep-research/run.sh` — Batch runner for research prompts
- `deep-research/prompts/_template_guide.md` — Template for creating research prompts
- `refactor/refactor.py` — Reusable auto-refactor script
- `refactor/INSTRUCTIONS.md` — Detailed multi-agent refactoring guide
- `refactor/.env.example` — Environment template for refactoring

## Agent Workflow Rules

- When the user asks to "research a topic" or "conduct deep research," always use the Deep Research agent.
- When the user asks to "refactor code" or "improve code quality," always use the Refactor agent.
- Do not run research or refactoring scripts in the background — wait for them to complete and verify the output.
- Always customize all 5 personas to match the user's specific domain for research prompts.