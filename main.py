from dotenv import load_dotenv
import os
import asyncio
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm # For multi-model support
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types # For creating message Content/Parts
import warnings

from app import get_weather, get_session, get_session_stateful, get_runner, say_hello, say_goodbye, get_weather_stateful
from app.models import  MODEL_GEMINI_2_0_FLASH, MODEL_GPT_4O, MODEL_CLAUDE_SONNET

from app.subAgentUtils import createAgent


# Ignore all warnings
warnings.filterwarnings("ignore")

import logging
logging.basicConfig(level=logging.ERROR)

load_dotenv()
 
# Configure ADK to use API keys directly (not Vertex AI for this multi-model setup)
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"



async def call_agent_async(query: str, runner, user_id, session_id):
  """Sends a query to the agent and prints the final response."""
  print(f"\n>>> User Query: {query}")

  # Prepare the user's message in ADK format
  content = types.Content(role='user', parts=[types.Part(text=query)])

  final_response_text = "Agent did not produce a final response." # Default

  # Key Concept: run_async executes the agent logic and yields Events.
  # We iterate through events to find the final answer.
  async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
      # You can uncomment the line below to see *all* events during execution
      # print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")

      # Key Concept: is_final_response() marks the concluding message for the turn.
      if event.is_final_response():
          if event.content and event.content.parts:
             # Assuming text response in the first part
             final_response_text = event.content.parts[0].text
          elif event.actions and event.actions.escalate: # Handle potential errors/escalations
             final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
          # Add more checks here if needed (e.g., specific error codes)
          break # Stop processing events once the final response is found

  print(f"<<< Agent Response: {final_response_text}")


##########################################################
# @title Define Greeting and Farewell Sub-Agents
##########################################################


# --- Greeting Agent ---
greeting_agent = createAgent(model=MODEL_GEMINI_2_0_FLASH,
                                name="greeting_agent",
                                instruction="You are the Greeting Agent. Your ONLY task is to provide a friendly greeting to the user. "
                                "Use the 'say_hello' tool to generate the greeting. "
                                "If the user provides their name, make sure to pass it to the tool. "
                                "Do not engage in any other conversation or tasks.",
                                description="Handles simple greetings and hellos using the 'say_hello' tool.", # Crucial for delegation
                                tools=[say_hello])


# --- Farewell Agent ---
farewell_agent = createAgent(model=MODEL_GEMINI_2_0_FLASH,
                                name="farewell_agent",
                                instruction="You are the Farewell Agent. Your ONLY task is to provide a polite goodbye message. "
                                "Use the 'say_goodbye' tool when the user indicates they are leaving or ending the conversation "
                                "(e.g., using words like 'bye', 'goodbye', 'thanks bye', 'see you'). "
                                "Do not perform any other actions.",
                                description="Handles simple farewells and goodbyes using the 'say_goodbye' tool.", # Crucial for delegation
                                tools=[say_goodbye])
 
##################################################################
# @title Define the Root Agent with Sub-Agents
##################################################################

# Ensure sub-agents were created successfully before defining the root agent.
# Also ensure the original 'get_weather' tool is defined.
root_agent = None
runner_root = None # Initialize runner
APP_NAME = "weather_tutorial_agent_team"
USER_ID = "user_1_agent_team"
SESSION_ID = "session_001_agent_team"

retrieved_session, session_service_stateful = get_session_stateful(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)

if greeting_agent and farewell_agent and 'get_weather_stateful' in globals():
    # Let's use a capable Gemini model for the root agent to handle orchestration
    root_agent_model = MODEL_GEMINI_2_0_FLASH
    
    root_agent_stateful = createAgent(
                                  model=root_agent_model,
                                  name="weather_agent_v4_stateful",
                                  description="The main coordinator agent. Handles weather requests and delegates greetings/farewells to specialists.",
                                  instruction="You are the main Weather Agent coordinating a team. Your primary responsibility is to provide weather information. "
                                  "Use the 'get_weather' tool ONLY for specific weather requests (e.g., 'weather in London'). "
                                  "You have specialized sub-agents: "
                                  "1. 'greeting_agent': Handles simple greetings like 'Hi', 'Hello'. Delegate to it for these. "
                                  "2. 'farewell_agent': Handles simple farewells like 'Bye', 'See you'. Delegate to it for these. ", 
                                  tools=[get_weather_stateful], 
                                  subAgentList=[greeting_agent, farewell_agent],
                                  outputKey="last_weather_report"
                                  )
     
    print(f"✅ Root Agent '{root_agent_stateful.name}' created using stateful tool and output_key and using model '{root_agent_model}' with sub-agents: {[sa.name for sa in root_agent_stateful.sub_agents]}")
    runner_root_stateful = Runner(
        agent=root_agent_stateful,
        app_name=APP_NAME,
        session_service=session_service_stateful # Use the NEW stateful session service
    )
    print(f"✅ Runner created for stateful root agent '{runner_root_stateful.agent.name}' using stateful session service.")
