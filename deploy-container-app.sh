#!/bin/bash
set -e

# Replace these values with your actual values if needed
RESOURCE_GROUP="MCP_resource"
ENVIRONMENT_NAME="mcp-server-env"
APP_NAME="insurance-claims-api"
ACR_NAME="insuuranceclaimspoc"
IMAGE_TAG="v1.0.0"

# Set your Groq API key (or export it before running this script)
# export GROQ_API_KEY=your_key_here

echo "Creating Container App using existing environment: $ENVIRONMENT_NAME in resource group: $RESOURCE_GROUP"

# Create the Container App with external access and internet outbound access
az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $ENVIRONMENT_NAME \
  --image "${ACR_NAME}.azurecr.io/car-insurance-claims-ai-agent:${IMAGE_TAG}" \
  --registry-server "${ACR_NAME}.azurecr.io" \
  --registry-username $(az acr credential show --name $ACR_NAME --query username -o tsv) \
  --registry-password $(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv) \
  --target-port 8000 \
  --ingress external \
  --env-vars "REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt" "SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt" "GROQ_API_KEY=$GROQ_API_KEY" \
  --query properties.configuration.ingress.fqdn -o tsv

echo "Adding health probe to Container App..."
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --probe-name "health-probe" \
  --probe-type "Liveness" \
  --probe-protocol "HTTP" \
  --probe-path "/health" \
  --probe-port 8000 \
  --probe-interval-seconds 30 \
  --probe-timeout-seconds 10 \
  --probe-success-threshold 1 \
  --probe-failure-threshold 3

echo "Container App deployed successfully!"
echo "Test your API with:"
echo "curl -X POST -F \"image=@test_images/luxury-car.jpg\" https://\$(az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv)/assess-damage" 