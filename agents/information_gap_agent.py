import json
import logging
from agents.state import AgentState
from models import get_chat_model
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

def run_information_gap_agent(state: AgentState) -> AgentState:
    """
    Determines if the user's request lacks necessary information required for a useful answer.
    """
    if not hasattr(state, "tool_calls"):
        state.tool_calls = {}
        
    # We only care about information gap if we're not doing a deterministic report analysis
    if state.task_plan and state.task_plan.task_type in ["MEDICAL_REPORT_ANALYSIS", "REPORT_COMPARISON"]:
        state.information_gap = {"status": "COMPLETE", "missing": []}
        return state
        
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an Information Gap Detector for a medical AI.
Your job is to determine if the user's query lacks necessary information to be answered safely.
Examples:
User: "Is this normal?" -> Missing: "measurement or report"
User: "My glucose is high." -> Missing: "numeric glucose value and reference range"
User: "What is diabetes?" -> Complete.

Do NOT ask unnecessary questions like age, sex, weight, or medications if the user just asks a general medical question.
Only flag an information gap if the query fundamentally cannot be addressed without it (like referring to 'this' without context).

Return ONLY valid JSON:
{{
  "status": "COMPLETE" or "MISSING_INFORMATION",
  "missing": ["list", "of", "missing", "items", "or", "empty", "if", "complete"],
  "message": "A helpful message explaining what is needed, or null if complete. (Write this message in {language})"
}}
"""),
        ("human", "{question}")
    ])
    
    llm = get_chat_model()
    state.tool_calls["llm_information_gap"] = state.tool_calls.get("llm_information_gap", 0) + 1
    
    try:
        response = (prompt | llm).invoke({
            "question": state.user_query,
            "language": getattr(state, "language", "en")
        })
        text = response.content.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
            
        data = json.loads(text.strip())
        state.information_gap = data
        
        if data.get("status") == "MISSING_INFORMATION":
            state.agent_trace.append("✗ Information Gap Detected")
        else:
            state.agent_trace.append("✓ Information Gap Check Passed")
            
    except Exception as e:
        logger.warning(f"Information Gap Agent failed: {e}")
        state.information_gap = {"status": "COMPLETE", "missing": []}
        
    return state
