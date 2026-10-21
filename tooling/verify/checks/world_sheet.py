"""G1 check for TICKET-0124 -- a world has a tone and can be edited, and the « Monde » page edits it.

WS1 -- static. `World.tone` exists and is nullable;
   `scripts/migrate_v2_30_world_tone.py` exists and holds
   `ADD COLUMN tone TEXT`.
WS2 -- create. `create_world` with `tone=" sombre "` and two laws, then
   `get_world`, answers `name "A"`, `description "d"`, `tone "sombre"`
   (stripped), `laws ["l1", "l2"]`, `is_active True`.
WS3 -- edit. A second `create_world` leaves WS2's world inactive; on it,
   `update_world` with `name " B "`, empty description and
   tone, `laws ["x", "", "y"]` answers `name "B"`, `description None`,
   `tone None`, `laws ["x", "y"]`, `is_active` unchanged; the world's
   `current_phase` is unchanged. An empty name answers 422 and changes
   nothing; an unknown id answers 404 to `get_world` and `update_world`.

The route functions are called directly with a `Session` on a fresh
temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collected nothing is a
FAILURE.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
MIGRATION = ROOT / "scripts" / "migrate_v2_30_world_tone.py"

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


def _expect(rule: str, got: dict, expected: dict) -> int:
    seen = 0
    for key, value in expected.items():
        seen += 1
        if got.get(key) != value:
            fail(f"{rule} {key}: expected {value!r}, got {got.get(key)!r}")
    return seen


def rule_ws1() -> None:
    from world_engine.models import World

    column = World.__table__.columns.get("tone")
    if column is None:
        fail("WS1 World has no tone column")
    elif not column.nullable:
        fail("WS1 World.tone is not nullable")
    if not MIGRATION.is_file():
        fail(f"WS1 {MIGRATION.relative_to(ROOT)} does not exist")
    elif "ADD COLUMN tone TEXT" not in MIGRATION.read_text(encoding="utf-8"):
        fail("WS1 migrate_v2_30_world_tone.py holds no `ADD COLUMN tone TEXT`")


def rule_ws2(engine) -> str | None:
    from sqlmodel import Session

    from world_engine.cockpit.routes.creator import WorldCreateBody, create_world, get_world

    with Session(engine) as db:
        created = create_world(
            WorldCreateBody(name="A", description="d", fundamental_laws="l1\nl2", tone=" sombre "), db
        )
    if not (isinstance(created, dict) and created.get("ok") is True):
        fail(f"WS2 create_world answered {created!r}")
        return None
    world_id = created["world_id"]
    with Session(engine) as db:
        got = get_world(world_id, db)
    seen = _expect("WS2", got, {"id": world_id, "name": "A", "description": "d", "tone": "sombre",
                                "laws": ["l1", "l2"], "is_active": True})
    if not seen:
        fail("WS2 collected nothing")
    return world_id


def rule_ws3(engine, world_id: str) -> None:
    from fastapi import HTTPException
    from sqlmodel import Session

    from world_engine.cockpit.routes.creator import (
        WorldCreateBody,
        WorldUpdateBody,
        create_world,
        get_world,
        update_world,
    )
    from world_engine.models import World

    with Session(engine) as db:
        other = create_world(WorldCreateBody(name="Other"), db)
    if not (isinstance(other, dict) and other.get("ok") is True):
        fail(f"WS3 fixture: the second create_world answered {other!r}")
        return
    with Session(engine) as db:
        before = db.get(World, world_id)
        active_before, phase_before = before.is_active, before.current_phase
    if active_before is not False:
        fail("WS3 fixture: the edited world is still active after the second create")
        return
    seen = 0
    with Session(engine) as db:
        got = update_world(
            world_id, WorldUpdateBody(name=" B ", description="", tone="", laws=["x", "", "y"]), db
        )
    seen += _expect("WS3", got, {"name": "B", "description": None, "tone": None,
                                 "laws": ["x", "y"], "is_active": active_before})
    with Session(engine) as db:
        after = db.get(World, world_id)
        seen += 1
        if after.current_phase != phase_before:
            fail(f"WS3 current_phase moved: {phase_before!r} -> {after.current_phase!r}")
        snapshot = get_world(world_id, db)

    with Session(engine) as db:
        try:
            update_world(world_id, WorldUpdateBody(name="  ", tone="t", laws=["z"]), db)
            fail("WS3 empty name: update_world did not refuse")
        except HTTPException as exc:
            seen += 1
            if exc.status_code != 422 or exc.detail != "Le nom est requis.":
                fail(f"WS3 empty name: answered {exc.status_code} {exc.detail!r}")
    with Session(engine) as db:
        seen += 1
        if get_world(world_id, db) != snapshot:
            fail("WS3 empty name: the world changed")

    for label, call in (
        ("get_world", lambda db: get_world("no-such-world", db)),
        ("update_world", lambda db: update_world("no-such-world", WorldUpdateBody(name="C"), db)),
    ):
        with Session(engine) as db:
            try:
                call(db)
                fail(f"WS3 unknown id: {label} did not answer 404")
            except HTTPException as exc:
                seen += 1
                if exc.status_code != 404:
                    fail(f"WS3 unknown id: {label} answered {exc.status_code}")
    if not seen:
        fail("WS3 collected nothing")


def main() -> int:
    engine = _fresh_engine()
    rule_ws1()
    world_id = None
    try:
        world_id = rule_ws2(engine)
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"WS2 raised {type(exc).__name__}: {exc}")
    if world_id is None:
        fail("WS3 collected nothing: WS2 created no world")
    else:
        try:
            rule_ws3(engine, world_id)
        except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
            fail(f"WS3 raised {type(exc).__name__}: {exc}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: world_sheet -- a world has a nullable tone; create stores it stripped; "
          "GET/PUT read and edit one world without touching its activation or phase")
    return 0


if __name__ == "__main__":
    sys.exit(main())
