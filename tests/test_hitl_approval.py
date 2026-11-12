from app.agent.guardrails import assess_action_risk
from app.db.models import ProcurementAction


def test_guardrails_risk_classification():
    # Low risk action
    low_action = {"action_type": "EXPEDITE_AND_ISSUE_CREDIT", "amount": 35.0}
    risk, req_app, reason = assess_action_risk(low_action)
    assert risk == "LOW"
    assert req_app is False

    # High risk action exceeding $100 threshold
    high_action = {"action_type": "REFUND_PAYMENT_DISCREPANCY", "amount": 145.50}
    risk, req_app, reason = assess_action_risk(high_action)
    assert risk == "HIGH"
    assert req_app is True

    # High risk action with supplier sanction
    sanction_action = {"action_type": "SUSPEND_SELLER", "amount": 0.0}
    risk, req_app, reason = assess_action_risk(sanction_action)
    assert risk == "HIGH"
    assert req_app is True


def test_hitl_approval_lifecycle(client, test_db_session):
    # 1. Create a pending action
    action = ProcurementAction(
        action_id="act_test_hitl_01",
        order_id="ord_000001",
        action_type="REFUND_CUSTOMER",
        amount=150.0,
        risk_level="HIGH",
        status="PENDING",
        reason="Exceeded delay SLA and customer cancellation requested.",
    )
    test_db_session.add(action)
    test_db_session.commit()

    # 2. Query pending approvals API
    res = client.get("/api/agent/pending-approvals")
    assert res.status_code == 200
    pending_list = res.json()
    action_ids = [a["action_id"] for a in pending_list]
    assert "act_test_hitl_01" in action_ids

    # 3. Approve action
    app_res = client.post(
        "/api/agent/approve/act_test_hitl_01",
        json={"decision": "APPROVED", "reviewed_by": "Test_Officer_Sarah", "notes": "Approved refund under policy 4B"},
    )
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "APPROVED"

    # 4. Verify no longer pending
    res_after = client.get("/api/agent/pending-approvals")
    action_ids_after = [a["action_id"] for a in res_after.json()]
    assert "act_test_hitl_01" not in action_ids_after

