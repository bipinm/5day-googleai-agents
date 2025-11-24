import os
import logging
import vertexai
import pandas as pd
from typing import List, Dict, Any
import importlib.resources as pkg_resources
from google.adk.agents import Agent
from google.adk.tools import AgentTool, ToolContext

# Try relative import first (for package usage), fall back to absolute import (for deployment)
try:
    from .knn_analyzer import WeatherKNN, AssetImpactAnalyzer
    from .work_order import WorkOrderManager
    from .work_activity import WorkActivityManager
except ImportError:
    from knn_analyzer import WeatherKNN, AssetImpactAnalyzer
    from work_order import WorkOrderManager
    from work_activity import WorkActivityManager

# Import data module for resource loading
try:
    from weather_impact_analysis import data
except ImportError:
    # If package import fails, we're in deployment mode
    # Create a data module reference
    import sys
    from types import ModuleType
    data = ModuleType('data')
    data.__file__ = os.path.join(os.path.dirname(__file__), 'data')

logger = logging.getLogger(__name__)

vertexai.init(
  project=os.environ["GOOGLE_CLOUD_PROJECT"],
  location=os.environ["GOOGLE_CLOUD_LOCATION"],
)

# Global variables to hold analyzers (accessible by tool functions)
_knn_analyzer: WeatherKNN = None
_impact_analyzer: AssetImpactAnalyzer = None


def _load_csv_data():
  """Load CSV data files using importlib.resources with fallback to direct file paths"""
  global _knn_analyzer, _impact_analyzer

  try:
    # Try loading from package resources first
    try:
      logger.info("Attempting to load CSV files from package resources...")
      with pkg_resources.open_text(data, "historical_weather_events.csv") as f:
        events_df = pd.read_csv(f)

      with pkg_resources.open_text(data, "assets.csv") as f:
        assets_df = pd.read_csv(f)

      with pkg_resources.open_text(data, "historical_incidents.csv") as f:
        incidents_df = pd.read_csv(f)

      logger.info("Successfully loaded CSV files from package resources")

    except (FileNotFoundError, AttributeError, TypeError) as e:
      # Fallback to direct file path loading (for deployment scenarios)
      logger.warning(f"Package resource loading failed: {e}. Trying direct file paths...")

      # Get the directory where this file is located
      base_dir = os.path.dirname(os.path.abspath(__file__))
      data_dir = os.path.join(base_dir, 'data')

      logger.info(f"Loading from directory: {data_dir}")

      events_df = pd.read_csv(os.path.join(data_dir, "historical_weather_events.csv"))
      assets_df = pd.read_csv(os.path.join(data_dir, "assets.csv"))
      incidents_df = pd.read_csv(os.path.join(data_dir, "historical_incidents.csv"))

      logger.info("Successfully loaded CSV files from direct file paths")

    # Initialize analyzers
    _knn_analyzer = WeatherKNN(k=5)
    _knn_analyzer.load_historical_data(events_df)

    _impact_analyzer = AssetImpactAnalyzer(assets_df, incidents_df)

    logger.info(f"Successfully loaded CSV data: {len(events_df)} events, {len(assets_df)} assets, {len(incidents_df)} incidents")

  except Exception as e:
    logger.error(f"Error loading CSV data: {e}")
    import traceback
    logger.error(traceback.format_exc())
    raise


# Load data on module import
_load_csv_data()


# --- Tool Functions for Weather Analysis ---

def find_similar_weather_events(
    temperature_c: float,
    wind_speed_kmh: float,
    precipitation_mm: float,
    humidity_percent: float,
    duration_hours: int
) -> dict:
  """
  Finds similar historical weather events using K-Nearest Neighbors algorithm.

  Args:
      temperature_c: Temperature in Celsius
      wind_speed_kmh: Wind speed in km/h
      precipitation_mm: Precipitation in millimeters
      humidity_percent: Humidity percentage
      duration_hours: Duration in hours

  Returns:
      Dictionary with status and list of similar historical events with similarity distances.
  """
  try:
    logger.info(f"Finding similar events for weather: {temperature_c}°C, {wind_speed_kmh} km/h wind")

    current_event = {
      'temperature_c': temperature_c,
      'wind_speed_kmh': wind_speed_kmh,
      'precipitation_mm': precipitation_mm,
      'humidity_percent': humidity_percent,
      'duration_hours': duration_hours
    }

    # Find k nearest neighbors
    similar_events = _knn_analyzer.find_similar_events(current_event)

    # Get details for each similar event
    results = []
    for event_id, distance in similar_events:
      event_details = _knn_analyzer.get_event_details(event_id)
      results.append({
        'event_id': int(event_id),
        'similarity_distance': round(float(distance), 3),
        'date': event_details['date'],
        'event_type': event_details['event_type'],
        'severity': event_details['severity'],
        'temperature_c': event_details['temperature_c'],
        'wind_speed_kmh': event_details['wind_speed_kmh'],
        'precipitation_mm': event_details['precipitation_mm']
      })

    return {
      'status': 'success',
      'found_count': len(results),
      'similar_events': results,
      'event_ids': [r['event_id'] for r in results]
    }

  except Exception as e:
    logger.error(f"Error finding similar events: {e}")
    return {'status': 'error', 'message': str(e)}


