"""
Tests for the API endpoints
"""
import io
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.main import app
from src.schemas.damage_assessment import DamageAssessmentResponse

client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert "version" in response.json()

@pytest.mark.asyncio
@patch("src.services.openai_service.OpenAIService.analyze_car_damage")
async def test_assess_damage_endpoint(mock_analyze):
    """Test the damage assessment endpoint with mocked OpenAI service"""
    # Mock response data
    mock_response = {
        "vehicle": {
            "make": "Toyota",
            "model": "Corolla",
            "year": "2020",
            "color": "Blue"
        },
        "damage_assessment": [
            {
                "part": "Front Bumper",
                "damage_type": "Scratch",
                "severity": "Moderate",
                "repair_action": "Repaint"
            }
        ],
        "cost_estimate": {
            "range": {
                "min": 500,
                "max": 700
            },
            "currency": "EUR"
        }
    }
    
    # Configure the mock to return our test data
    mock_analyze.return_value = DamageAssessmentResponse(**mock_response)
    
    # Create a test image (1x1 pixel black PNG)
    img_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    
    # Make the request
    response = client.post(
        "/api/v1/assess-damage",
        files={"image": ("test.png", io.BytesIO(img_data), "image/png")}
    )
    
    # Verify the response
    assert response.status_code == 200
    result = response.json()
    
    assert result["vehicle"]["make"] == "Toyota"
    assert result["vehicle"]["model"] == "Corolla"
    assert len(result["damage_assessment"]) == 1
    assert result["cost_estimate"]["range"]["min"] == 500
    assert result["cost_estimate"]["range"]["max"] == 700
    assert result["cost_estimate"]["currency"] == "EUR"
    
    # Verify the mock was called
    mock_analyze.assert_called_once() 