"""Migration v1.84 — `location_type_catalog` (classified interior/exterior
type registry, TICKET-0039, BRIEF-0039-a).

First step of the spatial-creation + door-materialization workstream.
Adds a per-world classified type registry that no reader consumes yet —
a deliberate, ticket-scoped exception to "no structure without a reader":
the reader lands later in the SAME ticket (BRIEF-0039-c/d/e).

Two independent guards (table existence, index existence — v1.77 lesson,
v1.80/v1.81 guard shape): a partially applied prior run completes only the
missing part on re-run, never skips wholesale.

SEEDING, per world, idempotent (INSERT only where `(world_id, name)` is
absent, case-insensitive — via `writes.upsert_location_type`, the
sanctioned write path):
  a. The 7 known defaults, classified:
     exterior: city, district, natural
     interior: building, room, underground
     NULL:     other
  b. Every DISTINCT non-null `location.location_type` value currently in
     use for that world, NOT already covered by (a) — inserted with
     classification = NULL and printed, so the creator sees what still
     needs classifying.

Never downgrades a decided classification to NULL — `upsert_location_type`
itself only updates an existing row's classification when the incoming
value is non-NULL. Idempotent: re-running reports the same seed set with
every row already present, zero new inserts.

Run from the project root:
    python scripts/migrate_v1_84_location_type_catalog.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.writes import upsert_location_type  # noqa: E402

_DEFAULTS: list[tuple[str, "str | None"]] = [
    ("city", "exterior"),
    ("district", "exterior"),
    ("natural", "exterior"),
    ("building", "interior"),
    ("room", "interior"),
    ("underground", "interior"),
    ("other", None),
]
_DEFAULT_NAMES_CASEFOLD = {name.casefold() for name, _ in _DEFAULTS}


def _ensure_table_and_index() -> list[str]:
    applied: list[str] = []
    inspector = inspect(engine)
    has_table = models.LocationTypeCatalog.__tablename__ in inspector.get_table_names()

    if not has_table:
        models.LocationTypeCatalog.__table__.create(engine)
        applied.append(f"created table `{models.LocationTypeCatalog.__tablename__}`")

    inspector = inspect(engine)
    indexes = {
        ix["name"] for ix in inspector.get_indexes(models.LocationTypeCatalog.__tablename__)
    }
    if "idx_location_type_catalog_name" not in indexes:
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE UNIQUE INDEX idx_location_type_catalog_name "
                "ON location_type_catalog(world_id, name COLLATE NOCASE)"
            ))
        applied.append("created index `idx_location_type_catalog_name`")

    return applied


def _existing_names_casefold(session: Session, world_id: str) -> set[str]:
    rows = session.exec(
        select(models.LocationTypeCatalog).where(
            models.LocationTypeCatalog.world_id == world_id
        )
    ).all()
    return {row.name.casefold() for row in rows}


def _distinct_location_types(session: Session, world_id: str) -> list[str]:
    result = session.execute(
        text(
            "SELECT DISTINCT location.location_type "
            "FROM location "
            "JOIN entity ON entity.id = location.id "
            "WHERE entity.world_id = :world_id AND location.location_type IS NOT NULL"
        ),
        {"world_id": world_id},
    )
    return [row[0] for row in result.all()]


def _seed_world(session: Session, world_id: str, world_name: str) -> None:
    print(f"\nWorld {world_name!r} ({world_id}):")

    existing = _existing_names_casefold(session, world_id)
    for name, classification in _DEFAULTS:
        was_present = name.casefold() in existing
        upsert_location_type(
            session, world_id=world_id, name=name, classification=classification,
            changed_by="migrate_v1_84",
        )
        status = "already present" if was_present else "inserted"
        print(f"    default  {name:<12} -> {classification!r:<10}  ({status})")

    discovered = _distinct_location_types(session, world_id)
    novel = [t for t in discovered if t.casefold() not in _DEFAULT_NAMES_CASEFOLD]
    if not novel:
        print("    no location.location_type values outside the 7 defaults")
        return

    existing = _existing_names_casefold(session, world_id)
    for name in novel:
        was_present = name.casefold() in existing
        upsert_location_type(
            session, world_id=world_id, name=name, classification=None,
            changed_by="migrate_v1_84",
        )
        status = "already present" if was_present else "inserted, classification NULL — needs classifying"
        print(f"    discovered  {name:<12} -> ({status})")


def main() -> None:
    print("Migration v1.84 — location_type_catalog")

    schema_actions = _ensure_table_and_index()
    if schema_actions:
        print("Schema: " + ", ".join(schema_actions))
    else:
        print("Schema: `location_type_catalog` table and index already present — nothing to do.")

    try:
        with Session(engine) as session:
            worlds = session.exec(select(models.World)).all()
            for world in worlds:
                _seed_world(session, world.id, world.name)
            session.commit()
    except Exception:
        print("\nERROR — transaction rolled back.", file=sys.stderr)
        raise

    print("\nMigration v1.84 applied.")


if __name__ == "__main__":
    main()
