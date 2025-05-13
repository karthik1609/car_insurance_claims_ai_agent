"""
Schema for base64 encoded image request
"""
from typing import Optional
from pydantic import BaseModel, Field, validator
import base64
import binascii

class Base64ImageRequest(BaseModel):
    """Request model for submitting base64-encoded image data"""
    image_base64: str = Field(
        ..., 
        description="Base64-encoded image data (should not include data:image prefix)"
    )
    image_format: Optional[str] = Field(
        None, 
        description="Format of the image (jpg, png, etc.) if known"
    )
    
    @validator('image_base64')
    def validate_base64(cls, v):
        """Validate that the string is valid base64"""
        try:
            # Try to decode - this will fail if not valid base64
            decoded = base64.b64decode(v)
            
            # Make sure it's not just an empty string or too short
            if len(decoded) < 10:
                raise ValueError("Decoded base64 image is too small")
                
            return v
        except binascii.Error:
            raise ValueError("Invalid base64 encoding")
        except Exception as e:
            raise ValueError(f"Base64 validation error: {str(e)}") 