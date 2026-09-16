from typing import List, Dict, Any
from document_analysis.report_schema import Trend

def compare_reports(report_a: List[Dict[str, Any]], report_b: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Compares two structured reports deterministically.
    report_a is chronologically older (previous).
    report_b is chronologically newer (latest).
    """
    trends = []
    
    # Index older report by canonical biomarker
    prev_map = {m["biomarker"]: m for m in report_a if "biomarker" in m}
    
    for latest in report_b:
        biomarker = latest.get("biomarker")
        if not biomarker:
            continue
            
        previous = prev_map.get(biomarker)
        if not previous:
            continue
            
        # Ensure units match exactly before comparing
        prev_unit = previous.get("unit")
        latest_unit = latest.get("unit")
        if prev_unit != latest_unit:
            # Cannot compare mismatches deterministically without conversion matrix
            continue
            
        try:
            prev_val = float(previous.get("value"))
            latest_val = float(latest.get("value"))
        except (TypeError, ValueError):
            continue
            
        change = round(latest_val - prev_val, 3)
        
        trend = Trend(
            biomarker=biomarker,
            previous=prev_val,
            latest=latest_val,
            change=change,
            unit=latest_unit
        )
        trends.append(trend.model_dump())
        
    return trends
