"""Initialize the World Engine database.

Creates the SQLite database file with every table and index defined in
`world_engine.models`. Safe to run repeatedly — existing tables are left as-is.

Run from the project root:

    python scripts/init_db.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the `src` package importable without an editable install.
SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect  # noqa: E402
from sqlmodel import Session  # noqa: E402

from world_engine.db import DATABASE_URL, create_db_and_tables, engine  # noqa: E402
from world_engine.models import SchemaMeta  # noqa: E402
from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402


def _seed_schema_meta_if_absent() -> None:
    """Virgin-head path (BRIEF-0044-a): a brand-new DB boots past the
    fail-closed schema_meta guard without a separate migration run."""
    with Session(engine) as session:
        if session.get(SchemaMeta, 1) is None:
            session.add(SchemaMeta(id=1, static_version=EXPECTED_STATIC_SCHEMA_VERSION))
            session.commit()
            print(f"Seeded schema_meta.id=1 at {EXPECTED_STATIC_SCHEMA_VERSION!r}")


def main() -> None:
    create_db_and_tables()
    _seed_schema_meta_if_absent()

    inspector = inspect(engine)
    tables = sorted(inspector.get_table_names())

    print(f"Database ready at: {DATABASE_URL}")
    print(f"Created/verified {len(tables)} tables:")
    for name in tables:
        index_count = len(inspector.get_indexes(name))
        suffix = f" ({index_count} index{'es' if index_count != 1 else ''})" if index_count else ""
        print(f"  - {name}{suffix}")


if __name__ == "__main__":
    main()
