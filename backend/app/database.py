"""
Database engine, session management, and pgvector extension initialization.
Uses SQLAlchemy 2.0 + pgvector in production (Neon PostgreSQL) and supports
SQLite fallback for zero-dependency local testing.
"""
import logging
from typing import Generator

from app.config import settings

logger = logging.getLogger(__name__)

try:
    from sqlalchemy import (
        Boolean,
        Column,
        DateTime,
        Float,
        ForeignKey,
        Index,
        Integer,
        JSON,
        String,
        Text,
        create_engine,
        func,
        text,
    )
    from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

    SQLALCHEMY_NATIVE = True
except ImportError:
    from app.utils.orm_fallback import (  # type: ignore[assignment]
        Boolean,
        Column,
        DateTime,
        Float,
        ForeignKey,
        Index,
        Integer,
        JSON,
        Session,
        String,
        Text,
        create_engine,
        declarative_base,
        func,
        relationship,
        sessionmaker,
        text,
    )

    SQLALCHEMY_NATIVE = False

try:
    from pgvector.sqlalchemy import Vector

    PGVECTOR_AVAILABLE = True
except ImportError:
    from app.utils.orm_fallback import Vector  # type: ignore[assignment]

    PGVECTOR_AVAILABLE = False

is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine_kwargs = {}
if is_sqlite and SQLALCHEMY_NATIVE:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
elif not is_sqlite and SQLALCHEMY_NATIVE:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_Vector_type(dim: int = 768):
    """Return pgvector Vector(dim) on PostgreSQL or JSON/Vector on SQLite."""
    if not is_sqlite and PGVECTOR_AVAILABLE:
        return Vector(dim)
    if SQLALCHEMY_NATIVE:
        return JSON
    return Vector(dim)


def init_db() -> None:
    """Initialize pgvector extension (on PostgreSQL) and create database tables."""
    import app.models  # noqa: F401 - ensure all models are registered on Base.metadata

    if not is_sqlite:
        try:
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
                logger.info("Verified pgvector extension on PostgreSQL.")
        except Exception as exc:
            logger.warning("Could not enable pgvector extension automatically: %s", exc)

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = [
    "Base",
    "Boolean",
    "Column",
    "DateTime",
    "Float",
    "ForeignKey",
    "Index",
    "Integer",
    "JSON",
    "PGVECTOR_AVAILABLE",
    "SQLALCHEMY_NATIVE",
    "Session",
    "SessionLocal",
    "String",
    "Text",
    "Vector",
    "engine",
    "func",
    "get_Vector_type",
    "get_db",
    "init_db",
    "is_sqlite",
    "relationship",
    "text",
]
