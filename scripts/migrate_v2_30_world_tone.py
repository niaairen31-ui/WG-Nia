"""Migration v2.30 — a world has a tone (TICKET-0124, BRIEF-0124-A; decision B2 of the world premise).

Schema, additive only; no data is written:

- adds `world.tone` (TEXT, nullable: the creator's « Ton et style », read
  by every generator through the world premise).

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.29. Idempotent: the column is checked before it is added. One raw
transaction (`foreign_keys` set before it).

Post-check, before `schema_meta` moves: `world` holds `tone`.
`schema_meta` then moves to v2.30.

Run from the project root:

    python scripts/migrate_v2_30_world_tone.py
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

_env = os.environ.get("WORLD_ENGINE_ENV")
if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
    print(
        "migrate_v2_30_world_tone.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import inspect, text  # noqa: E402
from sqlmodel import Session  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402

_PREVIOUS_VERSION = "v2.29"
_THIS_VERSION = "v2.30"


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _refuse() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.30 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _has_tone() -> bool:
    return "tone" in {c["name"] for c in inspect(engine).get_columns("world")}


def _apply() -> list[str]:
    """One raw transaction (`migrate_v1_95_parked_plans.py`'s docstring: the
    PRAGMAs must land before any transaction exists)."""
    if _has_tone():
        return []
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("BEGIN")
        cursor.execute("ALTER TABLE world ADD COLUMN tone TEXT")
        cursor.execute("COMMIT")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()
    return ["world.tone added"]


def _post_checks() -> None:
    if not _has_tone():
        raise SystemExit("Migration v2.30 aborted, post-check failed: world lacks tone.")
    print("Post-check: world.tone in place.")


def _converge_schema_meta() -> None:
    with Session(engine) as session:
        row = session.get(models.SchemaMeta, 1)
        if row is None:
            session.add(models.SchemaMeta(id=1, static_version=_THIS_VERSION))
            print(f"Row: seeded schema_meta.id=1 at {_THIS_VERSION!r}")
        elif _version_key(row.static_version) < _version_key(_THIS_VERSION):
            previous = row.static_version
            row.static_version = _THIS_VERSION
            row.updated_at = datetime.now(UTC)
            session.add(row)
            print(f"Row: updated schema_meta.id=1: {previous!r} -> {_THIS_VERSION!r}")
        else:
            print(f"Row: schema_meta.id=1 already at {row.static_version!r} — nothing to do")
        session.commit()


def main() -> None:
    print("Migration v2.30 — a world has a tone")
    _refuse()
    applied = _apply()
    print("Applied: " + ", ".join(applied) + "." if applied else "Migration v2.30 already fully applied.")
    _post_checks()
    _converge_schema_meta()
    print("\nMigration v2.30 applied.")


if __name__ == "__main__":
    main()
