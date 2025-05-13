#!/usr/bin/env python3
"""
Connect to Azure endpoint to process Telegram images using real AI
"""
import os
import sys
import json
import time
import requests
import urllib3
from datetime import datetime

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_CAR_ASSESSOR")
if not TELEGRAM_BOT_TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN_CAR_ASSESSOR environment variable not set")
    sys.exit(1)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
AZURE_ENDPOINT = "https://insurance-claims-api.wittywave-e9da17ef.centralindia.azurecontainerapps.io"

# Welcome message for new users
WELCOME_MESSAGE = """
🚗 *Welcome to the Car Damage Assessor!* 

I can help you assess vehicle damage by analyzing photos. Here's how:

1️⃣ Send a clear photo of the damaged vehicle
2️⃣ I'll analyze it using AI to provide a detailed damage assessment
3️⃣ You'll receive cost estimates for repairs

To get started, just send a photo of the damaged vehicle.
"""

# Keep track of the last update ID we processed
last_update_id = 0

def get_updates(offset=None, timeout=30):
    """Get updates from Telegram"""
    params = {
        "timeout": timeout,
    }
    
    if offset:
        params["offset"] = offset
    
    response = requests.get(f"{TELEGRAM_API_URL}/getUpdates", params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting updates: {response.text}")
        return None
    
def send_message(chat_id, text, parse_mode="Markdown"):
    """Send a message to a Telegram chat"""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    
    response = requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error sending message: {response.text}")
        return None

def download_file_from_telegram(file_id):
    """Download a file from Telegram using the file_id"""
    # First, get the file path
    url = f"{TELEGRAM_API_URL}/getFile"
    response = requests.get(url, params={"file_id": file_id})
    
    if response.status_code != 200:
        print(f"Failed to get file path: {response.text}")
        return None
    
    file_path = response.json().get("result", {}).get("file_path")
    if not file_path:
        print("File path not found in response")
        return None
    
    # Then download the file
    download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    file_response = requests.get(download_url)
    
    if file_response.status_code != 200:
        print(f"Failed to download file: {file_response.text}")
        return None
    
    return file_response.content

def process_image_with_azure(image_bytes):
    """Send the image to the Azure Container App for processing"""
    print(f"Sending image to Azure endpoint: {AZURE_ENDPOINT}/api/v1/assess-damage")
    
    try:
        files = {
            'image': ('car_damage.jpg', image_bytes, 'image/jpeg')
        }
        
        # Disable SSL verification for testing
        response = requests.post(
            f"{AZURE_ENDPOINT}/api/v1/assess-damage", 
            files=files,
            verify=False  # Warning: Only for testing purposes
        )
        
        if response.status_code == 200:
            print("Successfully processed image with Azure AI")
            return response.json()
        else:
            print(f"Error from Azure API: Status {response.status_code}, {response.text}")
            return None
            
    except Exception as e:
        print(f"Error connecting to Azure: {str(e)}")
        return None

def format_damage_assessment(assessment):
    """Format the API response into a readable Telegram message"""
    try:
        # Extract the first assessment if it's a list
        if isinstance(assessment, list) and len(assessment) > 0:
            first_assessment = assessment[0]
        else:
            first_assessment = assessment
            
        vehicle_info = first_assessment.get("vehicle_info", {})
        damage_data = first_assessment.get("damage_data", {})
        
        # Format vehicle information
        vehicle_str = (
            f"🚗 *VEHICLE DETAILS*\n"
            f"Make: {vehicle_info.get('make', 'Unknown')} "
            f"({vehicle_info.get('make_certainty', 0):.1f}%)\n"
            f"Model: {vehicle_info.get('model', 'Unknown')} "
            f"({vehicle_info.get('model_certainty', 0):.1f}%)\n"
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
            f"Parts: €{cost_breakdown.get('parts_total', {}).get('expected', 0)}\n"
            f"Labor: €{cost_breakdown.get('labor_total', {}).get('expected', 0)}\n"
            f"Fees: €{cost_breakdown.get('fees_total', {}).get('expected', 0)}\n"
            f"Total: €{total_estimate.get('expected', 0)} {total_estimate.get('currency', 'EUR')}\n"
            f"Range: €{total_estimate.get('min', 0)}-€{total_estimate.get('max', 0)} {total_estimate.get('currency', 'EUR')}"
        )
        
        return f"{vehicle_str}\n{damage_str}\n{cost_str}"
    except Exception as e:
        print(f"Error formatting damage assessment: {str(e)}")
        return "Error formatting damage assessment. Please try again later."

def handle_message(message):
    """Handle incoming messages"""
    chat_id = message["chat"]["id"]
    
    # Handle text messages
    if "text" in message:
        text = message["text"]
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Message from {chat_id}: {text}")
        
        # Check for commands
        if text.startswith("/"):
            if text == "/start" or text == "/help":
                return send_message(chat_id, WELCOME_MESSAGE)
        else:
            # For any other text message, send instructions
            return send_message(chat_id, WELCOME_MESSAGE)
    
    # Handle photo messages
    elif "photo" in message:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Photo received from {chat_id}")
        
        # Inform the user we're processing their image
        send_message(
            chat_id, 
            "📸 I've received your photo! Processing with real AI analysis... This will take a moment."
        )
        
        # Get the file_id of the largest photo (last in the array)
        photo = message["photo"][-1]
        file_id = photo["file_id"]
        
        # Download the photo from Telegram
        image_bytes = download_file_from_telegram(file_id)
        if not image_bytes:
            return send_message(
                chat_id, 
                "Sorry, I couldn't download this image. Please try again with a different photo."
            )
        
        # Process with Azure Container App
        assessment_result = process_image_with_azure(image_bytes)
        if assessment_result:
            # Format and send the real results
            formatted_result = format_damage_assessment(assessment_result)
            return send_message(chat_id, formatted_result)
        else:
            # Send error message if processing failed
            return send_message(
                chat_id,
                "Sorry, I couldn't analyze this image with the AI service. Please make sure it clearly shows vehicle damage and try again."
            )
    
    # Handle other message types
    else:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Unsupported message type from {chat_id}")
        return send_message(
            chat_id, 
            "I can only process text messages or images. Please send a photo of the damaged vehicle for assessment."
        )

def main():
    """Run the message monitor"""
    global last_update_id
    
    print(f"🤖 Starting Telegram monitor with REAL AI for @CarDamageAssessorBot")
    print(f"Connected to: {AZURE_ENDPOINT}")
    print(f"Press Ctrl+C to stop")
    print("-" * 70)
    
    # Get initial updates to find the last update ID
    updates = get_updates()
    if updates and updates.get("result"):
        for update in updates.get("result", []):
            if update["update_id"] > last_update_id:
                last_update_id = update["update_id"]
    
    print(f"Starting from update ID: {last_update_id}")
    
    # Main loop
    try:
        while True:
            updates = get_updates(offset=last_update_id + 1)
            if updates and updates.get("result"):
                for update in updates.get("result", []):
                    # Process the update
                    if "message" in update:
                        handle_message(update["message"])
                    
                    # Update the last update ID
                    if update["update_id"] > last_update_id:
                        last_update_id = update["update_id"]
            
            # Wait before checking for updates again
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nMonitor stopped by user")

if __name__ == "__main__":
    main() 