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
    



def get_session_stateful(*, app_name, user_id, session_id, initial_state={
        "user_preference_temperature_unit": "Celsius"
    }):
    # Create a NEW session service instance for this state demonstration
    session_service_stateful = InMemorySessionService()

    # Define a NEW session ID for this part of the tutorial
    SESSION_ID_STATEFUL = session_id
    USER_ID_STATEFUL = user_id    

    # Create the session, providing the initial state
    session_stateful = session_service_stateful.create_session(
        app_name=app_name, # Use the consistent app name
        user_id=USER_ID_STATEFUL,
        session_id=SESSION_ID_STATEFUL,
        state=initial_state
    )
    # print(f"✅ Session '{SESSION_ID_STATEFUL}' created for user '{USER_ID_STATEFUL}'.")

    # Verify the initial state was set correctly
    retrieved_session = session_service_stateful.get_session(app_name=app_name,
                                                            user_id=USER_ID_STATEFUL,
                                                            session_id = SESSION_ID_STATEFUL)
    # print("\n--- Initial Session State ---")
    # if retrieved_session:
        # print(retrieved_session.state)
    # else:
        # print("Error: Could not retrieve session.")
    return retrieved_session, session_service_stateful
