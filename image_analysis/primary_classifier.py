"""
Primary classification logic for image analysis.
"""

import os
import base64
from typing import Dict, Any
from google.cloud import aiplatform
from google.cloud.aiplatform.gapic.schema import predict
from .config import ConfigManager


class PrimaryClassifier:
    """Primary image classifier using heuristic or Vertex AI."""

    def __init__(self, config_manager: ConfigManager, use_mock: bool = False):
        self.config_manager = config_manager
        self.use_mock = use_mock
        print(f"\nPrimary Classification using {'filename heuristics (MOCK MODE)' if use_mock else 'Vertex AI Vision API'}.\n")
        self.categories = config_manager.get_top_level_categories()
        self._normalized_categories = {
            config_manager.normalize_name(k): k for k in self.categories
        }

        # Vertex AI configuration (loaded from environment variables)
        self.vertex_project = os.getenv('VERTEX_AI_PROJECT')
        self.vertex_endpoint_id = os.getenv('VERTEX_AI_ENDPOINT_ID')
        self.vertex_location = os.getenv('VERTEX_AI_LOCATION')

        if not use_mock:
            if not all([self.vertex_project, self.vertex_endpoint_id, self.vertex_location]):
                raise ValueError(
                    "Vertex AI configuration missing. Please set environment variables: "
                    "VERTEX_AI_PROJECT, VERTEX_AI_ENDPOINT_ID, VERTEX_AI_LOCATION"
                )

        self.vertex_api_endpoint = f"{self.vertex_location}-aiplatform.googleapis.com" if self.vertex_location else None

        # Initialize Vertex AI client (reused for multiple requests)
        if not use_mock:
            client_options = {"api_endpoint": self.vertex_api_endpoint}
            self.prediction_client = aiplatform.gapic.PredictionServiceClient(
                client_options=client_options
            )
        else:
            self.prediction_client = None

    def classify(self, image_path: str) -> Dict[str, Any]:
        """
        Classify an image into a top-level category.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with 'prediction' key containing the category
        """
        if self.use_mock:
            return self._mock_classify(image_path)
        else:
            return self._vertex_ai_classify(image_path)

    def _mock_classify(self, image_path: str) -> Dict[str, Any]:
        """
        Mock classification using filename heuristics for testing.
        """
        print(f"Using mock primary classification based on filename heuristics.")
        name = os.path.basename(image_path).lower()
        category = None

        if any(k in name for k in ("electric", "electricity", "circuit", "cable")):
            if "circuit" in name or "pcb" in name:
                category = "PCB"
            else:
                category = "ElectricityDistribution"
        elif any(k in name for k in ("track", "railway")):
            category = "RailwayTrack"
        elif any(k in name for k in ("wagon", "wagon_")):
            category = "TrainWagon"
        elif any(k in name for k in ("wheel", "wheel_")):
            category = "TrainWheel"

        return {"prediction": category}

    def _vertex_ai_classify(self, image_path: str) -> Dict[str, Any]:
        """
        Classify using Vertex AI Vision API.

        Args:
            image_path: Path to the image file (local path or HTTP URL)

        Returns:
            Dictionary with 'prediction' key containing the category
        """
        print(f"Using Vertex AI Vision API for primary classification.")
        print(f"Image: {image_path}")

        try:
            # Download image if it's an HTTP URL
            local_image_path = image_path
            if image_path.startswith(('http://', 'https://')):
                local_image_path = self._download_image(image_path)

            # Read and encode the image
            with open(local_image_path, "rb") as f:
                file_content = f.read()

            encoded_content = base64.b64encode(file_content).decode("utf-8")

            # Create prediction instance
            instance = predict.instance.ImageClassificationPredictionInstance(
                content=encoded_content,
            ).to_value()
            instances = [instance]

            # Set prediction parameters
            parameters = predict.params.ImageClassificationPredictionParams(
                confidence_threshold=0.5,
                max_predictions=5,
            ).to_value()

            # Build endpoint path
            endpoint = self.prediction_client.endpoint_path(
                project=self.vertex_project,
                location=self.vertex_location,
                endpoint=self.vertex_endpoint_id
            )

            print(f"Calling Vertex AI endpoint: {endpoint}")

            # Make prediction request
            response = self.prediction_client.predict(
                endpoint=endpoint,
                instances=instances,
                parameters=parameters
            )

            print(f"Vertex AI Response - Deployed Model ID: {response.deployed_model_id}")

            # Process predictions
            predictions = response.predictions
            if not predictions:
                print("No predictions returned from Vertex AI")
                return {"prediction": None}

            # Get the top prediction
            top_prediction = dict(predictions[0])
            print(f"Top prediction: {top_prediction}")

            # Extract the display name (category) from prediction
            display_names = top_prediction.get('displayNames', [])
            confidences = top_prediction.get('confidences', [])

            if display_names and confidences:
                # Get the category with highest confidence
                top_category = display_names[0]
                top_confidence = confidences[0]

                print(f"Classified as: {top_category} (confidence: {top_confidence:.2%})")

                # Map the prediction to our categories
                category = self._map_prediction_to_category(top_category)

                return {
                    "prediction": category
                }
            else:
                print("No display names or confidences in prediction")
                return {"prediction": None}

        except Exception as e:
            print(f"Error during Vertex AI classification: {e}")
            print(f"Falling back to mock classification")
            # Fall back to mock classification on error
            return self._mock_classify(image_path)

    def _download_image(self, url: str) -> str:
        """
        Download image from HTTP URL to temporary location.

        Args:
            url: HTTP URL of the image

        Returns:
            Path to the downloaded image file
        """
        import requests

        # Create tmp/inputs directory
        tmp_dir = os.path.join(os.getcwd(), "tmp", "inputs")
        os.makedirs(tmp_dir, exist_ok=True)

        # Extract filename from URL
        filename = os.path.basename(url.split('?')[0])
        local_path = os.path.join(tmp_dir, filename)

        # Download if not already exists
        if not os.path.exists(local_path):
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                with open(local_path, 'wb') as f:
                    f.write(response.content)

                print(f"Downloaded image from {url} to {local_path}")
            except Exception as e:
                print(f"Failed to download image from {url}: {e}")
                raise

        return local_path

    def _map_prediction_to_category(self, prediction: str) -> str:
        """
        Map Vertex AI prediction to our category structure.

        Args:
            prediction: The raw prediction label from Vertex AI

        Returns:
            Mapped category name or the original prediction
        """
        # Normalize the prediction
        normalized_pred = self.config_manager.normalize_name(prediction)

        # Check if it matches any of our categories
        if normalized_pred in self._normalized_categories:
            return self._normalized_categories[normalized_pred]

        # Try partial matching
        for norm_cat, actual_cat in self._normalized_categories.items():
            if norm_cat in normalized_pred or normalized_pred in norm_cat:
                print(f"Mapped '{prediction}' to '{actual_cat}' via partial match")
                return actual_cat

        # Return the original prediction if no match found
        print(f"No category mapping found for '{prediction}', using as-is")
        return prediction

