import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime

LITEROUTER_PORT = os.getenv("LITEROUTER_PORT", "7766")
LITEROUTER_KEY = os.getenv("LITEROUTER_AUTH_KEY", "sk-lr-8f2a9e3b1c4d7e5f")
GATEWAY_URL = f"http://localhost:{LITEROUTER_PORT}/v1beta/interactions"

SCRIPT_DIR = Path(__file__).resolve().parent
MANIFESTS_DIR = SCRIPT_DIR / "manifests"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "output"
AGENT_NAME = "antigravity-preview-05-2026"


def extract_output_text(res_json: dict) -> str | None:
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


def load_manifest_dir(manifest_dir: str) -> list[dict]:
    dir_path = Path(manifest_dir)
    if not dir_path.is_dir():
        print(f"❌ Error: Manifest directory not found at {dir_path}")
        sys.exit(1)
    manifests = []
    for f in sorted(dir_path.glob("*.json")):
        if f.name == "template.json":
            continue
        manifests.append(load_manifest(str(f)))
    if not manifests:
        print(f"❌ Error: No .json manifest files found in {manifest_dir}")
        sys.exit(1)
    return manifests


def build_input(prompt: str, target_file: Path, reference_files: list[Path]) -> str:
    parts = [prompt, ""]
    parts.append("CRITICAL: Output ONLY the raw, refactored code for the TARGET FILE. Do not output the reference files.")
    parts.append("")

    for ref in reference_files:
        if ref.exists():
            content = ref.read_text(encoding="utf-8").strip()
            parts.append(f"--- START OF REFERENCE FILE: {ref.name} ---")
            parts.append(content)
            parts.append(f"--- END OF REFERENCE FILE: {ref.name} ---")
            parts.append("")
        else:
            parts.append(f"⚠️ Reference file not found: {ref}")
            parts.append("")

    target_content = target_file.read_text(encoding="utf-8").strip()
    parts.append(f"--- START OF TARGET FILE TO REFACTOR: {target_file.name} ---")
    parts.append(target_content)
    parts.append(f"--- END OF TARGET FILE TO REFACTOR: {target_file.name} ---")

    return "\n".join(parts)


def refactor_with_manifest(manifest: dict) -> dict[str, bool]:
    prompt = manifest.get("prompt", "")
    if not prompt:
        print("❌ Error: Manifest has no 'prompt' field.")
        return {}

    targets_raw = manifest.get("targets", [])
    output_dir = Path(manifest.get("output_dir", str(DEFAULT_OUTPUT_DIR)))
    output_dir.mkdir(parents=True, exist_ok=True)
    output_naming = manifest.get("output_naming", "{stem}_refactored")

    reference_files = []
    for rf in manifest.get("reference_files", []):
        p = Path(rf)
        if p.exists():
            reference_files.append(p)
        else:
            print(f"⚠️ Reference file not found: {p}")

    results = {}
    for target_raw in targets_raw:
        target = Path(target_raw)
        if not target.exists():
            print(f"❌ Error: Target file not found at {target}")
            results[str(target)] = False
            continue

        if target.suffix != ".py":
            print(f"⚠️ Skipping non-Python file: {target.name}")
            results[str(target)] = False
            continue

        user_input = build_input(prompt, target, reference_files)

        payload = {
            "agent": AGENT_NAME,
            "input": user_input,
            "environment": "remote",
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LITEROUTER_KEY}",
        }
        req = urllib.request.Request(
            GATEWAY_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        print(f"🚀 Refactoring {target.name}...")
        start_time = time.time()

        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                res_body = resp.read().decode("utf-8")
                res_json = json.loads(res_body)

                refactored_code = extract_output_text(res_json)

                if refactored_code is None:
                    print(f"❌ Error: No output text found for {target.name}")
                    results[str(target)] = False
                    continue

                refactored_code = refactored_code.strip()
                if refactored_code.startswith("```python"):
                    refactored_code = refactored_code[9:].strip()
                elif refactored_code.startswith("```"):
                    refactored_code = refactored_code[3:].strip()
                if refactored_code.endswith("```"):
                    refactored_code = refactored_code[:-3].strip()

                stem = target.stem
                output_name = output_naming.replace("{stem}", stem)
                output_file = output_dir / f"{output_name}{target.suffix}"

                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(refactored_code.strip() + "\n")

                elapsed = time.time() - start_time
                print(f"✅ Saved {output_file.name} ({elapsed:.2f}s)")
                results[str(target)] = True

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            elapsed = time.time() - start_time
            print(f"❌ HTTP Error {e.code}: {err_body[:500]} ({elapsed:.2f}s)")
            results[str(target)] = False
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"❌ Execution Error: {e} ({elapsed:.2f}s)")
            results[str(target)] = False

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
        description="Manifest-driven auto-refactor using antigravity sandbox agent."
    )
    parser.add_argument(
        "--manifest",
        metavar="FILE",
        help="Path to a single JSON manifest file",
    )
    parser.add_argument(
        "--manifest-dir",
        metavar="DIR",
        help="Directory of JSON manifest files (auto-discovered)",
    )
    parser.add_argument(
        "--transform",
        action="store_true",
        help="Transform an existing raw JSON response without calling the API",
    )
    args = parser.parse_args()

    if not args.manifest and not args.manifest_dir:
        parser.print_help()
        print("\n❌ Error: Provide --manifest FILE or --manifest-dir DIR")
        sys.exit(1)

    if args.transform:
        raw_json_file = Path(args.manifest or args.manifest_dir)
        if not raw_json_file.exists():
            print(f"❌ Error: File not found at {raw_json_file}")
            sys.exit(1)
        res_json = json.loads(raw_json_file.read_text(encoding="utf-8"))
        code = extract_output_text(res_json)
        if code:
            print(code)
        else:
            print("No content found in response JSON.")
        sys.exit(0)

    all_results = {}

    if args.manifest:
        manifest = load_manifest(args.manifest)
        all_results.update(refactor_with_manifest(manifest))

    if args.manifest_dir:
        manifests = load_manifest_dir(args.manifest_dir)
        for manifest in manifests:
            all_results.update(refactor_with_manifest(manifest))

    results_list = [
        {"file": k, "success": v, "output": str(v)} for k, v in all_results.items()
    ]

    successes = sum(1 for v in all_results.values() if v)
    failures = sum(1 for v in all_results.values() if not v)
    total = len(all_results)

    print(f"\n{'='*40}")
    print(f"Refactor complete: {successes} succeeded, {failures} failed ({total} total)")
    print(f"{'='*40}")

    generate_batch_report(results_list)

    if failures == 0:
        sys.exit(0)
    elif successes == 0:
        sys.exit(1)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()