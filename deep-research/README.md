# Deep Research Tool (Dual-Engine: Google Gemini & LiteRouter)

This tool executes **Institutional-Grade Deep Research** using Google's Antigravity sandbox (`antigravity-preview-09-2026`) via the `/v1beta/interactions` endpoint.

It automates orchestrating a multi-perspective "Persona Council" (5 specialized domain experts) to research complex topics, fetch live web data via search, and synthesize a comprehensive, cited whitepaper natively compiled into Markdown, HTML, PDF, and DOCX.

---

## ⚡ Inference Modes

1. **Public Community Mode (Default)**: Connects directly to Google Gemini API (`https://generativelanguage.googleapis.com`) using `GEMINI_API_KEY`.
2. **Self-Hosted Mode (LiteRouter)**: Connects to your local or private LiteRouter gateway using `LITEROUTER_AUTH_KEY`.

---

## 📂 Core Components

1. **`prompts/` directory** 
   - Stores target research prompts (`prompts/*.md`).
   - `prompts/_template_guide.md` provides the structural template for writing effective prompts with 5 tailored personas.
2. **`deep-research.py`**
   - The execution script. Reads prompt files, resolves provider credentials, executes the interaction, and extracts compiled sandbox artifacts.
   - Also exports `execute_research(...)` for programmatic Python use or MCP integration.
3. **`reports/` directory** (Generated & gitignored)
   - Outputs the final whitepapers here: `.md`, `.html`, `.pdf`, `.docx`, and `_raw.json`.
4. **`run.sh`**
   - Batch runner shell script for scheduling research across multiple topics.

---

## 🚀 Quick Start

### 1. Configure Credentials
Copy `.env.example` in the repository root to `.env`:
```bash
cp .env.example .env
```
Set your `GEMINI_API_KEY` (or `LITEROUTER_AUTH_KEY`).

### 2. Create a Research Prompt
Copy the template guide to a new file:
```bash
cp deep-research/prompts/_template_guide.md deep-research/prompts/My_Topic.md
```
Edit `My_Topic.md` to define your research objective and customize the 5 personas.

> **💡 Pro-Tip:** Ask your LLM (Claude, ChatGPT, Gemini):
> *"Read `deep-research/prompts/_template_guide.md` and generate 5 adversarial expert personas tailored for researching [YOUR TOPIC]."*

### 3. Run the Research
```bash
uv run python deep-research/deep-research.py My_Topic
```
To force a specific provider:
```bash
uv run python deep-research/deep-research.py My_Topic --provider gemini
# or
uv run python deep-research/deep-research.py My_Topic --provider literouter
```

### 4. Review Results
Check `deep-research/reports/`:
- `My_Topic_TIMESTAMP.md`
- `My_Topic_TIMESTAMP.html`
- `My_Topic_TIMESTAMP.pdf`
- `My_Topic_TIMESTAMP.docx`

---

## 🔌 Programmatic Usage

```python
from deep_research import execute_research

result = execute_research(
    prompt_content="Analyze impacts of quantum cryptography on financial networks...",
    prompt_stem="quantum_finance",
)
print("Saved reports:", result["extracted_files"])
```
