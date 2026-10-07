import argparse
import concurrent.futures
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

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


def get_provider_config(provider_override: str = "auto") -> tuple[str, str, dict]:
    """
    Resolves the active inference provider, gateway URL, and HTTP auth headers.
    Returns: (provider_name, gateway_url, headers)
    """
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    lr_key = os.getenv("LITEROUTER_AUTH_KEY", "").strip()
    lr_host = os.getenv("LITEROUTER_HOST", "literouter.lan").strip()
    lr_port = os.getenv("LITEROUTER_PORT", "7766").strip()
    google_base = os.getenv("GOOGLE_NATIVE_BASE_URL", "https://generativelanguage.googleapis.com").strip()

    choice = provider_override.lower()
    if choice == "auto":
        if gemini_key:
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
        return "gemini", gateway_url, headers

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
        return "literouter", gateway_url, headers

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


def extract_output_text(res_json: dict) -> str | None:
    """Extracts raw text content from the interaction response."""
    for k in ["output_text", "output", "response", "answer", "result"]:
        v = res_json.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        elif isinstance(v, dict) and (v.get("text") or v.get("message")):
            return str(v.get("text") or v.get("message")).strip()

    steps = res_json.get("steps", [])
    for step in steps:
        if step.get("type") == "model_output":
            contents = step.get("content", [])
            parts = []
            for c in contents:
                if isinstance(c, dict) and c.get("text"):
                    parts.append(c["text"].strip())
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


def build_input(prompt: str, target_filename: str, target_code: str, reference_files: list[Path] = None) -> str:
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
    reference_files: list[Path] = None,
    provider: str = "auto",
    agent_name: str = AGENT_NAME,
    timeout: int = DEFAULT_TIMEOUT,
    previous_interaction_id: str | None = None,
) -> dict:
    """
    Core modular function for executing a code refactor.
    Ready for CLI, automated pipelines, or future MCP server tools.
    """
    provider_name, gateway_url, headers = get_provider_config(provider)

    if not prompt:
        if DEFAULT_PROMPT_FILE.exists():
            prompt = DEFAULT_PROMPT_FILE.read_text(encoding="utf-8")
        else:
            prompt = "Refactor this code to clean architecture, idiomatic PEP 8, and add complete type hints."

    user_input = build_input(prompt, target_filename, code_content, reference_files)

    payload = {
        "agent": agent_name,
        "input": user_input,
        "environment": "remote",
    }
    if previous_interaction_id:
        payload["previous_interaction_id"] = previous_interaction_id

    req = urllib.request.Request(
        gateway_url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            res_body = resp.read().decode("utf-8")
            res_json = json.loads(res_body)
            elapsed = time.time() - start_time

            raw_code = extract_output_text(res_json)
            if raw_code is None:
                raise RuntimeError(f"Agent did not return output text for {target_filename}")

            cleaned_code = clean_code_fences(raw_code)
            return {
                "status": "completed",
                "provider": provider_name,
                "refactored_code": cleaned_code,
                "elapsed_seconds": round(elapsed, 2),
                "raw_response": res_json,
            }

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        elapsed = time.time() - start_time
        raise RuntimeError(f"HTTP Error {e.code} from {provider_name} ({elapsed:.2f}s): {err_body[:500]}")
    except Exception as e:
        elapsed = time.time() - start_time
        raise RuntimeError(f"Execution Error ({elapsed:.2f}s): {e}")


def refactor_file(
    file_path: Path,
    output_path: Path | None = None,
    prompt: str = "",
    reference_files: list[Path] = None,
    provider: str = "auto",
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
        out_file.write_text(result["refactored_code"] + "\n", encoding="utf-8")

        print(f"✅ Saved refactored code to: {out_file} ({result['elapsed_seconds']}s)")
        return True

    except Exception as e:
        print(f"❌ Failed to refactor {file_path.name}: {e}")
        return False


def load_manifest(manifest_path: str) -> dict:
    path = Path(manifest_path)
    if not path.exists():
        print(f"❌ Error: Manifest not found at {path}")
        sys.exit(1)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in {path}: {e}")
        sys.exit(1)


def load_manifests() -> list[dict]:
    manifests = []
    for f in sorted(MANIFESTS_DIR.glob("*.json")):
        if f.name == "template.json":
            continue
        manifests.append(load_manifest(str(f)))
    return manifests


def refactor_with_manifest(manifest: dict, provider: str = "auto", delay: int = 0) -> dict[str, bool]:
    if delay > 0:
        time.sleep(delay)
    prompt = manifest.get("prompt", "")
    if not prompt:
        print("❌ Error: Manifest has no 'prompt' field.")
        return {}

    project_folder = Path(manifest.get("project_folder", str(PROJECT_ROOT)))
    if not project_folder.is_absolute():
        project_folder = PROJECT_ROOT / project_folder

    targets_raw = manifest.get("targets", [])
    output_dir = Path(manifest.get("output_dir", str(DEFAULT_OUTPUT_DIR)))
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_naming = manifest.get("output_naming", "{stem}_refactored")

    reference_files = []
    for rf in manifest.get("reference_files", []):
        p = project_folder / rf if not Path(rf).is_absolute() else Path(rf)
        if p.exists():
            reference_files.append(p)
        else:
            print(f"⚠️ Reference file not found: {p}")

    results = {}
    for target_raw in targets_raw:
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
        output_name = output_naming.replace("{stem}", stem)
        output_file = output_dir / f"{output_name}{target.suffix}"

        success = refactor_file(
            file_path=target,
            output_path=output_file,
            prompt=prompt,
            reference_files=reference_files,
            provider=provider,
        )
        results[str(target)] = success

    return results


def generate_batch_report(results: list[dict]) -> Path:
    report_dir = SCRIPT_DIR / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    report_file = report_dir / f"batch_report_{timestamp}.md"

    lines = [
        "# Batch Refactor Report",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Total files processed:** {len(results)}",
        f"**Successful:** {sum(1 for r in results if r['success'])}",
        f"**Failed:** {sum(1 for r in results if not r['success'])}",
        "",
    ]

    for r in results:
        status = "✅" if r["success"] else "❌"
        lines.append(f"{status} `{r['file']}`")
        if r.get("output"):
            lines.append(f"   → `{r['output']}`")

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
