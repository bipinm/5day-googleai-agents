"""
Image processing utilities for bounding box visualization.
"""

import os
import requests
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
from .exceptions import ImageProcessingError


class ImageAnnotator:
    """Handles image annotation with bounding boxes and labels."""

    def __init__(self, font_size: int = 24):
        self.font_size = font_size
        self._font = None

    def _get_font(self) -> ImageFont.ImageFont:
        """Load font for text rendering."""
        if self._font is not None:
            return self._font

        try:
            self._font = ImageFont.truetype("Arial.ttf", self.font_size)
        except Exception:
            try:
                self._font = ImageFont.truetype(
                    "/System/Library/Fonts/Arial.ttf",
                    self.font_size
                )
            except Exception:
                self._font = ImageFont.load_default()

        return self._font

    def _extract_predictions(self, result: Dict[str, Any]) -> Optional[list]:
        """
        Extract predictions from result, handling nested structures.

        Supports:
        - Direct predictions at root level
        - Predictions nested under any root-level dict key
        - Explicit 'roboflow_fault_analysis_response' wrapper
        """
        preds = None

        if isinstance(result, dict):
            # 1) Check for explicit wrapper key
            if "roboflow_fault_analysis_response" in result:
                inner = result.get("roboflow_fault_analysis_response")
                if isinstance(inner, dict):
                    preds = inner.get("predictions") or inner.get("preds")

            # 2) Scan other root-level dict values for predictions
            if preds is None:
                for k, v in result.items():
                    if k in ("predictions", "preds") or not isinstance(v, dict):
                        continue
                    p = v.get("predictions") or v.get("preds")
                    if p:
                        preds = p
                        break

        # 3) Fallback to top-level predictions
        if preds is None:
            preds = result.get("predictions") or result.get("preds")

        return preds

    def _download_image(self, url: str) -> str:
        """
        Download image from HTTP URL to temporary location.

        Args:
            url: HTTP URL of the image

        Returns:
            Path to the downloaded image file
        """
        # Create tmp/inputs directory
        tmp_dir = os.path.join(os.getcwd(), "tmp", "inputs")
        os.makedirs(tmp_dir, exist_ok=True)

        # Extract filename from URL
        filename = os.path.basename(url.split('?')[0])  # Remove query params if any
        local_path = os.path.join(tmp_dir, filename)
        print(f"Downloading image from {url} to {local_path}")

        # Download the image
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            with open(local_path, 'wb') as f:
                f.write(response.content)

            print(f"Image download completed ...")
            return local_path
        except requests.exceptions.RequestException as e:
            raise ImageProcessingError(f"Failed to download image from {url}: {e}")

    def _calculate_text_position(
        self,
        draw: ImageDraw.ImageDraw,
        label: str,
        x1: int,
        y1: int,
        img_width: int,
        img_height: int,
        font: ImageFont.ImageFont
    ) -> Tuple[int, int]:
        """
        Calculate optimal text position ensuring it stays within image bounds.
        """
        try:
            bbox = draw.textbbox((0, 0), label, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except Exception:
            # Fallback for older Pillow versions
            text_width = len(label) * 10
            text_height = 20

        # Initial position (above the box)
        text_x = x1 + 2
        text_y = y1 - text_height - 2

        # Adjust if text goes beyond left edge
        if text_x < 0:
            text_x = 2

        # Adjust if text goes beyond right edge
        if text_x + text_width > img_width:
            text_x = img_width - text_width - 2

        # Adjust if text goes beyond top edge (move inside box)
        if text_y < 0:
            text_y = y1 + 2

        # Adjust if text goes beyond bottom edge
        if text_y + text_height > img_height:
            text_y = img_height - text_height - 2

        return text_x, text_y

    def annotate(
        self,
        image_path: str,
        roboflow_result: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> str:
        """
        Draw bounding boxes and labels on an image.

        Args:
            image_path: Path to input image (local path or HTTP URL)
            roboflow_result: Detection results containing predictions
            output_path: Optional output path (auto-generated if None)

        Returns:
            Path to the annotated image file
        """
        # Download image if it's an HTTP URL
        local_image_path = image_path
        print(f"Processing image {image_path}, adding annotations...")

        if image_path.startswith(('http://', 'https://')):
            local_image_path = self._download_image(image_path)

        # Load image
        try:
            image = Image.open(local_image_path)
        except Exception as e:
            raise ImageProcessingError(f"Could not load image from {local_image_path}: {e}")

        # Generate output path if not provided
        if output_path is None:
            base_name = os.path.splitext(os.path.basename(local_image_path))[0]
            extension = os.path.splitext(local_image_path)[1] or ".jpg"
            output_dir = os.path.join(os.getcwd(), "tmp", "output")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{base_name}_detected{extension}")

        # Extract predictions
        print("="*180)
        print(type(roboflow_result))
        print(roboflow_result)
        print("="*180)

        preds = self._extract_predictions(roboflow_result)

        if not preds:
            print("No predictions found, skipping drawing bounding boxes and saving file.")
            return ""

        # Setup drawing
        draw = ImageDraw.Draw(image)
        font = self._get_font()
        img_width, img_height = image.size

        # Draw each prediction
        for p in preds:
            x = int(p.get("x", 0))
            y = int(p.get("y", 0))
            w = int(p.get("width", 20))
            h = int(p.get("height", 20))

            # Calculate bounding box coordinates
            x1 = x - w // 2
            y1 = y - h // 2
            x2 = x + w // 2
            y2 = y + h // 2

            # Draw rectangle
            draw.rectangle([x1, y1, x2, y2], outline="red", width=3)

            # Draw label with semi-transparent black background
            label = p.get('class', 'obj')
            text_x, text_y = self._calculate_text_position(
                draw, label, x1, y1, img_width, img_height, font
            )

            # Calculate text bounding box for background
            try:
                bbox = draw.textbbox((text_x, text_y), label, font=font)
                text_bg_x1, text_bg_y1 = bbox[0] - 2, bbox[1] - 2
                text_bg_x2, text_bg_y2 = bbox[2] + 2, bbox[3] + 2
            except Exception:
                # Fallback for older Pillow versions
                text_width = len(label) * 10
                text_height = 20
                text_bg_x1 = text_x - 2
                text_bg_y1 = text_y - 2
                text_bg_x2 = text_x + text_width + 2
                text_bg_y2 = text_y + text_height + 2

            # Draw semi-transparent black background
            # Create a temporary image for alpha blending
            overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle(
                [text_bg_x1, text_bg_y1, text_bg_x2, text_bg_y2],
                fill=(0, 0, 0, 180)  # Semi-transparent black (70% opacity)
            )

            # Convert original image to RGBA if needed and composite the overlay
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            image = Image.alpha_composite(image, overlay)

            # Update draw object with the new image
            draw = ImageDraw.Draw(image)

            # Draw red text on top of the background
            draw.text((text_x, text_y), label, fill="red", font=font)

        # Save annotated image
        out_dir = os.path.dirname(output_path)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        # Convert back to RGB if saving as JPEG
        if output_path.lower().endswith(('.jpg', '.jpeg')):
            if image.mode == 'RGBA':
                # Create white background
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[3])  # Use alpha channel as mask
                image = rgb_image

        image.save(output_path)
        print(f"Saved annotated image to: {output_path}")

        return output_path

