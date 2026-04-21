#!/bin/bash
set -e

# Load environment variables
if [ -f .env ]; then
  source .env
fi

echo "🤖 Starting local ADK Agent Server on port 8080..."
.venv/bin/adk api_server \
  --port 8080 \
  --auto_create_session \
  --disable_features=PROGRESSIVE_SSE_STREAMING \
  apps/
