from google.adk.agents.llm_agent import Agent
from google.adk.tools import AgentTool

from image_analysis import ConfigManager, AgentFactory
import logging

logging.basicConfig(
  level=logging.DEBUG,
  format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

config_manager = ConfigManager()

# Pre-requisite: Ensure real classifier is deployed and VERTEX_AI_* & ROBOFLOW_API_KEY is set in .env file
# Un-comment the following line to avoid using mocks
# factory = AgentFactory(config_manager, use_mock_classifier=False, use_mock_detector=False)

# Create agent factory with mock components for testing
factory = AgentFactory(config_manager, use_mock_classifier=True, use_mock_detector=True)

# Create orchestrator agent
orchestrator = factory.create_orchestrator()

root_agent = Agent(
  model="gemini-2.5-flash-lite",
  name="root_agent",
  description="Master agent to perform image analysis tasks.",
  instruction="""
    You are an expert image analysis agent.
    - Use the 'orchestrator' tool with `input_image_path` to answer image analysis requests by performing primary classification, detailed fault detection, and work order creation.
    - **DO NOT** derieve the primary classification from the input description. Always use the orchestrator tool to get accurate classification.
    - Generate a summary in English of the analysis results including any created work orders and activities.
      - Format the output in markdown and use emojis for visual appeal 
    """,
  tools=[AgentTool(orchestrator)],
  output_key="input_image_path"
)
