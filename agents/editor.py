from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext
from mcp_stubs.workspace import publish_response
from typing import Dict
import json
from a2ui_setup import generate_ui_instruction

def save_final_response(response_draft: str, readiness_json: str, tool_context: ToolContext) -> Dict:
    """Saves the final assembled response to state."""
    print(f"Editor Agent: Saving final response to state.")
    try:
        readiness = json.loads(readiness_json)
        tool_context.state['final_output'] = {
            "response_draft": response_draft,
            "readiness": readiness
        }
        return {"status": "success", "message": "Final response saved."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to parse JSON: {e}"}

def publish_final_response(content_json: str, tool_context: ToolContext) -> Dict:
    """Queries the Workspace MCP to publish the response."""
    print(f"Editor Agent: Publishing final response.")
    try:
        content = json.loads(content_json)
        return publish_response(content)
    except Exception as e:
        return {"status": "error", "message": f"Failed to parse JSON: {e}"}

# Generate A2UI enriched instructions
instruction = generate_ui_instruction(
    role="You are the Editor Agent. Your job is to assemble and publish the final response.",
    workflow="""Read the drafts stored in 'solution_workspace' from the shared state. 
    You MUST generate a fully-fledged RFP response draft based on the gathered evidence. 
    The response MUST be formatted exactly into the following sections:
    1. Executive Summary
    2. Technical Approach
    3. Security and Compliance
    4. Implementation Plan
    5. Pricing Assumptions
    6. Customer References
    7. Closing

    Call the `save_final_response` tool passing:
    - "response_draft": the generated fully-fledged RFP response draft as a plaintext string
    - "readiness_json": a JSON string containing:
         {
           "readiness_score": 95,
           "approvals": {
              "security": "Approved",
              "legal": "Approved",
              "commercial": "Approved"
           },
           "all_sections_present": true,
           "all_blockers_resolved": true,
           "approvals_complete": true,
           "submission_compliant": true
         }
    """,
    ui_desc="Present the final response using rich UI components. Use a Card to show the Readiness Score (95%), an Approvals Checklist panel, and placeholders for 'Export to PDF/Word' actions.",
    allowed_components=["Card", "Text", "Heading", "Table"]
)

editor_agent = LlmAgent(
    name="Editor",
    model="projects/vipin-genai-bb/locations/us-central1/publishers/google/models/gemini-2.5-flash",
    instruction=instruction,
    tools=[save_final_response, publish_final_response]
)
