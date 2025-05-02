"""
Fraud detection utilities for car damage claims
"""
import io
import logging
from typing import Tuple, Dict, Any, Optional
from PIL import Image
from PIL.ExifTags import TAGS

# Configure logging
logger = logging.getLogger(__name__)

def extract_image_metadata(image_bytes: bytes) -> Dict[str, Any]:
    """
    Extract metadata from image to help with fraud detection
    
    Args:
        image_bytes: Raw bytes of the image
        
    Returns:
        Dictionary containing metadata from the image
    """
    metadata = {
        "has_exif": False,
        "exif_data": {},
        "image_properties": {}
    }
    
    try:
        # Open the image
        img = Image.open(io.BytesIO(image_bytes))
        
        # Get basic image properties
        metadata["image_properties"] = {
            "format": img.format,
            "mode": img.mode,
            "width": img.width,
            "height": img.height,
            "size_bytes": len(image_bytes)
        }
        
        # Extract EXIF data if available
        exif_data = {}
        if hasattr(img, '_getexif') and img._getexif():
            metadata["has_exif"] = True
            raw_exif = img._getexif()
            
            # Convert EXIF tags to readable format
            for tag, value in raw_exif.items():
                decoded = TAGS.get(tag, tag)
                exif_data[decoded] = value
                
            # Filter out binary data for better logging
            filtered_exif = {k: v for k, v in exif_data.items() 
                            if not isinstance(v, bytes) and k not in ('MakerNote', 'UserComment')}
            
            metadata["exif_data"] = filtered_exif
            
            # Extract GPS data if available
            if 'GPSInfo' in exif_data:
                metadata["has_gps"] = True
    
    except Exception as e:
        logger.warning(f"Error extracting image metadata: {str(e)}")
    
    return metadata

def detect_potential_fraud(image_bytes: bytes) -> Tuple[bool, Optional[str]]:
    """
    Detect potential fraud in submitted car damage images
    
    Args:
        image_bytes: Raw bytes of the image
        
    Returns:
        Tuple containing a boolean (True if fraud suspected) and an optional reason
    """
    try:
        # Extract metadata
        metadata = extract_image_metadata(image_bytes)
        
        # Check 1: Is this a screenshot? (common in fraud cases)
        # Screenshots typically lack EXIF data
        if not metadata["has_exif"] and metadata["image_properties"].get("format") in ("PNG",):
            return True, "Image appears to be a screenshot, not an original photo"
        
        # Check 2: Was the image edited?
        # Some editing software leaves traces in metadata
        exif = metadata.get("exif_data", {})
        software_fields = ("Software", "ProcessingSoftware")
        for field in software_fields:
            if field in exif and any(editor in str(exif[field]) for editor in 
                                    ("Photoshop", "GIMP", "Lightroom", "Affinity")):
                return True, f"Image appears to be edited with {exif[field]}"
        
        # Additional checks can be implemented here
        
        return False, None
        
    except Exception as e:
        logger.error(f"Error in fraud detection: {str(e)}")
        # On error, don't flag as fraud but log the issue
        return False, None 