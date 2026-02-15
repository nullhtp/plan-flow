#!/usr/bin/env bash
# Pre-commit hook wrapper for biome.
# Converts repo-root-relative paths to frontend-relative paths and runs biome from the frontend directory.
set -euo pipefail

FRONTEND_DIR="$(cd "$(dirname "$0")/../frontend" && pwd)"
RELATIVE_FILES=()

for file in "$@"; do
  # Strip the "frontend/" prefix to get paths relative to the frontend directory
  RELATIVE_FILES+=("${file#frontend/}")
done

cd "$FRONTEND_DIR"
exec ./node_modules/.bin/biome check --write "${RELATIVE_FILES[@]}"