def analyze_affected_assets(event_ids: List[int]) -> dict:
  """
  Analyzes which assets were affected in historical weather events.

  Args:
      event_ids: List of event IDs from similar historical events

  Returns:
      Dictionary with status and analysis of affected assets, damage patterns, and risk factors.
  """
  try:
    logger.info(f"Analyzing affected assets for events: {event_ids}")

    # Get affected assets
    affected_assets = _impact_analyzer.get_affected_assets(event_ids)

    # Analyze risk patterns
    risk_analysis = _impact_analyzer.analyze_risk_patterns(affected_assets)

    return {
      'status': 'success',
      'risk_analysis': risk_analysis
    }

  except Exception as e:
    logger.error(f"Error analyzing affected assets: {e}")
    return {'status': 'error', 'message': str(e)}


def predict_at_risk_assets(
    total_incidents: int,
    by_asset_type: dict,
    by_criticality: dict,
    by_damage_severity: dict
) -> dict:
  """
  Predicts which current assets are at risk based on historical patterns.

  Args:
      total_incidents: Total number of historical incidents
      by_asset_type: Dictionary of incident counts by asset type
      by_criticality: Dictionary of incident counts by criticality level
      by_damage_severity: Dictionary of incident counts by damage severity

  Returns:
      Dictionary with status and list of assets with risk scores sorted by risk level.
  """
  try:
    logger.info("Predicting at-risk assets")

    # Reconstruct risk analysis from parameters
    risk_analysis = {
      'total_incidents': total_incidents,
      'by_asset_type': by_asset_type,
      'by_criticality': by_criticality,
      'by_damage_severity': by_damage_severity
    }

    # Predict at-risk assets
    at_risk_assets = _impact_analyzer.predict_at_risk_assets(risk_analysis)

    return {
      'status': 'success',
      'at_risk_count': len(at_risk_assets),
      'top_10_at_risk': at_risk_assets[:10],
      'all_at_risk': at_risk_assets
    }

  except Exception as e:
    logger.error(f"Error predicting at-risk assets: {e}")
    return {'status': 'error', 'message': str(e)}


# --- Create Agent ---

work_order_manager = WorkOrderManager()
work_activity_manager = WorkActivityManager()

def create_work_order(
    tool_context: ToolContext,
    work_order: Dict[str, Any]
) -> Dict[str, Any]:
  """Create a work order based on detected problems."""
  result = work_order_manager.create_work_order_from_input(work_order)
  tool_context.state["work_order_id"] = result.get("work_order_id", None)
  return result

def create_work_activity(
    tool_context: ToolContext,
    work_activity: Dict[str, Any],
) -> Dict[str, Any]:
  """Create a work activity based on a detected problem."""
  work_order_id = tool_context.state.get("work_order_id", None)
  return work_activity_manager.create_work_activity_from_input(work_activity, work_order_id)

# --- Create Agents ---

