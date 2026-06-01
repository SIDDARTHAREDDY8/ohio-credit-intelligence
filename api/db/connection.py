import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/ohio_credit",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def execute_query(query: str, params: dict | None = None) -> list[dict]:
    """Run a SELECT query and return rows as a list of dicts."""
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        return [dict(row._mapping) for row in result]


def execute_write(query: str, params: dict | None = None) -> dict | None:
    """Run an INSERT/UPDATE in a transaction; return the first row if any."""
    with engine.begin() as conn:
        result = conn.execute(text(query), params or {})
        if result.returns_rows:
            row = result.first()
            return dict(row._mapping) if row else None
        return None
