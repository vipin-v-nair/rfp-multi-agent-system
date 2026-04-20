import os
import json
from typing import Any, Dict
from google.cloud import firestore

# Firestore initialization
project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "vipin-genai-bb")
try:
    db = firestore.Client(project=project_id)
except Exception as e:
    print(f"Warning: Failed to initialize Firestore. Falling back to local memory if needed. Error: {e}")
    db = None

COLLECTION_NAME = "rfp_sessions"

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
        "ui_state": {},
        "final_output": {
            "response_draft": None,
            "readiness": {},
            "all_sections_present" :False,
            "submission_complete" :False,
            "publish_status": "not_ready",
            "approvals" : {}
        }
    }

class FirestoreStateManager:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.local_state = get_initial_state()
        self.local_events = []
        self.use_firestore = False
        
        if db:
            self.doc_ref = db.collection(COLLECTION_NAME).document(session_id)
            self.use_firestore = True
        else:
            self.doc_ref = None
            
    def init_state(self):
        if self.use_firestore:
            try:
                self.doc_ref.set({
                    "state": get_initial_state(),
                    "events": []
                })
            except Exception as e:
                print(f"Warning: Firestore set failed, falling back to memory. Error: {e}")
                self.use_firestore = False
                
        # Reset local state
        self.local_state = get_initial_state()
        self.local_events = []
            
    def get_state(self):
        if self.use_firestore:
            try:
                doc = self.doc_ref.get()
                if doc.exists:
                    return doc.to_dict().get("state", get_initial_state())
            except Exception as e:
                print(f"Warning: Firestore get failed. Error: {e}")
                self.use_firestore = False
        return self.local_state
        
    def get_events(self):
        if self.use_firestore:
            try:
                doc = self.doc_ref.get()
                if doc.exists:
                    return doc.to_dict().get("events", [])
            except Exception as e:
                print(f"Warning: Firestore get failed. Error: {e}")
                self.use_firestore = False
        return self.local_events
        
    def update_state(self, new_state: Dict[str, Any]):
        self.local_state = new_state
        if self.use_firestore:
            try:
                self.doc_ref.update({"state": new_state})
            except Exception as e:
                print(f"Warning: Firestore update failed. Error: {e}")
                self.use_firestore = False
            
    def append_event(self, event: Dict[str, Any]):
        self.local_events.append(event)
        if self.use_firestore:
            try:
                self.doc_ref.update({"events": firestore.ArrayUnion([event])})
            except Exception as e:
                print(f"Warning: Firestore event append failed. Error: {e}")
                self.use_firestore = False

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
