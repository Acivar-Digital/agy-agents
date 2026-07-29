# agy-agents — Agent Instructions

This repository contains standalone agentic workflows and tools designed to run against the LiteRouter API Gateway using Google's Antigravity sandbox (`antigravity-preview-05-2026`).

## Available Agents

### Deep Research (Institutional Protocol)

A multi-persona research council workflow that leverages Antigravity's web-search and sandbox execution capabilities to produce heavily cited, institutional-grade whitepapers.

**Input:** A prompt file in `deep-research/prompts/` defining the topic and 5 research personas.
**Output:** A structured Markdown whitepaper saved in `deep-research/reports/`.

## How to Use

1. Ensure the LiteRouter gateway is running on port 7766.
2. Create or edit a prompt file in `deep-research/prompts/` using `_template_guide.md` as the structural template.
3. Run: `uv run python deep-research/deep-research.py PromptName`
4. Verify the report was generated in `deep-research/reports/`.

## Key Files

- `deep-research/deep-research.py` — Core execution script
- `deep-research/run.sh` — Batch runner for multiple prompts
- `deep-research/prompts/_template_guide.md` — Template for creating new prompts
- `deep-research/.env.example` — Environment variable template

## Agent Workflow Rules

- When the user asks to "research a topic" or "conduct deep research," always use the Deep Research agent.
- Do not run the research script in the background — wait for it to complete and verify the output.
- Always customize all 5 personas to match the user's specific domain.
