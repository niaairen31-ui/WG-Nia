"""L1 check for TICKET-0040 (BRIEF-0040-e) — door distinct-point invariant.

DB-backed, self-contained fresh temp-file SQLite fixture (WORLD_ENGINE_
DATABASE_URL set BEFORE any world_engine import) — same idiom as
door_coverage.py. FAILURES list, print FAIL lines, sys.exit(1); zero
qualifying locations scanned is a FAIL, not a vacuous pass.

Assertion: for every active location of a world carrying non-NULL, positive
bounds, no two of its `door` rows share the same `(x, y)` within 1e-9.
Locations with NULL bounds are EXCLUDED — their doors are legitimately all
at `(0, 0)` (I1).

Exercises the REAL production writers (`spatial_author.connect_locations` /
`materialize_doors`, `writes.write_location_doors`) to build the positive
fixture (three neighbours -> three distinct perimeter points), forces a
duplicate on purpose to prove the FAIL path names the pair, heals by
deleting and re-materializing (materialize_doors alone does NOT heal two
off-center duplicates) to prove recovery, then proves the G1 path: two
doors hand-placed at the exact bounds center are both re-derived onto
distinct perimeter points by materialize_doors, with
summary["rederived"] == 2.
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


def _make_location(
    session, world_id: str, name: str, *, width=None, height=None, status: str = "active"
) -> str:
    from world_engine.models import Entity, Location

    entity = Entity(world_id=world_id, type="location", name=name, status=status)
    session.add(entity)
    session.commit()
    session.refresh(entity)
    session.add(Location(id=entity.id, bounds_width=width, bounds_height=height))
    session.commit()
    return entity.id


def _scan_duplicates(session, world_id: str):
    """Returns (locations_scanned, duplicate_pairs) — locations of this world
    with non-NULL, positive bounds, and any (x, y) collision among their
    door rows. The query concretely runs every time this is called."""
    from sqlmodel import select

    from world_engine.models import Door, Entity, Location

    locations = session.exec(
        select(Location, Entity)
        .where(Entity.id == Location.id)
        .where(
            Entity.world_id == world_id,
            Entity.type == "location",
            Entity.status == "active",
        )
    ).all()

    scanned = 0
    duplicates: list[tuple[str, str, str, tuple[float, float]]] = []
    for location, entity in locations:
        width, height = location.bounds_width, location.bounds_height
        if width is None or height is None or width <= 0 or height <= 0:
            continue
        scanned += 1
        doors = session.exec(select(Door).where(Door.location_id == entity.id)).all()
        seen: dict[tuple[float, float], str] = {}
        for door in doors:
            key = (round(door.x, 9), round(door.y, 9))
            if key in seen:
                duplicates.append((entity.id, seen[key], door.target_location_id, (door.x, door.y)))
            else:
                seen[key] = door.target_location_id
    return scanned, duplicates


def check_positive_negative_and_healed_fixture(engine) -> None:
    from sqlmodel import Session as DbSession

    from world_engine.models import World
    from world_engine.spatial_author import connect_locations, materialize_doors
    from world_engine.writes import write_location_doors

    with DbSession(engine) as session:
        world = World(name="Check World", is_active=True)
        session.add(world)
        session.commit()
        session.refresh(world)
        world_id = world.id

        loc = _make_location(session, world_id, "Room", width=12.0, height=8.0)
        n1 = _make_location(session, world_id, "N1")
        n2 = _make_location(session, world_id, "N2")
        n3 = _make_location(session, world_id, "N3")

        for neighbour in (n1, n2, n3):
            connect_locations(session, world_id=world_id, entity_a_id=loc, entity_b_id=neighbour, changed_by="check")
        session.commit()

        # ── Positive: three neighbours -> three distinct points ─────────────
        scanned, duplicates = _scan_duplicates(session, world_id)
        if scanned != 1:
            fail(f"expected 1 qualifying location scanned, got {scanned}")
        if duplicates:
            fail(f"unexpected duplicate points on a freshly materialized room: {duplicates}")

        # ── Negative: force two doors onto the same coordinates on purpose ──
        write_location_doors(
            session, world_id=world_id, location_id=loc,
            doors=[
                {"target_location_id": n1, "x": 3.0, "y": 0.0},
                {"target_location_id": n2, "x": 3.0, "y": 0.0},
                {"target_location_id": n3, "x": 12.0, "y": 4.0},
            ],
            changed_by="check",
        )
        session.commit()

        _, duplicates_after_break = _scan_duplicates(session, world_id)
        pair_names = {(d[1], d[2]) for d in duplicates_after_break}
        if (n1, n2) not in pair_names and (n2, n1) not in pair_names:
            fail(f"forcing a duplicate did not surface as a named pair: {duplicates_after_break}")

        # ── Prove materialize_doors alone does NOT heal an off-center dup ───
        materialize_doors(session, world_id=world_id, location_ids=[loc], changed_by="check")
        session.commit()
        _, still_dup = _scan_duplicates(session, world_id)
        if not still_dup:
            fail("materialize_doors unexpectedly healed an off-center duplicate on its own")

        # ── Recovery: delete the doors and re-materialize -> distinct again ─
        from sqlmodel import select as _select

        from world_engine.models import Door as _Door

        for door in session.exec(_select(_Door).where(_Door.location_id == loc)).all():
            session.delete(door)
        session.commit()
        materialize_doors(session, world_id=world_id, location_ids=[loc], changed_by="check")
        session.commit()
        _, healed_duplicates = _scan_duplicates(session, world_id)
        if healed_duplicates:
            fail(f"re-materialization after deletion did not produce distinct points: {healed_duplicates}")


def check_g1_rederivation_path(engine) -> None:
    from sqlmodel import Session as DbSession

    from world_engine.models import World
    from world_engine.spatial_author import connect_locations, materialize_doors
    from world_engine.writes import write_location_doors

    with DbSession(engine) as session:
        world = World(name="Check World G1", is_active=False)
        session.add(world)
        session.commit()
        session.refresh(world)
        world_id = world.id

        loc = _make_location(session, world_id, "Room", width=12.0, height=8.0)
        n1 = _make_location(session, world_id, "N1")
        n2 = _make_location(session, world_id, "N2")

        connect_locations(session, world_id=world_id, entity_a_id=loc, entity_b_id=n1, changed_by="check")
        connect_locations(session, world_id=world_id, entity_a_id=loc, entity_b_id=n2, changed_by="check")
        session.commit()

        # Hand-place both doors at the exact bounds center (H1 placeholder).
        write_location_doors(
            session, world_id=world_id, location_id=loc,
            doors=[
                {"target_location_id": n1, "x": 6.0, "y": 4.0},
                {"target_location_id": n2, "x": 6.0, "y": 4.0},
            ],
            changed_by="check",
        )
        session.commit()

        summary = materialize_doors(session, world_id=world_id, location_ids=[loc], changed_by="check")
        session.commit()

        if summary.get("rederived") != 2:
            fail(f"expected summary['rederived'] == 2 on a two-door exact-center fixture, got {summary}")

        scanned, duplicates = _scan_duplicates(session, world_id)
        if scanned != 1:
            fail(f"G1 fixture: expected 1 qualifying location scanned, got {scanned}")
        if duplicates:
            fail(f"G1 fixture: both doors still at the exact center after materialize_doors: {duplicates}")


def main() -> int:
    engine = _fresh_engine()
    check_positive_negative_and_healed_fixture(engine)
    check_g1_rederivation_path(engine)

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: door_distinct_points — scanned qualifying locations with "
        "non-NULL positive bounds; no two door rows of any location share "
        "the same (x, y); a forced duplicate surfaces by name and heals via "
        "delete + re-materialize; two doors sitting at the exact bounds "
        "center are re-derived onto distinct perimeter points by "
        "materialize_doors (G1, TICKET-0040)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
