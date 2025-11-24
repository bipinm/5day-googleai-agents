"""
Work activity creation functionality for image analysis problems.
"""
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

# Try relative import first (for package usage), fall back to absolute import (for deployment)
try:
    from .auth_manager import AuthManager
except ImportError:
    from auth_manager import AuthManager


class WorkActivityManager:
    """Manages work activity creation and API communication."""

    def __init__(self):
        self.auth_manager = AuthManager()
        self.base_url = self.auth_manager.base_url
        self.work_activities_url = f"{self.base_url}/work-activities"

    def create_work_activity(
        self,
        work_order_id: int,
        description: str,
        status: str = "PENDING",
        priority: str = "MEDIUM",
        activity_type: str = "MAINTENANCE",
        duration_minutes: int = 120,
        notes: Optional[str] = None,
        person_id: Optional[int] = None,
        problem_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new work activity."""
        # Get auth headers from auth manager
        auth_headers = self.auth_manager.get_auth_headers()
        if not auth_headers:
            return {
                "status": "error",
                "message": "Failed to authenticate"
            }

        headers = {
            "Content-Type": "application/json",
            **auth_headers
        }

        work_activity_data = {
            "workOrderId": work_order_id,
            "description": description,
            "plannedStartDate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "plannedEndDate": (datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "status": status,
            "durationMinutes": duration_minutes,
        }

        if notes:
            work_activity_data["notes"] = notes

        if person_id:
            work_activity_data["personId"] = person_id

        if problem_type:
            work_activity_data["problemType"] = problem_type

        try:
            response = requests.post(
                self.work_activities_url,
                headers=headers,
                json=work_activity_data
            )
            response.raise_for_status()
            activity_id = response.json().get('data').get('id')
            print("Work activity created successfully with ID:", activity_id)
            return {
                "status": "success",
                "activity_id": activity_id,
                "data": response.json().get('data')
            }
        except requests.exceptions.RequestException as e:
            error_msg = f"Error creating work activity: {e}"
            if hasattr(e, 'response') and e.response.text:
                error_msg += f"\nResponse: {e.response.text}"
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

    def create_work_activity_from_input(
        self,
        work_activity: Dict[str, Any],
        work_order_id: int,
        primary_classification: str
    ) -> Dict[str, Any]:
        """
        Create a single work activity based on input data.

        Args:
            work_activity: AI generated work activity data (can be plain JSON or wrapped)
            work_order_id: ID of the parent work order
            primary_classification: Primary classification of the image

        Returns:
            Dict containing work activity creation result
        """
        if not work_activity:
            return {
                "status": "skipped",
                "message": "No work activity data provided"
            }

        if not work_order_id:
            return {
                "status": "error",
                "message": "Work order ID is required to create work activity"
            }

        # Check if work_activity has a wrapper attribute containing the actual fields
        work_activity_data = work_activity

        # Try to detect and unwrap if it's a wrapped object
        for wrapper_key in ['data', 'work_activity', 'payload', 'fields', 'content']:
            if wrapper_key in work_activity and isinstance(work_activity[wrapper_key], dict):
                # Check if the wrapper contains the expected work activity fields
                wrapped_content = work_activity[wrapper_key]
                if any(key in wrapped_content for key in ['description', 'notes', 'priority', 'status', 'problemType']):
                    work_activity_data = wrapped_content
                    break

        # Extract fields with defaults
        description = work_activity_data.get('description', 'Work activity for detected problem')
        priority = work_activity_data.get('priority', 'MEDIUM')
        notes = work_activity_data.get('notes', f'Work activity for {primary_classification} problem')
        status = work_activity_data.get('status', 'PENDING')
        activity_type = work_activity_data.get('type', 'MAINTENANCE')
        problem_type = work_activity_data.get('problemType', 'OTHER')
        duration_minutes = work_activity_data.get('durationMinutes', 120)
        person_id = work_activity_data.get('personId')

        # Adjust duration based on priority
        if priority == "HIGH" or priority == "CRITICAL":
            duration_minutes = max(duration_minutes, 180)
        elif priority == "LOW":
            duration_minutes = min(duration_minutes, 60)

        return self.create_work_activity(
            work_order_id=work_order_id,
            description=description,
            priority=priority,
            status=status,
            activity_type=activity_type,
            duration_minutes=duration_minutes,
            notes=notes,
            person_id=person_id,
            problem_type=problem_type
        )

