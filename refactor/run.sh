#!/bin/bash
set -e

export LITEROUTER_PORT=7766
export LITEROUTER_AUTH_KEY=sk-lr-8f2a9e3b1c4d7e5f

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 Running all manifests from refactor/manifests/"
echo "   Mode: concurrent"
echo "   Timeout: 300s per manifest"
echo ""

uv run python "$SCRIPT_DIR/refactor.py"

echo ""
echo "✅ Done. Check the diff:"
echo "   git diff --stat"
echo ""
echo "   Then verify with:"
echo "   uv run ruff check --select C901 src2/engine/"
echo "   uv run pytest"