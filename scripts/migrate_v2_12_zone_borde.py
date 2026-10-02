"""Migration v2.12 — `borde`, the geographic link that touches a zone
(TICKET-0101, BRIEF-0101-D, decisions O1, N1, T1).

1. Index (O1). `idx_relation_oriented_social` is rebuilt with the predicate
   `type NOT IN ('connects_to','borde','controls')` — the same split as
   `relation_orientation.RELATION_GRAPH_EXCLUDED_TYPES`. The new predicate
   covers a subset of the old one's rows, so the rebuild cannot fail on
   existing data.
2. Conversion (N1). Every `connects_to` row touching a location that is
   already a zone (`zone_rules.zone_ids`: at least one active child) is
   retyped in place to `borde` through `writes.relations.write_relation
   (mode="set")`: the row's previous state goes to its `change_history`,
   its typed fact is rewritten (`borde_fact_content`) with the previous
   content kept in the fact's `change_history`. No row is created or
   deleted. Each conversion is printed.
3. Report (T1). Characters, NPC schedule rows, items lying somewhere and
   discoverable details that already sit in a zone are LISTED, never moved
   — Nia corrects them through the fiche.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.11 (the migrations are sequential).

Idempotent: the index is rebuilt only while its stored SQL lacks `'borde'`;
a second run finds no `connects_to` touching a zone and writes nothing.

Post-checks, before `schema_meta` converges: the stored index SQL names
`'borde'`; zero `connects_to` rows touch a zone; the `relation` row count is
unchanged.

Run from the project root:

    python scripts/migrate_v2_12_zone_borde.py
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
        "migrate_v2_12_zone_borde.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import text  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.models import (  # noqa: E402
    Character, DiscoverableDetail, Entity, Item, NpcSchedule, Relation, World,
)
from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402
from world_engine.writes.relations import write_relation  # noqa: E402
from world_engine.zone_rules import zone_ids  # noqa: E402

_PREVIOUS_VERSION = "v2.11"
_INDEX = "idx_relation_oriented_social"
_INDEX_DDL = (
    f"CREATE UNIQUE INDEX {_INDEX} ON relation(entity_a_id, entity_b_id) "
    "WHERE type NOT IN ('connects_to','borde','controls')"
)
_CHANGED_BY = "migrate_v2_12"


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _refuse_if_behind() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.12 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _index_sql() -> str:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT sql FROM sqlite_master WHERE type = 'index' AND name = :name"), {"name": _INDEX}
        ).first()
    return row[0] if row is not None and row[0] else ""


def _rebuild_index() -> bool:
    if "'borde'" in _index_sql():
        print(f"Index {_INDEX} already excludes 'borde' — nothing to do.")
        return False
    with engine.begin() as conn:
        conn.execute(text(f"DROP INDEX IF EXISTS {_INDEX}"))
        conn.execute(text(_INDEX_DDL))
    print(f"Index {_INDEX} rebuilt: type NOT IN ('connects_to','borde','controls').")
    return True


def _zones_by_world(session: Session) -> dict[str, set[str]]:
    return {w.id: zone_ids(session, w.id) for w in session.exec(select(World)).all()}


def _names(session: Session, ids: set[str]) -> dict[str, str]:
    if not ids:
        return {}
    return {e.id: e.name for e in session.exec(select(Entity).where(Entity.id.in_(ids))).all()}


def _convert(session: Session, zones: set[str]) -> int:
    rows = session.exec(select(Relation).where(Relation.type == "connects_to")).all()
    touching = [r for r in rows if r.entity_a_id in zones or r.entity_b_id in zones]
    names = _names(session, {r.entity_a_id for r in touching} | {r.entity_b_id for r in touching})
    for rel in touching:
        write_relation(
            session, mode="set", relation_id=rel.id, type="borde", value=rel.intensity,
            direction=rel.direction, visible_to_b=rel.visible_to_b, notes=rel.notes,
            changed_by=_CHANGED_BY,
        )
        print(f"  borde: {names.get(rel.entity_a_id)} -- {names.get(rel.entity_b_id)} (relation {rel.id})")
    return len(touching)


def _report(session: Session, zones: set[str]) -> int:
    """T1: what already sits in a zone, listed, never moved."""
    if not zones:
        return 0
    names = _names(session, zones)
    lines: list[str] = []
    for char, ent in session.exec(
        select(Character, Entity).join(Entity, Entity.id == Character.id)
        .where(Character.current_location_id.in_(zones))
    ).all():
        lines.append(f"  personnage « {ent.name} » est dans la zone « {names[char.current_location_id]} »")
    for row in session.exec(select(NpcSchedule).where(NpcSchedule.location_id.in_(zones))).all():
        npc = session.get(Entity, row.npc_id)
        lines.append(f"  horaire {row.phase} de « {npc.name if npc else row.npc_id} » vise la zone "
                     f"« {names[row.location_id]} »")
    for item, ent in session.exec(
        select(Item, Entity).join(Entity, Entity.id == Item.id).where(Item.location_id.in_(zones))
    ).all():
        lines.append(f"  objet « {ent.name} » est posé dans la zone « {names[item.location_id]} »")
    for detail in session.exec(select(DiscoverableDetail).where(DiscoverableDetail.location_id.in_(zones))).all():
        lines.append(f"  détail « {detail.subject} » est dans la zone « {names[detail.location_id]} »")
    for line in lines:
        print(line)
    return len(lines)


def _post_checks(session: Session, relations_before: int) -> None:
    if "'borde'" not in _index_sql():
        raise SystemExit(f"Migration v2.12 aborted, post-check failed: {_INDEX} does not exclude 'borde'.")
    zones = set().union(*_zones_by_world(session).values())
    left = [
        r.id for r in session.exec(select(Relation).where(Relation.type == "connects_to")).all()
        if r.entity_a_id in zones or r.entity_b_id in zones
    ]
    if left:
        raise SystemExit(f"Migration v2.12 aborted, post-check failed: connects_to still touches a zone: {left}")
    after = session.exec(select(Relation)).all()
    if len(after) != relations_before:
        raise SystemExit(
            f"Migration v2.12 aborted, post-check failed: relation rows {relations_before} -> {len(after)}."
        )
    print(f"Post-check: no connects_to touches a zone; relation rows unchanged ({relations_before}).")


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
    print("Migration v2.12 — borde, the geographic link that touches a zone")
    _refuse_if_behind()
    rebuilt = _rebuild_index()
    with Session(engine) as session:
        relations_before = len(session.exec(select(Relation)).all())
        converted = 0
        reported = 0
        for world_id, zones in _zones_by_world(session).items():
            print(f"World {world_id}: {len(zones)} zone(s).")
            converted += _convert(session, zones)
            reported += _report(session, zones)
        session.flush()
        _post_checks(session, relations_before)
        session.commit()
    print(f"Converted {converted} connects_to -> borde; {reported} placement(s) in a zone reported "
          "(not moved — correct them through the fiche).")
    if not rebuilt and not converted:
        print("Migration v2.12 already fully applied — zero writes.")
    _converge_schema_meta()
    print("\nMigration v2.12 applied.")


if __name__ == "__main__":
    main()
