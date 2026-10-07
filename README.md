# antigravity-agents (agy-agents)

Autonomous, institutional-grade Deep Research and Code Refactoring agents powered by Google's Antigravity sandbox (`antigravity-preview-09-2026`) via the `/v1beta/interactions` endpoint.

Built for the open-source community: plug in your standard **Google Gemini API Key** and run immediately, or route through a self-hosted **LiteRouter** inference gateway.

---

## ⚡ Highlights

- **🔬 Deep Research (Council Protocol)**: Multi-persona research council synthesizing live web data into fully cited whitepapers, with automatic sandbox compilation into Markdown, HTML, PDF, and DOCX formats.
- **🛠️ Autonomous Code Refactoring**: Dual-mode pipeline (CLI file argument or JSON manifests) that analyzes codebases, enforces clean architecture and PEP 8, and generates verified refactored code.
- **🌐 Dual-Engine Execution**:
  - **Public Community Mode (Default)**: Direct connection to Google Gemini API (`https://generativelanguage.googleapis.com`) using `GEMINI_API_KEY`.
  - **Self-Hosted Mode**: Route through your private LiteRouter inference gateway using `LITEROUTER_AUTH_KEY`.
- **🔌 MCP & Automation Ready**: Core execution functions (`execute_research`, `execute_refactor`) are cleanly exported for seamless integration into Model Context Protocol (MCP) servers or Python pipelines.

---

## 🚀 Quick Start (Community / Gemini API)

### 1. Prerequisites
- Python 3.10+
- Recommended: [uv](https://docs.astral.sh/uv/) (fast Python package runner) or standard `pip`
- A Google Gemini API Key ([get one from Google AI Studio](https://aistudio.google.com/))

### 2. Setup
Clone the repository and set your API key:

```bash
git clone https://github.com/your-username/agy-agents.git
cd agy-agents

# Copy environment template
cp .env.example .env
```

Open `.env` and set your key:
```ini
GEMINI_API_KEY=AIzaSy...your_gemini_api_key_here
```

Install dependencies (if using pip):
```bash
pip install -r requirements.txt
# Or simply use `uv run` which handles dependencies automatically!
```

---

## 🔬 1. Running Deep Research

The Deep Research agent executes a structured 5-persona research council across live web sources, synthesizes the findings, and renders native reports in Markdown, HTML, PDF, and Word document formats inside its execution sandbox.

```bash
# 1. Create a prompt for your research topic
cp deep-research/prompts/_template_guide.md deep-research/prompts/My_Topic.md

# 2. Edit My_Topic.md to define your research question and 5 personas

# 3. Execute research
uv run python deep-research/deep-research.py My_Topic
```

Reports are automatically generated and extracted into `deep-research/reports/`:
- `My_Topic_TIMESTAMP.md`
- `My_Topic_TIMESTAMP.html`
- `My_Topic_TIMESTAMP.pdf`
- `My_Topic_TIMESTAMP.docx`
- `My_Topic_TIMESTAMP_raw.json`

---

## 🛠️ 2. Running Autonomous Refactoring

The refactoring agent inspects code, applies strict typing, architectural decoupling, and PEP 8 best practices.

### Mode A: Refactor a Single File Directly
```bash
# Refactors the file and outputs path/to/script_refactored.py
uv run python refactor/refactor.py path/to/script.py

# Optional: supply custom prompt instructions on the fly
uv run python refactor/refactor.py path/to/script.py --prompt "Convert this script to use async/await and Pydantic v2"

# Optional: overwrite the file in-place
uv run python refactor/refactor.py path/to/script.py --inplace
```

### Mode B: Batch Processing via Manifests
For large codebases, define targeted refactoring jobs in `refactor/manifests/*.json`:
```bash
# Runs all manifests concurrently with staggered execution
uv run python refactor/refactor.py

# Or run a single specific manifest
uv run python refactor/refactor.py --manifest refactor/manifests/my_batch.json
```

---

## 💡 Pro-Tip: Use Your LLM to Customize Everything

This repository is designed to be a flexible foundation. **You should ask your favorite LLM (Claude, ChatGPT, Gemini, or OpenCode) to tailor it to your exact needs!**

Here are recommended prompts you can copy-paste into your LLM:

### Customizing Research Personas
> *"I want to conduct deep research on [YOUR DOMAIN, e.g. Quantum Computing / DeFi Protocols / Biotech]. Read `deep-research/prompts/_template_guide.md` and generate 5 specialized, adversarial personas representing top industry experts, along with a detailed prompt tailored for this domain."*

### Customizing the Refactoring Rules
> *"Read `refactor/prompt.txt`. Refactor this system prompt to enforce our engineering team's style guide: [list your rules, e.g., enforce FastAPI patterns, strict Pydantic v2 schemas, zero Any types, and Google docstrings]."*

### Customizing Batch Manifests
> *"Look at `refactor/manifests/template.json`. Generate a manifest targeting my repository in `/src` to refactor all database queries into repository pattern classes."*

---

## 🏠 Advanced: Self-Hosted / LiteRouter Gateway Mode

If you run your own local or private inference gateway ([LiteRouter](https://github.com/gastownhall/literouter)), you can route all requests through your LAN gateway without changing code:

In `.env`:
```ini
LITEROUTER_HOST=literouter.lan
LITEROUTER_PORT=7766
LITEROUTER_AUTH_KEY=your_literouter_key_here
```

The scripts automatically detect `LITEROUTER_AUTH_KEY`. You can also explicitly specify the provider via CLI:
```bash
uv run python deep-research/deep-research.py My_Topic --provider literouter
uv run python refactor/refactor.py path/to/script.py --provider literouter
```

---

## 🔌 Python API & MCP Server Readiness

Both tools export clean, modular functions ready to be embedded into custom pipelines or served via a Model Context Protocol (MCP) server:

```python
from deep_research import execute_research
from refactor import execute_refactor

# Run research programmatically
result = execute_research(
    prompt_content="Analyze macroeconomic impact of rate cuts...",
    prompt_stem="macro_analysis",
)
print(f"Report files: {result['extracted_files']}")

# Refactor code programmatically
refactored = execute_refactor(
    code_content="def add(a, b): return a + b",
    prompt="Add complete type hints and docstrings.",
)
print(refactored["refactored_code"])
```

---

## 📂 Project Structure

```
agy-agents/
├── .env.example             ← Unified environment variables template
├── pyproject.toml           ← Standard project packaging
├── requirements.txt         ← Dependencies (python-dotenv, httpx, h2)
├── deep-research/
│   ├── deep-research.py     ← Dual-engine research runner & execute_research() export
│   ├── run.sh               ← Batch runner script
│   ├── prompts/
│   │   ├── _template_guide.md ← Structural template for 5-persona prompts
│   │   └── *.md             ← Topic prompts
│   └── reports/             ← Generated reports (gitignored)
├── refactor/
│   ├── refactor.py          ← Dual-engine hybrid refactorer & execute_refactor() export
│   ├── prompt.txt           ← Default refactoring instructions
│   ├── manifests/           ← Batch refactoring jobs
│   └── reports/             ← Batch execution reports (gitignored)
├── .opencode/skills/        ← Skill definitions for OpenCode / assistant agents
└── README.md
```

---

## 📄 License

MIT License. Free to use, adapt, and share with the open-source community.
