import pytest
from agents.state import AgentState
from agents.orchestrator import run_language_agent
from knowledge.entity_extractor import extract_entities
from agents.query_expansion_agent import run_query_expansion_agent

def test_language_detection():
    # English
    state_en = AgentState(user_query="What are the symptoms of hypertension?")
    state_en = run_language_agent(state_en)
    assert state_en.language == "en"

    # Hindi (Devanagari)
    state_hi = AgentState(user_query="मधुमेह के लक्षण क्या हैं?")
    state_hi = run_language_agent(state_hi)
    assert state_hi.language == "hi"

    # Marathi
    state_mr = AgentState(user_query="डेंग्यूची लक्षणे काय आहेत?")
    state_mr = run_language_agent(state_mr)
    assert state_mr.language == "mr"

    # Hinglish (Should fallback or detect as hinglish/hi/en)
    state_hinglish = AgentState(user_query="Hypertension ke symptoms kya hain?")
    state_hinglish = run_language_agent(state_hinglish)
    # The language detector classifies this as 'hinglish' or falls back to 'en' / 'hi' depending on LLM
    assert state_hinglish.language in ["en", "hi", "hinglish"]

def test_entity_extraction_and_query_expansion():
    # 1. English Disease
    state = AgentState(user_query="What are the symptoms of measles?")
    state.entities = extract_entities(state.user_query)
    
    assert len(state.entities) > 0
    assert state.entities[0]["canonical_name"] == "Measles"
    
    state = run_query_expansion_agent(state)
    assert "Measles symptoms" in state.expanded_queries

    # 2. Hindi Disease
    state = AgentState(user_query="खसरा के लक्षण क्या हैं?")
    state.entities = extract_entities(state.user_query)
    
    assert len(state.entities) > 0
    assert state.entities[0]["canonical_name"] == "Measles"
    
    state = run_query_expansion_agent(state)
    assert "Measles symptoms" in state.expanded_queries

    # 3. Marathi Symptom
    state = AgentState(user_query="मला छातीत तीव्र वेदना होत आहेत")
    state.entities = extract_entities(state.user_query)
    
    assert len(state.entities) > 0
    assert state.entities[0]["canonical_name"] == "Chest Pain"
    
    state = run_query_expansion_agent(state)
    assert "Chest Pain causes and diagnosis" in state.expanded_queries
