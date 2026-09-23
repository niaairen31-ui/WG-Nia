"""G1 check for TICKET-0090 (BRIEF-0090-a) — perceiver-oriented relations.

DB-backed, self-contained fresh temp-file SQLite fixture (WORLD_ENGINE_
DATABASE_URL set BEFORE any world_engine import) — same idiom as
fact_spine.py, so this check never touches Nia's real DB. FAILURES list,
print FAIL lines, sys.exit(1); zero rows examined in any assertion is a
FAIL, never a vacuous pass. Fixture data is built through the REAL
sanctioned writers (`writes/relations.py::write_relation`,
`set_target_knows`).

Four assertions:
  a. `write_relation` refuses a social relation with `direction="mutual"`
     and with `"b_to_a"` (each a `ValueError`) and accepts `"a_to_b"`.
  b. After creating one social, one `connects_to` and one `controls`
     relation, exactly one `fact` row points at each of the first two and
     none at the third; the social fact's `default_level` is `unaware`, the
     `connects_to` fact's is `knows`; the social content equals
     `relation_orientation.lien_fact_content(...)` called here, never a
     re-typed literal.
  c. With A->B and B->A both present, a delta on (B, A) moves only the
     B->A row's intensity — the A->B row's intensity and `change_history`
     length are unchanged (then the same for (A, B)). Before that, with A->B
     alone, a delta on (B, A) creates B->A and leaves A->B untouched — the
     case that catches an order-blind finder, which SQLite's index plan can
     otherwise mask when both rows exist.
  d. `set_target_knows` is idempotent both ways: True twice leaves one
     knowledge row, False removes it, False again is a no-op.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

FAILURES: list[str] = []
COUNTS: dict[str, int] = {}


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


def _seed(session):
    """One world, three characters (A, B, C), two locations (L1, L2) and one
    faction (F). Returns (world_id, ids_by_label)."""
    from world_engine.models import Entity, World

    world = World(name="Check World", is_active=True)
    session.add(world)
    session.commit()
    session.refresh(world)
    ids: dict[str, str] = {}
    for label, etype in (("A", "character"), ("B", "character"), ("C", "character"),
                         ("L1", "location"), ("L2", "location"), ("F", "faction")):
        entity = Entity(world_id=world.id, type=etype, name=f"Entity {label}")
        session.add(entity)
        session.commit()
        session.refresh(entity)
        ids[label] = entity.id
    return world.id, ids


def _facts_of(session, relation_id: str):
    from sqlmodel import select

    from world_engine.models import Fact

    return session.exec(select(Fact).where(Fact.relation_id == relation_id)).all()


def check_a_orientation_guard(session, world_id, ids) -> None:
    from world_engine.writes.relations import write_relation

    refused = 0
    for bad in ("mutual", "b_to_a"):
        try:
            write_relation(
                session, mode="set", world_id=world_id, entity_a_id=ids["A"],
                entity_b_id=ids["C"], type="fear", value=40, direction=bad,
            )
        except ValueError:
            refused += 1
            session.rollback()
        else:
            session.rollback()
            fail(f"(a) write_relation accepted a social relation with direction={bad!r}")
    rel = write_relation(
        session, mode="set", world_id=world_id, entity_a_id=ids["A"],
        entity_b_id=ids["C"], type="fear", value=40, direction="a_to_b",
    )
    session.commit()
    accepted = 1 if rel.direction == "a_to_b" else 0
    if not accepted:
        fail(f"(a) accepted a_to_b row carries direction={rel.direction!r}")
    COUNTS["a"] = refused + accepted
    if refused != 2:
        fail(f"(a) expected 2 refused directions, got {refused}")


def check_b_typed_fact_at_birth(session, world_id, ids) -> None:
    from world_engine.models import Entity
    from world_engine.prose_render import fact_text
    from world_engine.relation_orientation import lien_fact_content
    from world_engine.writes.relations import write_relation

    social = write_relation(
        session, mode="set", world_id=world_id, entity_a_id=ids["A"],
        entity_b_id=ids["B"], type="ally", value=60,
    )
    connects = write_relation(
        session, mode="set", world_id=world_id, entity_a_id=ids["L1"],
        entity_b_id=ids["L2"], type="connects_to", value=50, direction="mutual",
    )
    controls = write_relation(
        session, mode="set", world_id=world_id, entity_a_id=ids["F"],
        entity_b_id=ids["L1"], type="controls", value=50,
    )
    session.commit()

    examined = 0
    social_facts = _facts_of(session, social.id)
    connects_facts = _facts_of(session, connects.id)
    controls_facts = _facts_of(session, controls.id)
    examined += len(social_facts) + len(connects_facts)
    if len(social_facts) != 1:
        fail(f"(b) social relation has {len(social_facts)} typed fact(s), expected 1")
    if len(connects_facts) != 1:
        fail(f"(b) connects_to relation has {len(connects_facts)} typed fact(s), expected 1")
    if controls_facts:
        fail(f"(b) controls relation has {len(controls_facts)} typed fact(s), expected 0")
    if social_facts:
        fact = social_facts[0]
        expected = lien_fact_content(
            session.get(Entity, ids["A"]).name, "ally", session.get(Entity, ids["B"]).name,
        )
        if fact.default_level != "unaware":
            fail(f"(b) social fact default_level={fact.default_level!r}, expected 'unaware'")
        # BRIEF-0091-J: the stored content carries identity tokens; the
        # RENDERED text is what equals lien_fact_content(current names).
        rendered = fact_text(session, fact)
        if rendered != expected:
            fail(f"(b) social fact content {rendered!r} != lien_fact_content {expected!r}")
    if connects_facts and connects_facts[0].default_level != "knows":
        fail(f"(b) connects_to fact default_level={connects_facts[0].default_level!r}, expected 'knows'")
    COUNTS["b"] = examined
    if examined == 0:
        fail("(b) vacuous-proof: zero typed facts examined")


def _delta_moves_only(session, world_id, *, perceiver, target, mover, bystander, value) -> None:
    """One delta on (perceiver, target): `mover` (that oriented row) moves
    by `value`, `bystander` (the reverse row) keeps its intensity and
    `change_history` length."""
    from world_engine.writes.relations import write_relation

    session.refresh(mover)
    session.refresh(bystander)
    mover_before = mover.intensity
    by_intensity, by_history = bystander.intensity, len(bystander.change_history or [])
    touched = write_relation(
        session, mode="delta", world_id=world_id, entity_a_id=perceiver,
        entity_b_id=target, type="rival", value=value,
    )
    session.commit()
    session.refresh(mover)
    session.refresh(bystander)
    if touched.id != mover.id:
        fail(f"(c) delta on ({perceiver}, {target}) touched {touched.id}, expected {mover.id}")
    if mover.intensity != mover_before + value:
        fail(f"(c) oriented row intensity {mover.intensity}, expected {mover_before + value}")
    if bystander.intensity != by_intensity or len(bystander.change_history or []) != by_history:
        fail(
            f"(c) reverse row changed by a delta on ({perceiver}, {target}): intensity "
            f"{by_intensity}->{bystander.intensity}, history {by_history}->"
            f"{len(bystander.change_history or [])}"
        )


def check_c_oriented_delta(session, world_id, ids) -> None:
    """Starts from B->C alone: a delta on (C, B) must CREATE the C->B row,
    never move B->C (an order-blind finder would move it). Then, with both
    rows present, a delta in each order moves only its own row."""
    from world_engine.writes.relations import write_relation

    bc = write_relation(
        session, mode="set", world_id=world_id, entity_a_id=ids["B"],
        entity_b_id=ids["C"], type="rival", value=50,
    )
    session.commit()
    bc_history = len(bc.change_history or [])
    cb = write_relation(
        session, mode="delta", world_id=world_id, entity_a_id=ids["C"],
        entity_b_id=ids["B"], type="rival", value=-10,
    )
    session.commit()
    session.refresh(bc)
    if cb.id == bc.id or (cb.entity_a_id, cb.entity_b_id) != (ids["C"], ids["B"]):
        fail("(c) delta on (C, B) with only B->C present did not create the C->B row")
        return
    if bc.intensity != 50 or len(bc.change_history or []) != bc_history:
        fail(f"(c) B->C moved by a delta on (C, B): intensity {bc.intensity}, history {bc.change_history}")
    _delta_moves_only(session, world_id, perceiver=ids["C"], target=ids["B"],
                      mover=cb, bystander=bc, value=-5)
    _delta_moves_only(session, world_id, perceiver=ids["B"], target=ids["C"],
                      mover=bc, bystander=cb, value=5)
    COUNTS["c"] = 2


def check_d_target_knows(session, world_id, ids) -> None:
    from sqlmodel import select

    from world_engine.models import Knowledge
    from world_engine.writes.relations import lien_fact_of, set_target_knows, write_relation

    rel = write_relation(
        session, mode="set", world_id=world_id, entity_a_id=ids["C"],
        entity_b_id=ids["A"], type="admire", value=70,
    )
    session.commit()
    lien = lien_fact_of(session, rel)
    if lien is None:
        fail("(d) no lien fact born for the social relation")
        return

    def _rows():
        return session.exec(
            select(Knowledge).where(Knowledge.entity_id == ids["A"], Knowledge.fact_id == lien.id)
        ).all()

    observed = []
    for knows in (True, True, False, False):
        set_target_knows(session, rel=rel, knows=knows, changed_by="check")
        session.commit()
        observed.append(len(_rows()))
    if observed != [1, 1, 0, 0]:
        fail(f"(d) knowledge row counts after True, True, False, False = {observed}, expected [1, 1, 0, 0]")
    COUNTS["d"] = sum(observed) + len(observed)


def main() -> int:
    engine = _fresh_engine()
    from sqlmodel import Session as DbSession

    with DbSession(engine) as session:
        world_id, ids = _seed(session)
        check_a_orientation_guard(session, world_id, ids)
        check_b_typed_fact_at_birth(session, world_id, ids)
        check_c_oriented_delta(session, world_id, ids)
        check_d_target_knows(session, world_id, ids)

    for key in ("a", "b", "c", "d"):
        if not COUNTS.get(key):
            fail(f"({key}) vacuous-proof: zero rows examined")

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: relation_orientation — "
        f"(a) social direction guard [{COUNTS['a']} writes], "
        f"(b) typed fact at birth [{COUNTS['b']} facts], "
        f"(c) oriented delta [{COUNTS['c']} rows], "
        f"(d) set_target_knows idempotent [{COUNTS['d']} observations]"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
