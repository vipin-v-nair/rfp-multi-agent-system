try:
    from google.adk.apps.app import App
    from google.adk.sessions.firestore_session_service import FirestoreSessionService
    print("Imports successful!")
except Exception as e:
    print(f"Error: {e}")
