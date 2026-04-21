from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext
from mcp_stubs.policy import validate_claim, check_compliance
from typing import Dict
import json
from a2ui_setup import generate_ui_instruction

def verify_claim(claim: str, tool_context: ToolContext) -> Dict:
    """Queries the Policy MCP to validate a claim."""
    print(f"Governance Agent: Verifying claim: {claim}")
    return validate_claim(claim)

def verify_compliance(text: str, tool_context: ToolContext) -> Dict:
    """Queries the Policy MCP to check compliance of text."""
    print(f"Governance Agent: Checking compliance for text")
    return check_compliance(text)

def save_governance_review(review_json: str, tool_context: ToolContext) -> Dict:
    """Saves the governance review results to state."""
    print(f"Governance Agent: Saving governance review to state.")
    try:
        review = json.loads(review_json)
        tool_context.state['governance'] = review
        return {"status": "success", "message": "Governance review saved."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to parse JSON: {e}"}

# Generate A2UI enriched instructions
instruction = generate_ui_instruction(
    role="You are the Governance Agent. Your job is to review drafts for compliance.",
    workflow="""Read drafts from 'solution_workspace'. Use `verify_claim` and `verify_compliance` to check them. 
    If compliance checks fail, identify the exact sections causing the failure. 
    Save results using `save_governance_review` by passing a JSON string containing the compliance checks and the exact failing sections.
    After checking the drafts, generate a final text summary to update the dashboard.
    You MUST end your response with a clear instruction for the next agent: 'Editor Agent, please proceed to assemble the final response.'""",

    ui_desc="""Present findings using rich UI components. 
    Use visual status indicators like green ticks (✅) for compliance or approvals, and red stops (❌ / 🛑) or warning signs (⚠️) to highlight risks or failures. 
    Use Cards to organize the review outcomes.""",
    allowed_components=["Card", "Text", "Heading"]
)

governance_agent = LlmAgent(
    name="Governance",
    model="gemini-2.5-pro",
    instruction=instruction,
    tools=[verify_claim, verify_compliance, save_governance_review]
)
