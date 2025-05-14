from google.adk.runners import Runner

def get_runner(agent, session_service, app_name):
    runner = Runner(
        agent=agent,
        app_name=app_name,
        session_service=session_service
    )
    print(f"Runner created for agent '{runner.agent.name}'.")
    return runner
