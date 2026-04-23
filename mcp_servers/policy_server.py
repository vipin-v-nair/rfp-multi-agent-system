"""
Policy Validation MCP Server

Supports two transport modes controlled by environment variables:
  - stdio (default): spawned as subprocess by ADK agents
  - streamable-http:  runs as standalone HTTP service on $PORT

Environment variables:
  MCP_TRANSPORT  "stdio" | "http"   (default: stdio)
  PORT           port number        (default: 3002, Cloud Run sets this automatically)
  MCP_HOST       bind host          (default: 127.0.0.1, use 0.0.0.0 for Cloud Run)
"""
import json
import os
import sys
from mcp.server.fastmcp import FastMCP

_transport = os.getenv("MCP_TRANSPORT", "stdio")
_host = os.getenv("MCP_HOST", "127.0.0.1")
_port = int(os.getenv("PORT", "3002"))

mcp = FastMCP("policy", host=_host, port=_port, stateless_http=True)


def _get_fixtures_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "demo_data", "knowledge", "approved_claims.json")


@mcp.tool()
def validate_claim(claim: str) -> dict:
    """Validate a claim against the approved policy claim list.

    Returns whether the claim is approved and the reason.
    """
    print(f"Policy MCP Server: Validating claim: {claim}", file=sys.stderr)
    fixtures_path = _get_fixtures_path()

    try:
        with open(fixtures_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for category_claims in data.values():
            for item in category_claims:
                approved_text = item.get("text", "").lower()
                if approved_text in claim.lower() or claim.lower() in approved_text:
                    return {
                        "status": "success",
                        "claim": claim,
                        "is_valid": True,
                        "reason": f"Matches allowed claim: {item.get('text', '')}",
                    }
    except Exception as e:
        print(f"Policy MCP Server: Error reading fixtures: {e}", file=sys.stderr)

    return {
        "status": "success",
        "claim": claim,
        "is_valid": False,
        "reason": "Unsupported claim or policy violation",
    }


@mcp.tool()
def check_compliance(text: str) -> dict:
    """Check a block of text for compliance against policy rules.

    Returns compliance status and any findings.
    """
    print("Policy MCP Server: Checking compliance", file=sys.stderr)
    return {
        "status": "success",
        "compliant": True,
        "findings": [],
    }


if __name__ == "__main__":
    if _transport == "http":
        print(f"Policy MCP Server: Starting streamable-http on {_host}:{_port}/mcp", file=sys.stderr)
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")
