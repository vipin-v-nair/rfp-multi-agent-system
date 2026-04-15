from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext
from mcp_stubs.workspace import save_draft
from typing import Dict
import json
from a2ui_setup import generate_ui_instruction

def save_solution_draft(draft_json: str, tool_context: ToolContext) -> Dict:
    """Saves a draft section to the workspace and session state."""
    print(f"Solution Agent: Saving draft to workspace")
    try:
        draft = json.loads(draft_json)
        section_id = draft.get("section_id")
        content = draft.get("content")
        mcp_result = save_draft(section_id, content)
        workspace = tool_context.state.get('solution_workspace', {})
        workspace[section_id] = content
        tool_context.state['solution_workspace'] = workspace
        return {
            "status": "success", 
            "message": f"Draft {section_id} saved to state.", 
            "mcp_status": mcp_result["status"]
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to parse JSON: {e}"}

# Generate A2UI enriched instructions
instruction = generate_ui_instruction(
    role="You are the Solution Agent. Your job is to draft response sections based on evidence.",
    workflow="""Read evidence from 'evidence_workspace' in state. 
    Draft response sections using the evidence. 
    For EACH section you draft, you MUST call the `save_solution_draft` tool passing a JSON string containing:
    - "section_id": the ID of the section (e.g., 'security' or 'implementation')
    - "content": the plaintext response draft content
    
    Draft sections for 'executive_summary', 'technical_approach', 'security', 'implementation', 'pricing', and 'references'.

    After calling the tools, generate a final text summary of the drafted sections to update the dashboard.
    """,
    ui_desc="Present the drafted sections using rich UI components like Cards. Highlight key solution points.",
    allowed_components=["Card", "Text", "Heading"]
)

solution_agent = LlmAgent(
    name="Solution",
    model="projects/vipin-genai-bb/locations/us-central1/publishers/google/models/gemini-2.5-flash",
    instruction=instruction,
    tools=[save_solution_draft]
)
