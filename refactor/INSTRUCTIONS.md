# Manifest-Driven Refactoring Instructions

This document explains how AI agents refactor Python code using manifest JSON config files and the LiteRouter API Gateway.

## Core Concept

You create a **JSON manifest file** that describes one refactoring task. The script reads the manifest, reads the target and reference files from disk, builds a single text prompt, sends it to the Antigravity agent, and writes the result back to disk.

**You never call the API directly.** The script handles all API communication, file I/O, and error handling.

## Endpoint Contract (Critical)

| Field | Value |
|---|---|
| **URL** | `http://localhost:7766/v1beta/interactions` |
| **Method** | `POST` |
| **Agent** | `antigravity-preview-05-2026` |
| **Environment** | `remote` |

> **⚠️ This uses `/v1beta/interactions` — NOT `/v1/chat/completions`.** The payload format is `{agent, input, environment}` where `input` is a single string. The response is an interaction object with `steps`, not a `choices` array.

## Manifest Format

Each manifest is a JSON file stored in `refactor/manifests/`. Here is the template:

```json
{
  "targets": ["path/to/file.py"],
  "reference_files": ["path/to/lib.py"],
  "prompt": "Your full prompt text here...",
  "output_dir": "refactor/output",
  "output_naming": "{stem}_refactored"
}
```

### Field Reference

| Field | Type | Required | Description |
|---|---|---|---|
| `targets` | `string[]` | Yes | List of `.py` files to refactor |
| `reference_files` | `string[]` | No | Extra files injected as read-only context |
| `prompt` | `string` | Yes | The full prompt text the agent follows |
| `output_dir` | `string` | No | Directory for `_refactored.py` files (default: `refactor/output`) |
| `output_naming` | `string` | No | Output filename pattern; `{stem}` is replaced with the source filename stem (default: `{stem}_refactored`) |

### Multiple Targets

You can refactor multiple files with the same prompt in one manifest:
```json
{
  "targets": ["src/engine/a.py", "src/engine/b.py"],
  "prompt": "...",
  "output_dir": "refactor/output"
}
```

### Reference Files

Reference files are read by the script and injected into the prompt with clear boundaries (`--- START OF REFERENCE FILE ---` / `--- END OF REFERENCE FILE ---`). The agent sees them as read-only context — it should never modify them.

If a reference file doesn't exist on disk, the script prints a warning but continues.

## How the Script Processes a Manifest

1. **Read manifest** — loads the JSON config
2. **Read target files** — reads each `.py` file into a string
3. **Read reference files** — reads each reference file into a string
4. **Build prompt** — concatenates `prompt + reference files + target file` with clear markers
5. **Send to API** — POSTs to `/v1beta/interactions` with `{agent, input, environment}`
6. **Extract output** — parses the interaction response using `extract_output_text()`
7. **Write result** — saves the refactored code to `output_dir/{stem}_refactored.py` (or custom name)
8. **Generate report** — appends result to `refactor/reports/batch_report_*.md`

## How to Use It

### Step 1: Create a Manifest

Copy the template and fill it in:
```bash
cp refactor/manifests/template.json refactor/manifests/my_task.json
```

Edit `my_task.json`:
- Set `targets` to the files you want to refactor
- Write your `prompt` with the specific instructions
- Add `reference_files` if the code depends on external modules
- Set `output_dir` and `output_naming` as needed

### Step 2: Run the Script

Process a single manifest:
```bash
uv run python refactor/refactor.py --manifest refactor/manifests/my_task.json
```

Process all manifests in the folder (auto-discovered):
```bash
uv run python refactor/refactor.py --manifest-dir refactor/manifests/
```

### Step 3: Review the Results

After the script finishes:
1. **Check the output** — refactored files are in `refactor/output/` (or your custom `output_dir`)
2. **Show the diff** — run `git diff` to see all changes
3. **Verify with tests** — run `uv run ruff check --select C901` and `uv run pytest`
4. **Review the report** — `refactor/reports/batch_report_*.md` summarizes all results

## Writing Effective Prompts

Your `prompt` field should contain the full system instructions for the agent. Follow these rules:

1. **Start with a role** — e.g., "You are a Senior Python Engineer"
2. **State the task clearly** — what to change and what constraints to follow
3. **Preserve the API** — if you don't want signature changes, say so explicitly
4. **Specify the output format** — always include "Output ONLY raw Python code. No markdown fences."
5. **Include reference file awareness** — mention which reference files exist so the agent doesn't try to modify them
6. **No placeholders** — the agent must output the entire file, not fragments or `# ... rest of code ...`

## Safety Rules for Agents

When creating or running a manifest:

1. **You are an agent, not a file operator** — you create the manifest JSON and run the script. The script reads files, calls the API, and writes output. You never touch `.py` files directly in this workflow.
2. **Verify the manifest is valid JSON** — before running, run `python3 -c "import json; json.load(open('my_manifest.json'))"` to check for syntax errors
3. **Check output after completion** — always review `git diff` before committing
4. **Run tests** — if `pytest` is present, run the relevant tests and fix any failures before finalizing

## Post-Run Steps

After the script finishes, you must do these yourself:

1. **Read the batch report** — check `refactor/reports/batch_report_*.md` for success/failure counts
2. **Review the diff** — run `git diff` to see exactly what changed
3. **Verify refactored files** — check that `_refactored.py` files are valid Python
4. **Run verification commands** — `uv run ruff check --select C901` and `uv run pytest`
5. **Commit if satisfied** — only commit after reviewing `git diff`

## Project Structure

```
refactor/
├── INSTRUCTIONS.md         ← This file
├── refactor.py             ← Core script (manifest-driven)
├── prompt.txt              ← Default system prompt (legacy, not used in manifest mode)
├── run.sh                  ← Convenience runner (--manifest-dir)
├── manifests/
│   ├── template.json       ← Copy this to start a new task
│   └── *.json              ← Your manifest files (auto-discovered)
├── output/                 ← Generated refactored files (from manifest runs)
└── reports/                ← Batch reports (gitignored)
```