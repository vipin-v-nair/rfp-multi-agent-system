from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext
from mcp_stubs.knowledge import get_evidence
from typing import Dict
import json
from a2ui_setup import generate_ui_instruction

def search_evidence(query: str, tool_context: ToolContext) -> Dict:
    """Queries the Knowledge base for evidence supporting a requirement."""
    print(f"Evidence Agent: Searching evidence for: {query}")
    return get_evidence(query)

def save_evidence_workspace(workspace_json: str, tool_context: ToolContext) -> Dict:
    """Saves the gathered evidence to the session state."""
    print(f"Evidence Agent: Saving evidence workspace to state.")
    try:
        workspace = json.loads(workspace_json)
        tool_context.state['evidence_workspace'] = workspace
        return {"status": "success", "message": "Evidence workspace saved."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to parse JSON: {e}"}

# Generate A2UI enriched instructions
instruction = generate_ui_instruction(
    role="You are the Evidence Agent. Your job is to gather evidence for RFP requirements.",
    workflow="""Read requirements from 'rfp_analysis' in state. Search for evidence benchmarks to populate a JSON output containing:
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
    model="projects/vipin-genai-bb/locations/us-central1/publishers/google/models/gemini-2.5-flash",
    instruction=instruction,
    tools=[search_evidence, save_evidence_workspace]
)
