import logging
import os
from typing import List, Dict, Any
from langchain_community.document_loaders import PyPDFLoader

logger = logging.getLogger(__name__)

def extract_pdf_pages(file_path: str) -> List[Dict[str, Any]]:
    """
    Extract text from a PDF file while strictly maintaining page boundaries and provenance.
    Returns a list of dictionaries: [{"page": 1, "text": "..."}, ...]
    """
    if not os.path.isfile(file_path):
        logger.error(f"File not found: {file_path}")
        return []
        
    try:
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        
        pages = []
        for doc in docs:
            # PyPDFLoader returns 0-indexed pages in metadata usually, we'll make it 1-indexed for UI.
            page_num = doc.metadata.get('page', 0) + 1 
            pages.append({
                "page": page_num,
                "text": doc.page_content
            })
            
        return pages
    except Exception as e:
        logger.exception(f"Failed to extract text from {file_path}: {e}")
        return []
