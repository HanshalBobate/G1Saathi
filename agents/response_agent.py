import json
import logging
from typing import List, Dict, Any
from agents.state import AgentState
from models import get_chat_model
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a careful assistant that answers questions about medical guidelines and research papers, and analyzes medical reports.

Rules:
1. Use ONLY the retrieved evidence context below. Never use outside knowledge or fabricate sources.
2. If the evidence is INSUFFICIENT, say exactly: "I don't have enough information in my medical knowledge base to answer this reliably." (Translate this phrase to the requested language if needed).
3. Cite every claim with its source tag in square brackets, for example [guideline.pdf, p. 12] or [who.int].
4. Follow these safety constraints: {constraints}
5. Answer in the requested language: {language}.
   - If English (en): Answer in English.
   - If Hindi (hi): Answer in Hindi.
   - If Marathi (mr): Answer in Marathi.
   - If Hinglish (hinglish): Answer naturally in Hinglish.
   - You MUST keep medical terminology in English when that improves clarity (e.g. "Diabetes", "Hypertension").
   - Do NOT translate citations. Citation filenames, page numbers, external source names, and URLs must remain EXACTLY unchanged.
6. CONTRADICTION DETECTION: If the LOCAL KNOWLEDGE BASE and EXTERNAL RESEARCH provide conflicting or inconsistent information (especially regarding latest recommendations), you MUST explicitly state the discrepancy. Do not independently declare which is clinically correct, but note if the external source is more recent.
7. REPORT ANALYSIS: If "REPORT MEASUREMENTS" are provided below, list them clearly. Explain what the biomarkers generally represent using the retrieved evidence. Explicitly state: "This is informational and not a diagnosis." NEVER invent or hallucinate values or reference ranges. 

REPORT MEASUREMENTS (From uploaded document):
{measurements}

Retrieved Evidence Context:
{context}

Conversation Context:
{conversation}"""

GROUNDING_PROMPT = """You are a grounding verification system. Given a generated response and the retrieved evidence context, extract the major factual claims made in the response. For each claim, determine if it is directly supported by the provided evidence.

Output ONLY valid JSON in this exact format:
[
    {{
        "claim": "Extracted factual claim...",
        "supported": true,
        "sources": [
            {{"source": "source_name", "page": "page_number_if_any"}}
        ]
    }}
]

Retrieved Evidence Context:
{context}

Generated Response:
{response}
"""

REVISION_PROMPT = """The previous generated response contained unsupported factual claims. Rewrite the response to REMOVE or CORRECT any unsupported claims. Rely ONLY on the provided evidence context.

Unsupported Claims to remove/fix:
{unsupported}

Required Output Language:
{language}

Original Query:
{question}

