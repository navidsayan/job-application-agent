#!/usr/bin/env bash
set -euo pipefail

exec "$HOME/.venvs/aider/bin/aider" \
  --model "${AIDER_MODEL:-ollama/qwen2.5-coder:7b}" \
  --no-check-update \
  "$@"