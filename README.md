# RFP Multi-Agent System

A multi-agent system built with the [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) that autonomously processes RFP documents and generates compliant proposals. A team of specialised agents (Document Ingestion, Evidence, Solution, Governance, Editor) collaborate via shared Firestore state, using MCP (Model Context Protocol) servers for tool access.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  FastAPI UI (Cloud Run)                  │
│              A2UI interactive dashboard                  │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP / SSE
┌───────────────────────▼─────────────────────────────────┐
│           Vertex AI Agent Engine                         │
│   Coordinator → Ingestion → Evidence → Solution          │
│              → Governance → Editor                       │
└───────┬──────────────────────────────┬───────────────────┘
        │ MCP (ThreadedMCPToolset)     │ Firestore state
┌───────▼───────────────────────────┐  │
│   MCP Servers (Cloud Run)         │  │
│   • rfp-mcp-knowledge             │  │
│   • rfp-mcp-policy                │  │
│   • rfp-mcp-workspace             │  │
└───────────────────────────────────┘  │
┌──────────────────────────────────────▼───────────────────┐
│                  Cloud Firestore                          │
│          Session state & workflow events                  │
└──────────────────────────────────────────────────────────┘
```

MCP server URLs are discovered at runtime from the **Vertex AI Agent Registry** (with `.env` fallback for local development).

---

## Prerequisites

| Requirement | Notes |
|---|---|
| **GCP Project** | With billing enabled |
| **Python 3.11+** | |
| **Git Bash / WSL** | Windows users need bash to run the `.sh` scripts |
| **`gcloud` CLI** | Installed and authenticated |
| **APIs enabled** | See below |

### Enable required GCP APIs

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  firestore.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  telemetry.googleapis.com \
  agentregistry.googleapis.com \
  --project=YOUR_PROJECT_ID
```

### Create a Firestore database

```bash
gcloud firestore databases create \
  --location=us-central1 \
  --project=YOUR_PROJECT_ID
```

---

## Local Setup

### 1. Clone and create virtual environment

```bash
git clone https://github.com/vipin-v-nair/rfp-multi-agent-system.git
cd rfp-multi-agent-system

python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows (Git Bash)
source .venv/Scripts/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Authenticate

```bash
gcloud auth application-default login
```

> **Windows note:** If your `gcloud` CLI has a Python conflict, run this from a standard Command Prompt or PowerShell rather than Git Bash.

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```
GOOGLE_CLOUD_PROJECT=your-project-id
GCP_REGION=us-central1
```

Leave `AGENT_ENGINE_ID` and MCP URLs blank for now — you will fill these in after deployment.

### 4. Start local MCP servers

The MCP servers run as separate processes on ports 3001–3003. You need three terminals:

```bash
# Terminal 1 — Knowledge MCP server
MCP_SERVER=knowledge .venv/bin/python mcp_main.py   # Linux/Mac
MCP_SERVER=knowledge .venv/Scripts/python mcp_main.py  # Windows

# Terminal 2 — Policy MCP server
MCP_SERVER=policy .venv/bin/python mcp_main.py

# Terminal 3 — Workspace MCP server
MCP_SERVER=workspace .venv/bin/python mcp_main.py
```

### 5. Start the agent server and UI

```bash
# Terminal 4 — ADK agent API server (port 8080)
./start_local_agent.sh

