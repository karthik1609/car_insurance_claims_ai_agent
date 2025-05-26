import asyncio
import os
import logging
from typing import Dict, Any, Optional, Union, List, Tuple
from datetime import date, time

from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer.aio import DocumentAnalysisClient
from azure.core.exceptions import HttpResponseError
from tenacity import retry, stop_after_attempt, wait_exponential_async, before_sleep_log

from src.schemas.accident_report_de import AccidentReport as AccidentReportDE, Versicherungsnehmer as VersicherungsnehmerDE, Fahrzeug as FahrzeugDE, Versicherung as VersicherungDE, Fahrer as FahrerDE, Umstaende as UmstaendeDE, Zeuge as ZeugeDE # Assuming German is the base
from src.schemas.accident_report_en import AccidentReportEN, PolicyholderEN, VehicleEN, InsuranceEN, DriverEN, CircumstancesEN, WitnessEN
from src.schemas.accident_report_nl import AccidentReportNL, VerzekeringnemerNL, VoertuigNL, VerzekeringNL, BestuurderNL, OmstandighedenNL, GetuigeNL
from src.schemas.language import Language
from src.logger import get_logger
from src.core.config import settings

logger = get_logger(__name__)

# Constants
MIN_CONFIDENCE_THRESHOLD = 0.8
RETRY_ATTEMPTS = 3
RETRY_WAIT_MULTIPLIER = 1 # Base for exponential backoff (e.g., 1s, 2s, 4s)

