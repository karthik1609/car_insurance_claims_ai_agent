#!/bin/bash
set -e

# Script to deploy Telegram bot integration for Car Damage Assessor
# Bot username: @CarDamageAssessorBot

# Set variables
RESOURCE_GROUP="MCP_resource"
APP_NAME="insurance-claims-api"
BOT_USERNAME="CarDamageAssessorBot"

# Get the token from environment variable
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN_CAR_ASSESSOR:-}
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
  echo "Error: TELEGRAM_BOT_TOKEN_CAR_ASSESSOR environment variable is not set"
  exit 1
fi

# Make sure Groq API key is set
GROQ_API_KEY=${GROQ_API_KEY:-}
if [ -z "$GROQ_API_KEY" ]; then
  echo "Error: GROQ_API_KEY environment variable is not set"
  exit 1
fi

echo "Updating Container App with Telegram integration for @$BOT_USERNAME..."

# Update the existing container app with the environment variables
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars \
    "TELEGRAM_BOT_TOKEN_CAR_ASSESSOR=$TELEGRAM_BOT_TOKEN" \
    "GROQ_API_KEY=$GROQ_API_KEY"

echo "Container App updated successfully!"

# Get the app URL
APP_URL=$(az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv)

echo "Your public endpoint: https://$APP_URL"
echo ""
echo "🤖 Bot Information:"
echo "- Name: Car damage assessor"
echo "- Username: @$BOT_USERNAME"
echo ""
echo "To configure the Telegram webhook, visit:"
echo "https://$APP_URL/telegram/set-webhook"
echo ""
echo "To check webhook status, visit:"
echo "https://$APP_URL/telegram/webhook-info"
echo ""
echo "To test your bot, open Telegram and search for @$BOT_USERNAME" 