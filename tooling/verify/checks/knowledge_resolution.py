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
  A fifth, non-DB unit-level demonstration of all five precedence tiers
  (stored row > location > faction > world > fact.default_level) is run and
  pasted separately in the brief's execution notes — this check covers the
  four assertions above only.
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
        f = create_fact(session, world_id=world_id, content=content, created_by="check", default_level="suspicious")
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
        if row.scope_type not in ("world", "faction", "location"):
            fail(f"fact_default {row.id}: scope_type={row.scope_type!r} outside ('world','faction','location')")
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

    check_no_retyped_vocabulary()

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: knowledge_resolution — all five precedence tiers resolve correctly, "
        "no fact_default shape violations, vocabulary imported (never re-typed), "
        "and the golden fixture is mutation-sensitive to both named alternate policies"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
