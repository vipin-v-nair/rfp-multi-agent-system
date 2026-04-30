#!/bin/bash
set -e

# Unset service account key so ADC is used
unset GOOGLE_APPLICATION_CREDENTIALS

# Fix Windows encoding issue — ADK deploy output contains emoji that cp1252 can't encode
export PYTHONIOENCODING=utf-8

echo "Preparing Agent Engine deployment package..."
mkdir -p deploy_staging/agents
cp agents/*.py deploy_staging/agents/
cp -r mcp_servers deploy_staging/
cp -r demo_data deploy_staging/
cp a2ui_setup.py deploy_staging/
cp mcp_client.py deploy_staging/
cp threaded_mcp_toolset.py deploy_staging/
cp agent_registry_lookup.py deploy_staging/
cp retry_llm.py deploy_staging/
cp state.py deploy_staging/
cp requirements.txt deploy_staging/
# Copy .env so Agent Engine picks up MCP URLs and other runtime config
cp .env deploy_staging/.env

# Write the agent.py entry point for Agent Engine
cat << 'EOF' > deploy_staging/agent.py
import sys
import os

# Agent Gateway proxies all outbound HTTPS from Agent Engine and presents its own
# CA cert. The system store has the Gateway CA installed at container startup.
# certifi's bundle does NOT include it — using certifi breaks all HTTPS calls
# (Agent Registry, MCP servers) routed through the proxy.
_SYSTEM_CERTS = '/etc/ssl/certs/ca-certificates.crt'
if os.path.exists(_SYSTEM_CERTS):
    os.environ['SSL_CERT_FILE'] = _SYSTEM_CERTS
    os.environ['REQUESTS_CA_BUNDLE'] = _SYSTEM_CERTS
else:
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.coordinator import coordinator as root_agent
EOF

# Load environment variables
if [ -f .env ]; then
  set -a && source .env && set +a
else
  echo "Error: .env file not found. Please copy .env.example to .env and fill in the values."
  exit 1
fi

echo "Deploying to Vertex AI Agent Engine in project ${GOOGLE_CLOUD_PROJECT}..."

# Detect venv binary path (Windows uses Scripts/, Mac/Linux uses bin/)
if [ -d ".venv/Scripts" ]; then
  VENV_BIN=".venv/Scripts"
else
  VENV_BIN=".venv/bin"
fi

# Build the base command
CMD="$VENV_BIN/adk deploy agent_engine \
  --project=${GOOGLE_CLOUD_PROJECT} \
  --region=${GCP_REGION} \
  --display_name=rfp_system \
  --otel_to_cloud \
  --trace_to_cloud"

# Add Agent Engine ID for in-place updates if available and valid
if [ -n "$AGENT_ENGINE_ID" ] && [[ "$AGENT_ENGINE_ID" != *"your-engine-id"* ]]; then
  CMD="$CMD --agent_engine_id=${AGENT_ENGINE_ID}"
fi

# Execute the command and capture output to extract the engine resource name
DEPLOY_OUTPUT=$($CMD deploy_staging 2>&1)
echo "$DEPLOY_OUTPUT"

# Extract the full engine resource name from the deploy output
NEW_ENGINE_ID=$(echo "$DEPLOY_OUTPUT" | grep -oE 'projects/[0-9]+/locations/[^/ ]+/reasoningEngines/[0-9]+' | head -1)

echo "Agent Engine Deployment Complete!"

if [ -n "$NEW_ENGINE_ID" ]; then
  echo "New engine resource: ${NEW_ENGINE_ID}"
  echo ""
  echo "ACTION REQUIRED: Update AGENT_ENGINE_ID in .env with the new engine ID for future in-place updates:"
  echo "  AGENT_ENGINE_ID=${NEW_ENGINE_ID}"
fi

# Bind to Agent Gateway if AGENT_GATEWAY_NAME is set
if [ -n "$AGENT_GATEWAY_NAME" ]; then
  if [ -n "$NEW_ENGINE_ID" ]; then
    $VENV_BIN/python bind_gateway.py "$NEW_ENGINE_ID"
  else
    $VENV_BIN/python bind_gateway.py
  fi
else
  echo "AGENT_GATEWAY_NAME not set in .env — skipping Agent Gateway binding."
fi
