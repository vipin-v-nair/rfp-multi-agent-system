# RFP Multi-Agent System

A repository utilizing the Agent Development Kit (ADK) to demonstrate a multi-agent collaborative system with shared memory. This system uses a team of specialized agents (Ingestion, Solution, Governance, Editor, etc.) to autonomously process RFPs and generate compliant proposals.

## Architecture Overview
This application is fully decoupled to support both local development and enterprise cloud deployments:
- **Backend (Agents)**: Hosted on a local ADK API server or Vertex AI Agent Engine.
- **Frontend (UI)**: A FastAPI web server hosting an A2UI interactive dashboard.
- **State Management**: Session memory and events are managed centrally via Google Cloud Firestore.

---

## Prerequisites
1. **Google Cloud Project**: You must have a GCP project with Vertex AI and Firestore APIs enabled.
2. **Firestore Database**: Ensure a default Firestore database is initialized for your project.
3. **Google Cloud CLI (`gcloud`)**: Installed and authenticated.
4. **Python 3.11+** installed locally.

---

## Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/rfp-multi-agent-system.git
cd rfp-multi-agent-system
```

### 2. Set Up the Python Environment
It's highly recommended to use a virtual environment to isolate the dependencies.
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Authentication
Log in to Google Cloud so the local agents can access Vertex AI and Firestore:
```bash
gcloud auth application-default login
```

### 4. Configuration
Copy the template environment file and fill in your project details:
```bash
cp .env.example .env
```
Update the `.env` file with your GCP Project ID and Region. *(Leave the `AGENT_ENGINE_ID` blank until you deploy the backend).*

---

## Running Locally

The project includes two scripts to instantly start the decoupled architecture locally.

**1. Start the Backend (Agent Server)**
In your first terminal, start the ADK Agent server:
```bash
./start_local_agent.sh
```
*This starts an API server on `localhost:8080` hosting your agents.*

**2. Start the Frontend (FastAPI & UI)**
In a second terminal, start the web server:
```bash
./start_local_ui.sh
```
*This runs the UI on `localhost:8001`. It will automatically route requests to your local Agent server.*

Open [http://localhost:8001](http://localhost:8001) in your browser to interact with the system!

You can upload the pdf file from rfp-multi-agent-system/demo_data/rfp/source/acme_rfp.pdf to test the system.

---

## Deploying to Google Cloud

When you are ready to push your changes to the cloud, the provided deployment scripts make it a breeze.

### Step 1: Deploy the Agents (Vertex AI Agent Engine)
Run the deployment script to package and deploy the agents to Vertex AI:
```bash
./deploy_agent.sh
```
When this finishes, the CLI will output a **Reasoning Engine ID** (e.g., `projects/12345/locations/us-central1/reasoningEngines/67890`). 

**Important:** Copy this ID and paste it into your `.env` file as `AGENT_ENGINE_ID`. From now on, running `./deploy_agent.sh` will perform rapid in-place updates to that specific engine!

### Step 2: Deploy the UI (Cloud Run)
Once your `.env` file contains the `AGENT_ENGINE_ID`, run the Cloud Run deployment script:
```bash
./deploy_ui.sh
```
This will build the Docker container and push the FastAPI server to the web. It will automatically pull the Agent Engine ID from your `.env` file and securely connect the cloud UI to your cloud agents!
