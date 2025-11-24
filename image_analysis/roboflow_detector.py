"""
Secondary detection logic using Roboflow API.
"""

import os
import time
from typing import Dict, Any
from .config import ConfigManager
from .exceptions import DetectionError


class RoboflowDetector:
    """Handles detailed fault detection using Roboflow inference."""

    def __init__(self, config_manager: ConfigManager, use_mock: bool = False):
        self.config_manager = config_manager
        print(f"\nRoboflow Detection using {'Mock' if use_mock else 'Roboflow API'}.\n")
        self.use_mock = use_mock
        self._client = None

    def _get_client(self):
        """Lazy initialization of Roboflow client."""
        if self._client is not None:
            return self._client

        try:
            from inference_sdk import InferenceHTTPClient
        except ImportError as e:
            raise ImportError(
                "inference_sdk is required for real API calls. "
                "Install it with `pip install inference-sdk`."
            ) from e

        api_key = os.environ.get("ROBOFLOW_API_KEY")
        if not api_key:
            raise DetectionError("ROBOFLOW_API_KEY not set in environment")

        self._client = InferenceHTTPClient(
            api_url="https://serverless.roboflow.com",
            api_key=api_key
        )
        return self._client

    def detect(self, image_path: str, primary_classification: str) -> Dict[str, Any]:
        """
        Perform detailed fault detection on an image.

        Args:
            image_path: Path to the image file
            primary_classification: Category from primary classifier

        Returns:
            Detection results with predictions
        """
        print(f"\n{'='*180}")
        print(f"Roboflow problem detection for image: {image_path} & category: {primary_classification}")
        print(f"{'='*180}\n")

        if self.use_mock:
            return self._mock_detect()

        model_id = self.config_manager.get_model_id_for_category(primary_classification)
        client = self._get_client()

        try:
            result = client.infer(image_path, model_id=model_id)
        except TypeError:
            # Fallback for different SDK versions
            result = client.infer(image_path, model_id)

        return result

    def _mock_detect(self) -> Dict[str, Any]:
        """Mock detection for testing without API calls."""
        time.sleep(0.5)  # Simulate network delay
        print("Using mock Roboflow detection results.")

        return {
            'image': {'height': 601, 'width': 601},
            'inference_id': 'ba167830-d9ca-47f7-9904-7ea13f5a67db',
            'predictions': [
                {
                    'class': 'spur',
                    'class_id': 4,
                    'confidence': 0.7668308615684509,
                    'detection_id': '812008b1-5e7f-4fb4-8f9f-366c560550a9',
                    'height': 24.0,
                    'width': 32.0,
                    'x': 574.0,
                    'y': 195.0
                },
                {
                    'class': 'open_circuit',
                    'class_id': 2,
                    'confidence': 0.7621399760246277,
                    'detection_id': '982ad388-e873-4212-8cab-97a44f348aa0',
                    'height': 15.0,
                    'width': 19.0,
                    'x': 510.5,
                    'y': 528.5
                }
            ],
            'time': 0.01937782899767626
        }


class DetectionProcessor:
    """Processes and summarizes detection results."""

    @staticmethod
    def process(result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw detection results into structured format.
        """
        preds = result.get("predictions") or result.get("detections")
        if preds is None:
            raise DetectionError("Unexpected API response format: missing 'predictions' key")

        class_counts: Dict[str, int] = {}
        top_confidence = 0.0

        for p in preds:
            cls = p.get("class") or p.get("label") or "<unknown>"
            class_counts[cls] = class_counts.get(cls, 0) + 1
            conf = float(p.get("confidence") or p.get("score") or 0.0)
            if conf > top_confidence:
                top_confidence = conf

        return {
            "num_detections": len(preds),
            "class_counts": class_counts,
            "top_confidence": top_confidence,
            "detections": preds
        }

    @staticmethod
    def summarize(roboflow_result: Dict[str, Any]) -> str:
        """
        Generate a textual summary of detection results.
        """
        processed = DetectionProcessor.process(roboflow_result)
        lines = [f"Detections: {processed.get('num_detections')}"]

        for det in processed.get("detections", []):
            cls = det.get("class") or det.get("label") or "<unknown>"
            conf = float(det.get("confidence") or det.get("score") or 0.0)
            lines.append(f" - {cls}: confidence={conf:.2f}")

        return "\n".join(lines)

