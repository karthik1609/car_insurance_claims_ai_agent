#!/bin/bash
set -e

ACR_NAME="insuuranceclaimspoc"
RESOURCE_GROUP="MCP_resource"
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)

# Replace placeholders with actual values
cp container-app-with-probes.yaml container-app-with-probes-temp.yaml
sed -i '' "s/PLACEHOLDER_FOR_PASSWORD/$ACR_PASSWORD/g" container-app-with-probes-temp.yaml
export GROQ_API_KEY

echo "Deploying Container App with health probes..."
az containerapp create --resource-group $RESOURCE_GROUP --file container-app-with-probes-temp.yaml --name insurance-claims-api

# Clean up the temporary file with credentials
rm container-app-with-probes-temp.yaml

echo "Container App deployed successfully!"
echo "Test your API with:"
echo "curl -X POST -F \"image=@test_images/luxury-car.jpg\" https://$(az containerapp show --name insurance-claims-api --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv)/assess-damage" 