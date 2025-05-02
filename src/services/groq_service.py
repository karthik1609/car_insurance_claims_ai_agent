"""
Groq service for car damage assessment using Llama 4 Maverick
"""
import base64
import logging
import json
import traceback
from typing import Dict, Any, List, Union
from groq import AsyncGroq

from src.core.config import settings
from src.schemas.damage_assessment_enhanced import EnhancedDamageAssessmentResponse, DamageAssessmentItem

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
    
    def validate_total_costs(self, assessment_data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Validates and recalculates total costs to ensure mathematical consistency
        
        Args:
            assessment_data: The assessment data from the model, either a dict or list of dicts
            
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
                
                # Add min/max costs to parts if not present (using fluctuation percentage)
                for part in cost_breakdown["parts"]:
                    if "min_cost" not in part:
                        part["min_cost"] = round(part["cost"] * 0.9, 2)
                    if "max_cost" not in part:
                        part["max_cost"] = round(part["cost"] * 1.1, 2)
                
                # Add min/max costs to labor if not present
                for labor in cost_breakdown["labor"]:
                    if "min_cost" not in labor:
                        labor["min_cost"] = round(labor["cost"] * 0.9, 2)
                    if "max_cost" not in labor:
                        labor["max_cost"] = round(labor["cost"] * 1.1, 2)
                
                # Add min/max costs to additional fees if not present
                for fee in cost_breakdown["additional_fees"]:
                    if "min_cost" not in fee:
                        fee["min_cost"] = round(fee["cost"] * 0.9, 2)
                    if "max_cost" not in fee:
                        fee["max_cost"] = round(fee["cost"] * 1.1, 2)
                
                # Calculate category totals
                parts_min_total = sum(part["min_cost"] for part in cost_breakdown["parts"])
                parts_max_total = sum(part["max_cost"] for part in cost_breakdown["parts"])
                parts_expected_total = sum(part["cost"] for part in cost_breakdown["parts"])
                
                labor_min_total = sum(labor["min_cost"] for labor in cost_breakdown["labor"])
                labor_max_total = sum(labor["max_cost"] for labor in cost_breakdown["labor"])
                labor_expected_total = sum(labor["cost"] for labor in cost_breakdown["labor"])
                
                fees_min_total = sum(fee["min_cost"] for fee in cost_breakdown["additional_fees"])
                fees_max_total = sum(fee["max_cost"] for fee in cost_breakdown["additional_fees"])
                fees_expected_total = sum(fee["cost"] for fee in cost_breakdown["additional_fees"])
                
                # Add category totals
                if "parts_total" not in cost_breakdown:
                    cost_breakdown["parts_total"] = {
                        "min": parts_min_total,
                        "max": parts_max_total,
                        "expected": parts_expected_total
                    }
                else:
                    cost_breakdown["parts_total"]["min"] = parts_min_total
                    cost_breakdown["parts_total"]["max"] = parts_max_total
                    cost_breakdown["parts_total"]["expected"] = parts_expected_total
                
                if "labor_total" not in cost_breakdown:
                    cost_breakdown["labor_total"] = {
                        "min": labor_min_total,
                        "max": labor_max_total,
                        "expected": labor_expected_total
                    }
                else:
                    cost_breakdown["labor_total"]["min"] = labor_min_total
                    cost_breakdown["labor_total"]["max"] = labor_max_total
                    cost_breakdown["labor_total"]["expected"] = labor_expected_total
                
                if "fees_total" not in cost_breakdown:
                    cost_breakdown["fees_total"] = {
                        "min": fees_min_total,
                        "max": fees_max_total,
                        "expected": fees_expected_total
                    }
                else:
                    cost_breakdown["fees_total"]["min"] = fees_min_total
                    cost_breakdown["fees_total"]["max"] = fees_max_total
                    cost_breakdown["fees_total"]["expected"] = fees_expected_total
                
                # Calculate overall totals (sum of categories)
                min_total = parts_min_total + labor_min_total + fees_min_total
                max_total = parts_max_total + labor_max_total + fees_max_total
                expected_total = parts_expected_total + labor_expected_total + fees_expected_total
                
                # Update the total estimate
                cost_breakdown["total_estimate"]["min"] = min_total
                cost_breakdown["total_estimate"]["max"] = max_total
                cost_breakdown["total_estimate"]["expected"] = expected_total
                
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
                    
                    # Add min/max costs to parts if not present (using fluctuation percentage)
                    for part in cost_breakdown["parts"]:
                        if "min_cost" not in part:
                            part["min_cost"] = round(part["cost"] * 0.9, 2)
                        if "max_cost" not in part:
                            part["max_cost"] = round(part["cost"] * 1.1, 2)
                    
                    # Add min/max costs to labor if not present
                    for labor in cost_breakdown["labor"]:
                        if "min_cost" not in labor:
                            labor["min_cost"] = round(labor["cost"] * 0.9, 2)
                        if "max_cost" not in labor:
                            labor["max_cost"] = round(labor["cost"] * 1.1, 2)
                    
                    # Add min/max costs to additional fees if not present
                    for fee in cost_breakdown["additional_fees"]:
                        if "min_cost" not in fee:
                            fee["min_cost"] = round(fee["cost"] * 0.9, 2)
                        if "max_cost" not in fee:
                            fee["max_cost"] = round(fee["cost"] * 1.1, 2)
                    
                    # Calculate category totals
                    parts_min_total = sum(part["min_cost"] for part in cost_breakdown["parts"])
                    parts_max_total = sum(part["max_cost"] for part in cost_breakdown["parts"])
                    parts_expected_total = sum(part["cost"] for part in cost_breakdown["parts"])
                    
                    labor_min_total = sum(labor["min_cost"] for labor in cost_breakdown["labor"])
                    labor_max_total = sum(labor["max_cost"] for labor in cost_breakdown["labor"])
                    labor_expected_total = sum(labor["cost"] for labor in cost_breakdown["labor"])
                    
                    fees_min_total = sum(fee["min_cost"] for fee in cost_breakdown["additional_fees"])
                    fees_max_total = sum(fee["max_cost"] for fee in cost_breakdown["additional_fees"])
                    fees_expected_total = sum(fee["cost"] for fee in cost_breakdown["additional_fees"])
                    
                    # Add category totals
                    if "parts_total" not in cost_breakdown:
                        cost_breakdown["parts_total"] = {
                            "min": parts_min_total,
                            "max": parts_max_total,
                            "expected": parts_expected_total
                        }
                    else:
                        cost_breakdown["parts_total"]["min"] = parts_min_total
                        cost_breakdown["parts_total"]["max"] = parts_max_total
                        cost_breakdown["parts_total"]["expected"] = parts_expected_total
                    
                    if "labor_total" not in cost_breakdown:
                        cost_breakdown["labor_total"] = {
                            "min": labor_min_total,
                            "max": labor_max_total,
                            "expected": labor_expected_total
                        }
                    else:
                        cost_breakdown["labor_total"]["min"] = labor_min_total
                        cost_breakdown["labor_total"]["max"] = labor_max_total
                        cost_breakdown["labor_total"]["expected"] = labor_expected_total
                    
                    if "fees_total" not in cost_breakdown:
                        cost_breakdown["fees_total"] = {
                            "min": fees_min_total,
                            "max": fees_max_total,
                            "expected": fees_expected_total
                        }
                    else:
                        cost_breakdown["fees_total"]["min"] = fees_min_total
                        cost_breakdown["fees_total"]["max"] = fees_max_total
                        cost_breakdown["fees_total"]["expected"] = fees_expected_total
                    
                    # Calculate overall totals (sum of categories)
                    min_total = parts_min_total + labor_min_total + fees_min_total
                    max_total = parts_max_total + labor_max_total + fees_max_total
                    expected_total = parts_expected_total + labor_expected_total + fees_expected_total
                    
                    # Update the total estimate
                    cost_breakdown["total_estimate"]["min"] = min_total
                    cost_breakdown["total_estimate"]["max"] = max_total
                    cost_breakdown["total_estimate"]["expected"] = expected_total
                    
                    # Set default certainty values if not provided
                    if "make_certainty" not in item["vehicle_info"]:
                        item["vehicle_info"]["make_certainty"] = 85.0
                    
                    if "model_certainty" not in item["vehicle_info"]:
                        item["vehicle_info"]["model_certainty"] = 80.0
                
                return assessment_data
            else:
                logger.warning(f"Unexpected assessment_data structure: {type(assessment_data)}")
                return assessment_data
            
        except Exception as e:
            logger.error(f"Error in validate_total_costs: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
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
        
        try:
            logger.info("Calling Groq API")
            # Call Groq API
            response = await self.client.chat.completions.create(
                model=self.model,
                # Allow flexible response format to handle both single object and list of objects
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": "Analyze this car image and provide a detailed damage assessment with cost breakdown. If multiple cars are visible, analyze each one separately:"},
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