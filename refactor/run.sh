#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

source "$SCRIPT_DIR/.env" 2>/dev/null || true

echo "🚀 Running all manifests from refactor/manifests/"
echo "   Mode: concurrent"
echo "   Timeout: ${TIMEOUT:-600}s per manifest"
echo ""

uv run python "$SCRIPT_DIR/refactor.py"

echo ""
echo "✅ Done. Check the diff:"
echo "   git diff --stat"
echo ""
echo "   Then verify with:"
echo "   uv run ruff check --select C901 src2/engine/"
echo "   uv run pytest"