"""Database engine and session management.

``WORLD_ENGINE_ENV`` (``prod`` or ``test``) is the primary, fail-closed
resolver for the engine URL: ``prod`` resolves to the local prod SQLite
file, ``test`` to a separate local SQLite file under a ``test/`` directory.
``WORLD_ENGINE_DATABASE_URL``, when set to a non-empty value, is an explicit
override that takes precedence over ``WORLD_ENGINE_ENV`` and satisfies the
fail-closed check on its own. There is no implicit default: if neither
variable resolves, importing this module raises ``RuntimeError``. Switching
to PostgreSQL/Supabase means setting ``WORLD_ENGINE_DATABASE_URL`` — no
application code changes.

On SQLite, DDL participates in the surrounding transaction: a CREATE TABLE
emitted before a failed commit is rolled back with the rest. Transactional
DDL is a structural guarantee of this engine, not a per-site precaution.

Concurrency posture (TICKET-0072): the carrier runs in WAL. Readers never
block writers there, which is what makes the nested-session persist pattern
in the Play stream legal -- a request session holding an open read
transaction for the life of an SSE response cannot stall a second session's
commit. WAL is a persistent property of the database file, re-asserted on
every connect and verified fail-closed; the busy timeout is declared here
rather than inherited from the driver default.
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


# Prod and test each carry their own carrier file, outside the git working
# tree, so a workspace-clean (e.g. ``git clean -fdx``) can never take either.
_PROD_DB_PATH = Path.home() / ".world_engine" / "world_engine.db"
_TEST_DB_PATH = Path.home() / ".world_engine" / "test" / "world_engine_test.db"


def _resolve_database_url() -> str:
    """Resolve the engine URL, fail-closed.

    Explicit ``WORLD_ENGINE_DATABASE_URL`` wins outright (override). Else
    ``WORLD_ENGINE_ENV`` must be exactly ``prod`` or ``test``. Any other
    state (both unset, or an unrecognized ``WORLD_ENGINE_ENV`` value) raises
    rather than silently defaulting to prod.
    """
    explicit_url = os.getenv("WORLD_ENGINE_DATABASE_URL")
    if explicit_url:
        return explicit_url

    env = os.getenv("WORLD_ENGINE_ENV")
    if env == "prod":
        return f"sqlite:///{_PROD_DB_PATH}"
    if env == "test":
        return f"sqlite:///{_TEST_DB_PATH}"

    raise RuntimeError(
        "WORLD_ENGINE_ENV must be 'prod' or 'test' (or set "
        "WORLD_ENGINE_DATABASE_URL explicitly). Refusing to start with no "
        "resolved database."
    )


DATABASE_URL = _resolve_database_url()

# SQLite needs check_same_thread disabled for use across threads (e.g. FastAPI).
_connect_args = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# Structural guarantee: the carrier directory exists before any connection.
_url = make_url(DATABASE_URL)
if _url.get_backend_name() == "sqlite" and _url.database and _url.database != ":memory:":
    Path(_url.database).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(DATABASE_URL, echo=False, connect_args=_connect_args)


# TICKET-0072 (BRIEF-0072-a). The concurrency posture, declared once here and
# read structurally by tooling/verify/checks/sqlite_concurrency.py.
#
# BRIEF-0044-f made every transaction explicit (isolation_level = None plus an
# explicit BEGIN) so DDL could not escape a rollback. Unintended consequence
# under the default rollback journal: a SELECT now holds a SHARED lock for the
# life of its transaction. A request-scoped session that outlives its handler
# -- which is exactly what a StreamingResponse does -- therefore holds that
# lock for the whole stream, and a second Session(engine) opened inside the
# stream can INSERT but cannot COMMIT: promotion to EXCLUSIVE waits on the
# reader, exhausts the busy timeout, and raises "database is locked". That is
# every Play turn.
#
# WAL removes the conflict at its root -- readers never block writers -- and
# leaves BRIEF-0044-f's transactional-DDL guarantee intact (re-proved by
# scripts/test_ddl_atomicity.py, unmodified). busy_timeout is declared here
# rather than inherited from pysqlite's 5.0s default, so the value is owned by
# this module instead of by the driver, and is readable by the check.
_SQLITE_JOURNAL_MODE = "WAL"
_SQLITE_BUSY_TIMEOUT_MS = 5000
# An in-memory database reports 'memory' and cannot be WAL. Nothing in the
# tree binds one today, but WORLD_ENGINE_DATABASE_URL can express one, so the
# accepted set is declared rather than assumed.
_SQLITE_JOURNAL_MODES_OK = ("wal", "memory")


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
        cursor.execute(f"PRAGMA busy_timeout={_SQLITE_BUSY_TIMEOUT_MS}")
        journal_mode = cursor.execute(
            f"PRAGMA journal_mode={_SQLITE_JOURNAL_MODE}"
        ).fetchone()[0]
        cursor.close()
        if str(journal_mode).lower() not in _SQLITE_JOURNAL_MODES_OK:
            raise RuntimeError(
                f"SQLite journal_mode is {journal_mode!r}, expected one of "
                f"{_SQLITE_JOURNAL_MODES_OK}. Under a rollback journal, a "
                "streaming request session's read lock blocks every nested "
                "write commit (TICKET-0072). Refusing the connection rather "
                "than serving a Play surface that cannot persist a turn."
            )


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
