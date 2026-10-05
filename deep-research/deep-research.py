import argparse
import json
import os
import sys
import time
import httpx
import tarfile
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ==============================================================================
# 🔑 API KEY & ROUTING CONFIGURATION
# Loaded dynamically via uv --env-file
# ==============================================================================
# Resolve repository root and load .env BEFORE reading config so .env is authoritative.
RESEARCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = RESEARCH_DIR.parent
load_dotenv(dotenv_path=REPO_ROOT / ".env")

# Gateway requires a Google directive (lr-gg-*), NOT the sk-lr-* master key.
LITEROUTER_KEY = os.getenv("LITEROUTER_AUTH_KEY", "REDACTED")
LITEROUTER_PORT = os.getenv("LITEROUTER_PORT", "7766")

# Google Gemini native API key for direct interactions endpoint.
# When set, the agent POSTs to the Gemini API directly (more reliable than the
# local LiteRouter gateway, which drops sandbox environments before downloads).
# Leave blank to fall back to the local LiteRouter gateway.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

GOOGLE_NATIVE_BASE_URL = os.getenv("GOOGLE_NATIVE_BASE_URL", "https://generativelanguage.googleapis.com")

# Core interaction endpoint. Prefer the direct Gemini API when GEMINI_API_KEY is set;
# otherwise use the local LiteRouter gateway (HTTPS only, HTTP/2 on 7766).
if GEMINI_API_KEY:
    GATEWAY_URL = f"{GOOGLE_NATIVE_BASE_URL}/v1beta/interactions"
else:
    GATEWAY_URL = f"https://localhost:{LITEROUTER_PORT}/v1beta/interactions"

# The CORRECT File API endpoint for downloading the full environment snapshot (.tar).
# When GEMINI_API_KEY is set, use the direct Gemini API (same host as GATEWAY_URL).
if GEMINI_API_KEY:
    FILE_DOWNLOAD_URL = f"{GOOGLE_NATIVE_BASE_URL}/v1beta/files/environment-{{env_id}}:download?alt=media"
else:
    FILE_DOWNLOAD_URL = f"https://localhost:{LITEROUTER_PORT}/v1beta/files/environment-{{env_id}}:download?alt=media"

# Per-request auth headers for the direct Gemini API.
GEMINI_HEADERS = {
    "Content-Type": "application/json",
    "x-goog-api-key": GEMINI_API_KEY,
}

# Shared HTTP/2 client for the local LiteRouter gateway. The gateway is HTTPS-only
# with a self-signed localhost cert, so verification is disabled and HTTP/2 is used
# when the `h2` package is available. If `h2` is missing we fall back to HTTP/1.1
# rather than crashing, and warn loudly so the operator knows HTTP/2 is not active.
try:
    _HTTP_CLIENT = httpx.Client(http2=True, verify=False, timeout=httpx.Timeout(600.0))
except ImportError:
    import sys

    print(
        "⚠️  The 'h2' package is not installed — falling back to HTTP/1.1. "
        "Install it (e.g. `pip install h2` or `uv pip install h2`) to enable HTTP/2.",
        file=sys.stderr,
    )
    _HTTP_CLIENT = httpx.Client(http2=False, verify=False, timeout=httpx.Timeout(600.0))
# ==============================================================================

PROMPTS_DIR = RESEARCH_DIR / "prompts"
REPORTS_DIR = RESEARCH_DIR / "reports"

# Ensure directories exist
PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Instruct the agent to natively build the files and save them to its disk
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

def download_and_extract_sandbox(env_id: str, base_output_path: Path):
    """Downloads the full sandbox snapshot (.tar) and extracts the target files."""
    url = FILE_DOWNLOAD_URL.format(env_id=env_id)

    # Passing both standard Auth and Google's expected header just to be safe with LiteRouter
    headers = {
        "Authorization": f"Bearer {LITEROUTER_KEY}",
        "x-goog-api-key": LITEROUTER_KEY,
    }

    try:
        with _HTTP_CLIENT.stream("GET", url, headers=headers) as resp:
            if resp.status_code != 200:
                err_body = resp.read().decode("utf-8", errors="ignore")
                print(f"❌ Failed to download sandbox snapshot (HTTP {resp.status_code}): {err_body}")
                return

            # 1. Download the raw tar payload into a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".tar") as tmp_tar:
                for chunk in resp.iter_bytes():
                    tmp_tar.write(chunk)
                tmp_tar_path = tmp_tar.name

        # 2. Extract the sandbox tar
        extract_dir = Path(tempfile.mkdtemp())
        with tarfile.open(tmp_tar_path) as tar:
            tar.extractall(path=extract_dir)

        # 3. Locate the 4 specific generated files and move them to your reports folder
        formats = ["md", "html", "pdf", "docx"]
        for fmt in formats:
            target_name = f"report.{fmt}"
            found = False

            # Recursively search the extracted sandbox (in case the agent put them in a subfolder)
            for root_dir, _, files in os.walk(extract_dir):
                if target_name in files:
                    src_file = Path(root_dir) / target_name
                    final_path = base_output_path.with_suffix(f".{fmt}")
                    shutil.move(str(src_file), str(final_path))
                    print(f"✅ Extracted native file: {final_path.name}")
                    found = True
                    break

            if not found:
                print(f"⚠️ Agent failed to generate {target_name} inside the sandbox.")

        # 4. Clean up temp files
        os.remove(tmp_tar_path)
        shutil.rmtree(extract_dir)

    except httpx.HTTPError as e:
        print(f"❌ Failed to download sandbox snapshot: {e}")
    except Exception as e:
        print(f"❌ System error during extraction: {e}")

