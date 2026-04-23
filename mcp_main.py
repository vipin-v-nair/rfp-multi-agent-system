"""
Entry point for MCP servers running on Cloud Run.

Reads MCP_SERVER env var to select which server to start:
  MCP_SERVER=knowledge  -> knowledge_server.py
  MCP_SERVER=policy     -> policy_server.py
  MCP_SERVER=workspace  -> workspace_server.py

Cloud Run automatically sets PORT. MCP_HOST must be 0.0.0.0 for Cloud Run.
"""
import os
import sys

server = os.getenv("MCP_SERVER", "knowledge")

if server == "knowledge":
    from mcp_servers.knowledge_server import mcp
elif server == "policy":
    from mcp_servers.policy_server import mcp
elif server == "workspace":
    from mcp_servers.workspace_server import mcp
else:
    print(f"ERROR: Unknown MCP_SERVER value: '{server}'. Must be knowledge, policy, or workspace.", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
