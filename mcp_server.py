"""
agy-agents MCP Server
====================

Autonomous Deep Research Council and Code Refactoring Agent Server
powered by Model Context Protocol (FastMCP), Google Gemini & LiteRouter.

Exposes 6 sovereign tools:
1. prepare_research_prompt: Generate and validate a domain-tailored 5-persona research prompt.
2. start_research: Non-blocking background research execution returning a job_id (avoids 60s MCP timeout).
3. get_research_status: Poll background research job progress, executive summary, and generated artifacts.
4. refactor_code: Synchronous autonomous Python code refactoring (PEP 8, clean architecture, type hints).
5. list_research_prompts: Discover available research prompt templates and stems in the repository.
6. check_gateway_health: Verify connectivity to LiteRouter (literouter.lan:7766) or Google Gemini API.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import json
import logging
import os
import re
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field
from pydantic.fields import FieldInfo

# Ensure repo root and deep-research/ are in sys.path
REPO_ROOT = Path(__file__).resolve().parent
DEEP_RESEARCH_DIR = REPO_ROOT / "deep-research"
PROMPTS_DIR = DEEP_RESEARCH_DIR / "prompts"
REPORTS_DIR = DEEP_RESEARCH_DIR / "reports"
JOBS_DIR = REPO_ROOT / ".jobs"

# Load environment variables from repo root and sub-packages
load_dotenv(REPO_ROOT / ".env")
load_dotenv(DEEP_RESEARCH_DIR / ".env")
load_dotenv(REPO_ROOT / "refactor" / ".env")
load_dotenv()


def _unwrap_field(val: Any, default_fallback: Any = None) -> Any:
    """Unwraps default FieldInfo if tool is called directly as a Python function."""
    if isinstance(val, FieldInfo):
        return default_fallback if val.default is ... else val.default
    return val


if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(DEEP_RESEARCH_DIR) not in sys.path:
    sys.path.insert(0, str(DEEP_RESEARCH_DIR))

# Import core modular engines
from deep_research import (  # noqa: E402
    ResearchExecutionResult,
    execute_research,
    get_provider_config as get_research_provider_config,
)
from refactor import (  # noqa: E402
    RefactorExecutionResult,
    clean_code_fences,
    execute_refactor,
    get_provider_config as get_refactor_provider_config,
)

logger = logging.getLogger("agy-mcp")

# Ensure required directories exist
JOBS_DIR.mkdir(parents=True, exist_ok=True)
PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# Pydantic V2 Contract Schemas
# ==============================================================================


class PromptPreparationInput(BaseModel):
    """Parameters for generating or validating a 5-persona research prompt."""

    topic: str = Field(
        ...,
        min_length=3,
        description="Core research subject or specific question for the 5-persona research council",
    )
    prompt_stem: str = Field(
        default="custom_research",
        description="File stem or identifier for generated prompt file (e.g., 'Direction_of_JPY')",
    )
    custom_rubric: str | None = Field(
        default=None,
        description="Optional specific research guidelines, scope limits, or focus domains",
    )

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class PromptPreparationOutput(BaseModel):
    """Result of prompt preparation."""

    prompt_stem: str
    prompt_file_path: str
    prompt_preview: str
    character_count: int
    cli_command: str

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class StartResearchInput(BaseModel):
    """Parameters to launch a background research job."""

    prompt_stem_or_topic: str = Field(
        ...,
        min_length=3,
        description="Existing prompt stem (e.g. 'Direction_of_JPY') or a research topic to sculpt dynamically",
    )
    prompt_stem: str = Field(
        default="custom_research",
        description="File stem to use if prompt needs to be prepared from topic",
    )
    custom_rubric: str | None = Field(
        default=None,
        description="Optional specific rubric or focus if creating a new prompt dynamically",
    )
    timeout_seconds: float = Field(
        default=600.0,
        gt=0.0,
        description="Max execution time in seconds (default: 600.0)",
    )

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class StartResearchOutput(BaseModel):
    """Immediate acknowledgment when background research job is launched."""

    job_id: str
    status: Literal["running", "failed"]
    prompt_stem: str
    message: str
    check_status_command: str

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class ResearchStatusInput(BaseModel):
    """Parameters to query research job progress."""

    job_id: str = Field(
        ...,
        min_length=1,
        description="Unique job ID returned by start_research",
    )

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class ResearchStatusOutput(BaseModel):
    """Job status, execution progress, and report artifact locations."""

    job_id: str
    status: Literal["running", "completed", "failed", "not_found"]
    prompt_stem: str
    elapsed_seconds: float
    summary: str | None = None
    report_path: str | None = None
    artifacts: list[str] = Field(default_factory=list)
    error: str | None = None

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class RefactorInput(BaseModel):
    """Parameters for autonomous code refactoring."""

    code: str = Field(
        ...,
        min_length=5,
        description="Python source code to refactor according to clean architecture and PEP 8",
    )
    filename: str = Field(
        default="target.py",
        description="Target filename hint used for structural context",
    )
    instructions: str | None = Field(
        default=None,
        description="Custom refactoring instructions, e.g. 'convert to Pydantic V2 models and add strict type hints'",
    )

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class RefactorOutput(BaseModel):
    """Result of autonomous code refactoring."""

    status: Literal["completed", "failed"] = "completed"
    refactored_code: str = Field(
        ...,
        description="Cleaned, PEP-8 compliant Python code without markdown code block fences",
    )
    diff_summary: str = Field(
        ...,
        description="Summary of modifications applied (lines added, removed, changed)",
    )
    elapsed_seconds: float = Field(ge=0.0)

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class GatewayStatusOutput(BaseModel):
    """Gateway connectivity and provider status."""

    gateway_url: str
    reachable: bool
    active_provider: str
    details: str

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


# ==============================================================================
# Helper Functions & Prompt Sculptor
# ==============================================================================


def _clean_stem(name: str) -> str:
    """Sanitizes prompt stem into valid alphanumeric filename."""
    stem = name.strip()
    if stem.endswith(".md"):
        stem = stem[:-3]
    return re.sub(r"[^\w\-_]", "_", stem)


def _sculpt_5_persona_prompt(topic: str, custom_rubric: str | None = None) -> str:
    """
    Generates an institutional Citi-grade 5-persona research prompt tailored to the given topic.
    """
    rubric_section = ""
    if custom_rubric and custom_rubric.strip():
        rubric_section = f"""
