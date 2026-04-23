#!/bin/bash
set -e

# Load environment variables
if [ -f .env ]; then
  set -a && source .env && set +a
fi

# Unset service account key override so ADC is used
unset GOOGLE_APPLICATION_CREDENTIALS

# Detect venv binary path (Windows uses Scripts/, Mac/Linux uses bin/)
if [ -d ".venv/Scripts" ]; then
  VENV_BIN=".venv/Scripts"
else
  VENV_BIN=".venv/bin"
fi

echo "Starting local ADK Agent Server on port 8080..."
$VENV_BIN/adk api_server \
  --port 8080 \
  --auto_create_session \
  --disable_features=PROGRESSIVE_SSE_STREAMING \
  apps/
