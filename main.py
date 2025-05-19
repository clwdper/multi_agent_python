from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import asyncio

from dotenv import load_dotenv
import os
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm # For multi-model support
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types # For creating message Content/Parts
import warnings

from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    SseServerParams,
    StdioServerParameters,
)
from app import get_weather, get_session, get_session_stateful, get_runner, say_hello, say_goodbye, get_weather_stateful
from app.models import MODEL_GEMINI_2_0_FLASH, MODEL_GPT_4O, MODEL_CLAUDE_SONNET

from app.agentUtils import createAgent
from app.tools import execute_maven_command


app = FastAPI()

# Sample in-memory "database"
fake_db = {"foo": "bar"}

# Pydantic model for POST request
class Item(BaseModel):
    name: str
    price: float

# Async GET endpoint
@app.get("/items/{item_id}")
async def read_item(item_id: str):
    await asyncio.sleep(1)  # Simulate async I/O (e.g., DB query)
    if item_id not in fake_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item_id": item_id, "data": fake_db[item_id]}

# Async POST endpoint
@app.post("/items/")
async def create_item(item: Item):
    await asyncio.sleep(0.5)  # Simulate async processing
    fake_db[item.name] = item.price
    return {"item_name": item.name, "item_price": item.price}



server_params = StdioServerParameters(
      command="node",
      args=["/Users/clearencewissar/clwd_per_code/ai-agent-claude/multi-agent/team-agents/stdio_server/build/index.js"],
      env={},
      cwd="/Users/clearencewissar/clwd_per_code/ai-agent-claude/multi-agent/team-agents/stdio_server",
      encoding="utf-8",
      encoding_error_handler="strict"
  )
  
async def get_tools_async():
  """Gets tools from the File System MCP Server."""
  try:
      tools, exit_stack = await MCPToolset.from_server(
          connection_params=server_params
      )
      print("MCP Toolset created successfully.")
      return tools, exit_stack
  except Exception as e:
      print(f"Error creating MCP Toolset: {e}")
      return None, None


# Calls the agent asynchronously
async def call_agent_async(query: str, runner, user_id, session_id):
  """Sends a query to the agent and prints the final response."""
  print(f">>> User Query: {query}")

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
  return final_response_text


# Catch-all handler for /mcp and all its subpaths
@app.api_route("/mcp/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def mcp_catch_all(request: Request, path: str):
    # You can access request method, headers, body, etc.
    method = request.method
    headers = dict(request.headers)
    
    # If you want to handle the request body (for POST, PUT, etc.)
    if method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
        except:
            body = None
    else:
        body = None
       

    # Get the MCP toolset asynchronously
    tools_list = []
    try:
        tools, exit_stack = await get_tools_async()
        if tools:
            tools_list = tools
            # print tools_list
            print("Tools loaded successfully.")
            print(f"Tools: {tools_list}")
            
    except Exception as e:
        print(f"Warning: Failed to load MCP tools: {e}")
    
    
    try:
      fix_vulnerability_agent = createAgent(model=MODEL_GEMINI_2_0_FLASH,
                                      name="fix_vulnerability_agent",
                                      instruction="You are the fix vulnerability Agent. Your ONLY task is to fix and address vulnerabilities in source code using the list of vulnerabilities provided. "
                                      "Use the 'fix_vulnerability' tool when the user requires you to."
                                      "(e.g., using words like fix, address vulnerability, fix vulnerability, etc.). "
                                      "Do not perform any other actions.",
                                      description="Handles vulnerability fixes using the 'fix_vulnerability' tool.", # Crucial for delegation
                                      tools=tools_list
                                      )
    except Exception as e:
        print(f"Error creating fix_vulnerability_agent: {e}")
        fix_vulnerability_agent = None
        
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


    maven_agent = createAgent(model=MODEL_GEMINI_2_0_FLASH,
                                    name="maven_agent",
                                    instruction="You are the Java Maven Agent. Your ONLY task is to run maven commands. "
                                    "Use the 'execute_maven_command' tool when the user requires you to run a maven command, they will provide you the command as well as the path or working_dir."
                                    "(e.g., using words like 'run', 'execute', 'mvn', 'build', 'clean', 'install', 'test', 'package'). "
                                    "Do not perform any other actions.",
                                    description="Handles simple maven commands using the 'execute_maven_command' tool.", # Crucial for delegation
                                    tools=[execute_maven_command])


    root_agent = None
    runner_root = None # Initialize runner
    APP_NAME = "weather_tutorial_agent_team"
    USER_ID = "user_1_agent_team"
    SESSION_ID = "session_001_agent_team"

    retrieved_session, session_service_stateful = get_session_stateful(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)

    # Create list of available sub-agents
    available_sub_agents = []
    if greeting_agent:
        available_sub_agents.append(greeting_agent)
    if farewell_agent:
        available_sub_agents.append(farewell_agent)
    if maven_agent:
        available_sub_agents.append(maven_agent)
    if fix_vulnerability_agent:
        available_sub_agents.append(fix_vulnerability_agent)

    if available_sub_agents and 'get_weather_stateful' in globals():
      # Let's use a capable Gemini model for the root agent to handle orchestration
      root_agent_model = MODEL_GEMINI_2_0_FLASH
      
    # Create instruction based on available sub-agents
    instruction = "You are the main   Agent coordinating a team. Your primary responsibility is to delegate tasks based on the prompt. "
    instruction += "Use the 'get_weather' tool ONLY for specific weather requests (e.g., 'weather in London'). "
    instruction += "You have specialized sub-agents: "
    
    if greeting_agent:
        instruction += "1. 'greeting_agent': Handles simple greetings like 'Hi', 'Hello'. Delegate to it for these. "
    if farewell_agent:
        instruction += "2. 'farewell_agent': Handles simple farewells like 'Bye', 'See you'. Delegate to it for these. "
    if maven_agent:
        instruction += "3. 'maven_agent': Handles maven commands. Delegate to it for these. "
    if fix_vulnerability_agent:
        instruction += "4. 'fix_vulnerability_agent': Handles vulnerability fixes. Delegate to it for these. "

    root_agent_stateful = createAgent(
                                  model=root_agent_model,
                                  name="weather_agent_v4_stateful",
                                  description="The main coordinator agent. Handles weather requests and delegates greetings/farewells maven commands to specialists.",
                                  instruction=instruction,
                                  tools=[get_weather_stateful], 
                                  subAgentList=available_sub_agents,
                                  outputKey="last_weather_report"
                                  )
      
      
    runner_root_stateful = Runner(
        agent=root_agent_stateful,
        app_name=APP_NAME,
        session_service=session_service_stateful
    )
    
    final_response_from_agent = await call_agent_async(query= "hi my name is Ramon, I need to run maven compile on this path: /Users/clearencewissar/clwd_per_code/mvn-tut. Also use the 'fix_vulnerability' tool on this source code: print('password is 123456') and this vulnerability report: exposes password in clear text",
                               runner=runner_root_stateful,
                               user_id=USER_ID,
                               session_id=SESSION_ID
                              )
    print(f"Final response from agent: {final_response_from_agent}")
    
    # Return all the information we have about the request
    return {
        "message": "MCP catch-all handler",
        "method": method,
        "path": path,
        "headers": headers,
        "body": body,
        "query_params": dict(request.query_params)
    }