---

## 5. CUSTOM USER RUBRIC & SCOPE CONSTRAINTS
{custom_rubric.strip()}
"""

    return f"""# CITI INSTITUTIONAL DEEP RESEARCH PROTOCOL: PERSONA COUNCIL & RISK COMMITTEE

## 1. OBJECTIVE & TARGET TOPIC
Conduct an institutional-grade deep research investigation on:
"{topic.strip()}"

---

## 2. CITI EDITORIAL SCHEMA & FORMATTING MANDATES
The final deliverable MUST strictly adhere to the editorial standards of **Citi Institutional Research**:

1. **Institutional Header Block**:
   ```markdown
   # CITI INSTITUTIONAL DEEP RESEARCH | {topic.strip()[:60]}
   **Classification:** CONFIDENTIAL / INSTITUTIONAL INVESTMENT RESEARCH
   **Rating Outlook:** [ACCELERATING / NEUTRAL / BEARISH] | **Target Horizon:** 2026–2036
   **Coverage:** {topic.strip()}
   ```

2. **Citi Investment Thesis Callout Box**:
   Include a mandatory executive box immediately following the header:
   ```markdown
   > 📌 **CITI INVESTMENT THESIS & CORE TAKEAWAYS**
   > • **Core Verdict:** [2-sentence institutional summary on overall thesis & outlook]
   > • **Forecast Range / Target:** [Base / Bull / Bear Quantitative Scenarios]
   > • **Dominant Growth Vector / Catalyst:** [Primary market or regulatory accelerant]
   > • **Key Bottleneck / Risk:** [Critical differentiator or operational constraint]
   ```

3. **Zero Hand-Waving / Hardened Quantitative Rigor**:
   - Every key claim MUST include explicit numerical values, units, metrics, and pricing curves ($M, $B, %, bps).
   - State all market sizes, volumes, and cost premiums in explicit units.

4. **Structured Data Dashboards & Visual Tables**:
   - Every section must contain at least one high-density Markdown comparison table.

---

## 3. AGENT EXECUTION PROTOCOL (CRITICAL)
You are an advanced execution engine operating in a remote sandbox. Follow this exact workflow:
1. **Phase 1: 50-Source Research Sprint** — Minimum 10 distinct Google Searches per persona (50 total independent sources minimum). Store findings in internal memory.
2. **Phase 2: The Aggregator** — Combine findings into a dense, highly detailed draft preserving granular numbers, entity names, pricing, and quotes.
3. **Phase 3: Supervisor Review & Committee Vote** — Personas vote 1 to 5. Execute exactly one revision cycle to patch gaps.
4. **Phase 4: Final Output Delivery** — Output final Markdown report directly into text response. Do not truncate.

---

## 4. THE 5-PERSONA RESEARCH COUNCIL

### Persona 1: Technology & Systems Architect
- **Focus:** Technical architectures, performance benchmarks, engineering bottlenecks, and technical trade-offs.
- **Key Questions:** What are the fundamental physical/architectural constraints? What are current state-of-the-art benchmarks?

