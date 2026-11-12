"""
Performance Benchmark: Retrieval Latency under 800 ms p95 SLA for Non-Generation Operations.
Measures SQL query execution, relational joins, and FAISS vector similarity search.
"""

import sys
import os
import time
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal
from app.db.models import Order
from app.agent.tools import fetch_order_evidence, fetch_semantic_evidence
from app.config import settings


def run_benchmark(num_iterations: int = 150):
    db = SessionLocal()
    try:
        orders = db.query(Order.order_id).limit(100).all()
        if not orders:
            print("❌ Error: No orders in database. Run 'python scripts/seed_data.py' first.")
            return False

        order_ids = [o[0] for o in orders]
        latencies = []

        print(f"\n⚡ Running Non-Generation Retrieval Latency Benchmark ({num_iterations} iterations)...")
        print(f"Target SLA: Under {settings.TARGET_P95_LATENCY_MS} ms (p95)")

        for i in range(num_iterations):
            oid = order_ids[i % len(order_ids)]
            t0 = time.perf_counter()

            # 1. SQL multi-table relational join
            _ = fetch_order_evidence(db, oid)

            # 2. FAISS vector search
            _ = fetch_semantic_evidence(f"fulfillment problem delay order {oid}", top_k=3)

            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)

        arr = np.array(latencies)
        p50 = float(np.percentile(arr, 50))
        p90 = float(np.percentile(arr, 90))
        p95 = float(np.percentile(arr, 95))
        p99 = float(np.percentile(arr, 99))
        mean = float(np.mean(arr))

        print("\n" + "=" * 50)
        print("📊 LATENCY BENCHMARK RESULTS")
        print("=" * 50)
        print(f"Total Iterations:   {num_iterations}")
        print(f"Min Latency:        {np.min(arr):.2f} ms")
        print(f"Average Latency:    {mean:.2f} ms")
        print(f"Median (p50):       {p50:.2f} ms")
        print(f"p90 Latency:        {p90:.2f} ms")
        print(f"p95 Latency:        {p95:.2f} ms (Target: < {settings.TARGET_P95_LATENCY_MS} ms)")
        print(f"p99 Latency:        {p99:.2f} ms")
        print(f"Max Latency:        {np.max(arr):.2f} ms")
        print("=" * 50)

        if p95 < settings.TARGET_P95_LATENCY_MS:
            print(f"✅ PASS: p95 latency ({p95:.2f} ms) is well UNDER the {settings.TARGET_P95_LATENCY_MS} ms SLA threshold!\n")
            return True
        else:
            print(f"❌ FAIL: p95 latency ({p95:.2f} ms) exceeded {settings.TARGET_P95_LATENCY_MS} ms threshold.\n")
            return False

    finally:
        db.close()


if __name__ == "__main__":
    run_benchmark()

