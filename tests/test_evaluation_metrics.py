import pytest
from agents.state import AgentState
from agents.evidence_evaluator import run_evidence_evaluator

def test_evidence_evaluator_sufficient_metrics():
    # Setup state with sufficient evidence
    state = AgentState(user_query="What is the treatment for hypertension?")
    state.retrieved_documents = [
        {"excerpt": "Treatment for hypertension includes lifestyle changes and medication like ACE inhibitors."},
        {"excerpt": "Beta blockers can also be used."}
    ]
    state.extracted_claims = [
        "ACE inhibitors are a treatment",
        "Beta blockers can be used"
    ]
    
    state = run_evidence_evaluator(state)
    
    metrics = state.evidence_quality_metrics
    assert metrics is not None
    assert metrics["evidence_coverage"] == 0 # Updated after response generation
    assert metrics["sources_used"] == 2
    assert "evidence_status" in metrics

def test_evidence_evaluator_insufficient_metrics():
    state = AgentState(user_query="What is the cure for chronic xenomorphosis?")
    state.retrieved_documents = []
    
    state = run_evidence_evaluator(state)
    
    assert state.evidence_status == "INSUFFICIENT"
    assert state.evidence_quality_metrics["sources_used"] == 0
    assert state.evidence_quality_metrics["evidence_coverage"] == 0.0
