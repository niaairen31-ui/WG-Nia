"""Migration v2.17 — quest offers and the widened requirement vocabulary
(TICKET-0108, BRIEF-0108-A, decisions A1, B, B-dir, H1, L1, M1).

1. Rebuild. `agenda_step_requirement` is rebuilt from the model so its two
   CHECKs carry the four new forms (`has_met`, `faction_member`,
   `skill_rank_gte`, `quest_completed`). SQLite cannot alter a CHECK: the
   table is renamed, recreated from `models.AgendaStepRequirement`, its rows
   copied column for column, the old table dropped -- the
   `migrate_v2_15_skill_ranks.py` raw-connection rebuild, verbatim in shape.
   The new CHECKs accept every row the old ones accepted.
2. Create. `quest_offer`, `quest_offer_step`, `quest_offer_requirement` and
   `quest`, from their models, when missing.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.16 (the migrations are sequential), before any change.

Idempotent: the rebuild runs only while the stored CHECK lacks
`'quest_completed'`; each table is created only when missing.

Post-checks, before `schema_meta` converges: the stored CHECK names the four
new forms; the `agenda_step_requirement` row count is unchanged; the four
new tables exist; `PRAGMA foreign_key_check` is empty on the five tables
this migration writes. A dangling reference elsewhere in the database
predates it: it is listed, never a reason to stop (AMENDMENT-0107-01).

Run from the project root:

    python scripts/migrate_v2_17_quests.py
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
        "migrate_v2_17_quests.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import inspect, text  # noqa: E402
from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402
from sqlmodel import Session  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402

_PREVIOUS_VERSION = "v2.16"
_REQUIREMENT_COLUMNS = "id, world_id, step_id, type, target_entity_id, target_key, threshold"
_NEW_FORMS = ("has_met", "faction_member", "skill_rank_gte", "quest_completed")
# Parents first: an offer before its steps, its steps before its requirements.
_NEW_MODELS = (models.QuestOffer, models.QuestOfferStep, models.QuestOfferRequirement, models.Quest)
# The tables this migration writes: the only ones its foreign-key post-check judges.
_TOUCHED_TABLES = ("agenda_step_requirement",) + tuple(m.__tablename__ for m in _NEW_MODELS)


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _refuse() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.17 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _requirement_table_sql() -> str:
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='agenda_step_requirement'"
        )).first()
    return row[0] if row is not None else ""


def _row_count(table: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()


def _create_from_model(cursor, model) -> None:
    cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
    for index in model.__table__.indexes:
        cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))


def _rebuild_requirements(cursor) -> None:
    for (index_name,) in cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='agenda_step_requirement' "
        "AND sql IS NOT NULL"
    ).fetchall():
        cursor.execute(f"DROP INDEX {index_name}")
    cursor.execute("ALTER TABLE agenda_step_requirement RENAME TO agenda_step_requirement_old")
    _create_from_model(cursor, models.AgendaStepRequirement)
    cursor.execute(
        f"INSERT INTO agenda_step_requirement ({_REQUIREMENT_COLUMNS}) "
        f"SELECT {_REQUIREMENT_COLUMNS} FROM agenda_step_requirement_old"
    )
    cursor.execute("DROP TABLE agenda_step_requirement_old")


def _apply_ddl() -> list[str]:
    """One raw transaction (see `migrate_v1_95_parked_plans.py`'s docstring:
    the PRAGMAs must land before any transaction exists): the rebuild when
    the CHECK lacks the new forms, then each missing quest table."""
    rebuild = "'quest_completed'" not in _requirement_table_sql()
    existing = set(inspect(engine).get_table_names())
    missing = [model for model in _NEW_MODELS if model.__tablename__ not in existing]
    if not rebuild and not missing:
        return []
    applied: list[str] = []
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("PRAGMA legacy_alter_table=ON")
        cursor.execute("BEGIN")
        if rebuild:
            _rebuild_requirements(cursor)
            applied.append("agenda_step_requirement rebuilt")
        for model in missing:
            _create_from_model(cursor, model)
            applied.append(f"{model.__tablename__} created")
        cursor.execute("COMMIT")
        cursor.execute("PRAGMA legacy_alter_table=OFF")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()
    return applied


def _post_checks(requirements_before: int) -> None:
    stored = _requirement_table_sql()
    absent = [form for form in _NEW_FORMS if f"'{form}'" not in stored]
    if absent:
        raise SystemExit(f"Migration v2.17 aborted, post-check failed: the CHECK lacks {absent}.")
    after = _row_count("agenda_step_requirement")
    if after != requirements_before:
        raise SystemExit(
            "Migration v2.17 aborted, post-check failed: agenda_step_requirement row count "
            f"changed ({requirements_before} -> {after})."
        )
    tables = set(inspect(engine).get_table_names())
    missing = [m.__tablename__ for m in _NEW_MODELS if m.__tablename__ not in tables]
    if missing:
        raise SystemExit(f"Migration v2.17 aborted, post-check failed: tables missing {missing}.")
    with engine.connect() as conn:
        dangling = [row for table in _TOUCHED_TABLES
                    for row in conn.execute(text(f"PRAGMA foreign_key_check({table})")).fetchall()]
        elsewhere = [row for row in conn.execute(text("PRAGMA foreign_key_check")).fetchall()
                     if row[0] not in _TOUCHED_TABLES]
    if dangling:
        raise SystemExit(f"Migration v2.17 aborted, post-check failed: foreign_key_check {dangling}.")
    for table, rowid, parent, _fk in elsewhere:
        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
    print(f"Post-check: CHECK widened; {after} requirement row(s) preserved; four quest tables in place.")


def _converge_schema_meta() -> None:
    with Session(engine) as session:
        row = session.get(models.SchemaMeta, 1)
        if row is None:
            session.add(models.SchemaMeta(id=1, static_version=EXPECTED_STATIC_SCHEMA_VERSION))
            print(f"Row: seeded schema_meta.id=1 at {EXPECTED_STATIC_SCHEMA_VERSION!r}")
        elif row.static_version != EXPECTED_STATIC_SCHEMA_VERSION:
            previous = row.static_version
            row.static_version = EXPECTED_STATIC_SCHEMA_VERSION
            row.updated_at = datetime.now(UTC)
            session.add(row)
            print(f"Row: updated schema_meta.id=1: {previous!r} -> {EXPECTED_STATIC_SCHEMA_VERSION!r}")
        else:
            print(f"Row: schema_meta.id=1 already at {EXPECTED_STATIC_SCHEMA_VERSION!r} — nothing to do")
        session.commit()


def main() -> None:
    print("Migration v2.17 — quest offers, quests, eight requirement forms")
    _refuse()
    before = _row_count("agenda_step_requirement")
    applied = _apply_ddl()
    print("Applied: " + ", ".join(applied) + "." if applied else "Schema already in place.")
    _post_checks(before)
    _converge_schema_meta()
    print("\nMigration v2.17 applied.")


if __name__ == "__main__":
    main()
