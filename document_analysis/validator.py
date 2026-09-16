import json
import logging
from pathlib import Path
from typing import Dict, Any, List

from document_analysis.report_schema import Measurement

logger = logging.getLogger(__name__)

ONTOLOGY_PATH = Path(__file__).parent / "test_ontology.json"
_ONTOLOGY_DATA = None

def get_ontology() -> Dict[str, Any]:
    global _ONTOLOGY_DATA
    if _ONTOLOGY_DATA is None:
        try:
            with open(ONTOLOGY_PATH, "r", encoding="utf-8") as f:
                _ONTOLOGY_DATA = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load ontology: {e}")
            _ONTOLOGY_DATA = {}
    return _ONTOLOGY_DATA

def is_valid_unit_for_biomarker(biomarker: str, unit: str) -> bool:
    if not unit:
        return True # Can't invalidate if missing
    ontology = get_ontology()
    for category, tests in ontology.items():
        for test in tests:
            if biomarker.lower() == test["canonical_name"].lower():
                valid_units = [u.lower() for u in test.get("units", [])]
                if unit.lower() in valid_units:
                    return True
                # Allow minor variations like removing spaces
                if unit.lower().replace(" ", "") in [u.replace(" ", "") for u in valid_units]:
                    return True
    return False

def calculate_classification(value: float, ref_low: float = None, ref_high: float = None) -> str:
    """Deterministically classify value based on bounds."""
    if ref_low is None and ref_high is None:
        return "UNKNOWN"
        
    if ref_low is not None and value < ref_low:
        return "LOW"
    if ref_high is not None and value > ref_high:
        return "HIGH"
        
    return "NORMAL"

def validate_measurement(raw_data: Dict[str, Any]) -> Measurement:
    """
    Validates the measurement dict and calculates classification deterministically.
    Throws ValueError if it violates deterministic arithmetic or ontology constraints.
    """
    biomarker = raw_data.get("biomarker")
    value = raw_data.get("value")
    
    if not biomarker:
        raise ValueError("Missing biomarker name")
    
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Value is not numeric: {value}")
        
    ref_low = raw_data.get("ref_low")
    if ref_low is not None:
        try:
            ref_low = float(ref_low)
        except ValueError:
            ref_low = None
            
    ref_high = raw_data.get("ref_high")
    if ref_high is not None:
        try:
            ref_high = float(ref_high)
        except ValueError:
            ref_high = None
            
    if ref_low is not None and ref_high is not None:
        if ref_low > ref_high:
            # Maybe swapped? Auto-correct it deterministically if we want, or just reject
            ref_low, ref_high = ref_high, ref_low
            
    classification = calculate_classification(value, ref_low, ref_high)
    
    # If the LLM provided a classification, we override it deterministically
    # (or reject if it was wrong, but it's safer to just correct it)
    
    unit = raw_data.get("unit")
    if unit:
        unit = unit.strip()
        
    if raw_data.get("extraction_method") == "llm_fallback":
        # Strict ontology validation for LLM fallback
        if not is_valid_unit_for_biomarker(biomarker, unit):
            raise ValueError(f"LLM hallucinated invalid unit {unit} for {biomarker}")
            
    return Measurement(
        biomarker=biomarker,
        value=value,
        unit=unit,
        ref_low=ref_low,
        ref_high=ref_high,
        classification=classification,
        page=int(raw_data.get("page", 1)),
        source_text=raw_data.get("source_text", ""),
        extraction_method=raw_data.get("extraction_method", "deterministic"),
        extraction_confidence=float(raw_data.get("extraction_confidence", 0.5))
    )
