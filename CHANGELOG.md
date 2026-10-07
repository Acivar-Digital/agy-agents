# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-10-08

### Added
- **Simplified MCP Instruction & CLI-Trigger Wrapper**: Streamlined `prepare_research_prompt` and `start_research` in `mcp_server.py` to act as pure instruction wrappers that (1) explain how the 5-persona research workflow operates and (2) instruct the LLM to trigger `uv run python deep-research/deep-research.py <stem>` directly so the script exits with exit code `0` (waking the LLM up automatically) and prints the exact `.md` report path to collect.
- **Markdown-Only (`.md`) Output & Fast Execution**: Removed slow sandbox `pip install` and HTML/PDF/DOCX compilation from `deep-research.py`, cutting research execution time below 210s and eliminating 360s gateway timeouts.
- **Preserved `InteractionStep.content` Extraction**: Added explicit `type` and `content` fields to `InteractionStep` so multi-part `model_output` steps are preserved and extracted directly into `deep-research/reports/<stem>_<timestamp>.md`.
- **Dual-Transport MCP Network Endpoint**: Implemented dual-transport routing in `mcp_server.py` supporting Streamable HTTP (`POST /sse` and `POST /mcp`) for `omp` (`type: remote`) alongside Server-Sent Events (`GET /sse`) and HEAD health probes.
- **In-Band Markdown Report & LAN HTTP Serving**: `get_research_status` returns the full `.md` report in-band and `GET /reports/{filename}` serves `.md` reports over HTTP on `:7788`.
- **Skill Documentation v1.3.0**: Updated `.opencode/skills/agy-agents/SKILL.md` with exact `mcp_server.py` parameter signatures and the simplified CLI-trigger `.md`-only workflow.

## [1.2.0] - 2026-10-07

### Added
- **FastMCP Server (`agy-mcp`)**: Native Model Context Protocol server exposing sovereign tools for deep research and autonomous code refactoring.
- **Hybrid Async Execution Architecture**: Implemented asynchronous background job management (`start_research`, `get_research_status`) to completely eliminate client-side 60s RPC timeout disconnects during extensive multi-persona research runs.
- **Domain-Tailored Prompt Sculptor**: Added `prepare_research_prompt` to generate institutional Citi-grade 5-persona prompts with ready-to-run background CLI commands.
- **Synchronous Autonomous Refactoring Tool**: Added `refactor_code` MCP tool with AST syntax verification, PEP 8 enforcement, and unified diff output.
- **Diagnostic & Discovery Tools**: Added `check_gateway_health` for LiteRouter / Gemini latency inspection and `list_research_prompts` for discovering existing structured prompt templates.
- **Remote VPS Deployment**: Deployed and verified to `vps466a:/home/vps466a/services/agy-agents` routed against LiteRouter at `literouter.lan:7766`.
- **Client Configuration Guides**: Added ready-to-use configuration blocks in `README.md` for OpenCode, Claude Desktop, and Cursor.

## [1.1.0] - 2026-10-07

### Added
- **Pydantic V2 Core Modernization**: Migrated the entire codebase to strict Pydantic V2 data contracts (`pydantic>=2.10.0`).
- **Validated Interaction Contracts**: Added `InteractionRequest`, `InteractionStep`, and `InteractionResponse` to strictly validate LiteRouter and Google Gemini `/v1beta/interactions` payloads and responses.
- **Strict Manifest & Execution Models**: Added `RefactorManifest`, `RefactorExecutionRequest`, `RefactorExecutionResult`, and `BatchReportItem` with robust field-level validation and error reporting.
- **Immutable Provider Configurations**: Added frozen `ProviderConfig` models across both `deep-research` and `refactor` modules ensuring validated gateway URLs, template placeholders, and authorization headers.
- **Backward-Compatible Interfaces**: Added dict-style subscription (`result["field"]`), `.get()`, and tuple-unpacking (`name, url, headers = config`) to preserve seamless backward compatibility with existing scripts.
- **Top-Level Modular Shim Re-exports**: Re-exported all Pydantic V2 models through root `deep_research.py` and `refactor/__init__.py`.

### Changed
- Standardized typing across all functions to modern Python 3.10+ union syntax (`X | None`, `list[Path] | None`) and parameterized collections.
- Widened `InteractionResponse` response fields to support both raw string outputs and dictionary message envelopes from the LiteRouter gateway.
- Enforced `ConfigDict(extra="forbid", validate_assignment=True)` on all internal input and result contracts.

---

## [1.0.0] - 2026-10-07

### Added
- **Initial Stable Release**: First public release of `agy-agents` framework.
- **Deep Research (Council Protocol)**: Multi-perspective 5-persona research panel generating whitepapers with automated web search and evidence synthesis.
- **Autonomous Refactoring Pipeline**: Single-file CLI and batch manifest-based Python code modernization engine.
- **Dual-Engine Auto-Resolution**: Support for direct Google Gemini API (`GEMINI_API_KEY`) and self-hosted LiteRouter gateway (`LITEROUTER_AUTH_KEY`).
- **Multi-Format Extraction**: Automatic compilation and extraction of `.md`, `.html`, `.pdf`, and `.docx` report artifacts from Antigravity sandboxes.
- **Modular APIs**: Core programmatic entry points `execute_research()` and `execute_refactor()` for Model Context Protocol (MCP) integrations.
