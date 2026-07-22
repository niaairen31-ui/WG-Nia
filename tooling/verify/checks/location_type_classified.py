"""G1 check for TICKET-0039 (BRIEF-0039-e) — location_type classified-vocab
invariant, on the door_terminal.py / single_canon_write.py FAILURES idiom
(zero parsed criteria is never a vacuous pass).

DB-backed, self-contained fresh temp-file SQLite fixture (WORLD_ENGINE_
DATABASE_URL set BEFORE any world_engine import) — same idiom as
spatial_door_travel.py / scene_join_target.py, so this check never touches
Nia's real DB.

Assertion: every DISTINCT `location_type` value on an ACTIVE location
exists in `location_type_catalog` (same world), case-insensitively, with a
non-NULL classification in {"interior", "exterior"}. Any type missing from
the catalog, or present but NULL, or with an out-of-vocab classification,
is a FAIL naming the type. An archived location's uncatalogued type must
never surface. Vacuous-proof: when active locations carry a location_type,
the examined-type count must be > 0 — guards against a broken WHERE clause
silently reporting zero criteria on real data.
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


def _scan_classification(session, world_id: str):
    """Returns (examined_type_count, failures) — every DISTINCT location_type
    on an active location of this world, checked against location_type_catalog
    (case-insensitive), the query concretely run every time this is called."""
    from sqlmodel import select

    from world_engine.models import Entity, Location, LocationTypeCatalog

    active_types: set[str] = set()
    for e, loc in session.exec(
        select(Entity, Location)
        .join(Location, Location.id == Entity.id)
        .where(Entity.world_id == world_id, Entity.type == "location", Entity.status == "active")
    ).all():
        if loc.location_type:
            active_types.add(loc.location_type)

    catalog = {
        row.name.casefold(): row.classification
        for row in session.exec(
            select(LocationTypeCatalog).where(LocationTypeCatalog.world_id == world_id)
        ).all()
    }

    failures: list[str] = []
    for type_name in sorted(active_types):
        folded = type_name.casefold()
        if folded not in catalog:
            failures.append(f"location_type {type_name!r} has no location_type_catalog row")
            continue
        classification = catalog[folded]
        if classification not in ("interior", "exterior"):
            failures.append(
                f"location_type {type_name!r} is catalogued with classification "
                f"{classification!r} (must be 'interior' or 'exterior')"
            )
    return len(active_types), failures


def check_classification_fixture(engine) -> None:
    from sqlmodel import Session as DbSession, select

    from world_engine.models import Entity, Location, LocationTypeCatalog, World
    from world_engine.writes import upsert_location_type

    with DbSession(engine) as session:
        world = World(name="Check World", is_active=True)
        session.add(world)
        session.commit()
        session.refresh(world)
        world_id = world.id

        def _loc(name: str, location_type: str, *, status: str = "active") -> str:
            entity = Entity(world_id=world_id, type="location", name=name, status=status)
            session.add(entity)
            session.commit()
            session.refresh(entity)
            session.add(Location(id=entity.id, location_type=location_type))
            session.commit()
            return entity.id

        _loc("Chambre du roi", "Chambre")
        _loc("Rue principale", "Rue")
        _loc("Grotte", "Grotte Mysterieuse")  # uncatalogued
        _loc("Ruine", "Ruine")  # catalogued but NULL classification
        _loc("Cave oubliee", "TypeInconnu", status="archived")  # excluded (not active)

        upsert_location_type(session, world_id=world_id, name="Chambre", classification="interior", changed_by="check")
        upsert_location_type(session, world_id=world_id, name="Rue", classification="exterior", changed_by="check")
        upsert_location_type(session, world_id=world_id, name="Ruine", classification=None, changed_by="check")
        session.commit()

        # ── Vacuous-proof: active locations carry types, so count must be > 0 ──
        examined, failures = _scan_classification(session, world_id)
        if examined == 0:
            fail("vacuous-proof: active locations with a location_type exist but zero distinct types were examined")

        expected_failing = {"Grotte Mysterieuse", "Ruine"}
        for expected in expected_failing:
            if not any(expected in msg for msg in failures):
                fail(f"expected a FAIL naming {expected!r}, got: {failures}")
        if any("TypeInconnu" in msg for msg in failures):
            fail("archived location's uncatalogued type must never surface as a failure")
        if len(failures) != len(expected_failing):
            fail(f"expected exactly {len(expected_failing)} failing types, got: {failures}")

        # ── Classify the remaining types -> green ───────────────────────────
        upsert_location_type(session, world_id=world_id, name="Grotte Mysterieuse", classification="interior", changed_by="check")
        upsert_location_type(session, world_id=world_id, name="Ruine", classification="exterior", changed_by="check")
        session.commit()
        _, failures_after = _scan_classification(session, world_id)
        if failures_after:
            fail(f"expected green after classifying every type, got: {failures_after}")

        # ── Out-of-vocab classification landing via a path other than
        #    upsert_location_type (which validates) -> FAILs naming the type ──
        chambre_row = None
        for row in session.exec(
            select(LocationTypeCatalog).where(LocationTypeCatalog.world_id == world_id)
        ).all():
            if row.name.casefold() == "chambre":
                chambre_row = row
                break
        if chambre_row is None:
            fail("fixture setup: 'Chambre' catalog row not found")
            return
        chambre_row.classification = "both"
        session.add(chambre_row)
        session.commit()

        _, failures_out_of_vocab = _scan_classification(session, world_id)
        if not any("Chambre" in msg and "both" in msg for msg in failures_out_of_vocab):
            fail(f"expected a FAIL naming the out-of-vocab classification, got: {failures_out_of_vocab}")

        # restore
        chambre_row.classification = "interior"
        session.add(chambre_row)
        session.commit()
        _, failures_restored = _scan_classification(session, world_id)
        if failures_restored:
            fail(f"expected green after restoring a valid classification, got: {failures_restored}")


def main() -> int:
    engine = _fresh_engine()
    check_classification_fixture(engine)

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: location_type_classified — every active location's type is "
        "catalogued with a non-NULL interior/exterior classification; an "
        "archived location's uncatalogued type never surfaces; missing, "
        "NULL, and out-of-vocab classifications all FAIL by name"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
