import cv2
import numpy as np
from typing import Tuple

def deskew(image: np.ndarray) -> np.ndarray:
    """
    Corrects skew in an image.

    Args:
        image: Input image as a NumPy array.

    Returns:
        Deskewed image as a NumPy array.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    coords = np.column_stack(np.where(gray > 0))
    angle = cv2.minAreaRect(coords)[-1]

    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Calculate new bounding box
    cos = np.abs(rotation_matrix[0, 0])
    sin = np.abs(rotation_matrix[0, 1])
    
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))
    
    # Adjust rotation matrix to account for translation
    rotation_matrix[0, 2] += (new_w / 2) - center[0]
    rotation_matrix[1, 2] += (new_h / 2) - center[1]
    
    deskewed = cv2.warpAffine(image, rotation_matrix, (new_w, new_h),
                              flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return deskewed

def to_grayscale(image: np.ndarray) -> np.ndarray:
    """
    Converts an image to grayscale.

    Args:
        image: Input image as a NumPy array.

    Returns:
        Grayscale image as a NumPy array.
    """
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def binarize(image: np.ndarray, threshold_value: int = 0) -> np.ndarray:
    """
    Binarizes an image using Otsu's thresholding.

    Args:
        image: Input grayscale image as a NumPy array.
        threshold_value: Threshold value. If 0, Otsu's method is used.

    Returns:
        Binarized image as a NumPy array.
    """
    if len(image.shape) == 3: # Ensure it's grayscale first
        image = to_grayscale(image)
    if threshold_value == 0:
        _, binarized = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        _, binarized = cv2.threshold(image, threshold_value, 255, cv2.THRESH_BINARY)
    return binarized

def denoise(image: np.ndarray) -> np.ndarray:
    """
    Applies Non-Local Means Denoising to an image.

    Args:
        image: Input image (can be color or grayscale).

    Returns:
        Denoised image as a NumPy array.
    """
    if len(image.shape) == 2: # Grayscale
        return cv2.fastNlMeansDenoising(image, None, h=10, templateWindowSize=7, searchWindowSize=21)
    elif len(image.shape) == 3 and image.shape[2] == 3: # Color
        return cv2.fastNlMeansDenoisingColored(image, None, h=10, hColor=10, templateWindowSize=7, searchWindowSize=21)
    return image # Return as-is if not grayscale or BGR color

def upscale_to_dpi(image: np.ndarray, target_dpi: int = 300, current_dpi: int = 72) -> Tuple[np.ndarray, float]:
    """
    Upscales an image to a target DPI.

    Args:
        image: Input image as a NumPy array.
        target_dpi: The desired DPI for the output image.
        current_dpi: The current DPI of the input image.

    Returns:
        A tuple containing the upscaled image and the scaling factor used.
    """
    if current_dpi <= 0:
        current_dpi = 72 # Assume a default if invalid
    scaling_factor = target_dpi / current_dpi
    if scaling_factor <= 1.0: # No upscaling needed or invalid factor
        return image, 1.0

    new_width = int(image.shape[1] * scaling_factor)
    new_height = int(image.shape[0] * scaling_factor)
    
    # Use Lanczos interpolation for upscaling, as it's good for preserving detail
    upscaled_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
    return upscaled_image, scaling_factor

def apply_unsharp_mask(image: np.ndarray, sigma: float = 1.0, strength: float = 1.5) -> np.ndarray:
    """
    Applies an unsharp mask to enhance image sharpness.

    Args:
        image: Input image as a NumPy array.
        sigma: Gaussian blur sigma value.
        strength: Strength of the sharpening effect.

    Returns:
        Sharpened image as a NumPy array.
    """
    blurred = cv2.GaussianBlur(image, (0, 0), sigma)
    sharpened = cv2.addWeighted(image, 1.0 + strength, blurred, -strength, 0)
    return sharpened

def preprocess_image_for_ocr(image_bytes: bytes, target_dpi: int = 300, current_dpi: int = 72) -> np.ndarray:
    """
    Applies a full suite of preprocessing steps to an image for OCR.
    - Converts bytes to OpenCV image.
    - Deskews.
    - Converts to grayscale.
    - Upscales to target DPI.
    - Applies unsharp mask.
    - Denoises.
    - Binarizes.

    Args:
        image_bytes: Raw bytes of the image.
        target_dpi: Target DPI for upscaling.
        current_dpi: Current DPI of the image.

    Returns:
        Preprocessed image as a NumPy array (binary).
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Could not decode image from bytes.")

    # 1. Deskew (works best on color or grayscale before intense binarization)
    deskewed_image = deskew(image)
    
    # 2. Convert to Grayscale
    gray_image = to_grayscale(deskewed_image)
    
    # 3. Upscale to target DPI (e.g., >=300 dpi)
    # Assuming a common default if not provided, e.g., 72 DPI for screen images
    upscaled_image, _ = upscale_to_dpi(gray_image, target_dpi=target_dpi, current_dpi=current_dpi)
    
    # 4. Apply Unsharp Mask for sharpening
    sharpened_image = apply_unsharp_mask(upscaled_image)
    
    # 5. Denoise (after upscaling and sharpening can be beneficial)
    denoised_image = denoise(sharpened_image)
    
    # 6. Binarize (Otsu's method is generally robust)
    binary_image = binarize(denoised_image)
    
    return binary_image

def encode_image_for_form_recognizer(image: np.ndarray, extension: str = ".png") -> bytes:
    """
    Encodes a NumPy image array to bytes in the specified format for Form Recognizer.

    Args:
        image: Preprocessed image as a NumPy array.
        extension: The desired image format (e.g., ".png", ".jpeg"). Default is ".png".

    Returns:
        Image bytes.
    """
    is_success, image_bytes = cv2.imencode(extension, image)
    if not is_success:
        raise ValueError(f"Could not encode image to {extension} format.")
    return image_bytes.tobytes() 