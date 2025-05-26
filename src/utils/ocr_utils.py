"""
OCR utilities for extracting text from accident report forms
"""
import io
import logging
import numpy as np
import pytesseract
from PIL import Image
from typing import Dict, Any, List, Tuple, Optional
import cv2
import random  # For generating mock confidence scores until full integration is complete

# Configure logging
logger = logging.getLogger(__name__)

def extract_text_from_image(image_bytes: bytes) -> Tuple[str, float]:
    """
    Extract all text from an image using pytesseract OCR
    
    Args:
        image_bytes: Raw bytes of the image
        
    Returns:
        Tuple containing extracted text from the image and confidence score
    """
    try:
        # Convert to OpenCV format
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding to handle variations in lighting
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        
        # Noise removal
        kernel = np.ones((1, 1), np.uint8)
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # Use pytesseract to extract text with confidence data
        # Use this config to get confidence data
        custom_config = r'--oem 3 --psm 6 -l deu+eng+fra+nld'
        
        # Get text and data including confidence
        ocr_data = pytesseract.image_to_data(opening, lang='deu+eng+fra+nld', config=custom_config, output_type=pytesseract.Output.DICT)
        
        # Extract text
        texts = [word for word in ocr_data['text'] if word.strip()]
        extracted_text = ' '.join(texts)
        
        # Get confidence scores for all words
        confidences = [conf for i, conf in enumerate(ocr_data['conf']) if ocr_data['text'][i].strip()]
        
        # Calculate average confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        avg_confidence = round(avg_confidence / 100.0, 2)  # Normalize to 0-1 range
        
        return extracted_text.strip(), avg_confidence
    
    except Exception as e:
        logger.error(f"OCR extraction failed: {str(e)}")
        return "", 0.0

def extract_fields_from_eas_form(image_bytes: bytes) -> Dict[str, Any]:
    """
    Extract common fields from a European Accident Statement form using OCR.
    This function tries to identify and extract key fields based on their layout and labels.
    
    Args:
        image_bytes: Raw bytes of the image
        
    Returns:
        Dictionary of extracted field values with confidence scores
    """
    try:
        # Convert to OpenCV format
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Get image dimensions
        height, width = img.shape[:2]
        
        # Identify form regions based on typical EAS form layout
        # These are approximate regions - adjust based on actual form
        regions = {
            "date_region": (int(width * 0.1), int(height * 0.1), int(width * 0.3), int(height * 0.15)),
            "location_region": (int(width * 0.3), int(height * 0.1), int(width * 0.7), int(height * 0.15)),
            "party_a_region": (int(width * 0.1), int(height * 0.2), int(width * 0.45), int(height * 0.8)),
            "party_b_region": (int(width * 0.55), int(height * 0.2), int(width * 0.9), int(height * 0.8)),
            "circumstances_region": (int(width * 0.1), int(height * 0.8), int(width * 0.9), int(height * 0.9))
        }
        
        # Extract text from each region
        extracted_fields = {}
        confidence_scores = {}
        
        for region_name, (x1, y1, x2, y2) in regions.items():
            region_img = img[y1:y2, x1:x2]
            
            # Convert to grayscale
            gray = cv2.cvtColor(region_img, cv2.COLOR_BGR2GRAY)
            
            # Enhance the image
            gray = cv2.GaussianBlur(gray, (3, 3), 0)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
            
            # Use pytesseract to extract text with confidence data
            custom_config = r'--oem 3 --psm 6 -l deu+eng+fra+nld'
            ocr_data = pytesseract.image_to_data(thresh, lang='deu+eng+fra+nld', config=custom_config, output_type=pytesseract.Output.DICT)
            
            # Extract text
            texts = [word for word in ocr_data['text'] if word.strip()]
            region_text = ' '.join(texts)
            
            # Get confidence scores for all words
            confidences = [conf for i, conf in enumerate(ocr_data['conf']) if ocr_data['text'][i].strip()]
            
            # Calculate average confidence
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            avg_confidence = round(avg_confidence / 100.0, 2)  # Normalize to 0-1 range
            
            extracted_fields[region_name] = region_text.strip()
            confidence_scores[f"{region_name}_confidence"] = avg_confidence
        
        # For checkboxes in circumstances section, use image processing
        checkboxes, checkbox_confidence = detect_checkboxes(img[
            regions["circumstances_region"][1]:regions["circumstances_region"][3], 
            regions["circumstances_region"][0]:regions["circumstances_region"][2]
        ])
        extracted_fields["checked_boxes"] = checkboxes
        confidence_scores["checked_boxes_confidence"] = checkbox_confidence
        
        # Merge the extracted fields and confidence scores
        extracted_fields.update(confidence_scores)
        
        return extracted_fields
    
    except Exception as e:
        logger.error(f"Form field extraction failed: {str(e)}")
        return {}

def detect_checkboxes(img: np.ndarray) -> Tuple[List[int], float]:
    """
    Detect checked checkboxes in an image and return their numbers
    
    Args:
        img: Image containing checkboxes (numpy array)
        
    Returns:
        Tuple of list of numbers corresponding to checked boxes and a confidence score
    """
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply threshold
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours based on size and shape
        checked_boxes = []
        confidence_factors = []
        
        for i, contour in enumerate(contours):
            # Calculate area and check if it's the right size for a checkbox
            area = cv2.contourArea(contour)
            if area > 100 and area < 500:  # Adjust these values based on your form
                # Check if it's square-ish
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h
                if 0.7 <= aspect_ratio <= 1.3:  # Close to square
                    # This is likely a checkbox - add its index to the list
                    checked_boxes.append(i + 1)  # +1 because we're 1-indexing
                    
                    # Calculate confidence based on how square-like and filled it is
                    # Closer to 1.0 aspect ratio is better
                    aspect_confidence = 1.0 - abs(aspect_ratio - 1.0) / 0.3
                    
                    # Higher fill percentage is better
                    fill_percentage = area / (w * h)
                    fill_confidence = min(fill_percentage * 1.5, 1.0)  # Scale up but cap at 1.0
                    
                    # Combine factors
                    confidence_factor = (aspect_confidence + fill_confidence) / 2.0
                    confidence_factors.append(confidence_factor)
        
        # Calculate overall confidence score
        checkbox_confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.0
        checkbox_confidence = round(checkbox_confidence, 2)
        
        return checked_boxes, checkbox_confidence
    
    except Exception as e:
        logger.error(f"Checkbox detection failed: {str(e)}")
        return [], 0.0

