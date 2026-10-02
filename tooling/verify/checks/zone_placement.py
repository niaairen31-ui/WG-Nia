"""G1 check for TICKET-0101 (BRIEF-0101-B) — nothing is placed in a zone.

DB-backed, self-contained fresh temp-file SQLite fixture (WORLD_ENGINE_
DATABASE_URL set BEFORE any world_engine import), plus one stdlib-`ast`
walk of `src/`. Every path is driven through its REAL function. Zero
outcomes in any assertion is a FAIL, never a vacuous pass.

Fixture: zone Z with active child C (visitable), visitable V; a player P at
V; an NPC N at V; a creator user.

Three assertions:
  a. Each placement path refuses Z and accepts C, and a refusal writes
     nothing:
       travel            `play_stream._perform_travel`  -> `zone_destination`
       npc_move          `mutations._mutation_apply_npc_move` -> message
       PC creation       `routes/creator._validate_pc_creation` -> 409
       fiche, character  `crud/entities._build_extension_kwargs` -> 409
       fiche, item       `crud/entities._build_extension_kwargs` -> 409
       schedule          `writes/config.write_npc_schedule` -> `ValueError`
       detail            `crud/locations.create_discoverable_detail` -> 409
     A fiche save whose `current_location_id` is UNCHANGED and already Z is
     accepted (existing data is reported, never re-judged).
  b. The NPC batch vocabulary (`npc_group_author.resolve_vocabulary`) rooted
     on Z offers C and not Z.
  c. P1's reactivation condition, structurally: the sites that assign
     `character.current_location_id` (an attribute assignment, or a
     `Character(...)` keyword) are exactly `writes/characters.py::
     write_character_location`, `cockpit/play_stream.py::_perform_travel`
     and `cockpit/routes/creator.py::create_player_character`. A seventh
     site fails here; the registry field path (`crud/entities.py`) is held
     by (a).

Named mutations: delete the `require_visitable` call in `_perform_travel`
-> (a) travel; delete `_require_placement_visitable(...)` in
`_build_extension_kwargs` -> (a) fiche; drop the `is_zone` filter in
`resolve_vocabulary` -> (b); add `char.current_location_id = x` to any other
function -> (c).
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys
import tempfile
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

FAILURES: list[str] = []
COUNTS: dict[str, int] = {}

KNOWN_LOCATION_WRITERS = {
    "world_engine/writes/characters.py::write_character_location",
    "world_engine/cockpit/play_stream.py::_perform_travel",
    "world_engine/cockpit/routes/creator.py::create_player_character",
}


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


def _seed(session) -> dict[str, str]:
    from world_engine.models import Character, Entity, Location, User, World

    world = World(name="Zone Placement", is_active=True)
    session.add(world)
    session.commit()
    ids = {"world": world.id}
    for label, parent in (("Z", None), ("C", "Z"), ("V", None)):
        entity = Entity(world_id=world.id, type="location", name=f"Lieu {label}")
        session.add(entity)
        session.flush()
        session.add(Location(id=entity.id, parent_location_id=ids.get(parent) if parent else None))
        session.commit()
        ids[label] = entity.id
    user = User(name="creator", role="creator")
    session.add(user)
    session.commit()
    for label, ctype in (("P", "player"), ("N", "npc")):
        entity = Entity(world_id=world.id, type="character", name=f"Être {label}")
        session.add(entity)
        session.flush()
        session.add(Character(
            id=entity.id, world_id=world.id, character_type=ctype,
            user_id=user.id if ctype == "player" else None, current_location_id=ids["V"],
        ))
        session.commit()
        ids[label] = entity.id
    return ids


def _location_of(session, character_id: str) -> str:
    from world_engine.models import Character

    session.expire_all()
    return session.get(Character, character_id).current_location_id


def _expect_http(label: str, fn, code: int = 409) -> int:
    from fastapi import HTTPException

    try:
        fn()
    except HTTPException as exc:
        if exc.status_code != code:
            fail(f"(a) {label}: HTTP {exc.status_code}, expected {code}")
        return 1
    fail(f"(a) {label}: a zone was accepted")
    return 0


def _accepts(label: str, fn) -> int:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 -- any refusal of a visitable place is the failure
        fail(f"(a) {label}: a visitable location was refused ({exc})")
        return 0
    return 1


def check_a_paths(session, ids) -> None:
    from world_engine.cockpit.crud.entities import _build_extension_kwargs
    from world_engine.cockpit.crud.locations import DiscoverableDetailBody, create_discoverable_detail
    from world_engine.cockpit.mutations import _mutation_apply_npc_move
    from world_engine.cockpit.play_stream import _perform_travel
    from world_engine.cockpit.routes.creator import PlayerCharacterCreateBody, _validate_pc_creation
    from world_engine.models import Character
    from world_engine.writes.config import write_npc_schedule

    n = 0
    result = _perform_travel(ids["P"], ids["Z"], session)
    if result.get("status") != "zone_destination" or _location_of(session, ids["P"]) != ids["V"]:
        fail(f"(a) travel into a zone: {result}")
    else:
        n += 1
    result = _perform_travel(ids["P"], ids["C"], session)
    n += 1 if result.get("status") == "ok" and _location_of(session, ids["P"]) == ids["C"] else 0

    mut = SimpleNamespace(id="check-mut", world_id=ids["world"])
    message = _mutation_apply_npc_move(mut, {"npc_id": ids["N"], "from_location_id": ids["V"],
                                            "to_location_id": ids["Z"]}, session)
    session.rollback()
    if not message or _location_of(session, ids["N"]) != ids["V"]:
        fail(f"(a) npc_move into a zone returned {message!r}")
    else:
        n += 1
    message = _mutation_apply_npc_move(mut, {"npc_id": ids["N"], "from_location_id": ids["V"],
                                            "to_location_id": ids["C"]}, session)
    session.commit()
    n += 1 if message is None and _location_of(session, ids["N"]) == ids["C"] else 0

    n += _expect_http("PC creation", lambda: _validate_pc_creation(
        PlayerCharacterCreateBody(name="Nouveau", current_location_id=ids["Z"]), session))
    n += _accepts("PC creation", lambda: _validate_pc_creation(
        PlayerCharacterCreateBody(name="Nouveau", current_location_id=ids["C"]), session))

    npc_row = session.get(Character, ids["N"])
    n += _expect_http("fiche, character", lambda: _build_extension_kwargs(
        session, "character", {"current_location_id": ids["Z"]}, present_only=True, current=npc_row))
    n += _accepts("fiche, character", lambda: _build_extension_kwargs(
        session, "character", {"current_location_id": ids["V"]}, present_only=True, current=npc_row))
    n += _expect_http("fiche, item", lambda: _build_extension_kwargs(
        session, "item", {"name": "x", "location_id": ids["Z"]}))
    n += _accepts("fiche, item", lambda: _build_extension_kwargs(
        session, "item", {"name": "x", "location_id": ids["C"]}))
    already = SimpleNamespace(current_location_id=ids["Z"])
    n += _accepts("fiche save with an unchanged zone", lambda: _build_extension_kwargs(
        session, "character", {"current_location_id": ids["Z"]}, present_only=True, current=already))

    try:
        write_npc_schedule(session, world_id=ids["world"], npc_id=ids["N"],
                           rows=[{"phase": "matin", "location_id": ids["Z"]}], changed_by="check")
    except ValueError:
        n += 1
    else:
        fail("(a) schedule: a zone was accepted")
    session.rollback()
    n += _accepts("schedule", lambda: write_npc_schedule(
        session, world_id=ids["world"], npc_id=ids["N"],
        rows=[{"phase": "matin", "location_id": ids["C"]}], changed_by="check"))
    session.rollback()

    body = DiscoverableDetailBody(world_id=ids["world"], subject="s", content="c")
    n += _expect_http("detail", lambda: create_discoverable_detail(ids["Z"], body, session))
    n += _accepts("detail", lambda: create_discoverable_detail(ids["C"], body, session))
    if n != 15:
        fail(f"(a) expected 15 outcomes (7 refusals, 8 acceptances), got {n}")
    COUNTS["a"] = n


def check_b_vocabulary(session, ids) -> None:
    from world_engine.npc_group_author import resolve_vocabulary

    vocab = resolve_vocabulary(session, ids["Z"])
    offered = set(vocab["expanded_location_ids"]) | {loc["id"] for loc in vocab["locations"]}
    if ids["Z"] in offered:
        fail("(b) the NPC batch vocabulary offers the zone itself")
    if ids["C"] not in offered:
        fail("(b) the NPC batch vocabulary lost the zone's visitable child")
    COUNTS["b"] = len(offered)


def _writes_location(node: ast.AST) -> bool:
    if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        return any(isinstance(t, ast.Attribute) and t.attr == "current_location_id" for t in targets)
    if isinstance(node, ast.Call):
        callee = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
        return callee == "Character" and any(k.arg == "current_location_id" for k in node.keywords)
    return False


def check_c_sites() -> None:
    found: set[str] = set()
    for path in sorted((SRC / "world_engine").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(SRC).as_posix()
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if any(_writes_location(node) for node in ast.walk(fn)):
                found.add(f"{rel}::{fn.name}")
    for site in sorted(found - KNOWN_LOCATION_WRITERS):
        fail(f"(c) a new current_location_id write site, unguarded until named here: {site}")
    for site in sorted(KNOWN_LOCATION_WRITERS - found):
        fail(f"(c) a known write site no longer writes current_location_id: {site}")
    COUNTS["c"] = len(found)


def main() -> int:
    engine = _fresh_engine()
    from sqlmodel import Session as DbSession

    with DbSession(engine) as session:
        ids = _seed(session)
        check_a_paths(session, ids)
        check_b_vocabulary(session, ids)
    check_c_sites()

    for key in ("a", "b", "c"):
        if not COUNTS.get(key):
            fail(f"({key}) vacuous-proof: zero outcomes examined")

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: zone_placement — "
        f"(a) every placement path refuses a zone [{COUNTS['a']} outcomes], "
        f"(b) NPC batch vocabulary visitable only [{COUNTS['b']}], "
        f"(c) {COUNTS['c']} current_location_id write sites, all named"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
