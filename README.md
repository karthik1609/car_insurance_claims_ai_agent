# Car Insurance Claims AI Agent

This service provides AI-powered car damage assessment using computer vision and large language models to analyze car images, identify damage, provide repair cost estimates, and detect potential insurance fraud attempts.

## Features

- Car make and model identification
- Detailed damage assessment
- Repair cost estimation
- Fraud detection for manipulated images
- REST API for easy integration
- CLI for quick testing and demos
- Docker support for deployment
- Azure Container Apps deployment support

## Requirements

- Python 3.11+
- Docker (for containerized deployment)
- Azure CLI (for Azure deployment)
- Groq API key for LLM access

## Setup

### Setting up the environment

```bash
# Clone the repository
git clone https://github.com/yourusername/car-insurance-claims-ai.git
cd car-insurance-claims-ai

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

## Usage

### API Server

Start the API server:

```bash
uvicorn run:app --reload --port 8000
```

The API will be available at http://localhost:8000.

### Command Line Interface

For quick tests and demos:

```bash
python cli.py path/to/car/image.jpg
```

## API Endpoints

- `GET /health`: Health check endpoint
- `POST /api/v1/assess-damage`: Upload an image for damage assessment

See the API documentation at http://localhost:8000/docs when the server is running.

## Docker Support

### Building the Docker image

```bash
docker build -t car-insurance-claims-api:latest .
```

### Running with Docker

```bash
docker run -p 8000:8000 -e GROQ_API_KEY=your_api_key car-insurance-claims-api:latest
```

### Multi-platform build and push

```bash
./build-and-push.sh
```

## Testing

Run the test suite:

```bash
pytest
```

## Azure Deployment

Deploy to Azure Container Apps:

```bash
export GROQ_API_KEY=your_groq_api_key
./deploy-container-app.sh
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 