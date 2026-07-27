"""Seed a small, deterministic fixture into the test database (C2, D1).

Independent of `seed_pilot.py` (the ~3000-line prod pilot seed) — this is a
distinct, minimal fixture, never imported or copied from it. Idempotent:
every row uses a deterministic slug primary key, so re-running checks-or-
creates and never duplicates. Prints a created/existing summary.

Refuses to run unless `WORLD_ENGINE_ENV=test`, so it can never touch prod.

    WORLD_ENGINE_ENV=test python scripts/seed_test.py

Deterministic-ID contract (H1) — `test_context.py` (BRIEF-0049-c) references
these IDs directly; this docstring is their single source of truth:

- World: ``world-test``
- Location: ``loc-test-tavern``
- NPC: ``npc-test-keeper``
- Player character: ``char-test-player``
- Knowledge on ``npc-test-keeper``:
  - ``kn-test-keeper-common`` — subject ``tavern_daily``,
    ``share_threshold=50`` (visible at neutral relation 50)
  - ``kn-test-keeper-guarded`` — subject ``local_rumor``,
    ``share_threshold=65`` (hidden at relation 50)
  - ``kn-test-keeper-secret`` — subject ``the_unnamed``,
    ``is_secret=True`` (never injected)
- Knowledge on ``char-test-player``:
  - ``kn-test-player-magic-incident`` — subject
    ``personal_magic_incident``, ``is_secret=True`` (player's own secret,
    absent from any NPC context)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_env = os.environ.get("WORLD_ENGINE_ENV")
if _env != "test":
    print(
        f"seed_test.py refuses to run unless WORLD_ENGINE_ENV=test (got: {_env or 'unset'})."
    )
    sys.exit(1)

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlmodel import Session  # noqa: E402

from world_engine import models as m  # noqa: E402
from world_engine.db import engine  # noqa: E402

WORLD_ID = "world-test"
LOCATION_ID = "loc-test-tavern"
NPC_ID = "npc-test-keeper"
PLAYER_ID = "char-test-player"

_created: list[tuple[str, str]] = []
_existing: list[tuple[str, str]] = []


def get_or_create(session: Session, model, id: str, **fields):
    """Return (obj, created). Create only if the primary key is absent."""
    obj = session.get(model, id)
    if obj is not None:
        _existing.append((model.__tablename__, id))
        return obj, False
    obj = model(id=id, **fields)
    session.add(obj)
    _created.append((model.__tablename__, id))
    return obj, True


def seed(session: Session) -> None:
    get_or_create(
        session,
        m.World,
        WORLD_ID,
        name="Test World",
        description="Minimal deterministic fixture world for the test DB.",
        is_active=True,
    )

    get_or_create(
        session,
        m.Entity,
        LOCATION_ID,
        world_id=WORLD_ID,
        type="location",
        name="Test Tavern",
        description="Fixture tavern for context-assembly assertions.",
        is_public=True,
    )
    get_or_create(
        session,
        m.Location,
        LOCATION_ID,
        parent_location_id=None,
        location_type="building",
    )

    get_or_create(
        session,
        m.Entity,
        NPC_ID,
        world_id=WORLD_ID,
        type="character",
        name="Test Keeper",
        is_public=True,
    )
    get_or_create(
        session,
        m.Character,
        NPC_ID,
        world_id=WORLD_ID,
        character_type="npc",
        current_location_id=LOCATION_ID,
        appearance="Fixture tavern-keeper.",
        backstory="Exists only to exercise the disclosure policy.",
    )

    get_or_create(
        session,
        m.Entity,
        PLAYER_ID,
        world_id=WORLD_ID,
        type="character",
        name="Test Player",
        is_public=True,
    )
    get_or_create(
        session,
        m.Character,
        PLAYER_ID,
        world_id=WORLD_ID,
        character_type="player",
        user_id="user-test",
        current_location_id=LOCATION_ID,
        appearance="Fixture player character.",
        backstory="Exists only to exercise the disclosure policy.",
    )

    # Shareable from neutral relation (threshold 50).
    get_or_create(
        session,
        m.Knowledge,
        "kn-test-keeper-common",
        entity_id=NPC_ID,
        subject="tavern_daily",
        level="knows",
        content="Everyday tavern-keeper talk, shared freely.",
        source="fixture",
        is_secret=False,
        share_threshold=50,
    )
    # Withheld at neutral relation, shared only as the relationship warms.
    get_or_create(
        session,
        m.Knowledge,
        "kn-test-keeper-guarded",
        entity_id=NPC_ID,
        subject="local_rumor",
        level="partial",
        content="A guarded rumor, shared only past relation 65.",
        source="fixture",
        is_secret=False,
        share_threshold=65,
    )
    # Never injected into any context (is_secret = TRUE).
    get_or_create(
        session,
        m.Knowledge,
        "kn-test-keeper-secret",
        entity_id=NPC_ID,
        subject="the_unnamed",
        level="fully_understands",
        content="A secret kept in the DB but never shared.",
        source="fixture",
        is_secret=True,
        share_threshold=50,
    )
    # Player's own secret — absent from any NPC context (mirrors the prod
    # fixture so the same assertion logic holds).
    get_or_create(
        session,
        m.Knowledge,
        "kn-test-player-magic-incident",
        entity_id=PLAYER_ID,
        subject="personal_magic_incident",
        level="fully_understands",
        content="The player's own secret incident.",
        source="fixture",
        is_secret=True,
        share_threshold=50,
    )


def main() -> None:
    with Session(engine) as session:
        seed(session)
        session.commit()

    for table, id_ in _created:
        print(f"  + created {table}: {id_}")
    for table, id_ in _existing:
        print(f"  = existing {table}: {id_}")
    print(f"seed_test: {len(_created)} created, {len(_existing)} existing")


if __name__ == "__main__":
    main()
