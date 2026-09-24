"""G1 check for TICKET-0092 — name resolution over the name index.

Created by BRIEF-0092-A so the ticket's acceptance arrow resolves from the
first brief on; BRIEF-0092-B rewrites G0 for the scoped `resolve_named`
signature and adds the lot's rung cases.

G0 (fixture) -- in a fresh world, a character "Maelis Varn" resolves with
   `resolve_named("Maelis Varn", "person", world.id, session)` to `matched`
   on it, via the `named_exact` rung.

Fixtures run on a fresh temp-file SQLite database
(`WORLD_ENGINE_DATABASE_URL` set before any world_engine import — never
Nia's DB). FAILURES list, print FAIL lines, exit 1.
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
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{pathlib.Path(tmp_dir) / 'check.db'}"
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def _world(session, label: str):
    from world_engine.models import Entity, World

    world = World(name=label, is_active=False)
    session.add(world)
    session.flush()

    def entity(kind: str, name: str):
        row = Entity(world_id=world.id, type=kind, name=name)
        session.add(row)
        session.flush()
        return row

    return world, entity


def check_g0(engine) -> None:
    from sqlmodel import Session

    from world_engine.lore_resolve import resolve_named

    with Session(engine) as session:
        world, entity = _world(session, "G0 World")
        maelis = entity("character", "Maelis Varn")
        got = resolve_named("Maelis Varn", "person", world.id, session)
        if (got.verdict, got.entity_id, got.rung) != ("matched", maelis.id, "named_exact"):
            fail(f"G0: {(got.verdict, got.entity_id, got.rung)!r} "
                 f"!= ('matched', {maelis.id!r}, 'named_exact')")
        session.rollback()


def main() -> int:
    check_g0(_fresh_engine())
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: name_resolution — a character's exact name resolves to it via named_exact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
