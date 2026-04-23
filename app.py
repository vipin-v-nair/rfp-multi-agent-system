import sys
# Ensure UTF-8 stdout on all platforms (needed on Windows with default cp1252 encoding)
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    pass  # Python < 3.7 fallback

from fastapi import FastAPI, BackgroundTasks, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import uvicorn
import asyncio
import os
import json
import uuid
import requests
from contextlib import asynccontextmanager
from state import FirestoreStateManager

# App Config
app_name = "rfp_system"
user_id = "demo_user"

# The endpoint for the ADK agent (local adk api_server or Agent Engine)
AGENT_ENDPOINT = os.getenv("AGENT_ENDPOINT", "http://localhost:8080")

base_dir = os.path.dirname(os.path.abspath(__file__))

# Initialize a global session and state manager
session_id = f"session-{uuid.uuid4().hex[:8]}"
state_manager = FirestoreStateManager(session_id)

def run_workflow_sync_impl(feedback: str = None):
    """Synchronous function to run the workflow by calling the remote agent via HTTP."""
    try:
        current_state = state_manager.get_state()
        
        if feedback:
            current_state.setdefault('workflow', {})['status'] = 'revision_requested'
            current_state['user_feedback'] = feedback
            state_manager.update_state(current_state)
            user_message_text = f"Rework the response based on this feedback: {feedback}"
        else:
            current_state.setdefault('workflow', {})['status'] = 'running'
            state_manager.update_state(current_state)
            current_file_path = current_state.get('rfp_input', {}).get('file_path')
            user_message_text = f"Process the RFP PDF at: {current_file_path}"

        AGENT_ENGINE_ID = os.getenv("AGENT_ENGINE_ID")
        
        # Agent Engine expects 'message' and NO 'app_name'
        message_key = "message" if AGENT_ENGINE_ID else "new_message"
        
        payload = {
            "user_id": user_id,
            "session_id": session_id,
            message_key: {
                "role": "user",
                "parts": [{"text": user_message_text}]
            }
        }
        
        if not AGENT_ENGINE_ID:
            payload["app_name"] = app_name
            payload["streaming"] = True

        if AGENT_ENGINE_ID:
            import google.auth
            import google.auth.transport.requests
            credentials, project = google.auth.default()
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)
            token = credentials.token
            
            location = AGENT_ENGINE_ID.split("/")[3]
            url = f"https://{location}-aiplatform.googleapis.com/v1beta1/{AGENT_ENGINE_ID}:streamQuery"
            
            print(f"Calling Vertex AI Agent Engine at {url}")
            response = requests.post(
                url,
                json={"input": payload},
                headers={"Authorization": f"Bearer {token}"},
                stream=True
            )
        else:
            print(f"Calling ADK Agent at {AGENT_ENDPOINT}/run_sse")
            response = requests.post(
                f"{AGENT_ENDPOINT}/run_sse",
                json=payload,
                stream=True
            )
        
        if response.status_code != 200:
            raise Exception(f"Agent returned error: {response.text}")

        # Process the stream (Handles both SSE and Vertex AI JSON Arrays)
        buffer = ""
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8').strip()
                
                # Handle local ADK server SSE format
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[len("data: "):]
                    if data_str == "[DONE]":
                        break
                    try:
                        event_data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                
                # Handle Vertex AI JSON Array stream
                else:
                    # Accumulate lines since JSON might be split across lines
                    buffer += decoded_line
                    
                    # We look for complete JSON objects in the buffer.
                    # Since Vertex AI streams `{ "result": ... }`, we can try to extract the objects.
                    # A simple heuristic: if the buffer contains a complete dict, try parsing it.
                    if buffer == "[" or buffer == "," or buffer == "]":
                        buffer = ""
                        continue
                        
                    try:
                        # It might have a trailing comma
                        clean_buf = buffer.rstrip(',')
                        parsed = json.loads(clean_buf)
                        
                        # Vertex AI wraps the yielded object in {"result": ...}
                        if "result" in parsed:
                            event_data = parsed["result"]
                        else:
                            event_data = parsed
                            
                        buffer = "" # Reset buffer after successful parse
                    except json.JSONDecodeError:
                        # Incomplete JSON object, keep accumulating
                        continue

                # Now we have event_data
                author = event_data.get("author")
                content = event_data.get("content")
                        
                if author and content:
                    # Extract meaningful text from ADK Content dictionary
                    content_str = ""
                    if isinstance(content, dict) and 'parts' in content:
                        parts = []
                        for p in content.get('parts', []):
                            if 'text' in p:
                                parts.append(p['text'])
                            elif 'function_call' in p:
                                func_name = p['function_call'].get('name')
                                func_args = p['function_call'].get('args', {})
                                parts.append(f"Called tool {func_name} with args: {json.dumps(func_args)}")
                        content_str = "".join(parts)
                    elif isinstance(content, str):
                        content_str = content
                    else:
                        content_str = str(content)
                        
                    print(f"Event from {author}: {content_str}")
                    
                    # Fetch the latest full state from the ADK Agent Server
                    if AGENT_ENGINE_ID:
                        from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService
                        location = AGENT_ENGINE_ID.split("/")[3]
                        project = AGENT_ENGINE_ID.split("/")[1]
                        engine_id = AGENT_ENGINE_ID.split("/")[-1]
                        
                        # ADK stores sessions in Vertex AI
                        va_session_service = VertexAiSessionService(
                            project=project, location=location, agent_engine_id=engine_id
                        )
                        
                        import asyncio
                        # We are in a sync thread, use asyncio.run
                        session_obj = asyncio.run(va_session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id))
                        adk_state = session_obj.state if session_obj else {}
                    else:
                        session_resp = requests.get(f"{AGENT_ENDPOINT}/apps/{app_name}/users/{user_id}/sessions/{session_id}")
                        if session_resp.status_code == 200:
                            session_data = session_resp.json()
                            adk_state = session_data.get("state", {})
                        else:
                            print(f"Warning: Failed to fetch ADK session state: {session_resp.text}")
                            adk_state = {}
                        
                    if adk_state:
                        # Merge our workflow updates (stage, active agent) into the ADK state
                        adk_state.setdefault('workflow', {})['active_agent'] = author
                        if author == "DocumentIngestion":
                            adk_state['workflow']['stage'] = 'intake'
                        elif author == "SolutionAgent":
                            adk_state['workflow']['stage'] = 'drafting'
                        elif author == "Governance":
                            adk_state['workflow']['stage'] = 'review'
                        elif author == "Editor":
                            adk_state['workflow']['stage'] = 'finalization'
                            
                        state_manager.update_state(adk_state)
                    
                    # Append event with CLEAN string
                    state_manager.append_event({
                        "author": author,
                        "content": content_str
                    })

        # Update status to completed when the stream ends successfully
        print("Workflow stream completed successfully.")
        final_state = state_manager.get_state()
        final_state.setdefault('workflow', {})['status'] = 'completed'
        final_state['workflow']['stage'] = 'publish'
        state_manager.update_state(final_state)

    except Exception as e:
        print(f"CRITICAL ERROR in workflow task: {e}")
        current_state = state_manager.get_state()
        current_state.setdefault('workflow', {})['status'] = 'error'
        current_state.setdefault('workflow', {})['halt_reason'] = str(e)
        state_manager.update_state(current_state)

