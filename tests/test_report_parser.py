import pytest
from document_analysis.report_parser import parse_medical_report

def test_parse_medical_report_basic():
    text = """
    Patient Name: John Doe
    Hemoglobin: 11.2 g/dL
    Reference Range: 12.0 - 16.0 g/dL
    
    Glucose Fasting: 126 mg/dL
    Reference Range: 70 - 99 mg/dL
    
    TSH: 3.1 mIU/L
    Reference Range: 0.4 - 4.0 mIU/L
    """
    
    pages = [{"page": 1, "text": text}]
    measurements = parse_medical_report(pages)
    
    assert len(measurements) >= 3
    
    # Check Hemoglobin
    hb = next(m for m in measurements if "Hemoglobin" in m["biomarker"] or "hemoglobin" in m["biomarker"].lower())
    assert float(hb["value"]) == 11.2
    assert "g/dL" in hb["unit"]
    assert hb["classification"] == "LOW"
    
    # Check Glucose
    glu = next(m for m in measurements if "Glucose" in m["biomarker"] or "glucose" in m["biomarker"].lower())
    assert float(glu["value"]) == 126
    assert "mg/dL" in glu["unit"]
    assert glu["classification"] == "HIGH"
    
    # Check TSH
    tsh = next(m for m in measurements if "TSH" in m["biomarker"] or "tsh" in m["biomarker"].lower())
    assert float(tsh["value"]) == 3.1
    assert "mIU/L" in tsh["unit"]
    assert tsh["classification"] == "NORMAL"

def test_parse_medical_report_empty():
    text = "This is a general health document about eating apples."
    pages = [{"page": 1, "text": text}]
    measurements = parse_medical_report(pages)
    assert measurements == []
