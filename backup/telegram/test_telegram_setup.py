#!/usr/bin/env python3
"""
Script to test Telegram bot functionality without needing to deploy a new container
"""
import os
import sys
import requests
import json

# Telegram Bot configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_CAR_ASSESSOR")
if not TELEGRAM_BOT_TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN_CAR_ASSESSOR environment variable not set")
    sys.exit(1)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Define your container app URL
CONTAINER_APP_URL = os.getenv("CONTAINER_APP_URL")
if not CONTAINER_APP_URL:
    print("Error: CONTAINER_APP_URL environment variable not set")
    sys.exit(1)

def get_webhook_info():
    """Get information about the currently set webhook"""
    url = f"{TELEGRAM_API_URL}/getWebhookInfo"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get webhook info: {response.text}")
        return None

def set_webhook():
    """Set the webhook to your container app URL"""
    webhook_url = f"https://{CONTAINER_APP_URL}/telegram/webhook"
    url = f"{TELEGRAM_API_URL}/setWebhook"
    payload = {"url": webhook_url}
    
    print(f"Setting webhook to: {webhook_url}")
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to set webhook: {response.text}")
        return None

def delete_webhook():
    """Delete the current webhook"""
    url = f"{TELEGRAM_API_URL}/deleteWebhook"
    response = requests.post(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to delete webhook: {response.text}")
        return None

def send_test_message():
    """Send a test message to the bot to verify it's working"""
    chat_id = input("Enter your Telegram chat ID (leave empty to skip): ")
    if not chat_id:
        print("Skipping test message...")
        return None
    
    message = "Hello from the Car Damage Assessor bot! This is a test message."
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to send message: {response.text}")
        return None

def main():
    print(f"Testing Telegram bot setup for {CONTAINER_APP_URL}...")
    
    # Check current webhook info
    print("\nCurrent webhook info:")
    webhook_info = get_webhook_info()
    print(json.dumps(webhook_info, indent=2))
    
    # Ask if user wants to set or delete webhook
    print("\nOptions:")
    print("1. Set webhook to your container app")
    print("2. Delete current webhook")
    print("3. Send test message")
    print("4. Exit")
    
    choice = input("Enter your choice (1-4): ")
    
    if choice == '1':
        result = set_webhook()
        print("\nWebhook set result:")
        print(json.dumps(result, indent=2))
        
        # Verify webhook was set
        print("\nVerifying webhook:")
        webhook_info = get_webhook_info()
        print(json.dumps(webhook_info, indent=2))
        
    elif choice == '2':
        result = delete_webhook()
        print("\nWebhook deletion result:")
        print(json.dumps(result, indent=2))
        
        # Verify webhook was deleted
        print("\nVerifying webhook deletion:")
        webhook_info = get_webhook_info()
        print(json.dumps(webhook_info, indent=2))
        
    elif choice == '3':
        result = send_test_message()
        if result:
            print("\nTest message sent successfully:")
            print(json.dumps(result, indent=2))
            
    elif choice == '4':
        print("Exiting...")
        
    else:
        print("Invalid choice. Exiting...")

if __name__ == "__main__":
    main() 