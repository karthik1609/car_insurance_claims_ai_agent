"""src
English accident report data models based on European Accident Statement JSON template
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class InjuriesEN(BaseModel):
    occurred: bool
    description: Optional[str] = ""

class MaterialDamageEN(BaseModel):
    other_than_vehicles: bool
    other_object: bool # Field name from provided JSON was 'other_object', not 'other_objects'
    description: Optional[str] = ""

class WitnessEN(BaseModel):
    name: Optional[str] = ""
    first_name: Optional[str] = ""
    address: Optional[str] = ""
    postal_code: Optional[str] = ""
    country: Optional[str] = ""
    telephone: Optional[str] = ""
    email: Optional[str] = ""

class AccidentDetailsEN(BaseModel):
    date: Optional[str] = ""
    time: Optional[str] = ""
    locality: Optional[str] = ""
    place: Optional[str] = ""
    country: Optional[str] = ""
    injuries: InjuriesEN
    material_damage: MaterialDamageEN
    witnesses: List[WitnessEN] = Field(default_factory=list)

class InsuredPolicyholderEN(BaseModel):
    name: Optional[str] = ""
    first_name: Optional[str] = ""
    address: Optional[str] = ""
    postal_code: Optional[str] = ""
    country: Optional[str] = ""
    telephone_or_email: Optional[str] = ""

class VehicleMotorEN(BaseModel):
    make_type: Optional[str] = ""
    registration_number: Optional[str] = ""
    country_of_registration: Optional[str] = ""

class VehicleTrailerEN(BaseModel):
    registration_number: Optional[str] = ""
    country_of_registration: Optional[str] = ""

class VehicleDetailEN(BaseModel): # Renamed from VehicleEN to avoid conflict
    motor: VehicleMotorEN
    trailer: VehicleTrailerEN

class InsuranceAgencyEN(BaseModel):
    name: Optional[str] = ""
    address: Optional[str] = ""
    country: Optional[str] = ""
    telephone_or_email: Optional[str] = ""

class InsuranceDetailsEN(BaseModel): # Renamed from InsuranceEN
    company_name: Optional[str] = ""
    policy_number: Optional[str] = ""
    green_card_number: Optional[str] = ""
    valid_from: Optional[str] = ""
    valid_to: Optional[str] = ""
    agency: InsuranceAgencyEN
    material_damage_covered: bool

class DriverEN(BaseModel):
    name: Optional[str] = ""
    first_name: Optional[str] = ""
    address: Optional[str] = ""
    postal_code: Optional[str] = ""
    country: Optional[str] = ""
    telephone_or_email: Optional[str] = ""
    date_of_birth: Optional[str] = ""
    driving_licence_number: Optional[str] = ""
    category: Optional[str] = ""
    valid_until: Optional[str] = ""

class CircumstancesEN(BaseModel):
    parked_stopped: bool = False
    leaving_parking: bool = False
    entering_parking: bool = False
    emerging_car: bool = False # JSON "emerging_car_park_private_driveway" -> "emerging_car"
    entering_car: bool = False # JSON "entering_car_park_private_driveway" -> "entering_car"
    entering_roundabout: bool = False
    circulating_roundabout: bool = False
    striking_rear: bool = False # JSON "striking_rear_same_direction_lane" -> "striking_rear"
    going_same_direction: bool = False # JSON "going_same_direction_different_lane" -> "going_same_direction"
    changing_lanes: bool = False
    overtaking: bool = False
    turning_right: bool = False
    turning_left: bool = False
    reversing: bool = False
    encroaching_lane: bool = False # JSON "encroaching_opposite_lane" -> "encroaching_lane"
    coming_right: bool = False # JSON "coming_from_right_junction" -> "coming_right"
    had_not_observed: bool = False # JSON "had_not_observed_priority_red_light" -> "had_not_observed"
    boxes_marked_total: int = 0

class PartyDetailsEN(BaseModel): # Renamed from PartyEN
    insured_policyholder: InsuredPolicyholderEN
    vehicle: VehicleDetailEN # Corresponds to "vehicle" in JSON for party A/B
    insurance: InsuranceDetailsEN # Corresponds to "insurance" in JSON for party A/B
    driver: DriverEN
    initial_impact_point: Optional[str] = ""
    visible_damage: Optional[str] = ""
    circumstances: CircumstancesEN
    remarks: Optional[str] = ""
    signed_by: Optional[str] = ""

class VehiclesEN(BaseModel):
    A: PartyDetailsEN # Corresponds to "A" in JSON
    B: PartyDetailsEN # Corresponds to "B" in JSON

class ImpactSketchEN(BaseModel):
    description: Optional[str] = "Sketch of accident when impact occurred"
    layout: Optional[str] = ""
    arrows: Optional[str] = ""
    positions: Optional[str] = ""
    road_lines: Optional[str] = ""

class FinalEN(BaseModel):
    liability_admission: bool = False
    note: Optional[str] = "Does not constitute an admission of liability, but a summary of identities and facts to speed up claim settlement"

class AccidentStatementDataEN(BaseModel):
    sheet: Optional[str] = ""
    accident_details: AccidentDetailsEN
    vehicles: VehiclesEN
    impact_sketch: ImpactSketchEN
    final: FinalEN

class AccidentReportEN(BaseModel): # Root model
    accident_statement: AccidentStatementDataEN

    model_config = ConfigDict(
        populate_by_name=True, # Ensures aliases are used if present (though not heavily used here)
        validate_assignment=True, # Validates on assignment
        extra='forbid' # Forbids extra fields not defined in the model
    )

# If you want to export the schema for documentation or other uses:
# if __name__ == \"__main__\":
#     print(AccidentReportEN.model_json_schema(indent=2))
#     # print(AccidentReportEN.schema_json(indent=2)) # Pydantic v1 way 