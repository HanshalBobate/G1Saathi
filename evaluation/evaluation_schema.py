from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class EvaluationCategory(str, Enum):
    LOCAL_KB = "LOCAL_KB"
    CURRENT_INFORMATION = "CURRENT_INFORMATION"
    MULTILINGUAL = "MULTILINGUAL"
    EMERGENCY = "EMERGENCY"
    FICTIONAL_DISEASE = "FICTIONAL_DISEASE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    GROUNDING = "GROUNDING"
    REPORT_ANALYSIS = "REPORT_ANALYSIS"
    REPORT_COMPARISON = "REPORT_COMPARISON"
    PII_PROTECTION = "PII_PROTECTION"

class EvaluationExpectedBehavior(BaseModel):
    evidence_status: Optional[List[str]] = Field(default=None, description="Expected evidence statuses like SUFFICIENT, INSUFFICIENT, etc.")
    external_research: Optional[bool] = Field(default=None, description="Whether external research should be triggered")
    emergency: Optional[bool] = Field(default=None, description="Whether safety emergency gate should be triggered")
    rag_bypassed: Optional[bool] = Field(default=None, description="Whether normal RAG should be bypassed")
    insufficient_evidence: Optional[bool] = Field(default=None, description="Whether the answer should indicate insufficient evidence")
    pii_scrubbed: Optional[bool] = Field(default=None, description="Check if PII was scrubbed")
    # specific to reports
    biomarker: Optional[str] = None
    expected_previous: Optional[float] = None
    expected_latest: Optional[float] = None
    expected_change: Optional[float] = None
    
class EvaluationTestCase(BaseModel):
    id: str
    category: EvaluationCategory
    query: str
    files: Optional[List[str]] = Field(default_factory=list, description="List of file names to include in the context")
    expected: EvaluationExpectedBehavior

class EvaluationResult(BaseModel):
    question_id: str
    category: str
    query: str
    expected_behavior: Dict[str, Any]
    actual_status: str
    evidence_coverage: float
    claims_supported: float
    emergency_triggered: bool
    external_research_used: bool
    llm_calls: int
    vector_searches: int
    passed: bool
    reason: str = ""
    duration_sec: float
    workflow_steps: List[str] = Field(default_factory=list)