def run_deep_research():
    parser = argparse.ArgumentParser(description="Deep Research Agent Tool (Native Sandbox Downloads)")
    parser.add_argument("target", help="The name of the prompt (e.g. Direction_of_JPY)")
    args = parser.parse_args()

    prompt_stem = Path(args.target).stem
    prompt_file = PROMPTS_DIR / f"{prompt_stem}.md"

    if not prompt_file.exists():
        print(f"❌ Error: Prompt template not found at {prompt_file}")
        sys.exit(1)

    # Setup output paths
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    base_output_path = REPORTS_DIR / f"{prompt_stem}_{timestamp}"
    output_json = REPORTS_DIR / f"{prompt_stem}_{timestamp}_raw.json"

    original_prompt_content = prompt_file.read_text(encoding="utf-8").strip()

    # Inject our command forcing the agent to build the files on its disk
    final_prompt = original_prompt_content + AGENT_FILE_INSTRUCTION

    print("==================================================================")
    print("🔬 DEEP RESEARCH AGENT (Native Sandbox File Download Mode)")
    print("==================================================================")
    print(f"📍 Target Gateway: {GATEWAY_URL}")
    print(f"📄 Reading Prompt: {prompt_file}")
    print(f"📁 Output Dir:     {REPORTS_DIR}")
    print("==================================================================\n")

    payload = {
        "agent": "antigravity-preview-05-2026",
        "input": final_prompt,
        "environment": "remote",
    }

    print("🚀 Dispatching request. Agent is doing research and rendering files natively...")
    start_time = time.time()

    def _process_response(resp, elapsed):
        if resp.status_code >= 400:
            print(f"❌ HTTP Error {resp.status_code}: {resp.text[:500]}")
            sys.exit(1)
        print(f"✅ Execution finished in {elapsed:.1f} seconds!")
        res_json = resp.json()
        # --- 1. SAVE RAW JSON FORMAT ---
        output_json.write_text(json.dumps(res_json, indent=2), encoding="utf-8")
        print(f"💾 Saved JSON API format to: {output_json}")
        # --- 2. EXTRACT ENVIRONMENT ID ---
        env_id = res_json.get("environment_id")
        if not env_id:
            print("❌ Error: No environment_id returned by the agent. Cannot download files.")
            sys.exit(1)
        # --- 3. DOWNLOAD & EXTRACT FILES DIRECTLY FROM THE AGENT'S SANDBOX ---
        print(f"\n📦 Accessing sandbox {env_id} to download generated files...")
        download_and_extract_sandbox(env_id, base_output_path)
        print("\n🎉 Deep Research Complete!")
        sys.exit(0)

    try:
        if GEMINI_API_KEY:
            # Direct Gemini API — more reliable; environment lives longer for downloads.
            resp = _HTTP_CLIENT.post(GATEWAY_URL, headers=GEMINI_HEADERS, json=payload, timeout=600.0)
            elapsed = time.time() - start_time
            _process_response(resp, elapsed)
        else:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LITEROUTER_KEY}",
                "x-goog-api-key": LITEROUTER_KEY,
            }
            resp = _HTTP_CLIENT.post(GATEWAY_URL, headers=headers, json=payload, timeout=600.0)
            elapsed = time.time() - start_time
            if resp.status_code >= 400:
                print(f"❌ HTTP Error {resp.status_code}: {resp.text[:500]}")
                sys.exit(1)

            print(f"✅ Execution finished in {elapsed:.1f} seconds!")

            res_json = resp.json()

            # --- 1. SAVE RAW JSON FORMAT ---
            output_json.write_text(json.dumps(res_json, indent=2), encoding="utf-8")
            print(f"💾 Saved JSON API format to: {output_json}")

            # --- 2. EXTRACT ENVIRONMENT ID ---
            env_id = res_json.get("environment_id")
            if not env_id:
                print("❌ Error: No environment_id returned by the agent. Cannot download files.")
                sys.exit(1)

            # --- 3. DOWNLOAD & EXTRACT FILES DIRECTLY FROM THE AGENT'S SANDBOX ---
            print(f"\n📦 Accessing sandbox {env_id} to download generated files...")
            download_and_extract_sandbox(env_id, base_output_path)

            print("\n🎉 Deep Research Complete!")
            sys.exit(0)

    except httpx.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Execution Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_deep_research()
