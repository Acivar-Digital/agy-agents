import argparse
import json
import os
import shutil
import sys
import tarfile
import tempfile
import time
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Literal, TypeAlias
from dotenv import load_dotenv
import httpx
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
)

# ==============================================================================
# 🔑 API ROUTING & CONFIGURATION
# Loaded dynamically via .env
# ==============================================================================
RESEARCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = RESEARCH_DIR.parent
load_dotenv(dotenv_path=REPO_ROOT / ".env")
load_dotenv(dotenv_path=RESEARCH_DIR / ".env")

PROMPTS_DIR = RESEARCH_DIR / "prompts"
REPORTS_DIR = RESEARCH_DIR / "reports"

PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Shared HTTP client with HTTP/2 support and fallback
try:
    _HTTP_CLIENT = httpx.Client(http2=True, verify=False, timeout=httpx.Timeout(600.0))
except ImportError:
    print(
        "⚠️  The 'h2' package is not installed — falling back to HTTP/1.1. "
        "Install it (e.g. `pip install h2` or `uv pip install h2`) to enable HTTP/2.",
        file=sys.stderr,
    )
    _HTTP_CLIENT = httpx.Client(http2=False, verify=False, timeout=httpx.Timeout(600.0))


# ==============================================================================
# 📐 PYDANTIC V2 SCHEMAS & CONTRACTS
# ==============================================================================
ProviderChoice: TypeAlias = Literal["auto", "gemini", "literouter"]
ActiveProvider: TypeAlias = Literal["gemini", "literouter"]


class ProviderConfig(BaseModel):
    """Immutable, strictly validated configuration for an inference provider."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True, frozen=True)

    provider_name: ActiveProvider
    gateway_url: str
    download_url_template: str
    headers: dict[str, str]

    @field_validator("gateway_url", mode="after")
    @classmethod
    def validate_gateway_url(cls, v: str) -> str:
        v_stripped = v.strip()
        if not (v_stripped.startswith("http://") or v_stripped.startswith("https://")):
            raise ValueError(f"gateway_url must be an HTTP/HTTPS URL, got: {v}")
        return v_stripped

    @field_validator("download_url_template", mode="after")
    @classmethod
    def validate_download_url(cls, v: str) -> str:
        if "{env_id}" not in v:
            raise ValueError("download_url_template must contain '{env_id}' placeholder")
        return v

    def __iter__(self) -> Iterator[str | dict[str, str]]:
        """Support unpacking: provider_name, gateway_url, download_url_template, headers = config."""
        return iter((self.provider_name, self.gateway_url, self.download_url_template, self.headers))


class InteractionRequest(BaseModel):
    """Validated payload model for the LiteRouter / Gemini interactions API."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    agent: str = Field(min_length=1, description="Agent model identifier")
    input: str = Field(min_length=1, description="Prompt and instructions for the agent")
    environment: Literal["remote", "local"] = "remote"
    previous_interaction_id: str | None = None

    @field_validator("agent", "input", mode="after")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("String field cannot be empty or whitespace only")
        return s


class InteractionStep(BaseModel):
    """Represents a thought or execution step in an interaction."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    thought: str | None = None
    model_output: str | None = None
    tool_call: dict[str, JsonValue] | None = None
    tool_output: dict[str, JsonValue] | None = None


class InteractionResponse(BaseModel):
    """Response envelope from the LiteRouter / Gemini interaction endpoint."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    id: str | None = None
    object: str | None = None
    created: int | None = None
    model: str | None = None
    environment_id: str | None = None
    status: str | None = None
    steps: list[InteractionStep] = Field(default_factory=list)
    usage: dict[str, JsonValue] | None = None

    @property
    def step_count(self) -> int:
        return len(self.steps)

    def extract_text(self) -> str | None:
        """Extracts text content from the steps."""
        for step in reversed(self.steps):
            if step.model_output and step.model_output.strip():
                return step.model_output.strip()
            if step.thought and step.thought.strip():
                return step.thought.strip()
        return None


