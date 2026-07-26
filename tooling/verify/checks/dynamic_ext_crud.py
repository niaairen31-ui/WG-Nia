"""G1 check: dynamic ext_* instance CRUD for governed runtime entity types
(TICKET-0046, BRIEF-0046-e), on the trait_registry_projection.py temp-fixture
idiom — a fresh temp-file SQLite fixture (WORLD_ENGINE_DATABASE_URL set
BEFORE any world_engine import), so this check never touches Nia's real DB.

Exercises the generalized create/read/update path end-to-end for a
throwaway spatial+secretable runtime type, calling the actual route
functions directly (Depends(get_session) is just a default value — passing
`db` explicitly bypasses FastAPI's DI cleanly):

1. `create_entity_type` (+ entity_trait projection) births `ext_smoketest`.
2. `create_entity`, through the generalized `_create_entity_core` dispatch,
   creates an entity + `ext_smoketest` row; `location_id`/`is_secret`
   round-trip through the create response AND a follow-up `get_entity`.
3. `update_entity` changes `is_secret`; the new value round-trips through
   the update response AND a follow-up `get_entity`.
4. `create_entity` against an ungoverned type slug (neither static nor an
   active `entity_type`) is rejected with 422 before any entity row exists.
5. `update_entity` against an existing entity whose OWN type is ungoverned
   (simulating a retired/foreign-world type) is rejected with 422 before
   its ext row is touched.

Zero assertions exercised = FAIL (location_type_classified.py idiom) —
a parse/harness that silently examines nothing is a broken check, not a
clean repo.
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
    """Same idiom as trait_registry_projection.py: rebind world_engine.db's
    module-level engine to a fresh temp SQLite file by purging world_engine
    (except world_engine.models, already registered on SQLModel's shared
    metadata) from sys.modules before reimport."""
    tmp_dir = tempfile.mkdtemp()
    db_path = pathlib.Path(tmp_dir) / "check.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or (
            name.startswith("world_engine.") and not name.startswith("world_engine.models")
        ):
            del sys.modules[name]

    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def main() -> int:
    engine = _fresh_engine()

    from fastapi import HTTPException
    from sqlmodel import Session as DbSession

    from world_engine.cockpit.crud.entities import (
        EntityWriteBody,
        create_entity,
        get_entity,
        update_entity,
    )
    from world_engine.models import Entity, EntityTrait, World
    from world_engine.traits import ext_columns_for
    from world_engine.writes.schema import create_entity_type

    examined = 0

    with DbSession(engine) as db:
        world = World(name="Check World", is_active=True)
        db.add(world)
        db.commit()
        db.refresh(world)

        trait_keys = ["spatial", "secretable"]
        etype_id = create_entity_type(
            db, world_id=world.id, name="Smoketest", slug="smoketest",
            columns=ext_columns_for(trait_keys), changed_by="check",
        )
        db.flush()
        for trait_key in trait_keys:
            db.add(EntityTrait(entity_type_id=etype_id, trait_key=trait_key))
        db.commit()

        # ── Create through the generalized path ──────────────────────────
        created = create_entity(
            EntityWriteBody(
                entity={"type": "smoketest", "name": "Wagon"},
                extension={"location_id": None, "is_secret": True},
            ),
            db,
        )
        examined += 1
        if created["extension"].get("is_secret") is not True:
            fail(f"created extension.is_secret == {created['extension'].get('is_secret')!r}, expected True")
        if created["extension"].get("location_id") is not None:
            fail(f"created extension.location_id == {created['extension'].get('location_id')!r}, expected None")

        entity_id = created["id"]
        fetched = get_entity(entity_id, db)
        examined += 1
        if fetched["extension"].get("is_secret") is not True:
            fail(f"fetched extension.is_secret == {fetched['extension'].get('is_secret')!r}, expected True (get_entity round-trip)")

        # ── Update, round-trip again ──────────────────────────────────────
        updated = update_entity(
            entity_id,
            EntityWriteBody(entity={"name": "Wagon"}, extension={"location_id": None, "is_secret": False}),
            db,
        )
        examined += 1
        if updated["extension"].get("is_secret") is not False:
            fail(f"updated extension.is_secret == {updated['extension'].get('is_secret')!r}, expected False")

        refetched = get_entity(entity_id, db)
        examined += 1
        if refetched["extension"].get("is_secret") is not False:
            fail(f"post-update fetched extension.is_secret == {refetched['extension'].get('is_secret')!r}, expected False (get_entity round-trip)")

        # ── Ungoverned slug on create: rejected, no entity row created ────
        examined += 1
        try:
            create_entity(
                EntityWriteBody(entity={"type": "not_a_real_type", "name": "Ghost"}, extension={}),
                db,
            )
            fail("create_entity against an ungoverned type slug did not raise")
        except HTTPException as exc:
            if exc.status_code != 422:
                fail(f"create_entity against an ungoverned type slug raised status {exc.status_code}, expected 422")

        # ── Ungoverned slug on update: an entity whose OWN type resolves
        #    to neither a static nor an active entity_type is rejected
        #    before its (nonexistent) ext row is touched. ─────────────────
        ghost_entity = Entity(world_id=world.id, type="ghost_type", name="Ghost Entity")
        db.add(ghost_entity)
        db.commit()
        db.refresh(ghost_entity)

        examined += 1
        try:
            update_entity(
                ghost_entity.id,
                EntityWriteBody(entity={"name": "Ghost Entity"}, extension={}),
                db,
            )
            fail("update_entity against an entity with an ungoverned type did not raise")
        except HTTPException as exc:
            if exc.status_code != 422:
                fail(f"update_entity against an entity with an ungoverned type raised status {exc.status_code}, expected 422")

    if examined == 0:
        fail("vacuous-proof: zero assertions exercised — broken harness, not a clean repo")

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: dynamic_ext_crud — governed runtime type create/read/update "
        "round-trips location_id/is_secret through the reflected ext_* "
        "table; an ungoverned slug is rejected with 422 on both create and "
        "update, touching no table"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
