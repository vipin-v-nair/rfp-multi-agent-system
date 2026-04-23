"""
MCP client using the official MCP Python SDK.

Runs each tool call in an isolated thread with its own event loop to avoid
the anyio cancel scope task mismatch that occurs in Vertex AI Agent Engine's
async execution model. This lets us use the full MCP protocol (initialization,
session management, schema validation) without MCPToolset.

Root cause of the original failure: anyio's CancelScope binds to the exact
asyncio.Task that enters it. Agent Engine can context-switch tasks between
entering and exiting the scope (inside streamablehttp_client's TaskGroup),
causing "Attempted to exit cancel scope in a different task than it was
entered in". Running each call in a fresh thread with asyncio.new_event_loop()
isolates the cancel scope entirely, avoiding the conflict.
"""
import asyncio
import json
import os
import threading
from typing import Any, Dict

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

_KNOWLEDGE_MCP_URL = os.getenv("KNOWLEDGE_MCP_URL", "http://127.0.0.1:3001/mcp")
_POLICY_MCP_URL = os.getenv("POLICY_MCP_URL", "http://127.0.0.1:3002/mcp")
_WORKSPACE_MCP_URL = os.getenv("WORKSPACE_MCP_URL", "http://127.0.0.1:3003/mcp")


def _call(url: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    Call an MCP tool using the official SDK, isolated in a fresh thread+event loop.

    Each call:
      1. Opens a new streamable-HTTP connection to the MCP server.
      2. Runs the MCP initialization handshake (protocol negotiation).
      3. Calls the tool with schema-validated arguments.
      4. Returns the parsed result.

    Running in a dedicated thread with asyncio.new_event_loop() means the
    anyio CancelScope created inside streamablehttp_client is entered and
    exited within the same task in that isolated loop — no cross-task conflict.
    """
    result: list = [None]
    error: list = [None]

    async def _async_call():
        async with streamablehttp_client(url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                call_result = await session.call_tool(tool_name, arguments)

                if call_result.isError:
                    raise RuntimeError(f"MCP tool error from {tool_name}: {call_result.content}")

                if call_result.content:
                    text = call_result.content[0].text
                    try:
                        return json.loads(text)
                    except (json.JSONDecodeError, AttributeError):
                        return {"text": text}
                return {}

    def _run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result[0] = loop.run_until_complete(_async_call())
        except Exception as exc:
            error[0] = exc
        finally:
            # Cancel any pending tasks so the event loop closes cleanly
            # (avoids "Task was destroyed but it is pending!" warnings from
            # async generators inside the MCP SDK transport)
            pending = asyncio.all_tasks(loop)
            if pending:
                for task in pending:
                    task.cancel()
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()

    thread = threading.Thread(target=_run_in_thread, daemon=True)
    thread.start()
    thread.join(timeout=40)

    if thread.is_alive():
        raise TimeoutError(f"MCP call to {url}/{tool_name} timed out after 40s")
    if error[0] is not None:
        raise error[0]
    return result[0] or {}


# --- Knowledge tools ---

def get_evidence(query: str) -> dict:
    """Retrieve evidence from the knowledge base for a given query."""
    return _call(_KNOWLEDGE_MCP_URL, "get_evidence", {"query": query})


def get_approved_claims() -> list:
    """Retrieve all approved claims from the knowledge base."""
    return _call(_KNOWLEDGE_MCP_URL, "get_approved_claims", {})


# --- Policy tools ---

def validate_claim(claim: str) -> dict:
    """Validate a claim against the approved policy claim list."""
    return _call(_POLICY_MCP_URL, "validate_claim", {"claim": claim})


def check_compliance(text: str) -> dict:
    """Check a block of text for compliance against policy rules."""
    return _call(_POLICY_MCP_URL, "check_compliance", {"text": text})


# --- Workspace tools ---

def save_draft(section_id: str, content: str) -> dict:
    """Save a draft section to the workspace."""
    return _call(_WORKSPACE_MCP_URL, "save_draft", {"section_id": section_id, "content": content})


def publish_response(content: dict) -> dict:
    """Publish the final assembled RFP response to the workspace."""
    return _call(_WORKSPACE_MCP_URL, "publish_response", {"content": content})
