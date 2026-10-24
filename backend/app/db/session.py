import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger(__name__)

# Centrally configured engine with connection pooling and pre-ping to detect stale connections
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session per request,
    guarantees transaction rollback on unhandled exceptions, and safely closes the session.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as exc:
        logger.error("Unhandled exception during request database session: %s. Rolling back.", exc)
        db.rollback()
        raise
    finally:
        db.close()
