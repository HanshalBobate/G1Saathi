import pytest
from evaluation.evaluation_schema import EvaluationTestCase, EvaluationCategory, EvaluationExpectedBehavior

def test_report_evaluation_schema():
    tc = EvaluationTestCase(
        id="q1",
        category=EvaluationCategory.REPORT_ANALYSIS,
        query="Analyze this report",
        files=["test_report.pdf"],
        expected=EvaluationExpectedBehavior(biomarker="WBC")
    )
    assert tc.files == ["test_report.pdf"]
    assert tc.expected.biomarker == "WBC"
