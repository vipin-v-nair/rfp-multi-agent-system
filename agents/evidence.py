import os
import json
from google.adk.agents import LlmAgent
from retry_llm import gemini_pro
from google.adk.tools import ToolContext
from typing import Dict
from a2ui_setup import generate_ui_instruction
from agent_registry_lookup import get_mcp_url
from threaded_mcp_toolset import ThreadedMCPToolset

_KNOWLEDGE_MCP_URL = get_mcp_url("rfp-mcp-knowledge", fallback_env_var="KNOWLEDGE_MCP_URL")


def save_evidence_workspace(workspace_json: str, tool_context: ToolContext) -> Dict:
    """Saves the gathered evidence to the session state."""
    print(f"Evidence Agent: Saving evidence workspace to state.")
    try:
        workspace = json.loads(workspace_json)
        tool_context.state['evidence_workspace'] = workspace

        try:
            if os.path.exists('workflow_state.json'):
                with open('workflow_state.json', 'r', encoding='utf-8') as f:
                    state = json.load(f)
                state['evidence_workspace'] = workspace
                with open('workflow_state.json', 'w', encoding='utf-8') as f:
                    json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Evidence Agent: Error writing to workflow_state.json: {e}")

        return {"status": "success", "message": "Evidence workspace saved."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to parse JSON: {e}"}


instruction = generate_ui_instruction(
    role="You are the Evidence Agent. Your job is to gather evidence for RFP requirements.",
    workflow="""Read requirements from 'rfp_analysis' in state.

    HITL Feedback Handling:
    If state['workflow']['status'] is 'revision_requested' and 'user_feedback' is present in the state:
    - Read the 'user_feedback' provided by the user.
    - If the feedback implies that information is missing or incorrect, use the `get_evidence` tool to search for new evidence.
    - Update the 'evidence_workspace' with any new evidence found or modifications required.

    Standard Steps:
    Use the `get_evidence` tool to search for evidence benchmarks. Compile the results into a JSON object containing:

    - approved_claims: array of objects with claim_id, text, category
    - customer_references: array of objects with reference_id, display_name, usage
    - certifications: array of objects with name
    - gaps: array of objects with gap_id, category, description

    Save the compiled evidence using `save_evidence_workspace` by passing a JSON string.
    """,
    ui_desc="Present the gathered evidence using rich UI components like Cards and Tables. Show clear mapping between requirements and evidence.",
    allowed_components=["Card", "Text", "Table", "Heading"]
)

evidence_agent = LlmAgent(
    name="Evidence",
    model=gemini_pro,
    instruction=instruction,
    tools=[
        ThreadedMCPToolset(url=_KNOWLEDGE_MCP_URL),
        save_evidence_workspace,
    ]
)
