## Project Overview
This is a demo about a multi agent system. The demo takes an RFP pdf document as an input and formulates a response use multiple specialized agents. These agents share the state of the workflow through session state. The demo is intended to demonstrate the end to end capability of GCP’s new Gemini Enterprise Agent Platform. Some of the key capabilities include Agent Engine, Agent Registry, Agent Gateway, Traces, Topology, Custom MCP Servers and a jazzy UI with A2UI

## Tech Stack
- MCP 
- ADK
- A2UI
- Gemini Enterprise Agent Platform
- Gemini Enterprise Agent Gateway
- Gemini Enterprise Agent Registry
- Agent Engine
- Cloud Run
- Firestore

## Architecture
-  ├── a2ui_setup.py                 # A2UI component helpers for agent instructions                                                                                                                                                             
-  ├── agent_registry_lookup.py      # Resolves MCP server URLs from Agent Registry                                                                                                                                                              
-  ├── mcp_client.py                 # Shared MCP HTTP client utilities                                                                                                                                                                          
-  ├── state.py                      # Shared session state helpers
-  ├── threaded_mcp_toolset.py       # Thread-isolated MCP toolset — avoids anyio cancel scope errors in Agent Engine                                                                                                                                                                
-    │                                                       
-  ├── agents/                       # Multi-agent system                                                                                                                                                                                        
-     │   ├── coordinator.py            # Root agent — routes to sub-agents
-     │   ├── ingestion.py              # Parses and registers RFP documents
-     │   ├── intake.py                 # Extracts RFP requirements and criteria
-     │   ├── evidence.py               # Gathers evidence via Knowledge MCP
-     │   ├── solution.py               # Drafts solution sections
-     │   ├── governance.py             # Compliance review via Policy MCP
-     │   └── editor.py                 # Assembles final response
-     │
- ├── mcp_servers/                  # Cloud Run MCP server implementations
-     │   ├── knowledge/                # rfp-mcp-knowledge: evidence/benchmarks lookup
-     │   ├── policy/                   # rfp-mcp-policy: compliance validation
-     │   └── workspace/                # rfp-mcp-workspace: draft storage
-     │
- ├── demo_data/                    # Sample RFP documents for testing
-     │   └── rfp/
-     │       └── uploads/
-     │           └── acme_rfp.pdf
-     │
- ├── deploy_staging/               # Auto-generated staging dir (git-ignored)
-     │
- ├── deploy_agent.sh               # Deploy/update agent to Vertex AI Agent Engine
- ├── deploy_agent_with_gateway.sh  # Deploy NEW engine with Agent Gateway binding
- ├── deploy_mcp.sh                 # Deploy MCP servers to Cloud Run
- ├── deploy_ui.sh                  # Deploy FastAPI UI to Cloud Run
- ├── deploy_with_gateway.py        # Python deploy logic (called by deploy_agent_with_gateway.sh)
- ├── bind_gateway.py               # REST-based gateway binding utility
- ├── start_local_agent.sh          # Run ADK agent server locally (port 8080)
- └── start_local_ui.sh             # Run FastAPI UI locally (port 8001)


    - Agent Engine: Deployed via deploy_agent_with_gateway.sh (new engine + gateway) or deploy_agent.sh (in-place update). The gateway deploy uses client.agent_engines.create() with source_packages — NOT adk deploy agent_engine —
    because the ADK CLI doesn't support agent_gateway_config at create time.
    - MCP tools: Both evidence.py and governance.py use ThreadedMCPToolset from threaded_mcp_toolset.py to avoid anyio CancelScope errors in Agent Engine. Each MCP call runs in an isolated thread with its own event loop.
    - Resuming on a new machine: the active Agent Engine ID is NOT in this repo (it lives in .env which is gitignored). To retrieve it on a fresh clone, run:
        gcloud ai reasoning-engines list --region=us-central1 --project=$(gcloud config get-value project)
      Copy the resource name of the rfp_system engine into .env as AGENT_ENGINE_ID.
    - Agent Gateway name: rfp-agent-gateway-2 (us-central1). Set AGENT_GATEWAY_NAME=rfp-agent-gateway-2 in .env.


## Coding Rules
- Make sure to include checks for mypy-diff failures since I need to commit this code to Open source git repos
- Make sure the code passes pre commit checks
- Always include unit test cases for all you functionality
- Always use .env for storing sensitive environment variables
- Since this code will be checked into public git always sanitize the code for sensitive environment and credentials
- Make sure that you follow all the google coding standards and lint checks
- Remind the user to check in the code after every successful deployment

## Design System
    - Ensure a modular design that we allow for development and testing locally and an easy migration / deployment to GCP once the local tests are successful
    - Follow ShadCN patterns wherever possible 

## Commands
Run the following commands whenever you need
 - gcloud auth login
 - gcloud auth application-default login

