from dotenv import load_dotenv
import os
import asyncio
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm # For multi-model support
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types # For creating message Content/Parts
import warnings

from app import get_weather, get_session, get_runner, say_hello, say_goodbye
from app.models import  MODEL_GEMINI_2_0_FLASH, MODEL_GPT_4O, MODEL_CLAUDE_SONNET

from app.subAgentUtils import createAgent


# Ignore all warnings
warnings.filterwarnings("ignore")

import logging
logging.basicConfig(level=logging.ERROR)

load_dotenv()
 
# Configure ADK to use API keys directly (not Vertex AI for this multi-model setup)
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"

# @title Define the Weather Agent
# Use one of the model constants defined earlier
AGENT_MODEL = MODEL_GEMINI_2_0_FLASH # Starting with Gemini

weather_agent = Agent(
    name="weather_agent_v1",
    model=AGENT_MODEL, # Can be a string for Gemini or a LiteLlm object
    description="Provides weather information for specific cities.",
    instruction="You are a helpful weather assistant. "
                "When the user asks for the weather in a specific city, "
                "use the 'get_weather' tool to find the information. "
                "If the tool returns an error, inform the user politely. "
                "If the tool is successful, present the weather report clearly.",
    tools=[get_weather], # Pass the function directly
)


# Define constants for identifying the interaction context
APP_NAME = "weather_tutorial_app"
USER_ID = "user_1"
SESSION_ID = "session_001" # Using a fixed ID for simplicity

session, session_service = get_session(APP_NAME, USER_ID, SESSION_ID)

# --- Runner ---
runner = get_runner(weather_agent, session_service, APP_NAME)


# @title Define Agent Interaction Function

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


# @title Run the Initial Conversation

# We need an async function to await our interaction helper
async def run_conversation():
    await call_agent_async("What is the weather like in London?",
                                       runner=runner,
                                       user_id=USER_ID,
                                       session_id=SESSION_ID)

    await call_agent_async("How about Paris?",
                                       runner=runner,
                                       user_id=USER_ID,
                                       session_id=SESSION_ID) # Expecting the tool's error message

    await call_agent_async("Tell me the weather in New York",
                                       runner=runner,
                                       user_id=USER_ID,
                                       session_id=SESSION_ID)


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

if greeting_agent and farewell_agent and 'get_weather' in globals():
    # Let's use a capable Gemini model for the root agent to handle orchestration
    root_agent_model = MODEL_GEMINI_2_0_FLASH
   
    
    weather_agent_team = createAgent(model=root_agent_model,
                                   name="weather_agent_v2",
                                   description="The main coordinator agent. Handles weather requests and delegates greetings/farewells to specialists.",
                                   instruction="You are the main Weather Agent coordinating a team. Your primary responsibility is to provide weather information. "
                                   "Use the 'get_weather' tool ONLY for specific weather requests (e.g., 'weather in London'). "
                                   "You have specialized sub-agents: "
                                   "1. 'greeting_agent': Handles simple greetings like 'Hi', 'Hello'. Delegate to it for these. "
                                   "2. 'farewell_agent': Handles simple farewells like 'Bye', 'See you'. Delegate to it for these. ", 
                                   tools=[get_weather], 
                                   subAgentList=[greeting_agent, farewell_agent]
                                  )
    print(f"✅ Root Agent '{weather_agent_team.name}' created using model '{root_agent_model}' with sub-agents: {[sa.name for sa in weather_agent_team.sub_agents]}")

else:
    print("❌ Cannot create root agent because one or more sub-agents failed to initialize or 'get_weather' tool is missing.")
    if not greeting_agent: print(" - Greeting Agent is missing.")
    if not farewell_agent: print(" - Farewell Agent is missing.")
    if 'get_weather' not in globals(): print(" - get_weather function is missing.")






# @title Interact with the Agent Team


# Ensure the root agent (e.g., 'weather_agent_team' or 'root_agent' from the previous cell) is defined.
# Ensure the call_agent_async function is defined.

# Check if the root agent variable exists before defining the conversation function
root_agent_var_name = 'root_agent' # Default name from Step 3 guide
if 'weather_agent_team' in globals(): # Check if user used this name instead
    root_agent_var_name = 'weather_agent_team'
elif 'root_agent' not in globals():
    print("⚠️ Root agent ('root_agent' or 'weather_agent_team') not found. Cannot define run_team_conversation.")
    # Assign a dummy value to prevent NameError later if the code block runs anyway
    root_agent = None # Or set a flag to prevent execution

# Only define and run if the root agent exists
if root_agent_var_name in globals() and globals()[root_agent_var_name]:
    # Define the main async function for the conversation logic.
    # The 'await' keywords INSIDE this function are necessary for async operations.
    async def run_team_conversation():
        print("\n--- Testing Agent Team Delegation ---")
        session_service = InMemorySessionService()
        APP_NAME = "weather_tutorial_agent_team"
        USER_ID = "user_1_agent_team"
        SESSION_ID = "session_001_agent_team"
        session = session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
        )
        print(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")

        actual_root_agent = globals()[root_agent_var_name]
        runner_agent_team = Runner( # Or use InMemoryRunner
            agent=actual_root_agent,
            app_name=APP_NAME,
            session_service=session_service
        )
        print(f"Runner created for agent '{actual_root_agent.name}'.")

        # --- Interactions using await (correct within async def) ---
        await call_agent_async(query = "Hello there!",
                               runner=runner_agent_team,
                               user_id=USER_ID,
                               session_id=SESSION_ID)
        await call_agent_async(query = "What is the weather in New York?",
                               runner=runner_agent_team,
                               user_id=USER_ID,
                               session_id=SESSION_ID)
        await call_agent_async(query = "Thanks, bye!",
                               runner=runner_agent_team,
                               user_id=USER_ID,
                               session_id=SESSION_ID)

    # --- Execute the `run_team_conversation` async function ---
    # Choose ONE of the methods below based on your environment.
    # Note: This may require API keys for the models used!

    # METHOD 1: Direct await (Default for Notebooks/Async REPLs)
    # If your environment supports top-level await (like Colab/Jupyter notebooks),
    # it means an event loop is already running, so you can directly await the function.
    print("Attempting execution using 'await' (default for notebooks)...")
 

    # METHOD 2: asyncio.run (For Standard Python Scripts [.py])
    # If running this code as a standard Python script from your terminal,
    # the script context is synchronous. `asyncio.run()` is needed to
    # create and manage an event loop to execute your async function.
    # To use this method:
    # 1. Comment out the `await run_team_conversation()` line above.
    # 2. Uncomment the following block:
  
    import asyncio
    if __name__ == "__main__": # Ensures this runs only when script is executed directly
        print("Executing using 'asyncio.run()' (for standard Python scripts)...")
        try:
            # This creates an event loop, runs your async function, and closes the loop.
            asyncio.run(run_team_conversation())
        except Exception as e:
            print(f"An error occurred: {e}")
   

else:
    # This message prints if the root agent variable wasn't found earlier
    print("\n⚠️ Skipping agent team conversation execution as the root agent was not successfully defined in a previous step.")

