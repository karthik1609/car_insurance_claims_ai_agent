# Deploying Car Insurance Claims AI Agent to Azure Container Apps

This guide provides instructions for deploying the Car Insurance Claims AI Agent to Azure Container Apps with proper SSL/TLS support for external API connections like Groq.

## Prerequisites

1. Azure CLI installed and configured
2. Docker installed and configured
3. An Azure Container Registry (ACR) instance
4. A valid Groq API key

## Building and Pushing the Docker Image

### Option 1: Using the provided script

```bash
# Login to Azure
az login

# Login to your ACR
az acr login --name YOUR_ACR_NAME

# Deploy to ACR using the script (builds and pushes a multi-platform image)
./deploy-to-acr.sh --acr-name YOUR_ACR_NAME --tag v1.0.0
```

### Option 2: Building and pushing manually

```bash
# Build the multi-platform image
./build-and-push.sh --registry YOUR_ACR_NAME.azurecr.io --tag v1.0.0 --platforms "linux/amd64,linux/arm64"
```

## Creating an Azure Container App

You have two options for deploying your Container App:

### Option 1: Using the provided deployment script

The easiest way to deploy is to use our provided script that creates a fully configured public Container App with Groq API connectivity:

```bash
# Set your Groq API key as an environment variable
export GROQ_API_KEY=your_groq_api_key

# Run the deployment script
./deploy-container-app.sh
```

The script will:
- Create a Container App with external public access
- Configure it to allow outbound internet access (needed for Groq API)
- Set up port 8000 as the target port for the API
- Configure proper SSL certificates for Groq connectivity
- Display the public endpoint URL when complete

### Option 2: Manual deployment with Azure CLI

If you need to customize the deployment, you can use the Azure CLI directly:

1. Create a resource group if you don't have one:
   ```bash
   az group create --name insurance-claims --location eastus
   ```

2. Create a Container App environment:
   ```bash
   az containerapp env create \
     --name insurance-claims-env \
     --resource-group insurance-claims \
     --location eastus
   ```

3. Create a Container App with public access and Groq connectivity:
   ```bash
   az containerapp create \
     --name insurance-claims-api \
     --resource-group insurance-claims \
     --environment insurance-claims-env \
     --image YOUR_ACR_NAME.azurecr.io/car-insurance-claims-ai-agent:v1.0.0 \
     --registry-server YOUR_ACR_NAME.azurecr.io \
     --registry-username $(az acr credential show --name YOUR_ACR_NAME --query username -o tsv) \
     --registry-password $(az acr credential show --name YOUR_ACR_NAME --query passwords[0].value -o tsv) \
     --target-port 8000 \
     --ingress external \
     --env-vars GROQ_API_KEY=your_groq_api_key REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
   ```

4. Add a health probe to the Container App:
   ```bash
   az containerapp update \
     --name insurance-claims-api \
     --resource-group insurance-claims \
     --probe-name "health-probe" \
     --probe-type "Liveness" \
     --probe-protocol "HTTP" \
     --probe-path "/health" \
     --probe-port 8000
   ```

## Testing Your Public API

Once deployed, you can test your API with:

```bash
# Get the public URL for your Container App
APP_URL=$(az containerapp show --name insurance-claims-api --resource-group insurance-claims --query properties.configuration.ingress.fqdn -o tsv)

# Test the API with a sample image
curl -X POST -F "image=@test_images/luxury-car.jpg" https://$APP_URL/assess-damage
```

## SSL Certificate Support for Groq API Connection

The Docker image has been configured with proper SSL certificate support to connect to the Groq API from within Azure Container Apps. The following changes have been made:

1. Added SSL certificates installation in the Dockerfile:
   ```dockerfile
   # Install SSL certificates
   RUN apt-get update && \
       apt-get install -y ca-certificates curl && \
       update-ca-certificates
   ```

2. Set environment variables for SSL certificate paths:
   ```dockerfile
   ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
       SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
   ```

These changes ensure that the application can make secure HTTPS connections to external APIs like Groq from within Azure Container Apps.

## Troubleshooting

If you encounter SSL/certificate issues despite these settings, you can:

1. Check the application logs in Azure Container Apps:
   ```bash
   az containerapp logs show --name insurance-claims-api --resource-group insurance-claims
   ```

2. Try updating the container with more explicit SSL configuration:
   ```bash
   az containerapp update \
     --name insurance-claims-api \
     --resource-group insurance-claims \
     --set-env-vars \
     REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
     SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
     PYTHONHTTPSVERIFY=1
   ```

## Health Checks

The application includes a health check endpoint at `/health` that Azure Container Apps can use to verify the application is running correctly.

Azure Container Apps will use the health check to determine if the application is healthy. The health check endpoint:
- Returns 200 when the application is running normally
- Returns non-200 status code when there are issues 