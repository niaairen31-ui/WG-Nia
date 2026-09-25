"""G1 check for TICKET-0093 (BRIEF-0093-A) — cast NPCs are named on the
fact sheet (J3a).

C-05: `_named_refs` names matched and cast entities, characters as npcs,
locations as locations, skips other types and missing rows, never
duplicates. Order is first occurrence, matched before cast.

Fixture runs on a fresh temp-file SQLite database
(`WORLD_ENGINE_DATABASE_URL` set before any world_engine import — never
Nia's DB). No model call. Vacuity-guarded: zero executed cases is a
FAILURE. FAILURES list, print FAIL lines, exit 1.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

FAILURES: list[str] = []
EXECUTED: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


# --- fixtures -----------------------------------------------------------------

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


# --- cases --------------------------------------------------------------------

def _matched(entity_id: str, name: str):
    from world_engine.day_concordance import MatchedMention
    from world_engine.day_extract import Mention

    return MatchedMention(
        mention=Mention(category="person", surface_form=name, kind="named"),
        entity_id=entity_id, rung="named_exact",
    )


def _cast(entity_id: str, text: str):
    from world_engine.day_concordance import CastMention
    from world_engine.day_extract import Mention

    return CastMention(
        mention=Mention(category="person", surface_form=text, kind="inferred", role_hint=text),
        entity_id=entity_id, rung="cast", basis="stable", candidate_ids=(),
    )


def check_matched_and_cast(engine) -> None:
    from sqlmodel import Session

    from world_engine.day_concordance import ConcordanceResult
    from world_engine.day_resolve import NamedRef, _named_refs

    EXECUTED.append("matched_and_cast")
    with Session(engine) as session:
        _, entity = _world(session, "day_fact_sheet_refs")
        aldric = entity("character", "Aldric")
        taverne = entity("location", "Taverne")
        marin = entity("character", "Marin")
        guilde = entity("faction", "Guilde")
        concordance = ConcordanceResult(
            matched=(
                _matched(aldric.id, "Aldric"), _matched(taverne.id, "Taverne"),
                _matched(guilde.id, "Guilde"), _matched("nope", "Personne"),
            ),
            cast=(_cast(marin.id, "le passeur"), _cast(aldric.id, "le forgeron")),
            ambiguous=(), unmatched=(), skipped_rungs=(),
        )
        npcs, locations = _named_refs(concordance, session)
        want_npcs = (NamedRef(aldric.id, "Aldric"), NamedRef(marin.id, "Marin"))
        want_locations = (NamedRef(taverne.id, "Taverne"),)
        if npcs != want_npcs:
            fail(f"matched_and_cast: npcs {npcs!r} != {want_npcs!r}")
        if locations != want_locations:
            fail(f"matched_and_cast: locations {locations!r} != {want_locations!r}")
        session.rollback()


def check_empty(engine) -> None:
    from sqlmodel import Session

    from world_engine.day_concordance import ConcordanceResult
    from world_engine.day_resolve import _named_refs

    EXECUTED.append("empty")
    empty = ConcordanceResult(matched=(), cast=(), ambiguous=(), unmatched=(), skipped_rungs=())
    with Session(engine) as session:
        got = _named_refs(empty, session)
    if got != ((), ()):
        fail(f"empty: {got!r} != ((), ())")


def main() -> int:
    engine = _fresh_engine()
    check_matched_and_cast(engine)
    check_empty(engine)
    if not EXECUTED:
        fail("vacuity: zero cases executed")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        f"PASS: day_fact_sheet_refs — {len(EXECUTED)} cases: matched and cast entities are "
        "named, characters as npcs, locations as locations, other types and missing rows "
        "skipped, no duplicates"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
