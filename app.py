from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse
import uvicorn
import asyncio
import os
import json
import uuid

# Fix SSL cert issue for Vertex AI calls
os.environ['SSL_CERT_FILE'] = os.path.abspath("./.venv/lib/python3.13/site-packages/certifi/cacert.pem")
from contextlib import asynccontextmanager
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai.types import Content, Part
from state import get_initial_state
from agents.coordinator import coordinator

session_service = InMemorySessionService()
app_name = "rfp_system"
user_id = "demo_user"
session_id = f"session_{uuid.uuid4().hex[:8]}"

base_dir = os.path.dirname(os.path.abspath(__file__))
rfp_pdf_path = os.path.join(base_dir, 'demo_data', 'rfp', 'source', 'acme_rfp.pdf')

initial_state = get_initial_state()
initial_state['rfp_input']['file_path'] = rfp_pdf_path

async def run_workflow_task(feedback: str = None):
    print("Running workflow...")
    session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    
    if feedback:
        # Update state with feedback
        session.state.setdefault('workflow', {})['status'] = 'revision_requested'
        session.state['user_feedback'] = feedback
        # Persist state to file immediately
        with open('workflow_state.json', 'w') as f:
            json.dump(session.state, f, indent=2)
        user_message = Content(parts=[Part(text=f"Rework the response based on this feedback: {feedback}")])
    else:
        # Fresh run: initialize state file
        from state import get_initial_state
        initial_state = get_initial_state()
        initial_state['rfp_input']['file_path'] = rfp_pdf_path
        with open('workflow_state.json', 'w') as f:
            json.dump(initial_state, f, indent=2)
        user_message = Content(parts=[Part(text=f"Process the sample RFP PDF at: {rfp_pdf_path}")])

    runner = Runner(
        agent=coordinator,
        app_name=app_name,
        session_service=session_service
    )
    
    # Reset event file for new run if not a feedback loop
    if not feedback:
        with open('workflow_events.json', 'w') as f:
            json.dump([], f)
            
    def run_workflow_sync_impl():
        # Set workflow status to running
        try:
            with open('workflow_state.json', 'r') as f:
                state = json.load(f)
            state.setdefault('workflow', {})['status'] = 'running'
            with open('workflow_state.json', 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Error setting workflow status to running: {e}")

        for event in runner.run(user_id=user_id, session_id=session_id, new_message=user_message):
            print(f"Event from {event.author}: {event.content}")
            
            # Read the most recent state from file to include tool updates
            from state import state_lock
            try:
                with state_lock:
                    try:
                        with open('workflow_state.json', 'r') as f:
                            current_state = json.load(f)
                    except Exception as e:
                        print(f"Error reading workflow_state.json: {e}")
                        current_state = {}
                    
                    # Update active agent and stage based on event author
                    current_state.setdefault('workflow', {})['active_agent'] = event.author
                    if event.author == "DocumentIngestion":
                        current_state['workflow']['stage'] = 'intake'
                    elif event.author == "SolutionAgent":
                        current_state['workflow']['stage'] = 'drafting'
                    elif event.author == "Governance":
                        current_state['workflow']['stage'] = 'review'
                    elif event.author == "Editor":
                        current_state['workflow']['stage'] = 'finalization'
                        
                    # Merge manual updates if missing
                    if feedback:
                        if 'user_feedback' not in current_state:
                            current_state['user_feedback'] = feedback
                        if current_state.get('workflow', {}).get('status') != 'revision_requested':
                            current_state.setdefault('workflow', {})['status'] = 'revision_requested'
                            
                    with open('workflow_state.json', 'w') as f:
                        json.dump(current_state, f, indent=2)
            except Exception as e:
                print(f"Error in state update block: {e}")
                
            # Append event to events file
            try:
                with open('workflow_events.json', 'r+') as f:
                    events = json.load(f)
                    events.append({
                        "author": event.author,
                        "content": event.content if isinstance(event.content, str) else str(event.content)
                    })
                    f.seek(0)
                    json.dump(events, f, indent=2)
            except Exception as e:
                print(f"Error updating events: {e}")

    try:
        await asyncio.to_thread(run_workflow_sync_impl)
    except Exception as e:
        print(f"CRITICAL ERROR in workflow task: {e}")
        # Update state to error
        try:
            with open('workflow_state.json', 'r') as f:
                state = json.load(f)
            state.setdefault('workflow', {})['status'] = 'error'
            state['workflow']['halt_reason'] = str(e)
            with open('workflow_state.json', 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as se:
            print(f"Failed to update state file with error: {se}")

active_workflow_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize session
    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state=initial_state
    )
    
    # Reset state file
    with open('workflow_state.json', 'w') as f:
        json.dump(initial_state, f, indent=2)
        
    # Reset events file
    with open('workflow_events.json', 'w') as f:
        json.dump([], f)
        
    print(f"Session created: {session_id}")
    
    # Start initial run in background
    global active_workflow_task
    active_workflow_task = asyncio.create_task(run_workflow_task())
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def read_index():
    return FileResponse("index.html")

@app.get("/workflow_state.json")
async def get_state():
    try:
        with open("workflow_state.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading workflow_state.json: {e}")
        return {}

@app.get("/workflow_events.json")
async def get_events():
    try:
        with open("workflow_events.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading workflow_events.json: {e}")
        return []

@app.post("/api/feedback")
async def receive_feedback(feedback_data: dict):
    global active_workflow_task
    feedback = feedback_data.get("feedback")
    print(f"Received feedback: {feedback}")
    
    if active_workflow_task and not active_workflow_task.done():
        print("Cancelling active workflow task...")
        active_workflow_task.cancel()
        try:
            await active_workflow_task
        except asyncio.CancelledError:
            print("Task cancelled successfully.")
            
    active_workflow_task = asyncio.create_task(run_workflow_task(feedback))
    return {"status": "success", "message": "Rework triggered."}

if __name__ == "__main__":
    print("Starting FastAPI server on http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)

