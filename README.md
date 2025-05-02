# Car Insurance Claims AI Agent

An AI-powered application that analyzes car damage images and provides:
- Vehicle make and model identification (with confidence levels)
- Detailed damage assessment for affected parts
- Comprehensive repair cost estimation in EUR

## Features

- CLI tool and API for car damage assessment
- Integration with Groq AI (Llama 4 Maverick model) for precise damage analysis
- Structured JSON output with detailed damage inventory and cost breakdown
- Both command-line interface and RESTful API with FastAPI

## Prerequisites

- Python 3.9+
- Groq API key
- Git

## Installation with Virtual Environment (Recommended)

### Option 1: Clone the repository (if you don't have the code yet)

```bash
git clone https://github.com/yourusername/car_insurance_claims_ai_agent.git
cd car_insurance_claims_ai_agent
```

### Option 2: If you already have the code and want to connect to a remote

If you already have the code locally but need to connect it to a remote repository:

```bash
# Navigate to your project directory
cd car_insurance_claims_ai_agent

# Initialize git if not already done
git init

# Add the remote repository
git remote add origin https://github.com/yourusername/car_insurance_claims_ai_agent.git

# If the remote has files that aren't in your local repository (like README or LICENSE)
# fetch and merge them with your local files
git fetch
git merge origin/main --allow-unrelated-histories

# Push your local changes to the remote
git push -u origin main
```

### Setting up the environment

1. Create a virtual environment
```bash
# On macOS/Linux
python3 -m venv .venv

# On Windows
py -m venv .venv
```

2. Activate the virtual environment
```bash
# On macOS/Linux
source .venv/bin/activate

# On Windows
.venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your Groq API key (or copy from `.env.example`)
```bash
# Groq API Key
GROQ_API_KEY=your_groq_api_key_here

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG_MODE=true

# Model Configuration
GROQ_MODEL=meta-llama/llama-4-maverick-17b-128e-instruct
```

## Usage

### Command Line Interface

Analyze a car damage image using the CLI:

```bash
# Basic usage
python cli.py path/to/car_image.jpg

# With verbose output
python cli.py path/to/car_image.jpg -v
```

Example output:
```
Car Damage Assessment Report
---------------------------
Vehicle: McLaren 720S (2017, Silver)
Make Certainty: 98.5%
Model Certainty: 92.1%

Damage Assessment:
1. Driver's Side Door - Moderate tear/rip 
   * Action: Repair and repaint

2. Driver's Side Mirror - Severe breakage
   * Action: Replace

Cost Breakdown:
- Parts: €1000
- Labor: €775
- Additional Fees: €125

Total Estimate: €1900 (Range: €1400 - €2090)
```

### RESTful API

Start the API server:
```bash
python run.py
```

The API will be available at `http://localhost:8000`. You can customize the host and port in the `.env` file.

#### Endpoint: POST /api/assess-damage

Submit an image for damage assessment:

```bash
curl -X POST -F "image=@path/to/car_image.jpg" http://localhost:8000/api/assess-damage
```

#### Sample Response

```json
{
  "vehicle_info": {
    "make": "McLaren",
    "model": "720S",
    "year": 2017,
    "color": "Silver",
    "type": "Sports Coupe",
    "trim": "Base",
    "make_certainty": 0.985,
    "model_certainty": 0.921
  },
  "damage_data": {
    "damaged_parts": [
      {
        "part_name": "Driver's Side Door",
        "damage_type": "Tear/Rip",
        "severity": "Moderate",
        "repair_action": "Repair and repaint"
      },
      {
        "part_name": "Driver's Side Mirror",
        "damage_type": "Breakage",
        "severity": "Severe",
        "repair_action": "Replace"
      }
    ],
    "cost_breakdown": {
      "parts_cost": 1000,
      "labor_cost": 775,
      "additional_fees": 125
    },
    "total_estimate": 1900,
    "estimate_range": {
      "min": 1400,
      "max": 2090
    },
    "currency": "EUR"
  }
}
```

## Development Workflow

### Pushing Changes to Remote Repository

After making changes to your code:

```bash
# Add your changes
git add .

# Commit your changes with a descriptive message
git commit -m "Description of the changes"

# Pull any changes from the remote repository
git pull origin main

# Push your changes to the remote repository
git push origin main
```

### Working with Branches

```bash
# Create a new branch for a feature
git checkout -b feature-name

# Make your changes and commit them
git add .
git commit -m "Implement feature-name"

# Push the branch to the remote repository
git push -u origin feature-name

# When ready to merge, switch to main and merge
git checkout main
git merge feature-name
git push origin main
```

## Troubleshooting

If you encounter issues:

1. Ensure your Groq API key is valid and properly set in the `.env` file
2. Check that you've activated the virtual environment before running commands
3. For verbose logging, use the `-v` flag with the CLI tool
4. Make sure the image file exists and is accessible

### Git-related Issues

If you encounter issues with git:

1. Check your remote URL: `git remote -v`
2. Ensure you have the latest changes: `git fetch origin`
3. If you have conflicts during merge: `git status` to view conflicting files, then resolve them and commit

## Testing

```bash
# Activate virtual environment first
pytest tests/
```

## Docker Support

Build and run using Docker:

```bash
docker-compose up -d
```

## License

MIT License 