# Terminal 5 — FastAPI UI (port 8001)
./start_local_ui.sh
```

Open [http://localhost:8001](http://localhost:8001) and upload `demo_data/rfp/source/acme_rfp.pdf` to test.

---

## Cloud Deployment

### Step 1: Deploy the MCP servers to Cloud Run

```bash
./deploy_mcp.sh
```

This deploys three Cloud Run services and prints their URLs. Copy the output URLs into your `.env`:

```
KNOWLEDGE_MCP_URL=https://rfp-mcp-knowledge-xxxx-uc.a.run.app/mcp
POLICY_MCP_URL=https://rfp-mcp-policy-xxxx-uc.a.run.app/mcp
WORKSPACE_MCP_URL=https://rfp-mcp-workspace-xxxx-uc.a.run.app/mcp
```

### Step 2: Register MCP servers in Vertex AI Agent Registry

The agents discover MCP server URLs from the Agent Registry at runtime. Register each server once via the Cloud Console:

1. Go to **Cloud Console → Vertex AI → Agent Builder → Agent Registry → MCP Servers**
2. Select location **Global**
3. Register each server using the values below, uploading the corresponding `toolspecs/` JSON file when prompted:

| Display Name | URL | Toolspec file |
|---|---|---|
| `rfp-mcp-knowledge` | `KNOWLEDGE_MCP_URL` from `.env` | `toolspecs/toolspec_knowledge.json` |
| `rfp-mcp-policy` | `POLICY_MCP_URL` from `.env` | `toolspecs/toolspec_policy.json` |
| `rfp-mcp-workspace` | `WORKSPACE_MCP_URL` from `.env` | `toolspecs/toolspec_workspace.json` |

> If the Agent Registry is unavailable, the agents fall back to the MCP URLs in `.env` automatically.

### Step 3: Deploy the agents to Vertex AI Agent Engine

```bash
./deploy_agent.sh
```

On the **first run** this creates a new Reasoning Engine. The script prints the Engine ID — copy it into your `.env`:

```
AGENT_ENGINE_ID=projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID
```

Subsequent runs of `./deploy_agent.sh` will perform fast in-place updates to the same engine.

### Step 4: Deploy the UI to Cloud Run

```bash
./deploy_ui.sh
```

The script reads `AGENT_ENGINE_ID` from `.env` and wires the UI to your cloud agents. When complete it prints the Cloud Run service URL.

---

## Project Structure

```
rfp-multi-agent-system/
├── agents/                  # ADK LlmAgent definitions
│   ├── coordinator.py       # Root orchestrator agent
│   ├── document_ingestion.py
│   ├── evidence.py          # Uses rfp-mcp-knowledge via Agent Registry
│   ├── governance.py        # Uses rfp-mcp-policy via Agent Registry
│   ├── solution.py
│   ├── editor.py
│   └── intake.py
├── mcp_servers/             # FastMCP server implementations
│   ├── knowledge_server.py  # get_evidence, get_approved_claims
│   ├── policy_server.py     # validate_claim, check_compliance
│   └── workspace_server.py  # save_draft, get_draft, log_event, publish_response
├── mcp_stubs/               # Local mock implementations (used without Cloud Run)
├── toolspecs/               # MCP tool specs for Agent Registry registration
├── demo_data/               # Fixture data (knowledge base, policy, RFP PDFs)
├── apps/rfp_system/         # ADK app entry point for local adk api_server
├── agent_registry_lookup.py # Resolves MCP URLs from Agent Registry with env fallback
├── threaded_mcp_toolset.py  # Custom BaseToolset — workaround for anyio cancel scope
│                            # bug in McpToolset on Agent Engine (see code comments)
├── mcp_client.py            # Low-level MCP SDK helpers (thread-isolated event loops)
├── mcp_main.py              # Local MCP server runner (selects server via MCP_SERVER env var)
├── app.py                   # FastAPI UI server
├── state.py                 # Firestore state manager
├── a2ui_setup.py            # A2UI dashboard configuration helpers
├── register_mcp_servers.py  # Utility to verify Agent Registry MCP server status
├── deploy_agent.sh          # Deploy agents → Vertex AI Agent Engine
├── deploy_mcp.sh            # Deploy MCP servers → Cloud Run
├── deploy_ui.sh             # Deploy UI → Cloud Run
├── start_local_agent.sh     # Start local ADK API server
├── start_local_ui.sh        # Start local FastAPI UI
├── requirements.txt         # Agent + UI dependencies
├── requirements-mcp.txt     # MCP server dependencies (deployed separately)
├── Dockerfile               # UI container image
└── Dockerfile.mcp           # MCP server container image
```

---

## Key Technical Notes

### MCP + Agent Engine compatibility
The standard ADK `McpToolset` fails on Vertex AI Agent Engine due to an anyio cancel scope task mismatch. `ThreadedMCPToolset` (in `threaded_mcp_toolset.py`) works around this by running each MCP call in an isolated thread with its own event loop, so cancel scopes never cross task boundaries.

### Agent Registry fallback
`agent_registry_lookup.py` performs a single `list` call to the Agent Registry on startup and caches all server URLs. If the registry is unreachable, it falls back to the `*_MCP_URL` environment variables — so local development works without any registry setup.

### Telemetry
Agent Engine traces appear in the **Traces** tab of the Agent Engine Console. This requires the `telemetry.googleapis.com` API to be enabled (separate from the Cloud Trace API).

### Windows development
- All `.sh` scripts require **Git Bash** or **WSL**
- The scripts auto-detect `.venv/Scripts/` vs `.venv/bin/` for cross-platform venv activation
- If `gcloud` fails in Git Bash due to a Python conflict, run `gcloud` commands from PowerShell or Command Prompt instead
