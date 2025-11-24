# AI-Powered Autonomous Agents for Enterprise Asset Management

## Project Overview

This project introduces a sophisticated multi-agent AI system designed to revolutionize Enterprise Asset Management (EAM) by automating and optimizing maintenance workflows. The system employs two distinct, yet complementary, autonomous agentic flows: a **reactive flow** for analyzing asset images to detect and report defects, and a **proactive flow** for assessing risks from weather events to prevent potential failures. By leveraging a combination of Large Language Models (LLMs) like Google's Gemini, specialized machine learning models, and integrations with external APIs, these agents can autonomously analyze situations, make decisions, and execute complex tasks, culminating in the automatic generation of detailed work orders and activities within a Computerized Maintenance Management System (CMMS).

The core of the architecture is a collaborative network of agents, each with a specialized function. These agents work together, sharing context and data through a centralized state management system, to move from initial trigger to final resolution without human intervention.

---

## Flow 1: Reactive Defect Detection via Image Analysis

This flow is designed to react to visual evidence of asset damage. When a user provides an image of an asset, a sequential chain of agents is triggered to analyze the image, identify problems, and create the necessary maintenance tasks.

### Architecture and Process

1.  **Initiation & Orchestration**: The process begins when a `Root Agent` receives an input image. It delegates the task to a `SequentialAgent` orchestrator, which manages the step-by-step execution of the analysis pipeline.

2.  **Primary Classification**: The `Primary Classifier Agent` is the first to act. It uses the **Vertex AI Vision API** to perform an initial classification of the image. Its goal is to determine if the image contains a relevant asset that requires further inspection. If not, the process can be terminated early, saving computational resources.

3.  **Problem Detection**: If the image is deemed relevant, the `Problem Detector Agent` takes over. This agent utilizes a specialized object detection model, accessed via the **Roboflow API**, to scan the image for specific types of defects (e.g., 'corrosion', 'crack', 'leak'). The output is a structured list of detected problems, including the class of each problem, a confidence score, and its precise location defined by bounding box coordinates.

4.  **Parallel Processing for Work Order & Summary**: Once defects are identified, the `Problems Processor Agent` initiates two tasks in parallel to improve efficiency:
    *   **Work Order Creation**: A `Work Order Agent` is tasked with creating a formal maintenance request. It synthesizes the detected problems into a coherent summary and calls the **CMMS API** to generate a new work order.
    *   **Problem Summarization**: Concurrently, a `Problem Summarizer Agent` generates a concise, human-readable markdown summary of all identified issues and their confidence levels.

5.  **Follow-up Actions**: After the work order is successfully created, its ID is stored in the shared context. The `Work Order Agent` then triggers a `FollowupAgent` which, in turn, runs two more parallel processes to enrich the work order:
    *   **Image Annotation**: The `Problem Annotator Agent` uses the stored bounding box data to draw visual markers directly onto the original image, highlighting the exact location of each defect. This annotated image is then uploaded to the corresponding work order via the CMMS API, providing clear visual context for maintenance technicians.
    *   **Work Activity Generation**: The `Work Activity Agent` iterates through the list of detected problems and creates a distinct work activity within the CMMS for each one. This breaks down the parent work order into granular, actionable tasks.

### Final Output

The flow concludes by generating a comprehensive markdown report containing the newly created Work Order, number of activities created, and the problem summary. The CMMS is updated with a new work order, an annotated image, and a set of specific maintenance activities.

---

## Flow 2: Proactive Risk Mitigation via Weather Impact Analysis

This proactive flow aims to prevent asset failure by analyzing impending weather events and their potential impact. It uses historical data to predict which assets are most at risk and automatically schedules preventive inspection work orders.

### Architecture and Process

1.  **Initiation & Orchestration**: The process is triggered by a JSON input containing detailed parameters of a weather event, such as temperature, wind speed, precipitation, severity, and location. A `Root Agent` receives this data and coordinates the `Weather_Risk_Analyzer` and `Work_Order_Agent`.

