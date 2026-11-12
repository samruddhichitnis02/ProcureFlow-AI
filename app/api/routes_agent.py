import uuid
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import ProcurementAction, AuditLog
from app.agent.graph import create_agent_graph
from app.agent.state import AgentState

router = APIRouter(prefix="/api/agent", tags=["Agentforce Procurement Agent"])


class InvestigateRequest(BaseModel):
    query: str = Field(..., json_schema_extra={"example": "Investigate delayed order ord_000001 and review carrier logistics"})
    order_id: Optional[str] = Field(None, json_schema_extra={"example": "ord_000001"})


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(..., json_schema_extra={"example": "APPROVED"})  # "APPROVED" or "REJECTED"
    reviewed_by: str = Field("Procurement_Officer_Alex", json_schema_extra={"example": "Procurement_Officer_Alex"})
    notes: Optional[str] = Field(None, json_schema_extra={"example": "Verified carrier tracking log. Reissue approved."})


@router.post("/investigate")
def investigate_order(req: InvestigateRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Executes the LangGraph autonomous procurement workflow:
    1. Triages customer/logistics inquiry
    2. Performs hybrid SQL + FAISS evidence retrieval
    3. Synthesizes fulfillment root-cause diagnosis
    4. Evaluates risk guardrails
    5. Dispatches to autonomous execution or places in Human-In-The-Loop approval queue
    """
    start_time = time.perf_counter()
    trace_id = f"trace_{uuid.uuid4().hex[:12]}"

    graph = create_agent_graph(db)

    initial_state: AgentState = {
        "trace_id": trace_id,
        "query": req.query,
        "order_id": req.order_id,
        "audit_trail": [],
    }

    try:
        final_state = graph.invoke(initial_state)
    except Exception as e:
        db.add(
            AuditLog(
                trace_id=trace_id,
                actor="ProcureFlow_Agent",
                event_type="INVESTIGATION_ERROR",
                order_id=req.order_id,
                details=f"Workflow failed: {str(e)}",
            )
        )
        db.commit()
        raise HTTPException(status_code=500, detail=f"Agent workflow failed: {str(e)}")

    elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

    return {
        "trace_id": trace_id,
        "order_id": final_state.get("order_id"),
        "intent": final_state.get("intent"),
        "plan": final_state.get("plan"),
        "diagnosis": final_state.get("diagnosis"),
        "proposed_action": final_state.get("proposed_action"),
        "action_id": final_state.get("action_id"),
        "risk_level": final_state.get("risk_level"),
        "approval_status": final_state.get("approval_status"),
        "requires_human_approval": final_state.get("requires_human_approval"),
        "evidence_accuracy_score": final_state.get("evidence_accuracy_score"),
        "final_response": final_state.get("final_response"),
        "latency_ms": elapsed_ms,
        "retrieved_evidence": {
            "order_found": final_state.get("retrieved_evidence", {}).get("order_sql") is not None,
            "semantic_review_matches": len(
                final_state.get("retrieved_evidence", {}).get("semantic_reviews", [])
            ),
        },
        "audit_trail": final_state.get("audit_trail"),
    }


@router.get("/pending-approvals")
def get_pending_approvals(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Lists all high-risk procurement actions quarantined for Human-In-The-Loop review.
    """
    actions = (
        db.query(ProcurementAction)
        .filter(ProcurementAction.status == "PENDING")
        .order_by(ProcurementAction.created_at.desc())
        .all()
    )

    return [
        {
            "action_id": a.action_id,
            "order_id": a.order_id,
            "seller_id": a.seller_id,
            "action_type": a.action_type,
            "amount": a.amount,
            "risk_level": a.risk_level,
            "reason": a.reason,
            "status": a.status,
            "evidence_summary": a.evidence_summary,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in actions
    ]


@router.post("/approve/{action_id}")
def resolve_human_approval(
    action_id: str,
    req: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Enforces Human-In-The-Loop authorization:
    Procurement officer approves or rejects a quarantined high-risk action.
    """
    action = (
        db.query(ProcurementAction)
        .filter(ProcurementAction.action_id == action_id)
        .first()
    )

    if not action:
        raise HTTPException(status_code=404, detail=f"Action '{action_id}' not found.")

    decision = req.decision.upper()
    if decision not in ("APPROVED", "REJECTED"):
        raise HTTPException(
            status_code=400,
            detail="Invalid decision. Must be 'APPROVED' or 'REJECTED'.",
        )

    action.status = decision
    action.reviewed_by = req.reviewed_by
    action.reviewed_at = datetime.utcnow()
    action.resolution_notes = req.notes

    # Immutable audit logging
    audit = AuditLog(
        trace_id=f"audit_{action_id}",
        actor=f"Human_Officer_{req.reviewed_by}",
        event_type=f"ACTION_{decision}",
        order_id=action.order_id,
        details=(
            f"Officer {req.reviewed_by} marked action '{action_id}' ({action.action_type}) "
            f"as {decision}. Notes: {req.notes or 'None'}"
        ),
    )
    db.add(audit)
    db.commit()

    return {
        "action_id": action.action_id,
        "status": action.status,
        "reviewed_by": action.reviewed_by,
        "reviewed_at": action.reviewed_at.isoformat(),
        "notes": action.resolution_notes,
    }
