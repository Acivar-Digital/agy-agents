# Multi-Agent Refactoring Instructions

## Endpoint Contract (Critical — Read First)

| Field | Value |
|---|---|
| **URL** | `http://localhost:7766/v1beta/interactions` |
| **Method** | `POST` |
| **Agent** | `antigravity-preview-05-2026` |
| **Environment** | `remote` |

**Payload format:**
```json
{
  "agent": "antigravity-preview-05-2026",
  "input": "<prompt + filename + code>",
  "environment": "remote"
}
```

**Response format:** An interaction object with `object: "interaction"`, `status: "completed"`, and a `steps` array containing `thought` and `model_output` entries. Extract the refactored code from `steps[].content` entries where `type == "model_output"`.

> **⚠️ This uses `/v1beta/interactions` — NOT `/v1/chat/completions`.** The interaction endpoint has a completely different request/response format than OpenAI chat completions. The payload uses `{agent, input, environment}` (not `messages`/`model`), and the response uses `steps` (not `choices`). Do not attempt to use the OpenAI chat completions format with this API.

This document explains how AI agents autonomously refactor code using the LiteRouter API Gateway and Antigravity sandbox.

## How It Works

The **script** (`refactor.py`) does all filesystem work. It reads `.py` files, sends code to the LiteRouter API, and writes refactored output. The **agent** (Antigravity) only returns text — never touches disk.

### Pipeline

1. **Ingest** — Script reads your `.py` file from disk
2. **Send** — Script POSTs to `/v1beta/interactions` with the interaction payload (see Endpoint Contract above)
3. **Agent** — Antigravity refactors the code and returns it as text via `steps[].model_output`
4. **Extract** — Script pulls the refactored code from the response
5. **Write** — Script writes the result to `original_name_refactored.py`
6. **Report** — Script generates a `refactor/reports/batch_report_*.md`

The agent never places files, never reads files, never knows the file path. It only receives code as text and returns refactored code as text.

## Step 0: Customize the Prompt

Before running the refactor, edit the prompt file that tells the agent how to refactor:

```
refactor/prompt.txt
```

This file contains the **system prompt** — the instructions the agent follows when refactoring. The default prompt:
- Modernizes code with Python features (f-strings, pathlib, dataclasses)
- Adds comprehensive type hints and Google-style docstrings
- Improves error handling and efficiency
- Preserves all business logic, API signatures, and imports

To use a custom prompt for a different task, create your own file and pass it with `--prompt`:

```bash
uv run python refactor/refactor.py path/to/script.py --prompt path/to/my_prompt.txt
```

## Workflow Stages

1. **Ingest** — Script reads target files or directories
2. **Analyze** — Agent identifies code smells and refactoring opportunities
3. **Refactor** — Agent returns clean, refactored Python code as text
4. **Write** — Script writes the returned text to a new file
5. **Verify** — Diff the changes with `git diff`, run tests, confirm correctness

## Best Practices (Grounded in Recent Workflows)

### 1. Start Small — File-by-File
Do not send a large codebase in a single prompt. Read individual files, refactor them, and write them back. This keeps the context window tight and reduces hallucinations.

### 2. Force Strict Raw Code Output
By default, AI models wrap code in Markdown blocks or add conversational text. Your prompt must explicitly instruct the agent to output **only raw code** so the script can write it directly to a file. The system prompt in `refactor.py` enforces this, and a safety net strips any stray ` ```python ` fences from the response (lines 71–74).

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
- Read the system prompt from `refactor/prompt.txt` (or use `--prompt` for a custom one)
- Include the filename in the user prompt (e.g., `auth.py`) so the agent understands context
- Read `messy_script.py` from disk
- Send it to the agent via the LiteRouter API
- Receive back refactored Python code as text
- Save the result as `messy_script_refactored.py` in the same directory
- Print a summary

To use a custom prompt file instead of the default `prompt.txt`:

```bash
uv run python refactor/refactor.py path/to/script.py --prompt path/to/custom_prompt.txt
```

### Running a Directory (Batch)

```bash
uv run python refactor/refactor.py path/to/src/
```

This will:
- Traverse all `.py` files in the directory recursively
- Refactor each file individually via the API
- Save refactored versions alongside originals (`_refactored.py`)
- Generate a `refactor/reports/batch_report_*.md` summarizing all changes

### Offline Transform Mode

If you have previously saved raw API responses and want to extract the code without hitting the API again:

```bash
uv run python refactor/refactor.py --transform refactor/reports/some_run_raw.json
```

This prints the extracted code to stdout (no file is written — useful for piping or inspection).

## Safety Rules for Agents

When a user asks to "refactor code" or "improve code quality":

1. **You are an agent, not a file operator** — you only return text. The Python script handles all filesystem operations (reading input files, writing output files). Do not attempt to open, read, or write files directly.
2. **Output only raw code** — do not wrap code in markdown blocks (no ` ```python `). Do not include any conversational text, explanations, or pleasantries. The output must be immediately executable Python.
3. **Verify your output is valid Python** — check for syntax errors and missing imports before returning code.
4. **Never delete required logic** — only restructure, rename, and add type hints.
5. **The human reviews the diff** — after the script writes `_refactored.py` files, the user runs `git diff` to see all changes before committing.
6. **Run tests if available** — if `pytest` or `unittest` is present, run the relevant tests on the refactored files and fix any failures before finalizing.

## Project Structure

```
refactor/
├── INSTRUCTIONS.md    ← This file
├── .env.example       ← Environment template
├── prompt.txt         ← Default system prompt for the agent (editable)
├── refactor.py        ← Reusable refactoring script (handles all I/O)
└── reports/           ← Generated (gitignored)
    └── batch_report_*.md
```
