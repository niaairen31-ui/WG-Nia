"""G1 check for TICKET-0039 (BRIEF-0039-e) — door coverage invariant.

DB-backed, self-contained fresh temp-file SQLite fixture (WORLD_ENGINE_
DATABASE_URL set BEFORE any world_engine import) — same idiom as
spatial_door_travel.py / scene_join_target.py, so this check never touches
Nia's real DB. FAILURES list, print FAIL lines, sys.exit(1); zero parsed
criteria is never a vacuous pass (door_terminal.py / single_canon_write.py
idiom).

Assertion: for every active `connects_to` relation whose BOTH endpoints are
active locations of a world, BOTH directed `door` rows exist (A->B and
B->A). An edge touching an archived location is excluded — same
active-locations filter as crud/locations.py:get_locations_graph. Exercises
the REAL production writers (`spatial_author.connect_locations` /
`materialize_doors`) to build the positive fixture, breaks one direction on
purpose to prove the FAIL path names the pair, then heals it via
`materialize_doors` to prove the PASS path recovers. A world with zero
qualifying edges prints an explicit "no edges to verify" PASS reason,
reached only if the query concretely ran (an exception during the scan
crashes the check non-zero, never a silent pass).
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    db_path = pathlib.Path(tmp_dir) / "check.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]

    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def _make_location(session, world_id: str, name: str, *, status: str = "active") -> str:
    from world_engine.models import Entity, Location

    entity = Entity(world_id=world_id, type="location", name=name, status=status)
    session.add(entity)
    session.commit()
    session.refresh(entity)
    session.add(Location(id=entity.id))
    session.commit()
    return entity.id


def _scan_coverage(session, world_id: str):
    """Returns (examined_pairs, missing_pairs) for every active connects_to
    edge between two active locations in this world — the query concretely
    runs every time this is called (a broken query raises, it never returns
    a silently-empty result)."""
    from sqlmodel import select

    from world_engine.models import Door, Entity, Relation

    active_location_ids = {
        e.id
        for e in session.exec(
            select(Entity).where(
                Entity.world_id == world_id,
                Entity.type == "location",
                Entity.status == "active",
            )
        ).all()
    }
    rels = session.exec(
        select(Relation).where(Relation.world_id == world_id, Relation.type == "connects_to")
    ).all()
    door_pairs = {
        (d.location_id, d.target_location_id)
        for d in session.exec(select(Door).where(Door.world_id == world_id)).all()
    }

    examined: set[tuple[str, str]] = set()
    missing: list[tuple[str, str]] = []
    for rel in rels:
        a, b = rel.entity_a_id, rel.entity_b_id
        if a not in active_location_ids or b not in active_location_ids:
            continue
        for src, dst in ((a, b), (b, a)):
            if (src, dst) in examined:
                continue
            examined.add((src, dst))
            if (src, dst) not in door_pairs:
                missing.append((src, dst))
    return examined, missing


def check_positive_negative_and_healed_fixture(engine) -> None:
    from sqlmodel import Session as DbSession, select

    from world_engine.models import Door, World
    from world_engine.spatial_author import connect_locations, materialize_doors
    from world_engine.writes import write_relation

    with DbSession(engine) as session:
        world = World(name="Check World", is_active=True)
        session.add(world)
        session.commit()
        session.refresh(world)
        world_id = world.id

        loc_a = _make_location(session, world_id, "A")
        loc_b = _make_location(session, world_id, "B")
        loc_c = _make_location(session, world_id, "C", status="archived")

        connect_locations(session, world_id=world_id, entity_a_id=loc_a, entity_b_id=loc_b, changed_by="check")
        # An edge touching an archived location must never demand coverage.
        write_relation(
            session, mode="set", world_id=world_id,
            entity_a_id=loc_a, entity_b_id=loc_c,
            type="connects_to", value=50, direction="mutual",
        )
        session.commit()

        # ── Positive: both directions materialized for the live A<->B edge ──
        examined, missing = _scan_coverage(session, world_id)
        if len(examined) != 2:
            fail(f"expected 2 directed pairs examined (A->B, B->A), got {len(examined)}: {examined}")
        if missing:
            fail(f"unexpected missing pairs on a freshly materialized edge: {missing}")

        # ── Negative: delete one direction on purpose -> FAILs naming it ────
        door_ba = session.exec(
            select(Door).where(Door.location_id == loc_b, Door.target_location_id == loc_a)
        ).first()
        if door_ba is None:
            fail("fixture setup: B->A door not found before deletion")
        else:
            session.delete(door_ba)
            session.commit()

            _, missing_after_break = _scan_coverage(session, world_id)
            if (loc_b, loc_a) not in missing_after_break:
                fail(f"deleting the B->A door did not surface as a missing pair: {missing_after_break}")

            # ── Restore via materialize_doors -> green again ────────────────
            materialize_doors(session, world_id=world_id, location_ids=[loc_a, loc_b], changed_by="check")
            session.commit()
            _, missing_restored = _scan_coverage(session, world_id)
            if missing_restored:
                fail(f"door coverage still missing after healing via materialize_doors: {missing_restored}")


def check_empty_world_explicit_pass(engine) -> None:
    from sqlmodel import Session as DbSession

    from world_engine.models import World

    with DbSession(engine) as session:
        world = World(name="Empty Check World", is_active=False)
        session.add(world)
        session.commit()
        session.refresh(world)

        examined, missing = _scan_coverage(session, world.id)
        if examined:
            fail(f"expected 0 edges to verify in an empty world, got {len(examined)}")
        if missing:
            fail(f"expected no missing pairs in an empty world, got {missing}")


def main() -> int:
    engine = _fresh_engine()
    check_positive_negative_and_healed_fixture(engine)
    check_empty_world_explicit_pass(engine)

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: door_coverage — every active connects_to edge between active "
        "locations carries both directed door rows; an archived endpoint is "
        "excluded; a broken direction surfaces by name and heals via "
        "materialize_doors; an empty world reaches an explicit "
        "'no edges to verify' pass"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