### Persona 2: Regulatory, Geopolitical & Policy Analyst
- **Focus:** Regulatory frameworks, international compliance, geopolitical risks, and antitrust or jurisdictional barriers.
- **Key Questions:** What regulatory milestones govern adoption? Where do compliance and cross-border frictions emerge?

### Persona 3: Quantitative Forecaster & Macro Sizing Specialist
- **Focus:** Total Addressable Market (TAM), CAGR forecasts, revenue trajectories, unit economics, and capital expenditure curves.
- **Key Questions:** What is the 5-to-10 year CAGR under Bull, Base, and Bear cases? What is the sensitivity to macro rates?

### Persona 4: Supply Chain, Vendor Ecosystem & Cost Analyst
- **Focus:** Component availability, input cost structures, vendor concentration risks, and margin sustainability.
- **Key Questions:** Where are single-source points of failure? What is the unit cost deflation or inflation rate?

### Persona 5: Bear Case Dissenter & Devil's Advocate
- **Focus:** Stress-testing assumptions, technological substitution, capital exhaustion, and structural risks.
- **Key Questions:** Under what conditions does this thesis collapse? What does consensus fundamentally misprice?
{rubric_section}
---

## 6. REQUIRED REPORT STRUCTURE
1. **Citi Cover Header & Executive Investment Thesis Box**
2. **Section I: Technical & Architectural Breakdown (with benchmark comparison table)**
3. **Section II: Policy, Regulatory & Geopolitical Matrix (with timeline matrix)**
4. **Section III: Quantitative Market Sizing & Sensitivity (with Bull/Base/Bear scenarios)**
5. **Section IV: Supply Chain & Cost Economics (with unit margin table)**
6. **Section V: Council Consensus vs. Bear Case Dissent Matrix**
7. **Section VI: Supervisor Scorecard & Revision Log**
8. **Sources & References** (50+ citations with URLs)
9. **Appendix: Persona Dossiers** (Raw findings, quotes, metrics, search queries from all 5 personas)
"""


def _save_job_state(job_id: str, data: dict[str, Any]) -> None:
    """Atomically writes job state to disk."""
    job_file = JOBS_DIR / f"{job_id}.json"
    temp_file = JOBS_DIR / f"{job_id}.json.tmp"
    temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp_file.replace(job_file)


def _load_job_state(job_id: str) -> dict[str, Any] | None:
    """Reads job state from disk."""
    job_file = JOBS_DIR / f"{job_id}.json"
    if not job_file.exists():
        return None
    try:
        return json.loads(job_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def _extract_markdown_from_raw(raw_response: dict[str, Any] | None) -> str | None:
    """Extracts full markdown output from Antigravity interaction steps."""
    if not raw_response or "steps" not in raw_response:
        return None
    steps = raw_response.get("steps", [])
    for step in reversed(steps):
        if not isinstance(step, dict):
            continue
        output = step.get("model_output", "")
        if isinstance(output, str) and output.strip():
            return output.strip()
        content = step.get("content")
        if isinstance(content, list):
            for part in content:
                if (
                    isinstance(part, dict)
                    and isinstance(part.get("text"), str)
                    and part["text"].strip()
                ):
                    return part["text"].strip()
    return None


def _extract_summary_from_report(
    report_path: Path | None, raw_response: dict[str, Any] | None
) -> str:
    """Extracts a high-signal markdown summary from generated report or response steps."""
    if report_path and report_path.exists():
        text = report_path.read_text(encoding="utf-8")
        # Look for executive thesis callout box or first 1200 characters
        match = re.search(
            r"(> 📌 \*\*CITI INVESTMENT THESIS.*?\n(?=[^>]))", text, re.DOTALL
        )
        if match:
            return match.group(1).strip()
        lines = [
            line
            for line in text.splitlines()
            if line.strip() and not line.startswith("#")
        ]
        return "\n".join(lines[:12])

    raw_md = _extract_markdown_from_raw(raw_response)
    if raw_md:
        return raw_md[:1000].strip()

    return "Research completed successfully. See artifact links for complete report."


def _run_research_worker(
    job_id: str,
    prompt_content: str,
    prompt_stem: str,
    timeout_seconds: float,
) -> None:
    """Background worker executing research and updating job state."""
    start_time = time.time()
    try:
        result: ResearchExecutionResult = execute_research(
            prompt_content=prompt_content,
            prompt_stem=prompt_stem,
            timeout=timeout_seconds,
        )

        elapsed = round(time.time() - start_time, 2)
        extracted = [str(f) for f in result.extracted_files]
        report_md = next(
            (Path(f) for f in result.extracted_files if f.endswith(".md")), None
        )
        summary = _extract_summary_from_report(report_md, result.response)

        job_data = {
            "job_id": job_id,
            "status": "completed",
            "prompt_stem": prompt_stem,
            "elapsed_seconds": elapsed,
            "report_path": str(report_md)
            if report_md
            else (extracted[0] if extracted else None),
            "artifacts": extracted,
            "summary": summary,
            "raw_json_path": result.raw_json_path,
            "error": None,
        }
        _save_job_state(job_id, job_data)
    except Exception as exc:
        elapsed = round(time.time() - start_time, 2)
        job_data = {
            "job_id": job_id,
            "status": "failed",
            "prompt_stem": prompt_stem,
            "elapsed_seconds": elapsed,
            "report_path": None,
            "artifacts": [],
            "summary": None,
            "error": str(exc),
        }
        _save_job_state(job_id, job_data)


# ==============================================================================
# FastMCP Server Instance & Tools
# ==============================================================================

mcp = FastMCP(
    "agy-agents",
    instructions=(
        "Autonomous Deep Research Council and Code Refactoring Agent Wrapper. "
        "HOW IT WORKS: (1) Prepare or select a research prompt in deep-research/prompts/<stem>.md "
        "via prepare_research_prompt or start_research. (2) Trigger the CLI command "
        "`uv run python deep-research/deep-research.py <stem>` via your bash tool (do NOT use & or nohup). "
        "(3) The CLI blocks until research completes, exits with exit code 0 to wake the LLM up, and "
        "prints the exact path to the generated Markdown (.md) report in deep-research/reports/."
    ),
)


@mcp.tool(
    name="prepare_research_prompt",
    description=(
        "Generate and validate an institutional Citi-grade 5-persona research prompt file. "
        "Saves the prompt into deep-research/prompts/<stem>.md and returns instructions on how "
        "the workflow operates plus the exact CLI command to trigger so the LLM wakes up on exit code 0 "
        "to collect the .md report."
    ),
)
def prepare_research_prompt(
    topic: str = Field(
        ...,
        min_length=3,
        description="Core research subject or specific question for the 5-persona research council",
    ),
    prompt_stem: str = Field(
        default="custom_research",
        description="File stem or identifier for generated prompt file (e.g. 'Direction_of_JPY')",
    ),
    custom_rubric: str | None = Field(
        default=None,
        description="Optional specific research guidelines, scope limits, or focus domains",
    ),
) -> str:
    """Crafts and saves a tailored 5-persona research prompt and returns CLI trigger instructions."""
    topic = _unwrap_field(topic, "")
    prompt_stem = _unwrap_field(prompt_stem, "custom_research")
    custom_rubric = _unwrap_field(custom_rubric, None)

    req = PromptPreparationInput(
        topic=topic,
        prompt_stem=prompt_stem,
        custom_rubric=custom_rubric,
    )

    clean_stem = _clean_stem(req.prompt_stem)
    target_file = PROMPTS_DIR / f"{clean_stem}.md"

    prompt_content = _sculpt_5_persona_prompt(req.topic, req.custom_rubric)
    target_file.write_text(prompt_content, encoding="utf-8")

    cli_command = f"uv run python deep-research/deep-research.py {clean_stem}"

    output = PromptPreparationOutput(
        prompt_stem=clean_stem,
        prompt_file_path=str(target_file),
        prompt_preview=prompt_content[:800] + "\n...",
        character_count=len(prompt_content),
        cli_command=cli_command,
    )

    return (
        f"### Research Prompt Prepared: `{output.prompt_stem}`\n\n"
        f"- **Prompt File:** `{output.prompt_file_path}` ({output.character_count:,} chars)\n\n"
        f"#### 1. How It Works\n"
        f"- The 5-persona Deep Research Council runs against `/v1beta/interactions` (`antigravity-preview-09-2026`).\n"
        f"- It synthesizes the final report **only in Markdown (`.md`) format** inside `{REPORTS_DIR}/`.\n\n"
        f"#### 2. Trigger the CLI Now\n"
        f"Run this exact command using your `bash` tool (do **not** append `&` or `nohup`, and set `timeout: 600`):\n"
        f"```bash\n{output.cli_command}\n```\n"
        f"- When the CLI finishes, it exits with **exit code `0`** (which automatically wakes you up if backgrounded by your harness) and prints `📄 COLLECT MARKDOWN REPORT AT: <path>.md`.\n"
        f"- Read that `.md` file path directly to consume the report.\n\n"
        f"#### Prompt Preview\n```markdown\n{output.prompt_preview}\n```"
    )


@mcp.tool(
    name="start_research",
    description=(
        "Instruction wrapper to prepare a research topic/stem and get the exact CLI command "
        "to trigger the 5-persona deep research run. The CLI exits with exit code 0 when done "
        "and prints the exact .md report path to collect."
    ),
)
def start_research(
    prompt_stem_or_topic: str = Field(
        ...,
        min_length=3,
        description="Existing prompt stem (e.g. 'Direction_of_JPY') or a research topic to sculpt dynamically",
    ),
    prompt_stem: str = Field(
        default="custom_research",
        description="File stem to use if prompt needs to be prepared dynamically",
    ),
    custom_rubric: str | None = Field(
        default=None,
        description="Optional specific rubric or focus if creating a new prompt dynamically",
    ),
    timeout_seconds: float = Field(
        default=600.0,
        gt=0.0,
        description="Max execution time in seconds (default: 600.0)",
    ),
) -> str:
    """Prepares the prompt if needed and returns instructions for the LLM to trigger the CLI."""
    prompt_stem_or_topic = _unwrap_field(prompt_stem_or_topic, "")
    prompt_stem = _unwrap_field(prompt_stem, "custom_research")
    custom_rubric = _unwrap_field(custom_rubric, None)
    timeout_seconds = _unwrap_field(timeout_seconds, 600.0)

    req = StartResearchInput(
        prompt_stem_or_topic=prompt_stem_or_topic,
        prompt_stem=prompt_stem,
        custom_rubric=custom_rubric,
        timeout_seconds=timeout_seconds,
    )

    clean_target = _clean_stem(req.prompt_stem_or_topic)
    potential_file = PROMPTS_DIR / f"{clean_target}.md"

    if potential_file.exists():
        effective_stem = clean_target
        prompt_file_path = potential_file
    else:
        effective_stem = _clean_stem(req.prompt_stem)
        prompt_content = _sculpt_5_persona_prompt(
            req.prompt_stem_or_topic, req.custom_rubric
        )
        prompt_file_path = PROMPTS_DIR / f"{effective_stem}.md"
        prompt_file_path.write_text(prompt_content, encoding="utf-8")

    cli_command = f"uv run python deep-research/deep-research.py {effective_stem}"
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    initial_job_data = {
        "job_id": job_id,
        "status": "running",
        "prompt_stem": effective_stem,
        "started_at": time.time(),
        "elapsed_seconds": 0.0,
        "report_path": None,
        "artifacts": [],
        "summary": None,
        "error": None,
    }
    _save_job_state(job_id, initial_job_data)

    output = StartResearchOutput(
        job_id=job_id,
        status="running",
        prompt_stem=effective_stem,
        message=(
            "Prompt ready. Trigger the CLI command below via your bash tool. "
            "The CLI exits with code 0 when finished and prints the exact .md report path to collect."
        ),
        check_status_command=cli_command,
    )

    return (
        f"### Deep Research Instructions (`{output.job_id}` | Stem: `{output.prompt_stem}`)\n\n"
        f"#### 1. How It Works\n"
        f"- Your research prompt is saved at `{prompt_file_path}`.\n"
        f"- Deep research runs via the CLI script `deep-research/deep-research.py`, which dispatches the 5-persona council to `/v1beta/interactions` and writes the final report **only in `.md` format** to `{REPORTS_DIR}/{output.prompt_stem}_<YYYYMMDD_HHMM>.md`.\n\n"
        f"#### 2. Trigger the CLI Now\n"
        f"Execute this command with your `bash` tool (use `timeout: {int(req.timeout_seconds)}`, do **not** use `&` or `nohup`):\n"
        f"```bash\n{cli_command}\n```\n\n"
        f"#### 3. Wake-Up & Collect Report (`.md` Only)\n"
        f"- When the CLI finishes, it exits with **exit code `0`**, waking you up with verbose output containing:\n"
        f"  `📄 COLLECT MARKDOWN REPORT AT: {REPORTS_DIR}/{output.prompt_stem}_<YYYYMMDD_HHMM>.md`\n"
        f"- Once woken by exit code `0`, read that `.md` file directly (or call `get_research_status(job_id='{output.prompt_stem}')`) to consume the report."
    )


def _find_latest_report_by_stem(stem_or_id: str) -> dict[str, Any] | None:
    """Finds the latest completed .md report matching a prompt stem in REPORTS_DIR."""
    clean = _clean_stem(stem_or_id)
    md_matches = sorted(REPORTS_DIR.glob(f"{clean}_*.md"))
    if not md_matches:
        return None
    latest_md = md_matches[-1]
    prefix = latest_md.stem
    raw_json = REPORTS_DIR / f"{prefix}_raw.json"
    summary = _extract_summary_from_report(latest_md, None)
    return {
        "job_id": stem_or_id,
        "status": "completed",
        "prompt_stem": clean,
        "elapsed_seconds": 0.0,
        "report_path": str(latest_md),
        "artifacts": [str(latest_md)],
        "summary": summary,
        "raw_json_path": str(raw_json) if raw_json.exists() else None,
        "error": None,
    }


@mcp.tool(
    name="get_research_status",
    description=(
        "Retrieve the latest completed Markdown (.md) report for a prompt stem or job_id, "
        "including executive summary, full Markdown report text, and exact .md file location."
    ),
)
def get_research_status(
    job_id: str = Field(
        ...,
        min_length=1,
        description="Prompt stem (e.g. 'Direction_of_JPY') or job ID returned by start_research",
    ),
) -> str:
    """Queries the latest .md report or job status for a research stem/job_id."""
    job_id = _unwrap_field(job_id, "")
    req = ResearchStatusInput(job_id=job_id)
    job_data = _find_latest_report_by_stem(req.job_id)
    if not job_data:
        loaded = _load_job_state(req.job_id)
        if loaded:
            stem_report = _find_latest_report_by_stem(loaded.get("prompt_stem", ""))
            job_data = stem_report if stem_report else loaded

    if not job_data:
        return f"Error: Job ID `{req.job_id}` was not found in `.jobs/` registry."

    status = job_data.get("status", "unknown")
    prompt_stem = job_data.get("prompt_stem", "unknown")
    elapsed = job_data.get("elapsed_seconds", 0.0)
    if status == "running" and "started_at" in job_data:
        elapsed = round(time.time() - job_data["started_at"], 1)

    if status == "running":
        return (
            f"### Research In Progress: `{req.job_id}`\n\n"
            f"- **Status:** `running` ⏳\n"
            f"- **Prompt Stem:** `{prompt_stem}`\n"
            f"- **Elapsed Time:** {elapsed:.1f}s\n"
            f"- Council is conducting 50 Google searches and synthesizing whitepaper. Please check again in 30-60 seconds."
        )

    if status == "failed":
        error_msg = job_data.get("error", "Unknown error")
        return (
            f"### Research Failed: `{req.job_id}`\n\n"
            f"- **Status:** `failed` ❌\n"
            f"- **Prompt Stem:** `{prompt_stem}`\n"
            f"- **Elapsed Time:** {elapsed:.1f}s\n"
            f"- **Error:**\n```\n{error_msg}\n```"
        )

    # Status completed
    report_path = job_data.get("report_path", "N/A")
    artifacts = job_data.get("artifacts", [])
    summary = job_data.get("summary", "No executive summary available.")
    public_base = os.getenv("MCP_PUBLIC_URL", "http://agy-agents.lan:7788").rstrip("/")

    artifact_lines: list[str] = []
    for a in artifacts:
        fname = Path(a).name
        artifact_lines.append(f"  - `{a}` (`{public_base}/reports/{fname}`)")
    artifacts_md = "\n".join(artifact_lines) if artifact_lines else "  - None"

    full_markdown = ""
    if report_path and report_path != "N/A":
        rp = Path(report_path)
        if rp.exists() and rp.suffix == ".md":
            full_markdown = rp.read_text(encoding="utf-8")
    if not full_markdown:
        raw_json_path = job_data.get("raw_json_path")
        if raw_json_path and Path(raw_json_path).exists():
            try:
                raw_obj = json.loads(Path(raw_json_path).read_text(encoding="utf-8"))
                full_markdown = _extract_markdown_from_raw(raw_obj) or ""
            except Exception:
                full_markdown = ""

    report_section = (
        f"\n\n#### Full Markdown Report\n\n{full_markdown}" if full_markdown else ""
    )

    return (
        f"### Research Completed: `{req.job_id}`\n\n"
        f"- **Status:** `completed` ✅\n"
        f"- **Prompt Stem:** `{prompt_stem}`\n"
        f"- **Elapsed Time:** {elapsed:.1f}s\n"
        f"- **Report Markdown:** `{report_path}`\n\n"
        f"#### Artifacts Generated\n{artifacts_md}\n\n"
        f"#### Executive Summary\n{summary}"
        f"{report_section}"
    )


@mcp.tool(
    name="refactor_code",
    description=(
        "Autonomously refactor Python code enforcing clean architecture, strict type hints, "
        "and PEP 8 standards. Fast synchronous tool (takes 5-15s). Returns cleaned raw Python code "
        "and unified diff summary."
    ),
)
def refactor_code(
    code: str = Field(
        ...,
        min_length=5,
        description="Python source code to refactor according to clean architecture and PEP 8",
    ),
    filename: str = Field(
        default="target.py",
        description="Target filename hint used for structural context",
    ),
    instructions: str | None = Field(
        default=None,
        description="Custom refactoring instructions, e.g. 'convert to Pydantic V2 models and add strict type hints'",
    ),
) -> str:
    """Executes synchronous automated refactoring on provided code."""
    code = _unwrap_field(code, "")
    filename = _unwrap_field(filename, "target.py")
    instructions = _unwrap_field(instructions, None)

    req = RefactorInput(
        code=code,
        filename=filename,
        instructions=instructions,
    )

    custom_prompt = req.instructions or ""
    start_time = time.time()

    result: RefactorExecutionResult = execute_refactor(
        code_content=req.code,
        target_filename=req.filename,
        prompt=custom_prompt,
    )
    elapsed = round(time.time() - start_time, 2)

    cleaned_code = clean_code_fences(result.refactored_code)

    # Syntax verification
    syntax_status = "Valid Python Syntax"
    try:
        ast.parse(cleaned_code)
    except SyntaxError as e:
        syntax_status = f"Syntax Warning: {e}"

    # Calculate unified diff summary
    orig_lines = req.code.splitlines()
    new_lines = cleaned_code.splitlines()
    diff = list(
        difflib.unified_diff(
            orig_lines,
            new_lines,
            fromfile=f"original/{req.filename}",
            tofile=f"refactored/{req.filename}",
            lineterm="",
        )
    )
    diff_text = "\n".join(diff[:50])
    if len(diff) > 50:
        diff_text += f"\n... ({len(diff) - 50} more diff lines)"

    output = RefactorOutput(
        status="completed",
        refactored_code=cleaned_code,
        diff_summary=f"{syntax_status} | {len(orig_lines)} -> {len(new_lines)} lines",
        elapsed_seconds=elapsed,
    )

    return (
        f"### Refactoring Completed ({output.elapsed_seconds:.2f}s)\n\n"
        f"- **Status:** `{output.status}` ({output.diff_summary})\n"
        f"- **File:** `{req.filename}`\n\n"
        f"#### Refactored Code\n```python\n{output.refactored_code}\n```\n\n"
        f"#### Diff Preview\n```diff\n{diff_text}\n```"
    )


@mcp.tool(
    name="list_research_prompts",
    description="List all available structured research prompt templates and stems in the repository.",
)
def list_research_prompts() -> str:
    """Scans deep-research/prompts/*.md and returns available prompt templates."""
    if not PROMPTS_DIR.exists():
        return "No prompts directory found."

    prompt_files = sorted(PROMPTS_DIR.glob("*.md"))
    if not prompt_files:
        return "No prompt files found in `deep-research/prompts/`."

    lines = [
        "### Available Research Prompts\n",
        "| Stem | Type | Target Objective |",
        "| :--- | :--- | :--- |",
    ]

    for p in prompt_files:
        stem = p.stem
        is_template = stem.startswith("_template")
        ptype = "Template" if is_template else "Ready Topic"

        # Read first 25 lines to extract objective
        try:
            content = p.read_text(encoding="utf-8")[:1500]
            obj_match = re.search(
                r'##\s*1?\s*\.?\s*OBJECTIVE[^\n]*\n[^\n]*\n"([^"]+)"',
                content,
                re.IGNORECASE,
            )
            if not obj_match:
                obj_match = re.search(
                    r'##\s*1?\s*\.?\s*OBJECTIVE[^\n]*\n.*?on:\s*\n"([^"]+)"',
                    content,
                    re.DOTALL | re.IGNORECASE,
                )
            if not obj_match:
                obj_match = re.search(r"#\s*([^\n]+)", content)

            objective = (
                obj_match.group(1).strip()
                if obj_match
                else "Standard research council protocol"
            )
            # Truncate for table
            if len(objective) > 75:
                objective = objective[:72] + "..."
        except Exception:
            objective = "Could not parse"

        lines.append(f"| `{stem}` | {ptype} | {objective} |")

    lines.append(
        "\nTo start research, call `start_research(prompt_stem_or_topic='<stem>')`."
    )
    return "\n".join(lines)


@mcp.tool(
    name="check_gateway_health",
    description="Inspect connectivity and configuration for the active inference gateway (LiteRouter or Gemini).",
)
def check_gateway_health() -> str:
    """Probes configured gateway endpoint and returns reachability status."""
    try:
        config = get_research_provider_config("auto")
    except Exception as e:
        return f"### Gateway Configuration Error\n\nFailed to load provider config: {e}"

    gateway_url = config.gateway_url
    provider_name = config.provider_name
    reachable = False
    details = ""

    start_time = time.time()
    try:
        if provider_name == "literouter":
            # For LiteRouter, probe /health or interactions endpoint
            health_url = gateway_url.replace("/v1beta/interactions", "/health")
            resp = httpx.get(health_url, timeout=3.0)
            latency = round((time.time() - start_time) * 1000, 1)
            if resp.status_code == 200:
                reachable = True
                details = f"HTTP {resp.status_code} in {latency}ms (healthy: {resp.text.strip()[:60]})"
            else:
                reachable = True
                details = f"HTTP {resp.status_code} in {latency}ms from /health"
        else:
            # Direct Gemini API
            resp = httpx.get(gateway_url, timeout=4.0)
            latency = round((time.time() - start_time) * 1000, 1)
            reachable = True
            details = f"Host reachable in {latency}ms (HTTP {resp.status_code})"
    except Exception as e:
        latency = round((time.time() - start_time) * 1000, 1)
        reachable = False
        details = f"Connection failed after {latency}ms: {e}"

    status_icon = "✅ Reachable" if reachable else "❌ Unreachable"
    return (
        f"### Gateway Health: {status_icon}\n\n"
        f"- **Active Provider:** `{provider_name}`\n"
        f"- **Target URL:** `{gateway_url}`\n"
        f"- **Status Details:** {details}"
    )


# ==============================================================================
# Entrypoint Runner & Dual-Transport Network App
# ==============================================================================


class _HybridSseStreamableASGIApp:
    """ASGI endpoint for /sse supporting both Legacy SSE (GET) and Streamable HTTP (POST/DELETE/session GET)."""

    def __init__(
        self,
        server: FastMCP,
        sse_transport: Any,
        streamable_app: Any,
    ) -> None:
        self._server = server
        self._sse = sse_transport
        self._streamable_app = streamable_app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        method = str(scope.get("method", "GET")).upper()
        headers = {bytes(k).lower() for k, _ in scope.get("headers", ())}
        if method in ("POST", "DELETE") or b"mcp-session-id" in headers:
            await self._streamable_app(scope, receive, send)
            return
        if method == "HEAD":
            from starlette.responses import Response

            resp = Response(status_code=200, media_type="text/event-stream")
            await resp(scope, receive, send)
            return
        async with self._sse.connect_sse(scope, receive, send) as streams:
            await self._server._mcp_server.run(
                streams[0],
                streams[1],
                self._server._mcp_server.create_initialization_options(),
            )


def create_network_app(server: FastMCP | None = None) -> Any:
    """Builds a Starlette ASGI app serving both Streamable HTTP (/mcp, /sse) and Legacy SSE (/sse, /messages/)."""
    from fastmcp.server.http import create_streamable_http_app
    from mcp.server.sse import SseServerTransport
    from mcp.server.transport_security import TransportSecuritySettings
    from starlette.routing import Mount, Route

    target_server = server or mcp
    app = create_streamable_http_app(
        server=target_server,
        streamable_http_path="/mcp",
    )

    streamable_endpoint: Any = None
    for route in app.routes:
        if isinstance(route, Route) and route.path == "/mcp":
            streamable_endpoint = route.endpoint
            break

    sse_transport = SseServerTransport(
        "/messages/",
        security_settings=TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        ),
    )
    hybrid_sse_app = _HybridSseStreamableASGIApp(
        server=target_server,
        sse_transport=sse_transport,
        streamable_app=streamable_endpoint,
    )

    app.routes.insert(
        0,
        Route(
            "/sse",
            endpoint=hybrid_sse_app,
            methods=["GET", "HEAD", "POST", "DELETE"],
        ),
    )
    app.routes.insert(
        1,
        Mount(
            "/messages/",
            app=sse_transport.handle_post_message,
        ),
    )

    async def _serve_report_file(request: Any) -> Any:
        from starlette.responses import FileResponse, PlainTextResponse

        filename = Path(request.path_params.get("filename", "")).name
        target = (REPORTS_DIR / filename).resolve()
        if not target.is_relative_to(REPORTS_DIR.resolve()) or not target.is_file():
            return PlainTextResponse("Report artifact not found", status_code=404)
        return FileResponse(target)

    app.routes.insert(
        2,
        Route(
            "/reports/{filename}",
            endpoint=_serve_report_file,
            methods=["GET", "HEAD"],
        ),
    )
    return app


def main() -> None:
    """Runs the FastMCP server supporting stdio and dual-transport SSE/Streamable-HTTP network endpoints."""
    parser = argparse.ArgumentParser(description="agy-agents FastMCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http", "streamable-http"],
        default=os.getenv("MCP_TRANSPORT", "stdio"),
        help="Transport protocol (default: stdio, or sse / http for network endpoint)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_HOST", "0.0.0.0"),
        help="Host address to bind to for network transports (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", "7788")),
        help="Port to bind to for network transports (default: 7788)",
    )
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        import uvicorn

        app = create_network_app(mcp)
        uvicorn.run(app, host=args.host, port=args.port, timeout_graceful_shutdown=2)


if __name__ == "__main__":
    main()
