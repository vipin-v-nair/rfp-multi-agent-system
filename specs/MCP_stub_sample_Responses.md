1. Mock MCP Server Responses

I’ll structure these in the order they appear during the demo.

Step 0 — Workspace MCP: Create Project
Request
{
  "tool": "create_project",
  "project_id": "rfp_001",
  "rfp_title": "Acme Bank Customer Service Transformation RFP",
  "issuer": "Acme Bank",
  "deadline": "2026-05-01",
  "created_by": "demo_user"
}
Response
{
  "project_id": "rfp_001",
  "status": "created",
  "created_at": "2026-04-15T18:00:00Z"
}
Step 1 — Workspace MCP: Log Project Init
Request
{
  "tool": "log_audit_event",
  "project_id": "rfp_001",
  "event_type": "project_initialized",
  "actor_type": "system",
  "actor_id": "coordinator_agent",
  "payload": {
    "message": "Project initialized for Acme Bank RFP."
  }
}
Response
{
  "status": "logged",
  "audit_event_id": "aud_001"
}
Step 2 — Knowledge MCP: Search Evidence for Security
Request
{
  "tool": "search_evidence",
  "project_id": "rfp_001",
  "query": "banking encryption hosting controls contact center ai",
  "filters": {
    "industry": ["banking"],
    "approval_status": ["approved"],
    "customer_safe": true
  },
  "top_k": 5
}
Response
{
  "results": [
    {
      "evidence_id": "ev_001",
      "doc_id": "doc_002",
      "chunk_id": "chunk_002",
      "title": "Security Controls",
      "snippet": "The platform supports encryption at rest and encryption in transit for supported deployments.",
      "claim_types": ["security"],
      "approval_status": "approved",
      "customer_safe": true
    },
    {
      "evidence_id": "ev_002",
      "doc_id": "doc_002",
      "chunk_id": "chunk_003",
      "title": "Hosting Controls",
      "snippet": "Supported deployment patterns include secure cloud architectures with access controls, audit logging, and network isolation controls.",
      "claim_types": ["security", "hosting"],
      "approval_status": "approved",
      "customer_safe": true
    }
  ]
}
Step 3 — Knowledge MCP: Search Evidence for Implementation
Request
{
  "tool": "search_evidence",
  "project_id": "rfp_001",
  "query": "phased rollout implementation plan pilot deployment controlled rollout",
  "filters": {
    "approval_status": ["approved"]
  },
  "top_k": 5
}
Response
{
  "results": [
    {
      "evidence_id": "ev_003",
      "doc_id": "doc_003",
      "chunk_id": "chunk_004",
      "title": "Implementation Approach",
      "snippet": "A phased implementation approach is recommended, beginning with discovery, pilot deployment, controlled rollout, and operational optimization.",
      "claim_types": ["implementation"],
      "approval_status": "approved",
      "customer_safe": true
    }
  ]
}
Step 4 — Knowledge MCP: Search Customer References
Request
{
  "tool": "search_customer_references",
  "project_id": "rfp_001",
  "industry": "banking",
  "region": "north_america",
  "capabilities": ["contact_center_ai", "agent_assist"],
  "top_k": 3
}
Response
{
  "references": [
    {
      "reference_id": "ref_001",
      "display_name": "Tier-1 North American Bank",
      "anonymized": true,
      "allowed_verbatim_usage": false,
      "allowed_summary_usage": true,
      "approved_talking_points": [
        "Improved agent-assist experience",
        "Supported modernization of service operations"
      ],
      "restrictions": [
        "Do not reveal customer name",
        "Do not claim quantitative outcomes unless separately approved"
      ]
    }
  ]
}
Step 5 — Knowledge MCP: Get Certifications
Request
{
  "tool": "get_certifications",
  "project_id": "rfp_001",
  "requested_tags": ["iso27001", "soc2", "pci"]
}
Response
{
  "certifications": [
    {
      "cert_id": "cert_001",
      "name": "ISO 27001",
      "status": "approved_for_use"
    },
    {
      "cert_id": "cert_002",
      "name": "SOC 2 Type II",
      "status": "approved_for_use"
    }
  ]
}

Note: No PCI certification returned.

