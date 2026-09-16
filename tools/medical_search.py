import re
import time
from urllib.parse import urlparse
import logging

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

logger = logging.getLogger(__name__)

TRUSTED_DOMAINS = [
    "who.int",
    "cdc.gov",
    "nih.gov",
    "nlm.nih.gov",
    "medlineplus.gov",
    "fda.gov",
    "nhs.uk"
]

def strip_pii(query: str) -> str:
    """Lightweight regex-based PII stripper for external search queries."""
    # Remove email addresses
    query = re.sub(r'[\w\.-]+@[\w\.-]+', '', query)
    # Remove phone numbers (simplified)
    query = re.sub(r'\+?\d[\d -]{8,12}\d', '', query)
    # Remove SSN-like or long numbers
    query = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '', query)
    # Basic attempt to remove greeting names (e.g. "My name is John")
    query = re.sub(r'(my name is|i am) [A-Z][a-z]+ [A-Z][a-z]+', '', query, flags=re.IGNORECASE)
    return query.strip()

def search_trusted_sources(query: str, max_results: int = 5) -> list:
    """
    Searches DuckDuckGo but restricts results to TRUSTED_DOMAINS.
    Returns normalized results.
    """
    if DDGS is None:
        logger.warning("duckduckgo_search is not installed.")
        return []
        
    safe_query = strip_pii(query)
    
    try:
        ddgs = DDGS()
        # Fetch a larger pool to filter down
        results = list(ddgs.text(safe_query, max_results=30))
    except Exception as e:
        logger.error(f"DDG search failed: {e}")
        return []

    verified_results = []
    seen_urls = set()
    
    for r in results:
        url = r.get("href", "")
        if url in seen_urls:
            continue
            
        try:
            domain = urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
        except Exception:
            continue
            
        is_trusted = any(domain == trusted or domain.endswith("." + trusted) for trusted in TRUSTED_DOMAINS)
        
        if is_trusted:
            verified_results.append({
                "title": r.get("title", ""),
                "url": url,
                "source": domain,
                "domain": domain,
                "snippet": r.get("body", ""),
                "retrieved_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            seen_urls.add(url)
            
            if len(verified_results) >= max_results:
                break
                
    return verified_results
