import os
import json
from google.adk.agents import LlmAgent
from retry_llm import gemini_pro
from google.adk.tools import ToolContext
from typing import Dict
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
        workspace = tool_context.state.get('solution_workspace', {})
        workspace[section_id] = content
        tool_context.state['solution_workspace'] = workspace

        saved_sections = sorted(workspace.keys())

        # Persist to file for dashboard
        try:
            import os
            if os.path.exists('workflow_state.json'):
                with open('workflow_state.json', 'r', encoding='utf-8') as f:
                    state = json.load(f)
                if 'solution_workspace' not in state:
                    state['solution_workspace'] = {}
                state['solution_workspace'][section_id] = content
                with open('workflow_state.json', 'w', encoding='utf-8') as f:
                    json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Solution Agent: Error writing to workflow_state.json: {e}")

        return {
            "status": "success",
            "saved_section": section_id,
            "all_saved_sections": saved_sections,
            "saved_count": len(saved_sections),
            "message": (
                f"Draft '{section_id}' saved. "
                f"{len(saved_sections)}/6 sections saved so far: {saved_sections}. "
                f"Remaining sections must still be drafted and saved."
            ),
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

        3. Use save_solution_draft tool to save the section draft.

            For EACH section you draft, you MUST call the `save_solution_draft` tool passing a JSON string containing:
            - "section_id": the ID of the section (e.g., 'security' or 'implementation')
            - "content": the plaintext response draft content

    ============================================================
    HARD REQUIREMENT — READ CAREFULLY:
    ============================================================
    You MUST draft and save EXACTLY SIX sections, with these EXACT section_id values:
        1. executive_summary
        2. technical_approach
        3. security
        4. implementation
        5. pricing
        6. references

    You MUST call `save_solution_draft` SIX SEPARATE TIMES — one call per section.
    Do NOT batch sections into a single tool call. Do NOT include multiple sections in
    one "content" field. Each `save_solution_draft` call must save EXACTLY ONE section.

    The tool response will tell you how many sections have been saved so far
    (`saved_count` and `all_saved_sections`). After EACH tool call, check the response:
    - If `saved_count` is less than 6, you MUST continue calling `save_solution_draft`
      with the next missing section. Do NOT produce a final text summary yet.
    - Only after the response shows `saved_count` = 6 (all six section_ids saved) are
      you allowed to produce the final text summary and end your turn.

    If you produce a final summary before all six saves complete, the workflow will
    fail downstream and the response will be incomplete. There is NO acceptable
    shortcut — six sections, six tool calls, in order.
    ============================================================

    CRITICAL: Prefer detailed, comprehensive enterprise-style paragraphs over terse summaries. The user wants LONGER, more detailed sections. Elaborate on the points using the approved claims.
    Use all relevant approved claims when they materially strengthen the section.
    After all six save_solution_draft calls have completed (saved_count = 6), generate a final text summary of the drafted sections to update the dashboard.
    """,
    ui_desc="""Present the drafted sections using rich UI components like Cards. 
    Highlight key solution points. 
    Use visual status indicators like green ticks (✅) for satisfied requirements or red stops (❌ / 🛑) for unfulfilled benchmarks.""",
    allowed_components=["Card", "Text", "Heading"]
)

solution_agent = LlmAgent(
    name="Solution",
    model=gemini_pro,
    instruction=instruction,
    tools=[build_section_brief, save_solution_draft]
)