def create_work_order_agent() -> Agent:
  """Create the work order creation agent."""
  return Agent(
    name="Work_Order_Agent",
    model="gemini-2.5-flash",
    instruction="""
        You are a work order creation agent.
        - Use `create_work_order()` tool to create a work order for the risks identified.
        - JSON payload for creating work order 
        ```json
        {
          "description": Short description of the inspection required (Max 8 words),
          "notes": Max 300 word description of the risk factors, inspection and actions required, Must be in markdown format,
          "status": "NEW",
          "priority": Based on criticality of detected problems: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
          "type": "INSPECTION"
          "assets": List of asset codes requiring inspection
        }
        ```
        - Format notes clearly with sections, bullet points, and key metrics. Use emojis for visual appeal: 🔴 for critical, 🟠 for high, 🟡 for medium risk.
        - After creating the work order, invoke the `work_activity_agent` to create work activity for each inspection item.
        - JSON payload for creating work activity 
        ```json
        {
          "description": Max 5-7 word description of the inspection or repair task,
          "notes": Max 100 word description of the risk factors and inspection and potential action required, Must be in markdown format,
          "status": "PENDING",
          "priority": Based on criticality of detected problems: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
          "problemType": "SAFETY"
          "asset": Asset code requiring inspection,
          "durationMinutes": Estimated duration in minutes (e.g., 120 for 2 hours)
        }
        ```                
        - Return the `id` field of the work order and number of activities created.
        - If any error occurs return 'None' and nothing else.
    """,
    tools=[create_work_order, create_work_activity],
    output_key="work_order_id"
  )


def create_risk_analyser_agent() -> Agent:
  return Agent(
    name="Weather_Risk_Analyzer",
    model="gemini-2.5-flash",
    instruction="""
        You are a weather impact analysis expert for railway and electricity 
        distribution infrastructure. You help predict which assets are at risk
        when severe weather events occur.
        
        Your task is to analyze weather events and predict at-risk assets:
        
        1. FIND SIMILAR EVENTS: Use find_similar_weather_events tool with the current
           weather parameters (temperature_c, wind_speed_kmh, precipitation_mm, 
           humidity_percent, duration_hours) to find historical similar events.
        
        2. ANALYZE HISTORICAL IMPACTS: Use analyze_affected_assets tool with the 
           event_ids returned from step 1 to understand which assets were damaged
           in similar past events.
        
        3. PREDICT AT-RISK ASSETS: Use predict_at_risk_assets tool with the 
           risk_analysis data (total_incidents, by_asset_type, by_criticality, 
           by_damage_severity) returned from step 2 to identify current assets at risk.
        
        4. Output a JSON summary of your findings with exactly the requested fields and no extra information.
          {
              "events": List of similar historical weather events with details,
              "affected_asset_types" : List of affected asset types,
              "historical_impact_patterns": Max 20 word summary of historical impact patterns,
              "estimated_downtime_hours": estimated downtime in hours
              "estimated_repair_cost": estimated repair cost
              "number_of_at_risk_assets": number of assets predicted at risk,
              "incident_statistics": {
                  "critical": number of critical incidents,
                  "high": number of high incidents,
                  "medium": number of medium incidents,
                  "low": number of low incidents
              },
              "top_at_risk_assets": [
                  {
                      "id": id of asset
                      "criticality": criticality level
                      "risk_score": risk score (0-100)
                      "incident_count": number of similar Historical incidents
                      "condition_score": current condition
                  },
                  ...
              ]
          }
          - The events list should be a string list of event summary lines similar to following examples
             - "Strong Wind (Temperature: 9°C, Wind: 98 km/h, Precipitation: 7mm, Severity: Critical)"
             - "Strong Wind (Temperature: 20°C, Wind: 105 km/h, Precipitation: 10mm, Severity: Critical)"
        """,
    tools=[
      find_similar_weather_events,
      analyze_affected_assets,
      predict_at_risk_assets
    ]
  )

root_agent = Agent(
  name="Weather_Impact_Mitigator",
  model="gemini-2.5-flash",
  instruction="""
      You are a weather impact mitigation expert
      Your task is to analyze weather risk findings and create work orders and activities for field inspections.
      1. Use the `Weather_Risk_Analyzer` agent to analyze the weather risk findings JSON input.
      2. JSON weather payload example for risk findings:
      ```json
      {
        "temperature_c": 1,
        "wind_speed_kmh": 150,
        "precipitation_mm": 5,
        "humidity_percent": 25,
        "duration_hours": 2,
        "event_type": "Strong Winds",
        "severity": "High",
        "location": "Central Operations District"
      }
      ```
      3. Based on the risk findings, use the `Work_Order_Agent` to create Orders and Activities for field inspections.
      4. Return the created work order ID and number of activities created.
  """,
  tools=[AgentTool(create_risk_analyser_agent()), AgentTool(create_work_order_agent())],
  output_key="work_order_summary"
)
