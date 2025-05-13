import os
import json
import requests
import base64
from tempfile import NamedTemporaryFile
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from src.services import damage_assessment_service
from src.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# WhatsApp API configuration
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL", "https://graph.facebook.com/v17.0")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")

# Welcome message for text interactions
WELCOME_MESSAGE = """
Welcome to the Car Insurance Claims Assistant! 🚗

I can help you assess vehicle damage by analyzing photos. Here's how:

1️⃣ Send a clear photo of the damaged vehicle
2️⃣ I'll analyze it and provide a detailed damage assessment
3️⃣ You'll receive cost estimates for repairs

To get started, just send a photo of the damaged vehicle.
"""

def download_media(media_id):
    """Download media file from WhatsApp API using the media ID"""
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"
    }
    
    # First, get the media URL
    url = f"{WHATSAPP_API_URL}/{media_id}"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        logger.error(f"Failed to get media URL: {response.text}")
        return None
    
    media_url = response.json().get("url")
    
    # Then download the actual media
    media_response = requests.get(media_url, headers=headers)
    
    if media_response.status_code != 200:
        logger.error(f"Failed to download media: {media_response.text}")
        return None
    
    # Create a temporary file to store the image
    with NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        temp_file.write(media_response.content)
        return temp_file.name

def send_whatsapp_message(to, message):
    """Send a WhatsApp text message"""
    url = f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {
            "body": message
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        logger.error(f"Failed to send WhatsApp message: {response.text}")
    
    return response.json()

def format_damage_assessment(assessment):
    """Format the damage assessment results into a readable WhatsApp message"""
    try:
        vehicle_info = assessment[0]["vehicle_info"]
        damage_data = assessment[0]["damage_data"]
        
        # Format vehicle information
        vehicle_str = (
            f"🚗 *VEHICLE DETAILS*\n"
            f"Make: {vehicle_info.get('make', 'Unknown')} ({vehicle_info.get('make_certainty', 0):.1f}%)\n"
            f"Model: {vehicle_info.get('model', 'Unknown')} ({vehicle_info.get('model_certainty', 0):.1f}%)\n"
            f"Year: {vehicle_info.get('year', 'Unknown')}\n"
            f"Color: {vehicle_info.get('color', 'Unknown')}\n"
        )
        
        # Format damage information
        damaged_parts = damage_data.get("damaged_parts", [])
        damage_str = "🔧 *DAMAGE ASSESSMENT*\n"
        for i, part in enumerate(damaged_parts, 1):
            damage_str += (
                f"{i}. {part.get('part', 'Unknown part')}: "
                f"{part.get('severity', 'Unknown')} {part.get('damage_type', 'damage')}\n"
                f"   Repair action: {part.get('repair_action', 'Unknown')}\n"
            )
        
        # Format cost breakdown
        cost_breakdown = damage_data.get("cost_breakdown", {})
        total_estimate = cost_breakdown.get("total_estimate", {})
        cost_str = (
            f"💰 *COST ESTIMATE*\n"
            f"Parts: {cost_breakdown.get('parts_total', {}).get('expected', 0)}\n"
            f"Labor: {cost_breakdown.get('labor_total', {}).get('expected', 0)}\n"
            f"Fees: {cost_breakdown.get('fees_total', {}).get('expected', 0)}\n"
            f"Total: {total_estimate.get('expected', 0)} {total_estimate.get('currency', 'EUR')}\n"
            f"Range: {total_estimate.get('min', 0)}-{total_estimate.get('max', 0)} {total_estimate.get('currency', 'EUR')}"
        )
        
        return f"{vehicle_str}\n{damage_str}\n{cost_str}"
    except Exception as e:
        logger.error(f"Error formatting damage assessment: {str(e)}")
        return "Error formatting damage assessment. Please try again later."

@router.post("/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle incoming WhatsApp webhook events"""
    try:
        body = await request.json()
        logger.debug(f"Received webhook: {json.dumps(body)}")
        
        # Check if this is a verification request
        if body.get("object") == "whatsapp_business_account":
            # Process messages
            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    
                    # Check if there are messages
                    if "messages" not in value:
                        continue
                    
                    for message in value["messages"]:
                        sender = message.get("from")
                        message_type = message.get("type")
                        
                        if message_type == "text":
                            # Handle text message
                            text = message.get("text", {}).get("body", "")
                            logger.info(f"Received text from {sender}: {text}")
                            
                            # Send welcome/instructions message
                            background_tasks.add_task(
                                send_whatsapp_message, 
                                sender, 
                                WELCOME_MESSAGE
                            )
                        
                        elif message_type == "image":
                            # Handle image message
                            logger.info(f"Received image from {sender}")
                            
                            # Inform user we're processing
                            background_tasks.add_task(
                                send_whatsapp_message, 
                                sender, 
                                "📸 I've received your photo! Processing damage assessment... This will take a moment."
                            )
                            
                            # Get the media ID
                            media_id = message.get("image", {}).get("id")
                            if not media_id:
                                background_tasks.add_task(
                                    send_whatsapp_message, 
                                    sender, 
                                    "Sorry, I couldn't process this image. Please try again with a different photo."
                                )
                                continue
                            
                            # Download the media
                            image_path = download_media(media_id)
                            if not image_path:
                                background_tasks.add_task(
                                    send_whatsapp_message, 
                                    sender, 
                                    "Sorry, I couldn't download this image. Please try again with a different photo."
                                )
                                continue
                            
                            try:
                                # Process the image with the damage assessment service
                                with open(image_path, "rb") as img_file:
                                    result = damage_assessment_service.assess_damage_from_image(img_file)
                                
                                # Format and send the results
                                formatted_result = format_damage_assessment(result)
                                background_tasks.add_task(
                                    send_whatsapp_message, 
                                    sender, 
                                    formatted_result
                                )
                                
                            except Exception as e:
                                logger.error(f"Error processing image: {str(e)}")
                                background_tasks.add_task(
                                    send_whatsapp_message, 
                                    sender, 
                                    "Sorry, I couldn't analyze this image. Please make sure it clearly shows the vehicle damage and try again."
                                )
                            
                            finally:
                                # Clean up the temporary file
                                if image_path and os.path.exists(image_path):
                                    os.unlink(image_path)
                        
                        else:
                            # Handle other message types
                            background_tasks.add_task(
                                send_whatsapp_message, 
                                sender, 
                                "I can only process text messages or images. Please send a photo of the damaged vehicle for assessment."
                            )
            
            return JSONResponse(content={"status": "success"})
        
        # Return error for non-WhatsApp webhooks
        return JSONResponse(
            status_code=400,
            content={"error": "Not a valid WhatsApp webhook request"}
        )
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"}
        )

@router.get("/webhook")
async def verify_webhook(request: Request):
    """Handle webhook verification from WhatsApp"""
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "your_verify_token")
    
    # Get query parameters
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    # Check if verification token matches
    if mode == "subscribe" and token == verify_token:
        if challenge:
            return int(challenge)
        return "WEBHOOK_VERIFIED"
    
    # Return error for invalid token
    raise HTTPException(status_code=403, detail="Verification failed") 