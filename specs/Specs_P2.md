I’m updating the architecture so the PDF becomes the true system entrypoint, not just a file sitting next to JSON fixtures. That mainly affects ingestion, parsing, provenance, and how Intake gets its inputs.

Thought for 9s

Yes. Starting with the PDF is the right move.

The main change is this:

The system should no longer treat the RFP as already-structured input.
Instead, it should treat the PDF as the primary source artifact, then run a small document-ingestion pipeline before the existing Intake/Evidence/Solution/Governance flow.

New top-level flow
User uploads PDF
  → Document Intake / Ingestion
  → Document Structuring
  → Intake Agent
  → Evidence Agent
  → Solution Agent
  → Governance Agent
  → Editor Agent
  → Publish
What changes architecturally

Your current design assumes:

rfp_input is mostly ready
Intake starts from structured sections

With PDF-first, you need two new responsibilities before Intake can do its job well:

extract text and structure from the PDF
normalize that extraction into agent-usable document objects

I recommend adding one new agent and one new MCP/server capability, while keeping the rest of the design intact.

Recommended updated architecture
New components
1. Document Ingestion Agent

New agent that handles:

PDF registration
text extraction handoff
page/section provenance
extraction quality checks
creation of normalized document objects
2. Document Processing Service

A new service layer, preferably behind MCP if you want a clean enterprise boundary.

This service handles:

PDF text extraction
page segmentation
heading detection
section candidate extraction
table / submission-rule extraction
provenance mapping
Updated architecture diagram
User / A2UI
   │
   ▼
ADK App
 ├── Coordinator Agent
 ├── Document Ingestion Agent   ← NEW
 ├── Intake Agent
 ├── Evidence Agent
 ├── Solution Agent
 ├── Governance Agent
 └── Editor Agent
        │
        ▼
Shared Session State
        │
        ├── Document Processing MCP Server   ← NEW
        ├── Knowledge MCP Server
        ├── Policy MCP Server
        └── Workspace MCP Server
Why this is the right change

This preserves your core story:

agents collaborate through shared memory
governance remains central
UI still works the same way

But now the system starts from something that feels much more real:

an uploaded PDF
parsed into structured memory
traced back to pages and sections

That makes the demo stronger.

New phase before Intake: Document ingestion

You should split the current “Intake” into two stages:

Stage A — Document Ingestion

Goal:
turn raw PDF into normalized extraction output

Stage B — RFP Intake Analysis

Goal:
turn normalized extraction into procurement requirements and workflow-ready structure

That means your workflow stages become:

document_ingestion
intake
evidence_gathering
drafting
governance_review
final_assembly
publish
New agent: Document Ingestion Agent
Mission

Convert uploaded PDF(s) into normalized, provenance-aware document structures for downstream use.

Responsibilities
register uploaded PDF in project state
call document extraction service
detect extraction issues
build structured section candidates
store page-level provenance
populate rfp_input
Reads
uploaded file reference
project
Writes
rfp_input.source_documents
rfp_input.extracted_pages
rfp_input.section_candidates
rfp_input.tables
rfp_input.extraction_warnings
workflow
Allowed tools
Document Processing MCP tools
Workspace MCP: audit logging
Forbidden actions
must not interpret business requirements
must not classify sections as final procurement requirements
must not draft response content
Success criteria
PDF text extracted
section candidates identified
provenance stored
warnings captured if extraction quality is imperfect
New MCP service: Document Processing MCP Server

You can either:

make this a new MCP server
or make it a local tool service inside the ADK app

My recommendation:

For the demo, make it a local service first unless you specifically want to showcase document services as reusable infrastructure.

Why:

easier to build
less moving parts
lower latency
easier for a junior engineer

If you want a cleaner long-term architecture, then expose it behind MCP later.

v1 recommendation
Document Processing = local tool/helper
Knowledge / Policy / Workspace remain MCP servers

That is the best tradeoff.

New tool contracts for document processing

Whether local or MCP, define these tool contracts.

register_source_document

Purpose: attach uploaded PDF to the project

Input:

{
  "project_id": "rfp_001",
  "file_name": "Acme_Bank_RFP.pdf",
  "mime_type": "application/pdf",
  "file_path": "demo_data/rfp/source/acme_bank_rfp.pdf"
}

Output:

