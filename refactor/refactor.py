import argparse
import concurrent.futures
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Literal, TypeAlias
from dotenv import load_dotenv
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
)

# ==============================================================================
# 🔑 CONFIGURATION & ENVIRONMENT SETUP
# ==============================================================================
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
load_dotenv(dotenv_path=SCRIPT_DIR / ".env")

MANIFESTS_DIR = SCRIPT_DIR / "manifests"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "refactor" / "output"
DEFAULT_PROMPT_FILE = SCRIPT_DIR / "prompt.txt"
AGENT_NAME = os.getenv("AGENT_MODEL", "antigravity-preview-09-2026")
DEFAULT_TIMEOUT = int(os.getenv("TIMEOUT", "600"))

# ==============================================================================
# 📐 PYDANTIC V2 SCHEMAS & CONTRACTS
# ==============================================================================
ProviderChoice: TypeAlias = Literal["auto", "gemini", "literouter"]
ActiveProvider: TypeAlias = Literal["gemini", "literouter"]


class RefactorManifest(BaseModel):
    """Immutable, strictly validated manifest configuration for batch refactoring."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    prompt: str = Field(min_length=1, description="Refactoring instructions for the agent")
    targets: list[str] = Field(min_length=1, description="Target Python files to refactor")
    project_folder: str = Field(default=".", description="Base directory for targets and references")
    output_dir: str = Field(default="refactor/output", description="Output directory for refactored files")
    output_naming: str = Field(default="{stem}_refactored", description="Output filename template containing {stem}")
    reference_files: list[str] = Field(default_factory=list, description="Optional reference files")

    @field_validator("prompt", mode="after")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Manifest prompt must not be empty or whitespace only")
        return s

    @field_validator("output_naming", mode="after")
    @classmethod
    def validate_naming(cls, v: str) -> str:
        if "{stem}" not in v:
            raise ValueError("output_naming must contain '{stem}' placeholder")
        return v

    @field_validator("targets", mode="after")
    @classmethod
    def validate_targets(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("targets list must not be empty")
        return v


class ProviderConfig(BaseModel):
    """Immutable, strictly validated configuration for an inference provider."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True, frozen=True)

    provider_name: ActiveProvider
    gateway_url: str
    headers: dict[str, str]

    @field_validator("gateway_url", mode="after")
    @classmethod
    def validate_gateway_url(cls, v: str) -> str:
        v_stripped = v.strip()
        if not (v_stripped.startswith("http://") or v_stripped.startswith("https://")):
            raise ValueError(f"gateway_url must be an HTTP/HTTPS URL, got: {v}")
        return v_stripped

    def __iter__(self) -> Iterator[str | dict[str, str]]:
        """Support unpacking: provider_name, gateway_url, headers = config."""
        return iter((self.provider_name, self.gateway_url, self.headers))


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


class InteractionResponse(BaseModel):
    """Response envelope from the LiteRouter / Gemini interaction endpoint."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    id: str | None = None
    object: str | None = None
    created: int | None = None
    model: str | None = None
    status: str | None = None
    steps: list[dict[str, JsonValue]] = Field(default_factory=list)
    output_text: str | dict[str, JsonValue] | None = None
    output: str | dict[str, JsonValue] | None = None
    response: str | dict[str, JsonValue] | None = None
    answer: str | dict[str, JsonValue] | None = None
    result: str | dict[str, JsonValue] | None = None

    def extract_text(self) -> str | None:
        """Extracts raw text content from the interaction response."""
        for v in [self.output_text, self.output, self.response, self.answer, self.result]:
            if isinstance(v, str) and v.strip():
                return v.strip()
            elif isinstance(v, dict):
                text_or_msg = v.get("text") or v.get("message")
                if text_or_msg and str(text_or_msg).strip():
                    return str(text_or_msg).strip()

        for step in self.steps:
            if step.get("type") == "model_output":
                contents = step.get("content", [])
                parts: list[str] = []
                if isinstance(contents, list):
                    for c in contents:
                        if isinstance(c, dict) and c.get("text"):
                            parts.append(str(c["text"]).strip())
                        elif isinstance(c, str) and c.strip():
                            parts.append(c.strip())
                if parts:
                    return "\n\n".join(parts)
            elif step.get("model_output"):
                val = step.get("model_output")
                if isinstance(val, str) and val.strip():
                    return val.strip()

        return None


class RefactorExecutionRequest(BaseModel):
    """Validated input parameters for executing a refactor."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    code_content: str = Field(min_length=1)
    target_filename: str = "target.py"
    prompt: str = ""
    reference_files: list[Path] = Field(default_factory=list)
    provider: ProviderChoice = "auto"
    agent_name: str = AGENT_NAME
    timeout: int = Field(default=DEFAULT_TIMEOUT, gt=0)
    previous_interaction_id: str | None = None


