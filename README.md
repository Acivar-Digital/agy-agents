# antigravity-agents (agy-agents)

Standalone agentic workflows and tools that run against the [LiteRouter](https://github.com/Acivar-Digital/literouter) API Gateway using Google's Antigravity sandbox (`antigravity-preview-05-2026`).

## Available Agents

| Agent | Description |
|---|---|
| **Deep Research (Institutional Protocol)** | Multi-persona research council that produces heavily cited, institutional-grade whitepapers from live web data. |

## Quick Start

### Prerequisites

- LiteRouter gateway running locally (default port `7766`)
- Antigravity sandbox access (`antigravity-preview-05-2026`)
- Python 3.10+ with [uv](https://docs.astral.sh/uv/)

### Setup

```bash
# 1. Configure the environment
cp deep-research/.env.example deep-research/.env
# Edit deep-research/.env with your LITEROUTER_PORT and LITEROUTER_AUTH_KEY

# 2. Ensure LiteRouter is running
bash scripts/start.sh
```

### Create a Prompt

Copy the template and customize it:

```bash
cp deep-research/prompts/_template_guide.md deep-research/prompts/My_Topic.md
# Edit My_Topic.md — set the objective and customize the 5 personas
```

### Run

```bash
uv run python deep-research/deep-research.py My_Topic
```

Reports are saved to `deep-research/reports/`.

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
│   └── reports/                 ← Generated (gitignored)
│       └── *.md + *_raw.json
├── README.md
├── AGENTS.md
└── .gitignore
```

## Skills

This project includes an opencode skill at `.opencode/skills/agy-agents/SKILL.md` that teaches agents how to use every workflow. Load it with the `agy-agents` skill name.

## License

MIT
