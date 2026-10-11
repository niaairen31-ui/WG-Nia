"""Migration v2.22 — the state of the world (TICKET-0113, BRIEF-0113-A;
decisions WA3, WB2, WC1, WD1 and WH1 of the conditions series).

Creates the five attribute tables, each with its CHECKs and indexes,
exactly as `models/canon_attribute.py` declares them (`Table.create`, the
`migrate_v1_89_conversation_window_config.py` precedent):
`attribute_definition`, `attribute_definition_type`, `attribute_choice`,
`attribute_value`, `attribute_change`.

Purely additive, zero rows created: a world's attributes are defined by
the creator going forward; the states the canon already keeps
(`character.vital_status`, `entity.status`, `location.magic_status`) are
read in place as system attributes and never copied (G3 of the series).

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.21 (the migrations are sequential).

Idempotent: each table's existence is checked before creating it; all five
are created in one transaction.

Post-check, before `schema_meta` moves: the five tables exist and hold zero
rows. `schema_meta` then moves to v2.22 -- this migration's own version, not
the code's: v2.23 (BRIEF-0113-B) converts data this one does not, and the
boot guard must keep refusing until it has run.

Run from the project root:

    python scripts/migrate_v2_22_attributes.py
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
        "migrate_v2_22_attributes.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import inspect, text  # noqa: E402
from sqlmodel import Session  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402

_PREVIOUS_VERSION = "v2.21"
_THIS_VERSION = "v2.22"
# Parents first: each table's foreign keys name a table created before it.
_MODELS = (
    models.AttributeDefinition,
    models.AttributeDefinitionType,
    models.AttributeChoice,
    models.AttributeValue,
    models.AttributeChange,
)


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _refuse_if_behind() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.22 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _apply_ddl() -> list[str]:
    present = set(inspect(engine).get_table_names())
    missing = [m for m in _MODELS if m.__tablename__ not in present]
    if not missing:
        print("The five attribute tables already exist — nothing to do.")
        return []
    with engine.begin() as conn:
        for model in missing:
            model.__table__.create(conn)
    return [m.__tablename__ for m in missing]


def _post_checks() -> None:
    present = set(inspect(engine).get_table_names())
    with engine.connect() as conn:
        for model in _MODELS:
            name = model.__tablename__
            if name not in present:
                raise SystemExit(f"Migration v2.22 aborted, post-check failed: {name} is missing.")
            count = conn.execute(text(f"SELECT COUNT(*) FROM {name}")).scalar()
            if count != 0:
                raise SystemExit(
                    f"Migration v2.22 aborted, post-check failed: {name} holds {count} row(s), "
                    "expected 0 — this migration creates zero rows."
                )
    print("Post-check: the five attribute tables exist and hold 0 rows.")


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
    print("Migration v2.22 — the state of the world")
    _refuse_if_behind()
    applied = _apply_ddl()
    if applied:
        print("Applied: " + ", ".join(applied) + ".")
    else:
        print("Migration v2.22 already fully applied — zero writes.")
    _post_checks()
    _converge_schema_meta()
    print("\nMigration v2.22 applied.")


if __name__ == "__main__":
    main()