class AzureRecognizerClient:
    """
    Client for interacting with Azure AI Document Intelligence (Form Recognizer).
    Handles document analysis using prebuilt and custom models.
    """
    def __init__(self):
        """Initializes the DocumentAnalysisClient."""
        if not settings.AZURE_FORM_RECOGNIZER_ENDPOINT or not settings.AZURE_FORM_RECOGNIZER_KEY:
            logger.error("Azure Form Recognizer endpoint or key is not configured.")
            raise ValueError("Azure Form Recognizer endpoint and key must be set in environment variables or config.")
        
        self.endpoint = settings.AZURE_FORM_RECOGNIZER_ENDPOINT
        self.key = AzureKeyCredential(settings.AZURE_FORM_RECOGNIZER_KEY)
        self.custom_model_id_de = settings.AZURE_FORM_RECOGNIZER_CUSTOM_MODEL_ID_DE
        self.custom_model_id_en = settings.AZURE_FORM_RECOGNIZER_CUSTOM_MODEL_ID_EN
        self.custom_model_id_nl = settings.AZURE_FORM_RECOGNIZER_CUSTOM_MODEL_ID_NL
        
        self.document_analysis_client = DocumentAnalysisClient(
            endpoint=self.endpoint, credential=self.key
        )
        logger.info("DocumentAnalysisClient initialized.")

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential_async(multiplier=RETRY_WAIT_MULTIPLIER),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def _analyze_document_with_model(self, model_id: str, document_bytes: bytes, **kwargs) -> Any:
        """
        Helper function to analyze a document with a specific model, with retries.

        Args:
            model_id: The ID of the model to use (e.g., 'prebuilt-layout', custom model ID).
            document_bytes: The document content as bytes.
            **kwargs: Additional arguments for begin_analyze_document.

        Returns:
            The analysis result.

        Raises:
            HttpResponseError: If the API call fails after retries.
        """
        try:
            logger.info(f"Starting document analysis with model: {model_id}")
            poller = await self.document_analysis_client.begin_analyze_document(
                model_id=model_id,
                document=document_bytes,
                **kwargs
            )
            result = await poller.result()
            logger.info(f"Successfully analyzed document with model: {model_id}")
            return result
        except HttpResponseError as e:
            logger.error(f"HTTP error during Form Recognizer call to model {model_id}: {e.message}", exc_info=True)
            # Log more context if available
            if e.response and hasattr(e.response, 'text'):
                logger.error(f"Azure API Response content: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Form Recognizer call to model {model_id}: {str(e)}", exc_info=True)
            raise

    async def get_layout_and_custom_form_results(
        self,
        image_bytes: bytes,
        language: Language
    ) -> Tuple[Optional[Any], Optional[Any]]:
        """
        Analyzes an image using both prebuilt-layout and a language-specific custom form model.

        Args:
            image_bytes: The preprocessed image bytes.
            language: The language of the form to select the correct custom model.

        Returns:
            A tuple containing (layout_result, custom_form_result).
            Either can be None if the respective analysis fails.
        """
        layout_result = None
        custom_form_result = None

        try:
            layout_result = await self._analyze_document_with_model(
                model_id="prebuilt-layout",
                document_bytes=image_bytes
            )
        except Exception as e:
            logger.error(f"Failed to get layout results after retries: {str(e)}")
            # Continue to custom model even if layout fails

        custom_model_id = self._get_custom_model_id(language)
        if not custom_model_id:
            logger.warning(f"No custom model ID configured for language: {language}. Skipping custom form analysis.")
            return layout_result, None

        try:
            custom_form_result = await self._analyze_document_with_model(
                model_id=custom_model_id,
                document_bytes=image_bytes
            )
        except Exception as e:
            logger.error(f"Failed to get custom form results for model {custom_model_id} after retries: {str(e)}")
            # Fallback to layout_result if custom fails entirely

        return layout_result, custom_form_result

    def _get_custom_model_id(self, language: Language) -> Optional[str]:
        """Returns the custom model ID based on the language."""
        if language == Language.DE:
            return self.custom_model_id_de
        elif language == Language.EN:
            return self.custom_model_id_en
        elif language == Language.NL:
            return self.custom_model_id_nl
        logger.warning(f"No custom model ID configured for language: {language}")
        return None

    # Placeholder for the main processing method
    async def extract_accident_report_data(
        self,
        preprocessed_image_bytes: bytes, # Bytes from ocr.preprocess.encode_image_for_form_recognizer
        language: Language,
        original_image_bytes: Optional[bytes] = None # For fallback or context if needed
    ) -> Union[AccidentReportDE, AccidentReportEN, AccidentReportNL, None]:
        """
        Orchestrates the OCR process using Azure AI Document Intelligence.
        1. Calls prebuilt-layout model.
        2. Calls custom-trained form model.
        3. Maps extracted fields to the appropriate Pydantic schema.

        Args:
            preprocessed_image_bytes: The bytes of the image after OpenCV preprocessing and encoding.
            language: The language of the form to process.
            original_image_bytes: Original image bytes, potentially for fallback if custom model fails badly.

        Returns:
            An instance of AccidentReportDE, AccidentReportEN, or AccidentReportNL, 
            or None if critical information cannot be extracted.
        """
        layout_result, custom_form_result = await self.get_layout_and_custom_form_results(
            image_bytes=preprocessed_image_bytes,
            language=language
        )

        if not custom_form_result and not layout_result:
            logger.error("Both layout and custom model analysis failed. Cannot extract data.")
            return None

        report: Union[AccidentReportDE, AccidentReportEN, AccidentReportNL, None] = None
        if language == Language.EN:
            report = self._map_to_accident_report_en(custom_form_result, layout_result)
        elif language == Language.NL:
            report = self._map_to_accident_report_nl(custom_form_result, layout_result)
        elif language == Language.DE:
            report = self._map_to_accident_report_de(custom_form_result, layout_result)
        else:
            logger.error(f"Unsupported language for mapping: {language}")
            return None
        
        if report:
            logger.info(f"Successfully extracted and mapped data for language {language}.")
        else:
            logger.warning(f"Failed to map data for language {language}. Check logs for details.")
            
        return report

    # --- Helper functions for field parsing and validation ---
    def _get_field_value(
        self,
        doc_fields: Dict[str, Any],
        field_name_map: Dict[str, str], # Maps Pydantic field to form field names
        pydantic_field_key: str,
        default_value: Any = None
    ) -> Optional[Any]:
        """Safely retrieves and validates a field value from DocumentAnalysisResult.documents[0].fields."""
        form_field_name = field_name_map.get(pydantic_field_key)
        if not form_field_name:
            # This case should ideally not happen if field_name_map is comprehensive
            logger.warning(f"No mapping found for Pydantic field: {pydantic_field_key}. Check field_name_map.")
            return default_value

        field = doc_fields.get(form_field_name)
        if field:
            if field.confidence is not None and field.confidence < MIN_CONFIDENCE_THRESHOLD:
                logger.warning(
                    f'Low confidence for field "{form_field_name}" (mapped to "{pydantic_field_key}"): ' \
                    f'{field.confidence:.2f}. Setting to default/None.'
                )
                return default_value
            
            # Return the content, specific type parsing will be handled by callers
            return field.content if field.content is not None else default_value
        return default_value

    def _parse_date(self, date_str: Optional[str], field_name: str) -> Optional[date]:
        """Parses a date string into YYYY-MM-DD format."""
        if not date_str:
            return None
        try:
            # Common European formats: DD.MM.YYYY, DD/MM/YYYY, YYYY-MM-DD
            # Azure Form Recognizer might return it already in YYYY-MM-DD
            if '-' in date_str and len(date_str.split('-')[0]) == 4: # YYYY-MM-DD or YYYY-M-D
                dt = date.fromisoformat(date_str)
            elif '.' in date_str:
                day, month, year = map(int, date_str.split('.'))
                dt = date(year, month, day)
            elif '/' in date_str:
                parts = list(map(int, date_str.split('/')))
                if len(parts[0]) == 4: # YYYY/MM/DD
                    dt = date(parts[0], parts[1], parts[2])
                else: # DD/MM/YYYY
                    dt = date(parts[2], parts[1], parts[0])
            else: # Attempt direct ISO format for other cases like YYYYMMDD
                dt = date.fromisoformat(date_str) 
            return dt
        except (ValueError, TypeError, IndexError) as e:
            logger.warning(f'Could not parse date string "{date_str}" for field "{field_name}": {e}. Returning None.')
            return None

    def _parse_time(self, time_str: Optional[str], field_name: str) -> Optional[time]:
        """Parses a time string into HH:MM format."""
        if not time_str:
            return None
        try:
            # Expects HH:MM or HH:MM:SS from Form Recognizer
            hour, minute = map(int, time_str.split(':')[:2])
            return time(hour, minute)
        except (ValueError, TypeError, IndexError) as e:
            logger.warning(f'Could not parse time string "{time_str}" for field "{field_name}": {e}. Returning None.')
            return None

    def _parse_postal_code(self, postal_code_str: Optional[str], field_name: str, country_code: Optional[str] = None) -> Optional[str]:
        """Validates and formats a postal code. Currently simple 5-digit check."""
        # TODO: Implement more sophisticated country-specific postal code validation if needed
        if not postal_code_str:
            return None
        
        # Basic validation: 5 digits for now (common in DE, can be adapted)
        # Preserve original casing if not strictly numeric (e.g. UK, NL)
        # For this project, EAS often has numeric postal codes
        cleaned_postal_code = ''.join(filter(str.isalnum, postal_code_str))
        
        # Example for German postal codes (must be 5 digits)
        if country_code == "DE":
            if len(cleaned_postal_code) == 5 and cleaned_postal_code.isdigit():
                return cleaned_postal_code
            else:
                logger.warning(f'Invalid German postal code "{postal_code_str}" for field "{field_name}". Expected 5 digits. Returning None.')
                return None
        
        # Basic fallback for other countries - can be expanded
        if len(cleaned_postal_code) >= 3 and len(cleaned_postal_code) <= 10: # Generic length check
             return postal_code_str # Return original if it passes a loose check

        logger.warning(f'Postal code "{postal_code_str}" for field "{field_name}" did not meet validation criteria. Returning None.')
        return None

    def _get_selection_mark_state(self, doc_fields: Dict[str, Any], field_name: str, default_value: bool = False) -> bool:
        """Retrieves the state of a selection mark (checkbox)."""
        field = doc_fields.get(field_name)
        if field:
            if field.confidence is not None and field.confidence < MIN_CONFIDENCE_THRESHOLD:
                logger.warning(f'Low confidence for selection mark "{field_name}": {field.confidence:.2f}. Defaulting to {default_value}.')
                return default_value
            # Azure Form Recognizer: 'selected' or 'unselected'
            return field.value == 'selected' if field.value else default_value 
        return default_value

    # --- Language-specific mapping functions ---

    def _map_to_accident_report_de(
        self, 
        custom_result: Optional[Any], 
        layout_result: Optional[Any]
    ) -> Optional[AccidentReportDE]:
        """Maps Azure Form Recognizer results to AccidentReportDE Pydantic model."""
        if not custom_result or not custom_result.documents:
            logger.warning("No custom model documents found for German mapping.")
            # TODO: Consider fallback to layout_result if custom fails entirely
            return None
        
        doc = custom_result.documents[0] # Assuming one document per image
        fields = doc.fields

        # IMPORTANT: Replace these with the *actual* field names from your trained Azure model for German forms
        DE_FIELD_MAP = {
            # Hauptteil (Unfallbericht)
            "blatt": "Allgemein_Blattnummer", # General_SheetNumber
            # Unfalldetails (1-5)
            "unfalldatum": "Unfalldetails_Datum", # AccidentDetails_Date
            "unfallzeit": "Unfalldetails_Uhrzeit", # AccidentDetails_Time
            "oertlichkeit_strasse_nr": "Unfalldetails_OertlichkeitStrasseNr", # AccidentDetails_LocationStreetNumber
            "unfallort_plz": "Unfalldetails_OrtPLZ", # AccidentDetails_LocationCityZip
            "unfallland": "Unfalldetails_Land", # AccidentDetails_Country
            "verletzte_ja_nein": "Verletzungen_JaNein", # Injuries_YesNo (SelectionMark)
            "verletzte_namen_anschriften": "Verletzungen_NamenAnschriften", # Injuries_NamesAddresses
            "sachschaeden_andere_kfz_ja_nein": "Sachschaeden_AndereKfzAlsAB_JaNein", # MaterialDamage_OtherVehiclesThanAB_YesNo (SelectionMark)
            "sachschaeden_andere_gegenstaende_ja_nein": "Sachschaeden_AndereGegenstaende_JaNein", # MaterialDamage_OtherObjects_YesNo (SelectionMark)
            "sachschaeden_beschreibung": "Sachschaeden_Beschreibung", # MaterialDamage_Description
            # Zeugen (5)
            "zeugen_name_anschrift_telefon": "Zeugen_NameAnschriftTelefon", # Witnesses_NameAddressPhone (This might be a single text field or multiple)
            # For individual witness fields, if your model extracts them separately:
            "zeuge1_name": "Zeuge1_Name",
            "zeuge1_vorname": "Zeuge1_Vorname",
            "zeuge1_anschrift": "Zeuge1_Anschrift",
            "zeuge1_plz": "Zeuge1_PLZ",
            "zeuge1_land": "Zeuge1_Land",
            "zeuge1_telefon": "Zeuge1_Telefon",
            "zeuge1_email": "Zeuge1_Email",
            # Fahrzeug A & B Sections (Common fields prefixed with ParteiA_ or ParteiB_)
            # Versicherungsnehmer (6)
            "partei_versicherungsnehmer_name": "{party}_Versicherungsnehmer_Name",
            "partei_versicherungsnehmer_vorname": "{party}_Versicherungsnehmer_Vorname",
            "partei_versicherungsnehmer_anschrift": "{party}_Versicherungsnehmer_Anschrift",
            "partei_versicherungsnehmer_plz": "{party}_Versicherungsnehmer_PLZ",
            "partei_versicherungsnehmer_land": "{party}_Versicherungsnehmer_Land",
            "partei_versicherungsnehmer_telefon_email": "{party}_Versicherungsnehmer_TelefonEmail",
            # Fahrzeug (7)
            "partei_fahrzeug_marke_typ": "{party}_Fahrzeug_MarkeTyp",
            "partei_fahrzeug_kennzeichen": "{party}_Fahrzeug_AmtlKennzeichen",
            "partei_fahrzeug_zulassungsland": "{party}_Fahrzeug_Zulassungsland",
            "partei_anhaenger_kennzeichen": "{party}_Anhaenger_AmtlKennzeichen",
            "partei_anhaenger_zulassungsland": "{party}_Anhaenger_Zulassungsland",
            # Versicherungsgesellschaft (8)
            "partei_versicherung_gesellschaft": "{party}_Versicherung_Gesellschaft",
            "partei_versicherung_schein_nr": "{party}_Versicherung_ScheinNr",
            "partei_versicherung_gruene_karte_nr": "{party}_Versicherung_GrueneKarteNr",
            "partei_versicherung_gueltig_ab": "{party}_Versicherung_GueltigAb",
            "partei_versicherung_gueltig_bis": "{party}_Versicherung_GueltigBis",
            "partei_versicherung_agentur_name": "{party}_Versicherung_AgenturName",
            "partei_versicherung_agentur_anschrift": "{party}_Versicherung_AgenturAnschrift",
            "partei_versicherung_agentur_land": "{party}_Versicherung_AgenturLand",
            "partei_versicherung_agentur_telefon_email": "{party}_Versicherung_AgenturTelefonEmail",
            "partei_versicherung_anhaenger_gedeckt_ja_nein": "{party}_Versicherung_AnhaengerGedeckt_JaNein", # (SelectionMark)
            "partei_versicherung_sachschaeden_gedeckt_ja_nein": "{party}_Versicherung_SachschaedenGedeckt_JaNein", # (SelectionMark)
            # Fahrer (9)
            "partei_fahrer_name": "{party}_Fahrer_Name",
            "partei_fahrer_vorname": "{party}_Fahrer_Vorname",
            "partei_fahrer_geburtsdatum": "{party}_Fahrer_Geburtsdatum",
            "partei_fahrer_anschrift": "{party}_Fahrer_Anschrift",
            "partei_fahrer_plz": "{party}_Fahrer_PLZ",
            "partei_fahrer_land": "{party}_Fahrer_Land",
            "partei_fahrer_telefon_email": "{party}_Fahrer_TelefonEmail",
            "partei_fahrer_fuehrerschein_nr": "{party}_Fahrer_FuehrerscheinNr",
            "partei_fahrer_fuehrerschein_kategorie": "{party}_Fahrer_FuehrerscheinKategorie",
            "partei_fahrer_fuehrerschein_gueltig_bis": "{party}_Fahrer_FuehrerscheinGueltigBis",
            # Aufprallpunkt (10)
            "partei_aufprallpunkt": "{party}_Aufprallpunkt", # Description from image mark
            # Sichtbare Schaeden (11)
            "partei_sichtbare_schaeden": "{party}_SichtbareSchaeden",
            # Umstaende (12) - These are typically selection marks
            "partei_umstand_1_geparkt_hielt_an": "{party}_Umstand_1_GeparktHieltAn",
            "partei_umstand_2_verliess_parkplatz": "{party}_Umstand_2_VerliessParkplatz",
            "partei_umstand_3_bog_in_parkplatz_ein": "{party}_Umstand_3_BogInParkplatzEin",
            "partei_umstand_4_kam_aus_parkplatz": "{party}_Umstand_4_KamAusParkplatz",
            "partei_umstand_5_bog_auf_parkplatz_ein": "{party}_Umstand_5_BogAufParkplatzEin",
            "partei_umstand_6_bog_in_kreisverkehr_ein": "{party}_Umstand_6_BogInKreisverkehrEin",
            "partei_umstand_7_fuhr_in_kreisverkehr": "{party}_Umstand_7_FuhrInKreisverkehr",
            "partei_umstand_8_auffahrunfall": "{party}_Umstand_8_Auffahrunfall",
            "partei_umstand_9_gleiche_richtung_andere_spur": "{party}_Umstand_9_GleicheRichtungAndereSpur",
            "partei_umstand_10_spurwechsel": "{party}_Umstand_10_Spurwechsel",
            "partei_umstand_11_ueberholte": "{party}_Umstand_11_Ueberholte",
            "partei_umstand_12_bog_rechts_ab": "{party}_Umstand_12_BogRechtsAb",
            "partei_umstand_13_bog_links_ab": "{party}_Umstand_13_BogLinksAb",
            "partei_umstand_14_fuhr_rueckwaerts": "{party}_Umstand_14_FuhrRueckwaerts",
            "partei_umstand_15_gegenverkehr_fahrspur": "{party}_Umstand_15_GegenverkehrFahrspur",
            "partei_umstand_16_kam_von_rechts": "{party}_Umstand_16_KamVonRechts",
            "partei_umstand_17_vorfahrt_missachtet": "{party}_Umstand_17_VorfahrtMissachtet",
            "partei_umstaende_anzahl_angekreuzt": "{party}_Umstaende_AnzahlAngekreuzt",
            # Bemerkungen (14)
            "partei_bemerkungen": "{party}_Bemerkungen",
            # Unterschrift (15)
            "partei_unterschrift_name": "{party}_UnterschriftName", # Check if model extracts name from signature area
            # Skizze (13)
            "skizze_beschreibung": "Skizze_Beschreibung",
             # Abschluss
            "haftungsanerkennung_ja_nein": "Abschluss_Haftungsanerkennung_JaNein", # (SelectionMark)
            "abschliessende_bemerkung": "Abschluss_Bemerkung"
        }

        # Helper to get party-specific field map
        def get_party_field_map(party_prefix: str) -> Dict[str, str]:
            party_map = {}
            for key, value in DE_FIELD_MAP.items():
                if "{party}" in value:
                    party_map[key.replace("partei_", "")] = value.format(party=party_prefix)
            return party_map

        # Helper to populate UmstaendeDE
        def _populate_umstaende(party_prefix: str, doc_fields: Dict[str, Any]) -> UmstaendeDE:
            umstaende_map = get_party_field_map(party_prefix)
            # Filter for circumstance fields only by checking if the Pydantic field name exists in UmstaendeDE
            umstaende_data = {}
            for pydantic_key in UmstaendeDE.model_fields.keys():
                # Construct the full key as it appears in DE_FIELD_MAP for circumstances
                # e.g., "umstand_1_geparkt_hielt_an" -> party_umstand_1_geparkt_hielt_an
                map_key_prefix = "umstand_"
                full_map_key = f"partei_{map_key_prefix}{pydantic_key}" 
                
                form_recognizer_field_name = DE_FIELD_MAP.get(full_map_key)
                if form_recognizer_field_name:
                    # Replace {party} placeholder for this specific call
                    actual_fr_field_name = form_recognizer_field_name.format(party=party_prefix)
                    umstaende_data[pydantic_key] = self._get_selection_mark_state(doc_fields, actual_fr_field_name, False)
            
            # Handle anzahl_angekreuzt separately if it's a direct number field
            anzahl_key = "umstaende_anzahl_angekreuzt"
            anzahl_val_str = self._get_field_value(doc_fields, umstaende_map, anzahl_key, "0")
            try:
                umstaende_data["angekreuzte_felder_summe"] = int(anzahl_val_str) if anzahl_val_str else 0
            except ValueError:
                logger.warning(f"Could not parse anzahl_angekreuzt '{anzahl_val_str}' to int for {party_prefix}. Defaulting to 0.")
                umstaende_data["angekreuzte_felder_summe"] = 0
            return UmstaendeDE(**umstaende_data)

        # Helper to populate party data (Versicherungsnehmer, Fahrzeug, Versicherung, Fahrer)
        def _populate_party_data(party_prefix: str, doc_fields: Dict[str, Any]) -> Tuple[Optional[VersicherungsnehmerDE], Optional[FahrzeugDE], Optional[VersicherungDE], Optional[FahrerDE], Optional[str], Optional[str], Optional[UmstaendeDE], Optional[str], Optional[str]]:
            party_map = get_party_field_map(party_prefix)
            country = self._get_field_value(doc_fields, party_map, "versicherungsnehmer_land")

            versicherungsnehmer = VersicherungsnehmerDE(
                name=self._get_field_value(doc_fields, party_map, "versicherungsnehmer_name"),
                vorname=self._get_field_value(doc_fields, party_map, "versicherungsnehmer_vorname"),
                anschrift=self._get_field_value(doc_fields, party_map, "versicherungsnehmer_anschrift"),
                postleitzahl=self._parse_postal_code(self._get_field_value(doc_fields, party_map, "versicherungsnehmer_plz"), "PLZ Versicherungsnehmer", country_code="DE" if country == "Deutschland" else None),
                land=country,
                telefon_oder_email=self._get_field_value(doc_fields, party_map, "versicherungsnehmer_telefon_email")
            )
            
            fahrzeug_motor_zul_land = self._get_field_value(doc_fields, party_map, "fahrzeug_zulassungsland")
            fahrzeug_anhaenger_zul_land = self._get_field_value(doc_fields, party_map, "anhaenger_zulassungsland")
            fahrzeug = FahrzeugDE(
                motor=FahrzeugDE.Motor(
                    marke_typ=self._get_field_value(doc_fields, party_map, "fahrzeug_marke_typ"),
                    amtliches_kennzeichen=self._get_field_value(doc_fields, party_map, "fahrzeug_kennzeichen"),
                    zulassungsland=fahrzeug_motor_zul_land
                ),
                anhaenger=FahrzeugDE.Anhaenger(
                    amtliches_kennzeichen=self._get_field_value(doc_fields, party_map, "anhaenger_kennzeichen"),
                    zulassungsland=fahrzeug_anhaenger_zul_land
                )
            )

            versicherung_agentur_land = self._get_field_value(doc_fields, party_map, "versicherung_agentur_land")
            versicherung = VersicherungDE(
                gesellschaftsname=self._get_field_value(doc_fields, party_map, "versicherung_gesellschaft"),
                policennummer=self._get_field_value(doc_fields, party_map, "versicherung_schein_nr"),
                gruene_karte_nummer=self._get_field_value(doc_fields, party_map, "versicherung_gruene_karte_nr"),
                gueltig_ab=self._parse_date(self._get_field_value(doc_fields, party_map, "versicherung_gueltig_ab"), "Versicherung Gültig Ab"),
                gueltig_bis=self._parse_date(self._get_field_value(doc_fields, party_map, "versicherung_gueltig_bis"), "Versicherung Gültig Bis"),
                agentur=VersicherungDE.Agentur(
                    name=self._get_field_value(doc_fields, party_map, "versicherung_agentur_name"),
                    anschrift=self._get_field_value(doc_fields, party_map, "versicherung_agentur_anschrift"),
                    land=versicherung_agentur_land,
                    telefon_oder_email=self._get_field_value(doc_fields, party_map, "versicherung_agentur_telefon_email")
                ),
                sachschaeden_gedeckt=self._get_selection_mark_state(doc_fields, DE_FIELD_MAP[f"partei_versicherung_sachschaeden_gedeckt_ja_nein"].format(party=party_prefix), False)
            )
            
            fahrer_land = self._get_field_value(doc_fields, party_map, "fahrer_land")
            fahrer = FahrerDE(
                name=self._get_field_value(doc_fields, party_map, "fahrer_name"),
                vorname=self._get_field_value(doc_fields, party_map, "fahrer_vorname"),
                geburtsdatum=self._parse_date(self._get_field_value(doc_fields, party_map, "fahrer_geburtsdatum"), "Fahrer Geburtsdatum"),
                anschrift=self._get_field_value(doc_fields, party_map, "fahrer_anschrift"),
                postleitzahl=self._parse_postal_code(self._get_field_value(doc_fields, party_map, "fahrer_plz"), "PLZ Fahrer", country_code="DE" if fahrer_land == "Deutschland" else None),
                land=fahrer_land,
                telefon_oder_email=self._get_field_value(doc_fields, party_map, "fahrer_telefon_email"),
                fuehrerscheinnummer=self._get_field_value(doc_fields, party_map, "fahrer_fuehrerschein_nr"),
                kategorie=self._get_field_value(doc_fields, party_map, "fahrer_fuehrerschein_kategorie"),
                gueltig_bis=self._parse_date(self._get_field_value(doc_fields, party_map, "fahrer_fuehrerschein_gueltig_bis"), "Führerschein Gültig Bis")
            )
            
            aufprallpunkt = self._get_field_value(doc_fields, party_map, "aufprallpunkt")
            sichtbare_schaeden = self._get_field_value(doc_fields, party_map, "sichtbare_schaeden")
            umstaende = _populate_umstaende(party_prefix, doc_fields)
            bemerkungen = self._get_field_value(doc_fields, party_map, "bemerkungen")
            unterschrift = self._get_field_value(doc_fields, party_map, "unterschrift_name")
            
            return versicherungsnehmer, fahrzeug, versicherung, fahrer, aufprallpunkt, sichtbare_schaeden, umstaende, bemerkungen, unterschrift

        # --- Main DE Mapping --- 
        unfall_land = self._get_field_value(fields, DE_FIELD_MAP, "unfallland")
        unfalldetails = AccidentReportDE.Unfalldetails(
            datum=self._parse_date(self._get_field_value(fields, DE_FIELD_MAP, "unfalldatum"), "Unfalldatum"),
            uhrzeit=self._parse_time(self._get_field_value(fields, DE_FIELD_MAP, "unfallzeit"), "Unfallzeit"),
            oertlichkeit=self._get_field_value(fields, DE_FIELD_MAP, "oertlichkeit_strasse_nr"), # Assuming oertlichkeit is street+nr
            ort=self._get_field_value(fields, DE_FIELD_MAP, "unfallort_plz"), # Assuming ort is city+PLZ
            land=unfall_land,
            verletzungen=AccidentReportDE.Unfalldetails.Verletzungen(
                stattgefunden=self._get_selection_mark_state(fields, DE_FIELD_MAP["verletzte_ja_nein"], False),
                beschreibung=self._get_field_value(fields, DE_FIELD_MAP, "verletzte_namen_anschriften")
            ),
            sachschaeden=AccidentReportDE.Unfalldetails.Sachschaeden(
                andere_als_fahrzeuge_a_und_b=self._get_selection_mark_state(fields, DE_FIELD_MAP["sachschaeden_andere_kfz_ja_nein"], False),
                an_anderen_gegenstaenden=self._get_selection_mark_state(fields, DE_FIELD_MAP["sachschaeden_andere_gegenstaende_ja_nein"], False),
                beschreibung=self._get_field_value(fields, DE_FIELD_MAP, "sachschaeden_beschreibung")
            ),
            zeugen=self._extract_zeugen_de(fields, DE_FIELD_MAP) # Implement _extract_zeugen_de separately
        )

        vn_a, fzg_a, vers_a, fahr_a, auf_a, sch_a, ums_a, bem_a, unt_a = _populate_party_data("ParteiA", fields)
        vn_b, fzg_b, vers_b, fahr_b, auf_b, sch_b, ums_b, bem_b, unt_b = _populate_party_data("ParteiB", fields)
        
        fahrzeuge_data = AccidentReportDE.Fahrzeuge(
            A=AccidentReportDE.Fahrzeuge.ParteiDaten(
                versicherungsnehmer=vn_a,
                fahrzeug=fzg_a,
                versicherung=vers_a,
                fahrer=fahr_a,
                erster_aufprallpunkt=auf_a,
                sichtbare_schaeden=sch_a,
                umstaende=ums_a,
                bemerkungen=bem_a,
                unterschrieben_von=unt_a
            ) if vn_a else None,
            B=AccidentReportDE.Fahrzeuge.ParteiDaten(
                versicherungsnehmer=vn_b,
                fahrzeug=fzg_b,
                versicherung=vers_b,
                fahrer=fahr_b,
                erster_aufprallpunkt=auf_b,
                sichtbare_schaeden=sch_b,
                umstaende=ums_b,
                bemerkungen=bem_b,
                unterschrieben_von=unt_b
            ) if vn_b else None
        )
        
        unfallskizze = AccidentReportDE.Unfallskizze(
            beschreibung=self._get_field_value(fields, DE_FIELD_MAP, "skizze_beschreibung")
            # Layout, Pfeile, Positionen, Fahrbahnmarkierungen might come from layout_result if not in custom fields
        )
        
        abschluss = AccidentReportDE.Abschluss(
            haftungsanerkenntnis=self._get_selection_mark_state(fields, DE_FIELD_MAP["haftungsanerkennung_ja_nein"], False),
            hinweis=self._get_field_value(fields, DE_FIELD_MAP, "abschliessende_bemerkung")
        )

        report_data = {
            "unfallbericht": {
                "blatt": self._get_field_value(fields, DE_FIELD_MAP, "blatt"),
                "unfalldetails": unfalldetails,
                "fahrzeuge": fahrzeuge_data,
                "unfallskizze": unfallskizze,
                "abschluss": abschluss
            }
        }
        
        try:
            return AccidentReportDE(**report_data)
        except Exception as e:
            logger.error(f"Pydantic validation error during German mapping: {e}", exc_info=True)
            logger.error(f"Data passed to Pydantic: {report_data}")
            return None

    def _extract_zeugen_de(self, doc_fields: Dict[str, Any], field_map: Dict[str, str]) -> List[ZeugeDE]:
        """Extracts witness information for German reports."""
        zeugen_list = []
        # Try to get combined field first
        combined_zeugen_text = self._get_field_value(doc_fields, field_map, "zeugen_name_anschrift_telefon")
        if combined_zeugen_text:
            # Basic parsing: assume each witness is on a new line or separated by a clear delimiter
            # This is a very simplistic approach and might need significant refinement based on actual model output
            possible_witnesses = combined_zeugen_text.split('\n') # Or other delimiter
            for wit_text in possible_witnesses:
                if wit_text.strip():
                    # Further split name, address, phone - this is highly dependent on format
                    parts = wit_text.split(',') # Example delimiter
                    name_vorname = parts[0].strip() if len(parts) > 0 else None
                    # Split name and vorname if possible
                    name_parts = name_vorname.split(" ", 1) if name_vorname else [None, None]
                    name = name_parts[0] if len(name_parts) > 0 else None
                    vorname = name_parts[1] if len(name_parts) > 1 else None
                    
                    zeugen_list.append(ZeugeDE(
                        name=name,
                        vorname=vorname,
                        anschrift=parts[1].strip() if len(parts) > 1 else None,
                        telefon=parts[2].strip() if len(parts) > 2 else None
                        # PLZ, Land, Email would need more structured data or more fields
                    ))
            if zeugen_list:
                return zeugen_list

        # Fallback to individual witness fields if model supports it (e.g., Zeuge1_Name, Zeuge2_Name)
        # This example shows for one witness, extend for more if needed (e.g. loop 1 to N)
        zeuge1_name_val = self._get_field_value(doc_fields, field_map, "zeuge1_name")
        if zeuge1_name_val: # If at least one named witness field has a value
            # Assume up to N witnesses if your model is trained for Zeuge1_..., Zeuge2_..., etc.
            # For simplicity, this example only shows Zeuge1.
            # You might loop here for ZeugeX_... fields.
            zeuge1_land = self._get_field_value(doc_fields, field_map, "zeuge1_land")
            zeuge1 = ZeugeDE(
                name=zeuge1_name_val,
                vorname=self._get_field_value(doc_fields, field_map, "zeuge1_vorname"),
                anschrift=self._get_field_value(doc_fields, field_map, "zeuge1_anschrift"),
                postleitzahl=self._parse_postal_code(self._get_field_value(doc_fields, field_map, "zeuge1_plz"), "PLZ Zeuge1", country_code="DE" if zeuge1_land == "Deutschland" else None),
                land=zeuge1_land,
                telefon=self._get_field_value(doc_fields, field_map, "zeuge1_telefon"),
                email=self._get_field_value(doc_fields, field_map, "zeuge1_email")
            )
            zeugen_list.append(zeuge1)
        
        return zeugen_list

    def _map_to_accident_report_en(
        self, 
        custom_result: Optional[Any], 
        layout_result: Optional[Any]
    ) -> Optional[AccidentReportEN]:
        """Maps Azure Form Recognizer results to AccidentReportEN Pydantic model."""
        if not custom_result or not custom_result.documents:
            logger.warning("No custom model documents found for English mapping.")
            return None
        doc = custom_result.documents[0]
        fields = doc.fields
        # IMPORTANT: Replace these with the *actual* field names from your trained Azure model for English forms
        EN_FIELD_MAP = {
            # Main (AccidentStatement)
            "sheet": "General_SheetIdentifier",
            # AccidentDetails (1-5)
            "date": "AccidentDetails_Date",
            "time": "AccidentDetails_Time",
            "locality": "AccidentDetails_Locality", # Street address or general area
            "place": "AccidentDetails_Place",    # City/Town/Village
            "country": "AccidentDetails_Country",
            "injuries_occurred": "Injuries_Occurred", # SelectionMark
            "injuries_description": "Injuries_Description",
            "material_damage_other_than_vehicles": "MaterialDamage_OtherThanVehiclesAB", # SelectionMark
            "material_damage_other_object": "MaterialDamage_OtherObjects", # SelectionMark
            "material_damage_description": "MaterialDamage_Description",
            # Witnesses (5) - Similar to German, can be combined or individual
            "witness1_name": "Witness1_Name",
            "witness1_first_name": "Witness1_FirstName",
            "witness1_address": "Witness1_Address",
            "witness1_postal_code": "Witness1_PostalCode",
            "witness1_country": "Witness1_Country",
            "witness1_telephone": "Witness1_Telephone",
            "witness1_email": "Witness1_Email",
            # Vehicles A & B Sections (Common fields prefixed with PartyA_ or PartyB_)
            # Insured/Policyholder (6)
            "party_policyholder_name": "{party}_Policyholder_Name",
            "party_policyholder_first_name": "{party}_Policyholder_FirstName",
            "party_policyholder_address": "{party}_Policyholder_Address",
            "party_policyholder_postal_code": "{party}_Policyholder_PostalCode",
            "party_policyholder_country": "{party}_Policyholder_Country",
            "party_policyholder_telephone_email": "{party}_Policyholder_TelephoneEmail",
            # Vehicle (7)
            "party_vehicle_motor_make_type": "{party}_Vehicle_Motor_MakeType",
            "party_vehicle_motor_reg_no": "{party}_Vehicle_Motor_RegistrationNumber",
            "party_vehicle_motor_country_reg": "{party}_Vehicle_Motor_CountryOfRegistration",
            "party_vehicle_trailer_reg_no": "{party}_Vehicle_Trailer_RegistrationNumber",
            "party_vehicle_trailer_country_reg": "{party}_Vehicle_Trailer_CountryOfRegistration",
            # Insurance (8)
            "party_insurance_company_name": "{party}_Insurance_CompanyName",
            "party_insurance_policy_no": "{party}_Insurance_PolicyNumber",
            "party_insurance_green_card_no": "{party}_Insurance_GreenCardNumber",
            "party_insurance_valid_from": "{party}_Insurance_ValidFrom",
            "party_insurance_valid_to": "{party}_Insurance_ValidTo",
            "party_insurance_agency_name": "{party}_Insurance_Agency_Name",
            "party_insurance_agency_address": "{party}_Insurance_Agency_Address",
            "party_insurance_agency_country": "{party}_Insurance_Agency_Country",
            "party_insurance_agency_telephone_email": "{party}_Insurance_Agency_TelephoneEmail",
            "party_insurance_material_damage_covered": "{party}_Insurance_MaterialDamageCovered", # SelectionMark
            # Driver (9)
            "party_driver_name": "{party}_Driver_Name",
            "party_driver_first_name": "{party}_Driver_FirstName",
            "party_driver_dob": "{party}_Driver_DateOfBirth",
            "party_driver_address": "{party}_Driver_Address",
            "party_driver_postal_code": "{party}_Driver_PostalCode",
            "party_driver_country": "{party}_Driver_Country",
            "party_driver_telephone_email": "{party}_Driver_TelephoneEmail",
            "party_driver_licence_no": "{party}_Driver_DrivingLicenceNumber",
            "party_driver_licence_category": "{party}_Driver_DrivingLicenceCategory",
            "party_driver_licence_valid_until": "{party}_Driver_DrivingLicenceValidUntil",
            # Initial Impact Point (10)
            "party_initial_impact_point": "{party}_InitialImpactPoint",
            # Visible Damage (11)
            "party_visible_damage": "{party}_VisibleDamage",
            # Circumstances (12) - Selection marks
            "party_circ_parked_stopped": "{party}_Circumstance_ParkedStopped",
            "party_circ_leaving_parking": "{party}_Circumstance_LeavingParking",
            "party_circ_entering_parking": "{party}_Circumstance_EnteringParking",
            "party_circ_emerging_car": "{party}_Circumstance_EmergingCarParkPrivateDriveway",
            "party_circ_entering_car": "{party}_Circumstance_EnteringCarParkPrivateDriveway",
            "party_circ_entering_roundabout": "{party}_Circumstance_EnteringRoundabout",
            "party_circ_circulating_roundabout": "{party}_Circumstance_CirculatingRoundabout",
            "party_circ_striking_rear": "{party}_Circumstance_StrikingRearSameDirectionLane",
            "party_circ_going_same_direction": "{party}_Circumstance_GoingSameDirectionDifferentLane",
            "party_circ_changing_lanes": "{party}_Circumstance_ChangingLanes",
            "party_circ_overtaking": "{party}_Circumstance_Overtaking",
            "party_circ_turning_right": "{party}_Circumstance_TurningRight",
            "party_circ_turning_left": "{party}_Circumstance_TurningLeft",
            "party_circ_reversing": "{party}_Circumstance_Reversing",
            "party_circ_encroaching_lane": "{party}_Circumstance_EncroachingOppositeLane",
            "party_circ_coming_right": "{party}_Circumstance_ComingFromRightJunction",
            "party_circ_had_not_observed": "{party}_Circumstance_HadNotObservedPriorityRedLight",
            "party_circ_boxes_marked_total": "{party}_Circumstance_BoxesMarkedTotal", # Number field
            # Remarks (14)
            "party_remarks": "{party}_Remarks",
            "party_signed_by": "{party}_SignedBy", # Name if visible near signature
            # Impact Sketch (13)
            "sketch_description": "Sketch_Description",
            "sketch_layout": "Sketch_Layout",
            "sketch_arrows": "Sketch_Arrows",
            "sketch_positions": "Sketch_Positions",
            "sketch_road_lines": "Sketch_RoadLines",
            # Final (Bottom of form)
            "final_liability_admission": "Final_LiabilityAdmission", # SelectionMark
            "final_note": "Final_Note"
        }

        def get_party_field_map_en(party_prefix: str) -> Dict[str, str]:
            party_map = {}
            for key, value in EN_FIELD_MAP.items():
                if "{party}" in value:
                    party_map[key.replace("party_", "")] = value.format(party=party_prefix)
            return party_map

        def _populate_circumstances_en(party_prefix: str, doc_fields: Dict[str, Any]) -> CircumstancesEN:
            circ_map = get_party_field_map_en(party_prefix)
            data = {}
            for pydantic_key in CircumstancesEN.model_fields.keys():
                map_key_prefix = "circ_"
                full_map_key = f"party_{map_key_prefix}{pydantic_key}"
                form_recognizer_field_name = EN_FIELD_MAP.get(full_map_key)
                if form_recognizer_field_name:
                    actual_fr_field_name = form_recognizer_field_name.format(party=party_prefix)
                    data[pydantic_key] = self._get_selection_mark_state(doc_fields, actual_fr_field_name, False)
            
            total_val_str = self._get_field_value(doc_fields, circ_map, "circ_boxes_marked_total", "0")
            try:
                data["boxes_marked_total"] = int(total_val_str) if total_val_str else 0
            except ValueError:
                data["boxes_marked_total"] = 0
            return CircumstancesEN(**data)

        def _populate_party_details_en(party_prefix: str, doc_fields: Dict[str, Any]) -> Tuple[Optional[PolicyholderEN], Optional[VehicleEN], Optional[InsuranceEN], Optional[DriverEN], Optional[str], Optional[str], Optional[CircumstancesEN], Optional[str], Optional[str]]:
            party_map = get_party_field_map_en(party_prefix)
            policyholder_country = self._get_field_value(doc_fields, party_map, "policyholder_country")
            policyholder = PolicyholderEN(
                name=self._get_field_value(doc_fields, party_map, "policyholder_name"),
                first_name=self._get_field_value(doc_fields, party_map, "policyholder_first_name"),
                address=self._get_field_value(doc_fields, party_map, "policyholder_address"),
                postal_code=self._parse_postal_code(self._get_field_value(doc_fields, party_map, "policyholder_postal_code"), "Policyholder Postal Code"),
                country=policyholder_country,
                telephone_or_email=self._get_field_value(doc_fields, party_map, "policyholder_telephone_email")
            )

            vehicle = VehicleEN(
                motor=VehicleEN.Motor(
                    make_type=self._get_field_value(doc_fields, party_map, "vehicle_motor_make_type"),
                    registration_number=self._get_field_value(doc_fields, party_map, "vehicle_motor_reg_no"),
                    country_of_registration=self._get_field_value(doc_fields, party_map, "vehicle_motor_country_reg")
                ),
                trailer=VehicleEN.Trailer(
                    registration_number=self._get_field_value(doc_fields, party_map, "vehicle_trailer_reg_no"),
                    country_of_registration=self._get_field_value(doc_fields, party_map, "vehicle_trailer_country_reg")
                )
            )
            
            insurance_agency_country = self._get_field_value(doc_fields, party_map, "insurance_agency_country")
            insurance = InsuranceEN(
                company_name=self._get_field_value(doc_fields, party_map, "insurance_company_name"),
                policy_number=self._get_field_value(doc_fields, party_map, "insurance_policy_no"),
                green_card_number=self._get_field_value(doc_fields, party_map, "insurance_green_card_no"),
                valid_from=self._parse_date(self._get_field_value(doc_fields, party_map, "insurance_valid_from"), "Insurance Valid From"),
                valid_to=self._parse_date(self._get_field_value(doc_fields, party_map, "insurance_valid_to"), "Insurance Valid To"),
                agency=InsuranceEN.Agency(
                    name=self._get_field_value(doc_fields, party_map, "insurance_agency_name"),
                    address=self._get_field_value(doc_fields, party_map, "insurance_agency_address"),
                    country=insurance_agency_country,
                    telefon_oder_email=self._get_field_value(doc_fields, party_map, "insurance_agency_telephone_email")
                ),
                material_damage_covered=self._get_selection_mark_state(doc_fields, EN_FIELD_MAP[f"party_insurance_material_damage_covered"].format(party=party_prefix), False)
            )

            driver_country = self._get_field_value(doc_fields, party_map, "driver_country")
            driver = DriverEN(
                name=self._get_field_value(doc_fields, party_map, "driver_name"),
                first_name=self._get_field_value(doc_fields, party_map, "driver_first_name"),
                date_of_birth=self._parse_date(self._get_field_value(doc_fields, party_map, "driver_dob"), "Driver Date of Birth"),
                address=self._get_field_value(doc_fields, party_map, "driver_address"),
                postal_code=self._parse_postal_code(self._get_field_value(doc_fields, party_map, "driver_postal_code"), "Driver Postal Code"),
                country=driver_country,
                telephone_or_email=self._get_field_value(doc_fields, party_map, "driver_telephone_email"),
                driving_licence_number=self._get_field_value(doc_fields, party_map, "driver_licence_no"),
                category=self._get_field_value(doc_fields, party_map, "driver_licence_category"),
                valid_until=self._parse_date(self._get_field_value(doc_fields, party_map, "driver_licence_valid_until"), "Licence Valid Until")
            )
            
            initial_impact_point = self._get_field_value(doc_fields, party_map, "initial_impact_point")
            visible_damage = self._get_field_value(doc_fields, party_map, "visible_damage")
            circumstances = _populate_circumstances_en(party_prefix, doc_fields)
            remarks = self._get_field_value(doc_fields, party_map, "remarks")
            signed_by = self._get_field_value(doc_fields, party_map, "signed_by")

            return policyholder, vehicle, insurance, driver, initial_impact_point, visible_damage, circumstances, remarks, signed_by

        # --- Main EN Mapping ---
        accident_details = AccidentReportEN.AccidentDetails(
            date=self._parse_date(self._get_field_value(fields, EN_FIELD_MAP, "date"), "Accident Date"),
            time=self._parse_time(self._get_field_value(fields, EN_FIELD_MAP, "time"), "Accident Time"),
            locality=self._get_field_value(fields, EN_FIELD_MAP, "locality"),
            place=self._get_field_value(fields, EN_FIELD_MAP, "place"),
            country=self._get_field_value(fields, EN_FIELD_MAP, "country"),
            injuries=AccidentReportEN.AccidentDetails.Injuries(
                occurred=self._get_selection_mark_state(fields, EN_FIELD_MAP["injuries_occurred"], False),
                description=self._get_field_value(fields, EN_FIELD_MAP, "injuries_description")
            ),
            material_damage=AccidentReportEN.AccidentDetails.MaterialDamage(
                other_than_vehicles=self._get_selection_mark_state(fields, EN_FIELD_MAP["material_damage_other_than_vehicles"], False),
                other_object=self._get_selection_mark_state(fields, EN_FIELD_MAP["material_damage_other_object"], False),
                description=self._get_field_value(fields, EN_FIELD_MAP, "material_damage_description")
            ),
            witnesses=self._extract_witnesses_en(fields, EN_FIELD_MAP)
        )

        ph_a, veh_a, ins_a, drv_a, imp_a, dmg_a, circ_a, rem_a, sign_a = _populate_party_details_en("PartyA", fields)
        ph_b, veh_b, ins_b, drv_b, imp_b, dmg_b, circ_b, rem_b, sign_b = _populate_party_details_en("PartyB", fields)
        
        vehicles_data = AccidentReportEN.Vehicles(
            A=AccidentReportEN.Vehicles.PartyDetails(
                insured_policyholder=ph_a, vehicle=veh_a, insurance=ins_a, driver=drv_a,
                initial_impact_point=imp_a, visible_damage=dmg_a, circumstances=circ_a,
                remarks=rem_a, signed_by=sign_a
            ) if ph_a else None,
            B=AccidentReportEN.Vehicles.PartyDetails(
                insured_policyholder=ph_b, vehicle=veh_b, insurance=ins_b, driver=drv_b,
                initial_impact_point=imp_b, visible_damage=dmg_b, circumstances=circ_b,
                remarks=rem_b, signed_by=sign_b
            ) if ph_b else None
        )

        impact_sketch = AccidentReportEN.ImpactSketch(
            description=self._get_field_value(fields, EN_FIELD_MAP, "sketch_description"),
            layout=self._get_field_value(fields, EN_FIELD_MAP, "sketch_layout"),
            arrows=self._get_field_value(fields, EN_FIELD_MAP, "sketch_arrows"),
            positions=self._get_field_value(fields, EN_FIELD_MAP, "sketch_positions"),
            road_lines=self._get_field_value(fields, EN_FIELD_MAP, "sketch_road_lines")
        )

        final_data = AccidentReportEN.Final(
            liability_admission=self._get_selection_mark_state(fields, EN_FIELD_MAP["final_liability_admission"], False),
            note=self._get_field_value(fields, EN_FIELD_MAP, "final_note")
        )

        report_data = {
            "accident_statement": {
                "sheet": self._get_field_value(fields, EN_FIELD_MAP, "sheet"),
                "accident_details": accident_details,
                "vehicles": vehicles_data,
                "impact_sketch": impact_sketch,
                "final": final_data
            }
        }
        try:
            return AccidentReportEN(**report_data)
        except Exception as e:
            logger.error(f"Pydantic validation error during English mapping: {e}", exc_info=True)
            logger.error(f"Data passed to Pydantic: {report_data}")
            return None

    def _extract_witnesses_en(self, doc_fields: Dict[str, Any], field_map: Dict[str, str]) -> List[WitnessEN]:
        """Extracts witness information for English reports."""
        witnesses_list = []
        # Example for one witness, extend or make dynamic for multiple if model supports Witness1, Witness2 etc.
        wit1_name_val = self._get_field_value(doc_fields, field_map, "witness1_name")
        if wit1_name_val:
            wit1_country = self._get_field_value(doc_fields, field_map, "witness1_country")
            witness1 = WitnessEN(
                name=wit1_name_val,
                first_name=self._get_field_value(doc_fields, field_map, "witness1_first_name"),
                address=self._get_field_value(doc_fields, field_map, "witness1_address"),
                postal_code=self._parse_postal_code(self._get_field_value(doc_fields, field_map, "witness1_postal_code"), "Witness1 Postal Code"),
                country=wit1_country,
                telephone=self._get_field_value(doc_fields, field_map, "witness1_telephone"),
                email=self._get_field_value(doc_fields, field_map, "witness1_email")
            )
            witnesses_list.append(witness1)
        # Add similar blocks for Witness2, Witness3 if your custom model extracts them as separate fields
        return witnesses_list

    def _map_to_accident_report_nl(
        self, 
        custom_result: Optional[Any], 
        layout_result: Optional[Any]
    ) -> Optional[AccidentReportNL]:
        """Maps Azure Form Recognizer results to AccidentReportNL Pydantic model."""
        if not custom_result or not custom_result.documents:
            logger.warning("No custom model documents found for Dutch mapping.")
            return None
        doc = custom_result.documents[0]
        fields = doc.fields
        
        # MINIMAL PLACEHOLDER - USER MUST UPDATE THIS EXTENSIVELY
        NL_FIELD_MAP = {
            "blad": "Algemeen_Bladnummer",
            "datum": "Ongeval_Datum",
            "partij_omst_totaal_aangekruiste_vakjes": "{party}_Omstandigheid_TotaalAangekruisteVakjes",
            # Add other essential, non-party specific fields here if needed for basic structure
        }

        # Dynamically populate NL circumstances field map entries based on Pydantic model OmstandighedenNL
        # This loop is kept for when the user populates NL_FIELD_MAP more fully
        for field_key in OmstandighedenNL.model_fields.keys():
            if field_key != "totaal_aangekruiste_vakjes" and f"partij_omst_{field_key}" not in NL_FIELD_MAP:
                fr_field_name_suffix = ''.join(word.capitalize() for word in field_key.split('_'))
                # Only add if a party placeholder is intended, otherwise define specific fields above
                # NL_FIELD_MAP[f"partij_omst_{field_key}"] = f"{{party}}_Omstandigheid_{fr_field_name_suffix}"
                # For now, this dynamic part will likely not add much due to minimal NL_FIELD_MAP
                pass 

        def get_party_field_map_nl(party_prefix: str) -> Dict[str, str]:
            party_map = {}
            # USER MUST ADD party-specific entries to NL_FIELD_MAP for this to work
            # Example: NL_FIELD_MAP["partij_verzekeringnemer_naam"] = "{party}_Verzekeringnemer_Naam"
            for key, value in NL_FIELD_MAP.items():
                if "{party}" in value:
                    party_map[key.replace("partij_", "")] = value.format(party=party_prefix)
                elif not key.startswith("partij_") and party_prefix: # For non-party specific general fields
                    party_map[key] = value
            return party_map

        def _populate_omstandigheden_nl(party_prefix: str, doc_fields: Dict[str, Any]) -> OmstandighedenNL:
            omst_map = get_party_field_map_nl(party_prefix)
            data = {}
            for pydantic_key in OmstandighedenNL.model_fields.keys():
                map_key_prefix = "omst_" 
                full_map_key = f"partij_{map_key_prefix}{pydantic_key}"
                form_recognizer_field_name = NL_FIELD_MAP.get(full_map_key) 
                
                # If not found with party prefix, try direct pydantic key if it was in NL_FIELD_MAP
                if not form_recognizer_field_name:
                    form_recognizer_field_name = NL_FIELD_MAP.get(pydantic_key)
                
                if form_recognizer_field_name: # Check if key exists
                    actual_fr_field_name = form_recognizer_field_name.format(party=party_prefix) if "{party}" in form_recognizer_field_name else form_recognizer_field_name
                    
                    if pydantic_key == "totaal_aangekruiste_vakjes":
                        # Pass the direct mapping for this field to _get_field_value
                        temp_map = {pydantic_key: actual_fr_field_name}
                        total_val_str = self._get_field_value(doc_fields, temp_map, pydantic_key, "0")
                        try:
                            data[pydantic_key] = int(total_val_str) if total_val_str else 0
                        except ValueError:
                            logger.warning(f"Could not parse {pydantic_key} '{total_val_str}' to int for {party_prefix}. Defaulting to 0.")
                            data[pydantic_key] = 0
                    else:
                        data[pydantic_key] = self._get_selection_mark_state(doc_fields, actual_fr_field_name, False)
                elif pydantic_key == "totaal_aangekruiste_vakjes":
                     data[pydantic_key] = 0
                # else: logger.debug(f"Pydantic key {pydantic_key} not mapped for OmstandighedenNL for {party_prefix}")

            return OmstandighedenNL(**data)

        def _populate_party_details_nl(party_prefix: str, doc_fields: Dict[str, Any]) -> Tuple[Optional[VerzekeringnemerNL], Optional[VoertuigNL], Optional[VerzekeringNL], Optional[BestuurderNL], Optional[str], Optional[str], Optional[OmstandighedenNL], Optional[str], Optional[str]]:
            party_map = get_party_field_map_nl(party_prefix)
            # USER MUST ENSURE party_map gets populated correctly by defining NL_FIELD_MAP above
            # For now, these will likely be None due to minimal NL_FIELD_MAP

            verzekeringnemer_land_key = "verzekeringnemer_land"
            verzekeringnemer_land = self._get_field_value(doc_fields, party_map, verzekeringnemer_land_key)
            verzekeringnemer = VerzekeringnemerNL(
                naam=self._get_field_value(doc_fields, party_map, "verzekeringnemer_naam"),
                voornaam=self._get_field_value(doc_fields, party_map, "verzekeringnemer_voornaam"),
                adres=self._get_field_value(doc_fields, party_map, "verzekeringnemer_adres"),
                postcode=self._parse_postal_code(self._get_field_value(doc_fields, party_map, "verzekeringnemer_postcode"), f"{party_prefix} Verzekeringnemer Postcode", country_code="NL" if verzekeringnemer_land == "Nederland" else None),
                land=verzekeringnemer_land,
                telefoon_of_email=self._get_field_value(doc_fields, party_map, "verzekeringnemer_telefoon_email")
            )
            # ... (similar placeholders for Voertuig, Verzekering, Bestuurder) ...
            voertuig = VoertuigNL() # Placeholder
            verzekering = VerzekeringNL() # Placeholder
            bestuurder = BestuurderNL() # Placeholder
            
            eerste_aanrijdingspunt = self._get_field_value(doc_fields, party_map, "eerste_aanrijdingspunt")
            zichtbare_schade = self._get_field_value(doc_fields, party_map, "zichtbare_schade")
            omstandigheden = _populate_omstandigheden_nl(party_prefix, doc_fields)
            opmerkingen = self._get_field_value(doc_fields, party_map, "opmerkingen")
            ondertekend_door = self._get_field_value(doc_fields, party_map, "ondertekend_door")

            # Check if any vital info was extracted for the policyholder to consider party data valid
            if not verzekeringnemer.naam and not verzekeringnemer.adres:
                 # return None, None, None, None, None, None, None, None, None # Python 3.7 compatibility
                 return (None,) * 9 

            return verzekeringnemer, voertuig, verzekering, bestuurder, eerste_aanrijdingspunt, zichtbare_schade, omstandigheden, opmerkingen, ondertekend_door

        # --- Main NL Mapping ---
        ongevaldetails_land_key = "land"
        ongevaldetails_land = self._get_field_value(fields, NL_FIELD_MAP, ongevaldetails_land_key)
        ongevaldetails = AccidentReportNL.Ongevaldetails(
            datum=self._parse_date(self._get_field_value(fields, NL_FIELD_MAP, "datum"), "Ongeval Datum"),
            tijd=self._parse_time(self._get_field_value(fields, NL_FIELD_MAP, "tijd"), "Ongeval Tijd"),
            # ... (other Ongevaldetails fields with placeholders if NL_FIELD_MAP is minimal) ...
            plaats_locatie=self._get_field_value(fields, NL_FIELD_MAP, "plaats_locatie"),
            plaats_exact=self._get_field_value(fields, NL_FIELD_MAP, "plaats_exact"),
            land=ongevaldetails_land,
            letsel=AccidentReportNL.Ongevaldetails.Letsel(
                ja=self._get_selection_mark_state(fields, NL_FIELD_MAP.get("letsel_ja", "Letsel_Ja_NonExistent"), False),
                beschrijving=self._get_field_value(fields, NL_FIELD_MAP, "letsel_beschrijving")
            ),
            materiele_schade=AccidentReportNL.Ongevaldetails.MaterieleSchade(), # Placeholder
            getuigen=self._extract_getuigen_nl(fields, NL_FIELD_MAP) # Placeholder for now
        )

        partij_a_data = _populate_party_details_nl("PartijA", fields)
        partij_b_data = _populate_party_details_nl("PartijB", fields)
        
        voertuigen_data = AccidentReportNL.Voertuigen(
            A=AccidentReportNL.Voertuigen.PartijGegevens(
                verzekeringnemer=partij_a_data[0], voertuig=partij_a_data[1], verzekering=partij_a_data[2], bestuurder=partij_a_data[3],
                eerste_aanrijdingspunt=partij_a_data[4], zichtbare_schade=partij_a_data[5], omstandigheden=partij_a_data[6],
                opmerkingen=partij_a_data[7], ondertekend_door=partij_a_data[8]
            ) if partij_a_data[0] else None,
            B=AccidentReportNL.Voertuigen.PartijGegevens(
                verzekeringnemer=partij_b_data[0], voertuig=partij_b_data[1], verzekering=partij_b_data[2], bestuurder=partij_b_data[3],
                eerste_aanrijdingspunt=partij_b_data[4], zichtbare_schade=partij_b_data[5], omstandigheden=partij_b_data[6],
                opmerkingen=partij_b_data[7], ondertekend_door=partij_b_data[8]
            ) if partij_b_data[0] else None
        )
        # ... (placeholders for aanrijdingsschets, slotverklaring) ...
        aanrijdingsschets = AccidentReportNL.Aanrijdingsschets()
        slotverklaring = AccidentReportNL.Slotverklaring()

        report_data = {
            "ongevalsaangifte": {
                "blad": self._get_field_value(fields, NL_FIELD_MAP, "blad"),
                "ongevaldetails": ongevaldetails,
                "voertuigen": voertuigen_data,
                "aanrijdingsschets": aanrijdingsschets,
                "slotverklaring": slotverklaring
            }
        }
        try:
            return AccidentReportNL(**report_data)
        except Exception as e:
            logger.error(f"Pydantic validation error during Dutch mapping: {e}", exc_info=True)
            logger.error(f"Data passed to Pydantic: {report_data}")
            return None

    def _extract_getuigen_nl(self, doc_fields: Dict[str, Any], field_map: Dict[str, str]) -> List[GetuigeNL]:
        """Extracts witness information for Dutch reports."""
        # Placeholder - USER MUST UPDATE NL_FIELD_MAP for this to work
        getuigen_list = []
        wit1_naam_key = "getuige1_naam"
        wit1_naam_val = self._get_field_value(doc_fields, field_map, wit1_naam_key)
        if wit1_naam_val:
            wit1_land_key = "getuige1_land"
            wit1_land = self._get_field_value(doc_fields, field_map, wit1_land_key)
            getuige1 = GetuigeNL(
                naam=wit1_naam_val,
                voornaam=self._get_field_value(doc_fields, field_map, "getuige1_voornaam"),
                adres=self._get_field_value(doc_fields, field_map, "getuige1_adres"),
                postcode=self._parse_postal_code(self._get_field_value(doc_fields, field_map, "getuige1_postcode"), "Getuige1 Postcode", country_code="NL" if wit1_land == "Nederland" else None),
                land=wit1_land,
                telefoon=self._get_field_value(doc_fields, field_map, "getuige1_telefoon"),
                email=self._get_field_value(doc_fields, field_map, "getuige1_email")
            )
            getuigen_list.append(getuige1)
        return getuigen_list

async def close_client(client: Optional[AzureRecognizerClient]):
    if client and client.document_analysis_client:
        logger.info("Closing Azure DocumentAnalysisClient.")
        await client.document_analysis_client.close()
        logger.info("Azure DocumentAnalysisClient closed.") 