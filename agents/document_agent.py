from agents.state import AgentState
from rag_chain import get_vectorstore, MIN_RELEVANCE
import os

def run_document_agent(state: AgentState, persist_dir: str = "chroma_db", files: list = None) -> AgentState:
    state.agent_trace.append("✓ Document Agent activated")
    
    try:
        store = get_vectorstore(persist_dir)
    except Exception as e:
        state.agent_trace.append("✗ ChromaDB search failed")
        state.evidence_status = "INSUFFICIENT"
        return state

    state.agent_trace.append("✓ Uploaded report analyzed")
    state.agent_trace.append("✓ RAG consulted for terminology")
    
    query = state.user_query
    
    try:
        try:
            scored = store.similarity_search_with_relevance_scores(query, k=4)
        except Exception:
            scored = [(d, None) for d in store.similarity_search(query, k=4)]
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Vector search failed: {e}")
        scored = []
        
    if MIN_RELEVANCE > 0:
        kept = [(d, s) for d, s in scored if s is None or s >= MIN_RELEVANCE]
    else:
        kept = scored
        
    if kept:
        state.evidence_status = "SUFFICIENT"
        state.agent_trace.append(f"✓ {len(kept)} evidence passages found")
    else:
        state.evidence_status = "INSUFFICIENT"

    if kept:
        sources = []
        combined_text = ""
        for d, s in kept:
            sources.append({
                "file": os.path.basename(d.metadata.get("source", "unknown")),
                "page": d.metadata.get("page", 0) + 1,
                "score": round(s, 3) if isinstance(s, (int, float)) else None,
                "excerpt": d.page_content[:400].strip() + ("..." if len(d.page_content) > 400 else ""),
                "page_content": d.page_content
            })
            combined_text += d.page_content + "\n\n"
        state.retrieved_documents = sources
        
        # Phase 6: Deterministic Report Extraction (Full Document, Page-Aware)
        from document_analysis.document_text import extract_pdf_pages
        from document_analysis.report_parser import parse_medical_report
        
        upload_dir = "data/uploads"
        measurements = []
        if os.path.isdir(upload_dir):
            for pdf_file in os.listdir(upload_dir):
                if pdf_file.lower().endswith(".pdf"):
                    pdf_path = os.path.join(upload_dir, pdf_file)
                    try:
                        pages = extract_pdf_pages(pdf_path)
                        doc_measurements = parse_medical_report(pages)
                        # Add document name to measurements if missing
                        for m in doc_measurements:
                            m["document"] = pdf_file
                        measurements.extend(doc_measurements)
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).warning(f"Failed to parse {pdf_file}: {e}")
        
        if measurements:
            state.report_measurements = measurements
            state.agent_trace.append(f"✓ Extracted {len(measurements)} structured measurements directly from PDF")
            
            # Retrieve supporting evidence for the found biomarkers to ground the explanation
            # Only pick top 3 biomarkers that match user query loosely, or just the first few
            biomarkers = list(set([m.get("biomarker") for m in measurements if m.get("biomarker")]))
            if biomarkers:
                # To prevent gigantic queries, we just grab up to 3 biomarkers
                explanation_query = "What is " + " and ".join(biomarkers[:3]) + "?" 
                try:
                    exp_scored = store.similarity_search_with_relevance_scores(explanation_query, k=3)
                    for ed, es in exp_scored:
                        if es is None or es >= MIN_RELEVANCE:
                            state.retrieved_documents.append({
                                "file": os.path.basename(ed.metadata.get("source", "unknown")),
                                "page": ed.metadata.get("page", 0) + 1,
                                "score": round(es, 3) if isinstance(es, (int, float)) else None,
                                "excerpt": ed.page_content[:400].strip() + ("..." if len(ed.page_content) > 400 else ""),
                                "page_content": ed.page_content
                            })
                    state.agent_trace.append("✓ Retrieved contextual medical evidence for measurements")
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Secondary evidence search failed: {e}")
        
    return state
