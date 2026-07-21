#!/bin/zsh
set -euo pipefail

PROJECT_DIR="${0:A:h}"
cd "$PROJECT_DIR"

SPEECH_TO_SPEECH_URL="${SPEECH_TO_SPEECH_URL:-ws://localhost:8765/v1/realtime}" \
  .venv/bin/uvicorn --app-dir demo server:app --host 127.0.0.1 --port 7860
