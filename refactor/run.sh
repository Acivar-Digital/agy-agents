#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="/home/yapilwsl/arthityap/baziforecaster"
PROMPT_DIR="$SCRIPT_DIR/prompts"

export LITEROUTER_PORT=7766
export LITEROUTER_AUTH_KEY=sk-lr-8f2a9e3b1c4d7e5f

TARGET_FILE="$PROJECT_DIR/src2/engine/contradiction_resolver.py"

echo "🚀 Refactoring with all prompts in $PROMPT_DIR"
echo "   Target: $TARGET_FILE"
echo "   Prompt dir: $PROMPT_DIR"
echo "   Mode: parallel"
echo "   Timeout: 300s per prompt"
echo ""

uv run python "$SCRIPT_DIR/refactor.py" "$TARGET_FILE" --prompt-dir "$PROMPT_DIR" --parallel

echo ""
echo "✅ Done. Check the diff:"
echo "   git diff --stat"
echo ""
echo "   Then verify with:"
echo "   uv run ruff check --select C901 src2/engine/"
echo "   uv run pytest"