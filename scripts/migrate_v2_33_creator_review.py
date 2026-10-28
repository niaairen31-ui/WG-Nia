"""Migration v2.33 — the creator's review of a submitted character: the review columns, the approved character, the review batches (TICKET-0129, BRIEF-0129-B).

Schema only; no data is written beyond the defaults of the new columns:

- rebuilds `pc_draft_sketch` so it holds `review_action`, `review_entity_id`,
  `review_relation_type` ('ally'), `review_intensity` (60) and the CHECKs
  `ck_pc_draft_sketch_review_action`, `ck_pc_draft_sketch_review_entity`,
  `ck_pc_draft_sketch_review_intensity`. Every row is copied unchanged;
  the new columns take their defaults;
- adds `pc_draft.review_location_id`, `pc_draft.character_id`,
  `pc_draft_membership.review_dropped` (0), `npc_batch.pc_draft_id`,
  `npc_batch.pc_group_label` and `npc_batch_row.pc_draft_sketch_id` (no FK);
- creates the partial unique index `idx_npc_batch_review_open` (one open
  review batch per draft and group).

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.32. Idempotent: each step runs only while still needed (the stored
`pc_draft_sketch` SQL lacks `ck_pc_draft_sketch_review_action`; the column
or the index is absent). One raw transaction (`foreign_keys` and
`legacy_alter_table` set before it).

Post-checks, before `schema_meta` moves: every new column and the index
exist; the stored `pc_draft_sketch` SQL holds the three CHECK names; the
sketch row count is unchanged. `schema_meta` then moves to v2.33.

Run from the project root:

    python scripts/migrate_v2_33_creator_review.py
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
        "migrate_v2_33_creator_review.py refuses to run without WORLD_ENGINE_ENV "
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

_PREVIOUS_VERSION = "v2.32"
_THIS_VERSION = "v2.33"
_SKETCH_COLUMNS = (
    "id, draft_id, world_id, position, name, role, sentence, group_label, "
    "kind, skill_key, existing_entity_id, origin"
)
_SKETCH_CHECKS = (
    "ck_pc_draft_sketch_review_action",
    "ck_pc_draft_sketch_review_entity",
    "ck_pc_draft_sketch_review_intensity",
)
_NEW_COLUMNS = (
    ("pc_draft", "review_location_id", "VARCHAR REFERENCES entity (id)"),
    ("pc_draft", "character_id", "VARCHAR REFERENCES entity (id)"),
    ("pc_draft_membership", "review_dropped", "BOOLEAN NOT NULL DEFAULT 0"),
    ("npc_batch", "pc_draft_id", "VARCHAR REFERENCES pc_draft (id)"),
    ("npc_batch", "pc_group_label", "VARCHAR"),
    ("npc_batch_row", "pc_draft_sketch_id", "VARCHAR"),
)
_REVIEW_INDEX = "idx_npc_batch_review_open"
_SKETCH_REVIEW_COLUMNS = ("review_action", "review_entity_id", "review_relation_type", "review_intensity")


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _refuse() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.33 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _tables() -> set[str]:
    return set(inspect(engine).get_table_names())


def _columns(table: str) -> set[str]:
    return {c["name"] for c in inspect(engine).get_columns(table)}


def _indexes() -> set[str]:
    with engine.connect() as conn:
        return {name for (name,) in conn.execute(text("SELECT name FROM sqlite_master WHERE type='index'"))}


def _sketch_sql() -> str:
    with engine.connect() as conn:
        return conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:n"),
                            {"n": "pc_draft_sketch"}).scalar_one()


def _sketch_count() -> int:
    with engine.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM pc_draft_sketch")).scalar_one()


def _create_from_model(cursor, model) -> None:
    cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
    for index in model.__table__.indexes:
        cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))


def _rebuild(cursor, model, columns: str) -> None:
    table = model.__tablename__
    for (index_name,) in cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL",
        (table,),
    ).fetchall():
        cursor.execute(f"DROP INDEX {index_name}")
    cursor.execute(f"ALTER TABLE {table} RENAME TO {table}_old")
    _create_from_model(cursor, model)
    cursor.execute(f"INSERT INTO {table} ({columns}) SELECT {columns} FROM {table}_old")
    cursor.execute(f"DROP TABLE {table}_old")


def _review_index_sql() -> str:
    index = next(i for i in models.NpcBatch.__table__.indexes if i.name == _REVIEW_INDEX)
    return str(CreateIndex(index).compile(dialect=engine.dialect))


def _plan() -> tuple[list[tuple], list[str], list[str]]:
    """((model, copied columns) rebuilds, ALTER statements, index statements) still to apply."""
    rebuilds: list[tuple] = []
    if _SKETCH_CHECKS[0] not in _sketch_sql():
        rebuilds.append((models.PcDraftSketch, _SKETCH_COLUMNS))
    adds = [
        f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"
        for table, column, sql_type in _NEW_COLUMNS
        if column not in _columns(table)
    ]
    indexes = [] if _REVIEW_INDEX in _indexes() else [_review_index_sql()]
    return rebuilds, adds, indexes


def _apply() -> list[str]:
    """One raw transaction (`migrate_v1_95_parked_plans.py`'s docstring: the
    PRAGMAs must land before any transaction exists)."""
    rebuilds, adds, indexes = _plan()
    if not rebuilds and not adds and not indexes:
        return []
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("PRAGMA legacy_alter_table=ON")
        cursor.execute("BEGIN")
        for model, columns in rebuilds:
            _rebuild(cursor, model, columns)
        for statement in adds:
            cursor.execute(statement)
        for statement in indexes:
            cursor.execute(statement)
        cursor.execute("COMMIT")
        cursor.execute("PRAGMA legacy_alter_table=OFF")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()
    rebuilt = [f"{model.__tablename__} rebuilt" for model, _ in rebuilds]
    added = [f"{statement.split()[2]}.{statement.split()[5]} added" for statement in adds]
    created = [f"{_REVIEW_INDEX} created" for _ in indexes]
    return rebuilt + added + created


def _post_checks(sketches_before: int) -> None:
    problems: list[str] = []
    for table, column, _ in _NEW_COLUMNS:
        if column not in _columns(table):
            problems.append(f"{table} lacks {column}")
    for column in _SKETCH_REVIEW_COLUMNS:
        if column not in _columns("pc_draft_sketch"):
            problems.append(f"pc_draft_sketch lacks {column}")
    if _REVIEW_INDEX not in _indexes():
        problems.append(f"{_REVIEW_INDEX} is missing")
    sketch_sql = _sketch_sql()
    for name in _SKETCH_CHECKS:
        if name not in sketch_sql:
            problems.append(f"pc_draft_sketch lacks the CHECK {name}")
    sketches_after = _sketch_count()
    if sketches_after != sketches_before:
        problems.append(f"pc_draft_sketch row count {sketches_before} -> {sketches_after}")
    if problems:
        raise SystemExit("Migration v2.33 aborted, post-check failed: " + "; ".join(problems) + ".")
    print(f"Post-check: {len(_NEW_COLUMNS) + len(_SKETCH_REVIEW_COLUMNS)} columns, "
          f"{len(_SKETCH_CHECKS)} CHECKs and {_REVIEW_INDEX} in place; "
          f"{sketches_after} sketch row(s) kept.")


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
    print("Migration v2.33 — the creator's review columns, the approved character, the review batches")
    _refuse()
    sketches_before = _sketch_count()
    applied = _apply()
    print("Applied: " + ", ".join(applied) + "." if applied else "Nothing to do.")
    _post_checks(sketches_before)
    _converge_schema_meta()
    print("\nMigration v2.33 applied.")


if __name__ == "__main__":
    main()
