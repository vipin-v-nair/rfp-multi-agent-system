#!/bin/bash
set -e

# Load environment variables
if [ -f .env ]; then
  set -a && source .env && set +a
else
  echo "Error: .env file not found."
  exit 1
fi

unset GOOGLE_APPLICATION_CREDENTIALS

echo "Preparing MCP server deployment package..."
rm -rf mcp_deploy
mkdir -p mcp_deploy
cp requirements-mcp.txt mcp_deploy/
cp mcp_main.py mcp_deploy/
cp Dockerfile.mcp mcp_deploy/Dockerfile
cp -r mcp_servers mcp_deploy/
cp -r demo_data mcp_deploy/

# Helper: deploy one Cloud Run service (Windows uses PowerShell due to old gcloud SDK)
deploy_service() {
  local service=$1
  local mcp_server=$2

  echo ""
  echo "Deploying ${service} (MCP_SERVER=${mcp_server})..."

  if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    powershell -Command "& { gcloud beta run deploy ${service} \
      --source mcp_deploy \
      --platform=managed \
      --project=${GOOGLE_CLOUD_PROJECT} \
      --region=${GCP_REGION} \
      --allow-unauthenticated \
      --set-env-vars='MCP_SERVER=${mcp_server}' 2>&1 }"
  else
    gcloud beta run deploy "${service}" \
      --source mcp_deploy \
      --platform=managed \
      --project="${GOOGLE_CLOUD_PROJECT}" \
      --region="${GCP_REGION}" \
      --allow-unauthenticated \
      --set-env-vars="MCP_SERVER=${mcp_server}"
  fi
}

# Helper: get Cloud Run service URL (never fails the script)
get_url() {
  local service=$1
  gcloud run services describe "${service}" \
    --project="${GOOGLE_CLOUD_PROJECT}" \
    --region="${GCP_REGION}" \
    --format="value(status.url)" 2>/dev/null || echo ""
}

# --- Deploy knowledge MCP server ---
deploy_service "rfp-mcp-knowledge" "knowledge"
set +e
KNOWLEDGE_BASE_URL=$(get_url "rfp-mcp-knowledge")
set -e
KNOWLEDGE_MCP_URL="${KNOWLEDGE_BASE_URL}/mcp"
echo "Knowledge MCP URL: ${KNOWLEDGE_MCP_URL}"

# --- Deploy policy MCP server ---
deploy_service "rfp-mcp-policy" "policy"
set +e
POLICY_BASE_URL=$(get_url "rfp-mcp-policy")
set -e
POLICY_MCP_URL="${POLICY_BASE_URL}/mcp"
echo "Policy MCP URL: ${POLICY_MCP_URL}"

# --- Deploy workspace MCP server ---
deploy_service "rfp-mcp-workspace" "workspace"
set +e
WORKSPACE_BASE_URL=$(get_url "rfp-mcp-workspace")
set -e
WORKSPACE_MCP_URL="${WORKSPACE_BASE_URL}/mcp"
echo "Workspace MCP URL: ${WORKSPACE_MCP_URL}"

echo ""
echo "============================================"
echo "All MCP servers deployed successfully!"
echo "============================================"
echo ""
echo "Add the following to your .env file:"
echo ""
echo "KNOWLEDGE_MCP_URL=${KNOWLEDGE_MCP_URL}"
echo "POLICY_MCP_URL=${POLICY_MCP_URL}"
echo "WORKSPACE_MCP_URL=${WORKSPACE_MCP_URL}"
echo ""
echo "NOTE: If any URL above is empty, get them from Cloud Run console"
echo "      or run: gcloud run services list --project=${GOOGLE_CLOUD_PROJECT} --region=${GCP_REGION}"
echo ""
echo "Then redeploy the agent: ./deploy_agent.sh"
