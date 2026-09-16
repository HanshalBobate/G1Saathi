import json
import logging
import re
from typing import Dict, Any
from agents.state import AgentState
from agents.workflow_schema import TaskPlan, TaskType
from models import get_chat_model
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

def determine_workflow_plan(query: str, state: AgentState, mode: str = "ask", files: list = None) -> TaskPlan:
    """
    Determines the task plan based on deterministic signals first, then LLM fallback.
    """
    files = files or []
    q_lower = query.lower()
    
    # 1. Deterministic Signals
    is_emergency = state.risk_level == "HIGH"
    
    # Heuristic temporal check for current info
    needs_current = bool(re.search(r'\b(latest|current|recent|today|updated|new|now|202[4-9]|203[0-9])\b', q_lower))
    
    # Check for report analysis modes or intents
    has_reports = len(files) > 0
    wants_analysis = "analyze" in q_lower or "report" in q_lower or "results" in q_lower or mode == "analyze"
    wants_compare = "compare" in q_lower or "trend" in q_lower or "change" in q_lower or mode == "compare"
    
    if is_emergency:
        plan = TaskPlan(
            task_type=TaskType.EMERGENCY,
            steps=["safety", "response"]
        )
        return plan
        
    if has_reports and wants_compare and len(files) >= 2:
        plan = TaskPlan(
            task_type=TaskType.REPORT_COMPARISON,
            requires_comparison=True,
            steps=["safety", "document_analysis", "report_comparator", "evidence_retrieval", "evidence_evaluation", "response", "next_steps"]
        )
        return plan
        
    if (has_reports and wants_analysis) or mode == "analyze":
        plan = TaskPlan(
            task_type=TaskType.MEDICAL_REPORT_ANALYSIS,
            requires_document_analysis=True,
            steps=["safety", "document_analysis", "validation", "evidence_retrieval", "evidence_evaluation", "response", "next_steps"]
        )
        return plan
        
    # If no obvious deterministic trigger, use LLM for TaskType
    llm = get_chat_model()
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a workflow routing assistant for a medical AI.
Classify the user's query into exactly one of these task types:
GENERAL_INFORMATION, MEDICAL_ENTITY_INFORMATION, CURRENT_INFORMATION.
If the query asks for recent guidelines, news, or current facts, use CURRENT_INFORMATION.
If the query asks about a specific disease, symptom, or medication, use MEDICAL_ENTITY_INFORMATION.
Otherwise, use GENERAL_INFORMATION.

Return ONLY valid JSON:
{{"task_type": "..."}}
"""),
        ("human", "{question}")
    ])
    
    task_type_str = TaskType.GENERAL_INFORMATION.value
    
    try:
        if "state.tool_calls" not in globals():
            if not hasattr(state, "tool_calls"):
                state.tool_calls = {}
                
        state.tool_calls["llm_workflow_planner"] = state.tool_calls.get("llm_workflow_planner", 0) + 1
        
        response = (prompt | llm).invoke({"question": query})
        text = response.content.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        data = json.loads(text.strip())
        
        if data.get("task_type") in [t.value for t in TaskType]:
            task_type_str = data["task_type"]
            
    except Exception as e:
        logger.warning(f"Workflow planner LLM fallback failed: {e}. Defaulting to GENERAL_INFORMATION.")
        
    if needs_current:
        task_type_str = TaskType.CURRENT_INFORMATION.value
        
    plan = TaskPlan(
        task_type=TaskType(task_type_str),
        requires_rag=True,
        requires_external_research=(task_type_str == TaskType.CURRENT_INFORMATION.value)
    )
    
    # Build steps
    steps = ["safety", "language", "information_gap", "entity_extraction"]
    
    if plan.task_type == TaskType.CURRENT_INFORMATION:
        steps.extend(["query_expansion", "local_retrieval", "external_research"])
    else:
        steps.append("local_retrieval")
        
    steps.extend(["evidence_evaluation", "response", "grounding_verification", "next_steps"])
    
    plan.steps = steps
    return plan
