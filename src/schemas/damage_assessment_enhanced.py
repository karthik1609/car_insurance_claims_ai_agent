"""
Enhanced data models for damage assessment response with detailed cost breakdown
"""
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field

class VehicleInfo(BaseModel):
    """Enhanced vehicle information"""
    make: str = Field(..., description="Manufacturer of the vehicle")
    model: str = Field(..., description="Model of the vehicle")
    year: str = Field(..., description="Year of manufacture")
    color: str = Field(..., description="Color of the vehicle")
    type: Optional[str] = Field(None, description="Type of vehicle (e.g., Sedan, SUV)")
    trim: Optional[str] = Field(None, description="Trim level of the vehicle")
    make_certainty: float = Field(..., description="Certainty percentage for make identification (0-100)")
    model_certainty: float = Field(..., description="Certainty percentage for model identification (0-100)")

class DamagedPart(BaseModel):
    """Details about damage to a specific car part"""
    part: str = Field(..., description="The damaged part of the vehicle")
    damage_type: str = Field(..., description="Type of damage (e.g., Scratch, Dent, Crack)")
    severity: str = Field(..., description="Severity of damage (Minor, Moderate, Severe)")
    repair_action: str = Field(..., description="Recommended repair action")

class CostEstimate(BaseModel):
    """Cost estimate with min, max, and expected values"""
    min: float = Field(..., description="Minimum estimated cost")
    max: float = Field(..., description="Maximum estimated cost")
    expected: float = Field(..., description="Expected (most likely) cost")

class PartItem(BaseModel):
    """Part needed for repair"""
    name: str = Field(..., description="Name of the part")
    cost: float = Field(..., description="Expected cost of the part")
    min_cost: float = Field(..., description="Minimum cost estimate for the part")
    max_cost: float = Field(..., description="Maximum cost estimate for the part")

class LaborItem(BaseModel):
    """Labor service for repair"""
    service: str = Field(..., description="Description of the service")
    hours: float = Field(..., description="Number of hours required")
    rate: float = Field(..., description="Hourly rate")
    cost: float = Field(..., description="Expected total cost for this service")
    min_cost: float = Field(..., description="Minimum cost estimate for this service")
    max_cost: float = Field(..., description="Maximum cost estimate for this service")

class AdditionalFee(BaseModel):
    """Additional fees for repair"""
    description: str = Field(..., description="Description of the fee")
    cost: float = Field(..., description="Expected cost of the fee")
    min_cost: float = Field(..., description="Minimum cost estimate for the fee")
    max_cost: float = Field(..., description="Maximum cost estimate for the fee")

class CategoryTotal(BaseModel):
    """Total for a category (parts, labor, or fees)"""
    min: float = Field(..., description="Minimum total cost for this category")
    max: float = Field(..., description="Maximum total cost for this category")
    expected: float = Field(..., description="Expected total cost for this category")

class TotalEstimate(BaseModel):
    """Total cost estimate range"""
    min: float = Field(..., description="Minimum estimated total cost")
    max: float = Field(..., description="Maximum estimated total cost")
    expected: float = Field(..., description="Expected (most likely) total cost")
    currency: str = Field(default="EUR", description="Currency of the cost estimate")

class CostBreakdown(BaseModel):
    """Detailed breakdown of repair costs"""
    parts: List[PartItem] = Field([], description="List of parts needed for repair")
    labor: List[LaborItem] = Field([], description="List of labor services required")
    additional_fees: List[AdditionalFee] = Field([], description="List of additional fees")
    parts_total: CategoryTotal = Field(..., description="Total for all parts")
    labor_total: CategoryTotal = Field(..., description="Total for all labor")
    fees_total: CategoryTotal = Field(..., description="Total for all additional fees")
    total_estimate: TotalEstimate = Field(..., description="Total cost estimate range")

class DamageData(BaseModel):
    """Complete damage assessment and cost breakdown"""
    damaged_parts: List[DamagedPart] = Field(..., description="List of damaged parts with details")
    cost_breakdown: CostBreakdown = Field(..., description="Detailed cost breakdown")

class FraudAnalysis(BaseModel):
    """Fraud analysis and risk assessment"""
    fraud_commentary: Optional[str] = Field(None, description="Commentary on potential fraud indicators in the claim")
    fraud_risk_level: str = Field(..., description="Assessed risk level of fraud/inauthenticity (very low, low, medium, high, very high)")

class DamageAssessmentItem(BaseModel):
    """Single damage assessment item with vehicle info and damage data"""
    vehicle_info: VehicleInfo = Field(..., description="Vehicle information")
    damage_data: DamageData = Field(..., description="Damage assessment and cost data")
    fraud_analysis: FraudAnalysis = Field(..., description="Fraud risk analysis and assessment")

# This is the type we'll use for the API response
EnhancedDamageAssessmentResponse = List[DamageAssessmentItem] 