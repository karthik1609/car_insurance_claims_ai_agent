#!/usr/bin/env python3
"""
Telegram message monitor and auto-responder for the Car Damage Assessor bot
"""
import os
import sys
import time
import json
import requests
from datetime import datetime

# Telegram Bot configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_CAR_ASSESSOR")
if not TELEGRAM_BOT_TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN_CAR_ASSESSOR environment variable not set")
    sys.exit(1)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
WELCOME_MESSAGE = """
🚗 *Welcome to the Car Damage Assessor!* 

I can help you assess vehicle damage by analyzing photos. Here's how:

1️⃣ Send a clear photo of the damaged vehicle
2️⃣ I'll analyze it and provide a detailed damage assessment
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
            "📸 I've received your photo! Since we're in testing mode, I'll simulate processing your image."
        )
        
        # Simulate processing delay
        time.sleep(2)
        
        # Send a simulated response
        return send_message(
            chat_id,
            """
🚗 *VEHICLE DETAILS*
Make: Honda (88.5%)
Model: Civic (75.2%)
Year: 2018
Color: Blue

🔧 *DAMAGE ASSESSMENT*
1. Front bumper: Moderate denting
   Repair action: Replacement

2. Hood: Minor scratches
   Repair action: Refinishing

3. Left headlight: Cracked
   Repair action: Replacement

💰 *COST ESTIMATE*
Parts: €650
Labor: €420
Fees: €95
Total: €1,165 EUR
Range: €950-€1,380 EUR

*Note: This is a simulated response for testing purposes.*
            """
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
    
    print(f"🤖 Starting Telegram monitor for @CarDamageAssessorBot")
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