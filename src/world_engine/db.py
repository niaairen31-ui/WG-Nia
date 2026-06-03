"""Database engine and session management.

The engine URL comes from the ``WORLD_ENGINE_DATABASE_URL`` environment
variable and defaults to a local SQLite file. Switching to PostgreSQL/Supabase
later means changing only that variable — no application code changes.
"""

from __future__ import annotations

import os

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

# Optional: load a local .env file if python-dotenv is installed.
try:  # pragma: no cover - convenience only
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


# Default to a single local SQLite file at the project root.
DEFAULT_DATABASE_URL = "sqlite:///world_engine.db"
DATABASE_URL = os.getenv("WORLD_ENGINE_DATABASE_URL", DEFAULT_DATABASE_URL)

# SQLite needs check_same_thread disabled for use across threads (e.g. FastAPI).
_connect_args = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(DATABASE_URL, echo=False, connect_args=_connect_args)


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """Enforce foreign keys on SQLite (off by default)."""
    # Only applies to SQLite connections; harmless to guard by driver name.
    if engine.dialect.name == "sqlite":
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_db_and_tables() -> None:
    """Create every registered table (and its indexes) if not present."""
    # Importing the models module registers all tables on SQLModel.metadata.
    from world_engine import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session():
    """Yield a database session (FastAPI dependency-friendly)."""
    with Session(engine) as session:
        yield session
