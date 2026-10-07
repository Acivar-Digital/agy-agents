# CLAUDE.md — Claude Code CLI Assistant Guide

`agy-agents` is an open-source framework of autonomous AI agent workflows running against Google Antigravity (`antigravity-preview-09-2026`) via the stateful `/v1beta/interactions` API.

---

## 🛠️ Essential Development & Verification Commands

```bash
# Install dependencies & sync venv
uv sync

# Run MCP server locally (stdio transport)
uv run agy-mcp

# Run MCP server as persistent intranet SSE endpoint (http://agy-agents.lan:7788/sse)
uv run agy-mcp --transport sse --host 0.0.0.0 --port 7788
# Run unit and integration tests (deterministic quality gate)
uv run python -m unittest tests/test_mcp_server.py

# Check inference gateway health (LiteRouter or Gemini)
uv run python -c "import mcp_server; print(mcp_server.check_gateway_health())"

# Discover ready research prompts
uv run python -c "import mcp_server; print(mcp_server.list_research_prompts())"

# Execute Deep Research (foreground CLI)
uv run agy-research Direction_of_JPY

# Execute Autonomous Code Refactoring (CLI)
uv run agy-refactor path/to/script.py --inplace
```

---

## 🧱 Architectural Invariants & Rules

1. **Stateful Interactions Endpoint (CRITICAL)**:
   - **Endpoint:** `POST /v1beta/interactions`.
   - **Payload:** `{"agent": "antigravity-preview-09-2026", "input": "...", "environment": "remote"}`.
   - **Prohibition:** NEVER call `/v1/chat/completions` (OpenAI format) or `:generateContent`. Antigravity only supports the Interactions API.
2. **Dual-Engine Auto-Resolution**:
   - `PROVIDER=literouter` or `LITEROUTER_AUTH_KEY` → LiteRouter gateway (`http://literouter.lan:7766` or `http://127.0.0.1:7766`).
   - `PROVIDER=gemini` or `GEMINI_API_KEY` → Google Gemini API (`https://generativelanguage.googleapis.com/v1beta/interactions`).
   - Priority selection can be explicitly forced with the `PROVIDER` environment variable (`literouter` or `gemini`).
3. **Pydantic V2 Strict Contracts**:
   - Every request, response, and manifest schema must use Pydantic V2 (`pydantic>=2.10.0`).
   - Models must declare `model_config = ConfigDict(extra="forbid", validate_assignment=True)`.
   - Python 3.10+ compatibility: use `list[T]`, `dict[K, V]`, and `T | None`. Avoid Python 3.12 PEP 695 `type X = ...` syntax.
4. **FastMCP Server Hybrid Protocol**:
   - Fast tools (`prepare_research_prompt`, `refactor_code`, `list_research_prompts`, `check_gateway_health`) execute synchronously.
   - Long-running research (`start_research`) MUST execute asynchronously via background threads to eliminate the client-side 60s RPC timeout, returning a `job_id` polled via `get_research_status`.
   - Tools decorated with `@mcp.tool` must unwrap `FieldInfo` defaults via `_unwrap_field()` to support both RPC calls and direct Python invocation.
5. **Git & Security Invariants**:
   - Never commit API keys or auth tokens.
   - Runtime cache directories (`.jobs/`, `.omp/`, `reports/`) are strictly gitignored.
   - Local-only by default: do not run `git commit` or `git push` without explicit user instruction.
