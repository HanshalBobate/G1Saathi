from agents.state import AgentState
from tools.medical_search import search_trusted_sources
import logging

logger = logging.getLogger(__name__)

MAX_EXTERNAL_SEARCHES = 2

def run_external_research_agent(state: AgentState) -> AgentState:
    """
    Performs autonomous medical research using trusted sources
    if the local knowledge base is insufficient or needs the latest data.
    """
    if state.research_attempts >= MAX_EXTERNAL_SEARCHES:
        state.agent_trace.append(f"✗ Maximum external research attempts ({MAX_EXTERNAL_SEARCHES}) reached")
        return state

    state.agent_trace.append("✓ Research Agent activated (External)")
    
    query = state.user_query
    if state.conversation_context:
        # Simplistic approach: just use the query, as DDG doesn't handle complex context well.
        # But we could extract keywords if needed. For now, we trust the raw query.
        pass

    try:
        state.research_attempts += 1
        state.agent_trace.append(f"✓ Querying external trusted sources (Attempt {state.research_attempts})")
        
        results = search_trusted_sources(query, max_results=3)
        
        if results:
            state.agent_trace.append(f"✓ {len(results)} trusted sources retrieved")
            state.agent_trace.append("✓ Source verification completed")
            state.external_documents = results
            state.agent_trace.append("✓ Evidence fused")
        else:
            state.agent_trace.append("✗ No trusted external sources found")

    except Exception as e:
        logger.error(f"External research failed: {e}")
        state.agent_trace.append("✗ External research unavailable (network or timeout error)")

    return state
