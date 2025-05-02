#!/bin/bash

# Exit on any error
set -e

# Default values
ACR_NAME=""
IMAGE_NAME="car-insurance-claims-ai-agent"
TAG="latest"
PLATFORMS="linux/amd64,linux/arm64"

# Help function
function show_help {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Build and push a multi-platform Docker image to Azure Container Registry"
    echo ""
    echo "Options:"
    echo "  -r, --acr-name     Azure Container Registry name"
    echo "  -n, --name         Image name (default: car-insurance-claims-ai-agent)"
    echo "  -t, --tag          Image tag (default: latest)"
    echo "  -p, --platforms    Platforms to build for (default: linux/amd64,linux/arm64)"
    echo "  -h, --help         Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 --acr-name myacr --tag v1.0.0"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -r|--acr-name)
            ACR_NAME="$2"
            shift 2
            ;;
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -p|--platforms)
            PLATFORMS="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check if ACR name is provided
if [ -z "$ACR_NAME" ]; then
    echo "Error: Azure Container Registry name must be specified"
    echo "Use --acr-name option"
    show_help
    exit 1
fi

# Check if az CLI is installed
if ! command -v az &> /dev/null; then
    echo "Error: Azure CLI (az) is not installed or not in your PATH"
    echo "Install it from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in your PATH"
    exit 1
fi

# Set up image name with ACR
FULL_IMAGE_NAME="$ACR_NAME.azurecr.io/$IMAGE_NAME:$TAG"

echo "========================================"
echo "Building and deploying to Azure Container Registry"
echo "ACR: $ACR_NAME.azurecr.io"
echo "Image: $FULL_IMAGE_NAME"
echo "Platforms: $PLATFORMS"
echo "========================================"

# Login to Azure if not already logged in
echo "Checking Azure login status..."
if ! az account show &> /dev/null; then
    echo "Logging into Azure..."
    az login
fi

# Login to ACR
echo "Logging into Azure Container Registry: $ACR_NAME.azurecr.io"
az acr login --name "$ACR_NAME"

# Enable Docker BuildKit for multi-platform builds
export DOCKER_BUILDKIT=1

# Check if Docker BuildX is available
if ! docker buildx version &> /dev/null; then
    echo "Creating Docker BuildX instance..."
    docker buildx create --name multiarch --use
fi

# Build and push image
echo "Building and pushing multi-platform image to ACR..."
docker buildx build --platform "$PLATFORMS" \
    -t "$FULL_IMAGE_NAME" \
    --push \
    .

echo "========================================"
echo "Deployment completed successfully!"
echo "Image built and pushed: $FULL_IMAGE_NAME"
echo "========================================"

# Show deployment commands for Azure Container Instances (optional)
echo ""
echo "To deploy this image to Azure Container Instances, you can run:"
echo ""
echo "az container create \\"
echo "  --resource-group YOUR_RESOURCE_GROUP \\"
echo "  --name car-insurance-claims \\"
echo "  --image $FULL_IMAGE_NAME \\"
echo "  --registry-login-server $ACR_NAME.azurecr.io \\"
echo "  --registry-username \$(az acr credential show --name $ACR_NAME --query username -o tsv) \\"
echo "  --registry-password \$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv) \\"
echo "  --dns-name-label your-unique-dns-name \\"
echo "  --ports 8000 \\"
echo "  --environment-variables GROQ_API_KEY=your_groq_api_key" 