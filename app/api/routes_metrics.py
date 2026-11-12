import time
import numpy as np
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Order, Seller, ProcurementAction, AuditLog
from app.agent.tools import fetch_order_evidence, fetch_semantic_evidence
from app.config import settings

router = APIRouter(prefix="/api/metrics", tags=["Performance & Metrics"])


@router.get("/p95-benchmark")
def run_latency_benchmark(
    samples: int = 100, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Executes automated performance latency benchmark for non-generation operations:
    - SQL relational order profile retrieval (joins across 5 tables)
    - FAISS vector index similarity search
    - SLA calculations

    Measures latency across n iterations and evaluates p50, p90, p95, p99 against the < 800ms target.
    """
    # Sample real order IDs from the database
    orders = db.query(Order.order_id).limit(min(samples, 200)).all()
    if not orders:
        return {"error": "Database has no orders. Seed data first."}

    order_ids = [o[0] for o in orders]
    latencies_ms: List[float] = []

    for i in range(samples):
        oid = order_ids[i % len(order_ids)]
        t_start = time.perf_counter()

        # Non-generation retrieval workload:
        # 1. SQL multi-table join
        _ = fetch_order_evidence(db, oid)
        # 2. FAISS vector search
        _ = fetch_semantic_evidence(f"delay problem with order {oid}", top_k=3)

        t_end = time.perf_counter()
        latencies_ms.append((t_end - t_start) * 1000.0)

    arr = np.array(latencies_ms)
    p50 = round(float(np.percentile(arr, 50)), 2)
    p90 = round(float(np.percentile(arr, 90)), 2)
    p95 = round(float(np.percentile(arr, 95)), 2)
    p99 = round(float(np.percentile(arr, 99)), 2)
    avg_lat = round(float(np.mean(arr)), 2)

    meets_sla = p95 < settings.TARGET_P95_LATENCY_MS

    return {
        "samples_executed": samples,
        "sla_target_ms": settings.TARGET_P95_LATENCY_MS,
        "meets_target": meets_sla,
        "p50_latency_ms": p50,
        "p90_latency_ms": p90,
        "p95_latency_ms": p95,
        "p99_latency_ms": p99,
        "avg_latency_ms": avg_lat,
        "min_latency_ms": round(float(np.min(arr)), 2),
        "max_latency_ms": round(float(np.max(arr)), 2),
        "status": "PASS: Exceeds SLA Performance Requirement" if meets_sla else "FAIL: Exceeds SLA threshold",
    }


@router.get("/summary")
def get_metrics_summary(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns enterprise high-level KPIs across orders, delays, SLA compliance, and human approval queue.
    """
    total_orders = db.query(Order).count()
    delayed_orders = db.query(Order).filter(Order.is_delayed.is_(True)).count()
    payment_issues = db.query(Order).filter(Order.has_payment_issue.is_(True)).count()

    total_sellers = db.query(Seller).count()
    pending_approvals = (
        db.query(ProcurementAction)
        .filter(ProcurementAction.status == "PENDING")
        .count()
    )
    total_actions = db.query(ProcurementAction).count()
    audit_logs_count = db.query(AuditLog).count()

    delay_rate_pct = round((delayed_orders / total_orders * 100.0), 2) if total_orders else 0.0

    return {
        "total_orders": total_orders,
        "delayed_orders": delayed_orders,
        "delayed_rate_percent": delay_rate_pct,
        "payment_issue_orders": payment_issues,
        "total_sellers": total_sellers,
        "pending_human_approvals": pending_approvals,
        "total_procurement_actions": total_actions,
        "audit_logs_count": audit_logs_count,
        "p95_latency_target_ms": settings.TARGET_P95_LATENCY_MS,
    }