else:
    print("❌ Cannot create root agent because one or more sub-agents failed to initialize or 'get_weather' tool is missing.")
    if not greeting_agent: print(" - Greeting Agent is missing.")
    if not farewell_agent: print(" - Farewell Agent is missing.")
    if 'get_weather_stateful' not in globals(): print(" - get_weather_stateful function is missing.")


#clwd start
# @title 4. Interact to Test State Flow and output_key



if 'runner_root_stateful' in globals() and runner_root_stateful:
    # Define the main async function for the stateful conversation logic.
    # The 'await' keywords INSIDE this function are necessary for async operations.
    async def run_stateful_conversation():
        print("\n--- Testing State: Temp Unit Conversion & output_key ---")

        # 1. Check weather (Uses initial state: Celsius)
        print("--- Turn 1: Requesting weather in London (expect Celsius) ---")
        await call_agent_async(query= "What's the weather in London?",
                               runner=runner_root_stateful,
                               user_id=USER_ID,
                               session_id=SESSION_ID
                              )

        # 2. Manually update state preference to Fahrenheit - DIRECTLY MODIFY STORAGE
        print("\n--- Manually Updating State: Setting unit to Fahrenheit ---")
        try:
            # Access the internal storage directly - THIS IS SPECIFIC TO InMemorySessionService for testing
            # NOTE: In production with persistent services (Database, VertexAI), you would
            # typically update state via agent actions or specific service APIs if available,
            # not by direct manipulation of internal storage.
            stored_session = session_service_stateful.sessions[APP_NAME][USER_ID][SESSION_ID]
            stored_session.state["user_preference_temperature_unit"] = "Fahrenheit"
            # Optional: You might want to update the timestamp as well if any logic depends on it
            # import time
            # stored_session.last_update_time = time.time()
            print(f"--- Stored session state updated. Current 'user_preference_temperature_unit': {stored_session.state.get('user_preference_temperature_unit', 'Not Set')} ---") # Added .get for safety
        except KeyError:
            print(f"--- Error: Could not retrieve session '{SESSION_ID}' from internal storage for user '{USER_ID}' in app '{APP_NAME}' to update state. Check IDs and if session was created. ---")
        except Exception as e:
             print(f"--- Error updating internal session state: {e} ---")

        # 3. Check weather again (Tool should now use Fahrenheit)
        # This will also update 'last_weather_report' via output_key
        print("\n--- Turn 2: Requesting weather in New York (expect Fahrenheit) ---")
        await call_agent_async(query= "Tell me the weather in New York.",
                               runner=runner_root_stateful,
                               user_id=USER_ID,
                               session_id=SESSION_ID
                              )

        # 4. Test basic delegation (should still work)
        # This will update 'last_weather_report' again, overwriting the NY weather report
        print("\n--- Turn 3: Sending a greeting ---")
        await call_agent_async(query= "Hi!",
                               runner=runner_root_stateful,
                               user_id=USER_ID,
                               session_id=SESSION_ID
                              )

     
    if __name__ == "__main__": # Ensures this runs only when script is executed directly
        print("Executing using 'asyncio.run()' (for standard Python scripts)...")
        try:
            # This creates an event loop, runs your async function, and closes the loop.
            asyncio.run(run_stateful_conversation())
        except Exception as e:
            print(f"An error occurred: {e}")

    # --- Inspect final session state after the conversation ---
    # This block runs after either execution method completes.
    print("\n--- Inspecting Final Session State ---")
    final_session = session_service_stateful.get_session(app_name=APP_NAME,
                                                         user_id= USER_ID,
                                                         session_id=SESSION_ID)
    if final_session:
        # Use .get() for safer access to potentially missing keys
        print(f"Final Preference: {final_session.state.get('user_preference_temperature_unit', 'Not Set')}")
        print(f"Final Last Weather Report (from output_key): {final_session.state.get('last_weather_report', 'Not Set')}")
        print(f"Final Last City Checked (by tool): {final_session.state.get('last_city_checked_stateful', 'Not Set')}")
        # Print full state for detailed view
        # print(f"Full State Dict: {final_session.state.as_dict()}") # Use as_dict() for clarity
    else:
        print("\n❌ Error: Could not retrieve final session state.")

else:
    print("\n⚠️ Skipping state test conversation. Stateful root agent runner ('runner_root_stateful') is not available.")
