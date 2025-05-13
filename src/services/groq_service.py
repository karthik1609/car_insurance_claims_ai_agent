"""
Groq service for car damage assessment using Llama 4 Maverick
"""
import base64
import logging
import json
import traceback
from typing import Dict, Any, List, Union
from groq import Groq

from src.core.config import settings
from src.schemas.damage_assessment_enhanced import EnhancedDamageAssessmentResponse, DamageAssessmentItem
from src.logger import get_logger

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
    
    async def analyze_car_damage(self, image_bytes: bytes) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Analyze car image using Llama 4 Maverick model to detect damage and estimate repair costs
        
        Args:
            image_bytes: The raw bytes of the uploaded image
            
        Returns:
            Union[Dict[str, Any], List[Dict[str, Any]]]: Single damage assessment or list of assessments if multiple cars detected
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
        
        IMPORTANT: If you see multiple cars in the image, you MUST return a list of objects, one for each car, following the format below.
        If there is only one car, you may return either a single object or a list with one object.
        
        Your response MUST be structured with the following keys for each car:
        1. "vehicle_info": Contains all vehicle identification details
        2. "damage_data": Contains complete damage assessment and cost breakdown
        
        For every cost value throughout your assessment (parts, labor, fees), you MUST provide three values:
        1. "cost": The expected/most likely cost
        2. "min_cost": The minimum estimated cost
        3. "max_cost": The maximum estimated cost
        
        Example of the expected JSON structure for multiple cars:
        
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
                  {"name": "Paint supplies", "cost": 150, "min_cost": 130, "max_cost": 170},
                  {"name": "Primer", "cost": 50, "min_cost": 45, "max_cost": 55}
                ],
                "labor": [
                  {"service": "Bumper removal and reinstallation", "hours": 1.5, "rate": 85, "cost": 127.5, "min_cost": 110, "max_cost": 145},
                  {"service": "Dent repair", "hours": 2, "rate": 90, "cost": 180, "min_cost": 160, "max_cost": 200},
                  {"service": "Paint preparation", "hours": 1, "rate": 80, "cost": 80, "min_cost": 70, "max_cost": 90},
                  {"service": "Painting and finishing", "hours": 2.5, "rate": 85, "cost": 212.5, "min_cost": 190, "max_cost": 235}
                ],
                "additional_fees": [
                  {"description": "Disposal fees", "cost": 25, "min_cost": 20, "max_cost": 30},
                  {"description": "Shop supplies", "cost": 35, "min_cost": 30, "max_cost": 40}
                ],
                "parts_total": {
                  "min": 175,
                  "max": 225,
                  "expected": 200
                },
                "labor_total": {
                  "min": 530,
                  "max": 670,
                  "expected": 600
                },
                "fees_total": {
                  "min": 50,
                  "max": 70,
                  "expected": 60
                },
                "total_estimate": {
                  "min": 755,
                  "max": 965,
                  "expected": 860,
                  "currency": "EUR"
                }
              }
            }
          },
          {
            "vehicle_info": {
              "make": "Honda",
              "model": "Civic",
              "year": "2020",
              "color": "Red",
              "type": "Sedan",
              "trim": "Sport",
              "make_certainty": 92.0,
              "model_certainty": 85.0
            },
            "damage_data": {
              // Similar structure as above
            }
          }
        ]
        
        Example of the expected JSON structure for a single car:
        
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
            // Same structure as in the list example
          }
        }
        
        Ensure your analysis is detailed and structured exactly as shown. The format must be consistent to work with the insurance system. Use "Minor", "Moderate", or "Severe" for damage severity.
        
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
        """
        
        # User prompt just includes the instruction to analyze the image
        user_prompt = "Analyze this car image for damage assessment and repair cost estimation."
        
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
                temperature=0.2,
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
                    if "assessments" in result_json:
                        # It's wrapped in an object with an "assessments" key
                        result = result_json["assessments"]
                    elif "vehicle_info" in result_json and "damage_data" in result_json:
                        # It's a single assessment
                        result = result_json
                    else:
                        # It's some other structure, but we'll try to use it anyway
                        logger.warning(f"Unexpected JSON structure: {list(result_json.keys())}")
                        result = result_json
                else:
                    logger.warning(f"Unexpected result type: {type(result_json)}")
                    raise ValueError(f"Unexpected response format: {type(result_json)}")
                
                # Validate and correct cost calculations
                validated_result = self.validate_total_costs(result)
                
                logger.info("Successfully analyzed car damage")
                return validated_result
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Groq response: {str(e)}")
                raise ValueError(f"Failed to parse AI response: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error analyzing car damage: {str(e)}", exc_info=True)
            raise ValueError(f"Error analyzing image with AI: {str(e)}")
    
    def analyze_car_damage_sync(self, image_bytes: bytes) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Synchronous version of analyze_car_damage for use in non-async contexts (like WhatsApp webhook)
        
        Args:
            image_bytes: The raw bytes of the uploaded image
            
        Returns:
            Union[Dict[str, Any], List[Dict[str, Any]]]: Single damage assessment or list of assessments if multiple cars detected
        """
        import asyncio
        
        # Create a new event loop to run the async function
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.analyze_car_damage(image_bytes))
            return result
        finally:
            loop.close() 