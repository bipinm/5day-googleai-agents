#!/usr/bin/env python3
"""
Script to submit a new ticket to the API
"""

import requests
import json
import sys
import os
import random

# API Configuration
API_URL = "http://localhost:3000/api/tickets"
TOKEN_FILE = "token.txt"


def generate_ticket_id():
    """
    Generate a random ticket ID in format TCK-2025-xxxxx

    Returns:
        str: Random ticket ID
    """
    random_number = random.randint(10000, 99999)
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
        "type": "INCIDENT",
        "subType": "Weather",
        "priority": "CRITICAL",
        "status": "OPEN",
        "location": "Central Operations District",
        "description": "Current Weather Event:\n- Temperature: 10°C\n- Wind Speed: 100 km/h\n- Precipitation: 8 mm\n- Humidity: 65%\n- Duration: 6 hours\n- Type: Strong Wind Storm\n- Severity: Critical"
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
    else:
        print(f"✗ Failed to submit ticket")
        print(f"Error: {result['error']}")
        if result['status_code']:
            print(f"Status Code: {result['status_code']}")
        sys.exit(1)

if __name__ == "__main__":
    main()

