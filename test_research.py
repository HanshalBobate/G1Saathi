import os
import sys
import logging
from unittest.mock import patch, MagicMock
from agents.orchestrator import run_orchestrator
from tools.medical_search import strip_pii

# Setup minimal logging
logging.basicConfig(level=logging.INFO)

def run_tests():
    print("--- Running Test 1: Local KB answer (No External) ---")
    state1 = run_orchestrator("What are common symptoms of dengue?", persist_dir="chroma_db")
    print(f"Risk Level: {state1.risk_level}")
    print(f"Agent Trace: {state1.agent_trace}")
    print(f"Final Response: {state1.final_response[:100]}...\n")

    print("--- Running Test 2: Current Info (External Research) ---")
    state2 = run_orchestrator("What are the latest recommendations regarding dengue in 2026?", persist_dir="chroma_db")
    print(f"Agent Trace: {state2.agent_trace}")
    print(f"Needs Current Info: {state2.needs_current_info}")
    print(f"External Docs: {len(state2.external_documents)}")
    print(f"Final Response: {state2.final_response[:100]}...\n")

    print("--- Running Test 3: External Source Unavailable ---")
    with patch("agents.external_research_agent.search_trusted_sources", side_effect=Exception("Network Timeout")):
        state3 = run_orchestrator("What are the latest 2026 updates for diabetes?", persist_dir="chroma_db")
        print(f"Agent Trace: {state3.agent_trace}")
        print(f"External Docs: {len(state3.external_documents)}")
        print(f"Final Response: {state3.final_response[:100]}...\n")

    print("--- Running Test 4: Untrusted Domain Result ---")
    # Actually this is handled by search_trusted_sources, let's test it directly
    from tools.medical_search import search_trusted_sources
    with patch("tools.medical_search.DDGS") as MockDDGS:
        instance = MockDDGS.return_value
        instance.text.return_value = [
            {"href": "https://random-health-blog.com/dengue", "title": "Random", "body": "stuff"},
            {"href": "https://www.who.int/news/dengue", "title": "WHO Dengue", "body": "official"}
        ]
        results = search_trusted_sources("dengue")
        print(f"Filtered Results: {[r['domain'] for r in results]}\n")

    print("--- Running Test 5: Conflicting Evidence ---")
    # For this, we just ensure the prompt allows the LLM to identify contradictions.
    # We can inject conflicting docs into state directly and run response agent.
    from agents.state import AgentState
    from agents.response_agent import run_response_agent
    conflict_state = AgentState(user_query="What is the recommended dosage for X?")
    conflict_state.retrieved_documents = [{"file": "local.pdf", "page": 1, "page_content": "Take 10mg of X."}]
    conflict_state.external_documents = [{"domain": "who.int", "snippet": "New 2026 guidelines state taking 10mg is dangerous, take 5mg instead."}]
    conflict_state.evidence_status = "SUFFICIENT"
    conflict_state = run_response_agent(conflict_state)
    print(f"Conflict Response: {conflict_state.final_response[:150]}...\n")

    print("--- Running Test 6: Emergency Query ---")
    state6 = run_orchestrator("I have severe chest pain and I can't breathe", persist_dir="chroma_db")
    print(f"Risk Level: {state6.risk_level}")
    print(f"Agent Trace: {state6.agent_trace}")
    print(f"Final Response: {state6.final_response[:100]}...\n")

    print("--- Running Test 7: Fictional disease ---")
    state7 = run_orchestrator("What does WHO recommend about XYZfictionaldisease?", persist_dir="chroma_db")
    print(f"Evidence Status: {state7.evidence_status}")
    print(f"Final Response: {state7.final_response[:100]}...\n")

    print("--- Running Test 8: PII Query ---")
    raw_query = "My name is John Doe, phone 555-1234-567, SSN is 123-45-6789, what is the latest on dengue?"
    stripped = strip_pii(raw_query)
    print(f"Raw: {raw_query}")
    print(f"Stripped: {stripped}\n")

if __name__ == "__main__":
    run_tests()
