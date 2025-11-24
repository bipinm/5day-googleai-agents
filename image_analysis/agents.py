"""
Agent definitions and orchestration for image analysis.
"""

from typing import Dict, Any
from google.adk.agents import LlmAgent, ParallelAgent, BaseAgent, SequentialAgent
from google.adk.tools import AgentTool, ToolContext
from .config import ConfigManager
from .primary_classifier import PrimaryClassifier
from .roboflow_detector import RoboflowDetector, DetectionProcessor
from .image_annotator import ImageAnnotator
from .work_order import WorkOrderManager
from .work_activity import WorkActivityManager


class AgentFactory:
    """Factory for creating configured agents."""

    def __init__(
        self,
        config_manager: ConfigManager,
        use_mock_classifier: bool = False,
        use_mock_detector: bool = False
    ):
        self.config_manager = config_manager
        self.classifier = PrimaryClassifier(config_manager, use_mock=use_mock_classifier)
        self.detector = RoboflowDetector(config_manager, use_mock=use_mock_detector)
        self.annotator = ImageAnnotator()
        self.work_order_manager = WorkOrderManager()
        self.work_activity_manager = WorkActivityManager()

    # Tool functions for agents

    def vertex_ai_image_classifier(self, tool_context: ToolContext, image_path: str) -> Dict[str, Any]:
        """Primary classification tool."""
        tool_context.state["input_image_path"] = image_path
        return self.classifier.classify(image_path)

    def roboflow_detect(self, tool_context: ToolContext, primary_classification: str) -> Dict[str, Any]:
        """Problem detection tool."""
        image_path = tool_context.state.get("input_image_path", None)
        tool_context.state["primary_classification"] = primary_classification
        result = self.detector.detect(image_path, primary_classification)
        tool_context.state["problems_detected"] = result
        return result

    def summarize_detections(self, tool_context: ToolContext) -> str:
        """Summarize detection results."""
        roboflow_result = tool_context.state.get("problems_detected", None)
        print("="*180)
        print("Getting `problems_detected` context state in summarize_detections:")
        print(roboflow_result)
        print(type(roboflow_result))
        print("="*180)

        return DetectionProcessor.summarize(roboflow_result)

    def annotate_bounding_boxes(self, tool_context: ToolContext) -> str:
        """Draw bounding boxes on image."""
        image_path = tool_context.state.get("input_image_path", None)
        roboflow_result = tool_context.state.get("problems_detected", None)
        print("="*180)
        print("Getting `problems_detected` context state in annotate_bounding_boxes:")
        print(roboflow_result)
        print(type(roboflow_result))
        print("="*180)
        output_path = self.annotator.annotate(image_path, roboflow_result)
        tool_context.state["annotated_image_path"] = output_path

    def create_work_order_from_problems(self, tool_context: ToolContext, work_order: Dict[str, Any]) -> Dict[str, Any]:
        """Create a work order based on detected problems."""
        primary_classification = tool_context.state.get("primary_classification", None)
        result = self.work_order_manager.create_work_order_from_input( work_order, primary_classification)
        tool_context.state["work_order_id"] = result.get("work_order_id", None)
        return result

    def upload_image_to_work_order(self, tool_context: ToolContext):
      """Upload annotated image to work order."""
      work_order_id = tool_context.state.get("work_order_id", None)
      annotated_image_path = tool_context.state.get("annotated_image_path", None)
      return self.work_order_manager.upload_image_to_work_order(work_order_id, annotated_image_path)


    def create_work_activity_from_problem(self, tool_context: ToolContext, work_activity: Dict[str, Any]) -> Dict[str, Any]:
        """Create a work activity based on a detected problem."""
        work_order_id = tool_context.state.get("work_order_id", None)
        primary_classification = tool_context.state.get("primary_classification", None)
        return self.work_activity_manager.create_work_activity_from_input(work_activity,work_order_id, primary_classification)

    # Agent creation methods

    def create_primary_classifier_agent(self) -> LlmAgent:
      """Create the primary classification agent."""
      return LlmAgent(
        name="primary_classifier_agent",
        model="gemini-2.5-flash",
        instruction="""
                You are a primary image classifier.
                - Use the `vertex_ai_image_classifier()` tool with `input_image_path` to get a classification
                - Return a JSON output with following structure. Do not output anything else
                {
                    "classification": "<classification_name or None>",
                    "image_path": "<input_image_path>"
                }
                - Classification must be one of the predefined classes (ElectricityDistribution, RailwayTrack, TrainWagon, TrainWheel, PCB)
                - Output must not contain any additional text or explanation.
            """,
        tools=[self.vertex_ai_image_classifier],
        output_key="primary_classification"
      )

    def create_problem_detector_agent(self) -> LlmAgent:
      """Create the secondary detection agent."""
      return LlmAgent(
        name="problem_detector_agent",
        model="gemini-2.5-flash-lite",
        instruction="""
                You are a detailed image analysis agent who can detect problems given an image input.
                - Use `roboflow_detect()` tool to perform detection of problems
            """,
        tools=[self.roboflow_detect],
        output_key="defects_detected"
      )

    def create_work_order_agent(self) -> LlmAgent:
        """Create the work order creation agent."""
        return LlmAgent(
            name="work_order_agent",
            model="gemini-2.5-flash",
            instruction="""
                You are a work order creation agent.
                - Use `create_work_order_from_problems()` tool with `problems_detected`, 
                  and `primary_classification` to create a work order.
                - JSON payload for creating work order 
                ```json
                {
                  "description": Max 5-7 word description of the problem,
                  "notes": Max 100 word description of the problems detected (without listing a solution),
                  "status": "NEW",
                  "priority": "MEDIUM",
                  "type": "MAINTENANCE"
                }
                ```
                - Return a small summary of the work order created.
                - The problem note must not contain description of image analysis, X, Y co-ordinates
                - After creating the work order, invoke the `work_order_followup_agent`
                - If any error occurs return 'None' and nothing else.
            """,
            tools=[self.create_work_order_from_problems, AgentTool(self.create_work_order_followup_agent())],
            output_key="work_order_details"
        )

    def create_problem_annotator_agent(self) -> LlmAgent:
      """Create the problem annotator agent."""
      return LlmAgent(
        name="problem_annotator_sub_agent",
        model="gemini-2.5-flash-lite",
        instruction="""
                You are a problem image annotator and uploader agent
                - First Use `annotate_bounding_boxes()` tool to generate image
                - Next, upload the image using `upload_image_to_work_order()`.  
            """,
        tools=[self.annotate_bounding_boxes, self.upload_image_to_work_order]
      )

    def create_work_activities_agent(self) -> LlmAgent:
      """Create the work activity creation agent."""
      return LlmAgent(
        name="work_activity_agent",
        model="gemini-2.5-flash",
        instruction="""
                You are a work activity creation agent.
                - Use `create_work_activity_from_problem()` tool with `work_activity` to create a work activity.
                - Invoke the tool multiple times, once for each detected problem in `problems_detected`.
                - JSON payload for creating work activity 
                ```json
                {
                  "description": Max 5-7 word description of the problem,
                  "notes": Max 100 word description of the problem and potential solutions,
                  "status": "PENDING",
                  "priority": "MEDIUM",
                  "type": "MAINTENANCE",
                  "problemType": "ELECTRONIC"
                }
                ```
                - Allowed problemType values based on primary_classification: 'MECHANICAL', 'ELECTRICAL', 'ELECTRONIC', 'SOFTWARE', 'INSPECTION', 'SAFETY', 'CALIBRATION', 'OTHER'
                - Return a small summary of the work activities created.
                - If any error occurs return 'None' and nothing else.
            """,
        tools=[self.create_work_activity_from_problem],
        output_key="work_activity_details"
      )

    def create_problem_summarizer_agent(self) -> LlmAgent:
      """Create the problem summarizer agent."""
      return LlmAgent(
        name="problem_summarizer_agent",
        model="gemini-2.5-flash-lite",
        instruction="""
                You are a problem summarization agent.
                - Your task is to read the `class` names and `confidence` levels from the JSON payload
                - JSON Data: {defects_detected}
                - The output should be a problem summary based on the class names and confidence level.
                - Do not include any coordinates or image analysis details.
                - Provide a concise summary of the detected problems in plain English.
            """,
        output_key="problem_summary"
      )

    def create_work_order_followup_agent(self) -> ParallelAgent:
        """Create the work order follow-up parallel agent."""
        return ParallelAgent(
            name="work_order_followup_agent",
            sub_agents=[
                self.create_problem_annotator_agent(),
                self.create_work_activities_agent()
            ]
        )

    def create_problems_processor_parallel_agent(self) -> ParallelAgent:
        return ParallelAgent(
            name="problems_processor_agent",
            sub_agents=[
                self.create_work_order_agent(),
                self.create_problem_summarizer_agent()
            ]
        )

    def create_orchestrator(self) -> BaseAgent:
        """Create the root orchestrator agent."""
        primary_classifier_agent = self.create_primary_classifier_agent()
        problem_detector_agent = self.create_problem_detector_agent()
        problem_processor_agent = self.create_problems_processor_parallel_agent()

        return SequentialAgent(
            name="orchestrator",
            sub_agents=[
                primary_classifier_agent,
                problem_detector_agent,
                problem_processor_agent
            ]
        )
