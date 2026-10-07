# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
