from typing import Any, Dict

def get_initial_state() -> Dict[str, Any]:
    """Returns the initial top-level state structure for the RFP system."""
    return {
        "project": {},
        "rfp_input": {},
        "rfp_analysis": {
            "requirements": [],
            "mandatory_sections": [],
            "evaluation_criteria": [],
            "submission_rules": {},
            "open_questions": [],
            "risks": []

        },
        "evidence_workspace": {
            "search_queries": [],
            "supporting_snippets": [],
            "approved_claims": [],
            "customer_references": [],
            "certifications": [],
            "gaps": []

        },
        "solution_workspace": {
            "outline": [],
            "section_briefs": {},
            "section_drafts": {},
            "assumptions": [],
            "missing_inputs": []
        },
        "governance": {
            "findings": [],
            "compliance_checks_by_section" :[],
            "blocked_items": [],
            "approvals_required": [],
            "approved_items": [],
            "submission_compliance": {}
        },
        "workflow": {
            "stage": "intake",
            "status": "not_started",
            "active_agent": None,
            "next_action": None,
            "halt_reason": None
        },
        "ui_state": {

        },
        "final_output": {
            "response_draft": None,
            "readiness": {},
            "all_sections_present" :False,
            "submission_complete" :False,
            "publish_status": "not_ready",
            "approvals" : {}
        }
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
STAGE_DOCUMENT_INGESTION = "document_ingestion"
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

import threading
state_lock = threading.Lock()
