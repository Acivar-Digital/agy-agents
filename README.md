# antigravity-agents (agy-agents)

Standalone agentic workflows and tools that run against the [LiteRouter API Gateway](http://localhost:7766/v1beta/interactions) (`/v1beta/interactions` endpoint) using Google's Antigravity sandbox (`antigravity-preview-05-2026`).

> **⚠️ Uses `/v1beta/interactions` (interaction format), NOT `/v1/chat/completions` (OpenAI format).**
> Payload: `{"agent": "antigravity-preview-05-2026", "input": "...", "environment": "remote"}`

## Available Agents

| Agent | Description |
|---|---|
| **Deep Research (Institutional Protocol)** | Multi-persona research council that produces heavily cited, institutional-grade whitepapers from live web data. |
| **Refactor** | Autonomous multi-agent refactoring pipeline that reads Python files, sends them to the Antigravity agent for clean refactoring, and writes the results back to disk. |

## Quick Start

### Prerequisites

- LiteRouter gateway running locally (default port `7766`)
- Antigravity sandbox access (`antigravity-preview-05-2026`)
- Python 3.10+ with [uv](https://docs.astral.sh/uv/)

### Deep Research

```bash
# 1. Configure the environment
cp deep-research/.env.example deep-research/.env

# 2. Create a prompt
cp deep-research/prompts/_template_guide.md deep-research/prompts/My_Topic.md
# Edit My_Topic.md

# 3. Run
uv run python deep-research/deep-research.py My_Topic
```

### Refactor

```bash
# 1. Configure the environment
cp refactor/.env.example refactor/.env

# 2. Refactor a single file
uv run python refactor/refactor.py path/to/script.py

# 3. Refactor an entire directory
uv run python refactor/refactor.py path/to/src/
```

## Project Structure

```
agy-agents/
├── .opencode/
│   └── skills/
│       └── agy-agents/
│           └── SKILL.md        ← Agent skill definitions
├── deep-research/
│   ├── deep-research.py         ← Core execution script
│   ├── run.sh                   ← Batch runner (cron-friendly)
│   ├── .env.example             ← Environment template
│   ├── prompts/
│   │   ├── _template_guide.md   ← Prompt structural template
│   │   └── *.md                 ← Prompt files (one per topic)
│   └── reports/                   ← Generated (gitignored)
│       └── *.md + *_raw.json
├── refactor/
│   ├── prompt.txt           ← Default system prompt (editable)
│   ├── refactor.py          ← Reusable auto-refactor script
│   ├── .env.example         ← Environment template
│   ├── INSTRUCTIONS.md      ← Multi-agent refactoring guide
│   └── reports/               ← Generated (gitignored)
│       └── batch_report_*.md
├── README.md
├── AGENTS.md
└── .gitignore
```

## Skills

This project includes an opencode skill at `.opencode/skills/agy-agents/SKILL.md` that teaches agents how to use every workflow. Load it with the `agy-agents` skill name.

## License

MIT
