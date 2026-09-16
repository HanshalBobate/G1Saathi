import logging
from agents.state import AgentState

logger = logging.getLogger(__name__)

def run_query_expansion_agent(state: AgentState) -> AgentState:
    """
    Expands the user query using detected medical entities to improve semantic retrieval.
    Does not use LLM to ensure maximum performance.
    Generates at most 2 variants.
    """
    if not state.entities:
        return state
        
    expanded = []
    
    # Analyze intent slightly using heuristics for the expansion
    query_lower = state.user_query.lower()
    is_symptom = any(word in query_lower for word in ["symptom", "लक्षण", "लक्षणे", "pain", "दुखणे", "दर्द"])
    is_treatment = any(word in query_lower for word in ["treatment", "cure", "medicine", "दवा", "इलाज", "उपचार", "औषध"])
    
    # We'll take the first major disease entity found for expansion to avoid combinatorial explosion
    disease_entities = [e for e in state.entities if e.get("category") != "symptom"]
    
    if disease_entities:
        primary_entity = disease_entities[0]["canonical_name"]
        
        if is_symptom:
            expanded.append(f"{primary_entity} symptoms")
        elif is_treatment:
            expanded.append(f"{primary_entity} treatment guidelines")
        else:
            expanded.append(f"{primary_entity} overview")
            expanded.append(f"{primary_entity} symptoms and diagnosis")
    
    elif state.entities:
        # If only symptoms are found (e.g., Chest Pain)
        primary_entity = state.entities[0]["canonical_name"]
        expanded.append(f"{primary_entity} causes and diagnosis")
    
    # Limit to max 2 variants
    state.expanded_queries = expanded[:2]
    
    if state.expanded_queries:
        state.agent_trace.append(f"✓ Query expanded: {state.expanded_queries[0]}")
        
    return state
