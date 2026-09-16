import json
from agents.state import AgentState
from models import get_chat_model
from langchain_core.prompts import ChatPromptTemplate

def run_safety_agent(state: AgentState) -> AgentState:
    state.agent_trace.append("✓ Safety review completed")
    
    # Simple fallback safety agent abstraction.
    # In a full production system this could be an LLM call.
    # We use a fast heuristic to avoid compounding LLM latency for local execution.
    query_lower = state.user_query.lower()
    
    risk_level = "LOW"
    requires_escalation = False
    constraints = ["Use evidence-grounded language", "Acknowledge uncertainty"]
    
    if "diagnos" in query_lower or "what do i have" in query_lower:
        constraints.append("Do not diagnose")
    
    if "prescription" in query_lower or "medication" in query_lower or "dose" in query_lower:
        constraints.append("Do not prescribe individualized treatment")
        
    if "guarantee" in query_lower or "sure" in query_lower:
        constraints.append("Cannot guarantee outcomes")
        
    state.safety_result = {
        "risk_level": risk_level,
        "requires_escalation": requires_escalation,
        "constraints": constraints
    }
    state.risk_level = risk_level
    
    return state
