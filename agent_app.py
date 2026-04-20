import os
from google.adk.app import App
from google.adk.sessions import FirestoreSessionService
from agents.coordinator import coordinator

# Use FirestoreSessionService if project ID is available, else fallback to InMemory for simple testing
project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "vipin-genai-bb")

try:
    session_service = FirestoreSessionService(project=project_id)
except Exception as e:
    print(f"Warning: Failed to initialize FirestoreSessionService. {e}")
    from google.adk.sessions import InMemorySessionService
    session_service = InMemorySessionService()

app = App(
    name="rfp_system",
    agent=coordinator,
    session_service=session_service
)
