import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.session import Base, get_db
from app.db.models import Order
from app.main import app
from app.pipeline.generator import OlistDataGenerator
from app.pipeline.ingest import ingest_olist_dataset
from app.rag.vector_store import vector_store

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="session", autouse=True)
def seed_test_database(test_engine):
    Session = sessionmaker(bind=test_engine)
    session = Session()
    gen = OlistDataGenerator(seed=123)
    dataset = gen.generate_dataset(num_customers=50, num_sellers=15, num_products=30, num_orders=60)
    ingest_olist_dataset(session, dataset, trace_id="test_setup")
    vector_store.build_from_db(session, max_records=60)
    session.close()


@pytest.fixture(scope="function")
def test_db_session(test_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="session")
def client(test_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
