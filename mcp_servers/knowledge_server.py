"""
Knowledge Base MCP Server

Exposes knowledge base tools via the MCP protocol (stdio transport).
Replaces mcp_stubs/knowledge.py with a real MCP server implementation.
"""
import json
import os
import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("knowledge")


def _get_fixtures_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "demo_data", "knowledge", "approved_claims.json")


@mcp.tool()
def get_evidence(query: str) -> dict:
    """Retrieve evidence from the knowledge base for a given query.

    Searches approved claims and returns matching evidence, customer references,
    and certifications relevant to the query.
    """
    print(f"Knowledge MCP Server: Retrieving evidence for query: {query}", file=sys.stderr)
    fixtures_path = _get_fixtures_path()

    try:
        with open(fixtures_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        results = []
        for section_claims in data.values():
            for item in section_claims:
                if any(
                    word in item["text"].lower()
                    for word in query.lower().split()
                    if len(word) > 3
                ):
                    results.append(item["text"])

        if results:
            return {
                "status": "success",
                "query": query,
                "evidence": results,
                "customer_references": [
                    {
                        "reference_id": "ref_001",
                        "display_name": "Tier-1 North American Bank",
                        "usage": "Supported modernization of service operations",
                    },
                    {
                        "reference_id": "ref_002",
                        "display_name": "Global Financial Institution",
                        "usage": "Enabled phased transformation approach",
                    },
                ],
                "certifications": [
                    {"name": "ISO 27001"},
                    {"name": "SOC 2 Type II"},
                ],
            }
    except Exception as e:
        print(f"Knowledge MCP Server: Error reading fixtures: {e}", file=sys.stderr)

    return {
        "status": "success",
        "query": query,
        "evidence": ["No specific evidence found in corpus."],
        "customer_references": [
            {
                "reference_id": "ref_001",
                "display_name": "Tier-1 North American Bank",
                "usage": "Supported modernization of service operations",
            },
            {
                "reference_id": "ref_002",
                "display_name": "Global Financial Institution",
                "usage": "Enabled phased transformation approach",
            },
        ],
        "certifications": [
            {"name": "ISO 27001"},
            {"name": "SOC 2 Type II"},
        ],
    }


@mcp.tool()
def get_approved_claims() -> list:
    """Retrieve all approved claims from the knowledge base."""
    print("Knowledge MCP Server: Retrieving all approved claims", file=sys.stderr)
    fixtures_path = _get_fixtures_path()
    try:
        with open(fixtures_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [item["text"] for section_claims in data.values() for item in section_claims]
    except Exception as e:
        print(f"Knowledge MCP Server: Error reading fixtures: {e}", file=sys.stderr)
        return []


if __name__ == "__main__":
    mcp.run()
