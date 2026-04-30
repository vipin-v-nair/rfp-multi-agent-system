#!/bin/bash
set -e

# Deploys the RFP agent to a NEW Agent Engine instance (does not touch the
# existing engine) and binds it to the Agent Gateway.
#
# Once verified, update AGENT_ENGINE_ID in .env with the new engine ID to
# promote it to production.

unset GOOGLE_APPLICATION_CREDENTIALS
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
cp .env deploy_staging/.env

if [ -f .env ]; then
  set -a && source .env && set +a
else
  echo "Error: .env file not found."
  exit 1
fi

if [ -d ".venv/Scripts" ]; then
  VENV_BIN=".venv/Scripts"
else
  VENV_BIN=".venv/bin"
fi

if [ -z "$AGENT_GATEWAY_NAME" ]; then
  echo "ERROR: AGENT_GATEWAY_NAME not set in .env — required for gateway deploy."
  exit 1
fi

echo "Fetching gateway root CA certificate for ${AGENT_GATEWAY_NAME}..."
gcloud alpha network-services agent-gateways describe "${AGENT_GATEWAY_NAME}" \
  --location="${GCP_REGION}" \
  --project="${GOOGLE_CLOUD_PROJECT}" \
  --format="json" | python3 -c "
import json, sys
d = json.load(sys.stdin)
certs = d.get('agentGatewayCard', {}).get('rootCertificates', [])
for cert in certs:
    sys.stdout.write(cert)
    if not cert.endswith('\n'):
        sys.stdout.write('\n')
" > deploy_staging/gateway_ca.pem
echo "Gateway CA written to deploy_staging/gateway_ca.pem ($(wc -l < deploy_staging/gateway_ca.pem) lines)"

# Write agent.py — suppress mTLS endpoint so the SDK uses standard TLS, and
# inject the gateway CA cert into Python's SSL trust store so Agent Registry
# lookups through the gateway succeed (the gateway uses a self-signed cert).
cat << 'EOF' > deploy_staging/agent.py
import sys
import os
import tempfile

# AGENT_IDENTITY provides a client cert which causes vertexai._genai session
# service to select the mTLS endpoint even when GOOGLE_API_USE_MTLS_ENDPOINT=never.
# Prevent cert loading entirely so the standard endpoint is always used.
os.environ['GOOGLE_API_USE_CLIENT_CERTIFICATE'] = 'false'
os.environ['GOOGLE_API_USE_MTLS_ENDPOINT'] = 'never'

# Inject gateway CA cert so Python trusts the gateway's self-signed certificate.
# This allows Agent Registry lookups routed through the gateway to succeed.
_here = os.path.dirname(os.path.abspath(__file__))
_gateway_ca = os.path.join(_here, 'gateway_ca.pem')
if os.path.exists(_gateway_ca):
    try:
        import certifi
        with open(certifi.where()) as _f:
            _existing = _f.read()
        with open(_gateway_ca) as _f:
            _ca = _f.read()
        _tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False)
        _tmp.write(_existing + '\n' + _ca)
        _tmp.close()
        os.environ['SSL_CERT_FILE'] = _tmp.name
        os.environ['REQUESTS_CA_BUNDLE'] = _tmp.name
    except Exception as _e:
        print(f'Warning: could not inject gateway CA cert: {_e}')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agents.coordinator import coordinator as root_agent
EOF

echo "Deploying to Agent Engine in project ${GOOGLE_CLOUD_PROJECT} (gateway: ${AGENT_GATEWAY_NAME})..."
echo ""

# deploy_with_gateway.py calls client.agent_engines.create/update() with
# agent_gateway_config (adk CLI doesn't support this).
$VENV_BIN/python deploy_with_gateway.py
