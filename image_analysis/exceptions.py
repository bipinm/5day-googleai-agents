"""
Custom exceptions for image analysis system.
"""


class ImageAnalysisError(Exception):
    """Base exception for image analysis errors."""
    pass


class ConfigError(ImageAnalysisError):
    """Exception raised for configuration-related errors."""
    pass


class ClassificationError(ImageAnalysisError):
    """Exception raised for classification errors."""
    pass


class DetectionError(ImageAnalysisError):
    """Exception raised for detection errors."""
    pass


class ImageProcessingError(ImageAnalysisError):
    """Exception raised for image processing errors."""
    pass

