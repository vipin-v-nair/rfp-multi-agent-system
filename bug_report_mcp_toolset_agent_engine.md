# Bug Report: `McpToolset` fails in Vertex AI Agent Engine with anyio cancel scope task mismatch

## Summary

`McpToolset` (both `StdioConnectionParams` and `StreamableHTTPConnectionParams`) raises a `RuntimeError` when used inside a Vertex AI Agent Engine deployment. The error is raised inside anyio's cancel scope exit handler and cannot be caught by user code because it propagates through the ADK tool execution pipeline, silently aborting all MCP tool calls.

**Affected package:** `google-adk`
**Affected class:** `google.adk.tools.mcp_tool.mcp_toolset.McpToolset`
**Affected versions:** Confirmed on `google-adk==1.30.0`, `mcp==1.27.0`, `anyio==4.13.0`
**Deployment target:** Vertex AI Agent Engine (Reasoning Engine)
**Does not affect:** Local `adk web` server

---

## Error

```
RuntimeError: Attempted to exit cancel scope in a different task than it was entered in
```

Full traceback (from Agent Engine session logs):

```
Traceback (most recent call last):
  File ".../google/adk/tools/mcp_tool/mcp_toolset.py", line 295, in _execute_with_session
    return await asyncio.wait_for(coroutine_func(session), timeout=...)
  File ".../mcp/client/streamable_http.py", line 717, in streamablehttp_client
    async with streamable_http_client(...):
  File ".../mcp/client/streamable_http.py", line 647, in streamable_http_client
    async with anyio.create_task_group() as tg:
  File ".../anyio/_backends/_asyncio.py", line 799, in __aexit__
    ...
  File ".../anyio/_backends/_asyncio.py", line 454, in __exit__
    if current_task() is not self._host_task:
RuntimeError: Attempted to exit cancel scope in a different task than it was entered in
```

---

## Root Cause

### anyio's CancelScope is task-bound

anyio's `CancelScope.__enter__` records the asyncio `Task` that entered the scope:

```python
# anyio/_backends/_asyncio.py
def __enter__(self) -> CancelScope:
    self._host_task = cast(asyncio.Task, current_task())  # binds to current task
    self._tasks.add(self._host_task)
    self._active = True
    return self
```

And `__exit__` enforces that the *same* task exits it:

```python
def __exit__(self, ...):
    if current_task() is not self._host_task:       # strict identity check
        raise RuntimeError(
            "Attempted to exit cancel scope in a different task than it was entered in"
        )
```

### Where the scope is created

`streamablehttp_client` (inside the `mcp` library) creates a `TaskGroup` — and therefore a `CancelScope` — on every connection:

```python
# mcp/client/streamable_http.py
@asynccontextmanager
async def streamable_http_client(url, ...):
    async with anyio.create_task_group() as tg:   # <-- CancelScope created here
        tg.start_soon(transport.post_writer, ...)
        yield (read_stream, write_stream, transport.get_session_id)
        tg.cancel_scope.cancel()                  # <-- CancelScope exited here
```

`McpToolset._execute_with_session` then calls this inside `asyncio.wait_for`:

```python
# mcp_toolset.py
return await asyncio.wait_for(coroutine_func(session), timeout=...)
```

### Why Agent Engine triggers the bug

Vertex AI Agent Engine runs agents inside its own async execution model. The critical detail is that **Agent Engine can migrate or reschedule the asyncio `Task` between the point where the scope is entered (inside `streamablehttp_client.__aenter__`) and where it is exited (`__aexit__`)**. This is not an issue in a straightforward `asyncio.run()` context (like the local ADK web server) because tasks run to completion on the same loop without migration. In Agent Engine's managed runtime, the task identity check in anyio's `CancelScope.__exit__` finds `current_task() is not self._host_task` and raises.

The same failure mode affects both `StdioConnectionParams` and `StreamableHTTPConnectionParams` because both use anyio internally (stdio uses `anyio.open_process`, streamable-HTTP uses `anyio.create_task_group`).

---

## Minimal Reproduction

This reproduces the error outside Agent Engine by simulating a task switch across the context manager boundary:

```python
import asyncio
import anyio
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_URL = "http://localhost:3001/mcp"  # any running FastMCP server

async def call_mcp_in_wrong_task():
    """Simulates what Agent Engine does: enter context in one task, exit in another."""
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # Simulate Agent Engine task switch by awaiting something that
            # lets the scheduler run a different coroutine first
            await asyncio.sleep(0)   # yields control
            result = await session.call_tool("get_evidence", {"query": "test"})
            return result

async def main():
    # Agent Engine wraps tool calls in tasks — reproduce by creating a task
    task = asyncio.create_task(call_mcp_in_wrong_task())
    await task

asyncio.run(main())
```

