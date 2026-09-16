import json
import logging
from agents.state import AgentState
from models import get_chat_model
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

def run_next_steps_agent(state: AgentState) -> AgentState:
    """
    Generates safe, informational next steps based on the executed workflow and evidence.
    """
    if not hasattr(state, "tool_calls"):
        state.tool_calls = {}
        
    # High risk / emergency bypass
    if state.risk_level == "HIGH":
        state.next_steps = ["Please seek immediate emergency medical assistance or call your local emergency number."]
        return state
        
    if state.evidence_status == "INSUFFICIENT":
        state.next_steps = ["The available sources do not provide enough evidence to answer this question reliably.", "Consider providing the relevant report section or asking about a specific measurement."]
        return state
        
    if state.evidence_status == "CONFLICTING":
        state.next_steps = ["The retrieved sources contain differing information.", "The system is not treating one source as definitive.", "Review the cited sources and consider professional interpretation."]
        return state
        
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Next Steps Assistant for a medical AI.
Based on the user query and the fact that we have provided a medical information response, generate 2-4 safe, actionable INFORMATIONAL next steps.

CRITICAL RULES:
- DO NOT prescribe medication.
- DO NOT recommend medication doses.
- DO NOT recommend specific medical interventions or say "Take X".
- ALWAYS keep the steps educational or administrative (e.g. "Review the cited evidence", "Discuss with a healthcare professional", "Compare with previous reports").

Return ONLY a valid JSON array of strings:
[
  "Step 1...",
  "Step 2..."
]
(Write these steps in {language})
"""),
        ("human", "Query: {question}\nTask Type: {task_type}")
    ])
    
    llm = get_chat_model()
    state.tool_calls["llm_next_steps"] = state.tool_calls.get("llm_next_steps", 0) + 1
    
    try:
        task_type = state.task_plan.task_type.value if getattr(state, "task_plan", None) else "UNKNOWN"
        response = (prompt | llm).invoke({
            "question": state.user_query,
            "task_type": task_type,
            "language": getattr(state, "language", "en")
        })
        
        text = response.content.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
            
        data = json.loads(text.strip())
        if isinstance(data, list):
            state.next_steps = data
        else:
            state.next_steps = ["Discuss relevant findings with a healthcare professional."]
            
        state.agent_trace.append(f"✓ Generated {len(state.next_steps)} Next Steps")
            
    except Exception as e:
        logger.warning(f"Next Steps Agent failed: {e}")
        state.next_steps = ["Discuss relevant findings with a healthcare professional."]
        
    return state