Retrieved Evidence Context:
{context}
"""

def extract_and_verify_claims(response_text: str, context_str: str) -> List[Dict[str, Any]]:
    prompt = ChatPromptTemplate.from_messages([("system", GROUNDING_PROMPT)])
    llm = get_chat_model()
    try:
        res = (prompt | llm).invoke({"context": context_str, "response": response_text})
        text = res.content.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception as e:
        logger.error(f"Claim extraction failed: {e}")
        return []

def run_response_agent(state: AgentState) -> AgentState:
    if getattr(state, "risk_level", "none") == "HIGH":
        state.agent_trace.append("✓ Response bypassed (Emergency handled by Safety Gate)")
        return state
        
    if getattr(state, "tool_calls", None) is None:
        state.tool_calls = {}
    state.tool_calls["llm_response_agent"] = state.tool_calls.get("llm_response_agent", 0) + 1

    if getattr(state, "information_gap", None) and state.information_gap.get("status") == "MISSING_INFORMATION":
        msg = state.information_gap.get("message")
        if not msg:
            missing = ", ".join(state.information_gap.get("missing", []))
            msg = f"I cannot provide a safe answer because the following information is missing: {missing}. Please provide it so I can help."
        state.final_response = msg
        state.agent_trace.append("✓ Response generated (Missing Information)")
        return state

    if state.evidence_status == "INSUFFICIENT" and not getattr(state, "external_documents", []):
        insufficient_responses = {
            "en": "I don't have enough information in my medical knowledge base to answer this reliably.",
            "hi": "मेरे पास इस प्रश्न का विश्वसनीय उत्तर देने के लिए मेरे चिकित्सा ज्ञानकोष में पर्याप्त जानकारी नहीं है।",
            "mr": "या प्रश्नाचे विश्वसार्ह उत्तर देण्यासाठी माझ्या वैद्यकीय ज्ञानकोशात पुरेशी माहिती नाही.",
            "hinglish": "Mere paas medical knowledge base me iska reliable answer dene ke liye enough information nahi hai."
        }
        state.final_response = insufficient_responses.get(state.language, insufficient_responses["en"])
        state.agent_trace.append("✓ Response generated (Insufficient Evidence)")
        return state

    # Build context string
    parts = []
    if state.retrieved_documents:
        parts.append("--- LOCAL KNOWLEDGE BASE ---")
        for doc in state.retrieved_documents:
            name = doc.get("file", "unknown")
            page = doc.get("page", 1)
            content = doc.get("page_content", "")
            parts.append(f"[{name}, p. {page}]\n{content}")
            
    if state.external_documents:
        parts.append("--- EXTERNAL RESEARCH ---")
        for doc in state.external_documents:
            domain = doc.get("domain", "unknown")
            content = doc.get("snippet", "")
            parts.append(f"[{domain}]\n{content}")
            
    context_str = "\n\n".join(parts)
    constraints_str = ", ".join(state.safety_result.get("constraints", []))
    
    conv_parts = []
    for msg in state.conversation_context[-3:]: 
        conv_parts.append(f"{msg.get('role', 'user')}: {msg.get('text', '')}")
    conv_str = "\n".join(conv_parts)
    
    llm = get_chat_model()
    
    measurements_str = "None"
    if state.report_measurements:
        measurements_str = json.dumps(state.report_measurements, indent=2)
    
    # Generation Cycle
    generation_prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", "{question}")])
    try:
        res = (generation_prompt | llm).invoke({
            "context": context_str, 
            "constraints": constraints_str,
            "conversation": conv_str,
            "language": state.language,
            "question": state.user_query,
            "measurements": measurements_str
        })
        current_response = res.content
        state.agent_trace.append("✓ Response generated")
    except Exception as e:
        state.final_response = f"An error occurred while generating the response: {str(e)}"
        state.agent_trace.append("✗ Response generation failed")
        return state

    # Grounding Check Loop
    max_revisions = 2
    claims = []
    
    for attempt in range(max_revisions + 1):
        state.agent_trace.append("✓ Response grounding checked")
        claims = extract_and_verify_claims(current_response, context_str)
        
        unsupported = [c for c in claims if not c.get("supported", False)]
        
        if not unsupported:
            state.agent_trace.append("✓ Safety validation completed")
            break
            
        if attempt < max_revisions:
            state.agent_trace.append("⚠ Unsupported claim detected")
            
            revision_p = ChatPromptTemplate.from_messages([("system", REVISION_PROMPT)])
            unsup_text = "\n".join([f"- {c['claim']}" for c in unsupported])
            try:
                res = (revision_p | llm).invoke({
                    "unsupported": unsup_text,
                    "question": state.user_query,
                    "context": context_str,
                    "language": state.language
                })
                current_response = res.content
                state.agent_trace.append("✓ Response revised using retrieved evidence")
            except Exception as e:
                logger.error(f"Revision failed: {e}")
                break
        else:
            state.agent_trace.append("⚠ Grounding revisions exhausted")
            break

    state.final_response = current_response
    state.extracted_claims = claims
    state.citations = state.retrieved_documents + state.external_documents
    
    # Calculate Coverage Metric
    total_claims = len(claims)
    supported_claims = len([c for c in claims if c.get("supported", True)]) # default True if parsing fails
    
    coverage = 0
    if total_claims > 0:
        coverage = int((supported_claims / total_claims) * 100)
    elif total_claims == 0 and len(current_response) > 20 and state.evidence_status != "INSUFFICIENT":
        # Heuristic: if no claims extracted but response is large, maybe parsing failed
        coverage = 100
        
    state.evidence_quality_metrics["evidence_coverage"] = coverage
    state.evidence_quality_metrics["claims_supported"] = f"{supported_claims}/{total_claims}"

    return state