2.  **Risk Analysis**: The `Weather_Risk_Analyzer` executes a sequential, three-step analysis to determine the potential impact.
    *   **Step 1: Find Similar Historical Events**: The agent first queries a historical weather database using a **K-Nearest Neighbors (KNN)** algorithm. By comparing the current event's features (normalized for accuracy) against past events, it identifies historical precedents with the most similar characteristics.
    *   **Step 2: Analyze Historical Impacts**: Using the similar events found, the agent then analyzes historical incident and asset data. It correlates past weather conditions with recorded asset failures to identify patterns, such as which asset types are most vulnerable, the typical severity of damage, and the associated costs and downtime.
    *   **Step 3: Predict At-Risk Assets**: Finally, the agent uses a **Risk Scoring Algorithm** to predict which specific assets are at high risk from the current event. This algorithm calculates a weighted score for each asset based on factors like historical incident frequency (40%), current condition (30%), age (20%), and business criticality (10%).

3.  **Work Order Generation**: The list of high-risk assets and the detailed risk analysis summary are passed to the `Work_Order_Agent`. This agent then interacts with the CMMS API to automate the creation of preventive maintenance tasks:
    *   **Create Work Order**: It first generates a single, overarching **INSPECTION** work order. The priority of this work order is set based on the overall risk level, and the list of at-risk assets is attached.
    *   **Create Work Activities**: Subsequently, it creates individual work activities under that work order, one for each at-risk asset identified. These activities instruct technicians to perform safety inspections and preventive maintenance.

### Final Output

The proactive flow concludes with an output detailing the created `work_order_id` and a summary of the risk mitigation actions proposed, including the number of inspection activities generated. This ensures that the organization can take preemptive measures to protect its most vulnerable assets before and soon after the weather event occurs.

---

## Future Enhancements & Ideas

1.  **Dynamic Agent Composition**: Implement a meta-agent that can dynamically assemble agent workflows based on the specific problem, rather than relying on pre-defined chains. This would allow the system to adapt to novel situations and create more efficient, context-specific solutions.

2.  **Self-Healing and Optimization**: Introduce a "supervisor" agent that monitors the performance of other agents, identifies bottlenecks or failures, and attempts to self-heal by re-routing tasks, adjusting parameters, or triggering alerts for human intervention when autonomous resolution is not possible.

3.  **Predictive Maintenance Scheduling**: Enhance the proactive flow to not just create inspection orders but also predict optimal maintenance schedules. By analyzing asset lifecycle data, usage patterns, and long-term failure predictions, the system could move from proactive risk mitigation to truly predictive maintenance.

4.  **Multi-Modal Inputs**: Extend the reactive flow to accept and process other forms of input beyond static images. This could include sensor data (e.g., temperature, vibration from IoT devices), audio streams (e.g., detecting unusual machine noises), or technician reports submitted in natural language.

5.  **Cost-Benefit Analysis Agent**: Add a specialized agent that performs a real-time cost-benefit analysis for proposed maintenance activities. This agent would weigh the cost of the repair against the potential cost of failure (including downtime, safety risks, and secondary damages) to help prioritize tasks based on financial and operational impact.

6.  **Integration with Supply Chain Management**: Connect the agents to inventory and supply chain systems. This would enable them to automatically check for spare parts availability when a maintenance activity is created and, if necessary, generate a purchase requisition to ensure parts are available when the technician arrives.

7.  **Advanced Human-in-the-Loop Feedback**: Develop a more sophisticated feedback mechanism where technicians can easily provide input on the accuracy of AI-driven diagnoses and the effectiveness of the prescribed actions. This feedback would be used to continuously fine-tune the underlying models, allowing the agents to learn from real-world outcomes and improve their decision-making over time.

8.  **Retrieval-Augmented Generation (RAG) for Deeper Insights**: Implement RAG to allow agents to query a vast knowledge base of technical manuals, historical maintenance records, and best practice guides. When a defect is identified, an agent could retrieve the specific repair protocol for that asset model and fault, attaching it directly to the work order to improve first-time fix rates. Similarly, for proactive analysis, RAG could be used to find obscure but critical information from historical incident reports.

9.  **AI-Powered Quality Assurance and Performance Rating**: Introduce a post-work analysis agent that assesses the quality of completed maintenance tasks. This agent could analyze "after" images of the repair, compare them to the "before" images and the work order requirements, and assign a quality score. This score could then be used to automatically rate the effectiveness of the repair and the performance of the technician, providing a feedback loop for continuous improvement and performance management.

---

## Conclusion

In conclusion, this multi-agent system demonstrates a powerful dual approach to enterprise asset management, combining reactive defect detection with proactive risk mitigation to enhance operational efficiency and asset longevity.
