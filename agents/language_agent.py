import re
import json
import logging
from typing import Dict, Any
from agents.state import AgentState
from models import get_chat_model
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

def detect_language_heuristic(text: str) -> str:
    """Attempts to deterministically detect the language."""
    text_lower = text.lower()
    
    # 1. Check for Devanagari script
    # Devanagari block is \u0900 to \u097F
    devanagari_chars = [c for c in text if '\u0900' <= c <= '\u097F']
    if len(devanagari_chars) > len(text) * 0.2:
        # It's Hindi or Marathi in Devanagari script
        marathi_keywords = ["काय", "आहे", "नाही", "कसे", "मला", "सांगा", "लक्षणे", "साठी", "आणि"]
        hindi_keywords = ["क्या", "है", "नहीं", "कैसे", "मुझे", "बताओ", "लक्षण", "के", "लिए", "और"]
        
        mr_count = sum(1 for w in marathi_keywords if w in text)
        hi_count = sum(1 for w in hindi_keywords if w in text)
        
        # 'ळ' (\u0933) is heavily used in Marathi, rare in standard Hindi
        if '\u0933' in text or mr_count > hi_count:
            return "mr"
        elif hi_count > mr_count:
            return "hi"
        # Ambiguous in Devanagari, fallback to LLM
        return "UNKNOWN_DEVANAGARI"
        
    # 2. Check for Latin script (English vs Hinglish)
    hinglish_keywords = ["kya", "hai", "nahi", "kaise", "mujhe", "batao", "dawai", "bimari", "sirf", "aur", "ke", "liye", "symptoms batao"]
    english_keywords = ["what", "is", "not", "how", "tell", "me", "medicine", "disease", "only", "and", "for", "symptoms"]
    
    hing_count = sum(1 for w in hinglish_keywords if re.search(r'\b' + w + r'\b', text_lower))
    eng_count = sum(1 for w in english_keywords if re.search(r'\b' + w + r'\b', text_lower))
    
    if hing_count > 0 and hing_count >= eng_count:
        return "hinglish"
    if eng_count > 0 and eng_count > hing_count:
        return "en"
        
    # Ambiguous Latin
    return "UNKNOWN_LATIN"

def detect_language_llm(text: str) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a language detector. Classify the user's text into one of: 'en' (English), 'hi' (Hindi in Devanagari), 'mr' (Marathi in Devanagari), or 'hinglish' (Hindi written in Latin script). Return ONLY a JSON object: {{\"language\": \"en\"}}"),
        ("human", "{text}")
    ])
    try:
        res = (prompt | get_chat_model()).invoke({"text": text})
        content = res.content.strip().replace("```json", "").replace("```", "")
        data = json.loads(content)
        lang = data.get("language", "en").lower()
        if lang in ["en", "hi", "mr", "hinglish"]:
            return lang
    except Exception as e:
        logger.warning(f"LLM language detection failed: {e}")
    return "en"

def run_language_agent(state: AgentState) -> AgentState:
    lang = detect_language_heuristic(state.user_query)
    
    if lang.startswith("UNKNOWN"):
        lang = detect_language_llm(state.user_query)
        
    state.language = lang
    
    lang_display_map = {
        "en": "English",
        "hi": "Hindi",
        "mr": "Marathi",
        "hinglish": "Hinglish"
    }
    
    state.agent_trace.append(f"✓ Language detected: {lang_display_map.get(lang, lang)}")
    return state
