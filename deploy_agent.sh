#!/bin/bash
set -e

echo "🚀 Preparing Agent Engine deployment package..."
mkdir -p deploy_staging/agents
cp agents/*.py deploy_staging/agents/
cp -r mcp_stubs deploy_staging/
cp -r demo_data deploy_staging/
cp a2ui_setup.py deploy_staging/
cp state.py deploy_staging/
cp requirements.txt deploy_staging/

# Write the agent.py entry point for Agent Engine
cat << 'EOF' > deploy_staging/agent.py
import sys
import os
import certifi

# Fix SSL cert issue for Vertex AI calls in ADK server
os.environ['SSL_CERT_FILE'] = certifi.where()

# Add the current directory to sys.path so the agents module can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.coordinator import coordinator as root_agent
EOF

# Load environment variables
if [ -f .env ]; then
  source .env
else
  echo "Error: .env file not found. Please copy .env.example to .env and fill in the values."
  exit 1
fi

echo "📦 Deploying to Vertex AI Agent Engine in project ${GOOGLE_CLOUD_PROJECT}..."

# Build the base command
CMD=".venv/bin/adk deploy agent_engine \
  --project=${GOOGLE_CLOUD_PROJECT} \
  --region=${GCP_REGION} \
  --display_name=rfp_system"

# Add Agent Engine ID for in-place updates if available and valid
if [ -n "$AGENT_ENGINE_ID" ] && [[ "$AGENT_ENGINE_ID" != *"your-engine-id"* ]]; then
  CMD="$CMD --agent_engine_id=${AGENT_ENGINE_ID}"
fi

# Execute the command
$CMD deploy_staging

echo "✅ Agent Engine Deployment Complete!"
