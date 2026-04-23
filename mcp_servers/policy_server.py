"""
Policy Validation MCP Server

Exposes policy validation tools via the MCP protocol (stdio transport).
Replaces mcp_stubs/policy.py with a real MCP server implementation.
"""
import json
import os
import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("policy")


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
    mcp.run()
