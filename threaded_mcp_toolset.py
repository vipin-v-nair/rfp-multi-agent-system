"""
ThreadedMCPToolset — proper MCPToolset integration for Vertex AI Agent Engine.

Root cause of the original MCPToolset failure:
  anyio's CancelScope binds to the asyncio.Task that enters it. Agent Engine
  can context-switch tasks between entering and exiting the scope (inside
  streamablehttp_client's anyio.create_task_group()), causing:
    "Attempted to exit cancel scope in a different task than it was entered in"

Fix:
  Run each MCP operation in a dedicated thread via asyncio.to_thread().
  Inside that thread, create asyncio.new_event_loop() and run the MCP call
  there. The anyio CancelScope is created and destroyed entirely within that
  isolated loop — no cross-task contamination from Agent Engine's scheduler.

Retry logic:
  Cloud Run autoscaling can cause a 401 when an initialize request lands on one
  pod and the subsequent tools/list or tool-call lands on a freshly-scaled pod
  that has no session context. Each retry creates a brand-new connection so the
  entire handshake lands on a single pod.

This gives us:
  - True MCP tool discovery via tools/list (no hardcoded tool names)
  - Full MCP protocol: init handshake → session → schema-validated call
  - Proper FunctionDeclaration with inputSchema from the server
  - The LLM knows it is calling MCP-backed tools
  - Works in both local ADK server and Vertex AI Agent Engine
"""

import asyncio
import json
import logging
import time
from typing import Any, List, Optional, Union

import httpx
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_DELAY_S = 0.5


# ---------------------------------------------------------------------------
# Retry helpers
# ---------------------------------------------------------------------------

