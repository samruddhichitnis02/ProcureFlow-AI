import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.db.models import (
    Customer,
    Seller,
    Product,
    Order,
    OrderItem,
    OrderPayment,
    OrderReview,
    AuditLog,
)
from app.pipeline.transform import clean_and_normalize_order

logger = logging.getLogger(__name__)


def ingest_olist_dataset(
    db: Session,
    dataset: Dict[str, List[Dict[str, Any]]],
    batch_size: int = 500,
    trace_id: str = "init_seed",
) -> Dict[str, int]:
    """
    Ingests cleaned Olist records in bulk into the relational database.
    Logs progress and records an immutable audit entry upon completion.
    """
    stats = {}

    # 1. Customers
    customers_data = dataset.get("customers", [])
    if customers_data:
        for i in range(0, len(customers_data), batch_size):
            chunk = [Customer(**c) for c in customers_data[i : i + batch_size]]
            db.bulk_save_objects(chunk)
        db.commit()
    stats["customers"] = len(customers_data)

    # 2. Sellers
    sellers_data = dataset.get("sellers", [])
    if sellers_data:
        for i in range(0, len(sellers_data), batch_size):
            chunk = [Seller(**s) for s in sellers_data[i : i + batch_size]]
            db.bulk_save_objects(chunk)
        db.commit()
    stats["sellers"] = len(sellers_data)

    # 3. Products
    products_data = dataset.get("products", [])
    if products_data:
        for i in range(0, len(products_data), batch_size):
            chunk = [Product(**p) for p in products_data[i : i + batch_size]]
            db.bulk_save_objects(chunk)
        db.commit()
    stats["products"] = len(products_data)

    # 4. Orders (with cleaning)
    orders_data = dataset.get("orders", [])
    if orders_data:
        cleaned_orders = [clean_and_normalize_order(o) for o in orders_data]
        for i in range(0, len(cleaned_orders), batch_size):
            chunk = [Order(**o) for o in cleaned_orders[i : i + batch_size]]
            db.bulk_save_objects(chunk)
        db.commit()
    stats["orders"] = len(orders_data)

    # 5. Order Items
    items_data = dataset.get("order_items", [])
    if items_data:
        for i in range(0, len(items_data), batch_size):
            chunk = [OrderItem(**itm) for itm in items_data[i : i + batch_size]]
            db.bulk_save_objects(chunk)
        db.commit()
    stats["order_items"] = len(items_data)

    # 6. Order Payments
    payments_data = dataset.get("order_payments", [])
    if payments_data:
        for i in range(0, len(payments_data), batch_size):
            chunk = [OrderPayment(**pay) for pay in payments_data[i : i + batch_size]]
            db.bulk_save_objects(chunk)
        db.commit()
    stats["order_payments"] = len(payments_data)

    # 7. Order Reviews
    reviews_data = dataset.get("order_reviews", [])
    if reviews_data:
        for i in range(0, len(reviews_data), batch_size):
            chunk = [OrderReview(**rev) for rev in reviews_data[i : i + batch_size]]
            db.bulk_save_objects(chunk)
        db.commit()
    stats["order_reviews"] = len(reviews_data)

    # Record Audit Log
    audit = AuditLog(
        trace_id=trace_id,
        actor="System_Pipeline",
        event_type="DATASET_INGESTION_COMPLETED",
        details=f"Successfully ingested unified Olist dataset: {stats}",
    )
    db.add(audit)
    db.commit()

    return stats

