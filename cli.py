#!/usr/bin/env python
"""
Command-line tool for car damage assessment
"""
import os
import sys
import json
import logging
import argparse
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from src.core.config import settings
from src.services.groq_service import GroqService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_api_keys():
    """Check if the required API keys are set"""
    if not settings.GROQ_API_KEY:
        logger.error("GROQ_API_KEY environment variable is not set.")
        logger.error("Please set it by either:")
        logger.error("  1. Creating a .env file with GROQ_API_KEY=your_key")
        logger.error("  2. Setting the environment variable directly")
        sys.exit(1)

async def assess_damage(image_path):
    """
    Assess car damage using Groq service
    
    Args:
        image_path: Path to the car damage image file
    """
    # Ensure the image file exists
    path = Path(image_path)
    if not path.exists():
        logger.error(f"Image file not found: {image_path}")
        sys.exit(1)
    
    # Read the image file
    with open(path, "rb") as f:
        image_bytes = f.read()
    
    logger.info("Using Groq service with Llama 4 Maverick model...")
    service = GroqService()
    
    logger.info(f"Analyzing image: {path.name}...")
    
    try:
        # Call the service
        result = await service.analyze_car_damage(image_bytes)
        
        # Print the result
        logger.info("\n📋 Car Damage Assessment Report:")
        logger.info("=" * 40)
        
        # Convert the result to a list if it's a dictionary (single item)
        items = [result] if isinstance(result, dict) else result
        
        for item in items:
            # Vehicle details
            vehicle = item['vehicle_info']
            logger.info(f"🚗 Vehicle: {vehicle['make']} {vehicle['model']} ({vehicle['year']}, {vehicle['color']})")
            logger.info(f"   Make certainty: {vehicle['make_certainty']:.1f}%")
            logger.info(f"   Model certainty: {vehicle['model_certainty']:.1f}%")
            if vehicle.get('type'):
                logger.info(f"   Type: {vehicle['type']}")
            if vehicle.get('trim'):
                logger.info(f"   Trim: {vehicle['trim']}")
            
            # Damage details
            logger.info("\n🔍 Damage Assessment:")
            for i, damage in enumerate(item['damage_data']['damaged_parts'], 1):
                logger.info(f"  {i}. {damage['part']}: {damage['damage_type']} - {damage['severity']}")
                logger.info(f"     Repair action: {damage['repair_action']}")
            
            # Cost breakdown
            cost_breakdown = item['damage_data']['cost_breakdown']
            logger.info("\n💰 Repair Cost Breakdown:")
            
            # Parts
            if cost_breakdown['parts']:
                logger.info("\n  Parts:")
                for part in cost_breakdown['parts']:
                    logger.info(f"    • {part['name']}: €{part['cost']:.2f}")
            
            # Labor
            if cost_breakdown['labor']:
                logger.info("\n  Labor:")
                for labor in cost_breakdown['labor']:
                    logger.info(f"    • {labor['service']}: {labor['hours']} hours @ €{labor['rate']}/hr = €{labor['cost']:.2f}")
            
            # Additional fees
            if cost_breakdown['additional_fees']:
                logger.info("\n  Additional Fees:")
                for fee in cost_breakdown['additional_fees']:
                    logger.info(f"    • {fee['description']}: €{fee['cost']:.2f}")
            
            # Total estimate
            total = cost_breakdown['total_estimate']
            logger.info(f"\n  Total Estimate:")
            logger.info(f"    • Expected: €{total['expected']:.2f}")
            logger.info(f"    • Range: €{total['min']:.2f} - €{total['max']:.2f}")
            logger.info(f"    • Currency: {total['currency']}")
        
        # Save to JSON if requested
        if args.output:
            output_path = args.output
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)
            logger.info(f"\nResults saved to: {output_path}")
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assess car damage from an image")
    parser.add_argument("image", help="Path to the car damage image file")
    parser.add_argument("-o", "--output", help="Save results to a JSON file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set debug level if verbose flag is provided
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Check if API keys are set
    check_api_keys()
    
    # Run the assessment
    asyncio.run(assess_damage(args.image)) 