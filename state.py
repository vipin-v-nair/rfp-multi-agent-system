from typing import Any, Dict

def get_initial_state() -> Dict[str, Any]:
    """Returns the initial top-level state structure for the RFP system."""
    return {
        "project": {},
        "rfp_input": {},
        "rfp_analysis": {},
        "evidence_workspace": {},
        "solution_workspace": {},
        "governance": {},
        "workflow": {
            "stage": "intake",
            "status": "not_started"
        },
        "ui_state": {},
        "final_output": {}
    }

# Constants for state keys
KEY_PROJECT = "project"
KEY_RFP_INPUT = "rfp_input"
KEY_RFP_ANALYSIS = "rfp_analysis"
KEY_EVIDENCE_WORKSPACE = "evidence_workspace"
KEY_SOLUTION_WORKSPACE = "solution_workspace"
KEY_GOVERNANCE = "governance"
KEY_WORKFLOW = "workflow"
KEY_UI_STATE = "ui_state"
KEY_FINAL_OUTPUT = "final_output"

# Stage constants
STAGE_INTAKE = "intake"
STAGE_EVIDENCE_GATHERING = "evidence_gathering"
STAGE_DRAFTING = "drafting"
STAGE_GOVERNANCE_REVIEW = "governance_review"
STAGE_FINAL_ASSEMBLY = "final_assembly"
STAGE_PUBLISH = "publish"

# Status constants
STATUS_NOT_STARTED = "not_started"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_BLOCKED = "blocked"
