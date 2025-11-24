"""
Work order creation functionality.
"""

import requests
from datetime import datetime, timedelta, timezone
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

    def _fetch_asset_ids(self, asset_codes: list) -> Optional[list]:
        """
        Fetch asset IDs from the API using asset codes.

        Args:
            asset_codes: List of asset codes (e.g., ['A002', 'A005'])

        Returns:
            List of asset IDs or None if fetch fails
        """
        if not asset_codes:
            return None

        # Get auth headers from auth manager
        headers = self.auth_manager.get_auth_headers()
        if not headers:
            print("Failed to authenticate for fetching asset IDs")
            return None


        # Build query string with asset codes
        codes_param = ','.join(asset_codes)
        assets_url = f"{self.base_url}/assets?codes={codes_param}"

        try:
            response = requests.get(assets_url, headers=headers)
            response.raise_for_status()
            assets_data = response.json()

            # Extract IDs from the response
            # Assuming the API returns a list of asset objects with 'id' field
            if isinstance(assets_data, list):
                asset_ids = [asset.get('id') for asset in assets_data if asset.get('id')]
                return asset_ids if asset_ids else None
            elif isinstance(assets_data, dict) and 'data' in assets_data:
                # Handle wrapped response
                assets_list = assets_data['data']
                asset_ids = [asset.get('id') for asset in assets_list if asset.get('id')]
                return asset_ids if asset_ids else None
            else:
                print(f"Unexpected assets API response format: {assets_data}")
                return None

        except requests.exceptions.RequestException as e:
            error_msg = f"Error fetching asset IDs: {e}"
            if hasattr(e, 'response') and e.response.text:
                error_msg += f"\nResponse: {e.response.text}"
            print(error_msg)
            return None

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
        work_order: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a work order based on detected problems.

        Args:
            work_order: AI generated work order data (can be plain JSON or wrapped)

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
        description = work_order_data.get('description', '')
        priority = work_order_data.get('priority', '')
        notes = work_order_data.get('notes', '')
        status = work_order_data.get('status', '')
        work_order_type = work_order_data.get('type', '')

        # Check for assets and fetch their IDs if present
        asset_ids = None
        if 'assets' in work_order_data:
            assets = work_order_data.get('assets')
            if assets:
                # Handle both list and comma-separated string formats
                if isinstance(assets, list):
                    asset_codes = assets
                elif isinstance(assets, str):
                    asset_codes = [code.strip() for code in assets.split(',')]
                else:
                    asset_codes = []

                # Fetch asset IDs from API
                if asset_codes:
                    asset_ids = self._fetch_asset_ids(asset_codes)

        # Use description as title (truncate if too long)
        title = description if len(description) <= 100 else description[:97] + "..."

        return self.create_work_order(
            title=title,
            description=description,
            priority=priority,
            status=status,
            work_order_type=work_order_type,
            notes=notes,
            days_until_due=7 if priority != "CRITICAL" else 2,
            asset_ids=asset_ids
        )
