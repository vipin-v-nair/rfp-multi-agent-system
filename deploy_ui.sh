#!/bin/bash
set -e

# Load environment variables
if [ -f .env ]; then
  source .env
else
  echo "Error: .env file not found. Please copy .env.example to .env and fill in the values."
  exit 1
fi

if [ -z "$AGENT_ENGINE_ID" ] || [[ "$AGENT_ENGINE_ID" == *"your-engine-id"* ]]; then
  echo "Error: AGENT_ENGINE_ID must be set in .env before deploying to Cloud Run."
  exit 1
fi

echo "🚀 Deploying FastAPI UI to Cloud Run in project ${GOOGLE_CLOUD_PROJECT}..."

gcloud run deploy rfp-dashboard \
  --source . \
  --project=${GOOGLE_CLOUD_PROJECT} \
  --region=${GCP_REGION} \
  --allow-unauthenticated \
  --set-env-vars="AGENT_ENGINE_ID=${AGENT_ENGINE_ID}"

echo "✅ Cloud Run Deployment Complete!"
