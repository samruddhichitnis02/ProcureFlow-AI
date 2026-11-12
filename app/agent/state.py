from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict, total=False):
    trace_id: str
    order_id: Optional[str]
    seller_id: Optional[str]
    query: str
    intent: str
    plan: List[str]
    retrieved_evidence: Dict[str, Any]
    diagnosis: Dict[str, Any]
    proposed_action: Optional[Dict[str, Any]]
    action_id: Optional[str]
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    requires_human_approval: bool
    approval_status: str  # "NONE", "PENDING_APPROVAL", "APPROVED", "REJECTED", "EXECUTED"
    final_response: str
    task_completed: bool
    evidence_accuracy_score: float
    audit_trail: List[Dict[str, Any]]
    error: Optional[str]

