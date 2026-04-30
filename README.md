# RFP Multi-Agent System

A demo of the **Gemini Enterprise Agent Platform** on Google Cloud. The system takes an RFP PDF as input and autonomously generates a compliant proposal using a pipeline of specialised agents. It showcases end-to-end capabilities including Agent Engine, Agent Registry, Agent Gateway, MCP servers, traces/topology, and an A2UI interactive dashboard.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI UI (Cloud Run)                       │
│              A2UI interactive dashboard                       │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP / SSE
┌───────────────────────────▼─────────────────────────────────┐
│              Vertex AI Agent Engine (rfp_system)              │
│                                                               │
│  Coordinator → Ingestion → Intake → Evidence                  │
│             → Solution → Governance → Editor                  │
└───────────┬──────────────────────────────────────────────────┘
            │ All outbound traffic
┌───────────▼──────────────────────────────────────────────────┐
│         Agent Gateway  (Agent-to-Anywhere egress proxy)       │
│      Governs & audits all agent → tool communication          │
└───────────┬──────────────────────────────────────────────────┘
            │ MCP (streamable-HTTP)
┌───────────▼──────────────────────────────────────────────────┐
│              MCP Servers  (Cloud Run)                         │
│         rfp-mcp-knowledge         │         rfp-mcp-policy          │
└──────────────────────────────────────────────────────────────┘

MCP server URLs are discovered at startup from Vertex AI Agent Registry.
Env-var fallback is used automatically for local development.
```

### Agent pipeline

| Agent | Role | MCP tool |
|---|---|---|
| Ingestion | Parses RFP PDF, extracts sections/criteria | — |
| Intake | Structures requirements and evaluation criteria | — |
| Evidence | Gathers supporting evidence and approved claims | `rfp-mcp-knowledge` |
| Solution | Drafts response sections | — |
| Governance | Reviews drafts for compliance | `rfp-mcp-policy` |
| Editor | Assembles and publishes final response | — |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agents | Google ADK (`LlmAgent`, `SequentialAgent`) |
| Model | Gemini 2.5 Pro (Vertex AI) |
| Runtime | Vertex AI Agent Engine (Reasoning Engine) |
| Egress governance | Vertex AI Agent Gateway (Agent-to-Anywhere) |
| MCP discovery | Vertex AI Agent Registry |
| MCP transport | MCP streamable-HTTP via `ThreadedMCPToolset` |
| MCP servers | FastMCP on Cloud Run |
| UI | FastAPI + A2UI |
| State | Cloud Firestore |
| Observability | Cloud Trace / OTel via Agent Engine telemetry |

---

## Prerequisites

| Requirement | Notes |
|---|---|
| GCP project with billing | — |
| Python 3.11+ | — |
| `gcloud` CLI | Authenticated (`gcloud auth login`) |
| Git Bash / WSL | Windows users — needed for `.sh` scripts |

### Enable required APIs

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  firestore.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
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

## Local Development

### 1. Clone and install

```bash
git clone https://github.com/vipin-v-nair/rfp-multi-agent-system.git
cd rfp-multi-agent-system

python -m venv .venv
source .venv/bin/activate          # Linux / macOS
# source .venv/Scripts/activate    # Windows (Git Bash)

pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Authenticate

```bash
gcloud auth application-default login
```

### 3. Configure environment

```bash
cp .env.example .env
```

Set at minimum:

```
GOOGLE_CLOUD_PROJECT=your-project-id
GCP_REGION=us-central1
```

Leave `AGENT_ENGINE_ID`, `AGENT_GATEWAY_NAME`, and MCP URLs blank until after cloud deployment.

### 4. Start local MCP servers

Each server runs on its own port (3001–3003). Open three terminals:

```bash
# Terminal 1 — Knowledge server (port 3001)
MCP_SERVER=knowledge .venv/bin/python mcp_main.py

# Terminal 2 — Policy server (port 3002)
MCP_SERVER=policy .venv/bin/python mcp_main.py

```

### 5. Start agent server and UI

```bash
# Terminal 4 — ADK agent API server (port 8080)
./start_local_agent.sh

# Terminal 5 — FastAPI UI (port 8001)
./start_local_ui.sh
```

