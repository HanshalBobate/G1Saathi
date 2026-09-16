import json
import os
import re

# Load the ontology once
ONTOLOGY_PATH = os.path.join(os.path.dirname(__file__), "medical_ontology.json")
with open(ONTOLOGY_PATH, "r", encoding="utf-8") as f:
    ONTOLOGY = json.load(f)

def extract_entities(query: str) -> list:
    """
    Detect medical entities in the query based on the ontology.
    Returns a list of dicts with mention, canonical_name, and category.
    """
    query_lower = query.lower()
    entities_found = []
    
    # Sort ontology entries by the length of their longest alias descending
    # to match longer phrases first (e.g., "high blood pressure" before "blood")
    sorted_ontology = sorted(
        ONTOLOGY, 
        key=lambda x: max((len(a) for a in x.get("aliases", [])), default=0), 
        reverse=True
    )
    
    for entry in sorted_ontology:
        canonical = entry.get("canonical_name", "")
        category = entry.get("category", "unknown")
        aliases = entry.get("aliases", [])
        
        # Sort aliases by length descending
        aliases = sorted(aliases, key=len, reverse=True)
        
        for alias in aliases:
            alias_lower = alias.lower()
            
            # Simple boundary check for Latin characters, 
            # and exact string inclusion for non-Latin to avoid complex unicode \b issues
            if re.search(r'[a-z]', alias_lower):
                pattern = r'\b' + re.escape(alias_lower) + r'\b'
                match = re.search(pattern, query_lower)
                if match:
                    entities_found.append({
                        "mention": match.group(0),
                        "canonical_name": canonical,
                        "category": category,
                        "related_terms": entry.get("related_terms", [])
                    })
                    # Replace the matched text with blanks to prevent sub-matching
                    query_lower = query_lower[:match.start()] + (" " * len(match.group(0))) + query_lower[match.end():]
                    break  # Found the longest match for this entity, move to next entity
            else:
                # Non-Latin (Hindi/Marathi)
                idx = query_lower.find(alias_lower)
                if idx != -1:
                    entities_found.append({
                        "mention": alias,
                        "canonical_name": canonical,
                        "category": category,
                        "related_terms": entry.get("related_terms", [])
                    })
                    query_lower = query_lower[:idx] + (" " * len(alias_lower)) + query_lower[idx + len(alias_lower):]
                    break
                    
    return entities_found
