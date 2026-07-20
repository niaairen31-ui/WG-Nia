"""G1 check for TICKET-0034 (BRIEF-0034-c) — `POST /api/spatial/travel`,
the door-gated in-fiction travel endpoint.

On the `scene_join_target.py` shape: fresh temp-file SQLite
(WORLD_ENGINE_DATABASE_URL set BEFORE any world_engine import), TestClient,
hard asserts, one summary PASS line. No Ollama, no monkeypatch needed — this
path makes zero model calls.

Fixture: one world, one player character in location A. A and B both
spatial (bounds 40x30), an active mutual connects_to relation between them,
A's door toward B at (2, 15), B's door toward A at (38, 15). A third
location C has NO connects_to edge to A; a door row A -> C is forced in
directly (bypassing write_location_doors, which would reject it) — this
proves the READ filter (spatial_doors.location_doors) is load-bearing on
its own, not merely a second opinion on the write gate.

Cases:
1. Unknown door_id -> 404, zero rows written.
2. Door whose location_id is B while the player is in A -> 409.
3. Door A -> C (no connects_to edge) -> 409 — the hard guarantee under
   test: a real door row, in the player's real location, from a legitimate
   position, refused because the map does not link A to C.
4. Same as 3 after creating the A -> C connects_to relation -> 200, player
   in C. Then (repositioned back to A, test-only) delete the relation and
   retry -> 409: the filter is live state, not a snapshot.
5. Target soft-deleted (entity.status = 'archived') -> 409.
6. Out-of-range position -> 409 "out of door range"; in-range -> 200.
7. Happy path: current_location_id == B, origin_location_id == A.
8. Regression: POST /api/travel (creator god-mode) still returns
   status/location_id and now also origin_location_id.

Also asserts, AST-side: routes/play.py's spatial_travel contains no
`math.` call and no import of routes.spatial.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys
import tempfile
from datetime import UTC, datetime

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
PLAY_ROUTES_FILE = SRC / "world_engine" / "cockpit" / "routes" / "play.py"

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


def _seed_fixture(engine):
    from sqlmodel import Session as DbSession

    from world_engine.models import Character, Door, Entity, Location, Relation, World

    with DbSession(engine) as session:
        world = World(name="Check World", is_active=True)
        session.add(world)
        session.commit()
        session.refresh(world)

        def _spatial_location(name: str) -> str:
            entity = Entity(world_id=world.id, type="location", name=name)
            session.add(entity)
            session.commit()
            session.refresh(entity)
            session.add(Location(id=entity.id, bounds_width=40.0, bounds_height=30.0))
            session.commit()
            return entity.id

        loc_a = _spatial_location("A")
        loc_b = _spatial_location("B")
        loc_c = _spatial_location("C")

        player_entity = Entity(world_id=world.id, type="character", name="Player")
        session.add(player_entity)
        session.commit()
        session.refresh(player_entity)
        session.add(Character(
            id=player_entity.id, world_id=world.id, character_type="player",
            user_id="check-user", current_location_id=loc_a,
        ))
        session.commit()

        rel_ab = Relation(world_id=world.id, entity_a_id=loc_a, entity_b_id=loc_b, type="connects_to")
        session.add(rel_ab)
        session.commit()
        session.refresh(rel_ab)

        door_ab = Door(world_id=world.id, location_id=loc_a, target_location_id=loc_b, x=2.0, y=15.0)
        door_ba = Door(world_id=world.id, location_id=loc_b, target_location_id=loc_a, x=38.0, y=15.0)
        session.add(door_ab)
        session.add(door_ba)
        session.commit()
        session.refresh(door_ab)
        session.refresh(door_ba)

        # A -> C door forced in directly: no connects_to edge exists between
        # A and C, and write_location_doors would reject this target. This
        # is the fixture that proves the read filter is load-bearing on its
        # own.
        door_ac = Door(world_id=world.id, location_id=loc_a, target_location_id=loc_c, x=5.0, y=5.0)
        session.add(door_ac)
        session.commit()
        session.refresh(door_ac)

        return {
            "world_id": world.id,
            "player_id": player_entity.id,
            "loc_a": loc_a,
            "loc_b": loc_b,
            "loc_c": loc_c,
            "rel_ab_id": rel_ab.id,
            "door_ab_id": door_ab.id,
            "door_ba_id": door_ba.id,
            "door_ac_id": door_ac.id,
        }


def _count_rows(engine, model) -> int:
    from sqlmodel import Session as DbSession, select
    with DbSession(engine) as session:
        return len(session.exec(select(model)).all())


def _current_location(engine, character_id: str):
    from sqlmodel import Session as DbSession

    from world_engine.models import Character

    with DbSession(engine) as session:
        return session.get(Character, character_id).current_location_id


def check_travel_endpoint() -> None:
    engine = _fresh_engine()
    fx = _seed_fixture(engine)

    from fastapi.testclient import TestClient
    from sqlmodel import Session as DbSession

    from world_engine.cockpit.app import app
    from world_engine.models import Conversation, Entity, GatheringMember, Relation

    client = TestClient(app)

    def _rows():
        return _count_rows(engine, Conversation), _count_rows(engine, GatheringMember)

    # ── 1. Unknown door_id -> 404, zero rows written ────────────────────
    before = _rows()
    resp = client.post("/api/spatial/travel", json={
        "door_id": "nonexistent-door", "position": {"x": 2.5, "y": 15.0},
        "player_id": fx["player_id"],
    })
    if resp.status_code != 404:
        fail(f"unknown door_id: expected 404, got {resp.status_code}: {resp.text}")
    if _rows() != before or _current_location(engine, fx["player_id"]) != fx["loc_a"]:
        fail("unknown door_id: state changed despite rejection")

    # ── 2. Door in another location than the player's current one -> 409 ─
    before = _rows()
    resp = client.post("/api/spatial/travel", json={
        "door_id": fx["door_ba_id"], "position": {"x": 38.0, "y": 15.0},
        "player_id": fx["player_id"],
    })
    if resp.status_code != 409:
        fail(f"door in wrong location: expected 409, got {resp.status_code}: {resp.text}")
    if _rows() != before or _current_location(engine, fx["player_id"]) != fx["loc_a"]:
        fail("door in wrong location: state changed despite rejection")

    # ── 3. Door A -> C, no connects_to edge -> 409 (the hard guarantee) ──
    before = _rows()
    resp = client.post("/api/spatial/travel", json={
        "door_id": fx["door_ac_id"], "position": {"x": 5.2, "y": 5.0},
        "player_id": fx["player_id"],
    })
    if resp.status_code != 409:
        fail(f"door A->C with no connects_to edge: expected 409, got {resp.status_code}: {resp.text}")
    if _rows() != before or _current_location(engine, fx["player_id"]) != fx["loc_a"]:
        fail("door A->C with no connects_to edge: state changed despite rejection")

    # ── 4. Create A -> C connects_to -> 200; then delete it and retry ────
    with DbSession(engine) as session:
        rel_ac = Relation(world_id=fx["world_id"], entity_a_id=fx["loc_a"], entity_b_id=fx["loc_c"], type="connects_to")
        session.add(rel_ac)
        session.commit()
        session.refresh(rel_ac)
        rel_ac_id = rel_ac.id

    resp = client.post("/api/spatial/travel", json={
        "door_id": fx["door_ac_id"], "position": {"x": 5.2, "y": 5.0},
        "player_id": fx["player_id"],
    })
    if resp.status_code != 200:
        fail(f"door A->C with live connects_to: expected 200, got {resp.status_code}: {resp.text}")
    else:
        body = resp.json()
        if body.get("location_id") != fx["loc_c"] or body.get("origin_location_id") != fx["loc_a"]:
            fail(f"door A->C with live connects_to: unexpected response shape: {body}")
    if _current_location(engine, fx["player_id"]) != fx["loc_c"]:
        fail("door A->C with live connects_to: player not moved to C")

    # Repositioned back to A (test-only, direct DB write — not exercising
    # any travel path) so the relation deletion can be re-tested from A.
    with DbSession(engine) as session:
        from world_engine.models import Character
        char = session.get(Character, fx["player_id"])
        char.current_location_id = fx["loc_a"]
        session.add(char)
        session.commit()

        rel = session.get(Relation, rel_ac_id)
        session.delete(rel)
        session.commit()

    before = _rows()
    resp = client.post("/api/spatial/travel", json={
        "door_id": fx["door_ac_id"], "position": {"x": 5.2, "y": 5.0},
        "player_id": fx["player_id"],
    })
    if resp.status_code != 409:
        fail(f"door A->C after relation deleted: expected 409, got {resp.status_code}: {resp.text}")
    if _rows() != before or _current_location(engine, fx["player_id"]) != fx["loc_a"]:
        fail("door A->C after relation deleted: state changed despite rejection (filter is not live)")

    # ── 5. Target soft-deleted -> 409 ────────────────────────────────────
    with DbSession(engine) as session:
        loc_b_entity = session.get(Entity, fx["loc_b"])
        loc_b_entity.status = "archived"
        session.add(loc_b_entity)
        session.commit()

    before = _rows()
    resp = client.post("/api/spatial/travel", json={
        "door_id": fx["door_ab_id"], "position": {"x": 2.5, "y": 15.0},
        "player_id": fx["player_id"],
    })
    if resp.status_code != 409:
        fail(f"target soft-deleted: expected 409, got {resp.status_code}: {resp.text}")
    if _rows() != before or _current_location(engine, fx["player_id"]) != fx["loc_a"]:
        fail("target soft-deleted: state changed despite rejection")

    with DbSession(engine) as session:
        loc_b_entity = session.get(Entity, fx["loc_b"])
        loc_b_entity.status = "active"
        session.add(loc_b_entity)
        session.commit()

    # ── 6. Out-of-range vs in-range position ─────────────────────────────
    before = _rows()
    resp = client.post("/api/spatial/travel", json={
        "door_id": fx["door_ab_id"], "position": {"x": 10.0, "y": 15.0},
        "player_id": fx["player_id"],
    })
    if resp.status_code != 409:
        fail(f"out of door range: expected 409, got {resp.status_code}: {resp.text}")
    if _rows() != before or _current_location(engine, fx["player_id"]) != fx["loc_a"]:
        fail("out of door range: state changed despite rejection")

    # ── 7. Happy path ─────────────────────────────────────────────────
    resp = client.post("/api/spatial/travel", json={
        "door_id": fx["door_ab_id"], "position": {"x": 2.5, "y": 15.0},
        "player_id": fx["player_id"],
    })
    if resp.status_code != 200:
        fail(f"happy path: expected 200, got {resp.status_code}: {resp.text}")
    else:
        body = resp.json()
        if body.get("status") != "ok" or body.get("location_id") != fx["loc_b"] or body.get("origin_location_id") != fx["loc_a"]:
            fail(f"happy path: unexpected response shape: {body}")
    if _current_location(engine, fx["player_id"]) != fx["loc_b"]:
        fail("happy path: character.current_location_id not moved to B")

    # ── 8. Regression: creator travel route carries origin_location_id ──
    resp = client.post(
        "/api/travel",
        json={"location_id": fx["loc_a"]},
        params={"player_id": fx["player_id"]},
    )
    if resp.status_code != 200:
        fail(f"creator travel regression: expected 200, got {resp.status_code}: {resp.text}")
    else:
        body = resp.json()
        if body.get("status") != "ok" or body.get("location_id") != fx["loc_a"] or body.get("origin_location_id") != fx["loc_b"]:
            fail(f"creator travel regression: unexpected response shape: {body}")


def check_spatial_travel_source() -> None:
    """AST-side: spatial_travel() calls no math.* and imports nothing from
    routes.spatial (K1's seam — a routes -> routes import is exactly what
    it exists to prevent)."""
    if not PLAY_ROUTES_FILE.exists():
        fail(f"{PLAY_ROUTES_FILE} does not exist")
        return

    try:
        tree = ast.parse(PLAY_ROUTES_FILE.read_text(encoding="utf-8"), filename=str(PLAY_ROUTES_FILE))
    except SyntaxError as exc:
        fail(f"{PLAY_ROUTES_FILE}: SyntaxError: {exc}")
        return

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and "routes.spatial" in node.module:
            fail(f"{PLAY_ROUTES_FILE}:{node.lineno} — imports from routes.spatial (K1 forbids a routes -> routes import)")

    func_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "spatial_travel":
            func_node = node
            break
    if func_node is None:
        fail(f"{PLAY_ROUTES_FILE}: spatial_travel() not found")
        return

    for node in ast.walk(func_node):
        if isinstance(node, ast.Attribute) and node.attr in ("hypot", "sqrt"):
            if isinstance(node.value, ast.Name) and node.value.id == "math":
                fail(f"{PLAY_ROUTES_FILE}:{node.lineno} — spatial_travel calls math.{node.attr}; distance must go through placement.distance")


def main() -> int:
    check_travel_endpoint()
    check_spatial_travel_source()

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: spatial_door_travel — POST /api/spatial/travel gates on "
        "unknown door / wrong location / dead connects_to edge / archived "
        "target / out-of-range position, happy path moves the player and "
        "returns origin_location_id, creator travel regression holds"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
