from google.adk.sessions import InMemorySessionService



def get_session_service():
    # --- Session Management ---
    # Key Concept: SessionService stores conversation history & state.
    # InMemorySessionService is simple, non-persistent storage for this tutorial.
    session_service = InMemorySessionService()
    return session_service

def get_session(app_name, user_id, session_id):
    session_service = get_session_service()
    # Create the specific session where the conversation will happen
    session = session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )
    print(f"Session created: App='{app_name}', User='{user_id}', Session='{session_id}'")
    return session, session_service
    
