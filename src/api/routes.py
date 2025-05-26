"""
API Routes for the car damage assessment
"""
import logging
import base64
from typing import Union, List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse
from enum import Enum

from src.services.groq_service import GroqService
from src.services.accident_report_service import AccidentReportService
from src.core.config import settings
from src.schemas.damage_assessment_enhanced import EnhancedDamageAssessmentResponse, DamageAssessmentItem
from src.schemas.base64_request import Base64ImageRequest
from src.schemas.accident_report_de import AccidentReport
from src.schemas.accident_report_en import AccidentReportEN
from src.schemas.accident_report_nl import AccidentReportNL
from src.schemas.language import Language
from src.utils.image_utils import validate_image, resize_image_if_needed
from src.utils.fraud_detection import detect_potential_fraud, extract_image_metadata

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["Damage Assessment"])

def get_vision_service():
    """Get the Groq vision service"""
    logger.debug("Creating Groq vision service")
    return GroqService()

def get_accident_report_service():
    """Get the accident report service"""
    logger.debug("Creating accident report service")
    return AccidentReportService()

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
        
        # Extract metadata from image - do this before fraud check to use the same metadata
        logger.info("Extracting image metadata")
        metadata = extract_image_metadata(image_content)
        
        # Fraud detection
        if not skip_fraud_check:
            logger.info("Running fraud detection")
            is_fraud, fraud_reason = detect_potential_fraud(image_content)
            if is_fraud:
                logger.warning(f"Potential fraud detected: {fraud_reason}")
                fraud_warning = f"Potential fraud detected: {fraud_reason}"
                
                # Add the fraud reason to metadata to ensure LLM sees it even if we process anyway
                if "fraud_indicators" not in metadata:
                    metadata["fraud_indicators"] = []
                if fraud_reason not in metadata["fraud_indicators"]:
                    metadata["fraud_indicators"].append(fraud_reason)
                
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
        
        # Process with Groq service, passing the metadata including fraud indicators
        logger.info("Sending image to Groq service for damage assessment")
        assessment_result = await vision_service.analyze_car_damage(image_content, metadata)
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

@router.post(
    "/assess-damage-base64",
    response_model=EnhancedDamageAssessmentResponse,
    summary="Assess car damage from base64-encoded image",
    description="Submit a base64-encoded image of a damaged car to get make/model, damage assessment, and repair cost estimation. Ideal for integrations where file upload is not feasible.",
)
async def assess_damage_base64(
    request: Base64ImageRequest,
    skip_fraud_check: bool = Query(False, description="Skip fraud detection entirely (not recommended for production)"),
    process_anyway: bool = Query(False, description="Process the request even if potential fraud is detected"),
    vision_service: GroqService = Depends(get_vision_service),
):
    """
    Process base64-encoded car image and return damage assessment with cost estimate
    """
    # Track if we have a fraud warning to include in the response
    fraud_warning = None
    
    try:
        logger.info("Processing base64-encoded image")
        
        # Convert base64 to image bytes
        try:
            image_content = base64.b64decode(request.image)
            logger.debug(f"Decoded image size: {len(image_content)} bytes")
        except Exception as e:
            logger.warning(f"Invalid base64 image: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail="Invalid base64 encoding. Please provide a properly encoded image.",
            )
        
        # Validate image
        logger.info("Validating image")
        is_valid, error_msg = validate_image(image_content)
        if not is_valid:
            logger.warning(f"Image validation failed: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=error_msg or "Invalid image data",
            )
        
        # Extract metadata from image - do this before fraud check to use the same metadata
        logger.info("Extracting image metadata")
        metadata = extract_image_metadata(image_content)
        
        # Fraud detection
        if not skip_fraud_check:
            logger.info("Running fraud detection")
            is_fraud, fraud_reason = detect_potential_fraud(image_content)
            if is_fraud:
                logger.warning(f"Potential fraud detected: {fraud_reason}")
                fraud_warning = f"Potential fraud detected: {fraud_reason}"
                
                # Add the fraud reason to metadata to ensure LLM sees it even if we process anyway
                if "fraud_indicators" not in metadata:
                    metadata["fraud_indicators"] = []
                if fraud_reason not in metadata["fraud_indicators"]:
                    metadata["fraud_indicators"].append(fraud_reason)
                
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
        
        # Process with Groq service, passing the metadata including fraud indicators
        logger.info("Sending image to Groq service for damage assessment")
        assessment_result = await vision_service.analyze_car_damage(image_content, metadata)
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
        logger.error(f"Error assessing damage from base64 image: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to process image: {str(e)}",
        )

