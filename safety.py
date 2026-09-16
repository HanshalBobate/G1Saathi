"""
G1Saathi — Safety Agent
Screens user queries for emergency/crisis language before they reach the RAG chain.
Active in both the Streamlit UI and the FastAPI layer.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Regex covering common medical emergency phrases.
# Intentionally broad — false positives are acceptable; false negatives are not.
_EMERGENCY_RE = re.compile(
    r"\b(chest pain|heart attack|stroke|can't breathe|cannot breathe|"
    r"difficulty breathing|suicidal|kill myself|hurt myself|self.harm|"
    r"overdose|unconscious|seizure|anaphylaxis|severe bleeding|heavy bleeding|bleeding heavily|"
    r"call 911|call 112|need an ambulance|emergency room|going to die|"
    r"सीने में दर्द|छाती में दर्द|सांस लेने में दिक्कत|छातीत दुखणे|छातीत तीव्र वेदना|"
    r"आत्महत्या|हार्ट अटैक|हार्ट अटॅक|हृदयविकाराचा झटका)\b",
    re.IGNORECASE,
)

_EMERGENCY_BANNER = (
    "⚠️ **This message may describe a medical emergency.**\n\n"
    "Please call **emergency services (112 / 911)** or go to the nearest "
    "emergency room **immediately**. Do not rely on an AI chatbot in an emergency.\n\n"
    "⚠️ **यह एक आपातकालीन चिकित्सा स्थिति हो सकती है।** कृपया तुरंत **आपातकालीन सेवाओं (112 / 108)** से संपर्क करें या निकटतम अस्पताल जाएं।\n\n"
    "⚠️ **ही वैद्यकीय आणीबाणी असू शकते.** कृपया त्वरित **रुग्णवाहिका किंवा आपत्कालीन सेवांशी (११२ / १०८)** संपर्क साधा.\n\n"
    "---\n\n"
)


from models import get_fast_chat_model
from langchain_core.prompts import ChatPromptTemplate

_SAFETY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are an emergency detection system. Does the following user query describe a potential medical emergency (like severe bleeding, chest pain, stroke, suicidal thoughts, etc.)? Answer ONLY with 'yes' or 'no'."),
    ("human", "{query}")
])

def screen(query: str) -> dict:
    """
    Screen a user query for safety concerns using a fast LLM.
    Returns: dict with is_emergency, risk_level, safety_note
    """
    try:
        res = (_SAFETY_PROMPT | get_fast_chat_model()).invoke({"query": query})
        answer = res.content.strip().lower()
        if "yes" in answer:
            logger.warning("Safety: emergency detected by LLM in query")
            return {
                "is_emergency": True,
                "risk_level": "emergency",
                "safety_note": _EMERGENCY_BANNER,
            }
    except Exception as e:
        logger.error(f"Safety LLM check failed: {e}")
        # Fallback to regex if LLM fails
        if _EMERGENCY_RE.search(query):
            return {
                "is_emergency": True,
                "risk_level": "emergency",
                "safety_note": _EMERGENCY_BANNER,
            }
            
    return {
        "is_emergency": False,
        "risk_level": "none",
        "safety_note": None,
    }