{
  "doc_id": "rfp_doc_001",
  "status": "registered"
}
extract_pdf_text

Purpose: extract page text and preserve page numbers

Input:

{
  "doc_id": "rfp_doc_001"
}

Output:

{
  "pages": [
    {
      "page_number": 1,
      "text": "Request for Proposal..."
    },
    {
      "page_number": 2,
      "text": "Acme Bank is a North American..."
    }
  ],
  "extraction_quality": "good",
  "warnings": []
}
detect_section_candidates

Purpose: identify likely headings and section ranges

Input:

{
  "doc_id": "rfp_doc_001",
  "pages": [...]
}

Output:

{
  "sections": [
    {
      "section_id": "sec_001",
      "title": "Introduction",
      "start_page": 1,
      "end_page": 1
    },
    {
      "section_id": "sec_002",
      "title": "Background",
      "start_page": 2,
      "end_page": 2
    }
  ]
}
extract_submission_rules

Purpose: pull submission constraints from the PDF

Input:

{
  "doc_id": "rfp_doc_001",
  "sections": [...]
}

Output:

{
  "submission_rules": {
    "required_format": "pdf",
    "max_pages": 20,
    "must_include_executive_contact": true
  }
}
extract_evaluation_criteria

Purpose: pull scoring criteria if present

Input:

{
  "doc_id": "rfp_doc_001",
  "sections": [...]
}

Output:

{
  "evaluation_criteria": [
    {
      "name": "technical_fit",
      "weight": 0.3
    },
    {
      "name": "security_and_compliance",
      "weight": 0.25
    }
  ]
}
Updated session-state schema

You now need to expand rfp_input.

Old
{
  "rfp_input": {
    "source_documents": [],
    "attachments": []
  }
}
New
{
  "rfp_input": {
    "source_documents": [
      {
        "doc_id": "rfp_doc_001",
        "doc_type": "rfp_main",
        "file_name": "acme_bank_rfp.pdf",
        "mime_type": "application/pdf",
        "ingestion_status": "parsed"
      }
    ],
    "extracted_pages": [
      {
        "page_number": 1,
        "text": "Request for Proposal..."
      }
    ],
    "section_candidates": [
      {
        "section_id": "sec_001",
        "title": "Introduction",
        "start_page": 1,
        "end_page": 1
      }
    ],
    "tables": [],
    "submission_constraints_raw": [],
    "issuer_questions_raw": [],
    "extraction_warnings": []
  }
}

This gives Intake a much better base.

Updated role of Intake Agent

The Intake Agent should no longer parse raw PDF directly.

Instead, it should read:

extracted pages
section candidates
extracted rules
evaluation criteria

and then perform:

requirement classification
mandatory section detection
risk extraction
open question extraction

So Intake becomes more reliable and easier to reason about.

New Intake inputs
rfp_input.extracted_pages
rfp_input.section_candidates
rfp_input.submission_constraints_raw
rfp_input.extraction_warnings
Intake output remains
rfp_analysis.requirements
rfp_analysis.mandatory_sections
rfp_analysis.submission_rules
rfp_analysis.open_questions
rfp_analysis.risks
Updated workflow
New stage sequence
1. document_ingestion
2. intake
3. evidence_gathering
4. drafting
5. governance_review
6. final_assembly
7. publish
New happy path
Upload PDF
→ Document Ingestion Agent registers and parses PDF
→ Intake Agent extracts requirements
→ Evidence Agent gathers approved support
→ Solution Agent drafts sections
→ Governance Agent validates and blocks one issue
→ Solution Agent revises
→ Governance Agent clears
→ Editor Agent assembles final response
→ Publish
UI changes

The UI only needs a few adjustments.

Header

Add:

source file name
ingestion status
Left timeline

Add new first stage:

Document Ingestion
Right shared memory panel

Add one summary card:

Pages parsed
optional Extraction warnings
Center tabs

Keep your four main tabs:

Drafting Board
Governance
Final Response
Readable Response

But add a lightweight pre-analysis state:

when document ingestion is running, Draft/Evidence/Governance can be disabled or partially empty
Optional new subview

You may want a very small Source drawer or tab, but I would not make it a main tab in v1.

A drawer is enough:

file info
detected sections
page count
extraction warnings

That keeps the main UI clean.