class ResearchExecutionRequest(BaseModel):
    """Validated input parameters for executing research."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    prompt_content: str = Field(min_length=1)
    prompt_stem: str = "custom_research"
    output_dir: Path | None = None
    previous_interaction_id: str | None = None
    provider: ProviderChoice = "auto"
    agent_model: str = "antigravity-preview-09-2026"
    timeout: float = Field(default=600.0, gt=0.0)

    @field_validator("prompt_content", mode="after")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("prompt_content must not be empty or whitespace only")
        return s


class ResearchExecutionResult(BaseModel):
    """Result data contract for completed deep research operations."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    status: Literal["completed", "failed"] = "completed"
    provider: ActiveProvider
    environment_id: str | None = None
    elapsed_seconds: float = Field(ge=0.0)
    raw_json_path: str
    extracted_files: list[str] = Field(default_factory=list)
    response: dict[str, JsonValue] = Field(default_factory=dict)

    def __getitem__(self, item: str) -> JsonValue:
        """Allow dict-style indexing for backwards compatibility."""
        if hasattr(self, item):
            val: JsonValue = getattr(self, item)
            return val
        raise KeyError(item)

    def get(self, item: str, default: JsonValue | None = None) -> JsonValue | None:
        return getattr(self, item, default)


def get_provider_config(provider_override: ProviderChoice = "auto") -> ProviderConfig:
    """
    Resolves the active provider, interaction URL, download URL, and auth headers.
    Returns: ProviderConfig instance (supports unpacking into a 4-tuple).
    """
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    lr_key = os.getenv("LITEROUTER_AUTH_KEY", "").strip()
    lr_host = os.getenv("LITEROUTER_HOST", "literouter.lan").strip()
    lr_port = os.getenv("LITEROUTER_PORT", "7766").strip()
    google_base = os.getenv("GOOGLE_NATIVE_BASE_URL", "https://generativelanguage.googleapis.com").strip()

    choice = provider_override.lower()
    if choice == "auto":
        env_provider = os.getenv("PROVIDER", "").strip().lower()
        if env_provider in ("gemini", "literouter"):
            choice = env_provider
        elif gemini_key:
            choice = "gemini"
        elif lr_key:
            choice = "literouter"
        else:
            choice = "none"

    if choice == "gemini":
        if not gemini_key:
            raise ValueError(
                "Gemini provider selected but GEMINI_API_KEY is not set.\n"
                "Please set GEMINI_API_KEY in your .env file or environment."
            )
        gateway_url = f"{google_base}/v1beta/interactions"
        download_url = f"{google_base}/v1beta/files/environment-{{env_id}}:download?alt=media"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": gemini_key,
        }
        return ProviderConfig(
            provider_name="gemini",
            gateway_url=gateway_url,
            download_url_template=download_url,
            headers=headers,
        )

    elif choice == "literouter":
        if not lr_key:
            raise ValueError(
                "LiteRouter provider selected but LITEROUTER_AUTH_KEY is not set.\n"
                "Please set LITEROUTER_AUTH_KEY in your .env file or environment."
            )
        gateway_url = f"http://{lr_host}:{lr_port}/v1beta/interactions"
        download_url = f"http://{lr_host}:{lr_port}/v1beta/files/environment-{{env_id}}:download?alt=media"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {lr_key}",
            "x-goog-api-key": lr_key,
        }
        return ProviderConfig(
            provider_name="literouter",
            gateway_url=gateway_url,
            download_url_template=download_url,
            headers=headers,
        )

    else:
        raise ValueError(
            "❌ No API credentials found!\n\n"
            "Please configure credentials using one of the following methods:\n"
            "  1. Public Community Mode (Direct Google Gemini API):\n"
            "     Set GEMINI_API_KEY in your .env file or environment.\n"
            "  2. Private / Self-Hosted Mode (LiteRouter Gateway):\n"
            "     Set LITEROUTER_AUTH_KEY in your .env file or environment.\n\n"
            "See .env.example for template configurations."
        )