@router.post(
    "/generate-accident-report",
    response_model=Union[AccidentReport, AccidentReportEN, AccidentReportNL],
    summary="Generate accident report from image",
    description="Upload an image of a completed European Accident Statement form to extract its data into a structured report. Supports German, English, and Dutch.",
)
async def generate_accident_report(
    image: UploadFile = File(...),
    language: Language = Query(Language.DE, description="Language for the accident report"),
    skip_fraud_check: bool = Query(False, description="Skip fraud detection entirely (not recommended for production)"),
    process_anyway: bool = Query(False, description="Process the request even if potential fraud is detected"),
    accident_report_service: AccidentReportService = Depends(get_accident_report_service),
):
    """
    Process uploaded accident image and generate a structured accident report
    """
    # Track if we have a fraud warning to include in the response
    fraud_warning = None
    
    try:
        logger.info(f"Processing uploaded accident image: {image.filename} in language: {language}")
        
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
        
        # Extract metadata from image - do this before fraud check to use the same metadata
        logger.info("Extracting image metadata")
        metadata = extract_image_metadata(image_content)
        
        # Fraud detection
        if not skip_fraud_check:
            logger.info("Running fraud detection")
            is_fraud, fraud_reason = detect_potential_fraud(image_content)
            if is_fraud:
                logger.warning(f"Potential fraud detected: {fraud_reason}")
                fraud_warning = f"Potential fraud detected: {fraud_reason}"
                
                # Add the fraud reason to metadata to ensure LLM sees it even if we process anyway
                if "fraud_indicators" not in metadata:
                    metadata["fraud_indicators"] = []
                if fraud_reason not in metadata["fraud_indicators"]:
                    metadata["fraud_indicators"].append(fraud_reason)
                
                # If not processing anyway, return a 202 Accepted with warning but no report
                if not process_anyway:
                    logger.info("Returning fraud warning without report")
                    return JSONResponse(
                        status_code=202,
                        content={
                            "warning": fraud_warning,
                            "message": "The image may be modified or manipulated. If this is a mistake, retry with process_anyway=true or contact support.",
                            "accident_report": None
                        }
                    )
                
                # If processing anyway, continue but log the decision
                logger.info("Processing despite fraud detection (process_anyway=true)")
        else:
            logger.info("Fraud detection skipped")
        
        # Resize image if needed for API limitations
        logger.info("Resizing image if needed")
        image_content = resize_image_if_needed(image_content)
        
        # Process with accident report service, passing the metadata and language
        logger.info(f"Sending image to generate accident report in {language}")
        report = await accident_report_service.generate_accident_report(image_content, language, metadata)
        logger.info("Accident report generation completed successfully")
        
        # If we have a fraud warning but still processing, include it in the response
        if fraud_warning:
            # We need to attach the warning to the response. Since the response model is strict, 
            # we'll return a JSON response with both the warning and the report
            return JSONResponse(
                status_code=202,
                content={
                    "warning": fraud_warning,
                    "message": "Report generated but fraud detection triggered. Results may be unreliable.",
                    "accident_report": report.model_dump(by_alias=True)
                }
            )
        
        # No fraud warning, return normal result
        return report
    
    except HTTPException as http_e:
        # Re-raise HTTP exceptions
        logger.warning(f"HTTP Exception: {http_e.detail}")
        raise http_e
    
    except Exception as e:
        logger.error(f"Error generating accident report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process image: {str(e)}",
        )

