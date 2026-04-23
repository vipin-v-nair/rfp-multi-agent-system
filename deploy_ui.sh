#!/bin/bash
set -e

# Load environment variables
if [ -f .env ]; then
  set -a && source .env && set +a
else
  echo "Error: .env file not found. Please copy .env.example to .env and fill in the values."
  exit 1
fi

if [ -z "$AGENT_ENGINE_ID" ] || [[ "$AGENT_ENGINE_ID" == *"your-engine-id"* ]]; then
  echo "Error: AGENT_ENGINE_ID must be set in .env before deploying to Cloud Run."
  exit 1
fi

unset GOOGLE_APPLICATION_CREDENTIALS
echo "Deploying FastAPI UI to Cloud Run in project ${GOOGLE_CLOUD_PROJECT}..."

# On Windows, gcloud in bash requires PowerShell due to Python version conflicts.
# On Mac/Linux, gcloud runs directly.
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
  powershell -Command "& { gcloud beta run deploy rfp-dashboard \
    --source . \
    --platform=managed \
    --project=${GOOGLE_CLOUD_PROJECT} \
    --region=${GCP_REGION} \
    --allow-unauthenticated \
    --set-env-vars='AGENT_ENGINE_ID=${AGENT_ENGINE_ID}' 2>&1 }"
else
  gcloud run deploy rfp-dashboard \
    --source . \
    --project=${GOOGLE_CLOUD_PROJECT} \
    --region=${GCP_REGION} \
    --allow-unauthenticated \
    --set-env-vars="AGENT_ENGINE_ID=${AGENT_ENGINE_ID}"
fi

echo "Cloud Run Deployment Complete!"
