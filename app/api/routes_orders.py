from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Order, Seller
from app.agent.tools import fetch_order_evidence, fetch_seller_sla_report

router = APIRouter(prefix="/api", tags=["Orders & Suppliers"])


@router.get("/orders")
def list_orders(
    delayed_only: bool = Query(False, description="Filter for delayed orders only"),
    payment_issues_only: bool = Query(False, description="Filter for payment discrepancy orders"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Lists orders with filtering for delay and payment anomalies.
    """
    query = db.query(Order)
    if delayed_only:
        query = query.filter(Order.is_delayed.is_(True))
    if payment_issues_only:
        query = query.filter(Order.has_payment_issue.is_(True))

    total = query.count()
    records = query.order_by(Order.order_purchase_timestamp.desc()).offset(offset).limit(limit).all()

    items = [
        {
            "order_id": o.order_id,
            "customer_id": o.customer_id,
            "order_status": o.order_status,
            "purchase_date": o.order_purchase_timestamp.isoformat() if o.order_purchase_timestamp else None,
            "delay_days": o.delay_days,
            "is_delayed": o.is_delayed,
            "has_payment_issue": o.has_payment_issue,
        }
        for o in records
    ]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "orders": items,
    }


@router.get("/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Retrieves full unified profile of an order (Customer, items, seller, payments, reviews).
    """
    data = fetch_order_evidence(db, order_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Order '{order_id}' not found.")
    return data


@router.get("/sellers/{seller_id}/performance")
def get_seller_performance(seller_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Calculates seller SLA score, late shipment rates, and compliance standing.
    """
    report = fetch_seller_sla_report(db, seller_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Seller '{seller_id}' not found.")
    return report

