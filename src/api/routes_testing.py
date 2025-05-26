"""
API routes for testing image processing and OCR functionalities.
"""
import base64
import io
from typing import Union, Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Query, Depends
from fastapi.responses import FileResponse
from PIL import Image
import tempfile

from src.schemas.base64_request import Base64ImageRequest
from src.schemas.testing_utils import (
    EnhancedImageResponse,
    OCRTextResponse,
    EnhancedImageAndOCRResponse,
    ImageOutputType
)
from src.utils.image_utils import preprocess_accident_report_image, validate_image, preprocess_image_for_ocr
from src.utils.ocr_utils import extract_text_from_image

router = APIRouter(
    prefix="/testing",
    tags=["Testing Utilities"],
)

# Dependency for file uploads
async def get_image_bytes_from_upload(image: UploadFile = File(...)) -> bytes:
    # The File(...) with ellipses makes it a required form field
    if not image:
        raise HTTPException(status_code=400, detail="No image file provided in form-data.")
    contents = await image.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded image file is empty.")
    return contents

# Dependency for base64 JSON body
async def get_image_bytes_from_base64(request_body: Base64ImageRequest) -> bytes:
    if not request_body or not request_body.image_base64:
        raise HTTPException(status_code=400, detail="No image_base64 provided in JSON body.")
    try:
        return base64.b64decode(request_body.image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 string: {str(e)}")

def image_bytes_to_base64_string(image_bytes: bytes, image_format: str = "PNG") -> str:
    return base64.b64encode(image_bytes).decode('utf-8')

@router.post("/enhance-image", response_model=EnhancedImageResponse, summary="Enhance an uploaded image")
async def enhance_image_upload(
    image_bytes: bytes = Depends(get_image_bytes_from_upload),
    output_type: ImageOutputType = Query(ImageOutputType.BASE64, description="Desired output format for the image.")
):
    """Enhance an uploaded image (e.g., European Accident Statement form) and return it."""
    try:
        is_valid, error = validate_image(image_bytes)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid image: {error}")
        
        enhanced_image_bytes = preprocess_accident_report_image(image_bytes)

        if output_type == ImageOutputType.BASE64:
            base64_str = image_bytes_to_base64_string(enhanced_image_bytes)
            return EnhancedImageResponse(image_base64=base64_str, message="Enhanced image in base64 format.")
        elif output_type == ImageOutputType.FILE:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                tmpfile.write(enhanced_image_bytes)
                tmp_file_path = tmpfile.name
            return FileResponse(path=tmp_file_path, media_type='image/png', filename='enhanced_image.png')
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enhancing image: {str(e)}")

@router.post("/enhance-image-base64", response_model=EnhancedImageResponse, summary="Enhance a base64 encoded image")
async def enhance_image_b64(
    image_bytes: bytes = Depends(get_image_bytes_from_base64),
    output_type: ImageOutputType = Query(ImageOutputType.BASE64, description="Desired output format for the image.")
):
    """Enhance a base64 encoded image and return it."""
    try:
        is_valid, error = validate_image(image_bytes)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid image: {error}")
        
        enhanced_image_bytes = preprocess_accident_report_image(image_bytes)

        if output_type == ImageOutputType.BASE64:
            base64_str = image_bytes_to_base64_string(enhanced_image_bytes)
            return EnhancedImageResponse(image_base64=base64_str, message="Enhanced image in base64 format.")
        elif output_type == ImageOutputType.FILE:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                tmpfile.write(enhanced_image_bytes)
                tmp_file_path = tmpfile.name
            return FileResponse(path=tmp_file_path, media_type='image/png', filename='enhanced_image.png')
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enhancing image: {str(e)}")

@router.post("/ocr-image", response_model=OCRTextResponse, summary="Perform OCR on an uploaded image")
async def ocr_image_upload(image_bytes: bytes = Depends(get_image_bytes_from_upload)):
    """Extract text from an uploaded image using OCR."""
    try:
        is_valid, error = validate_image(image_bytes)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid image: {error}")
        
        # Preprocess specifically for OCR
        ocr_ready_image_bytes = preprocess_image_for_ocr(image_bytes)
        extracted_text, _ = extract_text_from_image(ocr_ready_image_bytes)
        return OCRTextResponse(extracted_text=extracted_text)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during OCR: {str(e)}")

@router.post("/ocr-image-base64", response_model=OCRTextResponse, summary="Perform OCR on a base64 encoded image")
async def ocr_image_b64(image_bytes: bytes = Depends(get_image_bytes_from_base64)):
    """Extract text from a base64 encoded image using OCR."""
    try:
        is_valid, error = validate_image(image_bytes)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid image: {error}")

        # Preprocess specifically for OCR
        ocr_ready_image_bytes = preprocess_image_for_ocr(image_bytes)
        extracted_text, _ = extract_text_from_image(ocr_ready_image_bytes)
        return OCRTextResponse(extracted_text=extracted_text)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during OCR: {str(e)}")

@router.post("/enhance-and-ocr-image", response_model=EnhancedImageAndOCRResponse, summary="Enhance an uploaded image and perform OCR")
async def enhance_and_ocr_image_upload(image_bytes: bytes = Depends(get_image_bytes_from_upload)):
    """Enhance an image, then perform OCR on the enhanced version."""
    try:
        is_valid, error = validate_image(image_bytes)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid image: {error}")

        # Enhance image for display
        enhanced_image_bytes = preprocess_accident_report_image(image_bytes)
        
        # Preprocess original image for OCR
        ocr_ready_image_bytes = preprocess_image_for_ocr(image_bytes) # Use original image_bytes for OCR
        extracted_text, _ = extract_text_from_image(ocr_ready_image_bytes)
        
        base64_str = image_bytes_to_base64_string(enhanced_image_bytes)
        
        return EnhancedImageAndOCRResponse(
            enhanced_image_base64=base64_str,
            ocr_result=OCRTextResponse(extracted_text=extracted_text)
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during enhancement and OCR: {str(e)}")

@router.post("/enhance-and-ocr-image-base64", response_model=EnhancedImageAndOCRResponse, summary="Enhance a base64 image and perform OCR")
async def enhance_and_ocr_image_b64(image_bytes: bytes = Depends(get_image_bytes_from_base64)):
    """Enhance a base64 encoded image, then perform OCR on the enhanced version."""
    try:
        is_valid, error = validate_image(image_bytes)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid image: {error}")

        # Enhance image for display
        enhanced_image_bytes = preprocess_accident_report_image(image_bytes)
        
        # Preprocess original image for OCR
        ocr_ready_image_bytes = preprocess_image_for_ocr(image_bytes) # Use original image_bytes for OCR
        extracted_text, _ = extract_text_from_image(ocr_ready_image_bytes)
        
        base64_str = image_bytes_to_base64_string(enhanced_image_bytes)
        
        return EnhancedImageAndOCRResponse(
            enhanced_image_base64=base64_str,
            ocr_result=OCRTextResponse(extracted_text=extracted_text)
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during enhancement and OCR: {str(e)}") 