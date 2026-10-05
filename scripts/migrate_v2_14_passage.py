"""Migration v2.14 — what a character keeps of a fact: `passage`, and the
last contact of an encounter (TICKET-0105, BRIEF-0105-A, decisions B5, M1,
Q1, V1).

1. DDL. Creates `passage` (`id, world_id, entity_id, location_id, last_at`,
   UNIQUE index `idx_passage_entity_location`, index `idx_passage_location`)
   and adds the nullable column `rencontre.last_at`.
2. Tenue (V1). Every `tenue` fact with no `fact_default` row and exactly one
   participant receives the `rencontre` default its facet now presets: scope
   = that participant, level `knows`, through `writes.facts.
   create_fact_default`. A `tenue` fact with zero or several participants is
   listed, never changed.
3. Encounters (Q1). Every `rencontre` row whose `last_at` is NULL gets the
   migration's own time: everyone who has met is taken to have seen the
   other as they are today. Taken AFTER step 2, so the new tenue defaults
   are not newer than the contact that reveals them.
4. Passages (M1), only while `passage` is empty: one row per (character,
   location) for every character's current location and every NPC schedule
   row (the migration's time), and for every `visit` row (the latest
   `entered_at` of that player at that place). A later run finds the table
   filled and writes nothing.

Change histories are not touched: an entry without a `kind` reads as a
correction (M1), so nobody's knowledge is stale after this migration.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.13 (the migrations are sequential).

Idempotent: the table and the column are created only when missing; steps 2
and 3 find nothing left to do on a second run; step 4 runs only on an empty
table.

Post-checks, before `schema_meta` converges: `passage` exists, no
`rencontre` row has a NULL `last_at`, and every one-participant `tenue` fact
has a `fact_default` row.

Run from the project root:

    python scripts/migrate_v2_14_passage.py
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
        "migrate_v2_14_passage.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import inspect, text  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.models import (  # noqa: E402
    Character, Entity, Fact, FactDefault, FactParticipant, NpcSchedule, Passage, Rencontre, Visit,
)
from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402
from world_engine.writes.facts import create_fact_default  # noqa: E402

_PREVIOUS_VERSION = "v2.13"
_CREATED_BY = "migrate_v2_14"


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _refuse_if_behind() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.14 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _apply_ddl() -> list[str]:
    applied: list[str] = []
    inspector = inspect(engine)
    with engine.begin() as conn:
        if "passage" not in set(inspector.get_table_names()):
            conn.execute(text(
                """
CREATE TABLE passage (
  id           TEXT PRIMARY KEY NOT NULL,
  world_id     TEXT NOT NULL REFERENCES world(id),
  entity_id    TEXT NOT NULL REFERENCES entity(id),
  location_id  TEXT NOT NULL REFERENCES entity(id),
  last_at      DATETIME NOT NULL
)
"""
            ))
            conn.execute(text(
                "CREATE UNIQUE INDEX idx_passage_entity_location ON passage(entity_id, location_id)"
            ))
            conn.execute(text("CREATE INDEX idx_passage_location ON passage(location_id)"))
            applied.append("passage table + idx_passage_entity_location + idx_passage_location")
        if "last_at" not in {c["name"] for c in inspector.get_columns("rencontre")}:
            conn.execute(text("ALTER TABLE rencontre ADD COLUMN last_at DATETIME"))
            applied.append("rencontre.last_at")
    return applied


def _participants(session: Session, fact_id: str) -> list[str]:
    return list(session.exec(
        select(FactParticipant.entity_id).where(FactParticipant.fact_id == fact_id)
    ).all())


def _tenue_defaults(session: Session) -> int:
    defaulted = set(session.exec(select(FactDefault.fact_id)).all())
    added = 0
    for fact in session.exec(select(Fact).where(Fact.facet == "tenue")).all():
        if fact.id in defaulted:
            continue
        owners = _participants(session, fact.id)
        if len(owners) != 1:
            print(f"  tenue {fact.id} has {len(owners)} participant(s): left without a default.")
            continue
        create_fact_default(
            session, world_id=fact.world_id, fact_id=fact.id, scope_type="rencontre",
            scope_id=owners[0], level="knows", created_by=_CREATED_BY,
        )
        added += 1
    session.flush()
    return added


def _encounters(session: Session, now: datetime) -> int:
    rows = session.exec(select(Rencontre).where(Rencontre.last_at.is_(None))).all()
    for row in rows:
        row.last_at = now
        session.add(row)
    session.flush()
    return len(rows)


def _utc(value: datetime) -> datetime:
    """`visit.entered_at` reads back naive (plain `DateTime`); it is UTC."""
    return value.replace(tzinfo=UTC) if value.utcoffset() is None else value.astimezone(UTC)


def _passages(session: Session, now: datetime) -> int:
    if session.exec(select(Passage.id)).first() is not None:
        print("Table passage already filled — no backfill.")
        return 0
    latest: dict[tuple[str, str], tuple[str, datetime]] = {}

    def keep(world_id: str, entity_id: str, location_id: str, at: datetime) -> None:
        key = (entity_id, location_id)
        if key not in latest or latest[key][1] < at:
            latest[key] = (world_id, at)

    for char, entity in session.exec(
        select(Character, Entity).join(Entity, Entity.id == Character.id)
        .where(Character.current_location_id.is_not(None))
    ).all():
        keep(entity.world_id, char.id, char.current_location_id, now)
    for row in session.exec(select(NpcSchedule)).all():
        keep(row.world_id, row.npc_id, row.location_id, now)
    for row in session.exec(select(Visit)).all():
        keep(row.world_id, row.player_id, row.location_id, _utc(row.entered_at) if row.entered_at else now)
    for (entity_id, location_id), (world_id, at) in latest.items():
        session.add(Passage(world_id=world_id, entity_id=entity_id,
                            location_id=location_id, last_at=at))
    session.flush()
    return len(latest)


def _apply_data() -> None:
    with Session(engine) as session:
        tenues = _tenue_defaults(session)
        now = datetime.now(UTC)
        encounters = _encounters(session, now)
        passages = _passages(session, now)
        session.commit()
    print(f"Tenue defaults added: {tenues}. Encounters dated: {encounters}. "
          f"Passages filled: {passages}.")


def _post_checks() -> None:
    if "passage" not in set(inspect(engine).get_table_names()):
        raise SystemExit("Migration v2.14 aborted, post-check failed: passage is missing.")
    with Session(engine) as session:
        undated = session.exec(select(Rencontre.id).where(Rencontre.last_at.is_(None))).all()
        if undated:
            raise SystemExit(
                f"Migration v2.14 aborted, post-check failed: {len(undated)} rencontre row(s) "
                "without last_at."
            )
        defaulted = set(session.exec(select(FactDefault.fact_id)).all())
        bare = [
            fact.id for fact in session.exec(select(Fact).where(Fact.facet == "tenue")).all()
            if fact.id not in defaulted and len(_participants(session, fact.id)) == 1
        ]
        if bare:
            raise SystemExit(
                f"Migration v2.14 aborted, post-check failed: tenue fact(s) without a "
                f"default: {bare}."
            )
    print("Post-check: passage exists; every rencontre row is dated; every tenue has a default.")


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
    print("Migration v2.14 — passage, rencontre.last_at, tenue defaults")
    _refuse_if_behind()
    applied = _apply_ddl()
    print("Applied: " + ", ".join(applied) + "." if applied else "DDL already applied.")
    _apply_data()
    _post_checks()
    _converge_schema_meta()
    print("\nMigration v2.14 applied.")


if __name__ == "__main__":
    main()
