#!/bin/bash
set -e

ACR_NAME="insuuranceclaimspoc"
RESOURCE_GROUP="MCP_resource"
APP_NAME="insurance-claims-api"
IMAGE_TAG="v1.0.0"
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)

# Make sure these are set in your environment before running this script
if [ -z "$GROQ_API_KEY" ]; then
  echo "Error: GROQ_API_KEY environment variable is not set"
  exit 1
fi

if [ -z "$WHATSAPP_PHONE_NUMBER_ID" ]; then
  echo "Error: WHATSAPP_PHONE_NUMBER_ID environment variable is not set"
  exit 1
fi

if [ -z "$WHATSAPP_ACCESS_TOKEN" ]; then
  echo "Error: WHATSAPP_ACCESS_TOKEN environment variable is not set"
  exit 1
fi

if [ -z "$WHATSAPP_VERIFY_TOKEN" ]; then
  echo "Error: WHATSAPP_VERIFY_TOKEN environment variable is not set"
  exit 1
fi

echo "Deploying Container App with WhatsApp integration..."
az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment "mcp-server-env" \
  --image "${ACR_NAME}.azurecr.io/car-insurance-claims-ai-agent:${IMAGE_TAG}" \
  --registry-server "${ACR_NAME}.azurecr.io" \
  --registry-username $ACR_NAME \
  --registry-password $ACR_PASSWORD \
  --target-port 8000 \
  --ingress external \
  --env-vars \
    "REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt" \
    "SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt" \
    "GROQ_API_KEY=$GROQ_API_KEY" \
    "WHATSAPP_API_URL=https://graph.facebook.com/v17.0" \
    "WHATSAPP_PHONE_NUMBER_ID=$WHATSAPP_PHONE_NUMBER_ID" \
    "WHATSAPP_ACCESS_TOKEN=$WHATSAPP_ACCESS_TOKEN" \
    "WHATSAPP_VERIFY_TOKEN=$WHATSAPP_VERIFY_TOKEN"

echo "Container App deployed successfully!"
APP_URL=$(az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv)
echo "Your public endpoint: https://$APP_URL"
echo ""
echo "WhatsApp webhook URL: https://$APP_URL/whatsapp/webhook"
echo "Test your API with:"
echo "curl -X POST -F \"image=@test_images/luxury-car.jpg\" https://$APP_URL/assess-damage" 