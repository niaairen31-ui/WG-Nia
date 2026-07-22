"""Migration v1.85 — `location_type_catalog` size templates (TICKET-0040,
BRIEF-0040-a).

First step of the contextual room-batch generation chantier. Adds two
nullable REAL columns, `default_width` and `default_height`, the ONLY
source of a location's birth bounds: code reads these, a model never
produces a number (A1). Applied ONCE, at creation — never retroactive to
an existing location (F1).

Two independent guards (one per column — `ALTER TABLE ADD COLUMN` cannot be
re-run safely, `migrate_v1_80_obstacle_geometry` idiom): a partially
applied prior run completes only the missing column, never skips wholesale.

K2 SEED, inside this migration, for EVERY world: find the `room` row
case-insensitively (same fold as `upsert_location_type`); if it exists and
both columns are NULL, set them to the seed values below; if it does not
exist, create it via `upsert_location_type` with `classification="interior"`
(matching `migrate_v1_84`'s `_DEFAULTS`) and the same two values. Never
overwrites a non-NULL value, in either direction, for any reason. No other
type is seeded.

Idempotent: re-running reports "nothing to do" for the schema part and the
same already-set template for `room` in every world, zero new writes.

Run from the project root:
    python scripts/migrate_v1_85_location_type_templates.py
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

# K2, TICKET-0040: the one seeded template, in world-meters. Creator-editable
# from the type picker; the migration never revisits it.
_ROOM_DEFAULT_WIDTH = 6.0
_ROOM_DEFAULT_HEIGHT = 5.0


def _ensure_columns() -> list[str]:
    applied: list[str] = []
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns(models.LocationTypeCatalog.__tablename__)}

    with engine.begin() as conn:
        if "default_width" not in columns:
            conn.execute(text(
                "ALTER TABLE location_type_catalog ADD COLUMN default_width REAL"
            ))
            applied.append("location_type_catalog.default_width column")
        if "default_height" not in columns:
            conn.execute(text(
                "ALTER TABLE location_type_catalog ADD COLUMN default_height REAL"
            ))
            applied.append("location_type_catalog.default_height column")

    return applied


def _seed_room(session: Session, world_id: str, world_name: str) -> None:
    existing = None
    for row in session.exec(
        select(models.LocationTypeCatalog).where(
            models.LocationTypeCatalog.world_id == world_id
        )
    ).all():
        if row.name.casefold() == "room":
            existing = row
            break

    if existing is not None and existing.default_width is not None and existing.default_height is not None:
        print(
            f"World {world_name!r}: `room` template already set "
            f"({existing.default_width} x {existing.default_height}) — nothing to do."
        )
        return

    upsert_location_type(
        session, world_id=world_id, name="room",
        classification="interior" if existing is None else None,
        changed_by="migrate_v1_85",
        default_width=_ROOM_DEFAULT_WIDTH, default_height=_ROOM_DEFAULT_HEIGHT,
    )
    status = "created" if existing is None else "template set"
    print(
        f"World {world_name!r}: `room` {status} -> "
        f"{_ROOM_DEFAULT_WIDTH} x {_ROOM_DEFAULT_HEIGHT}"
    )


def main() -> None:
    print("Migration v1.85 — location_type_catalog size templates")

    schema_actions = _ensure_columns()
    if schema_actions:
        print("Schema: " + ", ".join(schema_actions))
    else:
        print("Schema: `default_width`/`default_height` columns already present — nothing to do.")

    try:
        with Session(engine) as session:
            worlds = session.exec(select(models.World)).all()
            for world in worlds:
                _seed_room(session, world.id, world.name)
            session.commit()
    except Exception:
        print("\nERROR — transaction rolled back.", file=sys.stderr)
        raise

    print("\nMigration v1.85 applied.")


if __name__ == "__main__":
    main()
