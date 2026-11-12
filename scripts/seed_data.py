"""
CLI Script to Seed Olist Dataset into PostgreSQL / SQLite and build the FAISS Index.
Usage:
    python scripts/seed_data.py --orders 1500 --batch-size 500
    python scripts/seed_data.py --orders 100000 --batch-size 2000
"""

import argparse
import sys
import os
import time

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import engine, Base, SessionLocal
from app.pipeline.generator import OlistDataGenerator
from app.pipeline.ingest import ingest_olist_dataset
from app.rag.vector_store import vector_store


def main():
    parser = argparse.ArgumentParser(description="Seed Olist Brazilian E-Commerce dataset into ProcureFlow AI.")
    parser.add_argument("--orders", type=int, default=1500, help="Number of orders to generate & seed (default: 1500, supports 100k+)")
    parser.add_argument("--batch-size", type=int, default=500, help="Bulk insert batch size")
    parser.add_argument("--build-index", action="store_true", default=True, help="Build and persist FAISS vector index")
    parser.add_argument("--reset", action="store_true", default=False, help="Drop existing tables before seeding")
    args = parser.parse_args()

    if args.reset or not os.path.exists(engine.url.database or ""):
        print("🗑️ Resetting database schema...")
        Base.metadata.drop_all(bind=engine)

    print(f"🚀 Initializing database tables on {engine.url}...")
    Base.metadata.create_all(bind=engine)

    # Scale entity counts proportionally
    num_orders = args.orders
    num_customers = max(200, int(num_orders * 0.4))
    num_sellers = max(30, int(num_orders * 0.08))
    num_products = max(100, int(num_orders * 0.15))

    print(f"📦 Generating synthetic Olist dataset ({num_orders:,} orders, {num_customers:,} customers, {num_sellers:,} sellers)...")
    start_gen = time.perf_counter()
    gen = OlistDataGenerator(seed=42)
    dataset = gen.generate_dataset(
        num_customers=num_customers,
        num_sellers=num_sellers,
        num_products=num_products,
        num_orders=num_orders,
    )
    gen_time = round(time.perf_counter() - start_gen, 2)
    print(f"✓ Dataset generated in {gen_time}s.")

    print("💾 Ingesting records into database...")
    start_ingest = time.perf_counter()
    db = SessionLocal()
    try:
        stats = ingest_olist_dataset(db, dataset, batch_size=args.batch_size, trace_id="cli_seed")
        ingest_time = round(time.perf_counter() - start_ingest, 2)
        print(f"✓ Ingestion completed in {ingest_time}s: {stats}")

        if args.build_index:
            print("🔍 Building FAISS vector index from customer dispute and review text...")
            start_index = time.perf_counter()
            count = vector_store.build_from_db(db, max_records=min(num_orders, 5000))
            vector_store.save()
            index_time = round(time.perf_counter() - start_index, 2)
            print(f"✓ FAISS index indexed {count} documents in {index_time}s.")

    finally:
        db.close()

    print("🎉 ProcureFlow AI database initialization and seeding complete!")


if __name__ == "__main__":
    main()