# Instruct the agent to natively build the files and save them to disk
AGENT_FILE_INSTRUCTION = """
\n\n======================================================================
CRITICAL SYSTEM OVERRIDE FOR NATIVE FILE GENERATION:
You are operating in a remote code execution sandbox. You MUST natively generate the final output in 4 formats and save them to your current working directory.
1. Synthesize your final research into a comprehensive Markdown report.
2. Write and execute a Python script in your sandbox to create the files. (Use pip to install libraries like markdown, weasyprint, or python-docx as needed).
3. You MUST save the files exactly as:
   - report.md
   - report.html
   - report.pdf
   - report.docx
4. Do not output their contents in text. Just save them to disk and confirm completion.
======================================================================
"""


def download_and_extract_sandbox(
    env_id: str,
    base_output_path: Path,
    download_url_template: str,
    headers: dict[str, str],
) -> list[Path]:
    """Downloads the full sandbox snapshot (.tar) and extracts the target report files."""
    url = download_url_template.format(env_id=env_id)
    extracted_paths: list[Path] = []

    try:
        with _HTTP_CLIENT.stream("GET", url, headers=headers) as resp:
            if resp.status_code != 200:
                err_body = resp.read().decode("utf-8", errors="ignore")
                raise RuntimeError(
                    f"Failed to download sandbox snapshot (HTTP {resp.status_code}): {err_body}"
                )

            with tempfile.NamedTemporaryFile(delete=False, suffix=".tar") as tmp_tar:
                for chunk in resp.iter_bytes():
                    tmp_tar.write(chunk)
                tmp_tar_path = tmp_tar.name

        extract_dir = Path(tempfile.mkdtemp())
        with tarfile.open(tmp_tar_path) as tar:
            tar.extractall(path=extract_dir)

        formats = ["md", "html", "pdf", "docx"]
        for fmt in formats:
            target_name = f"report.{fmt}"
            found = False

            for root_dir, _, files in os.walk(extract_dir):
                if target_name in files:
                    src_file = Path(root_dir) / target_name
                    final_path = base_output_path.with_suffix(f".{fmt}")
                    shutil.move(str(src_file), str(final_path))
                    print(f"✅ Extracted native file: {final_path.name}")
                    extracted_paths.append(final_path)
                    found = True
                    break

            if not found:
                print(f"⚠️ Agent failed to generate {target_name} inside the sandbox.")

        os.remove(tmp_tar_path)
        shutil.rmtree(extract_dir)

    except httpx.HTTPError as e:
        raise RuntimeError(f"HTTP error downloading sandbox snapshot: {e}") from e
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"System error during sandbox extraction: {e}") from e

    return extracted_paths


