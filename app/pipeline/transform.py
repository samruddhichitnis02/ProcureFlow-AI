from datetime import datetime
from typing import Dict, Any, List


def clean_and_normalize_order(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cleans raw order records:
    - Normalizes null timestamps
    - Computes delay days against delivery SLA
    - Flags late delivery anomalies
    """
    cleaned = dict(order_data)
    est_date = cleaned.get("order_estimated_delivery_date")
    delivered_date = cleaned.get("order_delivered_customer_date")

    delay_days = 0.0
    is_delayed = False

    if isinstance(est_date, str):
        est_date = datetime.fromisoformat(est_date)
        cleaned["order_estimated_delivery_date"] = est_date

    if isinstance(delivered_date, str):
        delivered_date = datetime.fromisoformat(delivered_date)
        cleaned["order_delivered_customer_date"] = delivered_date

    if delivered_date and est_date:
        if delivered_date > est_date:
            delta = delivered_date - est_date
            delay_days = round(delta.total_seconds() / 86400.0, 2)
            is_delayed = delay_days > 0.0

    cleaned["delay_days"] = delay_days
    cleaned["is_delayed"] = is_delayed
    return cleaned


def detect_payment_discrepancy(
    items: List[Dict[str, Any]], payments: List[Dict[str, Any]], tolerance: float = 0.05
) -> Dict[str, Any]:
    """
    Calculates expected sum (price + freight) vs actual payments received.
    Returns discrepancy amount and flag.
    """
    expected_sum = sum(
        float(item.get("price", 0.0)) + float(item.get("freight_value", 0.0))
        for item in items
    )
    actual_sum = sum(float(p.get("payment_value", 0.0)) for p in payments)

    difference = round(actual_sum - expected_sum, 2)
    has_discrepancy = abs(difference) > tolerance

    return {
        "expected_total": round(expected_sum, 2),
        "actual_paid": round(actual_sum, 2),
        "discrepancy_amount": difference,
        "has_issue": has_discrepancy,
    }


def compute_seller_sla(total_orders: int, late_orders: int) -> float:
    """
    Computes SLA compliance score from 0.0 to 1.0.
    """
    if total_orders <= 0:
        return 1.0
    rate = (total_orders - late_orders) / float(total_orders)
    return round(max(0.0, min(1.0, rate)), 3)

