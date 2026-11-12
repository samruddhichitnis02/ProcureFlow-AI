import datetime
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import relationship
from app.db.session import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(50), primary_key=True, index=True)
    customer_unique_id = Column(String(50), index=True)
    customer_zip_code_prefix = Column(Integer)
    customer_city = Column(String(100))
    customer_state = Column(String(10))

    orders = relationship("Order", back_populates="customer")


class Seller(Base):
    __tablename__ = "sellers"

    seller_id = Column(String(50), primary_key=True, index=True)
    seller_zip_code_prefix = Column(Integer)
    seller_city = Column(String(100))
    seller_state = Column(String(10))
    sla_score = Column(Float, default=1.0)  # 0.0 to 1.0 rating
    total_orders = Column(Integer, default=0)
    late_orders_count = Column(Integer, default=0)

    order_items = relationship("OrderItem", back_populates="seller")


class Product(Base):
    __tablename__ = "products"

    product_id = Column(String(50), primary_key=True, index=True)
    product_category_name = Column(String(100), index=True)
    product_name_lenght = Column(Integer)
    product_description_lenght = Column(Integer)
    product_photos_qty = Column(Integer)
    product_weight_g = Column(Float)
    product_length_cm = Column(Float)
    product_height_cm = Column(Float)
    product_width_cm = Column(Float)

    order_items = relationship("OrderItem", back_populates="product")


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String(50), primary_key=True, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), index=True)
    order_status = Column(String(50), index=True)
    order_purchase_timestamp = Column(DateTime, index=True)
    order_approved_at = Column(DateTime, nullable=True)
    order_delivered_carrier_date = Column(DateTime, nullable=True)
    order_delivered_customer_date = Column(DateTime, nullable=True)
    order_estimated_delivery_date = Column(DateTime, nullable=True)

    # Derived procurement telemetry fields
    delay_days = Column(Float, default=0.0)
    is_delayed = Column(Boolean, default=False, index=True)
    has_payment_issue = Column(Boolean, default=False, index=True)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("OrderPayment", back_populates="order", cascade="all, delete-orphan")
    reviews = relationship("OrderReview", back_populates="order", cascade="all, delete-orphan")
    actions = relationship("ProcurementAction", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), index=True)
    order_item_id = Column(Integer)
    product_id = Column(String(50), ForeignKey("products.product_id"), index=True)
    seller_id = Column(String(50), ForeignKey("sellers.seller_id"), index=True)
    shipping_limit_date = Column(DateTime)
    price = Column(Float)
    freight_value = Column(Float)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    seller = relationship("Seller", back_populates="order_items")


class OrderPayment(Base):
    __tablename__ = "order_payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), index=True)
    payment_sequential = Column(Integer)
    payment_type = Column(String(50))
    payment_installments = Column(Integer)
    payment_value = Column(Float)

    order = relationship("Order", back_populates="payments")


class OrderReview(Base):
    __tablename__ = "order_reviews"

    review_id = Column(String(50), primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), index=True)
    review_score = Column(Integer, index=True)
    review_comment_title = Column(String(200), nullable=True)
    review_comment_message = Column(Text, nullable=True)
    review_creation_date = Column(DateTime)
    review_answer_timestamp = Column(DateTime, nullable=True)

    order = relationship("Order", back_populates="reviews")


class ProcurementAction(Base):
    """
    Tracks actions proposed by AI Agent (Refunds, Supplier sanctions, Carrier disputes)
    and enforces Human-In-The-Loop approval for sensitive operations.
    """
    __tablename__ = "procurement_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(String(64), unique=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), index=True)
    seller_id = Column(String(50), ForeignKey("sellers.seller_id"), nullable=True)
    action_type = Column(String(50))  # "REFUND_CUSTOMER", "PENALIZE_SELLER", "ESCALATE_CARRIER", "SEND_WARNING"
    reason = Column(Text)
    amount = Column(Float, default=0.0)
    risk_level = Column(String(20), default="LOW")  # "LOW", "MEDIUM", "HIGH"
    status = Column(String(20), default="PENDING")  # "PENDING", "APPROVED", "REJECTED", "EXECUTED"
    evidence_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    order = relationship("Order", back_populates="actions")


class AuditLog(Base):
    """
    Immutable Enterprise Audit Trail for compliance, decision tracking, and failure investigation.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    trace_id = Column(String(64), index=True)
    actor = Column(String(50))  # "ProcureFlow_Agent", "Human_Officer", "System_Pipeline"
    event_type = Column(String(100), index=True)
    order_id = Column(String(50), nullable=True, index=True)
    details = Column(Text)
    latency_ms = Column(Float, nullable=True)


Index("idx_orders_status_delay", Order.order_status, Order.is_delayed)

