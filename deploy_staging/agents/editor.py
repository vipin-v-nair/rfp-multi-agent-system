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
        tool_context.state.setdefault('workflow', {})['status'] = 'pending_review'

        # Persist to file for dashboard
        from state import state_lock
        try:
            with state_lock:
                with open('workflow_state.json', 'r') as f:
                    state = json.load(f)
                
                state['final_output'] = {
                    "response_draft": response_draft,
                    "readiness": readiness
                }
                state.setdefault('workflow', {})['status'] = 'pending_review'
                
                with open('workflow_state.json', 'w') as f:
                    json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Editor Agent: Error writing to workflow_state.json: {e}")

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
    Also read the compliance checks stored in 'governance' from the shared state to check if any governance failures occurred.
    
    You MUST generate a fully-fledged RFP response draft based on the gathered evidence.
    If the governance review indicates compliance failures, you MUST raise appropriate red flags in the response draft referencing the failed sections.
    
    CRITICAL: The user wants LONGER, more detailed sections. Ensure the final response is comprehensive and detailed. If the input drafts are short, elaborate on them to create full, enterprise-style paragraphs. Do NOT truncate or summarize.
    
    The response MUST be formatted exactly into the following sections:
    1. Executive Summary
    2. Technical Approach
    3. Security and Compliance
    4. Implementation Plan
    5. Pricing Assumptions
    6. Customer References
    7. Closing

    You MUST call the `save_final_response` tool as your very first action. Pass:
    - "response_draft": the generated fully-fledged RFP response draft as a plaintext string
    - "readiness_json": a JSON string containing the readiness score and approvals status. 
         If governance failures are present, reduce the readiness score accordingly, mark the failing approvals as "Flagged" or "Rejected", and mark "submission_compliant" as false.
         Otherwise, use a standard passing JSON configuration:
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

    After calling the tool, you MUST generate a textual summary of the final response draft to update the dashboard.
    """,
    ui_desc="""Present the final response using rich UI components. 
    Use a Card to show the Readiness Score.
    Use an Approvals Checklist panel featuring visual status indicators like green ticks (✅) for approvals and red stops (❌ / 🛑) for failures.
    Provide placeholders for 'Export to PDF/Word' actions.""",
    allowed_components=["Card", "Text", "Heading", "Table"]
)

editor_agent = LlmAgent(
    name="Editor",
    model="gemini-2.5-pro",
    instruction=instruction,
    tools=[save_final_response, publish_final_response]
)
