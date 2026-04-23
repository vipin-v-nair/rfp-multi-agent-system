"""
Workspace MCP Server

Supports two transport modes controlled by environment variables:
  - stdio (default): spawned as subprocess by ADK agents
  - streamable-http:  runs as standalone HTTP service on $PORT

Environment variables:
  MCP_TRANSPORT  "stdio" | "http"   (default: stdio)
  PORT           port number        (default: 3003, Cloud Run sets this automatically)
  MCP_HOST       bind host          (default: 127.0.0.1, use 0.0.0.0 for Cloud Run)
"""
import os
import sys
from mcp.server.fastmcp import FastMCP

_transport = os.getenv("MCP_TRANSPORT", "stdio")
_host = os.getenv("MCP_HOST", "127.0.0.1")
_port = int(os.getenv("PORT", "3003"))

mcp = FastMCP("workspace", host=_host, port=_port, stateless_http=True)


@mcp.tool()
def save_draft(section_id: str, content: str) -> dict:
    """Save a draft section to the workspace.

    Args:
        section_id: Unique identifier for the section (e.g. 'executive_summary').
        content: The draft text content to save.
    """
    print(f"Workspace MCP Server: Saving draft for section '{section_id}'", file=sys.stderr)
    return {"status": "success", "section_id": section_id, "saved": True}


@mcp.tool()
def get_draft(section_id: str) -> dict:
    """Retrieve a previously saved draft section from the workspace.

    Args:
        section_id: Unique identifier for the section to retrieve.
    """
    print(f"Workspace MCP Server: Retrieving draft for section '{section_id}'", file=sys.stderr)
    return {"status": "success", "section_id": section_id, "content": f"Draft content for {section_id}"}


@mcp.tool()
def log_event(event_type: str, summary: str) -> dict:
    """Log a workflow event to the workspace audit trail.

    Args:
        event_type: Category of event (e.g. 'draft_saved', 'review_complete').
        summary: Human-readable description of what happened.
    """
    print(f"Workspace MCP Server: Logging event '{event_type}': {summary}", file=sys.stderr)
    return {"status": "success", "logged": True}


@mcp.tool()
def publish_response(content: dict) -> dict:
    """Publish the final assembled RFP response to the workspace.

    Args:
        content: Dictionary containing the final response draft and metadata.
    """
    print("Workspace MCP Server: Publishing final response", file=sys.stderr)
    return {"status": "success", "published": True, "url": "http://example.com/published_rfp"}


if __name__ == "__main__":
    if _transport == "http":
        print(f"Workspace MCP Server: Starting streamable-http on {_host}:{_port}/mcp", file=sys.stderr)
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")
