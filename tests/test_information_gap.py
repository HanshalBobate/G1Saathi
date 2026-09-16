import pytest
from agents.state import AgentState
from agents.information_gap_agent import run_information_gap_agent
from agents.workflow_schema import TaskPlan, TaskType

def test_missing_report():
    state = AgentState(user_query="Is this normal?", risk_level="LOW")
    state.task_plan = TaskPlan(task_type=TaskType.GENERAL_INFORMATION)
    state = run_information_gap_agent(state)
    assert state.information_gap["status"] == "MISSING_INFORMATION"

def test_missing_numeric_value():
    state = AgentState(user_query="My glucose is high", risk_level="LOW")
    state.task_plan = TaskPlan(task_type=TaskType.GENERAL_INFORMATION)
    state = run_information_gap_agent(state)
    assert state.information_gap["status"] == "MISSING_INFORMATION"

def test_complete_question():
    state = AgentState(user_query="What is diabetes?", risk_level="LOW")
    state.task_plan = TaskPlan(task_type=TaskType.GENERAL_INFORMATION)
    state = run_information_gap_agent(state)
    assert state.information_gap["status"] == "COMPLETE"
