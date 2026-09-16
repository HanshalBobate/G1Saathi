from agents.state import AgentState
from rag_chain import get_vectorstore, MIN_RELEVANCE
from models import get_chat_model
from langchain_core.prompts import ChatPromptTemplate

def run_research_agent(state: AgentState, persist_dir: str = "chroma_db") -> AgentState:
    state.agent_trace.append("✓ Research Agent activated")
    
    try:
        store = get_vectorstore(persist_dir)
    except Exception as e:
        state.agent_trace.append("✗ ChromaDB search failed")
        state.evidence_status = "INSUFFICIENT"
        return state

    query = state.user_query
    if state.conversation_context:
        last_exchange = state.conversation_context[-1]
        query = f"{query} (context: {last_exchange})"
        state.agent_trace.append("✓ Query refined with conversation context")

    queries_to_run = [query] + state.expanded_queries
    ENTITY_BOOST = 0.05
    all_scored = {}

    state.agent_trace.append(f"✓ ChromaDB queried with {len(queries_to_run)} variants")

    for q in queries_to_run:
        try:
            try:
                scored = store.similarity_search_with_relevance_scores(q, k=4)
            except Exception:
                scored = [(d, 0.7) for d in store.similarity_search(q, k=4)]
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Vector search failed for {q}: {e}")
            scored = []
            
        for doc, score in scored:
            # Deduplicate using page_content hash or string
            doc_id = hash(doc.page_content)
            current_score = score if score is not None else 0.7
            
            # Apply ENTITY_BOOST
            if state.entities:
                for entity in state.entities:
                    if entity["canonical_name"].lower() in doc.page_content.lower():
                        current_score += ENTITY_BOOST
                        break
            
            if doc_id not in all_scored or all_scored[doc_id][1] < current_score:
                all_scored[doc_id] = (doc, current_score)

    sorted_results = sorted(list(all_scored.values()), key=lambda x: x[1], reverse=True)[:6]

    docs_kept = []
    if MIN_RELEVANCE > 0:
        docs_kept = [(d, s) for d, s in sorted_results if s >= MIN_RELEVANCE]
    else:
        docs_kept = sorted_results
        
    if docs_kept:
        state.evidence_status = "SUFFICIENT"
        state.agent_trace.append(f"✓ {len(docs_kept)} relevant passages retrieved")
        state.agent_trace.append("✓ Evidence status: SUFFICIENT")
    else:
        state.evidence_status = "INSUFFICIENT"
        state.agent_trace.append("✗ No relevant passages found")
    
    if docs_kept:
        import os
        sources = []
        for d, s in docs_kept:
            sources.append({
                "file": os.path.basename(d.metadata.get("source", "unknown")),
                "page": d.metadata.get("page", 0) + 1,
                "score": round(s, 3) if isinstance(s, (int, float)) else None,
                "excerpt": d.page_content[:400].strip() + ("..." if len(d.page_content) > 400 else ""),
                "page_content": d.page_content
            })
        state.retrieved_documents = sources
    
    return state
