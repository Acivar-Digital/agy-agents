# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-10-08

### Added
- **Dual-Transport MCP Network Endpoint**: Implemented dual-transport routing in `mcp_server.py` supporting Streamable HTTP (`POST /sse` and `POST /mcp`) for `omp` (`type: remote`) alongside Server-Sent Events (`GET /sse`) and HEAD health probes.
- **In-Band Markdown Report Delivery**: Enhanced `get_research_status` to embed the complete Markdown report (`report.md`) directly in the tool response (`#### Full Markdown Report`), enabling client LLMs to ingest deep research reports instantly without filesystem dependencies.
- **LAN HTTP Artifact Serving**: Added `GET /reports/{filename}` route to `agy-mcp` on port `:7788`, allowing LAN agents and browsers to directly fetch `.md`, `.html`, `.pdf`, and `.docx` artifacts via `http://agy-agents.lan:7788/reports/...`.
- **Stem-Based Job Lookup Fallback**: `get_research_status` now accepts topic stems (e.g. `Direction_of_JPY`) to automatically resolve and deliver the most recent completed run for that topic.
- **Interaction Step Extraction Fallback**: `deep-research.py` now extracts Markdown text directly from `InteractionStep` content blocks in raw interactions if the remote Antigravity sandbox does not produce a separate `report.md` artifact file.
- **Comprehensive FastMCP Test Suite**: Added Starlette `TestClient` tests covering Streamable HTTP, SSE, HEAD probes, static `/reports/{filename}` serving, and in-band Markdown extraction in `tests/test_mcp_server.py`.
- **Skill Documentation v1.3.0**: Completely updated `.opencode/skills/agy-agents/SKILL.md` covering the 6 sovereign MCP tools, dual-transport endpoints, artifact consumption channels, and `omp` / `OpenCode` configuration patterns.

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
