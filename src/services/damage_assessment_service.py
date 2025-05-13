"""
Service for assessing damage from images
"""
import os
import logging
from typing import List, Tuple, Dict, Any, Union, BinaryIO

from src.services.groq_service import GroqService
from src.utils.fraud_detection import detect_potential_fraud
from src.utils.image_utils import validate_image, resize_image_if_needed
from src.logger import get_logger

# Configure logging
logger = get_logger(__name__)
groq_service = GroqService()

def assess_damage_from_image(image_file):
    """
    Assess car damage from an uploaded image file.
    
    This function:
    1. Validates the image
    2. Checks for potential fraud
    3. Processes the image with Groq API
    4. Returns the damage assessment results
    
    Args:
        image_file: The uploaded image file object
        
    Returns:
        List[Dict[str, Any]]: A list of assessment results, one per vehicle detected
    """
    try:
        # Read the image data
        image_content = image_file.read()
        if hasattr(image_file, 'seek'):
            image_file.seek(0)  # Reset file pointer for potential reuse
        
        logger.info(f"Image size: {len(image_content)} bytes")
        
        # Validate image
        is_valid, error_msg = validate_image(image_content)
        if not is_valid:
            logger.warning(f"Invalid image: {error_msg}")
            raise ValueError(error_msg or "Invalid image")
        
        # Check for potential fraud
        is_fraud, fraud_reason = detect_potential_fraud(image_content)
        if is_fraud:
            logger.warning(f"Potential fraud detected: {fraud_reason}")
            raise ValueError(f"Potential fraud detected: {fraud_reason}")
        
        # Resize image if needed for API limitations
        logger.info("Resizing image if needed")
        image_content = resize_image_if_needed(image_content)
        
        # Process with Groq service (synchronous version)
        logger.info("Processing with Groq service")
        assessment_result = groq_service.analyze_car_damage_sync(image_content)
        
        logger.info("Damage assessment completed successfully")
        
        # Ensure the result is a list as expected
        if isinstance(assessment_result, dict) and "vehicle_info" in assessment_result and "damage_data" in assessment_result:
            logger.debug("Single assessment received, wrapping in list")
            result_list = [assessment_result]
        elif isinstance(assessment_result, list):
            logger.debug(f"List of {len(assessment_result)} assessments received")
            result_list = assessment_result
        else:
            logger.warning(f"Unexpected result format: {type(assessment_result)}")
            raise ValueError("Unexpected response format from assessment service")
        
        return result_list
    
    except ValueError as ve:
        # Re-raise validation errors
        logger.warning(f"Validation error: {str(ve)}")
        raise
    
    except Exception as e:
        logger.error(f"Error assessing damage: {str(e)}", exc_info=True)
        raise ValueError(f"Failed to process image: {str(e)}") 