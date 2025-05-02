"""
API Routes for the car damage assessment
"""
import logging
from typing import Union, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from src.services.groq_service import GroqService
from src.core.config import settings
from src.schemas.damage_assessment_enhanced import EnhancedDamageAssessmentResponse, DamageAssessmentItem
from src.utils.image_utils import validate_image, resize_image_if_needed
from src.utils.fraud_detection import detect_potential_fraud
from src.routes.whatsapp_webhook import router as whatsapp_router
from src.routes.telegram_bot import router as telegram_router

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["Damage Assessment"])

# Include the WhatsApp webhook router
router.include_router(whatsapp_router, prefix="/whatsapp", tags=["WhatsApp"])

# Include the Telegram webhook router
router.include_router(telegram_router, prefix="/telegram", tags=["Telegram"])

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
    skip_fraud_check: bool = Query(False, description="Skip fraud detection entirely (not recommended for production)"),
    process_anyway: bool = Query(False, description="Process the request even if potential fraud is detected"),
    vision_service: GroqService = Depends(get_vision_service),
):
    """
    Process uploaded car image and return damage assessment with cost estimate
    """
    # Track if we have a fraud warning to include in the response
    fraud_warning = None
    
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
                fraud_warning = f"Potential fraud detected: {fraud_reason}"
                
                # If not processing anyway, return a 202 Accepted with warning but no assessment
                if not process_anyway:
                    logger.info("Returning fraud warning without assessment")
                    return JSONResponse(
                        status_code=202,
                        content={
                            "warning": fraud_warning,
                            "message": "The image may be modified or manipulated. If this is a mistake, retry with process_anyway=true or contact support.",
                            "assessment": None
                        }
                    )
                
                # If processing anyway, continue but log the decision
                logger.info("Processing despite fraud detection (process_anyway=true)")
        else:
            logger.info("Fraud detection skipped")
        
        # Resize image if needed for API limitations
        logger.info("Resizing image if needed")
        image_content = resize_image_if_needed(image_content)
        
        # Process with Groq service
        logger.info("Sending image to Groq service for damage assessment")
        assessment_result = await vision_service.analyze_car_damage(image_content)
        logger.info("Damage assessment completed successfully")
        
        # Ensure the result is a list as expected by the response model
        if isinstance(assessment_result, dict) and "vehicle_info" in assessment_result and "damage_data" in assessment_result:
            logger.debug("Single assessment received, wrapping in list")
            result_list = [assessment_result]
        elif isinstance(assessment_result, list):
            logger.debug(f"List of {len(assessment_result)} assessments received")
            result_list = assessment_result
        else:
            logger.warning(f"Unexpected result format: {type(assessment_result)}")
            raise HTTPException(
                status_code=500,
                detail="Unexpected response format from assessment service",
            )
        
        # If we have a fraud warning but still processing, include it in the response
        if fraud_warning:
            return JSONResponse(
                status_code=202,
                content={
                    "warning": fraud_warning,
                    "message": "Assessment completed but fraud detection triggered. Results may be unreliable.",
                    "assessment": result_list
                }
            )
        
        # No fraud warning, return normal result
        return result_list
    
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