def _is_retryable(exc: Exception) -> bool:
    """Return True for transient errors worth retrying (401, connection drops)."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (401, 503, 502)
    if isinstance(exc, (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadError)):
        return True
    # 401/connection errors wrapped in ExceptionGroup by anyio TaskGroup
    if isinstance(exc, ExceptionGroup):
        return any(_is_retryable(e) for e in exc.exceptions)
    # Fallback: check string representation
    return "401" in str(exc) or "Unauthorized" in str(exc)


def _run_with_retry(fn, *args) -> Any:
    """Run fn(*args) synchronously, retrying on transient errors."""
    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(_MAX_RETRIES):
        if attempt > 0:
            time.sleep(_RETRY_DELAY_S)
            logger.warning("MCP retry %d/%d for %s", attempt, _MAX_RETRIES - 1, args[0])
        try:
            return fn(*args)
        except Exception as exc:
            if _is_retryable(exc):
                last_exc = exc
                continue
            raise
    raise last_exc


# ---------------------------------------------------------------------------
# Low-level helpers — run MCP operations synchronously in an isolated loop
# ---------------------------------------------------------------------------

def _cancel_pending(loop: asyncio.AbstractEventLoop) -> None:
    """Cancel remaining tasks so the loop closes without warnings."""
    pending = asyncio.all_tasks(loop)
    if pending:
        for task in pending:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))


def _mcp_list_tools_once(url: str) -> list:
    """Single attempt: open an MCP session, run tools/list, return raw tools."""
    async def _async():
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return result.tools

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async())
    finally:
        _cancel_pending(loop)
        loop.close()


def _mcp_call_tool_once(url: str, tool_name: str, arguments: dict) -> Any:
    """Single attempt: open an MCP session, call a tool, return parsed result."""
    async def _async():
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)

                if result.isError:
                    raise RuntimeError(
                        f"MCP tool '{tool_name}' returned an error: {result.content}"
                    )

                if result.content:
                    text = result.content[0].text
                    try:
                        return json.loads(text)
                    except (json.JSONDecodeError, AttributeError):
                        return {"text": text}
                return {}

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async())
    finally:
        _cancel_pending(loop)
        loop.close()


def _mcp_list_tools(url: str) -> list:
    return _run_with_retry(_mcp_list_tools_once, url)


def _mcp_call_tool(url: str, tool_name: str, arguments: dict) -> Any:
    return _run_with_retry(_mcp_call_tool_once, url, tool_name, arguments)


# ---------------------------------------------------------------------------
# ThreadedMCPTool — a single MCP tool as an ADK BaseTool
# ---------------------------------------------------------------------------

class ThreadedMCPTool(BaseTool):
    """
    An ADK BaseTool backed by a single tool on an MCP server.

    The tool name, description, and input schema come directly from the
    MCP server's tools/list response. Execution runs in a dedicated thread
    with an isolated asyncio event loop, avoiding the anyio cancel scope
    issue in Agent Engine.
    """

    def __init__(self, *, url: str, mcp_tool: Any):
        super().__init__(
            name=mcp_tool.name,
            description=mcp_tool.description or "",
        )
        self._url = url
        self._mcp_tool = mcp_tool

    def _get_declaration(self) -> types.FunctionDeclaration:
        """Build a FunctionDeclaration using the JSON schema from the MCP server."""
        try:
            return types.FunctionDeclaration(
                name=self.name,
                description=self.description,
                parameters_json_schema=self._mcp_tool.inputSchema,
            )
        except TypeError:
            # Older ADK versions that don't support parameters_json_schema
            from google.adk.tools.mcp_tool.conversion_utils import _to_gemini_schema
            return types.FunctionDeclaration(
                name=self.name,
                description=self.description,
                parameters=_to_gemini_schema(self._mcp_tool.inputSchema),
            )

    async def run_async(self, *, args: dict, tool_context: ToolContext) -> Any:
        """
        Execute the MCP tool call.

        asyncio.to_thread() offloads _mcp_call_tool to the thread pool so
        Agent Engine's event loop is not blocked. Inside that thread, a fresh
        asyncio.new_event_loop() hosts the MCP session — cancel scopes never
        cross task boundaries.
        """
        return await asyncio.to_thread(_mcp_call_tool, self._url, self.name, args)


# ---------------------------------------------------------------------------
# ThreadedMCPToolset — a full BaseToolset for one MCP server
# ---------------------------------------------------------------------------

class ThreadedMCPToolset(BaseToolset):
    """
    A BaseToolset that connects to an MCP server via streamable-HTTP transport,
    discovers its tools dynamically, and exposes them as ADK-compatible tools.

    All MCP I/O runs in isolated threads so the anyio cancel scope issue in
    Vertex AI Agent Engine is completely avoided. Transient 401 errors caused
    by Cloud Run autoscaling are retried automatically.

    Usage in an LlmAgent:
        LlmAgent(
            tools=[
                ThreadedMCPToolset(url="https://my-mcp-server.run.app/mcp"),
                my_native_adk_tool,
            ]
        )
    """

    def __init__(
        self,
        *,
        url: str,
        tool_filter: Optional[Union[List[str], Any]] = None,
        tool_name_prefix: Optional[str] = None,
    ):
        super().__init__(tool_filter=tool_filter, tool_name_prefix=tool_name_prefix)
        self._url = url

    async def get_tools(self, readonly_context: Optional[Any] = None) -> List[BaseTool]:
        """
        Discover tools from the MCP server via tools/list.

        Runs in a thread so the MCP SDK's anyio internals are isolated from
        Agent Engine's event loop.
        """
        mcp_tools = await asyncio.to_thread(_mcp_list_tools, self._url)
        tools = []
        for mcp_tool in mcp_tools:
            if self._should_include(mcp_tool.name):
                tools.append(ThreadedMCPTool(url=self._url, mcp_tool=mcp_tool))
        return tools

    def _should_include(self, tool_name: str) -> bool:
        if self.tool_filter is None:
            return True
        if isinstance(self.tool_filter, list):
            return tool_name in self.tool_filter
        if callable(self.tool_filter):
            return self.tool_filter(tool_name)
        return True
