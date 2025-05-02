# src/routes/telegram_bot.py

import os
import json
import logging
import requests
from tempfile import NamedTemporaryFile
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from src.services import damage_assessment_service
from src.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Telegram Bot configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_CAR_ASSESSOR", "")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Welcome message for new users
WELCOME_MESSAGE = """
Welcome to the Car Damage Assessor! 🚗

I can help you assess vehicle damage by analyzing photos. Here's how:

1️⃣ Send a clear photo of the damaged vehicle
2️⃣ I'll analyze it and provide a detailed damage assessment
3️⃣ You'll receive cost estimates for repairs

To get started, just send a photo of the damaged vehicle.
"""

def send_telegram_message(chat_id, message, parse_mode="Markdown"):
    """Send a Telegram message"""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode
    }
    
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        logger.error(f"Failed to send Telegram message: {response.text}")
    
    return response.json()

def download_file_from_telegram(file_id):
    """Download a file from Telegram using the file_id"""
    # First, get the file path
    url = f"{TELEGRAM_API_URL}/getFile"
    response = requests.get(url, params={"file_id": file_id})
    
    if response.status_code != 200:
        logger.error(f"Failed to get file path: {response.text}")
        return None
    
    file_path = response.json().get("result", {}).get("file_path")
    if not file_path:
        logger.error("File path not found in response")
        return None
    
    # Then download the file
    download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    file_response = requests.get(download_url)
    
    if file_response.status_code != 200:
        logger.error(f"Failed to download file: {file_response.text}")
        return None
    
    # Create a temporary file
    with NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        temp_file.write(file_response.content)
        return temp_file.name

def format_damage_assessment(assessment):
    """Format the damage assessment results into a readable Telegram message"""
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
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle incoming Telegram webhook events"""
    try:
        update = await request.json()
        logger.debug(f"Received Telegram update: {json.dumps(update)}")
        
        # Check if this is a message update
        if "message" not in update:
            return JSONResponse(content={"status": "success", "message": "Not a message update"})
        
        message = update["message"]
        chat_id = message["chat"]["id"]
        
        # Handle text messages
        if "text" in message:
            text = message["text"]
            logger.info(f"Received text from {chat_id}: {text}")
            
            # If it's a /start command
            if text == "/start":
                background_tasks.add_task(send_telegram_message, chat_id, WELCOME_MESSAGE)
            else:
                # For any other text message, send instructions
                background_tasks.add_task(send_telegram_message, chat_id, WELCOME_MESSAGE)
        
        # Handle photo messages
        elif "photo" in message:
            logger.info(f"Received photo from {chat_id}")
            
            # Inform user we're processing
            background_tasks.add_task(
                send_telegram_message, 
                chat_id, 
                "📸 I've received your photo! Processing damage assessment... This will take a moment."
            )
            
            # Get the file_id of the largest photo (last in the array)
            photo = message["photo"][-1]
            file_id = photo["file_id"]
            
            # Download the photo
            image_path = download_file_from_telegram(file_id)
            if not image_path:
                background_tasks.add_task(
                    send_telegram_message, 
                    chat_id, 
                    "Sorry, I couldn't download this image. Please try again with a different photo."
                )
                return JSONResponse(content={"status": "error", "message": "Failed to download image"})
            
            try:
                # Process the image with the damage assessment service
                with open(image_path, "rb") as img_file:
                    result = damage_assessment_service.assess_damage_from_image(img_file)
                
                # Format and send the results
                formatted_result = format_damage_assessment(result)
                background_tasks.add_task(
                    send_telegram_message, 
                    chat_id, 
                    formatted_result
                )
                
            except Exception as e:
                logger.error(f"Error processing image: {str(e)}")
                background_tasks.add_task(
                    send_telegram_message, 
                    chat_id, 
                    "Sorry, I couldn't analyze this image. Please make sure it clearly shows the vehicle damage and try again."
                )
            
            finally:
                # Clean up the temporary file
                if image_path and os.path.exists(image_path):
                    os.unlink(image_path)
        
        # Handle other message types
        else:
            background_tasks.add_task(
                send_telegram_message, 
                chat_id, 
                "I can only process text messages or images. Please send a photo of the damaged vehicle for assessment."
            )
        
        return JSONResponse(content={"status": "success"})
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"}
        )

@router.get("/set-webhook")
async def set_webhook(request: Request):
    """Set the Telegram webhook to this server's URL"""
    base_url = str(request.base_url).rstrip('/')
    webhook_url = f"{base_url}/telegram/webhook"
    
    response = requests.post(
        f"{TELEGRAM_API_URL}/setWebhook",
        json={"url": webhook_url}
    )
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set webhook: {response.text}"
        )
    
    return {"status": "success", "message": f"Webhook set to {webhook_url}", "details": response.json()}

@router.get("/webhook-info")
async def webhook_info():
    """Get information about the currently set webhook"""
    response = requests.get(f"{TELEGRAM_API_URL}/getWebhookInfo")
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get webhook info: {response.text}"
        )
    
    return {"status": "success", "webhook_info": response.json()}