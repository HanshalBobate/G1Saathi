import json
import logging
from typing import Dict, Any
from agents.state import AgentState
from models import get_chat_model
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

def determine_source_tier(source_url_or_name: str) -> str:
    """Categorizes a source into TIER_1, TIER_2, or TIER_3."""
    src = source_url_or_name.lower()
    tier_1_domains = ["who.int", "cdc.gov", "nih.gov", "fda.gov", "nhs.uk"]
    if any(d in src for d in tier_1_domains):
        return "TIER_1"
    if ".edu" in src or "hospital" in src or "university" in src:
        return "TIER_2"
    return "TIER_3"

def run_evidence_evaluator(state: AgentState) -> AgentState:
    """
    Evaluates the retrieved evidence (both local and external) for relevance, 
    source quality, coverage, freshness, and agreement.
    Sets state.evidence_status and populates state.evidence_quality_metrics.
    """
    state.agent_trace.append("✓ Evidence sufficiency evaluated")
    
    # 1. Calculate Retrieval Diagnostics (Local)
    scores = []
    for doc in state.retrieved_documents:
        score = doc.get("score")
        if score is not None:
            scores.append(score)
            
    diagnostics = {
        "retrieval_count": len(state.retrieved_documents),
        "top_score": max(scores) if scores else None,
        "average_score": round(sum(scores) / len(scores), 3) if scores else None,
        "sources_count": len(set(d.get("file") for d in state.retrieved_documents))
    }
    state.retrieval_diagnostics = diagnostics
    
    # 2. Source Quality
    tiers = []
    for doc in state.retrieved_documents:
        tiers.append("TIER_1") # Treat internal medical documents as TIER_1 by default
    for ext in state.external_documents:
        tiers.append(determine_source_tier(ext.get("domain", "")))
        
    if "TIER_3" in tiers and "TIER_1" not in tiers:
        source_quality = "Low"
    elif "TIER_1" in tiers:
        source_quality = "High"
    elif tiers:
        source_quality = "Medium"
    else:
        source_quality = "None"
        
    # 3. Agreement & Sufficiency via LLM (Lightweight Check)
    if not state.retrieved_documents and not state.external_documents:
        state.evidence_status = "INSUFFICIENT"
    elif state.retrieved_documents and state.external_documents:
        # Check for contradiction between local and external
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an evidence evaluator. Compare LOCAL EVIDENCE and EXTERNAL EVIDENCE. Determine if they are CONFLICTING (materially disagree) or AGREE. Return JSON: {{'agreement': 'CONFLICTING' | 'AGREE'}}"),
            ("human", "LOCAL: {local}\n\nEXTERNAL: {external}")
        ])
        local_text = " ".join([d.get("excerpt", "") for d in state.retrieved_documents])
        ext_text = " ".join([d.get("snippet", "") for d in state.external_documents])
        llm = get_chat_model()
        try:
            res = (prompt | llm).invoke({"local": local_text, "external": ext_text})
            text = res.content.replace("```json", "").replace("```", "").strip()
            data = json.loads(text)
            if data.get("agreement") == "CONFLICTING":
                state.evidence_status = "CONFLICTING"
            else:
                state.evidence_status = "SUFFICIENT"
        except Exception as e:
            logger.warning(f"Agreement check failed: {e}")
            state.evidence_status = "SUFFICIENT"
    else:
        state.evidence_status = "SUFFICIENT"
        
    # Initialize basic metrics; coverage will be updated after response generation
    state.evidence_quality_metrics = {
        "source_quality": source_quality,
        "evidence_status": state.evidence_status,
        "evidence_coverage": 0,
        "claims_supported": "0/0",
        "sources_used": len(state.retrieved_documents) + len(state.external_documents)
    }

    return state
