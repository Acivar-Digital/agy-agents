---
name: agy-agents
description: Use the agy-agents toolkit — run the Deep Research agent, create prompts, transform results, or auto-refactor Python code. Use when the user asks to conduct deep research, refactor code, or use the agy-agents project.
compatibility: Requires Python 3.10+, uv, and a running LiteRouter gateway (port 7766) with Antigravity sandbox access.
license: MIT
metadata:
  version: "1.0.0"
  author: Acivar Digital
---

# agy-agents — Agent Toolkit Skill

This skill teaches agents how to use the **agy-agents** project: a collection of standalone agentic workflows that run against the LiteRouter API Gateway using Google's Antigravity sandbox.

## Available Agents

### 1. Deep Research (Institutional Protocol)

A multi-persona research council workflow that leverages Antigravity's web-search and sandbox execution to produce heavily cited, institutional-grade whitepapers.

### 2. Refactor (Auto-Refactoring Pipeline)

An autonomous agent pipeline that reads Python files, sends them to Antigravity for clean refactoring (PEP 8, type hints, docstrings, clean architecture), and writes the results back to disk.

## How to Use — Deep Research

### Prerequisites

Ensure the LiteRouter gateway is running locally on port 7766:

```bash
bash scripts/start.sh
# OR
bun run src/index.ts
```

Configure the environment:

```bash
cp deep-research/.env.example deep-research/.env
# Edit deep-research/.env with your LITEROUTER_PORT and LITEROUTER_AUTH_KEY
```

### Create a Research Prompt

Prompts live in `deep-research/prompts/`. Each prompt defines a topic and a 5-persona research council.

To create a new prompt:
1. Copy `deep-research/prompts/_template_guide.md` to a new file in `deep-research/prompts/` (e.g., `deep-research/prompts/My_Topic.md`).
2. Fill in the topic, customize the 5 personas, and set the rubric target.
3. Save the file — no extensions needed (the `.md` suffix is conventional).

### Run the Deep Research Agent

```bash
uv run python deep-research/deep-research.py My_Topic
```

This dispatches the prompt to the Antigravity agent via LiteRouter. The agent will:
- Run a 50-source research sprint across 5 personas
- Aggregate findings
- Perform a supervisor review with one revision cycle
- Output a structured Markdown whitepaper

**Important:** Do not run the agent in the background (`&`). You must wait for it to finish so you can verify the output.

### Review Results

Reports are saved in `deep-research/reports/` with timestamps:
- `My_Topic_YYYYMMDD_HHMM.md` — the final whitepaper
- `My_Topic_YYYYMMDD_HHMM_raw.json` — the raw API response for debugging

### Re-generate from Raw JSON (Offline Transform Mode)

If you want to re-render the Markdown report without hitting the API again:

```bash
uv run python deep-research/deep-research.py --transform deep-research/reports/My_Topic_YYYYMMDD_HHMM_raw.json
```

### Batch Execution

Configure `deep-research/run.sh` with your list of prompts, then run:

```bash
bash deep-research/run.sh
```

## How to Use — Refactor

### Prerequisites

The LiteRouter gateway must be running on port 7766 with Antigravity sandbox access.

```bash
cp refactor/.env.example refactor/.env
```

### Refactor a Single File

```bash
uv run python refactor/refactor.py path/to/script.py
```

This reads the system prompt from `refactor/prompt.txt` (editable to customize refactoring instructions), sends the file to the Antigravity agent, and saves the refactored version as `script_refactored.py` in the same directory.

To use a custom prompt file:

```bash
uv run python refactor/refactor.py path/to/script.py --prompt path/to/custom_prompt.txt
```

### Refactor an Entire Directory

```bash
uv run python refactor/refactor.py path/to/src/
```

This traverses all `.py` files in the directory recursively, refactors each one individually, and generates a batch report at `refactor/reports/batch_report_*.md`.

### Offline Transform Mode

Re-render code from a saved raw API response without hitting the API:

```bash
uv run python refactor/refactor.py --transform refactor/reports/some_run_raw.json
```

### Safety Rules

When a user asks to "refactor code" or "improve code quality":

1. **Always read the file first** — do not send a file you haven't read.
2. **Output only raw code** — remove Markdown fences and conversational text.
3. **Verify the output is valid Python** — check for syntax errors before writing.
4. **Never delete required logic** — only restructure, rename, and add type hints.
5. **Show the diff** — run `git diff` after writing and present it to the user.
6. **Run tests if available** — if `pytest` or `unittest` is present, run the relevant tests and fix any failures before finalizing.

## Agent-Specific Instructions

### When to Use Each Agent

| Request | Agent |
|---|---|
| "research a topic" / "conduct deep research" | Deep Research |
| "refactor code" / "improve code quality" | Refactor |

### Research Workflow Rules

1. **Target Topic Alignment:** Create a prompt file in `deep-research/prompts/` using the template guide. Customize all 5 personas for the user's domain.
2. **Execution:** Run `uv run python deep-research/deep-research.py PromptName`. Wait for completion — do not background the process.
3. **Verification:** Check that the report exists in `deep-research/reports/`. Read it to confirm correctness before delivering to the user.

### Refactor Workflow Rules

1. **Read first:** Always read the target file before sending it to the agent.
2. **Wait for completion:** Do not run refactoring in the background.
3. **Review the diff:** Always run `git diff` after the agent writes the refactored file.
4. **Test if possible:** If a test suite exists, run it on the refactored files before finalizing.

## Project Structure

```
agy-agents/
├── .opencode/skills/agy-agents/
│   └── SKILL.md          ← This file
├── deep-research/
│   ├── deep-research.py  ← Core Python script
│   ├── run.sh            ← Batch runner
│   ├── .env.example      ← Environment template
│   ├── prompts/
│   │   ├── _template_guide.md  ← Prompt template guide
│   │   └── *.md             ← User prompts (Topic_Name.md)
│   └── reports/           ← Generated reports (gitignored)
│       ├── *.md
│       └── *_raw.json
├── refactor/
│   ├── prompt.txt         ← Default system prompt (editable)
│   ├── refactor.py        ← Reusable auto-refactor script
│   ├── .env.example       ← Environment template
│   ├── INSTRUCTIONS.md    ← Multi-agent refactoring guide
│   └── reports/           ← Generated reports (gitignored)
│       └── batch_report_*.md
├── README.md
├── AGENTS.md
└── .gitignore
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LITEROUTER_PORT` | `7766` | Port of the LiteRouter gateway |
| `LITEROUTER_AUTH_KEY` | `YOUR_KEY_HERE` | Bearer token for LiteRouter auth |