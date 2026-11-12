from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import AuditLog

router = APIRouter(prefix="/api/audit-logs", tags=["Audit & Compliance"])


@router.get("")
def list_audit_logs(
    actor: Optional[str] = Query(None, description="Filter by actor"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    order_id: Optional[str] = Query(None, description="Filter by order ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns immutable audit entries for compliance, workflow investigation, and security tracking.
    """
    query = db.query(AuditLog)
    if actor:
        query = query.filter(AuditLog.actor.ilike(f"%{actor}%"))
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    if order_id:
        query = query.filter(AuditLog.order_id == order_id)

    total = query.count()
    records = (
        query.order_by(AuditLog.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "trace_id": log.trace_id,
            "actor": log.actor,
            "event_type": log.event_type,
            "order_id": log.order_id,
            "details": log.details,
            "latency_ms": log.latency_ms,
        }
        for log in records
    ]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "logs": items,
    }

