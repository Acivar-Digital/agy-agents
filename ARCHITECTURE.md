# Architectural Blueprint: `agy-agents`

`agy-agents` is an open-source framework designed for autonomous research generation and automated codebase modernization. It connects to the stateful Google Antigravity environment (`antigravity-preview-09-2026`) via the `/v1beta/interactions` endpoint.

---

## 1. System Topology & Component Overview

```mermaid
graph TB
    subgraph Clients["Clients & AI Assistants"]
        OC["OpenCode / Terminal"]
        CD["Claude Desktop"]
        CR["Cursor IDE"]
        CLI["CLI Users (Terminal)"]
    end

    subgraph InterfaceLayer["Interface & Execution Layer"]
        MCP["FastMCP Server (mcp_server.py)<br/>agy-mcp"]
        JOB[".jobs/ Registry<br/>(Async Worker Threads)"]
        CLIRunners["CLI Runners<br/>agy-research & agy-refactor"]
        PythonAPI["Programmatic Python APIs<br/>execute_research() & execute_refactor()"]
    end

    subgraph InferenceRouting["Dual-Engine Inference Routing"]
        PC["Provider Resolver<br/>(get_provider_config)"]
        LR["LiteRouter Gateway<br/>http://literouter.lan:7766<br/>(LITEROUTER_AUTH_KEY)"]
        GG["Google Gemini API<br/>https://generativelanguage.googleapis.com<br/>(GEMINI_API_KEY)"]
    end

    subgraph RemoteExecution["Google Antigravity Sandbox"]
        AG["antigravity-preview-09-2026<br/>POST /v1beta/interactions"]
        SB["Remote Sandbox<br/>(Web Search, Compilers, Tools)"]
        TAR["Snapshot Tarball (.tar)<br/>environment-{env_id}"]
    end

    subgraph LocalArtifacts["Generated Artifacts"]
        REP["deep-research/reports/<br/>report.md | .html | .pdf | .docx"]
        REF["refactor/output/<br/>Clean Python Code + Diffs"]
    end

    OC -->|SSE Network / SSH Stdio| MCP
    CD -->|SSE Network / SSH Stdio| MCP
    CR -->|SSE Network / SSH Stdio| MCP
    CLI --> CLIRunners

    MCP -->|Async Jobs| JOB
    JOB --> PythonAPI
    MCP -->|Sync Tools| PythonAPI
    CLIRunners --> PythonAPI

    PythonAPI --> PC
    PC -->|PROVIDER=literouter| LR
    PC -->|PROVIDER=gemini| GG

    LR -->|POST /v1beta/interactions| AG
    GG -->|POST /v1beta/interactions| AG

    AG --> SB
    SB --> TAR
    TAR -->|Download & Extract| REP
    AG -->|Model Output| REF
```

---

## 2. Hybrid Async MCP Execution Sequence

Standard MCP clients enforce a **hard 60-second RPC timeout**. Deep research runs take 3–8 minutes because the 5-persona council executes 50 live Google searches and compiles documents in the remote sandbox. The diagram below shows how the hybrid non-blocking job protocol operates:

```mermaid
sequenceDiagram
    autonumber
    actor Client as MCP Client (Claude / Cursor / OpenCode)
    participant MCP as FastMCP (mcp_server.py)
    participant Worker as Background Worker Thread
    participant Registry as .jobs/<job_id>.json
    participant Engine as deep_research.py (execute_research)
    participant Gateway as Inference Gateway (LiteRouter / Gemini)

    Client->>MCP: prepare_research_prompt(topic, stem)
    MCP-->>Client: Returns prompt preview + CLI command (<1s)

    Client->>MCP: start_research(topic, timeout=600s)
    MCP->>Registry: Write initial state {"status": "running"}
    MCP->>Worker: Spawn daemon thread
    MCP-->>Client: Returns {job_id: "job_12345678", status: "running"} (<1s)

    par Background Execution
        Worker->>Engine: execute_research(prompt, stem)
        Engine->>Gateway: POST /v1beta/interactions
        Gateway-->>Engine: InteractionResponse + environment_id
        Engine->>Engine: Download tarball & extract .md, .html, .pdf, .docx
        Engine-->>Worker: ResearchExecutionResult
        Worker->>Registry: Atomically update state {"status": "completed", report_path, artifacts}
    and Client Polling
        loop Every 30-60 seconds
            Client->>MCP: get_research_status(job_id="job_12345678")
            MCP->>Registry: Read .jobs/job_12345678.json
            alt Still Running
                MCP-->>Client: {status: "running", elapsed_seconds: 45.2s}
            else Completed
                MCP-->>Client: {status: "completed", summary, report_path, artifacts}
            end
        end
    end
```

