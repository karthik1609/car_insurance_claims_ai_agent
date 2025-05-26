"""
Dutch accident report data models based on European Accident Statement JSON template
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class LetselNL(BaseModel):
    ja: bool # occurred
    beschrijving: Optional[str] = ""

class MaterieleSchadeNL(BaseModel):
    andere_dan_voertuigen_a_en_b: bool # other_than_vehicles
    aan_andere_zaken_dan_voertuigen: bool # other_object
    beschrijving: Optional[str] = ""

class GetuigeNL(BaseModel):
    naam: Optional[str] = ""
    voornaam: Optional[str] = ""
    adres: Optional[str] = ""
    postcode: Optional[str] = ""
    land: Optional[str] = ""
    telefoon: Optional[str] = ""
    email: Optional[str] = ""

class OngevaldetailsNL(BaseModel):
    datum: Optional[str] = "" # YYYY-MM-DD
    tijd: Optional[str] = "" # HH:MM:SS
    plaats_locatie: Optional[str] = "" # locality
    plaats_exact: Optional[str] = "" # place
    land: Optional[str] = ""
    letsel: LetselNL # injuries
    materiele_schade: MaterieleSchadeNL # material_damage
    getuigen: List[GetuigeNL] = Field(default_factory=list)

class VerzekeringnemerNL(BaseModel):
    naam: Optional[str] = ""
    voornaam: Optional[str] = ""
    adres: Optional[str] = ""
    postcode: Optional[str] = ""
    land: Optional[str] = ""
    telefoon_of_email: Optional[str] = ""

class VoertuigMotorNL(BaseModel):
    merk_type: Optional[str] = ""
    kenteken: Optional[str] = ""
    land_van_inschrijving: Optional[str] = ""

class VoertuigAanhangwagenNL(BaseModel):
    kenteken: Optional[str] = ""
    land_van_inschrijving: Optional[str] = ""

class VoertuigdetailsNL(BaseModel):
    motor: VoertuigMotorNL
    aanhangwagen: VoertuigAanhangwagenNL

class VerzekeringsagentschapNL(BaseModel):
    naam: Optional[str] = ""
    adres: Optional[str] = ""
    land: Optional[str] = ""
    telefoon_of_email: Optional[str] = ""

class VerzekeringsgegevensNL(BaseModel):
    maatschappij_naam: Optional[str] = ""
    polisnummer: Optional[str] = ""
    groene_kaart_nummer: Optional[str] = ""
    geldig_vanaf: Optional[str] = ""
    geldig_tot: Optional[str] = ""
    agentschap: VerzekeringsagentschapNL
    materiele_schade_gedekt: bool

class BestuurderNL(BaseModel):
    naam: Optional[str] = ""
    voornaam: Optional[str] = ""
    adres: Optional[str] = ""
    postcode: Optional[str] = ""
    land: Optional[str] = ""
    telefoon_of_email: Optional[str] = ""
    geboortedatum: Optional[str] = ""
    rijbewijsnummer: Optional[str] = ""
    categorie: Optional[str] = ""
    geldig_tot: Optional[str] = ""

class OmstandighedenNL(BaseModel):
    stond_geparkeerd_stond_stil: bool = Field(False, alias="1_stond_geparkeerd_stond_stil")
    verliet_parkeerplaats_ging_weg_van_stilstaande_positie: bool = Field(False, alias="2_verliet_een_parkeerplaats_ging_weg_van_een_stilstaande_positie_opende_een_portier")
    reed_parkeerplaats_op_nam_stilstaande_positie_in: bool = Field(False, alias="3_reed_een_parkeerplaats_op_nam_een_stilstaande_positie_in")
    kwam_van_parkeerterrein_private_plaats_aardeweg: bool = Field(False, alias="4_kwam_van_een_parkeerterrein_van_een_private_plaats_van_een_aardeweg")
    reed_parkeerterrein_private_plaats_aardeweg_op: bool = Field(False, alias="5_reed_een_parkeerterrein_een_private_plaats_een_aardeweg_op")
    reed_rotonde_op: bool = Field(False, alias="6_reed_een_rotonde_op")
    reed_op_rotonde: bool = Field(False, alias="7_reed_op_een_rotonde")
    reed_in_op_achterzijde_andere_voertuig_in_zelfde_rijstrook_en_richting: bool = Field(False, alias="8_reed_in_op_de_achterzijde_van_een_ander_voertuig_dat_in_dezelfde_richting_en_in_dezelfde_rijstrook_reed")
    reed_in_zelfde_richting_maar_andere_rijstrook: bool = Field(False, alias="9_reed_in_dezelfde_richting_maar_in_een_andere_rijstrook")
    veranderde_van_rijstrook: bool = Field(False, alias="10_veranderde_van_rijstrook")
    haalde_in: bool = Field(False, alias="11_haalde_in")
    sloeg_rechtsaf: bool = Field(False, alias="12_sloeg_rechtsaf")
    sloeg_linksaf: bool = Field(False, alias="13_sloeg_linksaf")
    reed_achteruit: bool = Field(False, alias="14_reed_achteruit")
    kwam_op_rijstrook_bestemd_voor_tegemoetkomend_verkeer: bool = Field(False, alias="15_kwam_op_een_rijstrook_die_bestemd_was_voor_het_tegemoetkomend_verkeer")
    kwam_van_rechts_op_kruispunt: bool = Field(False, alias="16_kwam_van_rechts_op_een_kruispunt")
    negeerde_verkeersteken_dat_voorrang_aanduidde_of_rood_licht: bool = Field(False, alias="17_negeerde_een_verkeersteken_dat_voorrang_aanduidde_of_een_rood_licht")
    totaal_aangekruiste_vakjes: int = Field(0, alias="aantal_aangekruiste_vakjes") # Translated from boxes_marked_total

class PartijDetailsNL(BaseModel):
    verzekeringnemer: VerzekeringnemerNL
    voertuig: VoertuigdetailsNL
    verzekering: VerzekeringsgegevensNL
    bestuurder: BestuurderNL
    eerste_aanrijdingspunt: Optional[str] = ""
    zichtbare_schade: Optional[str] = ""
    omstandigheden: OmstandighedenNL
    opmerkingen: Optional[str] = ""
    ondertekend_door: Optional[str] = ""

class VoertuigenNL(BaseModel):
    A: PartijDetailsNL
    B: PartijDetailsNL

class AanrijdingsschetsNL(BaseModel):
    beschrijving: Optional[str] = "Schets van de aanrijding op het ogenblik van de botsing"
    layout: Optional[str] = "" # Beeldgegevens of gedetailleerdere beschrijving
    pijlen: Optional[str] = ""
    posities: Optional[str] = ""
    wegmarkeringen: Optional[str] = ""

class SlotverklaringNL(BaseModel):
    erkenning_van_aansprakelijkheid: bool = False
    opmerking: Optional[str] = "Betekent geen erkenning van aansprakelijkheid, maar dient ter vaststelling van de identiteit en de feiten en versnelt de regeling van de schade."

class OngevalsaangifteGegevensNL(BaseModel):
    blad: Optional[str] = "" # Sheet number/identifier
    ongevaldetails: OngevaldetailsNL
    voertuigen: VoertuigenNL
    aanrijdingsschets: AanrijdingsschetsNL
    slotverklaring: SlotverklaringNL # final

class AccidentReportNL(BaseModel): # Root model
    ongevalsaangifte: OngevalsaangifteGegevensNL # Translated from accident_statement

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        extra='forbid'
    )

# if __name__ == "__main__":
#     print(AccidentReportNL.model_json_schema(indent=2)) 