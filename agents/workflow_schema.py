from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

class TaskType(str, Enum):
    GENERAL_INFORMATION = "GENERAL_INFORMATION"
    MEDICAL_ENTITY_INFORMATION = "MEDICAL_ENTITY_INFORMATION"
    CURRENT_INFORMATION = "CURRENT_INFORMATION"
    MEDICAL_REPORT_ANALYSIS = "MEDICAL_REPORT_ANALYSIS"
    REPORT_COMPARISON = "REPORT_COMPARISON"
    EMERGENCY = "EMERGENCY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

class TaskPlan(BaseModel):
    task_type: TaskType
    requires_rag: bool = False
    requires_external_research: bool = False
    requires_document_analysis: bool = False
    requires_comparison: bool = False
    language: str = "en"
    steps: List[str] = Field(default_factory=list)

class InformationGap(BaseModel):
    status: str  # "COMPLETE" or "MISSING_INFORMATION"
    missing: List[str] = Field(default_factory=list)
    message: Optional[str] = None
