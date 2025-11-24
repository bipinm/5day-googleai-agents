"""
Shared authentication manager for API communication.
Provides cached JWT token management across multiple managers.
"""

import os
import requests
from typing import Optional
from dotenv import load_dotenv


class AuthManager:
    """Singleton authentication manager with cached token."""

    _instance = None
    _token: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AuthManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Load environment variables
        load_dotenv()

        self.base_url = os.getenv('BASE_URL', 'http://localhost:3000/api')
        self.username = os.getenv('USERNAME', 'ai')
        self.password = os.getenv('PASSWORD', 'aihash')
        self.login_url = f"{self.base_url}/auth/login"
        self.credentials = {
            "username": self.username,
            "password": self.password
        }
        self._initialized = True

    def get_jwt_token(self, force_refresh: bool = False) -> Optional[str]:
        """
        Get JWT token (cached or fresh).

        Args:
            force_refresh: If True, forces a new token fetch even if one is cached

        Returns:
            JWT token or None if authentication fails
        """
        if self._token and not force_refresh:
            return self._token

        try:
            response = requests.post(self.login_url, json=self.credentials)
            response.raise_for_status()
            self._token = response.json().get('token')
            return self._token
        except requests.exceptions.RequestException as e:
            print(f"Login failed: {e}")
            return None

    def clear_token(self):
        """Clear the cached token."""
        self._token = None

    def get_auth_headers(self) -> dict:
        """
        Get authorization headers with current token.

        Returns:
            Dictionary with Authorization header
        """
        token = self.get_jwt_token()
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}

