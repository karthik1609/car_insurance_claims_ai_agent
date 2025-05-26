"""
German accident report data models based on European Accident Statement JSON template
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class VerletzungenDE(BaseModel):
    stattgefunden: bool
    beschreibung: Optional[str] = ""

class SachschaedenDE(BaseModel):
    andere_als_fahrzeuge_a_und_b: bool # Sachschaden an anderen Fahrzeugen als A und B
    an_anderen_gegenstaenden: bool # Sachschaden an anderen Gegenständen als Fahrzeuge A und B
    beschreibung: Optional[str] = ""

class ZeugeDE(BaseModel):
    name: Optional[str] = ""
    vorname: Optional[str] = ""
    anschrift: Optional[str] = ""
    postleitzahl: Optional[str] = ""
    land: Optional[str] = ""
    telefon: Optional[str] = ""
    email: Optional[str] = ""

class UnfalldetailsDE(BaseModel):
    datum: Optional[str] = "" # YYYY-MM-DD
    uhrzeit: Optional[str] = "" # HH:MM:SS
    oertlichkeit: Optional[str] = ""
    ort: Optional[str] = "" # Genaue Ortsangabe
    land: Optional[str] = ""
    verletzungen: VerletzungenDE
    sachschaeden: SachschaedenDE # Field renamed from material_damage
    zeugen: List[ZeugeDE] = Field(default_factory=list)

class VersicherungsnehmerDE(BaseModel):
    name: Optional[str] = ""
    vorname: Optional[str] = ""
    anschrift: Optional[str] = ""
    postleitzahl: Optional[str] = ""
    land: Optional[str] = ""
    telefon_oder_email: Optional[str] = ""

class FahrzeugMotorDE(BaseModel):
    marke_typ: Optional[str] = ""
    amtliches_kennzeichen: Optional[str] = ""
    zulassungsland: Optional[str] = ""

class FahrzeugAnhaengerDE(BaseModel):
    amtliches_kennzeichen: Optional[str] = ""
    zulassungsland: Optional[str] = ""

class FahrzeugdetailsDE(BaseModel):
    motor: FahrzeugMotorDE
    anhaenger: FahrzeugAnhaengerDE

class VersicherungsagenturDE(BaseModel):
    name: Optional[str] = ""
    anschrift: Optional[str] = ""
    land: Optional[str] = ""
    telefon_oder_email: Optional[str] = ""

class VersicherungsdatenDE(BaseModel):
    gesellschaftsname: Optional[str] = ""
    policennummer: Optional[str] = ""
    gruene_karte_nummer: Optional[str] = ""
    gueltig_ab: Optional[str] = ""
    gueltig_bis: Optional[str] = ""
    agentur: VersicherungsagenturDE
    sachschaeden_gedeckt: bool

class FahrerDE(BaseModel):
    name: Optional[str] = ""
    vorname: Optional[str] = ""
    anschrift: Optional[str] = ""
    postleitzahl: Optional[str] = ""
    land: Optional[str] = ""
    telefon_oder_email: Optional[str] = ""
    geburtsdatum: Optional[str] = ""
    fuehrerscheinnummer: Optional[str] = ""
    kategorie: Optional[str] = ""
    gueltig_bis: Optional[str] = ""

class UmstaendeDE(BaseModel):
    geparkt_hielt_an: bool = Field(False, alias="1_stand_geparkt_hielt_an")
    verliess_parkplatz_oeffnete_tuer: bool = Field(False, alias="2_verliess_einen_parkplatz_oeffnete_eine_tuer")
    bog_in_parkplatz_ein: bool = Field(False, alias="3_bog_in_einen_parkplatz_ein")
    kam_aus_parkplatz_grundstueck_feldweg: bool = Field(False, alias="4_kam_aus_einem_parkplatz_einem_grundstueck_einem_feldweg")
    bog_auf_parkplatz_grundstueck_feldweg_ein: bool = Field(False, alias="5_bog_auf_einen_parkplatz_ein_grundstueck_einen_feldweg_ein")
    bog_in_kreisverkehr_ein: bool = Field(False, alias="6_bog_in_einen_kreisverkehr_ein")
    fuhr_in_kreisverkehr: bool = Field(False, alias="7_fuhr_im_kreisverkehr")
    fuhr_auf_heck_eines_anderen_fahrzeugs_auf_gleiche_richtung_spur: bool = Field(False, alias="8_fuhr_auf_das_heck_eines_anderen_fahrzeugs_auf_das_in_derselben_richtung_und_auf_demselben_fahrstreifen_fuhr")
    fuhr_in_gleicher_richtung_anderer_fahrstreifen: bool = Field(False, alias="9_fuhr_in_derselben_richtung_aber_auf_einem_anderen_fahrstreifen")
    wechselte_fahrstreifen: bool = Field(False, alias="10_wechselte_den_fahrstreifen")
    ueberholte: bool = Field(False, alias="11_ueberholte")
    bog_rechts_ab: bool = Field(False, alias="12_bog_rechts_ab")
    bog_links_ab: bool = Field(False, alias="13_bog_links_ab")
    fuhr_rueckwaerts: bool = Field(False, alias="14_fuhr_rueckwaerts")
    drang_auf_fahrstreifen_fuer_gegenverkehr_ein: bool = Field(False, alias="15_drang_auf_einen_fahrstreifen_ein_der_fuer_den_gegenverkehr_bestimmt_war")
    kam_von_rechts_kreuzung: bool = Field(False, alias="16_kam_von_rechts_kreuzung")
    hatte_vorfahrt_oder_rote_ampel_nicht_beachtet: bool = Field(False, alias="17_hatte_ein_vorfahrtzeichen_oder_eine_rote_ampel_nicht_beachtet")
    angekreuzte_felder_summe: int = Field(0, alias="angekreuzte_felder_anzahl") # Translated from boxes_marked_total

class ParteiDetailsDE(BaseModel):
    versicherungsnehmer: VersicherungsnehmerDE
    fahrzeug: FahrzeugdetailsDE
    versicherung: VersicherungsdatenDE
    fahrer: FahrerDE
    erster_aufprallpunkt: Optional[str] = ""
    sichtbare_schaeden: Optional[str] = ""
    umstaende: UmstaendeDE
    bemerkungen: Optional[str] = ""
    unterschrieben_von: Optional[str] = ""

class FahrzeugeDE(BaseModel):
    A: ParteiDetailsDE
    B: ParteiDetailsDE

class UnfallskizzeDE(BaseModel):
    beschreibung: Optional[str] = "Skizze des Unfallhergangs zum Zeitpunkt des Zusammenstosses"
    layout: Optional[str] = "" # Bilddaten oder detailliertere Beschreibung der Skizze
    pfeile: Optional[str] = ""
    positionen: Optional[str] = ""
    fahrbahnmarkierungen: Optional[str] = ""

class AbschlussDE(BaseModel):
    haftungsanerkenntnis: bool = False
    hinweis: Optional[str] = "Stellt kein Haftungsanerkenntnis dar, sondern eine Zusammenfassung von Identitäten und Fakten zur Beschleunigung der Schadenregulierung"

class UnfallberichtDatenDE(BaseModel):
    blatt: Optional[str] = "" # Sheet number/identifier
    unfalldetails: UnfalldetailsDE
    fahrzeuge: FahrzeugeDE
    unfallskizze: UnfallskizzeDE
    abschluss: AbschlussDE

class AccidentReport(BaseModel): # Root model, class name kept as AccidentReport for German
    unfallbericht: UnfallberichtDatenDE # Translated from accident_statement

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        extra='forbid'
    )

# if __name__ == "__main__":
#     print(AccidentReport.model_json_schema(indent=2)) 