async def run_workflow_task(feedback: str = None):
    print("Running workflow task...")
    await asyncio.to_thread(run_workflow_sync_impl, feedback)

active_workflow_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize session in Firestore
    state_manager.init_state()
    print(f"Session created: {session_id}")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def read_index():
    return FileResponse("index.html")

@app.get("/workflow_state.json")
async def get_state():
    try:
        return state_manager.get_state()
    except Exception as e:
        print(f"Error reading state: {e}")
        return {}

@app.get("/workflow_events.json")
async def get_events():
    try:
        return state_manager.get_events()
    except Exception as e:
        print(f"Error reading events: {e}")
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

@app.post("/api/upload")
async def upload_rfp(file: UploadFile = File(...)):
    global active_workflow_task
    
    global session_id
    global state_manager
    
    current_state = state_manager.get_state()
    if current_state.get('workflow', {}).get('status') == 'running':
        raise HTTPException(status_code=409, detail="A workflow is already in progress.")
        
    # Ensure uploads directory exists
    uploads_dir = os.path.join(base_dir, 'demo_data', 'rfp', 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    
    file_path = os.path.join(uploads_dir, file.filename)
    
    # Save the file
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
        
    print(f"File saved to: {file_path}")
    
    # Regenerate session ID for a completely fresh run on the ADK Server
    session_id = f"session-{uuid.uuid4().hex[:8]}"
    state_manager = FirestoreStateManager(session_id)
    
    # Reset state and set new file path
    from state import get_initial_state
    new_state = get_initial_state()
    new_state['rfp_input']['file_path'] = file_path
    
    state_manager.init_state()
    state_manager.update_state(new_state)
    
    AGENT_ENGINE_ID = os.getenv("AGENT_ENGINE_ID")
    if AGENT_ENGINE_ID:
        from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService
        location = AGENT_ENGINE_ID.split("/")[3]
        project = AGENT_ENGINE_ID.split("/")[1]
        engine_id = AGENT_ENGINE_ID.split("/")[-1]
        
        va_session_service = VertexAiSessionService(
            project=project, location=location, agent_engine_id=engine_id
        )
        
        # Explicitly create the session in Vertex AI before querying the agent
        try:
            await va_session_service.create_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                state=new_state
            )
            print(f"Created Vertex AI Session: {session_id}")
        except Exception as e:
            print(f"Warning: Failed to create Vertex AI session: {e}")
            
    # Trigger workflow in background
    active_workflow_task = asyncio.create_task(run_workflow_task())
    
    return {"status": "success", "message": "File uploaded and workflow triggered."}

if __name__ == "__main__":
    print("Starting FastAPI server on http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
