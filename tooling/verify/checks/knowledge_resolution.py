"""G1 check for TICKET-0082 (BRIEF-0082-c) — scoped default knowledge-level
resolution (G2a).

DB-backed, self-contained fresh temp-file SQLite fixture (WORLD_ENGINE_
DATABASE_URL set BEFORE any world_engine import) — same idiom as
fact_spine.py / door_coverage.py, so this check never touches Nia's real DB.
FAILURES list, print FAIL lines, sys.exit(1); zero pairs/rows examined for
any DB assertion is a FAIL, never a vacuous pass.

Four assertions:
  1. Every sampled (entity, fact) pair resolves, via
     `knowledge_resolve.resolve_knowledge_level`, to a value in the
     six-value vocabulary — never None, never an unrecognised string.
  2. No `fact_default` row violates its shape constraints
     (`ck_fact_default_scope_type` / `ck_fact_default_scope_shape`).
  3. AST scan: `knowledge_resolve.py` and this check both import the
     six-value vocabulary from `writes/knowledge.py` — neither re-types it
     as a literal collection anywhere in the resolution path.
  4. Mutation-sensitivity (golden cases are failing inputs). Fixture: an
     entity holds ACTIVE membership in two factions — Faction A (joined
     first, `fact_default` level `'rumor'`) and Faction B (joined second,
     level `'knows'`) — on the same fact. The REAL `resolve_knowledge_level`
     (highest-wins, G2a) returns `'knows'`. Two named mutations, computed
     over the SAME raw `('rumor', 'knows')` pair in join order, are each
     asserted to disagree with `'knows'` — proving this fixture would make
     the check FAIL under either:
       - **lowest-wins**: `min` by ladder rank instead of `max` — yields
         `'rumor'`.
       - **first-membership-wins**: the level of whichever faction was
         joined first, ignoring the others — also `'rumor'` here (Faction A
         joined first).
  5. C-09 case table (TICKET-0091, BRIEF-0091-D): the seven-tier order
     (stored > self > rencontre > location > faction > world >
     fact.default_level), rows 1-9 of the lot's table, each built through
     the real writers (`create_fact`, `attach_participants`,
     `create_fact_default`, `write_knowledge`, `record_encounter`) and
     asserted on BOTH entry points — `resolve_knowledge_level` and
     `resolve_levels_for_entity` (absent from the batch dict = `'unaware'`).
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
THIS_FILE = pathlib.Path(__file__).resolve()

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


def _build_fixture(session):
    """Returns (alice_id, facts, raw_faction_levels_in_join_order) — a
    single fixture exercising all five precedence tiers plus the
    mutation-sensitivity golden case (tier 3, faction, doubles as both)."""
    from world_engine.models import (
        Character, Entity, Faction, FactionMembership, Location, World,
    )
    from world_engine.writes import create_fact, create_fact_default, write_knowledge

    world = World(name="Check World", is_active=True)
    session.add(world)
    session.commit()
    session.refresh(world)
    world_id = world.id

    def _entity(etype: str, name: str) -> str:
        entity = Entity(world_id=world_id, type=etype, name=name)
        session.add(entity)
        session.commit()
        session.refresh(entity)
        return entity.id

    root_id = _entity("location", "Root Location")
    session.add(Location(id=root_id, parent_location_id=None))
    child_id = _entity("location", "Child Location")
    session.add(Location(id=child_id, parent_location_id=root_id))
    session.commit()

    faction_a_id = _entity("faction", "Faction A")
    session.add(Faction(id=faction_a_id))
    faction_b_id = _entity("faction", "Faction B")
    session.add(Faction(id=faction_b_id))
    session.commit()

    alice_id = _entity("character", "Alice")
    session.add(Character(
        id=alice_id, world_id=world_id, character_type="npc",
        current_location_id=child_id,
    ))
    session.commit()

    # Faction A joined FIRST, Faction B joined SECOND (join order matters
    # for the first-membership-wins mutation below).
    session.add(FactionMembership(world_id=world_id, entity_id=alice_id, faction_id=faction_a_id))
    session.commit()
    session.add(FactionMembership(world_id=world_id, entity_id=alice_id, faction_id=faction_b_id))
    session.commit()

    def _fact(content: str) -> str:
        f = create_fact(session, world_id=world_id, content=content, created_by="check", facet="information", default_level="suspicious")
        session.commit()
        return f.id

    # Tier 1 — stored row beats everything, including a faction default.
    fact_stored = _fact("tier1: stored beats faction default")
    create_fact_default(session, world_id=world_id, fact_id=fact_stored, scope_type="faction", scope_id=faction_a_id, level="knows", created_by="check")
    write_knowledge(session, entity_id=alice_id, fact_id=fact_stored, subject="tier1", level="partial")
    session.commit()

    # Tier 2 — location beats world.
    fact_loc_vs_world = _fact("tier2: location beats world")
    create_fact_default(session, world_id=world_id, fact_id=fact_loc_vs_world, scope_type="world", scope_id=None, level="rumor", created_by="check")
    create_fact_default(session, world_id=world_id, fact_id=fact_loc_vs_world, scope_type="location", scope_id=child_id, level="knows", created_by="check")
    session.commit()

    # Tier 2b — nearest ancestor beats a farther one.
    fact_loc_nearest = _fact("tier2b: nearest location ancestor wins")
    create_fact_default(session, world_id=world_id, fact_id=fact_loc_nearest, scope_type="location", scope_id=root_id, level="suspicious", created_by="check")
    create_fact_default(session, world_id=world_id, fact_id=fact_loc_nearest, scope_type="location", scope_id=child_id, level="partial", created_by="check")
    session.commit()

    # Tier 3 — two active memberships resolve to the HIGHEST level (G2a);
    # this is also the mutation-sensitivity golden case.
    fact_faction_highest = _fact("tier3: highest of two active memberships wins")
    create_fact_default(session, world_id=world_id, fact_id=fact_faction_highest, scope_type="faction", scope_id=faction_a_id, level="rumor", created_by="check")
    create_fact_default(session, world_id=world_id, fact_id=fact_faction_highest, scope_type="faction", scope_id=faction_b_id, level="knows", created_by="check")
    session.commit()

    # Tier 5 — no fact_default at all, no stored row: fact.default_level.
    fact_no_default = _fact("tier5: falls back to fact.default_level")
    session.commit()

    facts = {
        "stored": fact_stored,
        "loc_vs_world": fact_loc_vs_world,
        "loc_nearest": fact_loc_nearest,
        "faction_highest": fact_faction_highest,
        "no_default": fact_no_default,
    }
    raw_faction_levels_in_join_order = ("rumor", "knows")  # Faction A, then Faction B
    return alice_id, facts, raw_faction_levels_in_join_order


def check_precedence_and_vacuous_proof(session, alice_id, facts) -> None:
    from world_engine.knowledge_resolve import resolve_knowledge_level
    from world_engine.writes.knowledge import KNOWLEDGE_LEVELS

    expected = {
        "stored": "partial",
        "loc_vs_world": "knows",
        "loc_nearest": "partial",
        "faction_highest": "knows",
        "no_default": "suspicious",
    }

    examined = 0
    for label, fact_id in facts.items():
        examined += 1
        result = resolve_knowledge_level(session, alice_id, fact_id)
        if result not in KNOWLEDGE_LEVELS:
            fail(f"resolve_knowledge_level({label!r}) returned {result!r} — not in the six-value vocabulary")
        if result != expected[label]:
            fail(f"precedence tier {label!r}: expected {expected[label]!r}, got {result!r}")

    if examined == 0:
        fail("vacuous-proof: zero (entity, fact) pairs examined on a freshly seeded fixture")


def check_fact_default_shape(session) -> None:
    from sqlmodel import select

    from world_engine.models import FactDefault

    rows = session.exec(select(FactDefault)).all()
    if not rows:
        fail("vacuous-proof: zero fact_default rows examined on a freshly seeded fixture")
    for row in rows:
        if row.scope_type not in ("world", "faction", "location", "rencontre"):
            fail(
                f"fact_default {row.id}: scope_type={row.scope_type!r} outside "
                "('world','faction','location','rencontre')"
            )
        if row.scope_type == "world" and row.scope_id is not None:
            fail(f"fact_default {row.id}: scope_type='world' but scope_id={row.scope_id!r} is not NULL")
        if row.scope_type != "world" and row.scope_id is None:
            fail(f"fact_default {row.id}: scope_type={row.scope_type!r} requires a non-NULL scope_id")


def check_mutation_sensitivity(session, alice_id, facts, raw_faction_levels_in_join_order) -> None:
    from world_engine.knowledge_resolve import resolve_knowledge_level
    from world_engine.writes.knowledge import KNOWLEDGE_LEVEL_LADDER

    fact_id = facts["faction_highest"]
    real = resolve_knowledge_level(session, alice_id, fact_id)
    if real != "knows":
        fail(f"golden case: expected 'knows' (highest-wins over rumor/knows), production returned {real!r}")
        return

    alt_lowest_wins = min(raw_faction_levels_in_join_order, key=KNOWLEDGE_LEVEL_LADDER.index)
    if alt_lowest_wins == "knows":
        fail(
            "mutation-sensitivity: a lowest-wins policy over the SAME golden fixture "
            "also produces 'knows' — this fixture cannot distinguish highest-wins "
            "(G2a, correct) from lowest-wins (mutation 1)"
        )

    alt_first_membership_wins = raw_faction_levels_in_join_order[0]
    if alt_first_membership_wins == "knows":
        fail(
            "mutation-sensitivity: a first-membership-wins policy over the SAME golden "
            "fixture also produces 'knows' — this fixture cannot distinguish "
            "highest-wins (G2a, correct) from first-membership-wins (mutation 2)"
        )


# ── C-09 case table: seven tiers, both entry points ────────────────────────
#
# Fallback `fact.default_level` is `fully_understands` on every row, a level
# no default in the table uses — a row reaching tier 7 is unambiguous.

C09_FALLBACK = "fully_understands"


def _build_c09_fixture(session):
    """Returns (perceiver_id, {case: (fact_id, expected)})."""
    from world_engine.encounters import record_encounter
    from world_engine.models import (
        Character, Entity, Faction, FactionMembership, Location, World,
    )
    from world_engine.writes import (
        attach_participants, create_fact, create_fact_default, write_knowledge,
    )

    world = World(name="C-09 World", is_active=False)  # one active world per DB
    session.add(world)
    session.commit()
    wid = world.id

    def _entity(etype: str, name: str) -> str:
        entity = Entity(world_id=wid, type=etype, name=name)
        session.add(entity)
        session.commit()
        return entity.id

    root_id = _entity("location", "C09 Root")
    session.add(Location(id=root_id, parent_location_id=None))
    here_id = _entity("location", "C09 Here")
    session.add(Location(id=here_id, parent_location_id=root_id))
    faction_id = _entity("faction", "C09 Faction")
    session.add(Faction(id=faction_id))
    session.commit()

    perceiver_id = _entity("character", "Perceiver")
    session.add(Character(
        id=perceiver_id, world_id=wid, character_type="npc", current_location_id=here_id,
    ))
    subject_id = _entity("character", "Subject")
    friend_id = _entity("character", "Friend")
    stranger_id = _entity("character", "Stranger")
    session.commit()
    session.add(FactionMembership(world_id=wid, entity_id=perceiver_id, faction_id=faction_id))
    record_encounter(session, world_id=wid, a_id=perceiver_id, b_id=friend_id, source="visit")
    session.commit()

    def _fact(label: str, facet: str, about: str) -> str:
        fact = create_fact(
            session, world_id=wid, content=f"c09 {label}", created_by="check",
            facet=facet, default_level=C09_FALLBACK,
        )
        session.flush()
        attach_participants(session, fact=fact, entity_ids=[about])
        session.commit()
        return fact.id

    def _default(fact_id: str, scope_type: str, scope_id, level: str) -> None:
        create_fact_default(
            session, world_id=wid, fact_id=fact_id, scope_type=scope_type,
            scope_id=scope_id, level=level, created_by="check",
        )
        session.commit()

    cases: dict[int, tuple[str, str]] = {}

    # 1 — stored 'unaware' beats every other tier, self included.
    f1 = _fact("1", "physique", perceiver_id)
    for scope_type, scope_id in (
        ("rencontre", friend_id), ("location", here_id), ("faction", faction_id), ("world", None),
    ):
        _default(f1, scope_type, scope_id, "knows")
    write_knowledge(session, entity_id=perceiver_id, fact_id=f1, subject="c09 1", level="unaware")
    session.commit()
    cases[1] = (f1, "unaware")

    # 2 — participant of a descriptive fact: self -> knows.
    cases[2] = (_fact("2", "physique", perceiver_id), "knows")

    # 3 — participant of an `information` fact: no self tier -> fallback.
    cases[3] = (_fact("3", "information", perceiver_id), C09_FALLBACK)

    # 4 — an acquaintance's rencontre default beats the location default.
    f4 = _fact("4", "physique", subject_id)
    _default(f4, "rencontre", friend_id, "partial")
    _default(f4, "location", here_id, "knows")
    cases[4] = (f4, "partial")

    # 5 — location.
    f5 = _fact("5", "reputation", subject_id)
    _default(f5, "location", here_id, "knows")
    cases[5] = (f5, "knows")

    # 6 — faction.
    f6 = _fact("6", "reputation", subject_id)
    _default(f6, "faction", faction_id, "rumor")
    cases[6] = (f6, "rumor")

    # 7 — world.
    f7 = _fact("7", "reputation", subject_id)
    _default(f7, "world", None, "suspicious")
    cases[7] = (f7, "suspicious")

    # 8 — nothing: fact.default_level.
    cases[8] = (_fact("8", "reputation", subject_id), C09_FALLBACK)

    # 9 — a rencontre default on someone the perceiver never met: ignored.
    f9 = _fact("9", "physique", subject_id)
    _default(f9, "rencontre", stranger_id, "knows")
    cases[9] = (f9, C09_FALLBACK)

    return perceiver_id, cases


def check_c09_case_table(session) -> None:
    from world_engine.knowledge_resolve import resolve_knowledge_level, resolve_levels_for_entity

    perceiver_id, cases = _build_c09_fixture(session)
    if len(cases) != 9:
        fail(f"C-09 vacuous-proof: expected 9 case rows, built {len(cases)}")
    batch = resolve_levels_for_entity(session, perceiver_id)
    for case, (fact_id, expected) in sorted(cases.items()):
        single = resolve_knowledge_level(session, perceiver_id, fact_id)
        if single != expected:
            fail(f"C-09 case {case}: resolve_knowledge_level expected {expected!r}, got {single!r}")
        batched = batch.get(fact_id, "unaware")
        if batched != expected:
            fail(f"C-09 case {case}: resolve_levels_for_entity expected {expected!r}, got {batched!r}")


# ── AST scan: no re-typed six-value vocabulary in the resolution path ──────
#
# The comparison set itself is imported (`KNOWLEDGE_LEVELS`), never
# re-typed as a literal here — this check is itself one of the two files
# it scans (item 7's "in this module and in knowledge_resolve.py").

KNOWLEDGE_RESOLVE_FILE = SRC / "world_engine" / "knowledge_resolve.py"


def _collection_string_values(node: ast.AST):
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values: set[str] = set()
        for elt in node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                values.add(elt.value)
            else:
                return None
        return values
    return None


def check_no_retyped_vocabulary() -> None:
    from world_engine.writes.knowledge import KNOWLEDGE_LEVELS as six_values

    targets = [KNOWLEDGE_RESOLVE_FILE, THIS_FILE]
    for path in targets:
        if not path.is_file():
            fail(f"{path} not found — AST scan target missing")
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        rel = path.name
        imports_vocabulary = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("writes.knowledge"):
                if any(alias.name in ("KNOWLEDGE_LEVELS", "KNOWLEDGE_LEVEL_LADDER") for alias in node.names):
                    imports_vocabulary = True
            values = _collection_string_values(node)
            if values == six_values:
                fail(
                    f"{rel}:{node.lineno} — re-typed six-value level vocabulary literal "
                    "(import KNOWLEDGE_LEVELS/KNOWLEDGE_LEVEL_LADDER from writes/knowledge.py instead)"
                )
        if not imports_vocabulary:
            fail(f"{rel} does not import the six-value vocabulary from writes/knowledge.py")


def main() -> int:
    engine = _fresh_engine()
    from sqlmodel import Session as DbSession

    with DbSession(engine) as session:
        alice_id, facts, raw_faction_levels_in_join_order = _build_fixture(session)
        check_precedence_and_vacuous_proof(session, alice_id, facts)
        check_fact_default_shape(session)
        check_mutation_sensitivity(session, alice_id, facts, raw_faction_levels_in_join_order)
        check_c09_case_table(session)

    check_no_retyped_vocabulary()

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: knowledge_resolution — the five legacy precedence rows and the nine "
        "C-09 rows resolve correctly on both entry points, "
        "no fact_default shape violations, vocabulary imported (never re-typed), "
        "and the golden fixture is mutation-sensitive to both named alternate policies"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
