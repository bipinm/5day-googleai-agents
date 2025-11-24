# AI-Powered Autonomous Agents for Enterprise Asset Management

![License](https://img.shields.io/badge/Educational-Nikhil_&_Bipin-blue)
![AI Framework](https://img.shields.io/badge/AI_Framework-Google_ADK-orange)
![Language](https://img.shields.io/badge/Language-Python_3.12+-blue)
![AI Platform](https://img.shields.io/badge/AI_Platform-Vertex_AI-green)
![Vision](https://img.shields.io/badge/Vision-Roboflow-purple)

> Note: Created as part of the `5-Day AI Agents Intensive Course with Google` learning project.

A multi-agent AI system built with Google's AI Agent Developer Kit (ADK) that automates and optimizes maintenance workflows for Enterprise Asset Management (EAM). 
The system features two complementary autonomous agent flows: 
- **Reactive defect detection** through image analysis 
- **Proactive risk mitigation** through weather impact analysis.

## 🎯 Overview

This project demonstrates advanced agentic AI patterns including:
- **Multi-agent orchestration** with sequential and parallel execution
- **Computer vision integration** using Vertex AI and Roboflow APIs
- **Machine learning models** for classification and detection
- **KNN-based risk analysis** with historical data correlation (Simulation)
- **CMMS integration** for automated work order and activity generation
- **Session management and state sharing** across agent workflows
- **Agents in local and Vertex AI** accessible via APIs 

## Demo
[Youtube Video](https://youtu.be/XtYsXQptKmo)

### Features

#### 1️⃣ Image Analysis Agent (Reactive Flow)
- Automated defect detection from asset images
- Multi-stage pipeline: classification → detection → work order creation
- Parallel processing for annotations and work activities
- Integration with Vertex AI Vision and Roboflow APIs
- Automatic work order generation with annotated images

#### 2️⃣ Weather Impact Analysis Agent (Proactive Flow)
- Predictive risk assessment for weather events
- KNN-based historical pattern matching
- Risk scoring algorithm (incident history, condition, age, criticality)
- Automated preventive maintenance work orders
- Asset-specific impact analysis

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or higher
- Google Cloud Project with Vertex AI enabled
- Custom Image Classifier (for real detector, optional)
- Roboflow API key (for real detector, optional)
- CMMS API access (for work order/activity creation)
- zrok or ngrok for localhost tunneling, if you wish to deploy the weather impact analysis agent to **Vertex Engine** and test against CMMS running locally 
- [CMMS Demo App](https://github.com/bipinm/sensei_express_cmms)

### Environment Setup

1. **Clone the repository**

2. **Set up environment variables**
   - Rename the .env.sample file and update configuration values

3. **Configure Google Cloud credentials**
   - Rename `google-account-file.json.sample` to `google-account-file.json` 
   - Add your service account credentials
---

## 📸 Image Analysis 

### Installation

1. **Install dependencies**
```bash
  cd image_analysis
  pip install -r requirements.txt
```

### Running Locally

1. Ensure the CMMS app is running
2. Start ADK local agent

```bash
  adk api_server
```
By default, the server will run on `http://localhost:8000`

### Mock vs Real Components

- **Mock Mode** (default): Uses predefined responses for testing without API calls
- **Real Mode**: Integrates with Vertex AI and Roboflow APIs
  - Set `use_mock_classifier=False` for real Vertex AI classification
  - Set `use_mock_detector=False` for real Roboflow detection
  - Change at line `factory = AgentFactory(config_manager, use_mock_classifier=True, use_mock_detector=True)` in `agent.py`
---

## 🌤️ Weather Impact Analysis Project

### Installation

1. **Install dependencies**
   ```bash
   cd weather_impact_analysis
   pip install -r requirements.txt
   ```

### Deploy to Vertex Engine in GCP
```bash
  export GOOGLE_APPLICATION_CREDENTIALS="/Users/I038437/Code/learn/5day-googleai-agents/google-account-file.json"
  adk deploy agent_engine --project=cellular-hybrid-478513-h7 --region=us-west1 weather_impact_analysis --agent_engine_config_file=weather_impact_analysis/.agent_engine_config.json

```
---

## 📁 Project Structure

```
├── image_analysis/              # Image analysis agent package
│   ├── agent.py                # Root agent definition
│   ├── agents.py               # All agent implementations including the orchestrator
│   ├── primary_classifier.py   # Vertex AI classifier
│   ├── roboflow_detector.py    # Roboflow detector
│   ├── image_annotator.py      # Image annotator
│   ├── work_order.py           # Work order creation
│   └── work_activity.py        # Work activity creation
├── weather_impact_analysis/    # Weather analysis agent package
│   ├── agent.py                # Root agent definition
│   ├── knn_analyzer.py         # KNN and risk scoring
│   ├── work_order.py           # Work order creation
│   ├── work_activity.py        # Work activity creation
│   └── data/                   # Sample data CSVs
├── scripts/                    # Utility scripts for creating initial Tickets in CMMS
│   ├── submit_inspection_ticket.py
│   ├── submit_weather_ticket.py
│   └── images/                 # Sample images
├── tutorials/                  # Learning materials
│   └── day-*-*.py             # Daily tutorial exercises
├── main.py                     # Image analysis entry point
├── agent_config.json           # Detector model configuration
└── .env                        # Environment variables
```
---

### 🧪 Testing

1. Start CMMS app locally
2. Use the scripts to create ticket in CMMS
3. In CMMS, use the `AI Analyse` button to call agent endpoint
    - For Image Analysis - `http://localhost:8000`
    - For Weather Impact Analysis - `https://{region}-aiplatform.googleapis.com`

---

## 🛠️ Configuration Files

### agent_config.json
Maps primary classification asset types to Roboflow image models:
```json
{
  "image_classifier_models": [
    {"ElectricityDistribution": [{"tower_defect": "model-id/version"}]},
    {"PCB": [{"defect-detection": "model-id/version"}]}
  ]
}
```
---

---

## ⚠️ Known Limitations

- ⚠️ **This is an educational project.** and must be used accordingly
- AI-generated code may contain bugs
- Mock/Partial implementations for some integrations

---

## 🤝 Contributing

This is an educational project. Feel free to fork and experiment!

---

## 📄 License

Educational use only - Created by Nikhil & Bipin

---

## 🙏 Acknowledgments

- Generated as part of the Google AI Agents workshop
- Built with AI assistance (~60% AI-generated code)
- Google AI Agent Developer Kit (ADK) for agent orchestration
- Vertex AI for vision and AI capabilities
- Roboflow for defect detection models
- Python for backend implementation
- And finally, 2 BIG 🧠🧠

---

**Disclaimer**: This project is for educational purposes only. Use at your own risk.