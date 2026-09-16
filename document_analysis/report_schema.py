from typing import List, Optional, Literal
from pydantic import BaseModel

Classification = Literal["LOW", "NORMAL", "HIGH", "UNKNOWN"]
ExtractionMethod = Literal["deterministic", "llm_fallback"]

class Measurement(BaseModel):
    biomarker: str
    value: float
    unit: Optional[str] = None
    ref_low: Optional[float] = None
    ref_high: Optional[float] = None
    classification: Classification = "UNKNOWN"
    page: int
    source_text: str
    extraction_method: ExtractionMethod
    extraction_confidence: float

class StructuredReport(BaseModel):
    document: str
    report_date: Optional[str] = None
    measurements: List[Measurement]

class Trend(BaseModel):
    biomarker: str
    previous: float
    latest: float
    change: float
    unit: Optional[str] = None

class ComparisonResult(BaseModel):
    reports: List[str]
    trends: List[Trend]
