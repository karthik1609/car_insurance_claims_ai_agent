#!/bin/bash
set -e

# Telegram CLI script to interact with the Telegram Bot API
# Usage: ./telegram_cli.sh [command]

# Set up variables
TOKEN=${TELEGRAM_BOT_TOKEN_CAR_ASSESSOR:-}
if [ -z "$TOKEN" ]; then
  echo "Error: TELEGRAM_BOT_TOKEN_CAR_ASSESSOR environment variable is not set"
  exit 1
fi

# Base URL for Telegram API
API_URL="https://api.telegram.org/bot$TOKEN"

# Show usage information
show_usage() {
  echo "Telegram CLI for Car Damage Assessor Bot"
  echo ""
  echo "Usage: ./telegram_cli.sh [command]"
  echo ""
  echo "Available commands:"
  echo "  getme            - Get information about the bot"
  echo "  updates          - Get recent updates/messages (polling mode)"
  echo "  webhook-info     - Get webhook information"
  echo "  set-webhook      - Set webhook to your Container App"
  echo "  delete-webhook   - Delete the current webhook"
  echo "  send-message     - Send a test message to a chat ID"
  echo "  bot-commands     - Show commands the bot supports"
  echo "  set-commands     - Set bot commands in Telegram UI"
  echo ""
  echo "Environment variables:"
  echo "  TELEGRAM_BOT_TOKEN_CAR_ASSESSOR - Your Telegram bot token"
  echo "  CONTAINER_APP_URL               - Your Container App URL (for set-webhook)"
  echo "  CHAT_ID                         - Chat ID to send test messages to (for send-message)"
}

# Get bot information
get_me() {
  echo "Getting bot information..."
  curl -s "$API_URL/getMe" | jq '.'
}

# Get recent updates
get_updates() {
  echo "Getting recent messages/updates..."
  curl -s "$API_URL/getUpdates" | jq '.'
}

# Get webhook information
get_webhook_info() {
  echo "Getting webhook information..."
  curl -s "$API_URL/getWebhookInfo" | jq '.'
}

# Set webhook
set_webhook() {
  CONTAINER_APP_URL=${CONTAINER_APP_URL:-}
  if [ -z "$CONTAINER_APP_URL" ]; then
    echo "Error: CONTAINER_APP_URL environment variable is not set"
    exit 1
  fi
  
  WEBHOOK_URL="https://$CONTAINER_APP_URL/telegram/webhook"
  echo "Setting webhook to: $WEBHOOK_URL"
  
  curl -s -X POST \
    "$API_URL/setWebhook" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"$WEBHOOK_URL\"}" | jq '.'
}

# Delete webhook
delete_webhook() {
  echo "Deleting webhook..."
  curl -s -X POST "$API_URL/deleteWebhook" | jq '.'
}

# Send a test message
send_message() {
  CHAT_ID=${CHAT_ID:-}
  if [ -z "$CHAT_ID" ]; then
    echo "Error: CHAT_ID environment variable is not set"
    exit 1
  fi
  
  MESSAGE=${1:-"Hello from the Car Damage Assessor bot! This is a test message."}
  
  echo "Sending message to chat ID $CHAT_ID..."
  curl -s -X POST \
    "$API_URL/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{
      \"chat_id\": \"$CHAT_ID\",
      \"text\": \"$MESSAGE\",
      \"parse_mode\": \"Markdown\"
    }" | jq '.'
}

# Get bot commands
get_bot_commands() {
  echo "Getting bot commands..."
  curl -s "$API_URL/getMyCommands" | jq '.'
}

# Set bot commands
set_bot_commands() {
  echo "Setting bot commands..."
  curl -s -X POST \
    "$API_URL/setMyCommands" \
    -H "Content-Type: application/json" \
    -d '{
      "commands": [
        {
          "command": "start",
          "description": "Start the bot and get instructions"
        },
        {
          "command": "help",
          "description": "Get help on how to use the bot"
        }
      ]
    }' | jq '.'
}

# Process command
case $1 in
  getme)
    get_me
    ;;
  updates)
    get_updates
    ;;
  webhook-info)
    get_webhook_info
    ;;
  set-webhook)
    set_webhook
    ;;
  delete-webhook)
    delete_webhook
    ;;
  send-message)
    send_message "$2"
    ;;
  bot-commands)
    get_bot_commands
    ;;
  set-commands)
    set_bot_commands
    ;;
  *)
    show_usage
    ;;
esac 