Open [http://localhost:8001](http://localhost:8001) and upload `demo_data/rfp/source/acme_rfp.pdf`.

---

## Cloud Deployment

### Step 1 — Deploy MCP servers to Cloud Run

```bash
./deploy_mcp.sh
```

Deploys three Cloud Run services with session affinity enabled (prevents MCP session routing issues under autoscaling). Copy the printed URLs into `.env`:

```
KNOWLEDGE_MCP_URL=https://rfp-mcp-knowledge-xxxx-uc.a.run.app/mcp
POLICY_MCP_URL=https://rfp-mcp-policy-xxxx-uc.a.run.app/mcp
```

### Step 2 — Register MCP servers in Agent Registry

MCP server URLs are discovered at runtime via the Agent Registry. Register each server once through the Cloud Console:

1. Go to **Cloud Console → Vertex AI → Agent Builder → Agent Registry → MCP Servers**
2. Select location **us-central1**
3. For each server, click **Register** and fill in:

| Display Name | URL |
|---|---|
| `rfp-mcp-knowledge` | `KNOWLEDGE_MCP_URL` from `.env` |
| `rfp-mcp-policy` | `POLICY_MCP_URL` from `.env` |

Set protocol to **CUSTOM / HTTP_JSON / 2024-11-05** for all three.

> The agents fall back to the `*_MCP_URL` environment variables automatically when the registry is unreachable, so local development works without any registry setup.

### Step 3 — Create an Agent Gateway

The Agent Gateway acts as a **transparent egress proxy** — all outbound traffic from Agent Engine (to MCP servers, Vertex AI, Agent Registry) flows through it for governance and auditing.

1. Go to **Cloud Console → Network Services → Agent Gateway**
2. Click **Add gateway**, enter a name (e.g. `rfp-agent-gateway`), select region **us-central1**
3. Set mode to **Agent-to-Anywhere (egress)**
4. Click **Create**

Set `AGENT_GATEWAY_NAME` in `.env`:

```
AGENT_GATEWAY_NAME=rfp-agent-gateway
STAGING_BUCKET=gs://your-project-id-bucket
```

#### Grant IAM permissions

The Reasoning Engine service account needs permission to use the gateway, and the Agent Engine's runtime Workload Identity needs permission to read from Agent Registry:

```bash
PROJECT_ID=your-project-id
PROJECT_NUMBER=your-project-number

# Create custom role for gateway access
gcloud iam roles create AgentGatewayAccess \
  --project=${PROJECT_ID} \
  --title="Agent Gateway Access" \
  --permissions="networkservices.operations.get,networkservices.agentGateways.get,networkservices.agentGateways.use"

# Grant it to the Reasoning Engine SA
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
  --role="projects/${PROJECT_ID}/roles/AgentGatewayAccess"

# Grant Agent Registry read access to the Reasoning Engine SA
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
  --role="roles/agentregistry.viewer"
```

After the first deployment, also grant `roles/agentregistry.viewer` to the Agent Engine's Workload Identity Federation principal. Retrieve the principal from your project's IAM policy (it has the form `principalSet://agents.global.org-*.system.id.goog/...`) and grant via the IAM REST API or Cloud Console.

### Step 4 — Deploy Agent Engine

```bash
./deploy_agent.sh
```

On the **first run** this creates a new Reasoning Engine. Copy the printed engine ID into `.env`:

```
AGENT_ENGINE_ID=projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID
```

Subsequent runs of `./deploy_agent.sh` perform fast in-place updates to the same engine and re-bind the gateway automatically.

> **Note:** `deploy_agent_with_gateway.sh` / `deploy_with_gateway.py` create a brand-new engine with gateway config wired in at creation time. Use this when you need a fresh engine rather than an in-place update.

> **Warning:** Gateway binding is **permanent and cannot be undone**.

### Step 5 — Deploy the UI

```bash
./deploy_ui.sh
```

Reads `AGENT_ENGINE_ID` from `.env` and wires the FastAPI UI to your cloud agent. Prints the Cloud Run service URL when complete.

---

## Project Structure

```
rfp-multi-agent-system/
│
├── agents/                        # ADK LlmAgent definitions
│   ├── coordinator.py             # Root orchestrator
│   ├── document_ingestion.py      # PDF parsing and section extraction
│   ├── intake.py                  # Requirements and criteria extraction
│   ├── evidence.py                # Evidence gathering (rfp-mcp-knowledge)
│   ├── solution.py                # Draft section generation
│   ├── governance.py              # Compliance review (rfp-mcp-policy)
│   └── editor.py                  # Final response assembly
│
├── mcp_servers/                   # FastMCP server implementations (Cloud Run)
│   ├── knowledge_server.py        # get_evidence, get_approved_claims
│   ├── policy_server.py           # validate_claim, check_compliance
│   └── workspace_server.py        # save_draft, get_draft, log_event, publish_response (not wired — available for future use)
│
├── mcp_stubs/                     # Local mock MCP implementations (no Cloud Run needed)
├── toolspecs/                     # MCP tool JSON specs for Agent Registry registration
├── demo_data/                     # Fixture data: knowledge base, policy rules, sample RFPs
├── apps/rfp_system/               # ADK app entry point for local `adk api_server`
│
├── agent_registry_lookup.py       # Resolves MCP URLs from Agent Registry; env-var fallback
├── threaded_mcp_toolset.py        # Custom BaseToolset — isolates MCP calls in threads to
│                                  # avoid anyio cancel scope errors in Agent Engine
├── bind_gateway.py                # Binds an existing Agent Engine to an Agent Gateway
├── deploy_with_gateway.py         # Creates a new Agent Engine with gateway config at create time
│
├── mcp_main.py                    # Local MCP server runner (select server via MCP_SERVER)
├── mcp_client.py                  # Low-level MCP SDK helpers
├── app.py                         # FastAPI UI server
├── state.py                       # Firestore session state manager
├── a2ui_setup.py                  # A2UI dashboard configuration helpers
├── retry_llm.py                   # Gemini model reference with retry config
├── register_mcp_servers.py        # Verifies Agent Registry MCP server status
│
├── deploy_agent.sh                # In-place update deploy → Vertex AI Agent Engine
├── deploy_agent_with_gateway.sh   # New engine deploy with Agent Gateway binding
├── deploy_mcp.sh                  # Deploy MCP servers → Cloud Run (with session affinity)
├── deploy_ui.sh                   # Deploy FastAPI UI → Cloud Run
├── start_local_agent.sh           # Start local ADK API server (port 8080)
├── start_local_ui.sh              # Start local FastAPI UI (port 8001)
│
├── requirements.txt               # Agent + UI Python dependencies
├── requirements-mcp.txt           # MCP server dependencies (deployed separately)
├── Dockerfile                     # UI container image
└── Dockerfile.mcp                 # MCP server container image
```

---

## Key Technical Notes

### ThreadedMCPToolset
The standard ADK `McpToolset` fails on Vertex AI Agent Engine because anyio's `CancelScope` binds to the asyncio task that enters it — Agent Engine can context-switch tasks between entering and exiting the scope, triggering `"Attempted to exit cancel scope in a different task than it was entered in"`.

`ThreadedMCPToolset` (in `threaded_mcp_toolset.py`) fixes this by running every MCP operation in a dedicated thread with its own isolated event loop. Cancel scopes are created and destroyed entirely within that loop with no cross-task contamination. It also includes automatic retry logic (up to 3 attempts) for transient 401/connection errors caused by Cloud Run autoscaling.

### Agent Gateway as transparent egress proxy
When an Agent Engine is bound to an Agent Gateway in **Agent-to-Anywhere** mode, all outbound HTTPS traffic from the engine (to Vertex AI, Agent Registry, MCP servers) is intercepted and routed through the gateway. The gateway installs its own CA certificate into the container at startup. The `agent.py` entry point uses the system cert bundle (`/etc/ssl/certs/ca-certificates.crt`) rather than the bundled `certifi` certs so the gateway CA is trusted.

### Agent Registry URL resolution
On startup, `agent_registry_lookup.py` makes a single `GET /mcpServers` call to the Agent Registry and caches all server URLs. MCP tools then use these cached URLs. If the registry is unreachable the agents fall back to `*_MCP_URL` environment variables — local dev works without any registry setup.

The registry call requires the runtime identity to have `roles/agentregistry.viewer`. With `AGENT_IDENTITY` set, Agent Engine uses a Workload Identity Federation principal rather than the standard Reasoning Engine service account — grant the WIF principal `roles/agentregistry.viewer` and set `GOOGLE_API_PREVENT_AGENT_TOKEN_SHARING_FOR_GCP_SERVICES=false` in `.env`.

### MCP session affinity
Cloud Run MCP servers use `--session-affinity` so the MCP initialize handshake and subsequent tool calls always route to the same pod. Without this, autoscaling can route the two requests to different pods, causing a 401 from the new pod which has no session context.

### Telemetry
Agent Engine traces appear in the **Traces** tab of the Agent Engine console. This requires `agentregistry.googleapis.com` and the `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true` environment variable. OTel content capture is enabled via `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`.

### Windows development
- All `.sh` scripts require **Git Bash** or **WSL**
- Scripts auto-detect `.venv/Scripts/` vs `.venv/bin/` for cross-platform venv support
- If `gcloud` fails in Git Bash due to Python conflicts, run `gcloud` commands from PowerShell or Command Prompt instead
