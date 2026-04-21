from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext
from mcp_stubs.workspace import save_draft
from typing import Dict
import json
from a2ui_setup import generate_ui_instruction

def build_section_brief(section_id, approved_claims, requirements):
    section_claims = []
    for c in approved_claims:
        if isinstance(c, dict):
            if c.get("section") == section_id:
                section_claims.append(c)
        elif isinstance(c, str):
            section_claims.append({"text": c, "subtopic": "general", "claim_id": "unknown"})

    grouped = {}
    for claim in section_claims:
        subtopic = claim.get("subtopic", "general")
        grouped.setdefault(subtopic, []).append(claim)

    subsections = []
    for subtopic, claims in grouped.items():
        subsections.append({
            "title": subtopic.replace('_', ' ').title(),
            "subtopic": subtopic,
            "claim_ids": [c.get("claim_id") for c in claims]
        })

    return {
        "section_id": section_id,
        "objective": f"Draft the {section_id} section.",
        "requirements": requirements,
        "subsections": [{
            "title": f"Draft the {section_id} section.",
            "subtopics": "Overview",
            "claim_ids":[]
        },
        {
            "title": f"Draft the {section_id} section.",
            "subtopics": "description of subtopic ,alligned to requirements",
            "claim_ids":[]
        }
        ],
        "global_constraints": [],
        "drafting_guidance": f"Draft according to {section_id} compliance guidelines. Cover each sub section explicitly",
        "status": "planned",
        "target_shape" :{
            "min_paragraphs" : 5,
            "must_have_opening" : True,
            "must_have_conclusions" : True,
        }
    }


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
        
        # Persist to file for dashboard
        from state import state_lock
        try:
            with state_lock:
                with open('workflow_state.json', 'r') as f:
                    state = json.load(f)
                
                if 'solution_workspace' not in state:
                    state['solution_workspace'] = {}
                    
                state['solution_workspace'][section_id] = content
                
                with open('workflow_state.json', 'w') as f:
                    json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Solution Agent: Error writing to workflow_state.json: {e}")
            
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
    
    HITL Feedback Handling:
    If state['workflow']['status'] is 'revision_requested' and 'user_feedback' is present in the state:
    - Read the 'user_feedback' provided by the user.
    - Identify which sections need changes based on the feedback.
    - Revise the existing drafts in 'solution_workspace' to address the feedback.
    - Proceed to save the revised drafts using the `save_solution_draft` tool.
    - You do NOT need to redraft all sections, only those affected by the feedback.

    Standard Drafting Steps:
    Draft response sections using the evidence using the following steps: 

        1. Use build_section_brief tool to build section brief : Create a structured brief for the section with objective, requirements, subsections, and constraints.
        2. Generate the section draft: 
            Draft the section as a proposal-quality response using the provided section brief and approved claims.

            Requirements:
            - Write an opening overview paragraph.
            - Cover each subsection in the brief.
            - Write at least TWO paragraphs for each subsection in the brief to ensure depth.
            - Use detailed, comprehensive enterprise-style paragraphs. Do NOT be concise.
            - Use only the approved claims provided.
            - Do not invent facts, metrics, certifications, or references.
            - Respect all global constraints.

            The section MUST feel comprehensive, detailed, structured, and supportable.
            
        3. Use save section draft tool to save section draft

    
            For EACH section you draft, you MUST call the `save_solution_draft` tool passing a JSON string containing:
            - "section_id": the ID of the section (e.g., 'security' or 'implementation')
            - "content": the plaintext response draft content
    
    Draft sections for 'executive_summary', 'technical_approach', 'security', 'implementation', 'pricing', and 'references'.
    

    CRITICAL: Prefer detailed, comprehensive enterprise-style paragraphs over terse summaries. The user wants LONGER, more detailed sections. Elaborate on the points using the approved claims.
    Use all relevant approved claims when they materially strengthen the section.
    After calling the tools, generate a final text summary of the drafted sections to update the dashboard.
    """,
    ui_desc="""Present the drafted sections using rich UI components like Cards. 
    Highlight key solution points. 
    Use visual status indicators like green ticks (✅) for satisfied requirements or red stops (❌ / 🛑) for unfulfilled benchmarks.""",
    allowed_components=["Card", "Text", "Heading"]
)

solution_agent = LlmAgent(
    name="Solution",
    model="gemini-2.5-pro",
    instruction=instruction,
    tools=[build_section_brief, save_solution_draft]
)
