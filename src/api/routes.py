"""
API Routes for the car damage assessment
"""
import logging
from typing import Union
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from src.services.groq_service import GroqService
from src.core.config import settings
from src.schemas.damage_assessment_enhanced import EnhancedDamageAssessmentResponse
from src.utils.image_utils import validate_image, resize_image_if_needed
from src.utils.fraud_detection import detect_potential_fraud

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["Damage Assessment"])

def get_vision_service():
    """Get the Groq vision service"""
    logger.debug("Creating Groq vision service")
    return GroqService()

@router.post(
    "/assess-damage",
    response_model=EnhancedDamageAssessmentResponse,
    summary="Assess car damage from image",
    description="Upload an image of a damaged car to get make/model, damage assessment, and repair cost estimation",
)
async def assess_damage(
    image: UploadFile = File(...),
    skip_fraud_check: bool = Query(False, description="Skip fraud detection (not recommended for production)"),
    vision_service: GroqService = Depends(get_vision_service),
):
    """
    Process uploaded car image and return damage assessment with cost estimate
    """
    try:
        logger.info(f"Processing uploaded image: {image.filename}")
        
        # Validate file is an image
        content_type = image.content_type
        if not content_type or "image" not in content_type:
            logger.warning(f"Invalid content type: {content_type}")
            raise HTTPException(
                status_code=400,
                detail="Uploaded file must be an image (jpeg, png, etc.)",
            )
        
        # Read image content
        image_content = await image.read()
        logger.debug(f"Image size: {len(image_content)} bytes")
        
        # Validate image
        logger.info("Validating image")
        is_valid, error_msg = validate_image(image_content)
        if not is_valid:
            logger.warning(f"Image validation failed: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=error_msg or "Invalid image file",
            )
        
        # Fraud detection
        if not skip_fraud_check:
            logger.info("Running fraud detection")
            is_fraud, fraud_reason = detect_potential_fraud(image_content)
            if is_fraud:
                logger.warning(f"Potential fraud detected: {fraud_reason}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Potential fraud detected: {fraud_reason}. If this is a mistake, try again with a different image or contact support.",
                )
        else:
            logger.info("Fraud detection skipped")
        
        # Resize image if needed for API limitations
        logger.info("Resizing image if needed")
        image_content = resize_image_if_needed(image_content)
        
        # Process with Groq service
        logger.info("Sending image to Groq service for damage assessment")
        assessment_result = await vision_service.analyze_car_damage(image_content)
        logger.info("Damage assessment completed successfully")
        
        return assessment_result
    
    except HTTPException as http_e:
        # Re-raise HTTP exceptions
        logger.warning(f"HTTP Exception: {http_e.detail}")
        raise http_e
    
    except Exception as e:
        logger.error(f"Error assessing damage: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process image: {str(e)}",
        ) 