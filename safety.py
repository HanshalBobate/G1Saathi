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
    r"overdose|unconscious|seizure|anaphylaxis|severe bleeding|"
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


def screen(query: str) -> dict:
    """
    Screen a user query for safety concerns.

    Returns:
        dict with keys:
          - is_emergency (bool)
          - risk_level (str): 'none' | 'emergency'
          - safety_note (str | None): Banner to prepend, or None
    """
    if _EMERGENCY_RE.search(query):
        logger.warning("Safety: emergency pattern detected in query (length=%d)", len(query))
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
