#!/bin/bash
set -e

# Load environment variables
if [ -f .env ]; then
  set -a && source .env && set +a
fi

unset GOOGLE_APPLICATION_CREDENTIALS

# Detect venv binary path (Windows uses Scripts/, Mac/Linux uses bin/)
if [ -d ".venv/Scripts" ]; then
  VENV_BIN=".venv/Scripts"
else
  VENV_BIN=".venv/bin"
fi

echo "Starting local FastAPI UI on port 8001..."
AGENT_ENDPOINT=http://127.0.0.1:8080 $VENV_BIN/uvicorn app:app --port 8001
