"""
Pydantic models for testing utility endpoints.
"""
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum

class ImageOutputType(str, Enum):
    BASE64 = "base64"
    FILE = "file" # Note: File response will be handled by FastAPI's FileResponse

class OCRTextResponse(BaseModel):
    extracted_text: str = Field(description="Raw text extracted from the image using OCR.")

class EnhancedImageResponse(BaseModel):
    image_base64: Optional[str] = Field(default=None, description="Base64 encoded string of the enhanced image. Provided if output_type is 'base64'.")
    # If output_type is 'file', the actual response will be a FileResponse, not part of this model directly.
    # The model can still be used as a response_model for documentation purposes.
    message: Optional[str] = Field(default=None, description="A message indicating the output type or status.")


class EnhancedImageAndOCRResponse(BaseModel):
    enhanced_image_base64: str = Field(description="Base64 encoded string of the enhanced image.")
    ocr_result: OCRTextResponse = Field(description="OCR results from the enhanced image.") 