#!/bin/bash
set -e

# Health check script for the Car Insurance Claims AI Agent
# This script is used by Docker and Azure Container Apps to verify the application is healthy

# The API port (default: 8000)
PORT="${PORT:-8000}"

# Check if the /health endpoint is returning a 200 status code
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${PORT}/health)

if [ "$STATUS" -eq 200 ]; then
    echo "Health check passed: API is running on port ${PORT}"
    exit 0
else
    echo "Health check failed: API is not responding properly on port ${PORT} (Status: ${STATUS})"
    exit 1
fi 