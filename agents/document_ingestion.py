from google.adk.agents import LlmAgent
from retry_llm import gemini_pro
from google.adk.tools import ToolContext
from typing import Dict
import json
import os
from a2ui_setup import generate_ui_instruction

def register_source_document(project_id: str, file_path: str, tool_context: ToolContext) -> Dict:
    """Registers the source PDF file in the session state."""
    print(f"Ingestion Agent: Registering {file_path}")
    # File existence check removed for remote decoupled execution
        
    doc = {
        "doc_id": "rfp_doc_001",
        "doc_type": "rfp_main",
        "file_name": os.path.basename(file_path),
        "mime_type": "application/pdf",
        "ingestion_status": "registered"
    }
    if 'rfp_input' not in tool_context.state:
        tool_context.state['rfp_input'] = {}
    tool_context.state['rfp_input'].setdefault('source_documents', []).append(doc)

    return {"status": "success", "doc_id": "rfp_doc_001"}

def extract_pdf_text(doc_id: str, tool_context: ToolContext) -> Dict:
    """Simulates extracting text from the registered PDF and populates extracted_pages."""
    print(f"Ingestion Agent: Extracting text for {doc_id}")
    
    # For the demo, we populate an extracted page containing the full RFP text to allow downstream agents to process all requirements.
    text = """
    Request for Proposal: Acme Bank Customer Service Transformation RFP

    Section: Executive Summary
    Provide an executive summary of your proposed approach.

    Section: Technical Approach
    Describe your AI-powered customer service solution, integrations, and deployment model.

    Section: Security and Compliance
    Describe encryption, hosting controls, certifications, and compliance posture relevant to regulated banking workloads.

    Section: Implementation Plan
    Provide a phased rollout plan, timeline, and operating model.

    Section: Pricing Assumptions
    Provide commercial assumptions and pricing approach.

    Section: Customer References
    Provide relevant references for similar deployments.
    """
    pages = [
        {
            "page_number": 1,
            "text": text.strip()
        }
    ]
    tool_context.state['rfp_input']['extracted_pages'] = pages
    return {"status": "success", "pages": pages}

def detect_section_candidates(doc_id: str, tool_context: ToolContext) -> Dict:
    """Populates section candidates for the registered document."""
    print(f"Ingestion Agent: Detecting section candidates.")
    sections = [
        {
            "section_id": "sec_001",
            "title": "Introduction",
            "start_page": 1,
            "end_page": 1
        }
    ]
    tool_context.state['rfp_input']['section_candidates'] = sections
    return {"status": "success", "sections": sections}

def extract_submission_rules(max_pages: int, required_format: str, must_include_executive_contact: bool, must_include_security_section: bool, must_include_pricing_assumptions: bool, tool_context: ToolContext) -> Dict:
    """Saves submission constraints extracted from the PDF."""
    print(f"Ingestion Agent: Extracting submission rules.")
    rules = {
        "max_pages": max_pages,
        "required_format": required_format,
        "must_include_executive_contact": must_include_executive_contact,
        "must_include_security_section": must_include_security_section,
        "must_include_pricing_assumptions": must_include_pricing_assumptions
    }
    tool_context.state['rfp_input']['submission_constraints_raw'] = rules
    return {"status": "success", "submission_rules": rules}

def extract_evaluation_criteria(criteria_json: str, tool_context: ToolContext) -> Dict:
    """Saves evaluation criteria extracted from the PDF.
    Args:
        criteria_json: A JSON string containing an array of criteria object with 'name' and 'weight'.
    """
    print(f"Ingestion Agent: Extracting evaluation criteria.")
    try:
        criteria = json.loads(criteria_json)
        tool_context.state['rfp_input']['evaluation_criteria'] = criteria
        return {"status": "success", "evaluation_criteria": criteria}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Enrich instructions for the A2UI
instruction = generate_ui_instruction(
    role="You are the Document Ingestion Agent. Your job is to register the PDF RFP and extract its structured content.",
    workflow="""Use the provided tools sequentially to process the RFP document:
    1. Call `register_source_document` with the project ID and file path.
    2. Call `extract_pdf_text` to extract text content.
    3. Call `detect_section_candidates` to structure the parsed text.
    4. Call `extract_submission_rules` to extract constraints.
    5. Call `extract_evaluation_criteria` to extract evaluation criteria.

    CRITICAL: If the user message contains feedback for rework (e.g., 'Rework the response based on this feedback') and not a request to process a new PDF, do NOT call any tools. Simply state that document ingestion is already complete and pass control to the next agent.
    """,
    ui_desc="Present the extracted pages, constraints, and structured section candidates.",
    allowed_components=["Card", "Text", "Table", "Heading"]
)

document_ingestion_agent = LlmAgent(
    name="DocumentIngestion",
    model=gemini_pro,
    instruction=instruction,
    tools=[
        register_source_document, 
        extract_pdf_text, 
        detect_section_candidates, 
        extract_submission_rules, 
        extract_evaluation_criteria
    ]
)
