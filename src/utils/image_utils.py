"""
Image processing utilities for car damage assessment and accident report processing
"""
import io
import logging
import numpy as np
from typing import Tuple, Optional, Dict, Any
from PIL import Image, ImageEnhance, ImageFilter, UnidentifiedImageError
import cv2

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

def enhance_document_image(image_bytes: bytes) -> bytes:
    """
    Enhance an image of a document to improve text readability and form recognition.
    
    This function applies several enhancements:
    1. Contrast adjustment
    2. Sharpening
    3. Noise reduction
    4. Perspective correction (if needed)
    
    Args:
        image_bytes: Raw bytes of the image
        
    Returns:
        Bytes of the enhanced image
    """
    try:
        # Open the image
        img = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if image is in RGBA mode
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        # Apply contrast enhancement
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)  # Increase contrast
        
        # Apply sharpening
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.5)  # Increase sharpness
        
        # Apply noise reduction
        img = img.filter(ImageFilter.SMOOTH_MORE)
        
        # Save to bytes
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=95)
        output.seek(0)
        
        return output.getvalue()
    
    except Exception as e:
        logger.warning(f"Image enhancement failed: {str(e)}. Using original image.")
        return image_bytes

def detect_and_correct_perspective(image_bytes: bytes) -> bytes:
    """
    Detect document edges and correct perspective distortion if a form is detected.
    Useful for images of accident forms taken at an angle.
    
    Args:
        image_bytes: Raw bytes of the image
        
    Returns:
        Bytes of the perspective-corrected image, or original if no correction needed
    """
    try:
        # Convert bytes to OpenCV format
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Edge detection
        edges = cv2.Canny(blur, 75, 200)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        # Sort contours by area (largest first)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        # Initialize variables
        max_area = 0
        document_contour = None
        
        # Look for rectangular contours (likely to be a document)
        for contour in contours[:5]:  # Check only the largest contours
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            
            # If contour has 4 corners, it might be a document
            if len(approx) == 4:
                area = cv2.contourArea(approx)
                # Check if it's a significant part of the image
                if area > img.shape[0] * img.shape[1] * 0.1 and area > max_area:
                    max_area = area
                    document_contour = approx
        
        # If a document contour was found, perform perspective correction
        if document_contour is not None:
            # Order points in the correct order (top-left, top-right, bottom-right, bottom-left)
            pts = document_contour.reshape(4, 2)
            rect = np.zeros((4, 2), dtype="float32")
            
            # Top-left point has the smallest sum of coordinates
            # Bottom-right point has the largest sum
            s = pts.sum(axis=1)
            rect[0] = pts[np.argmin(s)]
            rect[2] = pts[np.argmax(s)]
            
            # Top-right point has the smallest difference between coordinates
            # Bottom-left point has the largest difference
            diff = np.diff(pts, axis=1)
            rect[1] = pts[np.argmin(diff)]
            rect[3] = pts[np.argmax(diff)]
            
            # Calculate width and height of the document
            width_a = np.sqrt(((rect[2][0] - rect[3][0]) ** 2) + ((rect[2][1] - rect[3][1]) ** 2))
            width_b = np.sqrt(((rect[1][0] - rect[0][0]) ** 2) + ((rect[1][1] - rect[0][1]) ** 2))
            max_width = max(int(width_a), int(width_b))
            
            height_a = np.sqrt(((rect[1][0] - rect[2][0]) ** 2) + ((rect[1][1] - rect[2][1]) ** 2))
            height_b = np.sqrt(((rect[0][0] - rect[3][0]) ** 2) + ((rect[0][1] - rect[3][1]) ** 2))
            max_height = max(int(height_a), int(height_b))
            
            # Create destination points
            dst = np.array([
                [0, 0],
                [max_width - 1, 0],
                [max_width - 1, max_height - 1],
                [0, max_height - 1]
            ], dtype="float32")
            
            # Calculate perspective transform matrix
            M = cv2.getPerspectiveTransform(rect, dst)
            
            # Apply transformation
            warped = cv2.warpPerspective(img, M, (max_width, max_height))
            
            # Convert back to bytes
            success, buffer = cv2.imencode(".jpg", warped)
            if success:
                return bytes(buffer)
        
        # If no correction was made, return original
        return image_bytes
        
    except Exception as e:
        logger.warning(f"Perspective correction failed: {str(e)}. Using original image.")
        return image_bytes

def preprocess_accident_report_image(image_bytes: bytes) -> bytes:
    """
    Apply a full preprocessing pipeline for accident report form images:
    1. Perspective correction
    2. Document enhancement
    3. Image resizing if needed
    
    Args:
        image_bytes: Raw bytes of the image
        
    Returns:
        Bytes of the fully preprocessed image
    """
    try:
        # Step 1: Correct perspective
        processed_image = detect_and_correct_perspective(image_bytes)
        
        # Step 2: Enhance document
        processed_image = enhance_document_image(processed_image)
        
        # Step 3: Resize if needed
        processed_image = resize_image_if_needed(processed_image)
        
        return processed_image
        
    except Exception as e:
        logger.error(f"Image preprocessing failed: {str(e)}. Using original image.")
        return image_bytes

def preprocess_image_for_ocr(image_bytes: bytes) -> bytes:
    """
    Preprocess an image specifically for OCR (Tesseract).
    This involves:
    1. Perspective correction.
    2. Conversion to grayscale.
    3. Adaptive thresholding.
    
    Args:
        image_bytes: Raw bytes of the image
        
    Returns:
        Bytes of the OCR-preprocessed image (PNG format)
    """
    try:
        # Step 1: Correct perspective (re-uses existing function)
        # This function returns JPEG bytes, so we'll need to decode for OpenCV
        persp_corrected_bytes = detect_and_correct_perspective(image_bytes)

        # Convert bytes to OpenCV format
        nparr = np.frombuffer(persp_corrected_bytes, np.uint8)
        img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_cv is None:
            logger.warning("Failed to decode image after perspective correction for OCR. Using original.")
            # Fallback to original if perspective correction somehow failed to produce a valid image
            nparr_orig = np.frombuffer(image_bytes, np.uint8)
            img_cv = cv2.imdecode(nparr_orig, cv2.IMREAD_COLOR)
            if img_cv is None:
                logger.error("Failed to decode original image for OCR. Cannot preprocess.")
                return image_bytes # give up

        # Step 2: Convert to grayscale
        gray_img = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # Step 3: Apply adaptive thresholding
        # ADAPTIVE_THRESH_GAUSSIAN_C is often good for variable lighting
        # C is a constant subtracted from the mean or weighted sum
        # blockSize is the size of a pixel neighborhood that is used to calculate a threshold value
        # Adjust C and blockSize as needed based on typical image characteristics
        binary_img = cv2.adaptiveThreshold(
            gray_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2  # Block size 11, Constant 2
        )
        
        # Encode to PNG bytes (lossless, good for OCR)
        success, buffer = cv2.imencode(".png", binary_img)
        if success:
            return bytes(buffer)
        else:
            logger.warning("Failed to encode OCR preprocessed image to PNG. Returning perspective corrected JPEG.")
            # Fallback to JPEG if PNG encoding fails for some reason
            success_jpg, buffer_jpg = cv2.imencode(".jpg", binary_img)
            if success_jpg:
                return bytes(buffer_jpg)
            return persp_corrected_bytes # Fallback further

    except Exception as e:
        logger.error(f"OCR image preprocessing failed: {str(e)}. Using original image bytes.")
        return image_bytes 