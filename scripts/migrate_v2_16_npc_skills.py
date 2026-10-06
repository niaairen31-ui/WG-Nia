"""Migration v2.16 — NPC skill sheets and skills learned from a master
(TICKET-0107, BRIEF-0107-A, decisions A2, C1, D1, E1).

1. DDL. Adds `skill_definition.requires_master` (BOOLEAN NOT NULL DEFAULT 0:
   no existing skill requires a master) and the nullable
   `skill.taught_by_id` (FK `entity`; every existing row was seeded, taught
   by nobody).
2. Carrures (E1). Every NPC whose `character.physical_tier` is not 0, and
   who holds no `physical` base row, receives one at
   `skill_ranks.TIER_TO_RANK[physical_tier]` (the former tier's exact
   modifier), through `writes.write_skill_row`. A player character's
   `physical_tier` is ignored (counted): its roll always read its own rows.
3. Drops `character.physical_tier` (`ALTER TABLE ... DROP COLUMN`, SQLite
   3.35 or later; refused below, before any change).

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.15 (the migrations are sequential), and on a `physical_tier` outside
-1..2 (nothing to map it to), before any change.

Idempotent: each column is added only when missing; step 2 and 3 run only
while `character.physical_tier` exists.

Post-checks, before `schema_meta` converges: both new columns exist,
`character.physical_tier` is gone, every converted NPC holds its `physical`
row at the mapped rank, and `PRAGMA foreign_key_check` is empty on the three
tables this migration changes (`skill`, `skill_definition`, `character`).
A dangling reference elsewhere in the database predates it: it is listed,
never a reason to stop (AMENDMENT-0107-01).

Run from the project root:

    python scripts/migrate_v2_16_npc_skills.py
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

_env = os.environ.get("WORLD_ENGINE_ENV")
if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
    print(
        "migrate_v2_16_npc_skills.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import inspect, text  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.models import Skill  # noqa: E402
from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402
from world_engine.skill_ranks import TIER_TO_RANK  # noqa: E402
from world_engine.writes import write_skill_row  # noqa: E402

_PREVIOUS_VERSION = "v2.15"
# The tables this migration writes: the only ones its foreign-key post-check judges.
_TOUCHED_TABLES = ("skill", "skill_definition", "character")


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _columns(table: str) -> set[str]:
    return {c["name"] for c in inspect(engine).get_columns(table)}


def _refuse() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.16 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )
    if sqlite3.sqlite_version_info < (3, 35, 0):
        raise SystemExit(f"Migration v2.16 refused: SQLite {sqlite3.sqlite_version} cannot drop a column (3.35+).")
    if "physical_tier" in _columns("character"):
        allowed = ", ".join(str(t) for t in sorted(TIER_TO_RANK))
        with engine.connect() as conn:
            bad = conn.execute(text(f"SELECT id, physical_tier FROM character WHERE physical_tier NOT IN ({allowed})")).fetchall()
        if bad:
            raise SystemExit(f"Migration v2.16 refused: physical_tier outside -1..2: {bad}.")


def _add_columns() -> list[str]:
    applied: list[str] = []
    with engine.begin() as conn:
        if "requires_master" not in _columns("skill_definition"):
            conn.execute(text("ALTER TABLE skill_definition ADD COLUMN requires_master BOOLEAN NOT NULL DEFAULT 0"))
            applied.append("skill_definition.requires_master")
        if "taught_by_id" not in _columns("skill"):
            conn.execute(text("ALTER TABLE skill ADD COLUMN taught_by_id VARCHAR REFERENCES entity (id)"))
            applied.append("skill.taught_by_id")
    return applied


def _convert_carrures() -> dict[str, int]:
    """{npc_id: rank} written; prints the players' non-zero tiers it ignores."""
    with engine.connect() as conn:
        tiers = conn.execute(text(
            "SELECT id, character_type, physical_tier FROM character WHERE physical_tier <> 0"
        )).fetchall()
    converted: dict[str, int] = {}
    with Session(engine) as session:
        for character_id, character_type, tier in tiers:
            if character_type != "npc":
                print(f"  player {character_id}: physical_tier {tier} ignored (its own rows are rolled).")
                continue
            held = session.exec(select(Skill).where(
                Skill.character_id == character_id, Skill.domain == "physical",
                Skill.skill_definition_id.is_(None))).first()
            if held is not None:
                continue
            write_skill_row(session, character_id=character_id, domain="physical", rank=TIER_TO_RANK[tier])
            converted[character_id] = TIER_TO_RANK[tier]
        session.commit()
    return converted


def _drop_physical_tier() -> None:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE character DROP COLUMN physical_tier"))


def _post_checks(converted: dict[str, int]) -> None:
    if "requires_master" not in _columns("skill_definition") or "taught_by_id" not in _columns("skill"):
        raise SystemExit("Migration v2.16 aborted, post-check failed: a new column is missing.")
    if "physical_tier" in _columns("character"):
        raise SystemExit("Migration v2.16 aborted, post-check failed: character.physical_tier still exists.")
    with Session(engine) as session:
        for npc_id, rank in converted.items():
            row = session.exec(select(Skill).where(
                Skill.character_id == npc_id, Skill.domain == "physical",
                Skill.skill_definition_id.is_(None))).first()
            if row is None or row.rank != rank:
                raise SystemExit(f"Migration v2.16 aborted, post-check failed: NPC {npc_id} physical row {row}.")
    with engine.connect() as conn:
        dangling = [row for table in _TOUCHED_TABLES
                    for row in conn.execute(text(f"PRAGMA foreign_key_check({table})")).fetchall()]
        elsewhere = [row for row in conn.execute(text("PRAGMA foreign_key_check")).fetchall()
                     if row[0] not in _TOUCHED_TABLES]
    if dangling:
        raise SystemExit(f"Migration v2.16 aborted, post-check failed: foreign_key_check {dangling}.")
    for table, rowid, parent, _fk in elsewhere:
        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
    print(f"Post-check: columns in place; physical_tier dropped; {len(converted)} carrure(s) converted.")


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
    print("Migration v2.16 — NPC skill sheets, requires_master, taught_by_id, physical_tier dropped")
    _refuse()
    applied = _add_columns()
    print("Applied: " + ", ".join(applied) + "." if applied else "Columns already present.")
    converted: dict[str, int] = {}
    if "physical_tier" in _columns("character"):
        converted = _convert_carrures()
        _drop_physical_tier()
        print(f"Carrures converted: {len(converted)}. character.physical_tier dropped.")
    else:
        print("character.physical_tier already dropped — no conversion.")
    _post_checks(converted)
    _converge_schema_meta()
    print("\nMigration v2.16 applied.")


if __name__ == "__main__":
    main()
