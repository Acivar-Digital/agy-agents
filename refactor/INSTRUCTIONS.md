# Multi-Agent Refactoring Instructions

This document explains how to use AI agents to autonomously refactor codebases using the LiteRouter API Gateway and Antigravity sandbox.

## Workflow Overview

The refactoring pipeline follows a four-stage approach:

1. **Ingest** — Read target files or directories
2. **Analyze** — Agent identifies code smells and refactoring opportunities
3. **Refactor** — Agent produces clean, refactored code
4. **Verify** — Diff the changes, run tests, and confirm correctness

## Best Practices (Grounded in Recent Workflows)

### 1. Start Small — File-by-File
Do not send a large codebase in a single prompt. Read individual files, refactor them, and write them back. This keeps the context window tight and reduces hallucinations.

### 2. Force Strict Raw Code Output
By default, AI models wrap code in Markdown blocks or add conversational text. Your prompt must explicitly instruct the agent to output **only raw code** so it can be written directly to a file.

### 3. Keep Context Tightly Scoped
If the file depends on external modules or shared utilities, include a brief summary of those dependencies in the prompt so the agent doesn't hallucinate missing functions.

### 4. Use Git as a Safety Net
Always run the refactoring script on files that are committed to Git. After the agent finishes, use `git diff` to review changes before committing them.

### 5. Low Temperature for Code
Set `temperature` to `0.2` or lower for coding tasks. This reduces random variation and keeps refactoring suggestions accurate.

## How to Use the Template

### Prerequisites

1. LiteRouter gateway running on port 7766
2. Antigravity sandbox access (`antigravity-preview-05-2026`)
3. Python 3.10+ with `uv`
4. Environment configured: `cp refactor/.env.example refactor/.env`

### Running a Single File

```bash
uv run python refactor/refactor.py path/to/messy_script.py
```

This will:
- Read the file
- Send it to the agent with refactoring instructions
- Save the refactored version as `path/to/messy_script_refactored.py`
- Print a summary of changes

### Running a Directory (Batch)

```bash
uv run python refactor/refactor.py path/to/src/
```

This will:
- Traverse all `.py` files in the directory recursively
- Refactor each file individually
- Save refactored versions alongside originals
- Generate a `refactor/reports/batch_report.md` summarizing all changes

### Offline Transform Mode

If you have previously saved raw API responses and want to re-render them without hitting the API:

```bash
uv run python refactor/refactor.py --transform refactor/reports/some_run_raw.json
```

## Safety Rules for Agents

When a user asks to "refactor code" or "improve code quality":

1. **Always read the file first** — do not send a file you haven't read.
2. **Output only raw code** — remove Markdown fences and conversational text.
3. **Verify the output is valid Python** — check for syntax errors before writing.
4. **Never delete required logic** — only restructure, rename, and add type hints.
5. **Show the diff** — run `git diff` after writing and present it to the user.
6. **Run tests if available** — if `pytest` or `unittest` is present, run the relevant tests and fix any failures before finalizing.

## Project Structure

```
refactor/
├── INSTRUCTIONS.md    ← This file
├── .env.example       ← Environment template
├── refactor.py        ← Reusable refactoring script
└── reports/           ← Generated reports (gitignored)
    ├── batch_report.md
    └── *_raw.json
```
