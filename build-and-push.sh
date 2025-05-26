#!/bin/bash

# Exit on any error
set -e

# Default values
REGISTRY=""
IMAGE_NAME="car-insurance-claims-ai-agent"
TAG="v3.0.0"
BUILD_ONLY=false
PLATFORMS="linux/amd64,linux/arm64"

# Help function
function show_help {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Build and push a multi-platform Docker image for the Car Insurance Claims AI Agent"
    echo ""
    echo "Options:"
    echo "  -r, --registry     Container registry URL (e.g., myacr.azurecr.io)"
    echo "  -n, --name         Image name (default: car-insurance-claims-ai-agent)"
    echo "  -t, --tag          Image tag (default: v3.0.0)"
    echo "  -p, --platforms    Platforms to build for (default: linux/amd64,linux/arm64)"
    echo "  -b, --build-only   Build image only, don't push"
    echo "  -h, --help         Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 --registry myacr.azurecr.io --tag v1.0.0"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -r|--registry)
            REGISTRY="$2"
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
        -b|--build-only)
            BUILD_ONLY=true
            shift
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

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in your PATH"
    exit 1
fi

# Enable Docker BuildKit for multi-platform builds
export DOCKER_BUILDKIT=1

# Set up image name with registry if provided
if [ -n "$REGISTRY" ]; then
    FULL_IMAGE_NAME="$REGISTRY/$IMAGE_NAME:$TAG"
else
    FULL_IMAGE_NAME="$IMAGE_NAME:$TAG"
fi

echo "========================================"
echo "Building multi-platform Docker image"
echo "Image: $FULL_IMAGE_NAME"
echo "Platforms: $PLATFORMS"
echo "========================================"

# Check if Docker BuildX is available
if ! docker buildx version &> /dev/null; then
    echo "Creating Docker BuildX instance..."
    docker buildx create --name multiarch --use
fi

# Build and push image
if [ "$BUILD_ONLY" = true ]; then
    echo "Building image without pushing..."
    docker buildx build --platform "$PLATFORMS" \
        -t "$FULL_IMAGE_NAME" \
        --load \
        .
else
    # Check if registry is provided for push
    if [ -z "$REGISTRY" ]; then
        echo "Error: Registry must be specified when pushing an image"
        echo "Use --registry option or --build-only if you just want to build"
        exit 1
    fi
    
    echo "Building and pushing image..."
    docker buildx build --platform "$PLATFORMS" \
        -t "$FULL_IMAGE_NAME" \
        --push \
        .
fi

echo "========================================"
echo "Process completed successfully!"
if [ "$BUILD_ONLY" = true ]; then
    echo "Image built: $FULL_IMAGE_NAME"
else
    echo "Image built and pushed: $FULL_IMAGE_NAME"
fi
echo "========================================" 