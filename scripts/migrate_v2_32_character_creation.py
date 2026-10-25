"""Migration v2.32 — a world's character creation rules, the creation overrides, a player's character draft, the creation journal kind (TICKET-0126, BRIEF-0126-B; decisions J1', L2, B1, U1).

Schema only; the one data write is the journal's copy:

- creates `creation_rules` (one row per world; a missing row is every
  default) and the five draft tables `pc_draft`, `pc_draft_skill`,
  `pc_draft_sketch`, `pc_draft_membership`, `pc_draft_knowledge` (non-canon,
  pending), parents before children, each with its indexes;
- adds `skill_system.visible_at_creation`, `max_rank_at_creation`,
  `cap_raised_at_creation`, `cap_held_at_creation` and
  `skill_definition.visible_at_creation`, `max_rank_at_creation` (nullable:
  NULL inherits);
- renames `pc_draft.backstory` to `story` on a database that ran this
  script before AMENDMENT-0126-01 (lore_as_facts R1 bans the name);
- rebuilds `lore_usage_event` so its step CHECK admits `kind = 'creation'`
  with steps `creation_subject` and `creation_design`. Every row is copied
  unchanged.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.31. Idempotent: each step runs only while still needed (the table
or the column is absent; `pc_draft` still holds `backstory`; the stored
table SQL lacks `'creation'`). One raw
transaction (`foreign_keys` and `legacy_alter_table` set before it).

Post-checks, before `schema_meta` moves: the six tables and the six columns
exist; `pc_draft` holds `story` and not `backstory`; the stored
`lore_usage_event` SQL holds `'creation_design'`; the journal's row count
is unchanged. `schema_meta` then moves to v2.32.

Run from the project root:

    python scripts/migrate_v2_32_character_creation.py
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
        "migrate_v2_32_character_creation.py refuses to run without WORLD_ENGINE_ENV "
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

_PREVIOUS_VERSION = "v2.31"
_THIS_VERSION = "v2.32"
_JOURNAL_COLUMNS = (
    "id, attempt_id, world_ref, world_name, kind, step, outcome, payload, "
    "model_calls, lore_entry_ref, created_at"
)
# Parents before children.
_NEW_TABLES = (
    models.CreationRules,
    models.PcDraft,
    models.PcDraftSkill,
    models.PcDraftSketch,
    models.PcDraftMembership,
    models.PcDraftKnowledge,
)
_NEW_COLUMNS = (
    ("skill_system", "visible_at_creation", "BOOLEAN"),
    ("skill_system", "max_rank_at_creation", "INTEGER"),
    ("skill_system", "cap_raised_at_creation", "INTEGER"),
    ("skill_system", "cap_held_at_creation", "INTEGER"),
    ("skill_definition", "visible_at_creation", "BOOLEAN"),
    ("skill_definition", "max_rank_at_creation", "INTEGER"),
)


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _refuse() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.32 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _tables() -> set[str]:
    return set(inspect(engine).get_table_names())


def _columns(table: str) -> set[str]:
    return {c["name"] for c in inspect(engine).get_columns(table)}


def _journal_sql() -> str:
    with engine.connect() as conn:
        return conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:n"),
                            {"n": "lore_usage_event"}).scalar_one()


def _journal_count() -> int:
    with engine.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM lore_usage_event")).scalar_one()


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


def _plan() -> tuple[list, list[str], list[tuple]]:
    """(models to create, ALTER statements, (model, copied columns) rebuilds) still to apply."""
    present = _tables()
    creates = [model for model in _NEW_TABLES if model.__tablename__ not in present]
    renames = []
    if "pc_draft" in present and "backstory" in _columns("pc_draft") and "story" not in _columns("pc_draft"):
        renames.append("ALTER TABLE pc_draft RENAME COLUMN backstory TO story")
    adds = [
        f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"
        for table, column, sql_type in _NEW_COLUMNS
        if column not in _columns(table)
    ]
    rebuilds: list[tuple] = []
    if "'creation'" not in _journal_sql():
        rebuilds.append((models.LoreUsageEvent, _JOURNAL_COLUMNS))
    return creates, renames + adds, rebuilds


def _apply() -> list[str]:
    """One raw transaction (`migrate_v1_95_parked_plans.py`'s docstring: the
    PRAGMAs must land before any transaction exists)."""
    creates, adds, rebuilds = _plan()
    if not creates and not adds and not rebuilds:
        return []
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("PRAGMA legacy_alter_table=ON")
        cursor.execute("BEGIN")
        for model in creates:
            _create_from_model(cursor, model)
        for statement in adds:
            cursor.execute(statement)
        for model, columns in rebuilds:
            _rebuild(cursor, model, columns)
        cursor.execute("COMMIT")
        cursor.execute("PRAGMA legacy_alter_table=OFF")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()
    created = [f"{model.__tablename__} created" for model in creates]
    added = [
        f"{statement.split()[2]}.{statement.split()[5]} renamed to {statement.split()[7]}"
        if " RENAME COLUMN " in statement else f"{statement.split()[2]}.{statement.split()[5]} added"
        for statement in adds
    ]
    return created + added + [f"{model.__tablename__} rebuilt" for model, _ in rebuilds]


def _post_checks(journal_before: int) -> None:
    problems: list[str] = []
    present = _tables()
    for model in _NEW_TABLES:
        if model.__tablename__ not in present:
            problems.append(f"{model.__tablename__} is missing")
    for table, column, _ in _NEW_COLUMNS:
        if column not in _columns(table):
            problems.append(f"{table} lacks {column}")
    if "pc_draft" in present and ("story" not in _columns("pc_draft") or "backstory" in _columns("pc_draft")):
        problems.append("pc_draft does not hold story in place of backstory")
    if "'creation_design'" not in _journal_sql():
        problems.append("lore_usage_event's step CHECK lacks 'creation_design'")
    journal_after = _journal_count()
    if journal_after != journal_before:
        problems.append(f"lore_usage_event row count {journal_before} -> {journal_after}")
    if problems:
        raise SystemExit("Migration v2.32 aborted, post-check failed: " + "; ".join(problems) + ".")
    print(f"Post-check: {len(_NEW_TABLES)} tables and {len(_NEW_COLUMNS)} columns in place; "
          f"lore_usage_event admits the creation kind; {journal_after} journal row(s) kept.")


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
    print("Migration v2.32 — character creation rules, overrides, drafts, the creation journal kind")
    _refuse()
    journal_before = _journal_count()
    applied = _apply()
    print("Applied: " + ", ".join(applied) + "." if applied else "Migration v2.32 already fully applied.")
    _post_checks(journal_before)
    _converge_schema_meta()
    print("\nMigration v2.32 applied.")


if __name__ == "__main__":
    main()
