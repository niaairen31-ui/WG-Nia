"""Migration v2.29 — a rank may ask a trial, and a trial is a quest
(TICKET-0116, BRIEF-0116-A; decisions B1, D2, D2-d, F1-b).

Schema only; no data row is written:

- `skill_rank` gains `trial_to_next` (BOOLEAN NOT NULL DEFAULT 0: leaving
  this rank asks a trial), and `skill_system` and `skill_definition` gain
  `trial_to_rank_1` .. `trial_to_rank_5` (BOOLEAN, NULL inherits), each by
  `ADD COLUMN` (the v2.16 precedent: the columns land at the end of their
  tables);
- `quest_offer_term` then `quest_term` are rebuilt from their models, their
  CHECKs admitting a sixth currency, `rank` (a reward only, naming a skill
  and the rank it gives);
- `quest_request` is rebuilt from its model: its day and step become
  optional, `skill_key` and `target_rank` are added for the `trial`
  trigger, `ck_quest_request_origin` ties each trigger to its columns and
  `idx_quest_request_trial` indexes (world, skill, rank).

SQLite cannot add a table CHECK nor change a column's nullability in place,
so the three tables are rebuilt (`migrate_v2_15_skill_ranks.py` precedent:
raw DBAPI connection, `PRAGMA foreign_keys=OFF` and `legacy_alter_table=ON`
before `BEGIN`, drop the indexes, rename, create from the model, copy every
named column, drop the old table), all of it in ONE transaction. Every row
is kept, `change_history` included; no rank asks a trial afterwards.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.28, before any change. Idempotent: a column is added only while
missing, a term table is rebuilt only while its DDL lacks `'rank'`, and
`quest_request` only while it lacks `skill_key`; a second run prints
« DDL already applied. ».

Post-checks, before `schema_meta` moves: the row counts of the three rebuilt
tables unchanged; the eleven columns present; every `skill_rank.trial_to_next`
is 0; the rebuilt tables carry their models' CHECK names and indexes;
`PRAGMA foreign_key_check` of the six tables compared with the same check
taken before the DDL -- a row dangling after and not before fails, one
dangling before is printed as a note and does not stop the migration
(AMENDMENT-0107-01). `schema_meta` then moves to v2.29.

Run from the project root:

    python scripts/migrate_v2_29_rank_trials.py
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
        "migrate_v2_29_rank_trials.py refuses to run without WORLD_ENGINE_ENV "
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

_PREVIOUS_VERSION = "v2.28"
_THIS_VERSION = "v2.29"

# `skill_ranks` has no constant for these yet (BRIEF-0116-B reads them).
_TRIAL_COLUMNS = ("trial_to_rank_1", "trial_to_rank_2", "trial_to_rank_3", "trial_to_rank_4", "trial_to_rank_5")
_TERM_COLUMNS = "id, world_id, {parent}, term_order, direction, currency, counterparty_entity_id, item_id, " \
                "fact_id, skill_key, amount, level"
_REQUEST_COLUMNS = ('id, world_id, character_id, pass_play_id, agenda_step_id, "trigger", declaration, subject, '
                    "status, existence_answer, creator_text, existing_entity_id, lore_entry_id, mutation_id, "
                    "offer_id, note, created_at, updated_at, change_history")

_REBUILT = ("quest_offer_term", "quest_term", "quest_request")
# The tables this migration writes: the foreign-key comparison is scoped to them.
_CHECKED_TABLES = ("skill_rank", "skill_system", "skill_definition") + _REBUILT
_EXPECTED_CHECKS = {
    "quest_offer_term": ("ck_quest_offer_term_direction", "ck_quest_offer_term_currency",
                         "ck_quest_offer_term_shape"),
    "quest_term": ("ck_quest_term_direction", "ck_quest_term_currency", "ck_quest_term_shape"),
    "quest_request": ("ck_quest_request_trigger", "ck_quest_request_status", "ck_quest_request_answer",
                      "ck_quest_request_origin"),
}
_EXPECTED_INDEXES = {
    "quest_offer_term": {"idx_quest_offer_term_offer": False},
    "quest_term": {"idx_quest_term_quest": False},
    "quest_request": {"idx_quest_request_world": False, "idx_quest_request_step": True,
                      "idx_quest_request_trial": False},
}


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _refuse_if_behind() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.29 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _columns(table: str) -> set[str]:
    return {c["name"] for c in inspect(engine).get_columns(table)}


def _table_sql(table: str) -> str:
    with engine.connect() as conn:
        return conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:n"),
                            {"n": table}).scalar_one()


def _counts() -> dict[str, int]:
    with engine.connect() as conn:
        return {table: conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one() for table in _REBUILT}


def _dangling() -> set[tuple]:
    with engine.connect() as conn:
        return {
            tuple(row)
            for table in _CHECKED_TABLES
            for row in conn.execute(text(f"PRAGMA foreign_key_check({table})")).fetchall()
        }


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


def _plan() -> tuple[list[str], list[tuple]]:
    """(ADD COLUMN statements, (model, copied columns) rebuilds) still to apply."""
    adds: list[str] = []
    if "trial_to_next" not in _columns("skill_rank"):
        adds.append("ALTER TABLE skill_rank ADD COLUMN trial_to_next BOOLEAN NOT NULL DEFAULT 0")
    for table in ("skill_system", "skill_definition"):
        present = _columns(table)
        adds += [f"ALTER TABLE {table} ADD COLUMN {c} BOOLEAN" for c in _TRIAL_COLUMNS if c not in present]
    rebuilds: list[tuple] = []
    for model, parent in ((models.QuestOfferTerm, "offer_id"), (models.QuestTerm, "quest_id")):
        if "'rank'" not in _table_sql(model.__tablename__):
            rebuilds.append((model, _TERM_COLUMNS.format(parent=parent)))
    if "skill_key" not in _columns("quest_request"):
        rebuilds.append((models.QuestRequest, _REQUEST_COLUMNS))
    return adds, rebuilds


def _apply_ddl() -> list[str]:
    """One raw transaction (see the module docstring)."""
    adds, rebuilds = _plan()
    if not adds and not rebuilds:
        return []
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("PRAGMA legacy_alter_table=ON")
        cursor.execute("BEGIN")
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
    added = [f"{len(adds)} column(s) added"] if adds else []
    return added + [f"{model.__tablename__} rebuilt" for model, _ in rebuilds]


def _post_checks(before: dict[str, int], dangling_before: set[tuple]) -> None:
    problems: list[str] = []
    after = _counts()
    if after != before:
        problems.append(f"row counts {before} -> {after}")
    expected_columns = {"skill_rank": ("trial_to_next",), "skill_system": _TRIAL_COLUMNS,
                        "skill_definition": _TRIAL_COLUMNS, "quest_request": ("skill_key", "target_rank")}
    for table, columns in expected_columns.items():
        missing = [c for c in columns if c not in _columns(table)]
        if missing:
            problems.append(f"{table} lacks {missing}")
    if not problems:
        with engine.connect() as conn:
            flagged = conn.execute(text("SELECT COUNT(*) FROM skill_rank WHERE trial_to_next <> 0")).scalar_one()
        if flagged:
            problems.append(f"{flagged} skill_rank row(s) ask a trial")
    inspector = inspect(engine)
    for table, names in _EXPECTED_CHECKS.items():
        present = {ck["name"] for ck in inspector.get_check_constraints(table)}
        problems += [f"{table} lacks CHECK {n}" for n in names if n not in present]
    for table, expected in _EXPECTED_INDEXES.items():
        have = {i["name"]: bool(i["unique"]) for i in inspector.get_indexes(table)}
        problems += [f"{table} index {n} missing or unique != {u}" for n, u in expected.items() if have.get(n) != u]
    dangling_after = _dangling()
    new = dangling_after - dangling_before
    if new:
        problems.append(f"foreign_key_check, new dangling rows {sorted(new)}")
    if problems:
        raise SystemExit("Migration v2.29 aborted, post-check failed: " + "; ".join(problems) + ".")
    for table, rowid, parent, _fk in sorted(dangling_after & dangling_before):
        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
    print(f"Post-check: rows kept {after}; the eleven columns present; no rank asks a trial; "
          "constraints and indexes present.")


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
    print("Migration v2.29 — rank trials: the trial columns, the rank currency, the trial request")
    _refuse_if_behind()
    before = _counts()
    dangling_before = _dangling()
    applied = _apply_ddl()
    print("Applied: " + ", ".join(applied) + "." if applied else "DDL already applied.")
    _post_checks(before, dangling_before)
    _converge_schema_meta()
    print("\nMigration v2.29 applied.")


if __name__ == "__main__":
    main()
