from google.adk.models.lite_llm import LiteLlm 
from google.adk.agents import Agent
from google.adk.agents.llm_agent import LlmAgent
import os
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"

def createAgent(*,model, name, instruction, description, tools=None, subAgentList=None, outputKey=None):
    subAgent = None
    try:
        subAgent = LlmAgent(
            model = model,
            name=name,
            instruction=instruction,
            description=description,
            tools=tools or [],
            sub_agents=subAgentList or [],
            output_key=outputKey
        )
        print(f"✅ sub agent '{subAgent.name}' created using model '{subAgent.model}'.")
    except Exception as e:
        print(f"❌ Could not create sub agent. Check API Key ({subAgent.model}). Error: {e}")
    return subAgent


