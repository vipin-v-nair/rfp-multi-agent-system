"""
Deploys the RFP agent to a NEW Agent Engine instance with Agent Gateway binding.

Uses the same source_packages approach as `adk deploy agent_engine` internally,
with agent_gateway_config added at create time (which `adk deploy` CLI doesn't support).

Usage:
    python deploy_with_gateway.py

Requires deploy_staging/ to be populated first (run the staging steps from
deploy_agent.sh, or run: bash -c "source deploy_agent.sh" up to the staging step).
The staging is handled by deploy_agent_with_gateway.sh which calls this script.

WARNING: Gateway binding is permanent and cannot be undone.
"""

import os
import sys

import vertexai
from vertexai import types

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from google.adk.cli.cli_deploy import _AGENT_ENGINE_CLASS_METHODS, _AGENT_ENGINE_APP_TEMPLATE

STAGING_DIR = "deploy_staging"

project = os.environ["GOOGLE_CLOUD_PROJECT"]
region = os.environ["GCP_REGION"]
gateway_name = os.environ["AGENT_GATEWAY_NAME"]
staging_bucket = os.environ["STAGING_BUCKET"]

# These are injected by Agent Engine itself and cannot be overridden via env_vars
_RESERVED_ENV_VARS = {
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
    "GOOGLE_CLOUD_REGION",
}

# Read env vars from .env to pass as runtime env vars to the engine
env_vars: dict = {}
env_file = os.path.join(STAGING_DIR, ".env")
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                key = key.strip()
                if key not in _RESERVED_ENV_VARS:
                    env_vars[key] = val.strip()

# Inject telemetry flag (mirrors --otel_to_cloud flag in adk deploy)
env_vars["GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"] = "true"
# AGENT_IDENTITY provides a client cert, which causes vertexai._genai session
# service to select the mTLS endpoint. Prevent this with both env vars:
# - GOOGLE_API_USE_CLIENT_CERTIFICATE=false: stops the auth library loading the cert
# - GOOGLE_API_USE_MTLS_ENDPOINT=never: belt-and-suspenders fallback
env_vars["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
env_vars["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"
# ENFORCE_MCP_REGISTRY: read from .env (default false — falls back to env var URLs if registry fails)
if "ENFORCE_MCP_REGISTRY" not in env_vars:
    env_vars["ENFORCE_MCP_REGISTRY"] = "false"

# Create the agent_engine_app.py entry point (same as adk deploy does)
agent_engine_app_content = _AGENT_ENGINE_APP_TEMPLATE.format(
    app_name="rfp_system",
    trace_to_cloud_option=True,
    is_config_agent=False,
    agent_folder=f"./{STAGING_DIR}",
    adk_app_object="root_agent",
    adk_app_type="agent",
    express_mode=False,
)
app_file = os.path.join(STAGING_DIR, "agent_engine_app.py")
with open(app_file, "w", encoding="utf-8") as f:
    f.write(agent_engine_app_content)
print(f"Created {app_file}")

client = vertexai.Client(project=project, location=region)

agent_config = {
    "display_name": "rfp_system_gateway",
    "source_packages": [STAGING_DIR],
    "entrypoint_module": f"{STAGING_DIR}.agent_engine_app",
    "entrypoint_object": "adk_app",
    "class_methods": _AGENT_ENGINE_CLASS_METHODS,
    "agent_framework": "google-adk",
    "requirements_file": os.path.join(STAGING_DIR, "requirements.txt"),
    "env_vars": env_vars,
    "identity_type": types.IdentityType.AGENT_IDENTITY,
    "agent_gateway_config": {
        "agent_to_anywhere_config": {
            "agent_gateway": f"projects/{project}/locations/{region}/agentGateways/{gateway_name}"
        }
    },
}

existing_engine_id = os.environ.get("AGENT_ENGINE_ID", "").strip()
is_update = bool(existing_engine_id and "your-engine-id" not in existing_engine_id)

if is_update:
    print(f"Updating existing gateway engine: {existing_engine_id}")
    print(f"Gateway: {gateway_name}")
    client.agent_engines.update(name=existing_engine_id, config=agent_config)
    engine_name = existing_engine_id
    print(f"\n✅ Updated agent engine: {engine_name}")
else:
    print(f"Deploying to Vertex AI Agent Engine in project {project}...")
    print(f"Binding to gateway: {gateway_name}")
    print("(Creating new engine — existing engine is untouched as fallback)")
    engine = client.agent_engines.create(config=agent_config)
    engine_name = engine.api_resource.name
    print(f"\n✅ Created agent engine: {engine_name}")
    print(f"\nTo promote to production, update your .env:")
    print(f"  AGENT_ENGINE_ID={engine_name}")
    print(f"\nTo delete this engine if testing fails:")
    print(f"  python -c \"import vertexai; vertexai.Client(project='{project}', location='{region}').agent_engines.delete('{engine_name}')\"")

engine_id = engine_name.split("/")[-1]
print("\n🎉 View your deployed agent here:")
print(f"https://console.cloud.google.com/vertex-ai/agents/agent-engines/locations/{region}/agent-engines/{engine_id}/playground?project={project}")
print("\nWARNING: Gateway binding is permanent and cannot be undone.")
