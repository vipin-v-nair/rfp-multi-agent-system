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
    Draft response sections using the evidence using the following steps: 

        1. Use build_section_brief tool to build section brief : Create a structured brief for the section with objective, requirements, subsections, and constraints.
        2. Use draft from section brief : 
            Draft the section as a proposal-quality response using the provided section brief and approved claims.

            Requirements:
            - Write an opening overview paragraph.
            - Cover each subsection in the brief.
            - Write at least one paragraph for each subsection in the brief.
            - Use complete enterprise-style paragraphs.
            - Use only the approved claims provided.
            - Do not invent facts, metrics, certifications, or references.
            - Respect all global constraints.

            The section should feel comprehensive, structured, and supportable.
            
        3. Use save section draft tool to save section draft

    
            For EACH section you draft, you MUST call the `save_solution_draft` tool passing a JSON string containing:
            - "section_id": the ID of the section (e.g., 'security' or 'implementation')
            - "content": the plaintext response draft content
    
    Draft sections for 'executive_summary', 'technical_approach', 'security', 'implementation', 'pricing', and 'references'.
    

    Prefer complete, enterprise-style paragraphs over terse summaries.
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
    model="projects/vipin-genai-bb/locations/us-central1/publishers/google/models/gemini-2.5-flash",
    instruction=instruction,
    tools=[build_section_brief, save_solution_draft]
)
