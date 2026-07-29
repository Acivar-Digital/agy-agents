---
name: agy-agents
description: Use the agy-agents toolkit — run the Deep Research agent, create prompts, and transform results via LiteRouter + Antigravity. Use when the user asks to conduct deep research, run a research agent, or use the agy-agents project.
compatibility: Requires Python 3.10+, uv, and a running LiteRouter gateway (port 7766) with Antigravity sandbox access.
license: MIT
metadata:
  version: "1.0.0"
  author: Acivar Digital
---

# agy-agents — Agent Toolkit Skill

This skill teaches agents how to use the **agy-agents** project: a collection of standalone agentic workflows that run against the LiteRouter API Gateway using Google's Antigravity sandbox.

## Available Agents

### Deep Research (Institutional Protocol)

A multi-persona research council workflow that leverages Antigravity's web-search and sandbox execution to produce heavily cited, institutional-grade whitepapers.

## How to Use — Step by Step

### 1. Prerequisites

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

### 2. Create a Research Prompt

Prompts live in `deep-research/prompts/`. Each prompt defines a topic and a 5-persona research council.

To create a new prompt:
1. Copy `deep-research/prompts/_template_guide.md` to a new file in `deep-research/prompts/` (e.g., `deep-research/prompts/My_Topic.md`).
2. Fill in the topic, customize the 5 personas, and set the rubric target.
3. Save the file — no extensions needed (the `.md` suffix is conventional).

### 3. Run the Deep Research Agent

Execute the script with the prompt name (without `.md`):

```bash
uv run python deep-research/deep-research.py My_Topic
```

This dispatches the prompt to the Antigravity agent via LiteRouter. The agent will:
- Run a 50-source research sprint across 5 personas
- Aggregate findings
- Perform a supervisor review with one revision cycle
- Output a structured Markdown whitepaper

**Important:** Do not run the agent in the background (`&`). You must wait for it to finish so you can verify the output.

### 4. Review Results

Reports are saved in `deep-research/reports/` with timestamps:
- `My_Topic_YYYYMMDD_HHMM.md` — the final whitepaper
- `My_Topic_YYYYMMDD_HHMM_raw.json` — the raw API response for debugging

### 5. Re-generate from Raw JSON (Offline Transform Mode)

If you want to re-render the Markdown report without hitting the API again:

```bash
uv run python deep-research/deep-research.py --transform deep-research/reports/My_Topic_YYYYMMDD_HHMM_raw.json
```

### 6. Batch Execution

Configure `deep-research/run.sh` with your list of prompts, then run:

```bash
bash deep-research/run.sh
```

## Agent-Specific Instructions

When a user asks you to "conduct deep research", "research a topic", or "run the deep research tool":

1. **Target Topic Alignment:** Create a prompt file in `deep-research/prompts/` using the template guide. Customize all 5 personas for the user's domain.
2. **Execution:** Run `uv run python deep-research/deep-research.py PromptName`. Wait for completion — do not background the process.
3. **Verification:** Check that the report exists in `deep-research/reports/`. Read it to confirm correctness before delivering to the user.

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
├── README.md
├── AGENTS.md
└── .gitignore
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LITEROUTER_PORT` | `7766` | Port of the LiteRouter gateway |
| `LITEROUTER_AUTH_KEY` | `sk-lr-8f2a9e3b1c4d7e5f` | Bearer token for LiteRouter auth |
