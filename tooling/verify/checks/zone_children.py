"""G1 check for TICKET-0101 (BRIEF-0101-E) — a zone's children take its neighbours.

DB-backed, self-contained fresh temp-file SQLite fixture (WORLD_ENGINE_
DATABASE_URL set BEFORE any world_engine import), driven through the real
routes with `TestClient(app, base_url="http://127.0.0.1")` (origin_guard).
Zero outcomes in any assertion is a FAIL.

Fixture: F, a zone (child F1) with a `borde` to V (visitable) and a `borde`
to Z2 (a zone, child Z2a); A, a visitable anchor with a `connects_to` to S
(visitable) and an NPC standing in A.

Five assertions:
  a. `GET /api/locations/{F}/neighbours` lists V (`is_zone` false) and Z2
     (`is_zone` true), nothing else.
  b. `POST /api/entities` creating E under F with `link_to: [V, Z2]` (F is
     already a zone, so nothing to confirm) is a 201: E-V is `connects_to`
     with its two door rows, E-Z2 is `borde` with none.
  c. `link_to` naming a character is a 422 and creates no entity.
  d. `POST /api/room-batch/commit` with one top-level room R1 under A and
     no `confirm_promotion` is `ok: false`, error `promotion_required`, no
     room committed, A-S still `connects_to`.
  e. The same commit with `confirm_promotion` and `room_links: {R1: [S]}`
     is `ok: true`: A-S is `borde` (same row), A-R1 is `borde` (the tree
     edge), R1-S is `connects_to`, and the NPC stands in R1.

Named mutations: drop `link_new_location(...)` from
`_create_static_entity_core` -> (b); drop `_commit_room_links(...)` from
`commit_room_batch` -> (e); stop passing `confirm_promotion` into the room
bodies -> (e).
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

FAILURES: list[str] = []
COUNTS: dict[str, int] = {}


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _ok(cond: bool, msg: str) -> int:
    if not cond:
        fail(msg)
        return 0
    return 1


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


def _seed(engine) -> dict[str, str]:
    from sqlmodel import Session

    from world_engine.models import Character, Entity, Location, World
    from world_engine.spatial_author import link_locations

    ids: dict[str, str] = {}
    with Session(engine) as db:
        world = World(name="Children check", is_active=True)
        db.add(world)
        db.commit()
        ids["world"] = world.id
        for label, parent in (("F", None), ("F1", "F"), ("V", None), ("Z2", None), ("Z2a", "Z2"),
                              ("A", None), ("S", None)):
            entity = Entity(world_id=world.id, type="location", name=f"Lieu {label}")
            db.add(entity)
            db.flush()
            db.add(Location(id=entity.id, parent_location_id=ids.get(parent) if parent else None))
            db.commit()
            ids[label] = entity.id
        for a, b in (("F", "V"), ("F", "Z2"), ("A", "S")):
            link_locations(db, world_id=world.id, entity_a_id=ids[a], entity_b_id=ids[b], changed_by="check")
        npc = Entity(world_id=world.id, type="character", name="Portier")
        db.add(npc)
        db.flush()
        db.add(Character(id=npc.id, world_id=world.id, character_type="npc", current_location_id=ids["A"]))
        db.commit()
        ids["N"] = npc.id
    return ids


def _rel(db, a: str, b: str):
    from sqlmodel import select

    from world_engine.models import Relation

    return db.exec(select(Relation).where(
        ((Relation.entity_a_id == a) & (Relation.entity_b_id == b))
        | ((Relation.entity_a_id == b) & (Relation.entity_b_id == a))
    )).first()


def _doors(db, a: str, b: str) -> int:
    from sqlmodel import select

    from world_engine.models import Door

    return len(db.exec(select(Door).where(
        ((Door.location_id == a) & (Door.target_location_id == b))
        | ((Door.location_id == b) & (Door.target_location_id == a))
    )).all())


def check_a_neighbours(client, ids) -> None:
    rows = client.get(f"/api/locations/{ids['F']}/neighbours").json()
    got = {r["id"]: r["is_zone"] for r in rows}
    COUNTS["a"] = _ok(got == {ids["V"]: False, ids["Z2"]: True}, f"(a) neighbours of F: {got}") + len(rows)


def check_b_c_children(client, engine, ids) -> None:
    from sqlmodel import Session, select

    from world_engine.models import Entity

    body = {"entity": {"name": "Lieu E", "type": "location", "status": "active"},
            "extension": {"parent_location_id": ids["F"]}, "link_to": [ids["V"], ids["Z2"]]}
    resp = client.post("/api/entities", json=body)
    n = _ok(resp.status_code == 201, f"(b) create under a zone answered {resp.status_code} {resp.text[:120]}")
    if resp.status_code == 201:
        e = resp.json()["id"]
        with Session(engine) as db:
            ev, ez = _rel(db, e, ids["V"]), _rel(db, e, ids["Z2"])
            n += _ok(ev is not None and ev.type == "connects_to", "(b) E-V is not connects_to")
            n += _ok(_doors(db, e, ids["V"]) == 2, "(b) E-V has no door pair")
            n += _ok(ez is not None and ez.type == "borde", "(b) E-Z2 is not borde")
            n += _ok(_doors(db, e, ids["Z2"]) == 0, "(b) E-Z2 got doors")
    COUNTS["b"] = n
    body = {"entity": {"name": "Lieu fautif", "type": "location", "status": "active"},
            "extension": {"parent_location_id": ids["F"]}, "link_to": [ids["N"]]}
    resp = client.post("/api/entities", json=body)
    with Session(engine) as db:
        left = db.exec(select(Entity).where(Entity.name == "Lieu fautif")).first()
    COUNTS["c"] = _ok(resp.status_code == 422 and left is None, f"(c) link_to a character answered {resp.status_code}")


def _batch(ids, **extra) -> dict:
    room = {"local_id": "r1", "name": "Vestibule", "parent_room": None,
            "result": {"draft": {"public": {"name": "Vestibule"}, "facets": {}}}}
    return dict({"anchor_id": ids["A"], "rooms": [room], "accepted": {"r1": True}}, **extra)


def check_d_e_room_batch(client, engine, ids) -> None:
    from sqlmodel import Session, select

    from world_engine.models import Character, Entity

    with Session(engine) as db:
        rel_id = _rel(db, ids["A"], ids["S"]).id
    out = client.post("/api/room-batch/commit", json=_batch(ids)).json()
    with Session(engine) as db:
        room = db.exec(select(Entity).where(Entity.name == "Vestibule")).first()
        n = _ok(out.get("ok") is False and out.get("error") == "promotion_required" and room is None
                and _rel(db, ids["A"], ids["S"]).type == "connects_to", f"(d) unconfirmed batch: {out}")
    COUNTS["d"] = n
    out = client.post("/api/room-batch/commit",
                      json=_batch(ids, confirm_promotion=True, room_links={"r1": [ids["S"]]})).json()
    n = _ok(out.get("ok") is True, f"(e) confirmed batch: {out}")
    with Session(engine) as db:
        room = db.exec(select(Entity).where(Entity.name == "Vestibule")).first()
        if room is not None:
            a_s = _rel(db, ids["A"], ids["S"])
            n += _ok(a_s.id == rel_id and a_s.type == "borde", "(e) A-S not retyped in place to borde")
            n += _ok(_rel(db, ids["A"], room.id).type == "borde", "(e) the tree edge A-R1 is not borde")
            r_s = _rel(db, room.id, ids["S"])
            n += _ok(r_s is not None and r_s.type == "connects_to", "(e) R1-S not linked by connects_to")
            n += _ok(db.get(Character, ids["N"]).current_location_id == room.id, "(e) the NPC did not move to R1")
    COUNTS["e"] = n


def main() -> int:
    engine = _fresh_engine()
    from fastapi.testclient import TestClient

    from world_engine.cockpit.app import app

    ids = _seed(engine)
    client = TestClient(app, base_url="http://127.0.0.1")
    check_a_neighbours(client, ids)
    check_b_c_children(client, engine, ids)
    check_d_e_room_batch(client, engine, ids)

    for key in ("a", "b", "c", "d", "e"):
        if not COUNTS.get(key):
            fail(f"({key}) vacuous-proof: zero outcomes examined")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: zone_children — "
        f"(a) neighbours route [{COUNTS['a']}], (b) link_to derives types [{COUNTS['b']}], "
        f"(c) bad link_to refused [{COUNTS['c']}], (d) batch asks first [{COUNTS['d']}], "
        f"(e) batch promotes and links [{COUNTS['e']}]"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
