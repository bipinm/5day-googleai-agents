"""
Configuration management for image analysis system.
"""

import os
import json
from typing import Dict, Any, List
from .exceptions import ConfigError


class ConfigManager:
    """Manages configuration loading and access."""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agent_config.json")
        self.config_path = config_path
        self._config = None
        self._top_level_categories = None

    def load(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        if not os.path.exists(self.config_path):
            raise ConfigError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            self._config = json.load(f)
        return self._config

    @property
    def config(self) -> Dict[str, Any]:
        """Get configuration, loading if necessary."""
        if self._config is None:
            self.load()
        return self._config

    def get_top_level_categories(self) -> List[str]:
        """Extract top-level categories from configuration."""
        if self._top_level_categories is not None:
            return self._top_level_categories

        mapping = self.config.get("image_classifier_models")
        keys: List[str] = []

        if isinstance(mapping, dict):
            keys = list(mapping.keys())
        elif isinstance(mapping, list):
            for entry in mapping:
                if isinstance(entry, dict):
                    for k in entry.keys():
                        if k not in keys:
                            keys.append(k)

        if not keys:
            raise ConfigError("No top level categories found in configuration")

        self._top_level_categories = keys
        return keys

    def get_model_id_for_category(self, category: str) -> str:
        """Get the Roboflow model ID for a given category."""
        mapping = self.config.get("image_classifier_models")
        if not mapping:
            raise ConfigError("Config missing 'image_classifier_models' key")

        model_id = None
        if isinstance(mapping, list):
            for entry in mapping:
                if not isinstance(entry, dict):
                    continue
                if category in entry:
                    inner = entry[category]
                    model_id = list(inner[0].values())[0] if isinstance(inner, list) and inner else None
                    break

        if not model_id:
            raise ConfigError(f"Model ID for category '{category}' not found in config")

        return model_id

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize a category name for comparison."""
        return ''.join(ch.lower() for ch in name if ch.isalnum())

