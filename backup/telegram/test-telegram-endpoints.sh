#!/bin/bash
set -e

# Script to test Telegram endpoints in the existing container app

# Set variables
RESOURCE_GROUP="MCP_resource"
APP_NAME="insurance-claims-api"

# Get the app URL
APP_URL=$(az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv)
if [ -z "$APP_URL" ]; then
  echo "Error: Could not get the app URL"
  exit 1
fi

echo "Testing Telegram endpoints on $APP_URL..."
echo ""

# Test the health endpoint
echo "Testing health endpoint..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://$APP_URL/health")
if [ "$HEALTH_STATUS" == "200" ]; then
  echo "✅ Health endpoint: OK (HTTP 200)"
else
  echo "❌ Health endpoint: Failed (HTTP $HEALTH_STATUS)"
fi

# Test the Telegram webhook info endpoint
echo ""
echo "Testing Telegram webhook info endpoint..."
WEBHOOK_INFO=$(curl -s "https://$APP_URL/telegram/webhook-info")
WEBHOOK_STATUS=$(echo $WEBHOOK_INFO | grep -c "status\|success\|webhook_info" || echo "0")

if [ "$WEBHOOK_STATUS" -gt "0" ]; then
  echo "✅ Telegram webhook info endpoint: OK"
  echo "$WEBHOOK_INFO" | python3 -m json.tool 2>/dev/null || echo "$WEBHOOK_INFO"
else
  echo "❌ Telegram webhook info endpoint: Failed"
  echo "Response: $WEBHOOK_INFO"
fi

# List available environment variables in the container app
echo ""
echo "Checking environment variables in the container app..."
ENV_VARS=$(az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query "properties.template.containers[0].env[].name" -o tsv)

if echo "$ENV_VARS" | grep -q "TELEGRAM_BOT_TOKEN_CAR_ASSESSOR"; then
  echo "✅ TELEGRAM_BOT_TOKEN_CAR_ASSESSOR is configured"
else
  echo "❌ TELEGRAM_BOT_TOKEN_CAR_ASSESSOR is not configured"
fi

if echo "$ENV_VARS" | grep -q "GROQ_API_KEY"; then
  echo "✅ GROQ_API_KEY is configured"
else
  echo "❌ GROQ_API_KEY is not configured"
fi

echo ""
echo "To set up the Telegram webhook, visit:"
echo "https://$APP_URL/telegram/set-webhook"
echo ""
echo "After setting up the webhook, users can interact with your bot at @CarDamageAssessorBot on Telegram." 