"""G1 check for TICKET-0125 (BRIEF-0125-C) -- a world opens to players from the « Monde » page and only when told.

PW1 -- create. `create_world` then `get_world`: `open_to_players` is False.
PW2 -- edit. `update_world` with `open_to_players=True` answers True and the
   row holds it; a second `update_world` without the field answers True
   still; one with `False` answers False and the row holds it.
PW3 -- static, the page. `WorldSheet.svelte` holds
   `bind:checked={openToPlayers}`, `open_to_players: openToPlayers` and
   `Ouvert aux joueurs`. A missing file is a FAILURE.

The route functions are called directly with a `Session` on a fresh
temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule not reached is a FAILURE.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
WORLD_SHEET = ROOT / "frontend" / "src" / "creation" / "WorldSheet.svelte"

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


def _row_flag(engine, world_id: str):
    from sqlmodel import Session

    from world_engine.models import World

    with Session(engine) as db:
        return db.get(World, world_id).open_to_players


def rule_pw1(engine) -> str | None:
    from sqlmodel import Session

    from world_engine.cockpit.routes.creator import WorldCreateBody, create_world, get_world

    with Session(engine) as db:
        created = create_world(WorldCreateBody(name="A", description="d"), db=db)
        if not created.get("ok"):
            fail(f"PW1 create_world failed: {created!r}")
            return None
        world_id = created["world_id"]
        got = get_world(world_id, db=db).get("open_to_players")
    if got is not False:
        fail(f"PW1 a new world answers open_to_players {got!r}, expected False")
    return world_id


def rule_pw2(engine, world_id: str) -> int:
    from sqlmodel import Session

    from world_engine.cockpit.routes.creator import WorldUpdateBody, update_world

    steps = (
        ("open", {"open_to_players": True}, True),
        ("omitted", {}, True),
        ("close", {"open_to_players": False}, False),
    )
    reached = 0
    for label, extra, expected in steps:
        with Session(engine) as db:
            got = update_world(world_id, WorldUpdateBody(name="A", **extra), db=db).get("open_to_players")
        if got is not expected:
            fail(f"PW2 {label}: update_world answered open_to_players {got!r}, expected {expected!r}")
        held = _row_flag(engine, world_id)
        if held is not expected:
            fail(f"PW2 {label}: the row holds open_to_players {held!r}, expected {expected!r}")
        reached += 1
    return reached


def rule_pw3() -> None:
    if not WORLD_SHEET.exists():
        fail(f"PW3 {WORLD_SHEET.name} missing")
        return
    text = WORLD_SHEET.read_text(encoding="utf-8")
    for needle in ("bind:checked={openToPlayers}", "open_to_players: openToPlayers", "Ouvert aux joueurs"):
        if needle not in text:
            fail(f"PW3 {WORLD_SHEET.name} lacks {needle!r}")


def main() -> int:
    engine = _fresh_engine()
    rule_pw3()
    world_id = None
    try:
        world_id = rule_pw1(engine)
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"PW1 raised {type(exc).__name__}: {exc}")
    reached = 0
    if world_id is not None:
        try:
            reached = rule_pw2(engine, world_id)
        except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
            fail(f"PW2 raised {type(exc).__name__}: {exc}")
    if reached != 3:
        fail(f"PW2 reached {reached} of its 3 steps")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: player_worlds -- a world is closed by default, opens and closes from the « Monde » page, "
          "and an omitted flag changes nothing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
