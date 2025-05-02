#!/bin/bash

# Exit on any error
set -e

echo "Building local Docker image for car-insurance-claims-ai-agent..."
echo "This will build an image for your local architecture only."

# Build with BuildKit enabled
export DOCKER_BUILDKIT=1
docker build -t car-insurance-claims-ai-agent:local .

echo ""
echo "Build completed successfully!"
echo "To run the container locally:"
echo "docker run -it --rm -p 8000:8000 -e GROQ_API_KEY=your_api_key car-insurance-claims-ai-agent:local" 