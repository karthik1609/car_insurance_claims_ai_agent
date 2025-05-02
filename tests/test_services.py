"""
Tests for the OpenAI service
"""
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from src.services.openai_service import OpenAIService
from src.schemas.damage_assessment import DamageAssessmentResponse

@pytest.mark.asyncio
@patch("openai.AsyncOpenAI")
async def test_analyze_car_damage(mock_openai):
    """Test the analyze_car_damage method of OpenAIService"""
    # Sample OpenAI API response
    mock_response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "vehicle": {
                            "make": "BMW",
                            "model": "3 Series",
                            "year": "2019",
                            "color": "Black"
                        },
                        "damage_assessment": [
                            {
                                "part": "Rear Bumper",
                                "damage_type": "Dent",
                                "severity": "Moderate",
                                "repair_action": "Replace"
                            },
                            {
                                "part": "Taillight",
                                "damage_type": "Crack",
                                "severity": "Severe",
                                "repair_action": "Replace"
                            }
                        ],
                        "cost_estimate": {
                            "range": {
                                "min": 1200,
                                "max": 1800
                            },
                            "currency": "EUR"
                        }
                    })
                }
            }
        ]
    }
    
    # Set up the mock
    mock_instance = mock_openai.return_value
    mock_instance.chat.completions.create = AsyncMock()
    mock_instance.chat.completions.create.return_value = MagicMock(**mock_response)
    
    # Create test instance
    service = OpenAIService()
    
    # Test with sample image data
    test_image = b"sample image data"
    result = await service.analyze_car_damage(test_image)
    
    # Verify the result
    assert isinstance(result, DamageAssessmentResponse)
    assert result.vehicle.make == "BMW"
    assert result.vehicle.model == "3 Series"
    assert len(result.damage_assessment) == 2
    assert result.damage_assessment[0].part == "Rear Bumper"
    assert result.damage_assessment[1].part == "Taillight"
    assert result.cost_estimate.range.min == 1200
    assert result.cost_estimate.range.max == 1800
    
    # Verify the mock was called correctly
    mock_instance.chat.completions.create.assert_called_once()
    args, kwargs = mock_instance.chat.completions.create.call_args
    assert kwargs["model"] == service.model
    assert kwargs["response_format"] == {"type": "json_object"} 