#!/usr/bin/env python
"""
Test script to simulate WhatsApp webhook messages
"""
import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Default test settings
API_URL = os.getenv("API_URL", "http://localhost:8000")
TEST_IMAGE = os.getenv("TEST_IMAGE", "test_images/luxury-car.jpg")
TEST_PHONE = os.getenv("TEST_PHONE", "123456789")

def simulate_text_message():
    """Simulate a text message from WhatsApp"""
    webhook_url = f"{API_URL}/whatsapp/webhook"
    
    # Prepare webhook payload for a text message
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "1234567890",
                                "phone_number_id": "1234567890"
                            },
                            "contacts": [
                                {
                                    "profile": {
                                        "name": "Test User"
                                    },
                                    "wa_id": TEST_PHONE
                                }
                            ],
                            "messages": [
                                {
                                    "from": TEST_PHONE,
                                    "id": "wamid.123456789",
                                    "timestamp": "1600000000",
                                    "text": {
                                        "body": "Hello, I need to assess car damage"
                                    },
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    
    print(f"Sending simulated text message to {webhook_url}")
    response = requests.post(
        webhook_url,
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")

def simulate_image_message():
    """Simulate an image message from WhatsApp"""
    # This is a simplified simulation that bypasses the actual WhatsApp API
    # In a real scenario, WhatsApp would provide a media ID and your webhook would download it
    
    # First, upload the image to our API directly to get an assessment
    print(f"Uploading image {TEST_IMAGE} to get assessment data")
    with open(TEST_IMAGE, "rb") as image_file:
        files = {"image": (Path(TEST_IMAGE).name, image_file, "image/jpeg")}
        response = requests.post(f"{API_URL}/assess-damage", files=files)
    
    if response.status_code != 200:
        print(f"Error getting assessment data: {response.status_code}")
        print(response.text)
        return
    
    assessment_data = response.json()
    print(f"Got assessment data")
    
    # Now, simulate the webhook with the image message
    webhook_url = f"{API_URL}/whatsapp/webhook"
    
    # Prepare webhook payload for an image message
    # Note: In reality, WhatsApp would send an image ID, not the actual image data
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "1234567890",
                                "phone_number_id": "1234567890"
                            },
                            "contacts": [
                                {
                                    "profile": {
                                        "name": "Test User"
                                    },
                                    "wa_id": TEST_PHONE
                                }
                            ],
                            "messages": [
                                {
                                    "from": TEST_PHONE,
                                    "id": "wamid.123456789",
                                    "timestamp": "1600000000",
                                    "image": {
                                        "id": "image_id_123456789",
                                        "mime_type": "image/jpeg",
                                        "sha256": "hash_123456789",
                                        "caption": "Car damage photo"
                                    },
                                    "type": "image"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    
    print(f"Sending simulated image message webhook to {webhook_url}")
    response = requests.post(
        webhook_url,
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    
    print("\nThis is a simulation only! The webhook response just acknowledges receipt of the message.")
    print("In a real scenario, WhatsApp would receive a message with car damage assessment.")
    print("\nSimulated message content that would be sent to the user:")
    
    # Create a formatted message similar to what our handler would send
    vehicle_info = assessment_data[0]["vehicle_info"]
    damage_data = assessment_data[0]["damage_data"]
    
    message = f"""
🚗 *VEHICLE DETAILS*
Make: {vehicle_info.get('make', 'Unknown')} ({vehicle_info.get('make_certainty', 0):.1f}%)
Model: {vehicle_info.get('model', 'Unknown')} ({vehicle_info.get('model_certainty', 0):.1f}%)
Year: {vehicle_info.get('year', 'Unknown')}
Color: {vehicle_info.get('color', 'Unknown')}

🔧 *DAMAGE ASSESSMENT*
"""
    
    for i, part in enumerate(damage_data.get("damaged_parts", []), 1):
        message += f"{i}. {part.get('part', 'Unknown part')}: {part.get('severity', 'Unknown')} {part.get('damage_type', 'damage')}\n"
        message += f"   Repair action: {part.get('repair_action', 'Unknown')}\n"
    
    cost_breakdown = damage_data.get("cost_breakdown", {})
    total_estimate = cost_breakdown.get("total_estimate", {})
    
    message += f"""
💰 *COST ESTIMATE*
Parts: {cost_breakdown.get('parts_total', {}).get('expected', 0)}
Labor: {cost_breakdown.get('labor_total', {}).get('expected', 0)}
Fees: {cost_breakdown.get('fees_total', {}).get('expected', 0)}
Total: {total_estimate.get('expected', 0)} {total_estimate.get('currency', 'EUR')}
Range: {total_estimate.get('min', 0)}-{total_estimate.get('max', 0)} {total_estimate.get('currency', 'EUR')}
"""
    
    print(message)

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python test-whatsapp.py [text|image]")
        sys.exit(1)
    
    message_type = sys.argv[1].lower()
    
    if message_type == "text":
        simulate_text_message()
    elif message_type == "image":
        simulate_image_message()
    else:
        print(f"Unknown message type: {message_type}")
        print("Usage: python test-whatsapp.py [text|image]")
        sys.exit(1)

if __name__ == "__main__":
    main() 