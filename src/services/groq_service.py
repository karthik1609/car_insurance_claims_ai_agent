"""
Groq service for car damage assessment using Llama 4 Maverick
"""
import base64
import logging
import json
import traceback
from typing import Dict, Any, List
from groq import AsyncGroq

from src.core.config import settings
from src.schemas.damage_assessment_enhanced import EnhancedDamageAssessmentResponse

# Configure logging
logger = logging.getLogger(__name__)

class GroqService:
    """Service to interact with Groq API for car damage assessment using Llama 4 Maverick"""
    
    def __init__(self):
        """Initialize Groq client with API key from settings"""
        logger.info("Initializing Groq service with API key")
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = "meta-llama/llama-4-maverick-17b-128e-instruct"
        logger.info(f"Using model: {self.model}")
    
    def validate_total_costs(self, assessment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates and recalculates total costs to ensure mathematical consistency
        
        Args:
            assessment_data: The assessment data from the model
            
        Returns:
            The assessment data with corrected total costs
        """
        logger.debug(f"Validating total costs for assessment data: {assessment_data}")
        try:
            # Handle direct object response (json_object format)
            if isinstance(assessment_data, dict) and "vehicle_info" in assessment_data and "damage_data" in assessment_data:
                # Process the direct dictionary
                if "cost_breakdown" not in assessment_data["damage_data"]:
                    logger.warning(f"Missing cost_breakdown in assessment data")
                    return assessment_data
                    
                cost_breakdown = assessment_data["damage_data"]["cost_breakdown"]
                
                # Calculate total parts cost
                parts_total = sum(part["cost"] for part in cost_breakdown["parts"])
                
                # Calculate total labor cost
                labor_total = sum(labor["cost"] for labor in cost_breakdown["labor"])
                
                # Calculate total additional fees
                fees_total = sum(fee["cost"] for fee in cost_breakdown["additional_fees"])
                
                # Calculate actual total
                actual_total = parts_total + labor_total + fees_total
                logger.debug(f"Calculated totals - Parts: {parts_total}, Labor: {labor_total}, Fees: {fees_total}, Actual total: {actual_total}")
                
                # Update the total estimate
                # Keep min and max if they're reasonable, otherwise derive from actual total
                if cost_breakdown["total_estimate"]["min"] > actual_total:
                    cost_breakdown["total_estimate"]["min"] = actual_total * 0.9
                
                if cost_breakdown["total_estimate"]["max"] < actual_total:
                    cost_breakdown["total_estimate"]["max"] = actual_total * 1.1
                
                # Set expected to actual calculation
                cost_breakdown["total_estimate"]["expected"] = actual_total
                
                # Set default certainty values if not provided
                if "make_certainty" not in assessment_data["vehicle_info"]:
                    assessment_data["vehicle_info"]["make_certainty"] = 85.0
                
                if "model_certainty" not in assessment_data["vehicle_info"]:
                    assessment_data["vehicle_info"]["model_certainty"] = 80.0
                    
                return assessment_data
                
            # Handle list response (legacy format)
            elif isinstance(assessment_data, list):
                # Process each item in the list
                for item in assessment_data:
                    if "damage_data" not in item or "cost_breakdown" not in item["damage_data"]:
                        logger.warning(f"Missing expected keys in assessment data: {item}")
                        continue
                        
                    cost_breakdown = item["damage_data"]["cost_breakdown"]
                    
                    # Calculate total parts cost
                    parts_total = sum(part["cost"] for part in cost_breakdown["parts"])
                    
                    # Calculate total labor cost
                    labor_total = sum(labor["cost"] for labor in cost_breakdown["labor"])
                    
                    # Calculate total additional fees
                    fees_total = sum(fee["cost"] for fee in cost_breakdown["additional_fees"])
                    
                    # Calculate actual total
                    actual_total = parts_total + labor_total + fees_total
                    logger.debug(f"Calculated totals - Parts: {parts_total}, Labor: {labor_total}, Fees: {fees_total}, Actual total: {actual_total}")
                    
                    # Update the total estimate
                    # Keep min and max if they're reasonable, otherwise derive from actual total
                    if cost_breakdown["total_estimate"]["min"] > actual_total:
                        cost_breakdown["total_estimate"]["min"] = actual_total * 0.9
                    
                    if cost_breakdown["total_estimate"]["max"] < actual_total:
                        cost_breakdown["total_estimate"]["max"] = actual_total * 1.1
                    
                    # Set expected to actual calculation
                    cost_breakdown["total_estimate"]["expected"] = actual_total
                    
                    # Set default certainty values if not provided
                    if "make_certainty" not in item["vehicle_info"]:
                        item["vehicle_info"]["make_certainty"] = 85.0
                    
                    if "model_certainty" not in item["vehicle_info"]:
                        item["vehicle_info"]["model_certainty"] = 80.0
                
                # Return the first item if there was only one item
                if len(assessment_data) == 1:
                    return assessment_data[0]
                
                return assessment_data
            else:
                logger.warning(f"Unexpected assessment_data structure: {type(assessment_data)}")
                return assessment_data
            
        except Exception as e:
            logger.error(f"Error in validate_total_costs: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    async def analyze_car_damage(self, image_bytes: bytes) -> EnhancedDamageAssessmentResponse:
        """
        Analyze car image using Llama 4 Maverick model to detect damage and estimate repair costs
        
        Args:
            image_bytes: The raw bytes of the uploaded image
            
        Returns:
            EnhancedDamageAssessmentResponse: Structured damage assessment with detailed cost breakdown
        """
        # Encode image to base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        logger.info("Image encoded to base64")
        
        # Define the system prompt with enhanced JSON structure
        system_prompt = """
        You are an expert car damage assessor specialized in insurance claims.
        Analyze this car image in detail to identify:
        
        1. Vehicle details (make, model, year, color, type, trim if visible)
        2. Comprehensive damage assessment (location, type, severity, repair approach)
        3. Detailed repair cost breakdown with itemized services and parts
        
        Your response MUST be in JSON format as a list of objects, where each object has exactly two keys:
        1. "vehicle_info": Contains all vehicle identification details
        2. "damage_data": Contains complete damage assessment and cost breakdown
        
        Example of the expected JSON structure:
        
        [
          {
            "vehicle_info": {
              "make": "Toyota",
              "model": "Corolla",
              "year": "2019",
              "color": "Blue",
              "type": "Sedan",
              "trim": "LE",
              "make_certainty": 95.5,
              "model_certainty": 87.3
            },
            "damage_data": {
              "damaged_parts": [
                {
                  "part": "Front Bumper",
                  "damage_type": "Scratch",
                  "severity": "Moderate",
                  "repair_action": "Repaint"
                },
                {
                  "part": "Hood",
                  "damage_type": "Dent",
                  "severity": "Minor",
                  "repair_action": "Repair and Repaint"
                }
              ],
              "cost_breakdown": {
                "parts": [
                  {"name": "Paint supplies", "cost": 150},
                  {"name": "Primer", "cost": 50}
                ],
                "labor": [
                  {"service": "Bumper removal and reinstallation", "hours": 1.5, "rate": 85, "cost": 127.5},
                  {"service": "Dent repair", "hours": 2, "rate": 90, "cost": 180},
                  {"service": "Paint preparation", "hours": 1, "rate": 80, "cost": 80},
                  {"service": "Painting and finishing", "hours": 2.5, "rate": 85, "cost": 212.5}
                ],
                "additional_fees": [
                  {"description": "Disposal fees", "cost": 25},
                  {"description": "Shop supplies", "cost": 35}
                ],
                "total_estimate": {
                  "min": 800,
                  "max": 1200,
                  "expected": 860,
                  "currency": "EUR"
                }
              }
            }
          }
        ]
        
        Ensure your analysis is detailed and structured exactly as shown. The format must be consistent to work with Microsoft Copilot extensions. Use "Minor", "Moderate", or "Severe" for damage severity.
        
        Make sure that your "total_estimate" has three cost values:
        1. "min" - the minimum expected cost
        2. "max" - the maximum expected cost
        3. "expected" - the most likely cost
        
        The expected cost should be the sum of all parts, labor, and additional fees. The min and max should be reasonable ranges around this expected cost.
        
        For vehicle identification, provide certainty percentages for make and model:
        1. "make_certainty" - confidence level (0-100) that the make is correctly identified
        2. "model_certainty" - confidence level (0-100) that the model is correctly identified
        
        Lower these certainty values if the image is unclear, partially visible, or if there are multiple similar models that could match.
        """
        
        try:
            logger.info("Calling Groq API")
            # Call Groq API
            response = await self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": "Analyze this car image and provide a detailed damage assessment with cost breakdown:"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000,
                temperature=0.2,  # Lower temperature for more deterministic outputs
            )
            
            # Extract the content from the response
            content = response.choices[0].message.content
            logger.info("Received response from Groq API")
            logger.debug(f"Raw API response content: {content}")
            
            # Parse JSON content
            try:
                assessment_data = json.loads(content)
                logger.info("Successfully parsed JSON response")
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {str(e)}")
                logger.error(f"Raw content that failed to parse: {content}")
                raise Exception(f"Failed to parse Groq API response as JSON: {str(e)}")
            
            # Validate and ensure total costs are mathematically consistent
            assessment_data = self.validate_total_costs(assessment_data)
            logger.info("Validated total costs")
            
            # Return the validated JSON data
            return assessment_data
            
        except Exception as e:
            logger.error(f"Groq API error: {str(e)}")
            logger.error(traceback.format_exc())
            raise Exception(f"Error communicating with Groq: {str(e)}") 