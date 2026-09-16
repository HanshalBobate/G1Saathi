import pytest
from pydantic import ValidationError
from evaluation.evaluation_schema import EvaluationTestCase, EvaluationCategory, EvaluationResult, EvaluationExpectedBehavior

def test_evaluation_test_case_validation():
    # Valid
    tc = EvaluationTestCase(
        id="q1",
        category=EvaluationCategory.LOCAL_KB,
        query="Test query",
        expected=EvaluationExpectedBehavior(evidence_status=["SUFFICIENT"])
    )
    assert tc.id == "q1"
    assert tc.expected.evidence_status == ["SUFFICIENT"]

    # Invalid Category
    with pytest.raises(ValidationError):
        EvaluationTestCase(
            id="q2",
            category="INVALID_CATEGORY",
            query="Test",
            expected=EvaluationExpectedBehavior()
        )

def test_evaluation_result_validation():
    res = EvaluationResult(
        question_id="q1",
        category="LOCAL_KB",
        query="Test query",
        expected_behavior={},
        actual_status="SUFFICIENT",
        evidence_coverage=0.9,
        claims_supported=1.0,
        emergency_triggered=False,
        external_research_used=False,
        llm_calls=2,
        vector_searches=1,
        passed=True,
        reason="",
        duration_sec=1.5
    )
    assert res.passed is True
    assert res.actual_status == "SUFFICIENT"