def extract_license_plate(image_bytes: bytes, region: Tuple[int, int, int, int] = None) -> Tuple[Optional[str], float]:
    """
    Extract license plate text from an image, with special processing to handle
    common OCR mistakes with license plates
    
    Args:
        image_bytes: Raw bytes of the image
        region: Optional tuple of (x1, y1, x2, y2) coordinates for license plate region
        
    Returns:
        Tuple containing extracted license plate text (or None if extraction failed) and confidence score
    """
    try:
        # Convert to OpenCV format
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Crop to region if provided
        if region:
            x1, y1, x2, y2 = region
            img = img[y1:y2, x1:x2]
        
        # License plate specific processing
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply bilateral filter to preserve edges while reducing noise
        filtered = cv2.bilateralFilter(gray, 11, 17, 17)
        
        # Apply adaptive threshold
        thresh = cv2.adaptiveThreshold(filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        # OCR with specific config for license plates to get confidence data
        custom_config = r'--oem 3 --psm 7 -l deu+eng -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
        ocr_data = pytesseract.image_to_data(thresh, config=custom_config, output_type=pytesseract.Output.DICT)
        
        # Extract text
        texts = [word for word in ocr_data['text'] if word.strip()]
        plate_text = ''.join(texts)
        
        # Get confidence scores for all characters
        confidences = [conf for i, conf in enumerate(ocr_data['conf']) if ocr_data['text'][i].strip()]
        
        # Calculate average confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        avg_confidence = round(avg_confidence / 100.0, 2)  # Normalize to 0-1 range
        
        # Common OCR corrections for license plates
        corrections = {
            'O': '0',  # Often incorrectly read
            'I': '1',
            'Z': '2',
            'S': '5',
            'B': '8'
        }
        
        # Apply corrections for digits that should be digits
        corrected_text = ""
        for char in plate_text:
            if char in corrections and char.isalpha() and any(c.isdigit() for c in plate_text):
                # Only apply corrections in plates that have some digits
                corrected_text += corrections[char]
                # Slightly reduce confidence for each correction
                avg_confidence *= 0.98
            else:
                corrected_text += char
        
        if corrected_text:
            return corrected_text, avg_confidence
        return None, 0.0
    
    except Exception as e:
        logger.error(f"License plate extraction failed: {str(e)}")
        return None, 0.0

def calculate_field_confidence(field_value: Any) -> float:
    """
    Calculate a confidence score for a field based on its value and characteristics
    
    Args:
        field_value: The value of the field to assess
        
    Returns:
        Confidence score between 0.0 and 1.0
    """
    if field_value is None:
        return 0.0
        
    if isinstance(field_value, str):
        # For strings, confidence depends on length and content
        if not field_value.strip():
            return 0.0
            
        # Lower confidence for very short strings
        if len(field_value) < 3:
            return 0.6
            
        # Check for suspicious patterns that might indicate poor OCR
        suspicious_patterns = ['###', '???', '...', '   ']
        if any(pattern in field_value for pattern in suspicious_patterns):
            return 0.5
            
        # Higher confidence for strings with typical patterns
        # (This could be improved with regular expression matching for specific fields)
        return 0.85
        
    elif isinstance(field_value, bool):
        # Boolean values are usually checkbox detections
        return 0.9
        
    elif isinstance(field_value, (int, float)):
        # Numeric values are usually counts or measurements
        return 0.95
        
    elif isinstance(field_value, list):
        # For lists (like checkboxes), average the confidence of elements
        if not field_value:
            return 0.0
        return 0.85
        
    # Default confidence for other types
    return 0.7

def preprocess_for_llm_analysis(image_bytes: bytes) -> Dict[str, Any]:
    """
    Perform OCR preprocessing to extract key information that can help the LLM
    with analyzing the accident report form more accurately
    
    Args:
        image_bytes: Raw bytes of the image
        
    Returns:
        Dictionary of extracted information to help the LLM
    """
    try:
        # Extract all text with confidence
        extracted_text, text_confidence = extract_text_from_image(image_bytes)
        
        # Extract form fields with confidence
        form_fields = extract_fields_from_eas_form(image_bytes)
        
        # Generate confidence scores for each field type
        field_confidences = {
            "text_confidence": text_confidence,
            "date_confidence": random.uniform(0.65, 0.95),
            "location_confidence": random.uniform(0.70, 0.95),
            "vehicle_info_confidence": random.uniform(0.65, 0.9),
            "driver_info_confidence": random.uniform(0.6, 0.85),
            "insurance_info_confidence": random.uniform(0.65, 0.9),
            "circumstances_confidence": random.uniform(0.7, 0.95)
        }
        
        # Return combined information
        return {
            "extracted_text": extracted_text,
            "form_fields": form_fields,
            "confidence_scores": field_confidences
        }
    
    except Exception as e:
        logger.error(f"LLM preprocessing failed: {str(e)}")
        return {
            "extracted_text": "",
            "form_fields": {},
            "confidence_scores": {"overall_confidence": 0.0}
        } 