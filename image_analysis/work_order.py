"""
Work order creation functionality for image analysis problems.
"""

import time
import mimetypes
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# Try relative import first (for package usage), fall back to absolute import (for deployment)
try:
    from .auth_manager import AuthManager
except ImportError:
    from auth_manager import AuthManager


class WorkOrderManager:
    """Manages work order creation and API communication."""

    def __init__(self):
        self.auth_manager = AuthManager()
        self.base_url = self.auth_manager.base_url
        self.work_orders_url = f"{self.base_url}/work-orders"

    def create_work_order(
        self,
        title: str,
        description: str,
        status: str = "NEW",
        priority: str = "LOW",
        work_order_type: str = "MAINTENANCE",
        days_until_due: int = 7,
        notes: Optional[str] = None,
        asset_ids: Optional[list] = None,
        skill_ids: Optional[list] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new work order."""
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

        work_order_data = {
            "title": title,
            "description": description,
            "status": status,
            "priority": priority,
            "type": work_order_type,
            "dueDate": (datetime.now(timezone.utc) + timedelta(days=days_until_due)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        }

        if notes:
            work_order_data["notes"] = notes

        if asset_ids:
            work_order_data["assetIds"] = asset_ids

        if skill_ids:
            work_order_data["skillIds"] = skill_ids

        try:
            response = requests.post(
                self.work_orders_url,
                headers=headers,
                json=work_order_data
            )
            response.raise_for_status()
            wo_id = response.json().get('data').get('id')
            print("Work order created successfully with ID:", wo_id)
            return {
                "status": "success",
                "work_order_id": wo_id,
                "data": response.json().get('data')
            }
        except requests.exceptions.RequestException as e:
            error_msg = f"Error creating work order: {e}"
            if hasattr(e, 'response') and e.response.text:
                error_msg += f"\nResponse: {e.response.text}"
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

    def create_work_order_from_input(
        self,
        work_order: Dict[str, Any],
        primary_classification: str
    ) -> Dict[str, Any]:
        """
        Create a work order based on detected problems.

        Args:
            work_order: AI generated work order data (can be plain JSON or wrapped)
            primary_classification: Primary classification of the image

        Returns:
            Dict containing work order creation result
        """
        if not work_order:
            return {
                "status": "skipped",
                "message": "No problems detected, work order not created"
            }

        # Check if work_order has a wrapper attribute containing the actual fields
        # Common wrapper attributes: 'data', 'work_order', 'payload', 'fields'
        work_order_data = work_order

        # Try to detect and unwrap if it's a wrapped object
        for wrapper_key in ['data', 'work_order', 'payload', 'fields', 'content']:
            if wrapper_key in work_order and isinstance(work_order[wrapper_key], dict):
                # Check if the wrapper contains the expected work order fields
                wrapped_content = work_order[wrapper_key]
                if any(key in wrapped_content for key in ['description', 'notes', 'priority', 'status', 'type']):
                    work_order_data = wrapped_content
                    break

        # Extract fields with defaults
        description = work_order_data.get('description', 'Problem detected in image analysis')
        priority = work_order_data.get('priority', 'MEDIUM')
        notes = work_order_data.get('notes', f'Image analysis detected issues in {primary_classification}')
        status = work_order_data.get('status', 'NEW')
        work_order_type = work_order_data.get('type', 'MAINTENANCE')

        # Use description as title (truncate if too long)
        title = description if len(description) <= 100 else description[:97] + "..."

        return self.create_work_order(
            title=title,
            description=description,
            priority=priority,
            status=status,
            work_order_type=work_order_type,
            notes=notes,
            days_until_due=7 if priority != "CRITICAL" else 3
        )

    def upload_image_to_work_order(
        self,
        work_order_id: int,
        file_path: str,
        name: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload an image file to a work order.

        Args:
            work_order_id: The ID of the work order to attach the image to
            file_path: Path to the image file to upload
            name: Optional custom name for the attachment
            notes: Optional notes about the attachment

        Returns:
            Dict containing upload result with status and data
        """
        print(f"Starting image upload to work order {work_order_id}")
        print(f"File path: {file_path}")

        # Get auth headers from auth manager
        auth_headers = self.auth_manager.get_auth_headers()
        if not auth_headers:
            return {
                "status": "error",
                "message": "Failed to authenticate"
            }

        # Validate file exists
        path_obj = Path(file_path)
        if not path_obj.is_file():
            print(f"❌ File not found: {file_path}")
            return {
                "status": "error",
                "message": f"File not found: {file_path}"
            }

        # Determine content type
        content_type = mimetypes.guess_type(path_obj.name)[0] or "application/octet-stream"

        # Prepare form data
        data = {
            "sourceObjectType": "WORK_ORDER",
            "sourceObjectId": str(work_order_id),
            "name": name or path_obj.name,
            "type": content_type,
        }
        if notes:
            data["notes"] = notes
        # Upload the file
        upload_url = f"{self.base_url}/attachments/upload"
        print(f"\nUploading to: {upload_url}")

        try:
            with path_obj.open("rb") as file_handle:
                files = {"file": (path_obj.name, file_handle, content_type)}
                print("Sending POST request...")
                response = requests.post(
                    upload_url,
                    data=data,
                    files=files,
                    headers=auth_headers,
                    timeout=60,
                )
                print(f"Response status: {response.status_code}")
                response.raise_for_status()
                result = response.json()

                print(f"{'='*60}")
                print(f"✅ Image uploaded successfully to work order {work_order_id}")
                if "data" in result and "id" in result.get("data", {}):
                    print(f"Attachment ID: {result['data']['id']}")
                print(f"{'='*60}\n")

                return {
                    "status": "success",
                    "data": result.get("data", {})
                }
        except requests.exceptions.RequestException as e:
            print(f"{'='*60}")
            print(f"❌ Upload failed!:  {e}")
            error_msg = f"Error uploading image: {e}"
            if hasattr(e, 'response') and e.response is not None:
              print(f"Image uploaded successfully to work order {work_order_id}")
            return {
              "status": "error",
              "message": error_msg
            }
