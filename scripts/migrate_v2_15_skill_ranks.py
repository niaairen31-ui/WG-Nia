"""Migration v2.15 — a skill has a rank and points (TICKET-0106, BRIEF-0106-A,
decisions G1, L1, O1, P2, T1, U2).

1. `skill_system` and `skill_definition` gain five nullable columns,
   `points_to_rank_1` .. `points_to_rank_5` (a positive count, or NULL to
   inherit), and `skill` loses `tier` for `rank` (0-5) and `xp` (>= 0). SQLite
   cannot add a table CHECK nor drop a column a CHECK names, so the three
   tables are rebuilt from the models (`migrate_v1_95_parked_plans.py`
   precedent: raw DBAPI connection, `PRAGMA foreign_keys=OFF` and
   `legacy_alter_table=ON` before `BEGIN`, rename, create from the model,
   copy, drop), in one transaction. Every row is kept; each former tier
   becomes its rank through `skill_ranks.TIER_TO_RANK` (-1/0/1/2 ->
   0/1/2/3), so no roll changes (L1); `xp` starts at 0. A `change_history`
   entry written before this migration keeps its `tier` key: history is
   never rewritten.
2. Creates `skill_rank` (a world's rank names and default points, O1/P2)
   empty: a world without rows reads the engine defaults
   (`skill_ranks.world_ladder`), so nothing is seeded.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.14 (the migrations are sequential), and on a `skill.tier` value
outside -1..2 (nothing to map it to), before any change.

Idempotent: each table is rebuilt only while it lacks its new columns;
`skill_rank` is created only when missing.

Post-checks, before `schema_meta` converges: row counts kept, `skill` has no
`tier` column and every rank is within 0-5, the three tables carry the
models' CHECK constraints, `skill_rank` exists, and
`PRAGMA foreign_key_check` is empty.

Run from the project root:

    python scripts/migrate_v2_15_skill_ranks.py
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
        "migrate_v2_15_skill_ranks.py refuses to run without WORLD_ENGINE_ENV "
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
from world_engine.skill_ranks import RANK_POINTS_COLUMNS, TIER_TO_RANK  # noqa: E402

_PREVIOUS_VERSION = "v2.14"

_SYSTEM_COLUMNS = "id, world_id, name, description, created_at, updated_at"
_DEFINITION_COLUMNS = (
    "id, world_id, name, base_domain, system_id, description, created_at, updated_at"
)
_SKILL_KEPT = "id, character_id, domain, change_history, skill_definition_id, created_at, updated_at"
_RANK_OF_TIER = "CASE tier " + " ".join(
    f"WHEN {tier} THEN {rank}" for tier, rank in sorted(TIER_TO_RANK.items())
) + " END"

_EXPECTED_CHECKS = {
    "skill_system": {"ck_skill_system_rank_points"},
    "skill_definition": {"ck_skill_definition_base_domain", "ck_skill_definition_rank_points"},
    "skill": {"ck_skill_rank", "ck_skill_xp"},
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
            f"Migration v2.15 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _columns(table: str) -> set[str]:
    return {c["name"] for c in inspect(engine).get_columns(table)}


def _refuse_unmapped_tiers() -> None:
    if "tier" not in _columns("skill"):
        return
    allowed = ", ".join(str(t) for t in sorted(TIER_TO_RANK))
    with engine.connect() as conn:
        bad = conn.execute(text(f"SELECT id, tier FROM skill WHERE tier NOT IN ({allowed})")).fetchall()
    if bad:
        raise SystemExit(f"Migration v2.15 refused: skill row(s) with a tier outside -1..2: {bad}.")


def _counts() -> dict[str, int]:
    with engine.connect() as conn:
        return {
            table: conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            for table in ("skill_system", "skill_definition", "skill")
        }


def _create_from_model(cursor, model) -> None:
    cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
    for index in model.__table__.indexes:
        cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))


def _rebuild(cursor, model, insert_columns: str, select_columns: str) -> None:
    table = model.__tablename__
    for (index_name,) in cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL",
        (table,),
    ).fetchall():
        cursor.execute(f"DROP INDEX {index_name}")
    cursor.execute(f"ALTER TABLE {table} RENAME TO {table}_old")
    _create_from_model(cursor, model)
    cursor.execute(f"INSERT INTO {table} ({insert_columns}) SELECT {select_columns} FROM {table}_old")
    cursor.execute(f"DROP TABLE {table}_old")


def _rebuild_plan() -> list[tuple]:
    """(model, insert columns, select expression) per table still missing its
    new columns, parents first."""
    plan: list[tuple] = []
    for model, kept in ((models.SkillSystem, _SYSTEM_COLUMNS), (models.SkillDefinition, _DEFINITION_COLUMNS)):
        if RANK_POINTS_COLUMNS[0] not in _columns(model.__tablename__):
            plan.append((model, kept, kept))
    if "tier" in _columns("skill"):
        plan.append((models.Skill, f"{_SKILL_KEPT}, rank, xp", f"{_SKILL_KEPT}, {_RANK_OF_TIER}, 0"))
    return plan


def _apply_ddl() -> list[str]:
    """One raw transaction (see the module docstring): the rebuilds, then
    `skill_rank` when missing."""
    plan = _rebuild_plan()
    create_ladder = "skill_rank" not in set(inspect(engine).get_table_names())
    if not plan and not create_ladder:
        return []
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("PRAGMA legacy_alter_table=ON")
        cursor.execute("BEGIN")
        for model, insert_columns, select_columns in plan:
            _rebuild(cursor, model, insert_columns, select_columns)
        if create_ladder:
            _create_from_model(cursor, models.SkillRank)
        cursor.execute("COMMIT")
        cursor.execute("PRAGMA legacy_alter_table=OFF")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()
    applied = [f"{model.__tablename__} rebuilt" for model, _, _ in plan]
    return applied + (["skill_rank table"] if create_ladder else [])


def _post_checks(before: dict[str, int]) -> None:
    after = _counts()
    if after != before:
        raise SystemExit(f"Migration v2.15 aborted, post-check failed: row counts {before} -> {after}.")
    if "tier" in _columns("skill") or not {"rank", "xp"} <= _columns("skill"):
        raise SystemExit("Migration v2.15 aborted, post-check failed: skill still has tier, or lacks rank/xp.")
    inspector = inspect(engine)
    for table, expected in _EXPECTED_CHECKS.items():
        present = {ck["name"] for ck in inspector.get_check_constraints(table)}
        if not expected <= present:
            raise SystemExit(f"Migration v2.15 aborted, post-check failed: {table} lacks {expected - present}.")
    if "skill_rank" not in set(inspector.get_table_names()):
        raise SystemExit("Migration v2.15 aborted, post-check failed: skill_rank is missing.")
    with engine.connect() as conn:
        out_of_range = conn.execute(text("SELECT COUNT(*) FROM skill WHERE rank NOT BETWEEN 0 AND 5")).scalar_one()
        dangling = conn.execute(text("PRAGMA foreign_key_check")).fetchall()
    if out_of_range or dangling:
        raise SystemExit(
            f"Migration v2.15 aborted, post-check failed: {out_of_range} rank(s) out of range, "
            f"foreign_key_check {dangling}."
        )
    print(f"Post-check: rows kept {after}; ranks within 0-5; constraints present; skill_rank exists.")


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
    print("Migration v2.15 — skill rank and points, rank thresholds, skill_rank")
    _refuse_if_behind()
    _refuse_unmapped_tiers()
    before = _counts()
    applied = _apply_ddl()
    print("Applied: " + ", ".join(applied) + "." if applied else "DDL already applied.")
    _post_checks(before)
    _converge_schema_meta()
    print("\nMigration v2.15 applied.")


if __name__ == "__main__":
    main()
