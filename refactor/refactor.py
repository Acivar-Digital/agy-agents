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
DEFAULT_PROMPT_FILE = SCRIPT_DIR / "prompt.txt"

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


def load_prompt(prompt_path: str | None) -> str:
    if prompt_path:
        path = Path(prompt_path)
        if not path.exists():
            print(f"❌ Error: Prompt file not found at {path}")
            sys.exit(1)
        return path.read_text(encoding="utf-8").strip()

    if DEFAULT_PROMPT_FILE.exists():
        return DEFAULT_PROMPT_FILE.read_text(encoding="utf-8").strip()

    print("❌ Error: No prompt file found. Create prompt.txt in the refactor/ directory.")
    sys.exit(1)


def refactor_file(input_file_path: str, prompt: str) -> str | None:
    target_file = Path(input_file_path)
    if not target_file.exists():
        print(f"❌ Error: File {target_file} not found.")
        return None

    if not target_file.suffix == ".py":
        print(f"⚠️  Skipping non-Python file: {target_file.name}")
        return None

    with open(target_file, "r", encoding="utf-8") as f:
        original_code = f.read()

    user_prompt = (
        f"{prompt}\n\n"
        f"Please refactor this file. The filename is `{target_file.name}`.\n\n"
        f"{original_code}"
    )

    payload = {
        "agent": AGENT_NAME,
        "input": user_prompt,
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

    print(f"🚀 Refactoring {target_file.name}...")
    start_time = time.time()

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            res_body = resp.read().decode("utf-8")
            res_json = json.loads(res_body)

            refactored_code = extract_output_text(res_json)

            if refactored_code is None:
                print("❌ Error: No output text found in API response.")
                return None

            refactored_code = refactored_code.strip()

            if refactored_code.startswith("```python"):
                refactored_code = refactored_code[9:].strip()
            elif refactored_code.startswith("```"):
                refactored_code = refactored_code[3:].strip()

            if refactored_code.endswith("```"):
                refactored_code = refactored_code[:-3].strip()

            output_file = target_file.with_name(
                f"{target_file.stem}_refactored{target_file.suffix}"
            )
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(refactored_code.strip() + "\n")

            elapsed = time.time() - start_time
            print(f"✅ Saved refactored version to: {output_file} ({elapsed:.2f}s)")
            return str(output_file)

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        elapsed = time.time() - start_time
        print(f"❌ HTTP Error {e.code}: {err_body[:500]} ({elapsed:.2f}s)")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Execution Error: {e} ({elapsed:.2f}s)")

    return None


def find_python_files(directory: str) -> list[Path]:
    target_dir = Path(directory)
    if target_dir.is_file() and target_dir.suffix == ".py":
        return [target_dir]
    if target_dir.is_dir():
        all_py_files = sorted(target_dir.rglob("*.py"))
        return [f for f in all_py_files if not f.name.endswith("_refactored.py")]
    print(f"❌ Error: {directory} is not a Python file or directory.")
    return []


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
        description="Auto-refactor Python files using antigravity sandbox agent."
    )
    parser.add_argument(
        "target",
        help="Path to a Python file or directory of Python files to refactor",
    )
    parser.add_argument(
        "--prompt",
        metavar="FILE",
        help="Path to a custom prompt file (default: refactor/prompt.txt)",
    )
    parser.add_argument(
        "--transform",
        action="store_true",
        help="Transform an existing raw JSON response without calling the API",
    )
    args = parser.parse_args()

    if args.transform:
        raw_json_file = Path(args.target)
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

    target = args.target
    files = find_python_files(target)

    if not files:
        print(f"⚠️  No Python files found in {target}")
        sys.exit(1)

    print(f"Found {len(files)} Python file(s) to refactor.\n")

    system_prompt = load_prompt(args.prompt)

    results = []
    for f in files:
        out = refactor_file(str(f), system_prompt)
        results.append({"file": str(f), "success": out is not None, "output": out})

    generate_batch_report(results)

    successes = sum(1 for r in results if r["success"])
    failures = sum(1 for r in results if not r["success"])

    if failures == 0:
        print(f"\n✅ All {len(results)} file(s) refactored successfully.")
        sys.exit(0)
    elif successes == 0:
        print(f"\n❌ All {len(results)} file(s) failed.")
        sys.exit(1)
    else:
        print(f"\n⚠️  {successes} succeeded, {failures} failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()