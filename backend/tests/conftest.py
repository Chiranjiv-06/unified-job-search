import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import app.models  # ensure all models are registered on Base.metadata
from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
from app.workers.celery_app import celery_app

# Enable Celery eager mode during testing to execute tasks in-memory without Redis
celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
    broker_connection_timeout=1.0,
)

# SQLite in-memory engine for fast, isolated tests
TEST_DATABASE_URL = "sqlite:///:memory:"

engine_test = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine_test,
    expire_on_commit=False,
)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)

@pytest.fixture
def db_session():
    """
    Yields a test database session rolled back per test for isolation.
    """
    connection = engine_test.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    """
    TestClient with get_db dependency overridden to the test session.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()
