"""
Evaluation Benchmark: LangGraph Agent Performance
Target Metrics:
- Task Completion Rate: >= 85%
- Evidence Accuracy: >= 90%
"""

import sys
import os
import uuid
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal
from app.db.models import Order
from app.agent.graph import create_agent_graph
from app.agent.state import AgentState


def evaluate_agent(num_cases: int = 20):
    db = SessionLocal()
    try:
        orders = db.query(Order).limit(num_cases).all()
        if not orders:
            print("❌ Error: No orders in database. Run 'python scripts/seed_data.py' first.")
            return False

        graph = create_agent_graph(db)

        tasks_completed = 0
        evidence_scores: List[float] = []

        print(f"\n🧠 Evaluating LangGraph AI Agent across {len(orders)} Procurement Scenarios...")

        for idx, order in enumerate(orders):
            trace_id = f"eval_{uuid.uuid4().hex[:8]}"

            # Generate realistic user prompt based on order properties
            if order.is_delayed:
                query = f"Investigate late delivery bottleneck and recommend compensation for order {order.order_id}"
            elif order.has_payment_issue:
                query = f"Audit payment discrepancy and billing records for order {order.order_id}"
            else:
                query = f"Check logistics status and seller compliance for order {order.order_id}"

            state: AgentState = {
                "trace_id": trace_id,
                "order_id": order.order_id,
                "query": query,
                "audit_trail": [],
            }

            final_state = graph.invoke(state)

            if final_state.get("task_completed"):
                tasks_completed += 1

            ev_score = final_state.get("evidence_accuracy_score", 0.0)
            evidence_scores.append(ev_score)

        completion_rate = (tasks_completed / len(orders)) * 100.0
        avg_evidence_acc = sum(evidence_scores) / len(evidence_scores)

        print("\n" + "=" * 55)
        print("🎯 AGENT ACCURACY & COMPLETION EVALUATION")
        print("=" * 55)
        print(f"Total Test Cases:          {len(orders)}")
        print(f"Tasks Completed:           {tasks_completed} / {len(orders)}")
        print(f"Task Completion Rate:      {completion_rate:.1f}% (Target: >= 85.0%)")
        print(f"Mean Evidence Accuracy:    {avg_evidence_acc:.1f}% (Target: >= 90.0%)")
        print("=" * 55)

        pass_completion = completion_rate >= 85.0
        pass_evidence = avg_evidence_acc >= 90.0

        if pass_completion and pass_evidence:
            print(f"✅ PASS: Both Task Completion ({completion_rate:.1f}%) and Evidence Accuracy ({avg_evidence_acc:.1f}%) meet enterprise targets!\n")
            return True
        else:
            print(f"❌ FAIL: Did not satisfy targets (Completion: {pass_completion}, Evidence: {pass_evidence})\n")
            return False

    finally:
        db.close()


if __name__ == "__main__":
    evaluate_agent()

