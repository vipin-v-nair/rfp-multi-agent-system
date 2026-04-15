1. Intake Agent Output
Purpose

Convert raw RFP into structured shared memory

Output (rfp_analysis)
{
  "requirements": [
    {
      "requirement_id": "req_001",
      "category": "executive_summary",
      "description": "Provide an executive summary of the proposed approach."
    },
    {
      "requirement_id": "req_002",
      "category": "technical_approach",
      "description": "Describe AI-powered solution, integrations, and deployment model."
    },
    {
      "requirement_id": "req_003",
      "category": "security",
      "description": "Describe encryption, hosting controls, certifications, and compliance posture."
    },
    {
      "requirement_id": "req_004",
      "category": "implementation",
      "description": "Provide phased rollout plan and operating model."
    },
    {
      "requirement_id": "req_005",
      "category": "pricing",
      "description": "Provide pricing assumptions and commercial model."
    },
    {
      "requirement_id": "req_006",
      "category": "references",
      "description": "Provide relevant customer references."
    }
  ],
  "mandatory_sections": [
    "executive_summary",
    "technical_approach",
    "security",
    "implementation_plan",
    "pricing_assumptions"
  ],
  "submission_rules": {
    "max_pages": 20,
    "format": "pdf",
    "must_include_security_section": true
  },
  "open_questions": [
    "What deployment model does Acme Bank prefer?",
    "Are there specific regulatory frameworks beyond standard banking controls?"
  ],
  "risks": [
    {
      "risk_id": "risk_001",
      "description": "Security expectations may require clarification for regulated workloads."
    }
  ]
}
UI impact

Right panel updates:

Requirements: 6
Gaps: 0

Timeline:

“Intake extracted 6 requirements”


2. Evidence Agent Output
Purpose

Populate approved knowledge workspace

Output (evidence_workspace)
{
  "approved_claims": [
    {
      "claim_id": "claim_001",
      "text": "The platform supports encryption at rest and in transit for supported deployments.",
      "category": "security"
    },
    {
      "claim_id": "claim_002",
      "text": "Supported deployment patterns include secure cloud architectures with access controls, audit logging, and network isolation controls.",
      "category": "security"
    },
    {
      "claim_id": "claim_003",
      "text": "A phased implementation approach begins with discovery, pilot deployment, controlled rollout, and operational optimization.",
      "category": "implementation"
    }
  ],
  "customer_references": [
    {
      "reference_id": "ref_001",
      "display_name": "Tier-1 North American Bank",
      "usage": "anonymized_only"
    }
  ],
  "certifications": [
    {
      "name": "ISO 27001"
    },
    {
      "name": "SOC 2 Type II"
    }
  ],
  "gaps": [
    {
      "gap_id": "gap_001",
      "category": "security",
      "description": "No approved PCI certification found"
    }
  ]
}
UI impact

Right panel:

Evidence matched: 3
Gaps: 1

Evidence tab:

shows approved claims
shows PCI gap
Narration moment

“This is where the system knows what it can and cannot say.”

3. Solution Agent Output (First Draft — WITH ERROR)
Purpose

Draft sections using shared memory

Output (solution_workspace.section_drafts)
Security section (intentionally flawed)
{
  "section_id": "security",
  "version": 1,
  "status": "drafted",
  "content": "The proposed solution is PCI certified and has been deployed across multiple top-10 US banks. The platform supports encryption at rest and in transit and includes access controls and audit logging."
}
Technical section (valid)
{
  "section_id": "technical_approach",
  "version": 1,
  "status": "drafted",
  "content": "The platform supports AI-assisted customer service workflows including agent assist and knowledge retrieval. A phased implementation approach begins with discovery and progresses through pilot and rollout."
}
UI impact

Draft tab:

shows all sections drafted
security section looks “fine” to a human

Right panel:

Draft completeness: 5/5


4. Governance Agent Output (BLOCKER)
Purpose

Enforce correctness

Output (governance)
{
  "findings": [
    {
      "finding_id": "gov_001",
      "section_id": "security",
      "severity": "high",
      "type": "unsupported_claim",
      "span_text": "PCI certified",
      "message": "No approved evidence supports this certification claim.",
      "recommended_fix": "Remove or replace with approved certification language."
    },
    {
      "finding_id": "gov_002",
      "section_id": "security",
      "severity": "high",
      "type": "unsupported_customer_reference",
      "span_text": "top-10 US banks",
      "message": "Customer references must be anonymized and pre-approved.",
      "recommended_fix": "Replace with approved anonymized reference phrasing."
    }
  ],
  "blocked_items": [
    {
      "item_type": "section",
      "item_id": "security",
      "reason": "unsupported_claims"
    }
  ],
  "approvals_required": [],
  "submission_compliance": {
    "status": "pending"
  }
}
UI impact
🔥 Key demo moment

Governance tab:

shows red findings
highlights exact phrases

Right panel:

Open findings: 2
Blockers: 1

Toast:

“Security section blocked due to unsupported claim”

5. Solution Agent Output (Revision)
Purpose

Fix based on governance feedback

Output
{
  "section_id": "security",
  "version": 2,
  "status": "revised",
  "content": "The proposed solution supports secure deployment patterns appropriate for enterprise environments, including encryption at rest and in transit for supported deployments, as well as access controls, audit logging, and network isolation controls."
}
Key difference

Removed:

PCI claim
top-10 banks reference

Uses:

only approved claims


6. Governance Agent Output (Resolved)
{
  "findings": [
    {
      "finding_id": "gov_001",
      "status": "resolved"
    },
    {
      "finding_id": "gov_002",
      "status": "resolved"
    }
  ],
  "blocked_items": [],
  "approvals_required": [],
  "submission_compliance": {
    "status": "passed"
  }
}
UI impact

Right panel:

Open findings: 0
Blockers: 0

Timeline:

“Governance resolved blocker”


7. Optional Approval Path Output
Scenario: Reference needs approval
Governance adds approval
{
  "approvals_required": [
    {
      "approval_request_id": "apr_001",
      "item_type": "reference_usage",
      "status": "pending",
      "description": "Use of anonymized Tier-1 bank reference"
    }
  ]
}
After approval
{
  "approvals_required": [],
  "approved_items": [
    {
      "item_type": "reference_usage",
      "approved": true
    }
  ]
}
UI moment
Governance tab → approval queue
User clicks approve
Workflow resumes


8. Editor Agent Output (Final Assembly)
Output (final_output)
{
  "response_draft": "FULL TEXT (as shown earlier)",
  "readiness": {
    "all_sections_present": true,
    "all_blockers_resolved": true,
    "approvals_complete": true,
    "submission_compliant": true
  }
}
UI impact

Final tab:

full response visible

Right panel:

all green


9. Publish Output
{
  "publish_status": "published",
  "artifact_id": "artifact_001"
}

UI:

toast: “Published successfully”
timeline complete