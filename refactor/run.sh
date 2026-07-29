#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="/home/yapilwsl/arthityap/baziforecaster"
TARGET_FILE="$PROJECT_DIR/src2/engine/contradiction_resolver.py"
PROMPT_FILE="$SCRIPT_DIR/prompt_cc_reduce.txt"

export LITEROUTER_PORT=7766
export LITEROUTER_AUTH_KEY=sk-lr-8f2a9e3b1c4d7e5f

echo "🚀 Refactoring contradiction_resolver.py with CC reduction prompt..."
echo "   Target: $TARGET_FILE"
echo "   Prompt: $PROMPT_FILE"
echo "   Timeout: 300s"
echo ""

uv run python "$SCRIPT_DIR/refactor.py" "$TARGET_FILE" --prompt "$PROMPT_FILE"

echo ""
echo "✅ Done. Check the diff:"
echo "   git diff --stat"
echo ""
echo "   Then verify with:"
echo "   uv run ruff check --select C901 src2/engine/contradiction_resolver.py"
echo "   uv run pytest"