# Car Insurance Claims AI Agent

An AI-powered service for analyzing car damage from images using computer vision and large language models.

## Features

- Image-based damage analysis using Groq API (Llama 4 Maverick model)
- Detailed damage assessment with repair cost estimates
- Simple command-line interface
- RESTful API with FastAPI
- Fraud detection logic
- Postman collection for easy API testing
- Azure Container Apps deployment support
- WhatsApp integration for damage assessment via messaging

## Requirements

- Python 3.8+
- Groq API key
- Docker (for containerized deployment)
- Azure CLI (for Azure deployment)

## Setup with Virtual Environment

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/car_insurance_claims_ai_agent.git
   cd car_insurance_claims_ai_agent
   ```

2. Create and activate a virtual environment:
   ```
   # On macOS/Linux
   python -m venv venv
   source venv/bin/activate

   # On Windows
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```
   cp .env.example .env
   ```
   Edit the `.env` file and add your Groq API key:
   ```
   GROQ_API_KEY=your_groq_api_key
   ```

## Usage

### Command Line Interface

To analyze a car image using the CLI:

```
python cli.py path/to/your/image.jpg
```

For verbose output:

```
python cli.py path/to/your/image.jpg -v
```

### API Server

To start the API server:

```
python run.py
```

The API will be available at http://localhost:8000.

### Using the API

#### With Postman

We provide a Postman collection to help you test the API:

1. Import the collection from the `postman` directory
2. Import the environment files for local or production use
3. Use the Assess Damage endpoint to upload images and get assessments

For detailed instructions, see the [Postman README](postman/README.md).

#### With cURL

```
curl -X POST -F "image=@path/to/your/image.jpg" http://localhost:8000/assess-damage
```

To skip fraud detection:

```
curl -X POST -F "image=@path/to/your/image.jpg" http://localhost:8000/assess-damage?skip_fraud_check=true
```

To process despite potential fraud:

```
curl -X POST -F "image=@path/to/your/image.jpg" http://localhost:8000/assess-damage?process_anyway=true
```

## API Endpoints

- `POST /assess-damage`: Upload an image to get damage assessment
- `GET /health`: Check if the service is operational
- `POST /whatsapp/webhook`: WhatsApp integration webhook
- `GET /whatsapp/webhook`: WhatsApp webhook verification endpoint

## WhatsApp Integration

The service includes integration with WhatsApp, allowing users to:
- Send a message to receive instructions
- Submit car damage photos directly through WhatsApp
- Receive detailed damage assessments and cost estimates

For setup instructions, see our [WhatsApp Integration Guide](WHATSAPP_INTEGRATION.md).

## Docker Support

### Building and Running with Docker Compose

Build and run with Docker Compose for local development:

```
docker-compose up -d
```

For production environments:
```
docker-compose -f docker-compose.prod.yml up -d
```

### Multi-Platform Docker Builds

We provide scripts to build and push multi-platform Docker images that work on different architectures (amd64, arm64).

#### Using the Shell Script (macOS/Linux)

```bash
# Build only for local testing
./build-and-push.sh --build-only

# Build and push to a registry
./build-and-push.sh --registry myregistry.azurecr.io --tag v1.0.0

# Build for specific platforms
./build-and-push.sh --platforms "linux/amd64,linux/arm64" --registry myregistry.azurecr.io
```

#### Using the PowerShell Script (Windows)

```powershell
# Build only for local testing
.\build-and-push.ps1 -BuildOnly

# Build and push to a registry
.\build-and-push.ps1 -Registry myregistry.azurecr.io -Tag v1.0.0

# Build for specific platforms
.\build-and-push.ps1 -Platforms "linux/amd64,linux/arm64" -Registry myregistry.azurecr.io
```

### Azure Container Registry (ACR) Deployment

We provide a specialized script for Azure deployments that handles all the steps for building and pushing multi-platform images to ACR:

```bash
# Deploy to ACR
./deploy-to-acr.sh --acr-name myregistry --tag v1.0.0

# Deploy to ACR with custom platforms
./deploy-to-acr.sh --acr-name myregistry --tag v1.0.0 --platforms "linux/amd64,linux/arm64,linux/arm/v7"
```

The script will:
1. Login to Azure and your ACR
2. Build a multi-platform Docker image
3. Push the image to your ACR
4. Provide commands for deploying to Azure Container Instances

## Azure Container Apps Deployment

For deploying to Azure Container Apps with proper SSL support for Groq API connectivity, we provide a streamlined deployment script:

```bash
# Set your API key
export GROQ_API_KEY=your_groq_api_key

# Deploy to Azure Container Apps
./deploy-container-app.sh
```

The script automatically:
- Creates a Container App with public access
- Configures it for secure external API connections
- Sets up proper SSL certificates for Groq API
- Displays the public endpoint URL

For detailed Azure deployment instructions, see our [Azure Deployment Guide](AZURE_DEPLOYMENT.md).

### Running in Production

For production environments, use the production Docker Compose file:

```bash
# Set environment variables
export REGISTRY=myregistry.azurecr.io
export TAG=v1.0.0
export REPLICAS=3
export API_PORT=8000

# Start the service
docker-compose -f docker-compose.prod.yml up -d
```

## Development

### Running Tests

```
python -m pytest tests/
```

## License

[MIT License](LICENSE) 