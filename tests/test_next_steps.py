import pytest
from agents.state import AgentState
from agents.next_steps_agent import run_next_steps_agent
from agents.workflow_schema import TaskPlan, TaskType

def test_emergency_next_steps():
    state = AgentState(user_query="Chest pain", risk_level="HIGH")
    state = run_next_steps_agent(state)
    assert "emergency" in state.next_steps[0].lower()

def test_insufficient_evidence_next_steps():
    state = AgentState(user_query="What is XYZ?", risk_level="LOW", evidence_status="INSUFFICIENT")
    state = run_next_steps_agent(state)
    assert "do not provide enough evidence" in state.next_steps[0]

def test_conflicting_evidence():
    state = AgentState(user_query="Current guidelines?", risk_level="LOW", evidence_status="CONFLICTING")
    state = run_next_steps_agent(state)
    assert "differing information" in state.next_steps[0]

def test_normal_request():
    state = AgentState(user_query="What is diabetes?", risk_level="LOW", evidence_status="SUFFICIENT")
    state.task_plan = TaskPlan(task_type=TaskType.GENERAL_INFORMATION)
    state = run_next_steps_agent(state)
    assert len(state.next_steps) > 0
    # Make sure we don't prescribe
    for step in state.next_steps:
        assert "take" not in step.lower() or "medicine" not in step.lower()
