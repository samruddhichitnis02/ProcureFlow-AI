from datetime import datetime, timedelta
from app.pipeline.generator import OlistDataGenerator
from app.pipeline.transform import (
    clean_and_normalize_order,
    detect_payment_discrepancy,
    compute_seller_sla,
)


def test_olist_data_generator():
    gen = OlistDataGenerator(seed=99)
    dataset = gen.generate_dataset(num_customers=20, num_sellers=5, num_products=10, num_orders=25)

    assert len(dataset["customers"]) == 20
    assert len(dataset["sellers"]) == 5
    assert len(dataset["products"]) == 10
    assert len(dataset["orders"]) == 25
    assert len(dataset["order_items"]) >= 25
    assert len(dataset["order_payments"]) == 25
    assert len(dataset["order_reviews"]) == 25


def test_clean_and_normalize_order_delay():
    est = datetime(2023, 5, 10, 12, 0)
    delivered = datetime(2023, 5, 15, 12, 0)  # 5 days late

    order = {
        "order_id": "test_ord_1",
        "order_estimated_delivery_date": est.isoformat(),
        "order_delivered_customer_date": delivered.isoformat(),
    }
    cleaned = clean_and_normalize_order(order)
    assert cleaned["is_delayed"] is True
    assert cleaned["delay_days"] == 5.0


def test_detect_payment_discrepancy():
    items = [{"price": 100.0, "freight_value": 20.0}]
    payments_matching = [{"payment_value": 120.0}]
    result_ok = detect_payment_discrepancy(items, payments_matching)
    assert result_ok["has_issue"] is False
    assert result_ok["discrepancy_amount"] == 0.0

    payments_underpaid = [{"payment_value": 80.0}]
    result_bad = detect_payment_discrepancy(items, payments_underpaid)
    assert result_bad["has_issue"] is True
    assert result_bad["discrepancy_amount"] == -40.0


def test_compute_seller_sla():
    assert compute_seller_sla(100, 5) == 0.95
    assert compute_seller_sla(50, 10) == 0.80
    assert compute_seller_sla(0, 0) == 1.0

