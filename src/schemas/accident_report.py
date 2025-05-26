"""
German accident report data models for European Accident Statement (EAS) forms
"""
from __future__ import annotations
from datetime import date, time
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class OtherDamage(BaseModel):
    """Information about other damage beyond the involved vehicles"""
    vehicles: bool = Field(..., alias="Sachschaden an anderen Fahrzeugen A und B")
    objects: bool = Field(..., alias="Sachschaden an anderen Gegenständen A und B")
    description: Optional[str] = Field(
        None,
        alias="Wenn ja: Welche Fahrzeuge / Gegenstände"
    )

class DamageDiagram(BaseModel):
    """Diagram indicating location of damage on a vehicle"""
    front: bool = Field(False, description="Schaden vorne")
    rear: bool = Field(False, description="Schaden hinten")
    left: bool = Field(False, description="Schaden links")
    right: bool = Field(False, description="Schaden rechts")
    top: bool = Field(False, description="Schaden oben")
    bottom: bool = Field(False, description="Schaden unten")

class InsuranceInfo(BaseModel):
    """Insurance details for a vehicle party"""
    company: str = Field(..., alias="Versicherer")
    policy_number: Optional[str] = Field(None, alias="Versicherungs-/Policen-Nr.")
    green_card_number: Optional[str] = Field(None, alias="Nummer der grünen Karte")
    green_card_valid_until: Optional[date] = Field(
        None, alias="grüne Karte gültig bis"
    )
    confirmation_date: Optional[date] = Field(None, alias="Versicherungsbestätigung vom")
    covers_damage: bool = Field(..., alias="Schäden versichert? (ja/nein)")
    contact: Optional[str] = Field(None, alias="Telefon oder E-Mail Versicherung")
    agent_or_office: Optional[str] = Field(None, alias="Geschäftsstelle / Makler")

class VehicleInfo(BaseModel):
    """Vehicle details for a party involved in an accident"""
    make: Optional[str] = Field(None, alias="Marke, Typ")
    trailer_make: Optional[str] = Field(None, alias="Marke Anhänger")
    license_plate: Optional[str] = Field(None, alias="Amtliches Kennzeichen")
    trailer_plate: Optional[str] = Field(None, alias="Kennzeichen Anhänger")
    registration_country: Optional[str] = Field(None, alias="Land der Zulassung")
    damage_text: Optional[str] = Field(None, alias="Sichtbare Schäden (Text)")
    damage_diagram: Optional[DamageDiagram] = Field(
        None, alias="Sichtbare Schäden (Diagramm-Tickboxes)"
    )

class Person(BaseModel):
    """Base model for people involved in an accident"""
    last_name: str = Field(..., alias="Name")
    first_name: str = Field(..., alias="Vorname")
    address: str = Field(..., alias="Anschrift")
    phone: Optional[str] = Field(None, alias="Telefon")
    email: Optional[str] = Field(None, alias="E-Mail")
    birth_date: Optional[date] = Field(None, alias="Geburtsdatum")

class DriverInfo(Person):
    """Driver details including license information"""
    license_number: Optional[str] = Field(None, alias="Führerschein-Nr.")
    license_class: Optional[str] = Field(None, alias="Führerschein Klasse")
    license_valid_from: Optional[date] = Field(None, alias="gültig ab")
    license_authority: Optional[str] = Field(None, alias="ausgestellt von")
    contact_alt: Optional[str] = Field(None, alias="Telefon oder E-Mail Fahrer")

class Witness(Person):
    """Witness information"""
    pass

class AccidentCircumstances(BaseModel):
    """Circumstances of the accident, including checkboxes"""
    selected_items: List[int] = Field(
        ..., alias="Angekreuzte Unfallumstände", 
        description="Nummern 1–17"
    )
    circumstance_count: int = Field(
        ..., alias="Anzahl angekreuzter Felder"
    )
    free_text: Optional[str] = Field(
        None, alias="Eigene Bemerkungen zum Unfallhergang"
    )

class Sketch(BaseModel):
    """Accident sketch details"""
    image_data: Optional[bytes] = Field(
        None, alias="Skizze (Grid-Bild)"
    )
    impact_point_a: Optional[str] = Field(
        None, alias="Ursprungsaufprallstelle A"
    )
    impact_point_b: Optional[str] = Field(
        None, alias="Ursprungsaufprallstelle B"
    )

class Signatures(BaseModel):
    """Digital signatures of the drivers"""
    driver_a: Optional[bytes] = Field(
        None, alias="Unterschrift Fahrer A"
    )
    driver_b: Optional[bytes] = Field(
        None, alias="Unterschrift Fahrer B"
    )

class Party(BaseModel):
    """One party involved in the accident (either A or B)"""
    insurance: InsuranceInfo = Field(..., alias="Versicherungsdaten")
    vehicle: VehicleInfo = Field(..., alias="Fahrzeugdaten")
    driver: DriverInfo = Field(..., alias="Fahrerdaten")
    icon_impact_marker: Optional[str] = Field(
        None,
        alias="Pfeil-Markierung auf Fahrzeug-Icon"
    )
    damages_notes: Optional[str] = Field(
        None, alias="Eigene Bemerkungen / Schadenbeschreibung"
    )

class AccidentReport(BaseModel):
    """Complete European Accident Statement (EAS) report"""
    accident_date: date = Field(..., alias="Datum des Unfalls")
    accident_time: time = Field(..., alias="Zeit des Unfalls")
    location: str = Field(..., alias="Ort")
    country: str = Field(..., alias="Land")
    injured: bool = Field(..., alias="Verletzte, einschließlich Leichtverletzte")
    injured_count: Optional[int] = Field(
        None, alias="Anzahl Verletzte"
    )
    other_damage: OtherDamage = Field(..., alias="Sachschäden an anderen Fahrzeugen/Gegenständen")
    witnesses: List[Witness] = Field(
        default_factory=list,
        alias="Zeugen, Namen, Anschrift, Telefon"
    )
    party_a: Party = Field(..., alias="Fahrzeug A")
    party_b: Party = Field(..., alias="Fahrzeug B")
    circumstances: AccidentCircumstances = Field(
        ..., alias="Unfallumstände (1–17)"
    )
    sketch: Optional[Sketch] = Field(None, alias="Skizze des Unfalls")
    signatures: Optional[Signatures] = Field(
        None, alias="Unterschriften der Fahrer"
    )
    additional_comments: Optional[str] = Field(
        None, alias="Eigene Bemerkungen unten"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        validate_default=True,
    ) 