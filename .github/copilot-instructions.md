# GitHub Copilot Instructions for agy-agents

`agy-agents` is an open-source autonomous agent framework connecting to the Google Antigravity sandbox (`antigravity-preview-09-2026`) via `/v1beta/interactions`.

## Core Guidelines & Invariants

1. **API Endpoint Contract**:
   - Always use the `/v1beta/interactions` endpoint with payload `{"agent": "antigravity-preview-09-2026", "input": "...", "environment": "remote"}`.
   - Do NOT use OpenAI-compatible `/v1/chat/completions` or Gemini `:generateContent`.

2. **Inference Providers**:
   - Dual-engine auto-resolution: Direct Google Gemini (`GEMINI_API_KEY`) or Self-Hosted LiteRouter gateway (`LITEROUTER_AUTH_KEY` at `http://literouter.lan:7766` or `127.0.0.1:7766`).
   - Resolved via `get_provider_config("auto")`, configurable with `PROVIDER=literouter` or `PROVIDER=gemini`.

3. **Data Modeling Standards**:
   - Use Pydantic V2 (`pydantic>=2.10.0`) for all request/response models.
   - Always enforce `ConfigDict(extra="forbid", validate_assignment=True)`.
   - Maintain Python 3.10+ compatibility (`from typing import Literal, Any`, `X | None`, `list[str]`).

4. **MCP Server Architecture**:
   - Built with FastMCP (`mcp_server.py`, script `agy-mcp`).
   - Deep research takes 3-8 minutes; long-running operations must run asynchronously using background workers (`start_research` -> `job_id` -> `get_research_status`) to prevent client RPC 60s timeout disconnects.

5. **Testing & Verification**:
   - Before completing tasks, always run `uv run python -m unittest tests/test_mcp_server.py`.