def execute_research(
    prompt_content: str,
    prompt_stem: str = "custom_research",
    output_dir: Path | str | None = None,
    previous_interaction_id: str | None = None,
    provider: ProviderChoice = "auto",
    agent_model: str = "antigravity-preview-09-2026",
    timeout: float = 600.0,
) -> ResearchExecutionResult:
    """
    Core modular function for executing deep research.
    Can be called directly by CLI, scripts, or future MCP servers.
    """
    exec_req = ResearchExecutionRequest(
        prompt_content=prompt_content,
        prompt_stem=prompt_stem,
        output_dir=Path(output_dir) if output_dir else None,
        previous_interaction_id=previous_interaction_id,
        provider=provider,
        agent_model=agent_model,
        timeout=timeout,
    )

    provider_config = get_provider_config(exec_req.provider)

    target_reports_dir = exec_req.output_dir if exec_req.output_dir else REPORTS_DIR
    target_reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    base_output_path = target_reports_dir / f"{exec_req.prompt_stem}_{timestamp}"
    output_json_path = target_reports_dir / f"{exec_req.prompt_stem}_{timestamp}_raw.json"

    final_prompt = exec_req.prompt_content.strip() + AGENT_FILE_INSTRUCTION

    interaction_req = InteractionRequest(
        agent=exec_req.agent_model,
        input=final_prompt,
        environment="remote",
        previous_interaction_id=exec_req.previous_interaction_id,
    )

    start_time = time.time()
    resp = _HTTP_CLIENT.post(
        provider_config.gateway_url,
        headers=provider_config.headers,
        json=interaction_req.model_dump(exclude_none=True),
        timeout=exec_req.timeout,
    )
    elapsed = time.time() - start_time

    if resp.status_code >= 400:
        raise RuntimeError(
            f"HTTP Error {resp.status_code} from {provider_config.provider_name}: {resp.text[:500]}"
        )

    res_json = resp.json()
    output_json_path.write_text(json.dumps(res_json, indent=2), encoding="utf-8")

    parsed_resp = InteractionResponse.model_validate(res_json)
    env_id = parsed_resp.environment_id

    extracted_files: list[Path] = []
    if env_id:
        extracted_files = download_and_extract_sandbox(
            env_id=env_id,
            base_output_path=base_output_path,
            download_url_template=provider_config.download_url_template,
            headers=provider_config.headers,
        )

    return ResearchExecutionResult(
        status="completed",
        provider=provider_config.provider_name,
        environment_id=env_id,
        elapsed_seconds=round(elapsed, 2),
        raw_json_path=str(output_json_path),
        extracted_files=[str(p) for p in extracted_files],
        response=res_json,
    )


def run_deep_research():
    """CLI entrypoint for deep research execution."""
    parser = argparse.ArgumentParser(
        description="Deep Research Agent Tool (Dual-Engine: Google Gemini & LiteRouter)",
    )
    parser.add_argument("target", help="The name of the prompt template (e.g. Direction_of_JPY)")
    parser.add_argument(
        "--provider",
        choices=["auto", "gemini", "literouter"],
        default="auto",
        help="Inference provider: 'auto' (default: checks GEMINI_API_KEY then LiteRouter), 'gemini', or 'literouter'",
    )
    parser.add_argument(
        "--previous-interaction-id",
        dest="previous_interaction_id",
        default=None,
        help="Optional previous interaction ID for stateful multi-turn continuation",
    )
    args = parser.parse_args()

    prompt_stem = Path(args.target).stem
    prompt_file = PROMPTS_DIR / f"{prompt_stem}.md"

    if not prompt_file.exists():
        print(f"❌ Error: Prompt template not found at {prompt_file}")
        sys.exit(1)

    try:
        provider_name, gateway_url, _, _ = get_provider_config(args.provider)
    except ValueError as e:
        print(f"\n{e}\n")
        sys.exit(1)

    print("==================================================================")
    print("🔬 DEEP RESEARCH AGENT (Dual-Engine Execution)")
    print("==================================================================")
    print(f"⚡ Provider:       {provider_name.upper()}")
    print(f"📍 Target Gateway: {gateway_url}")
    print(f"📄 Reading Prompt: {prompt_file}")
    print(f"📁 Output Dir:     {REPORTS_DIR}")
    if args.previous_interaction_id:
        print(f"🔗 Stateful Turn:  Continuing interaction {args.previous_interaction_id}")
    print("==================================================================\n")

    prompt_content = prompt_file.read_text(encoding="utf-8").strip()

    print("🚀 Dispatching request. Agent is conducting research and rendering files...")
    try:
        result = execute_research(
            prompt_content=prompt_content,
            prompt_stem=prompt_stem,
            previous_interaction_id=args.previous_interaction_id,
            provider=args.provider,
        )
        print(f"\n✅ Execution finished in {result['elapsed_seconds']} seconds!")
        print(f"💾 Saved JSON API format to: {result['raw_json_path']}")
        if result["extracted_files"]:
            print(f"📦 Extracted files: {len(result['extracted_files'])}")
        print("\n🎉 Deep Research Complete!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Execution Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_deep_research()
