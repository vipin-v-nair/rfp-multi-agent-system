import asyncio
import os
import json
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai.types import Content, Part
from state import get_initial_state
from agents.coordinator import coordinator

async def main():
    session_service = InMemorySessionService()
    app_name = "rfp_system"
    import uuid
    user_id = "demo_user"
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    rfp_pdf_path = os.path.join(base_dir, 'demo_data', 'rfp', 'source', 'acme_rfp.pdf')
        
    initial_state = get_initial_state()
    # Initialize the project state with the PDF file path
    initial_state['rfp_input']['file_path'] = rfp_pdf_path
    
    # Create session with initial state
    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state=initial_state
    )
    
    # Clear and initialize local state files for dashboard
    with open('workflow_events.json', 'w') as f:
        json.dump([], f)
    with open('workflow_state.json', 'w') as f:
        json.dump(initial_state, f, indent=2)

    
    runner = Runner(
        agent=coordinator,
        app_name=app_name,
        session_service=session_service
    )
    
    print(f"Session created: {session_id}")
    print(f"Initial state: {session.state}")
    
    # Run the flow
    print("Running workflow...")
    user_message = Content(parts=[Part(text=f"Process the sample RFP PDF at: {rfp_pdf_path}")])
    
    # Runner.run is usually a generator or async generator.
    # Based on docs, it seems to be a standard generator in some examples,
    # but let's assume we can iterate over it.
    # If it's async, we'd use `async for`. Let's try standard for loop first or check docs.
    # In the state doc example: `for event in runner.run(...)`
    
    events_list = []
    try:
        for event in runner.run(user_id=user_id, session_id=session_id, new_message=user_message):
            print(f"Event from {event.author}: {event.content}")
            events_list.append({
                "author": event.author,
                "content": str(event.content)
            })
            with open('workflow_events.json', 'w') as f:
                json.dump(events_list, f, indent=2)
                
            # Fetch and save full state
            session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
            with open('workflow_state.json', 'w') as f:
                json.dump(session.state, f, indent=2)
                
    except Exception as e:
        print(f"Error running workflow: {e}")
        print("Note: This might be due to missing API keys or model access if not configured.")

if __name__ == "__main__":
    asyncio.run(main())
