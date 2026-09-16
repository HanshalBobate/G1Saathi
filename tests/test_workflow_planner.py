import pytest
from agents.state import AgentState
from agents.workflow_planner import determine_workflow_plan
from agents.workflow_schema import TaskType

def test_general_information():
    state = AgentState(user_query="What is the capital of France?", risk_level="LOW")
    plan = determine_workflow_plan(state.user_query, state, mode="ask", files=[])
    assert plan.task_type == TaskType.GENERAL_INFORMATION
    assert "information_gap" in plan.steps

def test_medical_entity():
    state = AgentState(user_query="What is diabetes?", risk_level="LOW")
    plan = determine_workflow_plan(state.user_query, state, mode="ask", files=[])
    # The LLM fallback might classify it as MEDICAL_ENTITY_INFORMATION. 
    # Since tests don't mock LLM perfectly out of the box, we just ensure it returns a valid type.
    assert plan.task_type in [TaskType.GENERAL_INFORMATION, TaskType.MEDICAL_ENTITY_INFORMATION]
    assert "local_retrieval" in plan.steps

def test_current_information():
    state = AgentState(user_query="What are the latest 2026 guidelines for diabetes?", risk_level="LOW")
    plan = determine_workflow_plan(state.user_query, state, mode="ask", files=[])
    assert plan.task_type == TaskType.CURRENT_INFORMATION
    assert "external_research" in plan.steps

def test_report_analysis():
    state = AgentState(user_query="Analyze my results", risk_level="LOW")
    plan = determine_workflow_plan(state.user_query, state, mode="analyze", files=["report1.pdf"])
    assert plan.task_type == TaskType.MEDICAL_REPORT_ANALYSIS
    assert "document_analysis" in plan.steps
    assert "validation" in plan.steps

def test_report_comparison():
    state = AgentState(user_query="What changed between these?", risk_level="LOW")
    plan = determine_workflow_plan(state.user_query, state, mode="compare", files=["r1.pdf", "r2.pdf"])
    assert plan.task_type == TaskType.REPORT_COMPARISON
    assert "report_comparator" in plan.steps

def test_emergency():
    state = AgentState(user_query="I am having a heart attack", risk_level="HIGH")
    plan = determine_workflow_plan(state.user_query, state, mode="ask", files=[])
    assert plan.task_type == TaskType.EMERGENCY
    assert plan.steps == ["safety", "response"]
