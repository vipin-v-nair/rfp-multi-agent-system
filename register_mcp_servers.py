"""
Register the RFP system's MCP servers in the Vertex AI Agent Registry.

NOTE ON API STATUS (as of April 2026):
  The Agent Registry REST API only supports READ operations (GET/list) at
  the v1alpha endpoint. The CREATE (POST) operation returns 404, meaning
  programmatic registration is not yet publicly available.

  To register MCP servers, use the Cloud Console UI:
    Cloud Console -> Vertex AI -> Agent Builder -> Agent Registry -> MCP Servers

  MCP servers to register:
    ID: rfp-mcp-knowledge
    URL: <KNOWLEDGE_MCP_URL from .env>

    ID: rfp-mcp-policy
    URL: <POLICY_MCP_URL from .env>

  Protocol for all: CUSTOM / HTTP_JSON / protocolVersion 2024-11-05

This script still verifies that the Agent Registry API is reachable and
lists any already-registered MCP servers.

NOTE: Even when registered, AgentRegistry.get_mcp_toolset() returns a
McpToolset which has the anyio cancel scope bug in Agent Engine. Continue
using ThreadedMCPToolset for actual connections. Registration here is for
governance and discoverability only.

Usage:
  python register_mcp_servers.py

Requirements:
  - ADC configured: gcloud auth application-default login
  - GOOGLE_APPLICATION_CREDENTIALS must NOT point to a stale service account key
    (unset it or use: GOOGLE_APPLICATION_CREDENTIALS="" python register_mcp_servers.py)
"""

import json
import os
import sys

import google.auth
import google.auth.transport.requests
import httpx
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("AGENT_REGISTRY_LOCATION", os.getenv("GCP_REGION", "us-central1"))

KNOWLEDGE_MCP_URL = os.getenv("KNOWLEDGE_MCP_URL")
POLICY_MCP_URL = os.getenv("POLICY_MCP_URL")

AGENT_REGISTRY_BASE = "https://agentregistry.googleapis.com/v1alpha"

# MCP servers to register
MCP_SERVERS = [
    {
        "mcpServerId": "rfp-mcp-knowledge",
        "displayName": "RFP Knowledge MCP Server",
        "description": (
            "Provides evidence retrieval and approved claims for RFP responses. "
            "Tools: get_evidence, get_approved_claims."
        ),
        "protocols": [
            {
                "type": "CUSTOM",
                "protocolVersion": "2024-11-05",
                "interfaces": [
                    {
                        "url": KNOWLEDGE_MCP_URL,
                        "protocolBinding": "HTTP_JSON",
                    }
                ],
            }
        ],
    },
    {
        "mcpServerId": "rfp-mcp-policy",
        "displayName": "RFP Policy MCP Server",
        "description": (
            "Validates claims and checks text compliance against RFP policy rules. "
            "Tools: validate_claim, check_compliance."
        ),
        "protocols": [
            {
                "type": "CUSTOM",
                "protocolVersion": "2024-11-05",
                "interfaces": [
                    {
                        "url": POLICY_MCP_URL,
                        "protocolBinding": "HTTP_JSON",
                    }
                ],
            }
        ],
    },
]


def get_auth_headers() -> dict:
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json",
    }


def register_mcp_server(client: httpx.Client, headers: dict, server: dict) -> dict:
    server_id = server["mcpServerId"]
    url = (
        f"{AGENT_REGISTRY_BASE}/projects/{PROJECT_ID}/locations/{LOCATION}"
        f"/mcpServers?mcpServerId={server_id}"
    )
    body = {k: v for k, v in server.items() if k != "mcpServerId"}

    print(f"\nRegistering: {server['displayName']} ({server_id})")
    print(f"  URL: {server['protocols'][0]['interfaces'][0]['url']}")

    resp = client.post(url, headers=headers, json=body)

    if resp.status_code == 409:
        print(f"  Already registered — updating...")
        update_url = (
            f"{AGENT_REGISTRY_BASE}/projects/{PROJECT_ID}/locations/{LOCATION}"
            f"/mcpServers/{server_id}"
        )
        resp = client.patch(update_url, headers=headers, json=body)

    if resp.status_code not in (200, 201):
        print(f"  ERROR {resp.status_code}: {resp.text}")
        return {}

    result = resp.json()
    print(f"  Registered: {result.get('name', 'unknown')}")
    return result


def list_registered_servers(client: httpx.Client, headers: dict) -> dict:
    url = (
        f"{AGENT_REGISTRY_BASE}/projects/{PROJECT_ID}/locations/{LOCATION}"
        f"/mcpServers"
    )
    resp = client.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"ERROR listing servers {resp.status_code}: {resp.text[:200]}")
        return {}
    return resp.json()


def main():
    if not PROJECT_ID:
        print("ERROR: GOOGLE_CLOUD_PROJECT not set in .env")
        sys.exit(1)

    print(f"Agent Registry MCP Server status")
    print(f"  Project:  {PROJECT_ID}")
    print(f"  Location: {LOCATION}")
    print()
    print("NOTE: Programmatic registration (POST) is not yet supported by the")
    print("  v1alpha Agent Registry API. Register servers via Cloud Console:")
    print(f"  https://console.cloud.google.com/agent-space/agent-registry?project={PROJECT_ID}")
    print()

    headers = get_auth_headers()

    with httpx.Client(timeout=30) as client:
        result = list_registered_servers(client, headers)

    servers = result.get("mcpServers", [])
    if servers:
        print(f"Currently registered MCP servers ({len(servers)}):")
        for s in servers:
            print(f"  {s.get('name')} — {s.get('displayName', '')}")
    else:
        print("No MCP servers registered yet.")
        print()
        print("Register these 3 servers in the Console:")
        for s in MCP_SERVERS:
            print(f"  ID: {s['mcpServerId']}")
            print(f"  URL: {s['protocols'][0]['interfaces'][0]['url']}")
            print()


if __name__ == "__main__":
    main()