---

## 3. Core Component Boundaries

| Component | Responsibility | Inputs / Outputs |
| :--- | :--- | :--- |
| `mcp_server.py` | FastMCP server implementation. Manages the 6 sovereign tools, unwraps parameter defaults, and coordinates non-blocking background workers. | **In:** MCP JSON-RPC calls.<br/>**Out:** Markdown previews, job IDs, status payloads, diffs. |
| `deep_research.py` | Modular import shim over `deep-research/deep-research.py`. Builds prompt payloads, executes council queries, and extracts sandbox artifacts. | **In:** `prompt_content`, `prompt_stem`.<br/>**Out:** `ResearchExecutionResult` with paths to `.md`, `.html`, `.pdf`, `.docx`. |
| `refactor/refactor.py` | Dual-engine refactoring engine. Handles single-file CLI requests and concurrent batch manifests. Strips code fences and checks AST syntax. | **In:** Python source string or file path.<br/>**Out:** Validated PEP-8 code and `RefactorExecutionResult`. |
| `.jobs/` | Local filesystem job registry for tracking background research tasks. | JSON files named `<job_id>.json`. |
| `deep-research/prompts/` | Prompt template library containing structured 5-persona research protocols. | Markdown files defining personas and research rubrics. |

---

## 4. Contract Schemas & Invariants (Pydantic V2)

All data moving through `agy-agents` is strictly governed by Pydantic V2 models (`pydantic>=2.10.0`):

1. **`ProviderConfig` (Immutable)**:
   - Validates gateway URLs (`http://...` or `https://...`), download URL templates, and HTTP authorization headers.
   - Frozen to guarantee thread-safe configuration sharing.
2. **`InteractionRequest` & `InteractionResponse`**:
   - Models the Google Antigravity `/v1beta/interactions` wire format.
   - Ensures `agent` is set to `antigravity-preview-09-2026` and `environment` is `remote`.
3. **`RefactorManifest`**:
   - Strictly validates batch manifests in `refactor/manifests/*.json` (`target_files`, `reference_files`, `output_mode`).
4. **`StartResearchInput` & `RefactorInput`**:
   - Enforce `min_length`, non-zero timeouts, and strict `ConfigDict(extra="forbid", validate_assignment=True)` to reject malformed parameters early.

---

## 5. Deterministic Verification Primitives

Agents working on this repository MUST verify their work using the following deterministic commands:

```bash
# 1. Unit & Integration Test Suite (covers schemas, tool registration, lifecycle)
uv run python -m unittest tests/test_mcp_server.py

# 2. Gateway Connectivity & Health Inspection
uv run python -c "import mcp_server; print(mcp_server.check_gateway_health())"

# 3. Prompt Template Scan
uv run python -c "import mcp_server; print(mcp_server.list_research_prompts())"

# 4. FastMCP Server Entrypoint Check
uv run agy-mcp --help

# 5. Network SSE Endpoint Health Probe (Intranet)
curl -s -D - -o /dev/null -m 2 http://agy-agents.lan:7788/sse
# or direct IP:
curl -s -D - -o /dev/null -m 2 http://192.168.50.10:7788/sse
```
