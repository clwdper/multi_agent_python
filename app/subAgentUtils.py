from google.adk.models.lite_llm import LiteLlm 
from google.adk.agents import Agent
import os
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"

def createAgent(*,model, name, instruction, description, tools=None, subAgentList=None):
    subAgent = None
    try:
        subAgent = Agent(
            model = model,
            name=name,
            instruction=instruction,
            description=description,
            tools=tools or [],
            sub_agents=subAgentList or []
        )
        print(f"✅ sub agent '{subAgent.name}' created using model '{subAgent.model}'.")
    except Exception as e:
        print(f"❌ Could not create sub agent. Check API Key ({subAgent.model}). Error: {e}")
    return subAgent


