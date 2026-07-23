"""Database engine and session management.

The engine URL comes from the ``WORLD_ENGINE_DATABASE_URL`` environment
variable and defaults to a local SQLite file. Switching to PostgreSQL/Supabase
later means changing only that variable — no application code changes.

On SQLite, DDL participates in the surrounding transaction: a CREATE TABLE
emitted before a failed commit is rolled back with the rest. Transactional
DDL is a structural guarantee of this engine, not a per-site precaution.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine, make_url
from sqlmodel import Session, SQLModel, create_engine

# Optional: load a local .env file if python-dotenv is installed.
try:  # pragma: no cover - convenience only
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


# Default to a single local SQLite file outside the git working tree, so a
# workspace-clean (e.g. ``git clean -fdx``) can never take the carrier file.
DEFAULT_DB_PATH = Path.home() / ".world_engine" / "world_engine.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DB_PATH}"
DATABASE_URL = os.getenv("WORLD_ENGINE_DATABASE_URL", DEFAULT_DATABASE_URL)

# SQLite needs check_same_thread disabled for use across threads (e.g. FastAPI).
_connect_args = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# Structural guarantee: the carrier directory exists before any connection.
_url = make_url(DATABASE_URL)
if _url.get_backend_name() == "sqlite" and _url.database and _url.database != ":memory:":
    Path(_url.database).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(DATABASE_URL, echo=False, connect_args=_connect_args)


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """Enforce foreign keys on SQLite (off by default)."""
    # Only applies to SQLite connections; harmless to guard by driver name.
    if engine.dialect.name == "sqlite":
        # Disable pysqlite's own BEGIN/COMMIT management: it auto-commits
        # before DDL, which would silently defeat the "begin" listener below
        # and break atomicity between a CREATE TABLE and the writes around it.
        dbapi_connection.isolation_level = None
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@event.listens_for(engine, "begin")
def _begin_sqlite_transaction(conn):
    """Emit an explicit BEGIN so DDL joins the surrounding transaction."""
    if engine.dialect.name == "sqlite":
        conn.exec_driver_sql("BEGIN")


def create_db_and_tables() -> None:
    """Create every registered table (and its indexes) if not present."""
    # Importing the models module registers all tables on SQLModel.metadata.
    from world_engine import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session():
    """Yield a database session (FastAPI dependency-friendly)."""
    with Session(engine) as session:
        yield session
