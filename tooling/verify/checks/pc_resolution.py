"""G1 check for TICKET-0128 (BRIEF-0128-B; first written for TICKET-0125) -- one resolver gives the cockpit its player character; several and none chosen is a refusal.

INV-70's enforcing check.

PR1 -- `active_pc.resolve_active_pc` walks the lot's case table (b) row by
   row on one world (users Ana and Bea, PCs Pia and Quentin, an inactive PC
   Rose): 0 PCs -> `NoPlayerCharacter(NO_PC_MESSAGE)`; 1 PC with
   `active_pc_id` NULL, the PC, or the inactive PC -> that PC; 2 PCs with
   NULL -> `ActivePcUnchosen(CHOOSE_PC_MESSAGE)`, with Pia -> Pia, with the
   inactive PC -> `ActivePcUnchosen`; an unknown world id -> as if NULL.
   `active_pc_id_or_none` answers the id or None on every row;
   `world_player_characters` lists the active PCs only, by name.
PR2 -- static. No function named `_resolve_player_character`,
   `_resolve_player_id` or `_player_character_id` is defined under
   `src/world_engine`, except `_player_character_id` in
   `cockpit/crud/_shared.py`; `routes/quests.py` and `routes/debts.py`
   import nothing from `.day`; `active_pc.py` makes no `.first()` call and
   imports no `fastapi`.
PR3 -- the adapters. `_crud._player_character` raises 400 `NO_PC_MESSAGE`
   with no PC, 409 `CHOOSE_PC_MESSAGE` with two and none chosen, returns the
   chosen one; `_crud._player_character_id` returns its id.
PR4 -- routes, `TestClient(app, base_url="http://127.0.0.1")` on the active
   world. `GET /api/active-pc` with two PCs and none chosen -> exactly
   C-06's keys, `active_pc_id` None, `chosen` false, both characters by
   name; `PUT` Quentin -> 200, `active_pc_id` Quentin, `chosen` true; `PUT`
   an NPC, another world's PC, the inactive Rose and an unknown id -> 422
   `ACTIVE_PC_REFUSED`, the column unchanged; `PUT` null -> 200, `chosen`
   false; `GET /api/bootstrap` answers Quentin's id when chosen, None when
   not.
PR5 -- deletion. With Quentin chosen, `POST /api/entities/{Quentin}/delete`
   -> 200 and `world.active_pc_id` NULL; `write_active_pc` and
   `clear_active_pc_of` never commit (a rollback after each leaves the row
   unchanged).

A row not reached is a FAILURE. Fresh temp-file SQLite database
(`WORLD_ENGINE_DATABASE_URL` set before any world_engine import) -- never
Nia's DB.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
PACKAGE = SRC / "world_engine"
SHARED = PACKAGE / "cockpit" / "crud" / "_shared.py"
ACTIVE_PC = PACKAGE / "active_pc.py"
ROUTES = PACKAGE / "cockpit" / "routes"
GONE = {"_resolve_player_character", "_resolve_player_id", "_player_character_id"}

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{pathlib.Path(tmp_dir) / 'check.db'}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]
    from sqlmodel import SQLModel

    import world_engine.models  # noqa: F401 -- registers every table
    from world_engine.db import engine

    SQLModel.metadata.create_all(engine)
    return engine


def _add_character(db, world_id: str, user_id: str | None, name: str, *,
                   character_type: str = "player", status: str = "active") -> str:
    from world_engine.models import Character, Entity

    entity = Entity(world_id=world_id, type="character", name=name, status=status)
    db.add(entity)
    db.flush()
    db.add(Character(id=entity.id, world_id=world_id, character_type=character_type, user_id=user_id))
    db.commit()
    return entity.id


def _set_choice(db, world_id: str, character_id: str | None) -> None:
    from world_engine.models import World

    world = db.get(World, world_id)
    world.active_pc_id = character_id
    db.add(world)
    db.commit()


def _choice(db, world_id: str) -> str | None:
    from world_engine.models import World

    db.rollback()  # end any read transaction: see what the routes committed
    value = db.get(World, world_id).active_pc_id
    db.rollback()
    return value


# --- PR1 ---------------------------------------------------------------------
def _expect_row(row: str, db, world_id: str, expected) -> None:
    """`expected` is a character id or an exception class."""
    from world_engine import active_pc

    try:
        got = active_pc.resolve_active_pc(db, world_id).id
    except (active_pc.NoPlayerCharacter, active_pc.ActivePcUnchosen) as exc:
        message = {active_pc.NoPlayerCharacter: active_pc.NO_PC_MESSAGE,
                   active_pc.ActivePcUnchosen: active_pc.CHOOSE_PC_MESSAGE}[type(exc)]
        if not (isinstance(expected, type) and type(exc) is expected and str(exc) == message):
            fail(f"PR1 {row}: expected {expected!r}, got {type(exc).__name__}({exc})")
    else:
        if got != expected:
            fail(f"PR1 {row}: expected {expected!r}, got {got!r}")
    or_none = active_pc.active_pc_id_or_none(db, world_id)
    if or_none != (None if isinstance(expected, type) else expected):
        fail(f"PR1 {row}: active_pc_id_or_none answered {or_none!r}")


def rule_pr1(db, ids: dict) -> int:
    from world_engine import active_pc

    w = ids["world"]
    reached = 0
    _expect_row("0 PCs", db, w, active_pc.NoPlayerCharacter)
    reached += 1

    ids["pia"] = _add_character(db, w, ids["ana"], "Pia")
    ids["rose"] = _add_character(db, w, None, "Rose", status="inactive")
    for label, choice in (("NULL", None), ("P", ids["pia"]), ("an inactive PC", ids["rose"])):
        _set_choice(db, w, choice)
        _expect_row(f"1 PC, active_pc_id {label}", db, w, ids["pia"])
        reached += 1

    ids["quentin"] = _add_character(db, w, ids["bea"], "Quentin")
    for label, choice, expected in (("NULL", None, active_pc.ActivePcUnchosen),
                                    ("P", ids["pia"], ids["pia"]),
                                    ("an inactive PC", ids["rose"], active_pc.ActivePcUnchosen)):
        _set_choice(db, w, choice)
        _expect_row(f"2 PCs, active_pc_id {label}", db, w, expected)
        reached += 1

    _set_choice(db, w, None)
    _expect_row("an unknown world", db, "no-such-world", active_pc.NoPlayerCharacter)
    reached += 1

    listed = [(c.id, name) for c, name in active_pc.world_player_characters(db, w)]
    if listed != [(ids["pia"], "Pia"), (ids["quentin"], "Quentin")]:
        fail(f"PR1 world_player_characters lists {listed!r}, expected Pia then Quentin (active only)")
    return reached + 1


# --- PR2 ---------------------------------------------------------------------
def rule_pr2() -> int:
    reached = 0
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in GONE:
                if not (path == SHARED and node.name == "_player_character_id"):
                    fail(f"PR2 {node.name} is defined in {path.relative_to(ROOT)}:{node.lineno}")
        reached += 1
    for name in ("quests.py", "debts.py"):
        tree = ast.parse((ROUTES / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module == "day":
                fail(f"PR2 routes/{name} imports from .day (line {node.lineno})")
    if not ACTIVE_PC.exists():
        fail("PR2 active_pc.py is missing")
        return 0
    tree = ast.parse(ACTIVE_PC.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "first":
            fail(f"PR2 active_pc.py calls .first() (line {node.lineno})")
        if isinstance(node, ast.Import) and any(a.name.split(".")[0] == "fastapi" for a in node.names):
            fail("PR2 active_pc.py imports fastapi")
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "fastapi":
            fail("PR2 active_pc.py imports fastapi")
    return reached


# --- PR3 ---------------------------------------------------------------------
def _expect_http(label: str, call, status: int, detail: str) -> None:
    from fastapi import HTTPException

    try:
        got = call()
    except HTTPException as exc:
        if exc.status_code != status or exc.detail != detail:
            fail(f"PR3 {label}: expected {status} {detail!r}, got {exc.status_code} {exc.detail!r}")
        return
    fail(f"PR3 {label}: expected {status} {detail!r}, got {got!r}")


def rule_pr3(db, ids: dict) -> int:
    from world_engine.active_pc import CHOOSE_PC_MESSAGE, NO_PC_MESSAGE
    from world_engine.cockpit import crud as _crud

    _expect_http("no PC", lambda: _crud._player_character(db, ids["empty_world"]), 400, NO_PC_MESSAGE)
    _set_choice(db, ids["world"], None)
    _expect_http("two PCs, none chosen", lambda: _crud._player_character(db, ids["world"]),
                 409, CHOOSE_PC_MESSAGE)
    _set_choice(db, ids["world"], ids["quentin"])
    if _crud._player_character(db, ids["world"]).id != ids["quentin"]:
        fail("PR3 _player_character does not return the chosen PC")
    if _crud._player_character_id(db, ids["world"]) != ids["quentin"]:
        fail("PR3 _player_character_id does not return the chosen PC's id")
    _set_choice(db, ids["world"], None)
    return 3


# --- PR4 ---------------------------------------------------------------------
def rule_pr4(client, db, ids: dict) -> int:
    from world_engine.writes.active_pc import ACTIVE_PC_REFUSED

    reached = 0
    body = client.get("/api/active-pc").json()
    keys = {"world_id", "active_pc_id", "chosen", "characters"}
    expected_chars = [{"id": ids["pia"], "name": "Pia"}, {"id": ids["quentin"], "name": "Quentin"}]
    if set(body) != keys or body["active_pc_id"] is not None or body["chosen"] is not False \
            or body["characters"] != expected_chars or body["world_id"] != ids["world"]:
        fail(f"PR4 GET with two PCs and none chosen answered {body!r}")
    if client.get("/api/bootstrap").json().get("player_id") is not None:
        fail("PR4 /api/bootstrap answers a player_id with none chosen")
    reached += 1

    resp = client.put("/api/active-pc", json={"character_id": ids["quentin"]})
    if resp.status_code != 200 or resp.json().get("active_pc_id") != ids["quentin"] \
            or resp.json().get("chosen") is not True:
        fail(f"PR4 PUT Quentin answered {resp.status_code} {resp.text[:200]}")
    if client.get("/api/bootstrap").json().get("player_id") != ids["quentin"]:
        fail("PR4 /api/bootstrap does not answer the chosen PC")
    reached += 1

    for label, character_id in (("an NPC", ids["npc"]), ("another world's PC", ids["foreign_pc"]),
                                ("the inactive Rose", ids["rose"]), ("an unknown id", "no-such-id")):
        resp = client.put("/api/active-pc", json={"character_id": character_id})
        if resp.status_code != 422 or resp.json().get("detail") != ACTIVE_PC_REFUSED:
            fail(f"PR4 PUT {label} answered {resp.status_code} {resp.text[:200]}")
        if _choice(db, ids["world"]) != ids["quentin"]:
            fail(f"PR4 PUT {label} changed the column")
        reached += 1

    resp = client.put("/api/active-pc", json={"character_id": None})
    if resp.status_code != 200 or resp.json().get("chosen") is not False \
            or resp.json().get("active_pc_id") is not None:
        fail(f"PR4 PUT null answered {resp.status_code} {resp.text[:200]}")
    if client.get("/api/bootstrap").json().get("player_id") is not None:
        fail("PR4 /api/bootstrap answers a player_id after the choice was cleared")
    return reached + 1


# --- PR5 ---------------------------------------------------------------------
def rule_pr5(client, db, ids: dict) -> int:
    from world_engine.models import World
    from world_engine.writes.active_pc import clear_active_pc_of, write_active_pc

    reached = 0
    _set_choice(db, ids["world"], ids["quentin"])
    world: World = db.get(World, ids["world"])
    write_active_pc(db, world=world, character_id=ids["pia"])
    db.rollback()
    if _choice(db, ids["world"]) != ids["quentin"]:
        fail("PR5 write_active_pc committed (a rollback did not undo it)")
    reached += 1
    if clear_active_pc_of(db, character_id=ids["quentin"]) != 1:
        fail("PR5 clear_active_pc_of did not count the one world that chose Quentin")
    db.rollback()
    if _choice(db, ids["world"]) != ids["quentin"]:
        fail("PR5 clear_active_pc_of committed (a rollback did not undo it)")
    reached += 1

    resp = client.post(f"/api/entities/{ids['quentin']}/delete")
    if resp.status_code != 200:
        fail(f"PR5 deleting Quentin answered {resp.status_code} {resp.text[:200]}")
    if _choice(db, ids["world"]) is not None:
        fail("PR5 world.active_pc_id still names the deleted Quentin")
    return reached + 1


def _fixture(db) -> dict:
    from world_engine.models import User, World

    world = World(name="W", is_active=True)
    other = World(name="Autre", is_active=False)
    empty = World(name="Vide", is_active=False)
    ana = User(name="Ana", role="player")
    bea = User(name="Bea", role="player")
    db.add_all([world, other, empty, ana, bea])
    db.commit()
    return {"world": world.id, "other_world": other.id, "empty_world": empty.id,
            "ana": ana.id, "bea": bea.id}


def main() -> int:
    engine = _fresh_engine()
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from world_engine.cockpit.app import app

    if rule_pr2() == 0:
        fail("PR2 scanned nothing")
    expected = {"PR1": 9, "PR3": 3, "PR4": 7, "PR5": 3}
    reached: dict[str, int] = {}
    try:
        with Session(engine) as db:
            ids = _fixture(db)
            reached["PR1"] = rule_pr1(db, ids)
            reached["PR3"] = rule_pr3(db, ids)
            ids["npc"] = _add_character(db, ids["world"], None, "Garde", character_type="npc")
            ids["foreign_pc"] = _add_character(db, ids["other_world"], ids["ana"], "Sola")
            client = TestClient(app, base_url="http://127.0.0.1")
            reached["PR4"] = rule_pr4(client, db, ids)
            reached["PR5"] = rule_pr5(client, db, ids)
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"raised {type(exc).__name__}: {exc}")
    for rule, count in expected.items():
        if reached.get(rule, 0) != count:
            fail(f"{rule} reached {reached.get(rule, 0)} of its {count} rows")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: pc_resolution -- PR1-PR5: one resolver walks the case table; no former resolver "
          "survives; the adapters answer 400 / 409 / the chosen PC; the active-PC routes refuse a "
          "foreign id with 422; deleting the active PC clears the choice; the writers never commit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
