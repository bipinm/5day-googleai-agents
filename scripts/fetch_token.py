#!/usr/bin/env python3
"""
Script to fetch JWT token from the API and save it to token.txt
"""

import requests
import json
import sys
import os
from datetime import datetime

# API Configuration
API_BASE_URL = "http://localhost:3000/api"
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login"
TOKEN_FILE = "token.txt"

# Default credentials (can be overridden by environment variables)
USERNAME = os.getenv('API_USERNAME', 'ai')
PASSWORD = os.getenv('API_PASSWORD', 'aihash')


def fetch_token(username, password):
    """
    Fetch JWT token from the API

    Args:
        username (str): API username
        password (str): API password

    Returns:
        dict: Result containing success status and token or error
    """
    credentials = {
        "username": username,
        "password": password
    }

    try:
        print(f"Requesting token from {LOGIN_ENDPOINT}...")
        response = requests.post(LOGIN_ENDPOINT, json=credentials)
        response.raise_for_status()

        data = response.json()
        token = data.get('token')

        if not token:
            return {
                'success': False,
                'error': 'No token in response'
            }

        return {
            'success': True,
            'token': token,
            'status_code': response.status_code,
            'data': data
        }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': str(e),
            'status_code': getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
        }


def save_token_to_file(token, filename=TOKEN_FILE):
    """
    Save token to file with metadata

    Args:
        token (str): JWT token
        filename (str): File path to save token
    """
    try:
        # Get the directory of this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, filename)

        with open(file_path, 'w') as f:
            f.write(f"# JWT Token fetched at {datetime.now().isoformat()}\n")
            f.write(f"# Use this token in Authorization header: Bearer <token>\n")
            f.write(f"{token}\n")

        return file_path
    except Exception as e:
        raise Exception(f"Failed to save token to file: {e}")


def main():
    print("=" * 60)
    print("JWT Token Fetcher")
    print("=" * 60)
    print(f"Username: {USERNAME}")
    print(f"Endpoint: {LOGIN_ENDPOINT}")
    print("-" * 60)

    # Fetch token
    result = fetch_token(USERNAME, PASSWORD)

    if result['success']:
        token = result['token']
        print(f"✓ Token fetched successfully!")
        print(f"Status Code: {result['status_code']}")

        # Save to file
        try:
            file_path = save_token_to_file(token)
            print(f"✓ Token saved to: {file_path}")
            print("-" * 60)
            print(f"Token preview: {token[:50]}...")
            print("-" * 60)
            print("\nTo use this token:")
            print(f"  1. Read from file: cat {file_path}")
            print(f"  2. Use in header: Authorization: Bearer <token>")
        except Exception as e:
            print(f"✗ Failed to save token: {e}")
            print(f"Token: {token}")
            sys.exit(1)
    else:
        print(f"✗ Failed to fetch token")
        print(f"Error: {result['error']}")
        if result.get('status_code'):
            print(f"Status Code: {result['status_code']}")
        sys.exit(1)


if __name__ == "__main__":
    main()

