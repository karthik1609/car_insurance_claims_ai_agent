"""
Service for generating accident reports from images using Azure AI Document Intelligence
"""
import base64
import json
import logging
from typing import Dict, Any, Optional, Union

from src.core.config import settings
from src.schemas.accident_report_de import AccidentReport
from src.schemas.accident_report_en import AccidentReportEN
from src.schemas.accident_report_nl import AccidentReportNL
from src.schemas.language import Language
from src.logger import get_logger
from src.ocr.preprocess import preprocess_image_for_ocr, encode_image_for_form_recognizer
from src.ocr.azure_recognizer import AzureRecognizerClient

# Configure logging
logger = get_logger(__name__)

class AccidentReportService:
    """Service for generating accident reports from images using Azure AI Document Intelligence."""
    
    def __init__(self):
        """Initialize the service with AzureRecognizerClient."""
        self.azure_recognizer_client = AzureRecognizerClient()
        logger.debug("AccidentReportService initialized with AzureRecognizerClient")
    
    async def generate_accident_report(
        self, 
        image_bytes: bytes, 
        language: Language,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Union[AccidentReport, AccidentReportEN, AccidentReportNL, None]:
        """
        Generate an accident report from an image using Azure AI Document Intelligence.
        
        Args:
            image_bytes: Raw bytes of the image.
            language: Language for the report (de, en, nl).
            metadata: Optional metadata (e.g., current DPI, if known from source).
            
        Returns:
            Union[AccidentReport, AccidentReportEN, AccidentReportNL, None]: Accident report or None on failure.
        """
        try:
            current_dpi = metadata.get("current_dpi", 72) if metadata else 72
            # 1. Preprocess image using OpenCV utilities
            logger.info(f"Starting image preprocessing for Azure OCR (Language: {language})")
            preprocessed_cv_image = preprocess_image_for_ocr(image_bytes, current_dpi=current_dpi)
            # 2. Encode preprocessed image for Azure client
            # Form Recognizer generally prefers PNG or JPEG for custom models.
            encoded_image_bytes = encode_image_for_form_recognizer(preprocessed_cv_image, extension=".png")
            logger.info("Image preprocessed and encoded for Azure AI Document Intelligence.")

            # 3. Extract data using AzureRecognizerClient
            # This client handles calls to prebuilt-layout and the custom model,
            # and then maps the results to our Pydantic schemas.
            report = await self.azure_recognizer_client.extract_accident_report_data(
                preprocessed_image_bytes=encoded_image_bytes,
                language=language,
                original_image_bytes=image_bytes # Pass original for potential fallback/debug
            )

            if report:
                logger.info(f"Successfully generated accident report using Azure for language {language}.")
            else:
                logger.warning(f"Failed to generate accident report using Azure for language {language}.")
            
            return report

        except ValueError as ve:
            logger.error(f"ValueError during accident report generation: {str(ve)}", exc_info=True)
            # Potentially re-raise or return a specific error response
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating accident report with Azure: {str(e)}", exc_info=True)
            # Potentially re-raise or return a specific error response
            raise