def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["app"] == "ProcureFlow AI"


def test_list_orders_api(client):
    res = client.get("/api/orders?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 60
    assert len(data["orders"]) == 10


def test_get_order_detail_api(client):
    res = client.get("/api/orders/ord_000001")
    assert res.status_code == 200
    data = res.json()
    assert data["order_id"] == "ord_000001"
    assert "items" in data
    assert "payments" in data


def test_agent_investigate_api(client):
    payload = {
        "query": "Investigate logistics and delay for order ord_000001",
        "order_id": "ord_000001",
    }
    res = client.post("/api/agent/investigate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["order_id"] == "ord_000001"
    assert "intent" in data
    assert "diagnosis" in data
    assert "proposed_action" in data
    assert data["evidence_accuracy_score"] >= 80.0


def test_metrics_p95_benchmark_api(client):
    res = client.get("/api/metrics/p95-benchmark?samples=10")
    assert res.status_code == 200
    data = res.json()
    assert "p95_latency_ms" in data
    assert data["p95_latency_ms"] < 800.0  # SLA requirement


def test_metrics_summary_api(client):
    res = client.get("/api/metrics/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["total_orders"] >= 60
    assert "delayed_rate_percent" in data

