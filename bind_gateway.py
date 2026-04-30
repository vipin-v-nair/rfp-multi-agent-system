"""
Binds a deployed Agent Engine to an Agent Gateway.

Works with engines deployed via `adk deploy agent_engine` (sourceCodeSpec / deployment_source).
Uses the REST API directly because the Vertex AI Python SDK validation blocks
gateway-only updates on sourceCodeSpec engines.

Run after deploy_agent.sh or standalone:

    python bind_gateway.py <engine_resource_name>

WARNING: Gateway binding is permanent and cannot be undone.
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error
import subprocess

# Load .env if python-dotenv is available, otherwise fall back to os.environ
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

project = os.environ["GOOGLE_CLOUD_PROJECT"]
region = os.environ["GCP_REGION"]
gateway_name = os.environ["AGENT_GATEWAY_NAME"]

# Accept engine ID as a CLI arg (for new engines) or fall back to .env
engine_id = sys.argv[1] if len(sys.argv) > 1 else os.environ["AGENT_ENGINE_ID"]

gateway_resource = f"projects/{project}/locations/{region}/agentGateways/{gateway_name}"
base_url = f"https://{region}-aiplatform.googleapis.com/v1beta1/{engine_id}"


def get_access_token() -> str:
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def patch(url: str, body: dict, update_mask: str, token: str) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{url}?updateMask={update_mask}",
        data=data,
        method="PATCH",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        try:
            return json.loads(error_body)
        except Exception:
            return {"error": {"code": e.code, "message": error_body}}


def wait_for_operation(op_name: str, token: str) -> dict:
    url = f"https://{region}-aiplatform.googleapis.com/v1beta1/{op_name}"
    for _ in range(40):
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
        if result.get("done"):
            return result
        print("  waiting for operation to complete...")
        time.sleep(15)
    return result


token = get_access_token()

print(f"Binding {engine_id} to gateway {gateway_name}...")
print(f"Gateway resource: {gateway_resource}")

# Step 1: ensure AGENT_IDENTITY is set (idempotent)
print("\nStep 1: Setting identity_type=AGENT_IDENTITY...")
result = patch(
    base_url,
    {"spec": {"identityType": "AGENT_IDENTITY"}},
    "spec.identity_type",
    token,
)
if "error" in result:
    print(f"  ERROR: {result['error']}")
    sys.exit(1)
op_name = result.get("name", "").lstrip("/")
print(f"  Operation: {op_name}")
final = wait_for_operation(op_name, token)
if "error" in final:
    print(f"  Operation failed: {final['error']}")
    sys.exit(1)
print("  AGENT_IDENTITY set successfully.")

# Refresh token after long wait
token = get_access_token()

# Step 2: bind agent gateway config
print(f"\nStep 2: Binding agent_gateway_config...")
result = patch(
    base_url,
    {
        "spec": {
            "deploymentSpec": {
                "agentGatewayConfig": {
                    "agentToAnywhereConfig": {
                        "agentGateway": gateway_resource
                    }
                }
            }
        }
    },
    "spec.deployment_spec.agent_gateway_config",
    token,
)
if "error" in result:
    print(f"  ERROR: {json.dumps(result['error'], indent=2)}")
    sys.exit(1)
op_name = result.get("name", "").lstrip("/")
print(f"  Operation: {op_name}")
final = wait_for_operation(op_name, token)
if "error" in final:
    print(f"  Operation failed: {final['error']}")
    sys.exit(1)

print("\nAgent Gateway binding complete.")
print("WARNING: This binding is permanent and cannot be undone.")
