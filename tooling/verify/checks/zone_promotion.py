"""G1 check for TICKET-0101 (BRIEF-0101-C) — a location's first child makes it a zone.

DB-backed, self-contained fresh temp-file SQLite fixture (WORLD_ENGINE_
DATABASE_URL set BEFORE any world_engine import), driven through the real
creator routes with `TestClient(app, base_url="http://127.0.0.1")`
(origin_guard). Zero outcomes in any assertion is a FAIL.

Fixture — the Forêt verte example: F (visitable) linked by `connects_to` to
V; a PC and an NPC at F; the NPC's `matin` schedule at F, its `soir` at V;
an item lying at F; a discoverable detail at F; an open gathering at F
holding the NPC. W, visitable and empty.

Five assertions:
  a. S1: `POST /api/entities` creating E under F without `confirm_promotion`
     is a 409 whose detail is `{"code": "promotion_required", "preview": …}`
     listing the link, both beings, the schedule, the item, the detail and
     the gathering; nothing moved and no E exists. `GET
     /api/locations/{F}/promotion-preview` returns the same lists.
  b. Confirmed: the same POST with `confirm_promotion: true` is a 201; F-V is
     the same relation row, now `borde`, its `change_history` one longer;
     the PC and the NPC are at E; the NPC's `matin` row is at E and its
     `soir` row still at V; the item and the detail are at E; the gathering
     is dissolved.
  c. Silent promotion: creating a child under W (nothing to move) needs no
     confirmation (201) and W is a zone.
  d. Demotion: soft-deleting F's only child makes F visitable again;
     nothing moves and F-V stays `borde`.
  e. Re-parent and reactivation: a `PUT` moving location X under V2 (V2
     holding an NPC) without `confirm_promotion` is a 409 and X keeps its
     parent; reactivating F's deleted child through an AI `status_change`
     with F holding a PC again is refused ("Needs attention"), and through
     `PUT` with `confirm_promotion` it promotes F.
  f. AMENDMENT-0101-01: a confirmed `PUT` moving Y -- itself a zone (child
     Ya) -- under V3, which holds an NPC, is a 409 whose detail is a string
     naming Y as a zone; Y keeps no parent, the NPC stays at V3, nothing is
     retyped; `GET /api/locations/{V3}/promotion-preview?child_id={Y}` says
     `target_is_zone`. The same move under W2 (nothing to move) is a 200.

Named mutations: make `promote_parent` ignore `confirmed` -> (a);
delete the `for being in preview["beings"]` loop of `apply_promotion` ->
(b); require `confirmed` even when `needs_confirmation` is False -> (c); drop `_zone_promotion_refusal` from `status_change` -> (e); delete
the `target_is_zone` refusal in `promote_parent` -> (f).
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

FAILURES: list[str] = []
COUNTS: dict[str, int] = {}
MOVING = ("links", "beings", "schedules", "items", "details", "gatherings")


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


def _location(db, world_id: str, name: str, parent=None) -> str:
    from world_engine.models import Entity, Location

    entity = Entity(world_id=world_id, type="location", name=name)
    db.add(entity)
    db.flush()
    db.add(Location(id=entity.id, parent_location_id=parent))
    db.commit()
    return entity.id


def _character(db, world_id: str, name: str, ctype: str, at: str, user_id=None) -> str:
    from world_engine.models import Character, Entity

    entity = Entity(world_id=world_id, type="character", name=name)
    db.add(entity)
    db.flush()
    db.add(Character(id=entity.id, world_id=world_id, character_type=ctype, user_id=user_id, current_location_id=at))
    db.commit()
    return entity.id


def _seed(db) -> dict[str, str]:
    from world_engine.models import (
        DiscoverableDetail, Entity, Gathering, GatheringMember, Item, ItemHolding, NpcSchedule, Session, User,
        World,
    )
    from world_engine.writes.relations import write_relation

    world = World(name="Aestia check", is_active=True)
    db.add(world)
    db.commit()
    w = world.id
    ids = {"world": w}
    for label in ("F", "V", "W", "V2", "X", "V3", "W2", "Y"):
        ids[label] = _location(db, w, f"Lieu {label}")
    ids["Ya"] = _location(db, w, "Lieu Ya", parent=ids["Y"])
    write_relation(db, mode="set", world_id=w, entity_a_id=ids["F"], entity_b_id=ids["V"],
                   type="connects_to", value=50, direction="mutual")
    db.commit()
    user = User(name="creator", role="creator")
    db.add(user)
    db.commit()
    ids["P"] = _character(db, w, "Millys", "player", ids["F"], user.id)
    ids["N"] = _character(db, w, "Garde", "npc", ids["F"])
    ids["N2"] = _character(db, w, "Veilleur", "npc", ids["V2"])
    ids["N3"] = _character(db, w, "Passeur", "npc", ids["V3"])
    db.add(NpcSchedule(world_id=w, npc_id=ids["N"], phase="matin", location_id=ids["F"]))
    db.add(NpcSchedule(world_id=w, npc_id=ids["N"], phase="soir", location_id=ids["V"]))
    item = Entity(world_id=w, type="item", name="Lanterne")
    db.add(item)
    db.flush()
    db.add(Item(id=item.id))
    db.add(ItemHolding(world_id=w, item_id=item.id, holder_entity_id=ids["F"], quantity=2, change_history=[]))
    detail = DiscoverableDetail(world_id=w, location_id=ids["F"], subject="trace", content="Une trace.")
    db.add(detail)
    sess = Session(world_id=w, number=1)
    db.add(sess)
    db.flush()
    gathering = Gathering(world_id=w, session_id=sess.id, location_id=ids["F"])
    db.add(gathering)
    db.flush()
    db.add(GatheringMember(gathering_id=gathering.id, entity_id=ids["N"]))
    db.commit()
    ids.update(item=item.id, detail=detail.id, gathering=gathering.id)
    return ids


def _body(name: str, parent: str, confirm: bool = False) -> dict:
    body = {"entity": {"name": name, "type": "location", "status": "active"},
            "extension": {"parent_location_id": parent}}
    if confirm:
        body["confirm_promotion"] = True
    return body


def _rel(db, a: str, b: str):
    from sqlmodel import select

    from world_engine.models import Relation

    return db.exec(select(Relation).where(
        ((Relation.entity_a_id == a) & (Relation.entity_b_id == b))
        | ((Relation.entity_a_id == b) & (Relation.entity_b_id == a))
    )).first()


def _where(db, character_id: str):
    from world_engine.models import Character

    return db.get(Character, character_id).current_location_id


def check_a_refused(client, engine, ids) -> None:
    from sqlmodel import Session, select

    from world_engine.models import Entity

    n = 0
    resp = client.post("/api/entities", json=_body("Entrée de la forêt", ids["F"]))
    detail = resp.json().get("detail") if resp.headers.get("content-type", "").startswith("application/json") else None
    if resp.status_code != 409 or not isinstance(detail, dict) or detail.get("code") != "promotion_required":
        fail(f"(a) unconfirmed promotion answered {resp.status_code} {resp.text[:160]}")
        return
    preview = detail["preview"]
    sizes = {key: len(preview[key]) for key in MOVING}
    expected = {"links": 1, "beings": 2, "schedules": 1, "items": 1, "details": 1, "gatherings": 1}
    if sizes != expected:
        fail(f"(a) preview lists {sizes}, expected {expected}")
    n += sum(sizes.values())
    with Session(engine) as db:
        if db.exec(select(Entity).where(Entity.name == "Entrée de la forêt")).first() is not None:
            fail("(a) the refused create left its entity behind")
        if _where(db, ids["P"]) != ids["F"] or _rel(db, ids["F"], ids["V"]).type != "connects_to":
            fail("(a) the refused create moved something")
    got = client.get(f"/api/locations/{ids['F']}/promotion-preview").json()
    if {key: len(got[key]) for key in MOVING} != expected:
        fail("(a) GET promotion-preview disagrees with the 409 preview")
    COUNTS["a"] = n


def check_b_confirmed(client, engine, ids) -> None:
    from sqlmodel import Session, select

    from world_engine.holdings import held_quantity
    from world_engine.models import DiscoverableDetail, Gathering, NpcSchedule

    with Session(engine) as db:
        rel = _rel(db, ids["F"], ids["V"])
        rel_id, history = rel.id, len(rel.change_history or [])
    resp = client.post("/api/entities", json=_body("Entrée de la forêt", ids["F"], confirm=True))
    if resp.status_code != 201:
        fail(f"(b) confirmed promotion answered {resp.status_code} {resp.text[:160]}")
        return
    child = resp.json()["id"]
    ids["E"] = child
    n = 0
    with Session(engine) as db:
        rel = _rel(db, ids["F"], ids["V"])
        n += _expect(rel.id == rel_id and rel.type == "borde" and len(rel.change_history) == history + 1,
                     f"(b) F-V after promotion: id kept={rel.id == rel_id}, type={rel.type!r}")
        for being in ("P", "N"):
            n += _expect(_where(db, ids[being]) == child, f"(b) {being} not moved to the first child")
        rows = {r.phase: r.location_id for r in db.exec(select(NpcSchedule).where(NpcSchedule.npc_id == ids["N"])).all()}
        n += _expect(rows == {"matin": child, "soir": ids["V"]}, f"(b) schedule after promotion: {rows}")
        n += _expect(held_quantity(db, child, ids["item"]) == 2 and held_quantity(db, ids["F"], ids["item"]) == 0,
                     "(b) the place's two items not moved to the first child")
        n += _expect(db.get(DiscoverableDetail, ids["detail"]).location_id == child, "(b) detail not moved")
        n += _expect(db.get(Gathering, ids["gathering"]).status == "dissolved", "(b) gathering left open")
    COUNTS["b"] = n


def _expect(ok: bool, msg: str) -> int:
    if not ok:
        fail(msg)
        return 0
    return 1


def check_c_silent(client, engine, ids) -> None:
    from sqlmodel import Session

    from world_engine.zone_rules import is_zone

    resp = client.post("/api/entities", json=_body("Coin de W", ids["W"]))
    with Session(engine) as db:
        COUNTS["c"] = _expect(resp.status_code == 201 and is_zone(db, ids["W"]),
                              f"(c) silent promotion answered {resp.status_code}")


def check_d_demotion(client, engine, ids) -> None:
    from sqlmodel import Session

    from world_engine.zone_rules import is_zone

    resp = client.post(f"/api/entities/{ids['E']}/delete")
    with Session(engine) as db:
        n = _expect(resp.status_code == 200 and not is_zone(db, ids["F"]), "(d) F still a zone without children")
        n += _expect(_rel(db, ids["F"], ids["V"]).type == "borde", "(d) F-V changed on demotion")
        n += _expect(_where(db, ids["P"]) == ids["E"], "(d) demotion moved the PC")
    COUNTS["d"] = n


def check_e_update_paths(client, engine, ids) -> None:
    from sqlmodel import Session

    from world_engine.cockpit.mutations import _mutation_apply_status_change
    from world_engine.models import Character, Location
    from world_engine.zone_rules import is_zone

    n = 0
    body = {"entity": {"name": "Lieu X", "type": "location", "status": "active"},
            "extension": {"parent_location_id": ids["V2"]}}
    resp = client.put(f"/api/entities/{ids['X']}", json=body)
    with Session(engine) as db:
        n += _expect(resp.status_code == 409 and db.get(Location, ids["X"]).parent_location_id is None,
                     f"(e) unconfirmed re-parent answered {resp.status_code}")
    with Session(engine) as db:
        db.get(Character, ids["P"]).current_location_id = ids["F"]
        db.commit()
        mut = SimpleNamespace(id="m", world_id=ids["world"], target_id=None)
        message = _mutation_apply_status_change(mut, {"entity_id": ids["E"], "status": "active"}, db)
        db.rollback()
        n += _expect(bool(message), "(e) an AI status_change promoted F without the dialog")
    body = {"entity": {"name": "Entrée de la forêt", "type": "location", "status": "active"},
            "extension": {"parent_location_id": ids["F"]}, "confirm_promotion": True}
    resp = client.put(f"/api/entities/{ids['E']}", json=body)
    with Session(engine) as db:
        n += _expect(resp.status_code == 200 and is_zone(db, ids["F"]) and _where(db, ids["P"]) == ids["E"],
                     f"(e) confirmed reactivation answered {resp.status_code}")
    COUNTS["e"] = n


def check_f_target_is_zone(client, engine, ids) -> None:
    from sqlmodel import Session

    from world_engine.models import Location

    body = {"entity": {"name": "Lieu Y", "type": "location", "status": "active"},
            "extension": {"parent_location_id": ids["V3"]}, "confirm_promotion": True}
    resp = client.put(f"/api/entities/{ids['Y']}", json=body)
    detail = resp.json().get("detail")
    n = _expect(resp.status_code == 409 and isinstance(detail, str) and "Lieu Y" in detail and "zone" in detail,
                f"(f) re-parenting a zone under an inhabited place answered {resp.status_code} {resp.text[:160]}")
    with Session(engine) as db:
        n += _expect(db.get(Location, ids["Y"]).parent_location_id is None, "(f) Y was re-parented")
        n += _expect(_where(db, ids["N3"]) == ids["V3"], "(f) the NPC left V3")
    got = client.get(f"/api/locations/{ids['V3']}/promotion-preview?child_id={ids['Y']}").json()
    n += _expect(got.get("target_is_zone") is True and got.get("needs_confirmation") is True,
                 f"(f) preview flags: {got.get('target_is_zone')}, {got.get('needs_confirmation')}")
    body["extension"]["parent_location_id"] = ids["W2"]
    resp = client.put(f"/api/entities/{ids['Y']}", json=body)
    n += _expect(resp.status_code == 200, f"(f) re-parenting a zone under an empty place answered {resp.status_code}")
    COUNTS["f"] = n


def main() -> int:
    engine = _fresh_engine()
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from world_engine.cockpit.app import app

    with Session(engine) as db:
        ids = _seed(db)
    client = TestClient(app, base_url="http://127.0.0.1")
    check_a_refused(client, engine, ids)
    check_b_confirmed(client, engine, ids)
    if "E" in ids:
        check_c_silent(client, engine, ids)
        check_d_demotion(client, engine, ids)
        check_e_update_paths(client, engine, ids)
        check_f_target_is_zone(client, engine, ids)

    for key in ("a", "b", "c", "d", "e", "f"):
        if not COUNTS.get(key):
            fail(f"({key}) vacuous-proof: zero outcomes examined")

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: zone_promotion — "
        f"(a) S1 refusal + preview [{COUNTS['a']} rows], (b) K applied [{COUNTS['b']}], "
        f"(c) silent promotion [{COUNTS['c']}], (d) demotion moves nothing [{COUNTS['d']}], "
        f"(e) re-parent / reactivation [{COUNTS['e']}], (f) a zone child receives nothing [{COUNTS['f']}]"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