Step 6 — Knowledge MCP: List Missing Evidence
Request
{
  "tool": "list_missing_evidence",
  "project_id": "rfp_001",
  "requirement_ids": ["req_003"]
}
Response
{
  "gaps": [
    {
      "requirement_id": "req_003",
      "gap_type": "no_approved_claim",
      "recommended_action": "do_not_claim_unverified_certification"
    }
  ]
}
Step 7 — Workspace MCP: Save Initial Security Draft
Request
{
  "tool": "save_draft_section",
  "project_id": "rfp_001",
  "section_id": "security",
  "content": "The proposed solution is PCI certified and has been deployed across multiple top-10 US banks. The platform supports encryption at rest and in transit and includes access controls and audit logging.",
  "author_type": "agent",
  "author_id": "solution_agent",
  "source_evidence_ids": ["ev_001", "ev_002"],
  "version_note": "Initial draft"
}
Response
{
  "draft_version_id": "dv_001",
  "section_id": "security",
  "version_number": 1,
  "saved_at": "2026-04-15T18:03:00Z"
}
Step 8 — Policy MCP: Validate Security Section Claims
Request
{
  "tool": "validate_section_claims",
  "project_id": "rfp_001",
  "section_id": "security",
  "text": "The proposed solution is PCI certified and has been deployed across multiple top-10 US banks. The platform supports encryption at rest and in transit and includes access controls and audit logging.",
  "evidence_ids": ["ev_001", "ev_002"]
}
Response
{
  "status": "failed",
  "findings": [
    {
      "finding_id": "gov_001",
      "severity": "high",
      "type": "unsupported_claim",
      "span_text": "PCI certified",
      "message": "No approved certification evidence matched this claim.",
      "recommended_fix": "Remove or replace with approved certification language."
    },
    {
      "finding_id": "gov_002",
      "severity": "high",
      "type": "unsupported_customer_reference",
      "span_text": "top-10 US banks",
      "message": "Reference quantity and customer class are not supported by approved references.",
      "recommended_fix": "Use approved anonymized reference language."
    }
  ]
}
Step 9 — Policy MCP: Check Reference Policy
Request
{
  "tool": "check_reference_policy",
  "project_id": "rfp_001",
  "text": "deployed across multiple top-10 US banks"
}
Response
{
  "status": "failed",
  "violations": [
    {
      "type": "disallowed_customer_reference_pattern",
      "span_text": "top-10 US banks",
      "message": "Only approved anonymized reference language may be used."
    }
  ]
}
Step 10 — Workspace MCP: Append Governance Findings
Request
{
  "tool": "append_governance_finding",
  "project_id": "rfp_001",
  "finding": {
    "finding_id": "gov_001",
    "section_id": "security",
    "severity": "high",
    "type": "unsupported_claim",
    "message": "No approved certification evidence matched this claim."
  }
}
Response
{
  "status": "stored",
  "finding_record_id": "gf_001"
}

Second finding:

{
  "status": "stored",
  "finding_record_id": "gf_002"
}
Step 11 — Workspace MCP: Save Revised Security Draft
Request
{
  "tool": "save_draft_section",
  "project_id": "rfp_001",
  "section_id": "security",
  "content": "The proposed solution supports secure deployment patterns appropriate for enterprise environments, including encryption at rest and in transit for supported deployments, as well as access controls, audit logging, and network isolation controls.",
  "author_type": "agent",
  "author_id": "solution_agent",
  "source_evidence_ids": ["ev_001", "ev_002"],
  "version_note": "Revised after governance review"
}
Response
{
  "draft_version_id": "dv_002",
  "section_id": "security",
  "version_number": 2,
  "saved_at": "2026-04-15T18:05:00Z"
}
Step 12 — Policy MCP: Re-Validate Revised Security Section
Request
{
  "tool": "validate_section_claims",
  "project_id": "rfp_001",
  "section_id": "security",
  "text": "The proposed solution supports secure deployment patterns appropriate for enterprise environments, including encryption at rest and in transit for supported deployments, as well as access controls, audit logging, and network isolation controls.",
  "evidence_ids": ["ev_001", "ev_002"]
}
Response
{
  "status": "passed",
  "findings": []
}
Step 13 — Policy MCP: Check Mandatory Coverage
Request
{
  "tool": "check_mandatory_coverage",
  "project_id": "rfp_001",
  "required_sections": [
    "executive_summary",
    "technical_approach",
    "security",
    "implementation_plan",
    "pricing_assumptions"
  ],
  "draft_sections": {
    "executive_summary": "...",
    "technical_approach": "...",
    "security": "...",
    "implementation_plan": "...",
    "pricing_assumptions": "..."
  }
}
Response
{
  "status": "passed",
  "missing_sections": [],
  "coverage_score": 1.0
}
Step 14 — Policy MCP: Check Submission Compliance
Request
{
  "tool": "check_submission_compliance",
  "project_id": "rfp_001",
  "submission_rules": {
    "max_pages": 20,
    "required_format": "pdf",
    "must_include_executive_contact": true
  },
  "package_metadata": {
    "page_count": 12,
    "format": "pdf",
    "includes_executive_contact": true
  }
}
Response
{
  "status": "passed",
  "violations": []
}
Step 15 — Workspace MCP: Publish Response Bundle
Request
{
  "tool": "publish_response_bundle",
  "project_id": "rfp_001",
  "final_draft_version_ids": ["dv_exec_001", "dv_tech_001", "dv_002", "dv_impl_001", "dv_price_001"],
  "export_artifact_ids": ["art_pdf_001"]
}
Response
{
  "status": "published",
  "published_at": "2026-04-15T18:08:00Z"
}