#!/bin/bash
set -e

# Variables - customize these
RESOURCE_GROUP="insurance-claims"
LOCATION="eastus"
ENVIRONMENT_NAME="insurance-claims-env"
APP_NAME="insurance-claims-api"
ACR_NAME="insuuranceclaimspoc"
IMAGE_TAG="v1.0.0"
IMAGE_NAME="${ACR_NAME}.azurecr.io/car-insurance-claims-ai-agent:${IMAGE_TAG}"

# Create resource group if it doesn't exist
echo "Checking if resource group exists..."
if ! az group show --name $RESOURCE_GROUP &>/dev/null; then
  echo "Creating resource group $RESOURCE_GROUP in $LOCATION..."
  az group create --name $RESOURCE_GROUP --location $LOCATION
else
  echo "Resource group $RESOURCE_GROUP already exists."
fi

# Check if Container App environment exists
echo "Checking if Container App environment exists..."
if ! az containerapp env show --name $ENVIRONMENT_NAME --resource-group $RESOURCE_GROUP &>/dev/null; then
  echo "Creating Container App environment $ENVIRONMENT_NAME..."
  # Create environment with outbound internet access enabled for Groq API
  az containerapp env create \
    --name $ENVIRONMENT_NAME \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION
else
  echo "Container App environment $ENVIRONMENT_NAME already exists."
fi

# Create the Container App with:
# 1. External ingress (public access from anywhere)
# 2. Internet outbound access (for Groq API)
# 3. Port 8000 exposed publicly
echo "Creating Container App $APP_NAME..."
az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $ENVIRONMENT_NAME \
  --image $IMAGE_NAME \
  --registry-server "${ACR_NAME}.azurecr.io" \
  --registry-username $(az acr credential show --name $ACR_NAME --query username -o tsv) \
  --registry-password $(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv) \
  --target-port 8000 \
  --ingress external \
  --env-vars "REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt" "SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt" "GROQ_API_KEY=$GROQ_API_KEY" \
  --min-replicas 1 \
  --max-replicas 3 \
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
echo "Your public endpoint: https://$(az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv)"
echo ""
echo "Test your API with:"
echo "curl -X POST -F \"image=@test_images/luxury-car.jpg\" https://$(az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv)/assess-damage" 