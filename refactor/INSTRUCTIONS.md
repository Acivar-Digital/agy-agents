# Autonomous Refactoring Pipeline Instructions

This document explains how AI agents and developers use the refactoring pipeline with either direct file arguments or manifest JSON configuration files, supporting both Google Gemini API directly and the LiteRouter API Gateway.

## Execution Modes

The refactor pipeline supports two primary execution workflows:

### 1. Direct File CLI Mode (Fast & Surgical)
Refactor a specific Python file directly from the terminal without creating a manifest:
```bash
# Saves output to path/to/script_refactored.py
uv run python refactor/refactor.py path/to/script.py

# With a custom inline prompt
uv run python refactor/refactor.py path/to/script.py --prompt "Enforce PEP 8, add type hints, and extract helper functions"

# Overwrite in-place
uv run python refactor/refactor.py path/to/script.py --inplace
```

### 2. Manifest Batch Mode (Structured & Multi-File)
For complex jobs or multiple files sharing reference context, define JSON manifest files in `refactor/manifests/`:
```bash
# Run all manifests in refactor/manifests/*.json
uv run python refactor/refactor.py

# Or run a specific manifest file
uv run python refactor/refactor.py --manifest refactor/manifests/my_task.json
```

---

## Dual-Engine Support

The script automatically detects your active configuration from environment variables or `.env`:

| Mode | Trigger Variable | Target Gateway URL |
|---|---|---|
| **Public Community (Default)** | `GEMINI_API_KEY` | `https://generativelanguage.googleapis.com/v1beta/interactions` |
| **Self-Hosted (LiteRouter)** | `LITEROUTER_AUTH_KEY` | `http://{LITEROUTER_HOST}:{LITEROUTER_PORT}/v1beta/interactions` |

You can also force the provider via CLI:
```bash
uv run python refactor/refactor.py path/to/script.py --provider gemini
# or
uv run python refactor/refactor.py path/to/script.py --provider literouter
```

---

## Endpoint Contract (Critical)

| Field | Value |
|---|---|
| **Payload Agent** | `antigravity-preview-09-2026` |
| **Payload Environment** | `remote` |
| **Format** | `/v1beta/interactions` (Interaction format, NOT OpenAI `/v1/chat/completions`) |

The payload format is `{"agent": "antigravity-preview-09-2026", "input": "...", "environment": "remote"}`.

---

## Manifest File Structure

Manifests live in `refactor/manifests/*.json`:

```json
{
  "targets": ["src/engine/resolver.py"],
  "reference_files": ["src/engine/models.py"],
  "prompt": "You are a Senior Python Engineer...\n\n## TASK\nRefactor to clean architecture, enforce type safety, and decouple dependencies.\n\n## OUTPUT FORMAT\nOutput ONLY raw Python code.",
  "output_dir": "refactor/output",
  "output_naming": "{stem}_refactored"
}
```

### Field Reference

| Field | Type | Required | Description |
|---|---|---|---|
| `project_folder` | `string` | No | Root directory of the project to refactor (defaults to repo root) |
| `targets` | `string[]` | Yes | List of `.py` files to refactor |
| `reference_files` | `string[]` | No | Extra files injected as read-only context into the prompt |
| `prompt` | `string` | Yes | System prompt instructions for the agent |
| `output_dir` | `string` | No | Directory for output files (default: `refactor/output`) |
| `output_naming` | `string` | No | Filename pattern; `{stem}` is replaced with source file stem |

---

## 💡 Customizing with Your LLM

You can ask your favorite LLM (Claude, ChatGPT, Gemini, etc.) to generate manifests and tailor prompts for your specific project:

> *"Read `refactor/manifests/template.json` and my codebase in `src/`. Generate a manifest targeting all API route handlers to refactor them to use dependency injection and Pydantic v2 schemas."*

---

## Post-Run Steps

After refactoring:
1. **Review the diff**: `git diff path/to/file.py path/to/file_refactored.py`
2. **Verify syntax**: `python -m py_compile path/to/file_refactored.py`
3. **Run your test suite**: `pytest` or `unittest`
