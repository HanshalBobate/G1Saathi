import pytest
from document_analysis.report_parser import parse_medical_report, extract_measurements_deterministic
from document_analysis.report_schema import Measurement

def test_basic_measurement_extraction():
    text = "Hemoglobin 11.2 g/dL Reference Range: 12.0 - 16.0"
    pages = [{"page": 1, "text": text}]
    results = parse_medical_report(pages)
    assert len(results) == 1
    m = results[0]
    assert m["biomarker"] == "Hemoglobin"
    assert m["value"] == 11.2
    assert m["unit"] == "g/dL"
    assert m["ref_low"] == 12.0
    assert m["ref_high"] == 16.0
    assert m["classification"] == "LOW"
    assert m["page"] == 1
    assert m["extraction_method"] == "deterministic"

def test_alias_extraction():
    text = "Hb 13.5 g/dL 12.0 - 16.0"
    pages = [{"page": 1, "text": text}]
    results = parse_medical_report(pages)
    assert len(results) == 1
    m = results[0]
    assert m["biomarker"] == "Hemoglobin"
    assert m["value"] == 13.5
    assert m["classification"] == "NORMAL"

def test_one_sided_range():
    text = "HbA1c 7.2 % < 5.7"
    pages = [{"page": 1, "text": text}]
    results = parse_medical_report(pages)
    assert len(results) == 1
    m = results[0]
    assert m["biomarker"] == "HbA1c"
    assert m["value"] == 7.2
    assert m["ref_low"] is None
    assert m["ref_high"] == 5.7
    assert m["classification"] == "HIGH"

def test_no_hallucinated_values():
    text = "The patient was told their Hemoglobin was fine but no numbers were printed."
    pages = [{"page": 1, "text": text}]
    results = parse_medical_report(pages)
    assert len(results) == 0

def test_unknown_classification():
    text = "Vitamin D 18 ng/mL"
    pages = [{"page": 1, "text": text}]
    results = parse_medical_report(pages)
    assert len(results) == 1
    m = results[0]
    assert m["ref_low"] is None
    assert m["ref_high"] is None
    assert m["classification"] == "UNKNOWN"

def test_multiple_measurements():
    text = "WBC 7200 /uL 4000-11000\nPlatelets 250000 /uL 150000-450000"
    pages = [{"page": 1, "text": text}]
    results = parse_medical_report(pages)
    assert len(results) == 2
    assert results[0]["biomarker"] == "WBC"
    assert results[1]["biomarker"] == "Platelets"
