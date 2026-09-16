import os
from rag_chain import answer as rag_answer
from safety import screen as safety_screen

def search_medical_knowledge(query: str, persist_dir: str = "chroma_db") -> dict:
    """Wrapper around existing RAG chain to search medical knowledge."""
    return rag_answer(query, persist_dir=persist_dir)

def read_uploaded_document(query: str, persist_dir: str = "chroma_db") -> dict:
    """Wrapper around existing RAG chain, conceptually for uploaded reports."""
    return rag_answer(query, persist_dir=persist_dir)

def run_safety_check(query: str) -> dict:
    """Wrapper around deterministic regex safety screen."""
    return safety_screen(query)
