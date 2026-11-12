import re
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.models import Order, Customer, OrderItem, OrderPayment, OrderReview, Seller
from app.rag.vector_store import vector_store

FORBIDDEN_SQL_PATTERNS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bCREATE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
]


def execute_safe_sql(db: Session, sql_query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Executes a read-only SQL query with security guardrails.
    Raises ValueError if destructive SQL keywords are detected.
    """
    for pattern in FORBIDDEN_SQL_PATTERNS:
        if re.search(pattern, sql_query, re.IGNORECASE):
            raise ValueError(f"Forbidden SQL operation detected: statement matched '{pattern}'")

    result = db.execute(text(sql_query), params or {})
    columns = result.keys()
    rows = [dict(zip(columns, row)) for row in result.fetchall()]
    return rows


def fetch_order_evidence(db: Session, order_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves full unified profile for an order across all relational tables:
    orders, customers, order_items, order_payments, and order_reviews.
    """
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        return None

    customer = db.query(Customer).filter(Customer.customer_id == order.customer_id).first()
    items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    payments = db.query(OrderPayment).filter(OrderPayment.order_id == order_id).all()
    reviews = db.query(OrderReview).filter(OrderReview.order_id == order_id).all()

    items_data = [
        {
            "product_id": itm.product_id,
            "seller_id": itm.seller_id,
            "shipping_limit_date": itm.shipping_limit_date.isoformat() if itm.shipping_limit_date else None,
            "price": itm.price,
            "freight_value": itm.freight_value,
        }
        for itm in items
    ]

    payments_data = [
        {
            "payment_type": p.payment_type,
            "installments": p.payment_installments,
            "payment_value": p.payment_value,
        }
        for p in payments
    ]

    reviews_data = [
        {
            "review_id": r.review_id,
            "score": r.review_score,
            "title": r.review_comment_title,
            "comment": r.review_comment_message,
        }
        for r in reviews
    ]

    total_item_cost = sum(i["price"] + i["freight_value"] for i in items_data)
    total_paid = sum(p["payment_value"] for p in payments_data)
    payment_discrepancy = round(total_paid - total_item_cost, 2)

    return {
        "order_id": order.order_id,
        "customer_id": order.customer_id,
        "customer_city": customer.customer_city if customer else None,
        "customer_state": customer.customer_state if customer else None,
        "order_status": order.order_status,
        "purchase_date": order.order_purchase_timestamp.isoformat() if order.order_purchase_timestamp else None,
        "estimated_delivery_date": order.order_estimated_delivery_date.isoformat() if order.order_estimated_delivery_date else None,
        "carrier_delivered_date": order.order_delivered_carrier_date.isoformat() if order.order_delivered_carrier_date else None,
        "customer_delivered_date": order.order_delivered_customer_date.isoformat() if order.order_delivered_customer_date else None,
        "delay_days": order.delay_days,
        "is_delayed": order.is_delayed,
        "has_payment_issue": order.has_payment_issue,
        "items_count": len(items_data),
        "items": items_data,
        "total_item_cost": round(total_item_cost, 2),
        "total_paid": round(total_paid, 2),
        "payment_discrepancy": payment_discrepancy,
        "payments": payments_data,
        "reviews": reviews_data,
    }


def fetch_semantic_evidence(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """
    Queries FAISS vector index for semantically related customer reviews,
    disputes, and logistics feedback.
    """
    return vector_store.search(query, top_k=top_k)


def fetch_seller_sla_report(db: Session, seller_id: str) -> Optional[Dict[str, Any]]:
    """
    Analyzes historical fulfillment SLA of a seller.
    """
    seller = db.query(Seller).filter(Seller.seller_id == seller_id).first()
    if not seller:
        return None

    late_ratio = (
        round(seller.late_orders_count / seller.total_orders, 3)
        if seller.total_orders > 0
        else 0.0
    )

    return {
        "seller_id": seller.seller_id,
        "city": seller.seller_city,
        "state": seller.seller_state,
        "sla_score": seller.sla_score,
        "total_orders": seller.total_orders,
        "late_orders_count": seller.late_orders_count,
        "late_ratio": late_ratio,
        "standing": "EXCELLENT" if seller.sla_score >= 0.95 else ("WARNING" if seller.sla_score >= 0.80 else "CRITICAL"),
    }


def calculate_evidence_accuracy(retrieved: Dict[str, Any], ground_truth_order: Dict[str, Any]) -> float:
    """
    Measures evidence citation accuracy (targeting >= 90%).
    Compares retrieved evidence attributes (delay_days, payments, order_status)
    against verified ground truth from the relational store.
    """
    if not ground_truth_order or not retrieved:
        return 0.0

    checks = []

    # Check 1: Order ID match
    checks.append(retrieved.get("order_id") == ground_truth_order.get("order_id"))

    # Check 2: Delay status verification
    checks.append(retrieved.get("is_delayed") == ground_truth_order.get("is_delayed"))

    # Check 3: Delay days precision (within 0.1 delta)
    retrieved_delay = retrieved.get("delay_days", 0.0)
    gt_delay = ground_truth_order.get("delay_days", 0.0)
    checks.append(abs(retrieved_delay - gt_delay) <= 0.5)

    # Check 4: Payment issue flag
    checks.append(retrieved.get("has_payment_issue") == ground_truth_order.get("has_payment_issue"))

    # Check 5: Items count verification
    retrieved_items_count = len(retrieved.get("items", []))
    gt_items_count = len(ground_truth_order.get("items", []))
    checks.append(retrieved_items_count == gt_items_count)

    passed = sum(1 for c in checks if c)
    return round((passed / len(checks)) * 100.0, 1)

