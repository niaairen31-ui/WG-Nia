"""G1 check for TICKET-0125 -- a world with several player characters is refused, never resolved to one of them.

PR1 -- fixture. One world, two `user` rows (`role="creator"`, `role="player"`),
   the M2 table walked row by row: 0 PCs, then one PC bound to the creator,
   then a second PC bound to the player user.
   `crud/entities.py::_player_character_id` answers 400
   `"No player character in the active world."` at 0, the PC's id at 1, and
   409 `"Plusieurs personnages joueurs dans ce monde : précisez lequel."` at 2;
   `analyzer_transcript.py::_resolve_player_id` answers None at 0, the PC's
   id at 1, None at 2. Status code AND detail are asserted for each refusal.
   A row not reached is a FAILURE.
PR2 -- static. The bodies of `_player_character_id` and `_resolve_player_id`
   (AST, found by name) hold no `.first()` call; either function not found
   is a FAILURE.

The functions are called directly with a `Session` on a fresh temp-file
SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any world_engine
import) -- never Nia's DB.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
ENTITIES = SRC / "world_engine" / "cockpit" / "crud" / "entities.py"
TRANSCRIPT = SRC / "world_engine" / "analyzer_transcript.py"

NONE_DETAIL = "No player character in the active world."
MANY_DETAIL = "Plusieurs personnages joueurs dans ce monde : précisez lequel."

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


def _add_pc(db, world_id: str, user_id: str, name: str) -> str:
    from world_engine.models import Character, Entity

    entity = Entity(world_id=world_id, type="character", name=name)
    db.add(entity)
    db.flush()
    db.add(Character(id=entity.id, world_id=world_id, character_type="player", user_id=user_id))
    db.commit()
    return entity.id


def _expect_refusal(row: str, db, world_id: str, status: int, detail: str) -> None:
    from fastapi import HTTPException

    from world_engine.cockpit.crud.entities import _player_character_id

    try:
        got = _player_character_id(db, world_id)
    except HTTPException as exc:
        if exc.status_code != status or exc.detail != detail:
            fail(f"PR1 {row} _player_character_id: expected {status} {detail!r}, "
                 f"got {exc.status_code} {exc.detail!r}")
        return
    fail(f"PR1 {row} _player_character_id: expected {status} {detail!r}, got {got!r}")


def _expect_resolved(row: str, db, world_id: str, pc_id: str) -> None:
    from world_engine.cockpit.crud.entities import _player_character_id

    got = _player_character_id(db, world_id)
    if got != pc_id:
        fail(f"PR1 {row} _player_character_id: expected {pc_id!r}, got {got!r}")


def _expect_resolve(row: str, db, world_id: str, expected: str | None) -> None:
    from world_engine.analyzer_transcript import _resolve_player_id

    got = _resolve_player_id(db, world_id)
    if got != expected:
        fail(f"PR1 {row} _resolve_player_id: expected {expected!r}, got {got!r}")


def rule_pr1(engine) -> int:
    from sqlmodel import Session

    from world_engine.models import User, World

    reached = 0
    with Session(engine) as db:
        world = World(name="W", is_active=True)
        creator = User(name="creator", role="creator")
        player = User(name="player", role="player")
        db.add_all([world, creator, player])
        db.commit()
        world_id, creator_id, player_id = world.id, creator.id, player.id

        _expect_refusal("0 PCs", db, world_id, 400, NONE_DETAIL)
        _expect_resolve("0 PCs", db, world_id, None)
        reached += 1

        first = _add_pc(db, world_id, creator_id, "Premier")
        _expect_resolved("1 PC", db, world_id, first)
        _expect_resolve("1 PC", db, world_id, first)
        reached += 1

        _add_pc(db, world_id, player_id, "Second")
        _expect_refusal("2 PCs", db, world_id, 409, MANY_DETAIL)
        _expect_resolve("2 PCs", db, world_id, None)
        reached += 1
    return reached


def _function_body(path: pathlib.Path, name: str) -> ast.FunctionDef | None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def rule_pr2() -> None:
    for path, name in ((ENTITIES, "_player_character_id"), (TRANSCRIPT, "_resolve_player_id")):
        if not path.exists():
            fail(f"PR2 {path.name} missing")
            continue
        func = _function_body(path, name)
        if func is None:
            fail(f"PR2 {name} not found in {path.name}")
            continue
        for node in ast.walk(func):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "first"):
                fail(f"PR2 {name} calls .first() (line {node.lineno})")


def main() -> int:
    engine = _fresh_engine()
    rule_pr2()
    reached = 0
    try:
        reached = rule_pr1(engine)
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"PR1 raised {type(exc).__name__}: {exc}")
    if reached != 3:
        fail(f"PR1 reached {reached} of the 3 table rows")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: pc_resolution -- 0, 1 and 2 PCs in one world: refused, resolved, refused")
    return 0


if __name__ == "__main__":
    sys.exit(main())
