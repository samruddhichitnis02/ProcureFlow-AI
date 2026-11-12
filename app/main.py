import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import engine, Base, SessionLocal
from app.db.models import Order
from app.rag.vector_store import vector_store
from app.api.routes_agent import router as agent_router
from app.api.routes_orders import router as orders_router
from app.api.routes_metrics import router as metrics_router
from app.api.routes_audit import router as audit_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup:
    1. Create database schema
    2. Check if data exists; if empty, seed initial high-fidelity Olist dataset
    3. Initialize/Load FAISS vector index
    """
    logger.info("Initializing ProcureFlow AI database and vector storage...")
    Base.metadata.create_all(bind=engine)

    # Check if database has orders; if not, seed automatically for zero-setup execution
    db = SessionLocal()
    try:
        order_count = db.query(Order).count()
        if order_count == 0:
            logger.info("No orders detected in database. Generating initial Olist seed dataset...")
            from app.pipeline.generator import OlistDataGenerator
            from app.pipeline.ingest import ingest_olist_dataset

            gen = OlistDataGenerator(seed=42)
            dataset = gen.generate_dataset(
                num_customers=300,
                num_sellers=50,
                num_products=150,
                num_orders=1000,
            )
            ingest_olist_dataset(db, dataset, trace_id="lifespan_init")
            logger.info("Database successfully seeded with 1,000 initial orders.")

        # Load or build FAISS vector index
        if not vector_store.load():
            logger.info("Building FAISS vector index from customer review records...")
            indexed_count = vector_store.build_from_db(db, max_records=2000)
            vector_store.save()
            logger.info("FAISS vector index built with %d documents.", indexed_count)
    finally:
        db.close()

    yield
    logger.info("ProcureFlow AI service shutdown.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Enterprise Procurement Automation platform powered by LangGraph, Claude, "
        "PostgreSQL/SQLite, and FAISS over the unified Olist dataset."
    ),
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(agent_router)
app.include_router(orders_router)
app.include_router(metrics_router)
app.include_router(audit_router)

# Mount Static Files & Frontend SPA
static_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/", include_in_schema=False)
def serve_dashboard():
    """Serves the interactive Agentforce Procurement Automation Dashboard."""
    return FileResponse(os.path.join(static_path, "index.html"))


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "llm_provider": settings.LLM_PROVIDER,
        "faiss_vectors": vector_store.index.ntotal,
    }