@router.post(
    "/generate-accident-report-base64",
    response_model=Union[AccidentReport, AccidentReportEN, AccidentReportNL],
    summary="Generate accident report from base64-encoded image",
    description="Submit a base64-encoded image of a completed European Accident Statement form to extract its data into a structured report. Supports German, English, and Dutch.",
)
async def generate_accident_report_base64(
    request: Base64ImageRequest,
    language: Language = Query(Language.DE, description="Language for the accident report"),
    skip_fraud_check: bool = Query(False, description="Skip fraud detection entirely (not recommended for production)"),
    process_anyway: bool = Query(False, description="Process the request even if potential fraud is detected"),
    accident_report_service: AccidentReportService = Depends(get_accident_report_service),
):
    """
    Process base64-encoded accident image and generate a structured accident report
    """
    # Track if we have a fraud warning to include in the response
    fraud_warning = None
    
    try:
        logger.info(f"Processing base64-encoded accident image in language: {language}")
        
        # Convert base64 to image bytes
        try:
            image_content = base64.b64decode(request.image)
            logger.debug(f"Decoded image size: {len(image_content)} bytes")
        except Exception as e:
            logger.warning(f"Invalid base64 image: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail="Invalid base64 encoding. Please provide a properly encoded image.",
            )
        
        # Validate image
        logger.info("Validating image")
        is_valid, error_msg = validate_image(image_content)
        if not is_valid:
            logger.warning(f"Image validation failed: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=error_msg or "Invalid image data",
            )
        
        # Extract metadata from image - do this before fraud check to use the same metadata
        logger.info("Extracting image metadata")
        metadata = extract_image_metadata(image_content)
        
        # Fraud detection
        if not skip_fraud_check:
            logger.info("Running fraud detection")
            is_fraud, fraud_reason = detect_potential_fraud(image_content)
            if is_fraud:
                logger.warning(f"Potential fraud detected: {fraud_reason}")
                fraud_warning = f"Potential fraud detected: {fraud_reason}"
                
                # Add the fraud reason to metadata to ensure LLM sees it even if we process anyway
                if "fraud_indicators" not in metadata:
                    metadata["fraud_indicators"] = []
                if fraud_reason not in metadata["fraud_indicators"]:
                    metadata["fraud_indicators"].append(fraud_reason)
                
                # If not processing anyway, return a 202 Accepted with warning but no report
                if not process_anyway:
                    logger.info("Returning fraud warning without report")
                    return JSONResponse(
                        status_code=202,
                        content={
                            "warning": fraud_warning,
                            "message": "The image may be modified or manipulated. If this is a mistake, retry with process_anyway=true or contact support.",
                            "accident_report": None
                        }
                    )
                
                # If processing anyway, continue but log the decision
                logger.info("Processing despite fraud detection (process_anyway=true)")
        else:
            logger.info("Fraud detection skipped")
        
        # Resize image if needed for API limitations
        logger.info("Resizing image if needed")
        image_content = resize_image_if_needed(image_content)
        
        # Process with accident report service, passing the metadata and language
        logger.info(f"Sending image to generate accident report in {language}")
        report = await accident_report_service.generate_accident_report(image_content, language, metadata)
        logger.info("Accident report generation completed successfully")
        
        # If we have a fraud warning but still processing, include it in the response
        if fraud_warning:
            # We need to attach the warning to the response. Since the response model is strict, 
            # we'll return a JSON response with both the warning and the report
            return JSONResponse(
                status_code=202,
                content={
                    "warning": fraud_warning,
                    "message": "Report generated but fraud detection triggered. Results may be unreliable.",
                    "accident_report": report.model_dump(by_alias=True)
                }
            )
        
        # No fraud warning, return normal result
        return report
    
    except HTTPException as http_e:
        # Re-raise HTTP exceptions
        logger.warning(f"HTTP Exception: {http_e.detail}")
        raise http_e
    
    except Exception as e:
        logger.error(f"Error generating accident report from base64 image: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process image: {str(e)}",
        ) 