from app.agent.graph import create_agent_graph
from app.agent.state import AgentState


def test_agent_graph_delayed_order_workflow(test_db_session):
    graph = create_agent_graph(test_db_session)

    state: AgentState = {
        "trace_id": "test_trace_delayed",
        "order_id": "ord_000001",
        "query": "Investigate delivery delay and transit carrier status for ord_000001",
        "audit_trail": [],
    }

    final_state = graph.invoke(state)

    assert final_state.get("task_completed") is True
    assert final_state.get("intent") == "DELAYED_ORDER_INVESTIGATION"
    assert "diagnosis" in final_state
    assert "proposed_action" in final_state
    assert final_state.get("evidence_accuracy_score", 0) >= 80.0
    assert len(final_state.get("audit_trail", [])) >= 4


def test_agent_graph_payment_dispute_workflow(test_db_session):
    graph = create_agent_graph(test_db_session)

    state: AgentState = {
        "trace_id": "test_trace_payment",
        "order_id": "ord_000003",
        "query": "Customer reported billing discrepancy and payment mismatch for ord_000003",
        "audit_trail": [],
    }

    final_state = graph.invoke(state)

    assert final_state.get("task_completed") is True
    assert final_state.get("intent") == "PAYMENT_DISPUTE"
    assert "proposed_action" in final_state

