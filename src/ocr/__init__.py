# This file makes 'ocr' a Python package

from .preprocess import preprocess_image_for_ocr, encode_image_for_form_recognizer
from .azure_recognizer import AzureRecognizerClient, close_client as close_azure_client, Language

__all__ = [
    "preprocess_image_for_ocr",
    "encode_image_for_form_recognizer",
    "AzureRecognizerClient",
    "close_azure_client",
    "Language" # Re-export Language if it's defined within azure_recognizer or schemas
] 