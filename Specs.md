

📘 RFP Multi-Agent System — Architecture Brief
1. System Overview
Objective
Build a multi-agent RFP response system that demonstrates:
Shared memory collaboration across agents
Agentic governance with enforceable controls
A polished, real-time UI using A2UI
Core Idea
Instead of a single LLM generating an answer, this system uses specialized agents collaborating over shared state, with governance enforcing correctness and compliance.

2. High-Level Architecture
User (A2UI Frontend)
        │
        ▼
ADK Orchestrator App (Core Runtime)
 ├── Coordinator Agent
 ├── Intake Agent
 ├── Evidence Agent
 ├── Solution Agent
 ├── Governance Agent
 └── Editor Agent
        │
        ▼
Shared Session State (Single Source of Truth)
        │
        ▼
MCP Layer (External Services)
 ├── Knowledge MCP Server
 ├── Policy MCP Server
 └── Workspace MCP Server
Key Principles
ADK = orchestration + shared memory
MCP = reusable enterprise services
A2UI = visualization layer
Session State = collaboration backbone

3. Core Components
3.1 ADK Orchestrator App
Responsibilities
Manages agent lifecycle
Maintains session state
Controls workflow progression
Emits UI events (A2UI)
Tech
Python ADK
InMemorySessionService (v1)
Streaming enabled

3.2 Agents
Coordinator Agent
Controls workflow
Routes between agents
Handles blockers and approvals
Intake Agent
Parses RFP
Extracts requirements and rules
Evidence Agent
Retrieves approved content (via MCP)
Builds evidence workspace
Solution Agent
Drafts response sections
Uses only approved evidence
Governance Agent
Validates claims and compliance
Blocks unsafe content
Creates approval workflows
Editor Agent
Assembles final response
Calculates readiness

3.3 Shared Session State
Purpose
Single collaboration layer across all agents.
Structure (Top-Level)
{
  "project": {},
  "rfp_input": {},
  "rfp_analysis": {},
  "evidence_workspace": {},
  "solution_workspace": {},
  "governance": {},
  "workflow": {},
  "ui_state": {},
  "final_output": {}
}
Key Idea
All agents read/write structured fields
No agent-to-agent messaging
Collaboration happens via state mutation

3.4 MCP Servers
1. Knowledge MCP Server
Handles:
Evidence retrieval
Approved claims
Customer references
Certifications
2. Policy MCP Server
Handles:
Claim validation
Reference policy
Compliance checks
Approval triggers
3. Workspace MCP Server
Handles:
Project persistence
Draft storage
Governance findings
Audit logs
Publish actions

4. Data Strategy (Tier 2)
Approach
Hybrid:
Structured fixtures + small curated corpus
Datasets
Knowledge Corpus
10–15 documents
Tagged + chunked
Approved metadata
Includes intentional gaps
Policy Fixtures
Allowed certifications
Banned claims
Reference rules
Mandatory sections
Workspace Seed
1 sample RFP project
Section templates
Sample drafts + findings

5. UI Architecture (A2UI)
5.1 Layout
Persistent Regions
Header
Left Rail: Workflow Timeline
Right Rail: Shared Memory Snapshot
Center Workspace (Tabbed)
Draft
Evidence
Governance
Final Response

5.2 UI Behavior
Always Visible
Current agent
Current stage
Memory summary
Focus Area
One tab at a time
Interaction Model
UI emits events → Coordinator handles → State updates → UI re-renders

6. Workflow Execution
6.1 Happy Path
Intake
 → Evidence
 → Drafting
 → Governance
 → Final Assembly
 → Publish

6.2 Governance Block Path
Drafting
 → Governance (block)
 → Revision (Solution)
 → Governance (re-check)

6.3 Approval Path
Governance
 → Approval Required
 → Human Decision
 → Continue OR Revise

6.4 Publish Path
Final Assembly
 → Readiness Check
 → User Confirm
 → Publish

7. State Transition Model
Stages
intake
evidence_gathering
drafting
governance_review
final_assembly
publish
Status Values
not_started
in_progress
completed
blocked

8. Governance Model
Layers
1. Retrieval Control
Only approved evidence returned
2. Draft Validation
Unsupported claims blocked
3. Approval Workflow
Human required for exceptions
4. Final Readiness Gate
Must satisfy:
all sections present
no blockers
approvals complete
submission compliant

9. Event Model
Example Event
{
  "event_type": "state_update",
  "actor": "governance_agent",
  "summary": "Blocked Security section"
}
Event Types
stage_changed
state_update
finding_created
approval_requested
draft_saved
published

10. UI Event Contract
Example
{
  "event_type": "ui.action.redraft_section",
  "section_id": "security"
}
Categories
workflow control
navigation
editing
approvals
publishing

11. Failure Modes
Key Scenarios
Evidence gap
→ create gap, do not fabricate
Governance block
→ halt workflow
Approval pending
→ require human input
MCP failure
→ halt + retry option
Early publish attempt
→ deny + show unmet criteria

12. Demo Script (7–10 min)
Flow
Load RFP
Run workflow
Show intake → memory populated
Show evidence → claims + gaps
Show draft sections appear
Governance blocks one section
Revise and clear
Show final readiness
Publish
Key messages
“Agents collaborate through shared memory”
“Governance enforces correctness”
“System knows when it doesn’t know”
“Human control is built-in”

13. Implementation Plan
Phase 1 — Backend skeleton
ADK app
session state
coordinator
stub agents
Phase 2 — MCP services
workspace
knowledge
policy
Phase 3 — Agents
implement each agent spec
wire tools
Phase 4 — UI (A2UI)
layout
tabs
event handling
Phase 5 — Demo data
curated corpus
policy rules
sample RFP
Phase 6 — Demo choreography
happy path
blocker path

14. Non-Goals (Important)
No full production infra
No large-scale RAG system
No multi-tenant architecture
No advanced auth model
This is a demo system with credible architecture, not a production build.

15. Key Design Decisions Recap
✅ ADK for orchestration
✅ Shared session state for collaboration
✅ MCP for enterprise tools
✅ A2UI for UI
✅ Tier 2 data strategy
✅ Tabbed UI (not 5 panels)
✅ Governance as first-class agent

16. Final Mental Model
Explain the system like this:
Coordinator = project manager
Agents = SMEs
Session state = shared workspace
MCP = enterprise systems
Governance = compliance/legal
UI = control tower

17. What the Junior Engineer Should Do First
Implement session state schema
Build Coordinator + Intake
Stub MCP services
Add Evidence + Solution
Add Governance (critical)
Add Editor
Build UI shell
Wire events
Add demo data
Run full flow

If you want, next I can:
turn this into a repo structure + file scaffolding
or generate starter ADK code + MCP server stubs
or create a presentation narrative aligned to this architecture
Just tell me 👍

