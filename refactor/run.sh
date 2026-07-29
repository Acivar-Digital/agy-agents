#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="/home/yapilwsl/arthityap/baziforecaster"
MANIFEST_DIR="$SCRIPT_DIR/manifests"

export LITEROUTER_PORT=7766
export LITEROUTER_AUTH_KEY=sk-lr-8f2a9e3b1c4d7e5f

echo "🚀 Auto-refactoring all manifests in $MANIFEST_DIR"
echo "   Project: $PROJECT_DIR"
echo "   Mode: sequential (one JSON manifest = one API call)"
echo "   Timeout: 300s per manifest"
echo ""

uv run python "$SCRIPT_DIR/refactor.py" --manifest-dir "$MANIFEST_DIR"

echo ""
echo "✅ Done. Check the diff:"
echo "   git diff --stat"
echo ""
echo "   Then verify with:"
echo "   uv run ruff check --select C901 src2/engine/"
echo "   uv run pytest"