A more direct reproduction using `McpToolset` as deployed on Agent Engine:

```python
import asyncio
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

async def main():
    toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url="http://localhost:3001/mcp"
        )
    )
    # get_tools internally calls _execute_with_session -> streamablehttp_client
    tools = await toolset.get_tools()
    tool = tools[0]
    # run_async internally calls _run_async_impl -> create_session -> cancel scope
    result = await tool.run_async(args={"query": "test"}, tool_context=None)
    print(result)

asyncio.run(main())
# Works locally. Fails on Agent Engine with:
# RuntimeError: Attempted to exit cancel scope in a different task than it was entered in
```

---

## Impact

- `McpToolset` is **completely unusable** on Vertex AI Agent Engine with either transport
- No workaround is possible within the `McpToolset` API — the error originates inside anyio's internal cancel scope management, not in user-accessible code
- Silent failure: the exception is caught by the ADK agent runner and surfaced only in session logs, so the agent continues without any MCP tool access

---

## Fix Applied (Workaround)

We replaced `McpToolset` with a custom `BaseToolset` implementation (`ThreadedMCPToolset`) that runs every MCP operation in a **dedicated thread with `asyncio.new_event_loop()`**. Because the cancel scope is created and destroyed entirely within that isolated loop, it never crosses task boundaries regardless of what Agent Engine's scheduler does to the outer loop.

```python
import asyncio
import json
from typing import Any, List, Optional
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client


def _mcp_call_tool(url: str, tool_name: str, arguments: dict) -> Any:
    """Synchronous: must be called from a thread (not an async context)."""
    async def _async():
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                if result.content:
                    return json.loads(result.content[0].text)
                return {}

    # Fresh event loop per call — cancel scopes are fully isolated
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async())
    finally:
        pending = asyncio.all_tasks(loop)
        for t in pending:
            t.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()


def _mcp_list_tools(url: str) -> list:
    async def _async():
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return (await session.list_tools()).tools

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async())
    finally:
        loop.close()


class ThreadedMCPTool(BaseTool):
    def __init__(self, *, url: str, mcp_tool: Any):
        super().__init__(name=mcp_tool.name, description=mcp_tool.description or "")
        self._url = url
        self._mcp_tool = mcp_tool

    def _get_declaration(self) -> types.FunctionDeclaration:
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters_json_schema=self._mcp_tool.inputSchema,
        )

    async def run_async(self, *, args: dict, tool_context: ToolContext) -> Any:
        # asyncio.to_thread runs _mcp_call_tool in the thread pool.
        # Inside that thread, asyncio.new_event_loop() creates a fully
        # isolated loop — cancel scopes cannot cross task boundaries.
        return await asyncio.to_thread(_mcp_call_tool, self._url, self.name, args)


class ThreadedMCPToolset(BaseToolset):
    def __init__(self, *, url: str, **kwargs):
        super().__init__(**kwargs)
        self._url = url

    async def get_tools(self, readonly_context=None) -> List[BaseTool]:
        mcp_tools = await asyncio.to_thread(_mcp_list_tools, self._url)
        return [ThreadedMCPTool(url=self._url, mcp_tool=t) for t in mcp_tools]
```

Usage in an `LlmAgent` is identical to `McpToolset`:

```python
from threaded_mcp_toolset import ThreadedMCPToolset

evidence_agent = LlmAgent(
    name="Evidence",
    model="gemini-2.5-pro",
    instruction=instruction,
    tools=[
        ThreadedMCPToolset(url="https://my-mcp-server.run.app/mcp"),
        my_native_adk_tool,
    ]
)
```

---

## Suggested Fix in `google-adk`

The root cause is that `McpToolset._execute_with_session` and `MCPSessionManager.create_session` allow the anyio `TaskGroup`/`CancelScope` to be entered in Agent Engine's task context. The fix could be applied at either level:

1. **In `McpToolset._execute_with_session`**: wrap the `coroutine_func` call with `asyncio.to_thread(lambda: asyncio.run(coroutine_func(...)))` when the environment is detected as Agent Engine.

2. **In `MCPSessionManager.create_session`**: detect when the running loop does not own the cancel scope's host task and re-create the session in an isolated thread.

3. **In the `mcp` library**: provide a synchronous or thread-safe `call_tool` API that does not rely on anyio `TaskGroup` persistence across await points.

Option 1 is the least invasive and can be made conditional on an environment variable (e.g., `GOOGLE_CLOUD_AGENT_ENGINE_ID` being set).

---

## Environment

```
google-adk==1.30.0
mcp==1.27.0
anyio==4.13.0
Python 3.11
Deployment: Vertex AI Agent Engine (us-central1)
MCP transport: StreamableHTTPConnectionParams (Cloud Run)
```
