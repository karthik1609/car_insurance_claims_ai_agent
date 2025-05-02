"""
Service for assessing damage from images
"""
import logging
from io import BytesIO

from src.services.groq_service import GroqService
from src.utils.image_utils import validate_image, resize_image_if_needed
from src.utils.fraud_detection import detect_potential_fraud

# Configure logging
logger = logging.getLogger(__name__)

def assess_damage_from_image(image_file):
    """
    Process an image file and return damage assessment with cost estimate
    
    Args:
        image_file: A file-like object containing the image data
    
    Returns:
        List[Dict]: A list of damage assessment dictionaries
    
    Raises:
        ValueError: If the image is invalid or processing fails
    """
    try:
        # Read image content
        image_file.seek(0)
        image_content = image_file.read()
        logger.debug(f"Image size: {len(image_content)} bytes")
        
        # Validate image
        logger.info("Validating image")
        is_valid, error_msg = validate_image(image_content)
        if not is_valid:
            logger.warning(f"Image validation failed: {error_msg}")
            raise ValueError(error_msg or "Invalid image file")
        
        # Run basic fraud detection
        logger.info("Running basic fraud detection")
        is_fraud, fraud_reason = detect_potential_fraud(image_content)
        if is_fraud:
            logger.warning(f"Potential fraud detected: {fraud_reason}")
            # For WhatsApp, we'll still process but log the warning
            logger.info("Processing despite potential fraud (WhatsApp request)")
        
        # Resize image if needed for API limitations
        logger.info("Resizing image if needed")
        image_content = resize_image_if_needed(image_content)
        
        # Process with Groq service
        logger.info("Sending image to Groq service for damage assessment")
        vision_service = GroqService()
        assessment_result = vision_service.analyze_car_damage_sync(image_content)
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