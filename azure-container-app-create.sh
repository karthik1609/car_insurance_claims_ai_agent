#!/bin/bash
set -e

# Variables - customize these
RESOURCE_GROUP="insurance-claims-api"
LOCATION="centralindia"
ENVIRONMENT_NAME="fxagent-env-new"
APP_NAME="insurance-claims-api"
ACR_NAME="fxagentsdk"
IMAGE_TAG="v6.0.2"
IMAGE_NAME="car-insurance-claims-ai-agent"
LOCAL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"
FULLY_QUALIFIED_IMAGE_NAME="${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}"
IDENTITY_NAME="insurance-claims-identity"

echo "==== Building and deploying Car Insurance Claims AI Agent ===="

# Create resource group if it doesn't exist
echo "Checking if resource group exists..."
if ! az group show --name $RESOURCE_GROUP &>/dev/null; then
  echo "Creating resource group $RESOURCE_GROUP in $LOCATION..."
  az group create --name $RESOURCE_GROUP --location $LOCATION
else
  echo "Resource group $RESOURCE_GROUP already exists."
fi

# Create ACR if it doesn't exist
echo "Checking if ACR exists..."
if ! az acr show --name $ACR_NAME &>/dev/null; then
  echo "Creating ACR $ACR_NAME..."
  az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic
else
  echo "ACR $ACR_NAME already exists."
fi

# Login to ACR
echo "Logging into ACR..."
az acr login --name $ACR_NAME

# Build locally and push to ACR (alternative approach)
echo "Building image locally for AMD64 architecture (for Azure compatibility)..."
# Use platform flag to specify AMD64 architecture even on Mac Silicon
docker build --no-cache --platform linux/amd64 -t $LOCAL_IMAGE_NAME .

echo "Tagging image for ACR..."
docker tag $LOCAL_IMAGE_NAME $FULLY_QUALIFIED_IMAGE_NAME

echo "Pushing image to ACR..."
docker push $FULLY_QUALIFIED_IMAGE_NAME

echo "Verifying image tag in ACR..."
ACR_TAGS=$(az acr repository show-tags --name $ACR_NAME --repository $IMAGE_NAME --output tsv)
if ! echo "$ACR_TAGS" | grep -q "^${IMAGE_TAG}$"; then
  echo "ERROR: Image tag ${IMAGE_TAG} not found in ACR repository ${IMAGE_NAME}."
  echo "Available tags: $ACR_TAGS"
  exit 1
fi
echo "Image tag ${IMAGE_TAG} successfully verified in ACR."

echo "Forcefully updating Container App $APP_NAME to use new image $FULLY_QUALIFIED_IMAGE_NAME..."
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $FULLY_QUALIFIED_IMAGE_NAME

echo "Verifying Container App revision image..."
# Give some time for the update to start provisioning
sleep 15 

LATEST_REVISION_IMAGE=$(az containerapp revision list -g $RESOURCE_GROUP -n $APP_NAME --query "[?properties.active==true || properties.provisioningState=='Provisioning'].properties.template.containers[0].image" -o tsv | tail -n1)

if [ "$LATEST_REVISION_IMAGE" == "$FULLY_QUALIFIED_IMAGE_NAME" ]; then
  echo "Container App $APP_NAME is provisioning or running with the correct image: $LATEST_REVISION_IMAGE"
else
  echo "WARNING: Container App $APP_NAME latest active/provisioning revision image ($LATEST_REVISION_IMAGE) does not match expected ($FULLY_QUALIFIED_IMAGE_NAME)."
  echo "It might still be updating, or there could be an issue. Please check Azure portal."
  # Depending on strictness, you might want to exit 1 here
fi

# Enable ARM tokens for ACR authentication if not already enabled
echo "Ensuring ARM tokens are enabled for ACR authentication..."
if [ "$(az acr config authentication-as-arm show --registry "$ACR_NAME" --query status -o tsv)" != "enabled" ]; then
  az acr config authentication-as-arm update --registry "$ACR_NAME" --status enabled
fi

# Create user-assigned managed identity
echo "Creating user-assigned managed identity..."
if ! az identity show --name $IDENTITY_NAME --resource-group $RESOURCE_GROUP &>/dev/null; then
  az identity create --name $IDENTITY_NAME --resource-group $RESOURCE_GROUP
fi

# Get identity resource ID
IDENTITY_ID=$(az identity show --name $IDENTITY_NAME --resource-group $RESOURCE_GROUP --query id -o tsv)
PRINCIPAL_ID=$(az identity show --name $IDENTITY_NAME --resource-group $RESOURCE_GROUP --query principalId -o tsv)

# Assign acrpull role to the identity for the ACR
echo "Assigning acrpull role to the identity for the ACR..."

ACR_RESOURCE_GROUP="fxAgentSDK"
ACR_ID=$(az acr show --name $ACR_NAME --resource-group $ACR_RESOURCE_GROUP --query id -o tsv)
az role assignment create --assignee $PRINCIPAL_ID --scope $ACR_ID --role acrpull

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

# Create or update the Container App
echo "Creating/updating Container App $APP_NAME..."
FQDN=$(az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $ENVIRONMENT_NAME \
  --image $FULLY_QUALIFIED_IMAGE_NAME \
  --registry-server "${ACR_NAME}.azurecr.io" \
  --registry-identity "$IDENTITY_ID" \
  --user-assigned "$IDENTITY_ID" \
  --target-port 8000 \
  --ingress external \
  --env-vars "REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt" "SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt" "GROQ_API_KEY=$GROQ_API_KEY" "GROQ_MODEL=meta-llama/llama-4-maverick-17b-128e-instruct" \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 1 \
  --memory 2Gi \
  --query properties.configuration.ingress.fqdn -o tsv)

# Configure auto-scaling for the container app
echo "Configuring auto-scaling for the Container App..."
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --scale-rule-name http-rule \
  --scale-rule-http-concurrency 50 \
  --min-replicas 1 \
  --max-replicas 3

echo "==== Deployment Summary ===="
echo "Container App deployed successfully!"
echo "Your public endpoint: https://$FQDN"
echo ""
echo "Test your API with:"
echo "curl -X GET https://$FQDN/health"
echo "curl -X POST -F \"image=@test_images/luxury-car.jpg\" https://$FQDN/assess-damage"
