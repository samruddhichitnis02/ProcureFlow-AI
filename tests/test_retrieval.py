import pytest
from app.agent.tools import (
    execute_safe_sql,
    fetch_order_evidence,
    fetch_semantic_evidence,
    fetch_seller_sla_report,
)
from app.rag.vector_store import vector_store


def test_safe_sql_execution(test_db_session):
    rows = execute_safe_sql(test_db_session, "SELECT count(*) as cnt FROM orders")
    assert len(rows) == 1
    assert rows[0]["cnt"] >= 60


def test_forbidden_sql_guardrail(test_db_session):
    with pytest.raises(ValueError, match="Forbidden SQL operation detected"):
        execute_safe_sql(test_db_session, "DROP TABLE orders")

    with pytest.raises(ValueError, match="Forbidden SQL operation detected"):
        execute_safe_sql(test_db_session, "DELETE FROM orders WHERE order_id = '1'")


def test_fetch_order_evidence(test_db_session):
    evidence = fetch_order_evidence(test_db_session, "ord_000001")
    assert evidence is not None
    assert evidence["order_id"] == "ord_000001"
    assert "items" in evidence
    assert "payments" in evidence
    assert "reviews" in evidence


def test_faiss_semantic_retrieval():
    assert vector_store.index.ntotal > 0
    results = fetch_semantic_evidence("entrega atrasada prazo", top_k=3)
    assert len(results) > 0
    assert "order_id" in results[0]
    assert "score" in results[0]


def test_fetch_seller_sla_report(test_db_session):
    report = fetch_seller_sla_report(test_db_session, "seller_0001")
    if report:
        assert "sla_score" in report
        assert "standing" in report

