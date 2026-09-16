import re
import json
import logging
from typing import List, Dict, Any, Tuple

from langchain_core.prompts import ChatPromptTemplate
from models import get_chat_model
from document_analysis.validator import get_ontology, validate_measurement
from document_analysis.report_schema import Measurement

logger = logging.getLogger(__name__)

# Compile regexes for performance
# Matches "12 - 16", "12.0-16.0", "12 to 16", "12–16"
RANGE_PATTERN = re.compile(r'([\d\.]+)\s*(?:-|to|–|—)\s*([\d\.]+)')
# Matches "< 100", "<= 100", "> 60", ">= 60"
ONE_SIDED_PATTERN = re.compile(r'(<|<=|>|>=)\s*([\d\.]+)')

def parse_reference_range(range_str: str) -> Tuple[float, float]:
    """Parse string reference ranges into (low, high) floats. Returns None for bounds if missing."""
    if not range_str:
        return None, None
        
    m = RANGE_PATTERN.search(range_str)
    if m:
        try:
            return float(m.group(1)), float(m.group(2))
        except ValueError:
            pass
            
    m = ONE_SIDED_PATTERN.search(range_str)
    if m:
        op = m.group(1)
        try:
            val = float(m.group(2))
            if op in ["<", "<="]:
                return None, val
            else:
                return val, None
        except ValueError:
            pass
            
    return None, None

def _get_all_aliases() -> List[Tuple[str, str, List[str]]]:
    """Returns [(canonical_name, alias_regex, units), ...]"""
    ontology = get_ontology()
    aliases = []
    for category, tests in ontology.items():
        for test in tests:
            canonical = test["canonical_name"]
            units = test.get("units", [])
            # Sort aliases by length descending so "Fasting Blood Glucose" matches before "Glucose"
            sorted_aliases = sorted(test.get("aliases", []), key=len, reverse=True)
            for alias in sorted_aliases:
                # Escape alias for regex and add word boundaries
                alias_regex = r'\b' + re.escape(alias) + r'\b'
                aliases.append((canonical, alias_regex, units))
    return aliases

def extract_measurements_deterministic(text: str, page_num: int) -> List[Measurement]:
    """
    Primary deterministic extraction using Regex and Ontology.
    Scans each line for known biomarkers and extracts values/ranges nearby.
    """
    aliases = _get_all_aliases()
    measurements = []
    lines = text.split('\n')
    
    for line in lines:
        if not line.strip():
            continue
            
        for canonical, alias_regex, units in aliases:
            # Look for alias in line (case insensitive)
            match = re.search(alias_regex, line, re.IGNORECASE)
            if match:
                # We found a biomarker name. Let's try to parse the rest of the line.
                # Common pattern: Biomarker: 11.2 g/dL 12-16
                # Replace the alias so we don't accidentally parse numbers inside the alias
                remainder = line[:match.start()] + " " + line[match.end():]
                
                # Find all numbers in the remainder
                # Using a regex to find numbers (including decimals), but ignoring things attached to letters (unless separated by space)
                # We want independent numbers or numbers followed by a unit
                num_matches = list(re.finditer(r'(?<![a-zA-Z])(\d+\.?\d*)(?![a-zA-Z]\w*)', remainder))
                
                if not num_matches:
                    # Ambiguous case: found biomarker but no numbers. Might be table format spanning lines.
                    # We will rely on LLM fallback for this specific line if needed.
                    continue
                    
                # Assume the first number is the value
                value_str = num_matches[0].group(1)
                try:
                    value = float(value_str)
                except ValueError:
                    continue
                    
                # Find unit
                found_unit = None
                for u in units:
                    if u.lower() in remainder.lower():
                        found_unit = u
                        break
                        
                # Find reference range on the same line
                ref_low, ref_high = parse_reference_range(remainder)
                
                # If not found, look ahead up to 2 lines
                if ref_low is None and ref_high is None:
                    # Find current line index
                    idx = lines.index(line)
                    for ahead_idx in range(idx + 1, min(idx + 3, len(lines))):
                        ahead_line = lines[ahead_idx]
                        if "reference" in ahead_line.lower() or "range" in ahead_line.lower() or "normal" in ahead_line.lower():
                            ref_low, ref_high = parse_reference_range(ahead_line)
                            if ref_low is not None or ref_high is not None:
                                break
                
                raw_data = {
                    "biomarker": canonical,
                    "value": value,
                    "unit": found_unit,
                    "ref_low": ref_low,
                    "ref_high": ref_high,
                    "page": page_num,
                    "source_text": line.strip(),
                    "extraction_method": "deterministic",
                    "extraction_confidence": 0.9 if found_unit else 0.7
                }
                
                try:
                    validated = validate_measurement(raw_data)
                    measurements.append(validated)
                except ValueError as e:
                    logger.debug(f"Validation failed for deterministic match: {e}")
                
                # Only match one biomarker per line to prevent chaos (usually true for reports)
                break 
                
    return measurements

def _llm_fallback(snippet: str, page_num: int) -> List[Measurement]:
    """Uses LLM ONLY for ambiguous snippets where deterministic parsing failed."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a strictly constrained data extractor. 
Extract biomarker measurements from the provided snippet.
Return a JSON array of objects:
[{"biomarker": "canonical name", "value": number, "unit": "unit or null", "ref_low": number or null, "ref_high": number or null}]

Rules:
1. DO NOT invent values, units, or ranges.
2. If no valid numeric value is associated with a biomarker, return [].
3. Only output valid JSON."""),
        ("human", "{text}")
    ])
    
    llm = get_chat_model()
    try:
        response = (prompt | llm).invoke({"text": snippet})
        content = response.content.strip()
        if content.startswith("```json"): content = content[7:]
        if content.endswith("```"): content = content[:-3]
        
        data = json.loads(content.strip())
        results = []
        for item in data:
            item["page"] = page_num
            item["source_text"] = snippet.strip()
            item["extraction_method"] = "llm_fallback"
            item["extraction_confidence"] = 0.5
            try:
                results.append(validate_measurement(item))
            except ValueError:
                pass
        return results
    except Exception as e:
        logger.debug(f"LLM fallback failed: {e}")
        return []

def parse_medical_report(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Parses full page-aware document text.
    Returns structured measurements as dicts for compatibility with upstream.
    """
    measurements = []
    
    for page in pages:
        page_num = page.get("page", 1)
        text = page.get("text", "")
        
        # 1. Deterministic Extraction
        det_measurements = extract_measurements_deterministic(text, page_num)
        measurements.extend(det_measurements)
        
        # 2. LLM Fallback (Optional)
        # We could run LLM fallback on lines that contained a biomarker alias but deterministic failed.
        # For simplicity and performance, we rely mostly on deterministic. 
        # If the user wants we can do a pass over unparsed lines.
        aliases = _get_all_aliases()
        parsed_biomarkers = set(m.biomarker for m in det_measurements)
        
        for line in text.split('\n'):
            if not line.strip(): continue
            for canonical, alias_regex, units in aliases:
                if canonical not in parsed_biomarkers:
                    if re.search(alias_regex, line, re.IGNORECASE):
                        # Found a biomarker that wasn't parsed deterministically!
                        # Send this specific snippet to LLM fallback
                        fb = _llm_fallback(line, page_num)
                        if fb:
                            measurements.extend(fb)
                            parsed_biomarkers.update(m.biomarker for m in fb)
                        break

    # Convert back to dicts for the existing pipeline
    return [m.model_dump() for m in measurements]
