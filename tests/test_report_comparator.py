import pytest
from document_analysis.report_comparator import compare_reports

def test_comparator_same_biomarker():
    report_a = [{"biomarker": "Hemoglobin", "value": 10.5, "unit": "g/dL"}]
    report_b = [{"biomarker": "Hemoglobin", "value": 11.2, "unit": "g/dL"}]
    
    trends = compare_reports(report_a, report_b)
    assert len(trends) == 1
    assert trends[0]["biomarker"] == "Hemoglobin"
    assert trends[0]["previous"] == 10.5
    assert trends[0]["latest"] == 11.2
    assert trends[0]["change"] == 0.7

def test_comparator_unit_mismatch():
    report_a = [{"biomarker": "Hemoglobin", "value": 105, "unit": "g/L"}]
    report_b = [{"biomarker": "Hemoglobin", "value": 11.2, "unit": "g/dL"}]
    
    trends = compare_reports(report_a, report_b)
    # Different units should not be compared deterministically
    assert len(trends) == 0

def test_comparator_missing_previous():
    report_a = []
    report_b = [{"biomarker": "Hemoglobin", "value": 11.2, "unit": "g/dL"}]
    
    trends = compare_reports(report_a, report_b)
    assert len(trends) == 0
