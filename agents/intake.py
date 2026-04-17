from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext
from typing import Dict
import json
from a2ui_setup import generate_ui_instruction

def save_rfp_analysis(analysis_json: str, tool_context: ToolContext) -> Dict:
    """Saves the extracted RFP requirements and rules to the session state.
    
    Args:
        analysis_json: A JSON string containing extracted requirements and rules.
    """
    print(f"Intake Agent: Saving RFP analysis to state.")
    try:
        analysis = json.loads(analysis_json)
        tool_context.state['rfp_analysis'] = analysis
        
        # Persist to file for dashboard
        try:
            with open('workflow_state.json', 'r') as f:
                state = json.load(f)
            state['rfp_analysis'] = analysis
            with open('workflow_state.json', 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Intake Agent: Error writing to workflow_state.json: {e}")
            
        return {"status": "success", "message": "RFP analysis saved."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to parse JSON: {e}"}

# Generate A2UI enriched instructions
instruction = generate_ui_instruction(
    role="You are the Intake Agent. Your job is to parse RFP text and extract requirements.",
    workflow="""Read the structured RFP extracted content from state under 'rfp_input' (specifically 'extracted_pages' and 'section_candidates'). Extract requirements into a structured JSON output containing:
    - requirements: Array of requirement objects with requirement_id, category, description
    - mandatory_sections: Array of mandatory section IDs
    - submission_rules: object containing max_pages, format, must_include_security_section
    - open_questions: Array of questions
    - risks: Array of risk objects with risk_id, description

    Save this structure using the `save_rfp_analysis` tool by passing a JSON string.

    CRITICAL: If the user message contains feedback for rework and not a request to analyze new content, do NOT call any tools. Simply state that intake analysis is already complete and pass control to the next agent.
    """,
    ui_desc="Present the extracted requirements and rules using rich UI components like Cards and Tables.",
    allowed_components=["Card", "Text", "Table", "Heading"]
)

intake_agent = LlmAgent(
    name="Intake",
    model="projects/vipin-genai-bb/locations/global/publishers/google/models/gemini-3.1-pro-preview",
    instruction=instruction,
    tools=[save_rfp_analysis]
)
