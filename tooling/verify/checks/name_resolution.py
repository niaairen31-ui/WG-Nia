"""G1 check for TICKET-0092 — name resolution over the name index.

Created by BRIEF-0092-A so the ticket's acceptance arrow resolves from the
first brief on; BRIEF-0092-B passes the scope to G0 and adds G1-G5;
BRIEF-0092-C adds G6-G8.

G0 (fixture) -- in a fresh world, a character "Maelis Varn" resolves with
   `resolve_named("Maelis Varn", "person", world.id, session,
   scope=CREATOR)` to `matched` on it, via the `named_exact` rung.
G1 (fixture) -- the LOT's "Rungs" table through `resolve_named`, exact
   equality on `(verdict, entity_id, candidate_ids, rung)`.
G2 (fixture) -- the LOT's "Near" table through `near_candidates`: "Maelys"
   yields only Maelis (83); "reine" yields La Reine Grise (63) then Reine
   Ysolde (59); `exclude_ids` drops an id; `scope=PROSE` raises ValueError.
G3 (fixture) -- the day chain sees the perceiver regime: a PC who knows the
   appellation "la reine" of an NPC resolves it via `named_exact`; a PC who
   does not leaves it unmatched.
G4 (fixture) -- `resolve_subject("la reine", ...)` stays unmatched with that
   appellation present (names only, N10a).
G5 (fixture) -- a tokenizer generator mention "Varn" next to "Maelis Varn"
   stays unresolved: no partial rung outside `creator`.
G6 (static) -- the LOT's "Categories after C" table through
   `category_of_type`, a runtime slug "golem" included.
G7 (fixture) -- an `item` "Épée de Kar" resolves under "object"; a "golem"
   "Gardien" resolves under "other", not under "person"; `validate_binding`
   agrees on both and refuses "object" for the golem.
G8 (static) -- `lore_plan._MENTION_CATEGORIES` equals
   `lore_resolve.CATEGORIES` (belt and braces over lore_isolation R9).

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
    from world_engine.name_index import CREATOR

    with Session(engine) as session:
        world, entity = _world(session, "G0 World")
        maelis = entity("character", "Maelis Varn")
        got = resolve_named("Maelis Varn", "person", world.id, session, scope=CREATOR)
        if (got.verdict, got.entity_id, got.rung) != ("matched", maelis.id, "named_exact"):
            fail(f"G0: {(got.verdict, got.entity_id, got.rung)!r} "
                 f"!= ('matched', {maelis.id!r}, 'named_exact')")
        session.rollback()


def _appellation(session, owner, content, scope=None):
    from world_engine.writes.facets import add_entity_fact

    return add_entity_fact(session, entity_id=owner.id, facet="appellation", content=content,
                           created_by="check", scope=scope)


def _got(resolution) -> tuple:
    return (resolution.verdict, resolution.entity_id, resolution.candidate_ids, resolution.rung)


def check_g1(engine) -> None:
    from sqlmodel import Session

    from world_engine.lore_resolve import resolve_named
    from world_engine.name_index import CREATOR, NAMES_ONLY

    with Session(engine) as session:
        world, entity = _world(session, "G1 World")
        maelis = entity("character", "Maelis Varn")
        grise = entity("location", "La Reine Grise")
        ysolde = entity("character", "Ysolde")
        _appellation(session, ysolde, "la reine")
        table = [
            ("la reine", "person", CREATOR, ("matched", ysolde.id, (ysolde.id,), "named_exact")),
            ("la reine", "place", CREATOR, ("matched", grise.id, (grise.id,), "named_partial")),
            ("Varn", "person", CREATOR, ("matched", maelis.id, (maelis.id,), "named_partial")),
            ("Varn", "person", NAMES_ONLY, ("unmatched", None, (), None)),
            ("Ma", "person", CREATOR, ("unmatched", None, (), None)),
        ]
        for surface, category, scope, expected in table:
            got = _got(resolve_named(surface, category, world.id, session, scope=scope))
            if got != expected:
                fail(f"G1 {surface!r} {category} {scope.regime}: {got!r} != {expected!r}")
        reine = entity("character", "Reine")
        expected = ("ambiguous", None, tuple(sorted((ysolde.id, reine.id))), "named_exact")
        got = _got(resolve_named("la reine", "person", world.id, session, scope=CREATOR))
        if got != expected:
            fail(f"G1 'la reine' person creator + 'Reine': {got!r} != {expected!r}")
        session.rollback()


def check_g2(engine) -> None:
    from sqlmodel import Session

    from world_engine.lore_resolve import near_candidates
    from world_engine.name_index import CREATOR, PROSE

    with Session(engine) as session:
        world, entity = _world(session, "G2 World")
        maelis = entity("character", "Maelis")
        entity("character", "Maelis Varn")
        ysolde = entity("character", "Reine Ysolde")
        grise = entity("location", "La Reine Grise")

        def near(surface, **kwargs):
            return near_candidates(surface, world.id, session, scope=CREATOR, **kwargs)

        got = [(c.entity_id, c.score) for c in near("Maelys")]
        if got != [(maelis.id, 83)]:
            fail(f"G2 'Maelys': {got!r} != {[(maelis.id, 83)]!r}")
        got = [(c.entity_id, c.score) for c in near("reine")]
        if got != [(grise.id, 63), (ysolde.id, 59)]:
            fail(f"G2 'reine': {got!r} != {[(grise.id, 63), (ysolde.id, 59)]!r}")
        got = [c.entity_id for c in near("reine", exclude_ids=frozenset({grise.id}))]
        if got != [ysolde.id]:
            fail(f"G2 'reine' excluding La Reine Grise: {got!r} != {[ysolde.id]!r}")
        try:
            near_candidates("reine", world.id, session, scope=PROSE)
            fail("G2: near_candidates(scope=PROSE) did not raise ValueError")
        except ValueError:
            pass
        session.rollback()


def check_g3_g4(engine) -> None:
    from sqlmodel import Session

    from world_engine.day_concordance import concord
    from world_engine.day_extract import Mention
    from world_engine.models import Character, Location
    from world_engine.subject_resolve import resolve_subject
    from world_engine.writes.facets import ScopeChoice
    from world_engine.writes.knowledge import write_knowledge

    with Session(engine) as session:
        world, entity = _world(session, "G3 World")
        place = entity("location", "Taverne")
        session.add(Location(id=place.id))

        def character(name: str, character_type: str):
            row = entity("character", name)
            session.add(Character(id=row.id, world_id=world.id, character_type=character_type,
                                  current_location_id=place.id))
            session.flush()
            return session.get(Character, row.id)

        pc_p, npc_y = character("Pell", "player"), character("Ysolde", "npc")
        pc_q = character("Quill", "player")
        fact = _appellation(session, npc_y, "la reine", ScopeChoice("none"))
        write_knowledge(session, entity_id=pc_p.id, fact_id=fact.id, subject="la reine",
                        level="knows", is_secret=False, changed_by="check")
        session.flush()
        mention = Mention(category="person", surface_form="la reine", kind="named")
        got = concord([mention], pc_p, session)
        seen = [(m.entity_id, m.rung) for m in got.matched]
        if seen != [(npc_y.id, "named_exact")]:
            fail(f"G3 knowing PC: matched {seen!r} != {[(npc_y.id, 'named_exact')]!r}")
        got = concord([mention], pc_q, session)
        if got.matched or got.cast or got.ambiguous or len(got.unmatched) != 1:
            fail(f"G3 unknowing PC: 'la reine' not unmatched: {got!r}")
        subject = resolve_subject("la reine", world.id, session)
        if subject.verdict != "unmatched":
            fail(f"G4: resolve_subject('la reine') is {subject.verdict!r}, not 'unmatched'")
        session.rollback()


def check_g5(engine) -> None:
    from sqlmodel import Session

    from world_engine.prose_tokens import tokenize

    with Session(engine) as session:
        world, entity = _world(session, "G5 World")
        entity("character", "Maelis Varn")
        got = tokenize(session, world_id=world.id, text="Varn arrive.",
                       mentions=[{"name": "Varn", "category": "person"}])
        pairs = [(u.surface, u.reason) for u in got.unresolved]
        if got.text != "Varn arrive." or pairs != [("Varn", "inconnu")]:
            fail(f"G5: {got.text!r} {pairs!r} != 'Varn arrive.' [('Varn', 'inconnu')]")
        session.rollback()


_CATEGORY_TABLE: tuple[tuple[str, str], ...] = (
    ("location", "place"), ("character", "person"), ("faction", "faction"),
    ("item", "object"), ("artifact", "other"), ("golem", "other"), ("", "other"),
)


def check_g6() -> None:
    from world_engine.lore_resolve import category_of_type

    for entity_type, expected in _CATEGORY_TABLE:
        got = category_of_type(entity_type)
        if got != expected:
            fail(f"G6: category_of_type({entity_type!r}) is {got!r}, not {expected!r}")


def check_g7(engine) -> None:
    from sqlmodel import Session

    from world_engine.lore_resolve import resolve_named, validate_binding
    from world_engine.name_index import CREATOR

    with Session(engine) as session:
        world, entity = _world(session, "G7 World")
        sword = entity("item", "Épée de Kar")
        golem = entity("golem", "Gardien")
        got = _got(resolve_named("l'épée de Kar", "object", world.id, session, scope=CREATOR))
        if got[:2] != ("matched", sword.id):
            fail(f"G7 'l'épée de Kar' object: {got!r} is not matched on the item")
        got = _got(resolve_named("Gardien", "other", world.id, session, scope=CREATOR))
        if got[:2] != ("matched", golem.id):
            fail(f"G7 'Gardien' other: {got!r} is not matched on the golem")
        got = _got(resolve_named("Gardien", "person", world.id, session, scope=CREATOR))
        if got[0] != "unmatched":
            fail(f"G7 'Gardien' person: {got!r} is not unmatched")
        for entity_id, category, expected in (
            (sword.id, "object", True), (golem.id, "other", True),
            (golem.id, "object", False), (golem.id, "person", False),
            (sword.id, "other", False), (golem.id, "weapon", False),
        ):
            if validate_binding(entity_id, category, world.id, session) is not expected:
                fail(f"G7: validate_binding({entity_id!r}, {category!r}) is not {expected!r}")
        session.rollback()


def check_g8() -> None:
    from world_engine import lore_plan, lore_resolve

    if lore_plan._MENTION_CATEGORIES != lore_resolve.CATEGORIES:
        fail(f"G8: lore_plan._MENTION_CATEGORIES {lore_plan._MENTION_CATEGORIES!r} != "
             f"lore_resolve.CATEGORIES {lore_resolve.CATEGORIES!r}")


def main() -> int:
    engine = _fresh_engine()
    check_g0(engine)
    check_g1(engine)
    check_g2(engine)
    check_g3_g4(engine)
    check_g5(engine)
    check_g6()
    check_g7(engine)
    check_g8()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: name_resolution — exact names resolve, appellations and partial names resolve "
          "for the creator only, near names score and order as the lot's table, the day chain "
          "sees only the appellations its character knows, subjects and tokenizer mentions "
          "stay on names, objects and every other type are nameable categories")
    return 0


if __name__ == "__main__":
    sys.exit(main())
