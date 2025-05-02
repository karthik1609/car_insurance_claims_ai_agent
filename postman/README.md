# Car Damage Assessment API - Postman Collection

This folder contains Postman collection and environment files to help you test and integrate with the Car Damage Assessment API.

## Files

- **Car_Damage_Assessment_API.postman_collection.json**: The main Postman collection with all API endpoints
- **Car_Damage_Assessment_API.postman_environment.json**: Environment variables for local development
- **Car_Damage_Assessment_API_Production.postman_environment.json**: Environment variables for production use

## Setup Instructions

1. Install [Postman](https://www.postman.com/downloads/)
2. Import the collection:
   - Click on "Import" in Postman
   - Select the `Car_Damage_Assessment_API.postman_collection.json` file

3. Import the environments:
   - Click on "Import" in Postman 
   - Select the environment files (`Car_Damage_Assessment_API.postman_environment.json` and `Car_Damage_Assessment_API_Production.postman_environment.json`)

4. Select the environment:
   - Choose "Car Damage Assessment API - Local" for local testing
   - Choose "Car Damage Assessment API - Production" for production API

## Environment Variables

The collection uses the following variables which can be customized in the environments:

| Variable | Description | Default (Local) | Default (Production) |
|----------|-------------|----------------|---------------------|
| `baseUrl` | Base URL for the API | http://localhost:8000 | https://api.example.com |
| `skipFraudCheck` | Flag to skip fraud detection | false | false |
| `processAnyway` | Flag to process even if fraud is detected | false | false |

## Endpoints

### Assess Damage

- **Method**: POST
- **Endpoint**: `/assess-damage`
- **Description**: Upload an image of a damaged car to get assessment and repair cost

#### Parameters

- `image` (file): The image file containing the damaged car
- `skip_fraud_check` (boolean): Optional parameter to skip fraud detection
- `process_anyway` (boolean): Optional parameter to process the image even if fraud is detected

#### Responses

- **200 OK**: Successful assessment with detailed damage report
- **202 Accepted**: Potential fraud detected (with or without assessment)
- **400 Bad Request**: Invalid image or request
- **500 Internal Server Error**: Server-side error

### Health Check

- **Method**: GET
- **Endpoint**: `/health`
- **Description**: Check if the API is up and running

#### Responses

- **200 OK**: API is running properly

## Examples

The collection includes example responses for various scenarios:

1. Successful assessment with detailed cost breakdown
2. Fraud detected without assessment
3. Fraud detected but processed anyway (with assessment)
4. Invalid image request

## Workflow

1. Select the appropriate environment
2. Open the "Assess Damage" request
3. Click on the "Body" tab
4. Click "Select File" to upload a car damage image
5. Send the request
6. View the detailed damage assessment and cost breakdown in the response

## Testing Fraud Detection

To test how fraud detection works:

1. Use the normal request first (with `skipFraudCheck` and `processAnyway` set to `false`)
2. If the image is flagged as potentially fraudulent, you'll get a 202 response
3. Set `processAnyway` to `true` to see the assessment despite the fraud warning

## Troubleshooting

- Ensure your server is running if using the local environment
- Check that your image is a valid JPEG or PNG file
- Verify that the API keys are set correctly if using authentication
- Make sure the environment variables are properly set 