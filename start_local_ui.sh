#!/bin/bash
set -e

echo "💻 Starting local FastAPI UI on port 8001..."
AGENT_ENDPOINT=http://localhost:8080 .venv/bin/uvicorn app:app --port 8001
