"""
Image processing utilities for car damage assessment
"""
import io
import logging
from typing import Tuple, Optional
from PIL import Image, UnidentifiedImageError

# Configure logging
logger = logging.getLogger(__name__)

def validate_image(image_bytes: bytes) -> Tuple[bool, Optional[str]]:
    """
    Validate if the provided bytes represent a valid image
    
    Args:
        image_bytes: Raw bytes of the image
        
    Returns:
        Tuple containing a boolean (True if valid) and an optional error message
    """
    try:
        # Try to open the image with PIL
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()  # Verify it's a valid image
        return True, None
    except UnidentifiedImageError:
        return False, "The file is not a valid image"
    except Exception as e:
        logger.error(f"Image validation error: {str(e)}")
        return False, f"Image validation failed: {str(e)}"

def resize_image_if_needed(image_bytes: bytes, max_size: int = 5 * 1024 * 1024) -> bytes:
    """
    Resize the image if it exceeds the maximum allowed size for API calls
    
    Args:
        image_bytes: Raw bytes of the image
        max_size: Maximum size in bytes (default: 5MB)
        
    Returns:
        Bytes of the resized image or original if already within size limits
    """
    if len(image_bytes) <= max_size:
        return image_bytes
    
    try:
        # Open the image
        img = Image.open(io.BytesIO(image_bytes))
        
        # Calculate the scale factor based on the max size
        scale_factor = (max_size / len(image_bytes)) ** 0.5
        
        # Calculate new dimensions
        new_width = int(img.width * scale_factor)
        new_height = int(img.height * scale_factor)
        
        # Resize the image
        resized_img = img.resize((new_width, new_height))
        
        # Save to bytes
        output = io.BytesIO()
        resized_img.save(output, format=img.format if img.format else 'JPEG')
        output.seek(0)
        
        return output.getvalue()
    
    except Exception as e:
        logger.warning(f"Image resize failed: {str(e)}. Using original image.")
        return image_bytes 