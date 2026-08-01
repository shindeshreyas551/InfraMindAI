"""
SQLAlchemy Database Engine, Session Factory & Dependency Injection
for InfraMind AI FastAPI Backend.

Design decisions:
- Uses SQLAlchemy 2.x with `create_engine` / `sessionmaker` API targeting PostgreSQL.
- `get_db()` is a FastAPI dependency that yields a session and always
  closes it — even on exception — preventing connection leaks.
- `Base` is imported by all ORM models so Alembic can auto-discover them.
- Connection pooling with `pool_pre_ping=True` prevents stale connections in cloud environments like Render & Neon.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.core.config import settings


# ── Engine creation (PostgreSQL) ─────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,   # Verify connections before use (avoids stale conn errors)
    pool_size=10,         # Maintain up to 10 persistent connections
    max_overflow=20,      # Allow up to 20 temporary connections beyond pool_size
    echo=False,           # Set to True for SQL query debugging
)



# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ── Declarative base ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """All ORM models inherit from this. Alembic uses it to detect tables."""
    pass


# ── FastAPI dependency ────────────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    Yields a database session for the duration of a single request.
    Always closes the session in the finally block.

    Usage:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Utility: create all tables (used on startup for SQLite / local dev) ───────
def create_all_tables() -> None:
    """Creates all SQLAlchemy-mapped tables in the database if they do not exist."""
    from app.models import user, device, metric, alert, ai_analysis  # noqa: F401 — registers models
    Base.metadata.create_all(bind=engine)
