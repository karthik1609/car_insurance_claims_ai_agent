# Car Insurance Claims AI Agent - Postman Collection

This repository contains a Postman collection and environment for interacting with the Car Insurance Claims AI Agent API.

## Getting Started

### Prerequisites
- [Postman](https://www.postman.com/downloads/) installed on your machine

### Importing the Collection and Environment

1. Open Postman
2. Click on "Import" in the top left corner
3. Select the `postman_collection.json` and `postman_environment.json` files
4. Click "Import"

## API Endpoints

### Root (`GET /`)
- Returns basic information about the API
- No parameters required

### Health Check (`GET /health`)
- Returns the health status of the API
- No parameters required

### Assess Damage - File Upload (`POST /api/v1/assess-damage`)
- Uploads an image of a damaged car to get make/model, damage assessment, and repair cost estimation
- **Body Parameters**:
  - `image`: File - The image of the damaged vehicle (required)
- **Query Parameters**:
  - `skip_fraud_check`: Boolean - Skip fraud detection entirely (default: false)
  - `process_anyway`: Boolean - Process the request even if potential fraud is detected (default: false)

### Assess Damage - Base64 (`POST /api/v1/assess-damage-base64`)
- Submit a base64-encoded image of a damaged car
- Ideal for integrations where file upload is not feasible (such as Pega workflows)
- **Body Parameters** (JSON):
  ```json
  {
    "image_base64": "base64EncodedStringHere...",
    "image_format": "jpg"  // Optional
  }
  ```
- **Query Parameters**:
  - `skip_fraud_check`: Boolean - Skip fraud detection entirely (default: false)
  - `process_anyway`: Boolean - Process the request even if potential fraud is detected (default: false)

## Response Format

Both damage assessment endpoints return a JSON response with the following structure:

```json
[
  {
    "vehicle_info": {
      "make": "string",
      "model": "string",
      "year": "string",
      "color": "string",
      "type": "string",
      "trim": "string",
      "make_certainty": 0,
      "model_certainty": 0
    },
    "damage_data": {
      "damaged_parts": [
        {
          "part": "string",
          "damage_type": "string",
          "severity": "string",
          "repair_action": "string"
        }
      ],
      "cost_breakdown": {
        "parts": [
          {
            "name": "string",
            "cost": 0,
            "min_cost": 0,
            "max_cost": 0
          }
        ],
        "labor": [
          {
            "service": "string",
            "hours": 0,
            "rate": 0,
            "cost": 0,
            "min_cost": 0,
            "max_cost": 0
          }
        ],
        "additional_fees": [
          {
            "description": "string",
            "cost": 0,
            "min_cost": 0,
            "max_cost": 0
          }
        ],
        "parts_total": {
          "min": 0,
          "max": 0,
          "expected": 0
        },
        "labor_total": {
          "min": 0,
          "max": 0,
          "expected": 0
        },
        "fees_total": {
          "min": 0,
          "max": 0,
          "expected": 0
        },
        "total_estimate": {
          "min": 0,
          "max": 0,
          "expected": 0,
          "currency": "EUR"
        }
      }
    }
  }
]
```

If fraud is detected and `process_anyway` is set to false, the response will have a 202 status code with the following structure:

```json
{
  "warning": "string",
  "message": "string",
  "assessment": null
}
```

## Environment Variables

The included environment file contains the following variables:

- `baseUrl`: The base URL of the API
- `skipFraudCheck`: Boolean flag to skip fraud detection
- `processAnyway`: Boolean flag to process requests despite fraud detection
- `imageBase64String`: String to store your base64-encoded image for the base64 endpoint

## Using the Base64 Endpoint in Pega

For Pega integration:

1. In your Pega workflow, capture the image and convert it to base64 encoding
2. Remove any data URL prefix (like `data:image/jpeg;base64,`) from the string
3. Send a POST request to the `/api/v1/assess-damage-base64` endpoint with the base64 string in the request body
4. Process the JSON response within your Pega workflow

## Notes

- For the file upload endpoint, make sure to select a valid image file in the request body
- For the base64 endpoint, ensure the base64 string is properly encoded and does not include the data URL prefix
- The API will return the same detailed cost estimates for both endpoints
- Fraud detection is enabled by default for both endpoints, but can be bypassed if needed for testing 