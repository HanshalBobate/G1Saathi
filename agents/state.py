from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class AgentState(BaseModel):
    user_query: str
    conversation_context: List[Dict[str, str]] = Field(default_factory=list)
    intent: Optional[str] = None
    risk_level: str = "LOW"
    required_tools: List[str] = Field(default_factory=list)
    retrieved_documents: List[Any] = Field(default_factory=list)
    document_context: Optional[str] = None
    safety_result: Dict[str, Any] = Field(default_factory=dict)
    evidence_status: Optional[str] = None  # SUFFICIENT, PARTIAL, INSUFFICIENT
    final_response: Optional[str] = None
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    agent_trace: List[str] = Field(default_factory=list)
    external_documents: List[Dict[str, Any]] = Field(default_factory=list)
    research_attempts: int = 0
    needs_current_info: bool = False
    evidence_quality_metrics: Dict[str, Any] = Field(default_factory=dict)
    extracted_claims: List[Dict[str, Any]] = Field(default_factory=list)
    retrieval_diagnostics: Dict[str, Any] = Field(default_factory=dict)
    language: str = "en"
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    expanded_queries: List[str] = Field(default_factory=list)
    report_measurements: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Phase 7: Workflow & Planning Additions
    task_plan: Optional[Any] = None  # Will hold TaskPlan
    information_gap: Optional[Dict[str, Any]] = None
    next_steps: List[str] = Field(default_factory=list)
    tool_calls: Dict[str, int] = Field(default_factory=dict)
