#!/usr/bin/env python3
"""
Script to submit a new ticket to the API
"""

import requests
import json
import sys
import os
import random
import mimetypes
from pathlib import Path

# API Configuration
API_URL = "http://localhost:3000/api/tickets"
TOKEN_FILE = "token.txt"


def generate_ticket_id():
    """
    Generate a random ticket ID in format TCK-2025-xxxxx

    Returns:
        str: Random ticket ID
    """
    random_number = random.randint(100, 99999)
    return f"TCK-2025-{random_number}"


def read_token_from_file(filename=TOKEN_FILE):
    """
    Read JWT token from file

    Args:
        filename (str): Path to token file

    Returns:
        str: JWT token

    Raises:
        FileNotFoundError: If token file doesn't exist
        ValueError: If token file is empty or invalid
    """
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)

    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            # Skip comment lines and empty lines
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    return line
            raise ValueError("No valid token found in file")
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Token file not found: {file_path}\n"
            f"Please run 'python scripts/fetch_token.py' first to generate the token file."
        )

def submit_ticket(ticket_data, auth_token):
    """
    Submit a ticket to the API

    Args:
        ticket_data (dict): Ticket information
        auth_token (str): JWT authentication token

    Returns:
        dict: API response
    """
    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(API_URL, headers=headers, json=ticket_data)
        response.raise_for_status()
        return {
            'success': True,
            'status_code': response.status_code,
            'data': response.json()
        }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': str(e),
            'status_code': getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
        }

def upload_attachment(file_path, ticket_id, auth_token, name=None, notes=None):
    """
    Upload a file attachment to a ticket

    Args:
        file_path (str): Path to the file to upload
        ticket_id (int): Ticket ID to attach the file to
        auth_token (str): JWT authentication token
        name (str, optional): Display name for the attachment
        notes (str, optional): Notes about the attachment

    Returns:
        dict: API response with success status
    """
    path_obj = Path(file_path)
    if not path_obj.is_file():
        return {
            'success': False,
            'error': f'File not found: {file_path}'
        }

    # Infer content type
    content_type = mimetypes.guess_type(path_obj.name)[0] or "application/octet-stream"

    # Prepare form data
    data = {
        "sourceObjectType": "TICKET",
        "sourceObjectId": str(ticket_id),
        "name": name or path_obj.name,
        "type": content_type,
    }
    if notes:
        data["notes"] = notes

    headers = {
        'Authorization': f'Bearer {auth_token}'
    }

    try:
        with path_obj.open("rb") as handle:
            files = {"file": (path_obj.name, handle, content_type)}
            response = requests.post(
                "http://localhost:3000/api/attachments/upload",
                data=data,
                files=files,
                headers=headers,
                timeout=60
            )
            response.raise_for_status()
            return {
                'success': True,
                'status_code': response.status_code,
                'data': response.json()
            }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': str(e),
            'status_code': getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
        }

def main():
    # Read token from file
    try:
        auth_token = read_token_from_file()
        print(f"✓ Token loaded from {TOKEN_FILE}")
    except (FileNotFoundError, ValueError) as e:
        print(f"✗ Error reading token: {e}")
        sys.exit(1)

    # Generate random ticket ID
    ticket_id = generate_ticket_id()

    # Sample ticket data
    ticket_data = {
        "ticketId": ticket_id,
        "type": "ISSUE",
        "subType": "Damage",
        "priority": "MEDIUM",
        "status": "OPEN",
        "location": "Central Operations District",
        "description": "I think there is some issue with this thing, please check.",
    }

    print("Submitting ticket to API...")
    print(f"API URL: {API_URL}")
    print(f"Ticket ID: {ticket_data['ticketId']}")
    print("-" * 50)

    result = submit_ticket(ticket_data, auth_token)

    if result['success']:
        print(f"✓ Ticket submitted successfully!")
        print(f"Status Code: {result['status_code']}")
        print(f"Response: {json.dumps(result['data'], indent=2)}")

        # Extract the ticket ID from response
        created_ticket_id = result['data'].get('data', {}).get('id')

        if created_ticket_id:
            # Upload an image attachment
            script_dir = os.path.dirname(os.path.abspath(__file__))
            image_path = os.path.join(script_dir, "images", "electric_lines3.jpg")

            print("\n" + "=" * 50)
            print("Uploading attachment...")
            print(f"File: {image_path}")
            print("-" * 50)

            upload_result = upload_attachment(
                file_path=image_path,
                ticket_id=created_ticket_id,
                auth_token=auth_token,
                name="electricity_pole_damage.jpg",
                notes="Damage to electricity pole"
            )

            if upload_result['success']:
                print(f"✓ Attachment uploaded successfully!")
                print(f"Status Code: {upload_result['status_code']}")
                attachment_data = upload_result['data'].get('data', {})
                print(f"Attachment ID: {attachment_data.get('id')}")
                print(f"File URL: {attachment_data.get('url')}")
            else:
                print(f"✗ Failed to upload attachment")
                print(f"Error: {upload_result['error']}")
                if upload_result.get('status_code'):
                    print(f"Status Code: {upload_result['status_code']}")
        else:
            print("\n⚠ Warning: Could not extract ticket ID from response, skipping attachment upload")
    else:
        print(f"✗ Failed to submit ticket")
        print(f"Error: {result['error']}")
        if result['status_code']:
            print(f"Status Code: {result['status_code']}")
        sys.exit(1)

if __name__ == "__main__":
    main()