class RefactorExecutionResult(BaseModel):
    """Result data contract for completed refactoring operations."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    status: Literal["completed", "failed"] = "completed"
    provider: ActiveProvider
    refactored_code: str
    elapsed_seconds: float = Field(ge=0.0)
    raw_response: dict[str, JsonValue] = Field(default_factory=dict)

    def __getitem__(self, item: str) -> JsonValue:
        """Allow dict-style indexing for backwards compatibility."""
        if hasattr(self, item):
            val: JsonValue = getattr(self, item)
            return val
        raise KeyError(item)

    def get(self, item: str, default: JsonValue | None = None) -> JsonValue | None:
        return getattr(self, item, default)


class BatchReportItem(BaseModel):
    """Data item representing a single refactor outcome in a batch run."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    file: str
    success: bool
    output: str | None = None


def get_provider_config(provider_override: ProviderChoice = "auto") -> ProviderConfig:
    """
    Resolves the active inference provider, gateway URL, and HTTP auth headers.
    Returns: ProviderConfig instance (supports unpacking into a 3-tuple).
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
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": gemini_key,
        }
        return ProviderConfig(
            provider_name="gemini",
            gateway_url=gateway_url,
            headers=headers,
        )

    elif choice == "literouter":
        if not lr_key:
            raise ValueError(
                "LiteRouter provider selected but LITEROUTER_AUTH_KEY is not set.\n"
                "Please set LITEROUTER_AUTH_KEY in your .env file or environment."
            )
        gateway_url = f"http://{lr_host}:{lr_port}/v1beta/interactions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {lr_key}",
            "x-goog-api-key": lr_key,
        }
        return ProviderConfig(
            provider_name="literouter",
            gateway_url=gateway_url,
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


def extract_output_text(res_json: dict[str, JsonValue]) -> str | None:
    """Extracts raw text content from the interaction response."""
    for k in ["output_text", "output", "response", "answer", "result"]:
        v = res_json.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        elif isinstance(v, dict) and (v.get("text") or v.get("message")):
            return str(v.get("text") or v.get("message")).strip()

    steps = res_json.get("steps", [])
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict):
                if step.get("type") == "model_output":
                    contents = step.get("content", [])
                    parts = []
                    if isinstance(contents, list):
                        for c in contents:
                            if isinstance(c, dict) and c.get("text"):
                                parts.append(str(c["text"]).strip())
                            elif isinstance(c, str) and c.strip():
                                parts.append(c.strip())
                    if parts:
                        return "\n\n".join(parts)

    return None


def clean_code_fences(code: str) -> str:
    """Strips Markdown markdown code fences (```python ... ```) if present."""
    code = code.strip()
    if code.startswith("```python"):
        code = code[9:].strip()
    elif code.startswith("```"):
        code = code[3:].strip()
    if code.endswith("```"):
        code = code[:-3].strip()
    return code


def build_input(prompt: str, target_filename: str, target_code: str, reference_files: list[Path] | None = None) -> str:
    """Assembles prompt with reference context and target file code."""
    parts = [prompt.strip(), ""]
    parts.append("CRITICAL: Output ONLY the raw, refactored code for the TARGET FILE. Do not include markdown code fences or conversational explanation.")
    parts.append("")

    if reference_files:
        for ref in reference_files:
            if ref.exists():
                content = ref.read_text(encoding="utf-8").strip()
                parts.append(f"--- START OF REFERENCE FILE: {ref.name} ---")
                parts.append(content)
                parts.append(f"--- END OF REFERENCE FILE: {ref.name} ---")
                parts.append("")

    parts.append(f"--- START OF TARGET FILE TO REFACTOR: {target_filename} ---")
    parts.append(target_code.strip())
    parts.append(f"--- END OF TARGET FILE TO REFACTOR: {target_filename} ---")

    return "\n".join(parts)


def execute_refactor(
    code_content: str,
    target_filename: str = "target.py",
    prompt: str = "",
    reference_files: list[Path] | None = None,
    provider: ProviderChoice = "auto",
    agent_name: str = AGENT_NAME,
    timeout: int = DEFAULT_TIMEOUT,
    previous_interaction_id: str | None = None,
) -> RefactorExecutionResult:
    """
    Core modular function for executing a code refactor.
    Ready for CLI, automated pipelines, or future MCP server tools.
    """
    if not prompt:
        if DEFAULT_PROMPT_FILE.exists():
            prompt = DEFAULT_PROMPT_FILE.read_text(encoding="utf-8")
        else:
            prompt = "Refactor this code to clean architecture, idiomatic PEP 8, and add complete type hints."

    exec_req = RefactorExecutionRequest(
        code_content=code_content,
        target_filename=target_filename,
        prompt=prompt,
        reference_files=reference_files or [],
        provider=provider,
        agent_name=agent_name,
        timeout=timeout,
        previous_interaction_id=previous_interaction_id,
    )

    provider_config = get_provider_config(exec_req.provider)
    user_input = build_input(exec_req.prompt, exec_req.target_filename, exec_req.code_content, exec_req.reference_files)

    interaction_req = InteractionRequest(
        agent=exec_req.agent_name,
        input=user_input,
        environment="remote",
        previous_interaction_id=exec_req.previous_interaction_id,
    )

    req = urllib.request.Request(
        provider_config.gateway_url,
        data=interaction_req.model_dump_json(exclude_none=True).encode("utf-8"),
        headers=provider_config.headers,
        method="POST",
    )

    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=exec_req.timeout) as resp:
            res_body = resp.read().decode("utf-8")
            res_json = json.loads(res_body)
            elapsed = time.time() - start_time

            parsed_resp = InteractionResponse.model_validate(res_json)
            raw_code = parsed_resp.extract_text()
            if raw_code is None:
                raise RuntimeError(f"Agent did not return output text for {exec_req.target_filename}")

            cleaned_code = clean_code_fences(raw_code)
            return RefactorExecutionResult(
                status="completed",
                provider=provider_config.provider_name,
                refactored_code=cleaned_code,
                elapsed_seconds=round(elapsed, 2),
                raw_response=res_json,
            )

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        elapsed = time.time() - start_time
        raise RuntimeError(f"HTTP Error {e.code} from {provider_config.provider_name} ({elapsed:.2f}s): {err_body[:500]}")
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        elapsed = time.time() - start_time
        raise RuntimeError(f"Execution Error ({elapsed:.2f}s): {e}") from e


def refactor_file(
    file_path: Path,
    output_path: Path | None = None,
    prompt: str = "",
    reference_files: list[Path] | None = None,
    provider: ProviderChoice = "auto",
) -> bool:
    """Refactors a single file on disk."""
    if not file_path.exists():
        print(f"❌ Error: File not found: {file_path}")
        return False

    code = file_path.read_text(encoding="utf-8")
    print(f"🚀 Refactoring {file_path.name}...")

    try:
        result = execute_refactor(
            code_content=code,
            target_filename=file_path.name,
            prompt=prompt,
            reference_files=reference_files,
            provider=provider,
        )

        out_file = output_path or file_path.parent / f"{file_path.stem}_refactored{file_path.suffix}"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(result.refactored_code + "\n", encoding="utf-8")

        print(f"✅ Saved refactored code to: {out_file} ({result.elapsed_seconds}s)")
        return True

    except Exception as e:
        print(f"❌ Failed to refactor {file_path.name}: {e}")
        return False


def load_manifest(manifest_path: str | Path) -> RefactorManifest:
    """Loads and validates a RefactorManifest from disk."""
    path = Path(manifest_path)
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found at {path}")
    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
        return RefactorManifest.model_validate(raw_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in manifest {path}: {e}") from e
    except Exception as e:
        raise ValueError(f"Manifest schema validation failed for {path}: {e}") from e


def load_manifests() -> list[RefactorManifest]:
    """Loads all valid manifests from the manifests directory."""
    manifests: list[RefactorManifest] = []
    for f in sorted(MANIFESTS_DIR.glob("*.json")):
        if f.name == "template.json":
            continue
        try:
            manifests.append(load_manifest(f))
        except Exception as e:
            print(f"⚠️ Error loading manifest {f}: {e}", file=sys.stderr)
    return manifests


def refactor_with_manifest(
    manifest: RefactorManifest | dict[str, JsonValue],
    provider: ProviderChoice = "auto",
    delay: int = 0,
) -> dict[str, bool]:
    """Executes refactoring for all targets in a manifest."""
    if delay > 0:
        time.sleep(delay)

    validated_manifest = (
        manifest if isinstance(manifest, RefactorManifest) else RefactorManifest.model_validate(manifest)
    )

    project_folder = Path(validated_manifest.project_folder)
    if not project_folder.is_absolute():
        project_folder = PROJECT_ROOT / project_folder

    output_dir = Path(validated_manifest.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    reference_files: list[Path] = []
    for rf in validated_manifest.reference_files:
        p = project_folder / rf if not Path(rf).is_absolute() else Path(rf)
        if p.exists():
            reference_files.append(p)
        else:
            print(f"⚠️ Reference file not found: {p}")

    results: dict[str, bool] = {}
    for target_raw in validated_manifest.targets:
        target = project_folder / target_raw if not Path(target_raw).is_absolute() else Path(target_raw)
        if not target.exists():
            print(f"❌ Error: Target file not found at {target}")
            results[str(target)] = False
            continue

        if target.suffix != ".py":
            print(f"⚠️ Skipping non-Python file: {target.name}")
            results[str(target)] = False
            continue

        stem = target.stem
        output_name = validated_manifest.output_naming.replace("{stem}", stem)
        output_file = output_dir / f"{output_name}{target.suffix}"

        success = refactor_file(
            file_path=target,
            output_path=output_file,
            prompt=validated_manifest.prompt,
            reference_files=reference_files,
            provider=provider,
        )
        results[str(target)] = success

    return results


def generate_batch_report(results: list[BatchReportItem | dict[str, JsonValue]]) -> Path:
    """Generates a markdown report summarizing a batch refactoring run."""
    report_dir = SCRIPT_DIR / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    report_file = report_dir / f"batch_report_{timestamp}.md"

    validated_items: list[BatchReportItem] = [
        item if isinstance(item, BatchReportItem) else BatchReportItem.model_validate(item)
        for item in results
    ]

    successful_count = sum(1 for r in validated_items if r.success)
    failed_count = sum(1 for r in validated_items if not r.success)

    lines = [
        "# Batch Refactor Report",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Total files processed:** {len(validated_items)}",
        f"**Successful:** {successful_count}",
        f"**Failed:** {failed_count}",
        "",
    ]

    for r in validated_items:
        status = "✅" if r.success else "❌"
        lines.append(f"{status} `{r.file}`")
        if r.output:
            lines.append(f"   → `{r.output}`")

    report_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n📊 Batch report saved to: {report_file}")
    return report_file


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Refactoring Pipeline (Dual-Engine: Gemini API & LiteRouter)",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Optional: Path to a specific Python file to refactor directly",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Optional: Run a specific manifest JSON file instead of batching all manifests",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="Custom prompt instruction for single-file refactoring",
    )
    parser.add_argument(
        "--prompt-file",
        default=None,
        help="Path to custom prompt file (default: refactor/prompt.txt)",
    )
    parser.add_argument(
        "--provider",
        choices=["auto", "gemini", "literouter"],
        default="auto",
        help="Inference provider: 'auto' (checks GEMINI_API_KEY then LiteRouter), 'gemini', or 'literouter'",
    )
    parser.add_argument(
        "--inplace",
        action="store_true",
        help="Overwrite original file directly instead of creating _refactored.py",
    )
    args = parser.parse_args()

    # Pre-validate credentials
    try:
        provider_name, gateway_url, _ = get_provider_config(args.provider)
    except ValueError as e:
        print(f"\n{e}\n")
        sys.exit(1)

    print("==================================================================")
    print("🛠️  AUTO-REFACTOR PIPELINE (Dual-Engine Execution)")
    print("==================================================================")
    print(f"⚡ Provider:       {provider_name.upper()}")
    print(f"📍 Target Gateway: {gateway_url}")
    print("==================================================================\n")

    # Mode 1: Single file direct CLI refactoring
    if args.target:
        target_path = Path(args.target).resolve()
        prompt_text = args.prompt
        if not prompt_text and args.prompt_file:
            pf = Path(args.prompt_file)
            if pf.exists():
                prompt_text = pf.read_text(encoding="utf-8")
            else:
                print(f"❌ Error: Prompt file not found: {pf}")
                sys.exit(1)

        output_path = target_path if args.inplace else None
        success = refactor_file(
            file_path=target_path,
            output_path=output_path,
            prompt=prompt_text or "",
            provider=args.provider,
        )
        sys.exit(0 if success else 1)

    # Mode 2: Specific manifest file
    if args.manifest:
        manifest = load_manifest(args.manifest)
        results = refactor_with_manifest(manifest, provider=args.provider)
        successes = sum(1 for v in results.values() if v)
        failures = sum(1 for v in results.values() if not v)
        sys.exit(0 if failures == 0 else 1)

    # Mode 3: Batch mode running all manifests in refactor/manifests/
    manifests = load_manifests()
    if not manifests:
        print("ℹ️  No manifests found in refactor/manifests/ and no target file provided.")
        print("💡 Usage:")
        print("   uv run python refactor/refactor.py path/to/script.py")
        print("   uv run python refactor/refactor.py --manifest path/to/manifest.json")
        sys.exit(1)

    print(f"Found {len(manifests)} manifest(s). Running all concurrently with staggered start.\n")
    start_time = time.time()

    all_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(manifests), 20)) as executor:
        futures = {}
        for i, manifest in enumerate(manifests):
            futures[executor.submit(refactor_with_manifest, manifest, args.provider, i * 2)] = manifest
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                all_results.update(result)
            except Exception as e:
                print(f"❌ Fatal error processing manifest: {e}")

    total_elapsed = time.time() - start_time
    results_list = [
        {"file": k, "success": v, "output": str(v)} for k, v in all_results.items()
    ]

    successes = sum(1 for v in all_results.values() if v)
    failures = sum(1 for v in all_results.values() if not v)
    total = len(all_results)

    print(f"\n{'='*40}")
    print(f"Refactor complete: {successes} succeeded, {failures} failed ({total} total)")
    print(f"Total time: {total_elapsed:.2f}s")
    print(f"{'='*40}")

    generate_batch_report(results_list)
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
