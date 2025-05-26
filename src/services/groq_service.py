"""
Groq service for car damage assessment using Llama 4 Maverick
"""
import base64
import logging
import json
import traceback
from typing import Dict, Any, List, Union, Optional
from groq import Groq

from src.core.config import settings
from src.schemas.damage_assessment_enhanced import EnhancedDamageAssessmentResponse, DamageAssessmentItem
from src.logger import get_logger
from src.utils.fraud_detection import extract_image_metadata

# Configure logging
logger = get_logger(__name__)

class GroqService:
    """Service to interact with Groq API for car damage assessment using Llama 4 Maverick"""
    
    def __init__(self):
        """Initialize the Groq client"""
        api_key = settings.GROQ_API_KEY
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        
        self.client = Groq(api_key=api_key)
        self.model = settings.GROQ_MODEL
        logger.debug(f"Groq client initialized with model: {self.model}")
    
    def validate_total_costs(self, assessment_data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Ensure the cost calculations are correct in the assessment data
        
        Args:
            assessment_data: Either a single assessment object or a list of assessments
            
        Returns:
            The validated assessment data with corrected cost totals if needed
        """
        try:
            # Handle list of assessments
            if isinstance(assessment_data, list):
                logger.debug(f"Validating costs for {len(assessment_data)} assessments")
                for item in assessment_data:
                    self._validate_single_assessment(item)
                return assessment_data
            
            # Handle single assessment
            elif isinstance(assessment_data, dict) and "vehicle_info" in assessment_data and "damage_data" in assessment_data:
                logger.debug("Validating costs for single assessment")
                self._validate_single_assessment(assessment_data)
                return assessment_data
            
            else:
                logger.warning(f"Unexpected assessment_data structure: {type(assessment_data)}")
                return assessment_data
            
        except Exception as e:
            logger.error(f"Error in validate_total_costs: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def _validate_single_assessment(self, item: Dict[str, Any]) -> None:
        """
        Validate and correct the cost calculations for a single assessment
        
        Args:
            item: A single assessment dictionary
        """
        try:
            if "damage_data" in item and "cost_breakdown" in item["damage_data"]:
                cost_breakdown = item["damage_data"]["cost_breakdown"]
                
                # Validate parts total
                if "parts" in cost_breakdown and "parts_total" in cost_breakdown:
                    parts = cost_breakdown["parts"]
                    
                    expected_sum = sum(part.get("cost", 0) for part in parts)
                    expected_min = sum(part.get("min_cost", 0) for part in parts)
                    expected_max = sum(part.get("max_cost", 0) for part in parts)
                    
                    if abs(cost_breakdown["parts_total"].get("expected", 0) - expected_sum) > 1:
                        logger.warning(f"Correcting parts total: {cost_breakdown['parts_total'].get('expected', 0)} → {expected_sum}")
                        cost_breakdown["parts_total"]["expected"] = expected_sum
                    
                    if abs(cost_breakdown["parts_total"].get("min", 0) - expected_min) > 1:
                        logger.warning(f"Correcting parts min: {cost_breakdown['parts_total'].get('min', 0)} → {expected_min}")
                        cost_breakdown["parts_total"]["min"] = expected_min
                    
                    if abs(cost_breakdown["parts_total"].get("max", 0) - expected_max) > 1:
                        logger.warning(f"Correcting parts max: {cost_breakdown['parts_total'].get('max', 0)} → {expected_max}")
                        cost_breakdown["parts_total"]["max"] = expected_max
                
                # Validate labor total
                if "labor" in cost_breakdown and "labor_total" in cost_breakdown:
                    labor = cost_breakdown["labor"]
                    
                    expected_sum = sum(labor_item.get("cost", 0) for labor_item in labor)
                    expected_min = sum(labor_item.get("min_cost", 0) for labor_item in labor)
                    expected_max = sum(labor_item.get("max_cost", 0) for labor_item in labor)
                    
                    if abs(cost_breakdown["labor_total"].get("expected", 0) - expected_sum) > 1:
                        logger.warning(f"Correcting labor total: {cost_breakdown['labor_total'].get('expected', 0)} → {expected_sum}")
                        cost_breakdown["labor_total"]["expected"] = expected_sum
                    
                    if abs(cost_breakdown["labor_total"].get("min", 0) - expected_min) > 1:
                        logger.warning(f"Correcting labor min: {cost_breakdown['labor_total'].get('min', 0)} → {expected_min}")
                        cost_breakdown["labor_total"]["min"] = expected_min
                    
                    if abs(cost_breakdown["labor_total"].get("max", 0) - expected_max) > 1:
                        logger.warning(f"Correcting labor max: {cost_breakdown['labor_total'].get('max', 0)} → {expected_max}")
                        cost_breakdown["labor_total"]["max"] = expected_max
                
                # Validate fees total
                if "additional_fees" in cost_breakdown and "fees_total" in cost_breakdown:
                    fees = cost_breakdown["additional_fees"]
                    
                    expected_sum = sum(fee.get("cost", 0) for fee in fees)
                    expected_min = sum(fee.get("min_cost", 0) for fee in fees)
                    expected_max = sum(fee.get("max_cost", 0) for fee in fees)
                    
                    if abs(cost_breakdown["fees_total"].get("expected", 0) - expected_sum) > 1:
                        logger.warning(f"Correcting fees total: {cost_breakdown['fees_total'].get('expected', 0)} → {expected_sum}")
                        cost_breakdown["fees_total"]["expected"] = expected_sum
                    
                    if abs(cost_breakdown["fees_total"].get("min", 0) - expected_min) > 1:
                        logger.warning(f"Correcting fees min: {cost_breakdown['fees_total'].get('min', 0)} → {expected_min}")
                        cost_breakdown["fees_total"]["min"] = expected_min
                    
                    if abs(cost_breakdown["fees_total"].get("max", 0) - expected_max) > 1:
                        logger.warning(f"Correcting fees max: {cost_breakdown['fees_total'].get('max', 0)} → {expected_max}")
                        cost_breakdown["fees_total"]["max"] = expected_max
                
                # Validate total estimate
                if "parts_total" in cost_breakdown and "labor_total" in cost_breakdown and "fees_total" in cost_breakdown and "total_estimate" in cost_breakdown:
                    expected_sum = (
                        cost_breakdown["parts_total"].get("expected", 0) +
                        cost_breakdown["labor_total"].get("expected", 0) +
                        cost_breakdown["fees_total"].get("expected", 0)
                    )
                    expected_min = (
                        cost_breakdown["parts_total"].get("min", 0) +
                        cost_breakdown["labor_total"].get("min", 0) +
                        cost_breakdown["fees_total"].get("min", 0)
                    )
                    expected_max = (
                        cost_breakdown["parts_total"].get("max", 0) +
                        cost_breakdown["labor_total"].get("max", 0) +
                        cost_breakdown["fees_total"].get("max", 0)
                    )
                    
                    if abs(cost_breakdown["total_estimate"].get("expected", 0) - expected_sum) > 1:
                        logger.warning(f"Correcting total: {cost_breakdown['total_estimate'].get('expected', 0)} → {expected_sum}")
                        cost_breakdown["total_estimate"]["expected"] = expected_sum
                    
                    if abs(cost_breakdown["total_estimate"].get("min", 0) - expected_min) > 1:
                        logger.warning(f"Correcting total min: {cost_breakdown['total_estimate'].get('min', 0)} → {expected_min}")
                        cost_breakdown["total_estimate"]["min"] = expected_min
                    
                    if abs(cost_breakdown["total_estimate"].get("max", 0) - expected_max) > 1:
                        logger.warning(f"Correcting total max: {cost_breakdown['total_estimate'].get('max', 0)} → {expected_max}")
                        cost_breakdown["total_estimate"]["max"] = expected_max
                
                # Ensure make_certainty is present
                if "vehicle_info" in item and "make_certainty" not in item["vehicle_info"]:
                    item["vehicle_info"]["make_certainty"] = 85.0
                
                # Ensure model_certainty is present
                if "vehicle_info" in item and "model_certainty" not in item["vehicle_info"]:
                    item["vehicle_info"]["model_certainty"] = 80.0
            
        except Exception as e:
            logger.error(f"Error validating single assessment: {str(e)}")
    
    async def analyze_car_damage(self, image_bytes: bytes, metadata: Optional[Dict[str, Any]] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Analyze car image using Llama 4 Maverick model to detect damage and estimate repair costs
        
        Args:
            image_bytes: The raw bytes of the uploaded image
            metadata: Optional metadata extracted from the image
            
        Returns:
            Union[Dict[str, Any], List[Dict[str, Any]]]: Single damage assessment or list of assessments if multiple cars detected
        """
        # Encode image to base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        logger.info("Image encoded to base64")
        
        # If metadata not provided, extract it
        if metadata is None:
            logger.info("Extracting image metadata")
            metadata = extract_image_metadata(image_bytes)
        
        # Prepare metadata for prompt
        metadata_prompt = self._format_metadata_for_prompt(metadata)
        
        # Define the system prompt with enhanced JSON structure
        system_prompt = f"""You are a car insurance damage assessment AI. Your task is to analyze images of damaged vehicles, identify make/model/year, assess damage severity, estimate repair costs, and evaluate fraud risk.

{metadata_prompt}

IMPORTANT: If there are any potential fraud indicators in the metadata (editing software, lack of EXIF data, etc.), you MUST incorporate these into your fraud_analysis section and adjust the fraud_risk_level accordingly.

Please provide an analysis in this JSON structure:

// For a single vehicle
{{
  "vehicle_info": {{
    "make": "Toyota", // Brand of the car
    "model": "Camry", // Model of the car
    "year": "2019", // Estimated year (as string)
    "color": "Silver", // Main color
    "type": "Sedan", // Body type: Sedan, SUV, Truck, etc.
    "trim": "SE", // If identifiable
    "make_certainty": 95.0, // Confidence level (0-100) that make is correctly identified
    "model_certainty": 90.0 // Confidence level (0-100) that model is correctly identified
  }},
  "damage_data": {{
    "damaged_parts": [
      {{
        "part": "Front Bumper", // Name of damaged part
        "damage_type": "Dented", // Type of damage: Dented, Scratched, Broken, Crushed, etc.
        "severity": "Moderate", // Severity: Minor, Moderate, Severe
        "repair_action": "Replace" // Repair, Replace, Paint, etc.
      }},
      // Additional damaged parts...
    ],
    "cost_breakdown": {{
      "parts": [
        {{
          "name": "Front Bumper",
          "cost": 350, // Expected cost in currency units
          "min_cost": 300, // Minimum possible cost
          "max_cost": 400 // Maximum possible cost
        }},
        // Additional parts...
      ],
      "labor": [
        {{
          "service": "Bumper removal and replacement",
          "hours": 2, // Estimated hours
          "rate": 85, // Hourly rate
          "cost": 170, // Expected cost (hours × rate)
          "min_cost": 150, // Minimum possible cost
          "max_cost": 190 // Maximum possible cost
        }},
        // Additional labor items...
      ],
      "additional_fees": [
        {{
          "description": "Hazardous material disposal",
          "cost": 50, // Expected cost
          "min_cost": 40, // Minimum possible cost
          "max_cost": 60 // Maximum possible cost
        }},
        // Additional fees...
      ],
      "parts_total": {{
        "min": 300, // Sum of all parts min_cost values
        "max": 400, // Sum of all parts max_cost values
        "expected": 350 // Sum of all parts cost values
      }},
      "labor_total": {{
        "min": 150, // Sum of all labor min_cost values
        "max": 190, // Sum of all labor max_cost values
        "expected": 170 // Sum of all labor cost values
      }},
      "fees_total": {{
        "min": 40, // Sum of all fees min_cost values
        "max": 60, // Sum of all fees max_cost values
        "expected": 50 // Sum of all fees cost values
      }},
      "total_estimate": {{
        "min": 490, // Sum of all category min values
        "max": 650, // Sum of all category max values
        "expected": 570, // Sum of all category expected values
        "currency": "USD" // Currency code
      }}
    }}
  }},
  "fraud_analysis": {{
    "fraud_commentary": "The image shows consistent lighting and shadow patterns with damage consistent with impact. EXIF data shows original camera metadata. No signs of digital manipulation detected.",
    "fraud_risk_level": "very low" // MUST be: very low, low, medium, high, or very high
  }}
}}

IMPORTANT RULES FOR COST CALCULATIONS:
1. For each individual item (parts, labor, fees), provide a reasonable min_cost and max_cost around the expected cost.
2. Calculate category totals as the sum of individual items: parts_total.expected = sum(part.cost) for all parts.
3. Calculate min and max for each category the same way: parts_total.min = sum(part.min_cost).
4. The overall total_estimate values MUST follow the rule: total_estimate.min = sum of all category mins
5. Similarly: total_estimate.max = sum of all category maxes, and total_estimate.expected = sum of all category expected values.

For vehicle identification, provide certainty percentages for make and model:
1. "make_certainty" - confidence level (0-100) that the make is correctly identified
2. "model_certainty" - confidence level (0-100) that the model is correctly identified

Lower these certainty values if the image is unclear, partially visible, or if there are multiple similar models that could match.

FRAUD DETECTION RULES:
1. The fraud_risk_level MUST be one of: "very low", "low", "medium", "high", "very high".
2. Base your fraud risk assessment on image quality, consistency, damage patterns, and any anomalies.
3. Consider the available metadata and if there are any red flags like editing software signatures.
4. Provide specific reasons in the fraud_commentary field explaining your assessment.
"""
        
        # User prompt just includes the instruction to analyze the image
        user_prompt = "Analyze this car image for damage assessment, repair cost estimation, and fraud risk analysis."
        
        try:
            # Create message with image
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
            
            # Make the API call
            logger.info("Sending request to Groq API")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.05,
                max_tokens=4096
            )
            
            # Extract the response content
            result_text = response.choices[0].message.content
            logger.debug(f"Raw response from Groq: {result_text}")
            
            try:
                # Parse the JSON response
                result_json = json.loads(result_text)
                
                # Some models might return the array directly, others might wrap it in another object
                if isinstance(result_json, list):
                    # It's already an array of assessments
                    result = result_json
                elif isinstance(result_json, dict):
                    # It's a single assessment
                    if "vehicle_info" in result_json and "damage_data" in result_json:
                        result = result_json
                    else:
                        # It might be wrapped in another object, try to find the assessment
                        keys = list(result_json.keys())
                        if len(keys) == 1 and isinstance(result_json[keys[0]], (list, dict)):
                            result = result_json[keys[0]]
                        else:
                            logger.warning(f"Unexpected JSON structure: {result_json.keys()}")
                            result = result_json
                else:
                    logger.warning(f"Unexpected result type: {type(result_json)}")
                    result = result_json
                
                # Add fraud_analysis if not present
                result = self._ensure_fraud_analysis_present(result)
                
                # Validate cost calculations
                result = self.validate_total_costs(result)
                
                return result
            
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from model response: {str(e)}")
                logger.error(f"Response text: {result_text}")
                raise ValueError(f"Invalid JSON in model response: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error in analyze_car_damage: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def _format_metadata_for_prompt(self, metadata: Dict[str, Any]) -> str:
        """Format metadata into a string for inclusion in the prompt"""
        if not metadata:
            return "METADATA: No image metadata available."
        
        metadata_text = ["METADATA INFORMATION (IMPORTANT FOR FRAUD ASSESSMENT):"]
        
        # Add image properties
        if "image_properties" in metadata and metadata["image_properties"]:
            props = metadata["image_properties"]
            metadata_text.append(f"- Image format: {props.get('format', 'Unknown')}")
            metadata_text.append(f"- Image dimensions: {props.get('width', 'Unknown')}x{props.get('height', 'Unknown')}")
            metadata_text.append(f"- Image size: {props.get('size_bytes', 'Unknown')} bytes")
        
        # Add EXIF information
        if "has_exif" in metadata:
            if metadata["has_exif"]:
                metadata_text.append("- EXIF data: Present")
                exif = metadata.get("exif_data", {})
                if "DateTime" in exif:
                    metadata_text.append(f"- Date taken: {exif['DateTime']}")
                if "Make" in exif:
                    metadata_text.append(f"- Camera make: {exif['Make']}")
                if "Model" in exif:
                    metadata_text.append(f"- Camera model: {exif['Model']}")
                if "Software" in exif:
                    metadata_text.append(f"- Software used: {exif['Software']} <-- FRAUD RISK INDICATOR if editing software")
            else:
                metadata_text.append("- EXIF data: Not present (may indicate screenshot or edited image) <-- POTENTIAL FRAUD RISK INDICATOR")
        
        # Add GPS information
        if "has_gps" in metadata and metadata["has_gps"]:
            metadata_text.append("- GPS data: Present")
        
        # Add a fraud risk section based on metadata analysis
        fraud_indicators = []
        
        if "exif_data" in metadata and metadata.get("exif_data", {}).get("Software"):
            software = metadata["exif_data"]["Software"]
            if any(editor in str(software) for editor in ("Photoshop", "GIMP", "Lightroom", "Affinity")):
                fraud_indicators.append(f"Image was edited with {software}")
        
        if not metadata.get("has_exif", True) and metadata.get("image_properties", {}).get("format") == "PNG":
            fraud_indicators.append("Image lacks EXIF data and is PNG format (potential screenshot)")
        
        if fraud_indicators:
            metadata_text.append("\nPOTENTIAL FRAUD INDICATORS:")
            for indicator in fraud_indicators:
                metadata_text.append(f"- {indicator}")
            metadata_text.append("\nYOU MUST REFLECT THESE INDICATORS IN YOUR FRAUD ANALYSIS SECTION!")
        
        return "\n".join(metadata_text)
    
    def _ensure_fraud_analysis_present(self, result: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Ensure fraud_analysis is present in all assessment items"""
        default_fraud_analysis = {
            "fraud_commentary": "No specific fraud indicators identified in the assessment.",
            "fraud_risk_level": "low"
        }
        
        if isinstance(result, list):
            for item in result:
                if "fraud_analysis" not in item:
                    logger.warning("Adding missing fraud_analysis to assessment item")
                    item["fraud_analysis"] = default_fraud_analysis
        elif isinstance(result, dict) and "vehicle_info" in result and "damage_data" in result:
            if "fraud_analysis" not in result:
                logger.warning("Adding missing fraud_analysis to assessment")
                result["fraud_analysis"] = default_fraud_analysis
        
        return result
    
    def analyze_car_damage_sync(self, image_bytes: bytes, metadata: Optional[Dict[str, Any]] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Synchronous version of analyze_car_damage
        
        Args:
            image_bytes: The raw bytes of the uploaded image
            metadata: Optional metadata extracted from the image
            
        Returns:
            Union[Dict[str, Any], List[Dict[str, Any]]]: Single damage assessment or list of assessments if multiple cars detected
        """
        try:
            import asyncio
            
            # Get the event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # Create a new event loop if there isn't one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the async function and return the result
            result = loop.run_until_complete(self.analyze_car_damage(image_bytes, metadata))
            return result
            
        except Exception as e:
            logger.error(f"Error in analyze_car_damage_sync: {str(e)}")
            logger.error(traceback.format_exc())
            raise 