"""G1 check for TICKET-0051 (BRIEF-0051-b, decision E2) — the worst-case-
listener disclosure floor in `assemble_npc_context`.

Uses a fresh temp-file SQLite DB (WORLD_ENGINE_DATABASE_URL set before any
world_engine import) so this check never touches Nia's real DB.

Fixture: NPC A, auditors B (trusted, intensity 80) and C (distrusted,
intensity 10), a knowledge row on A with share_threshold 50, interlocutor = B.

1. Rule 1 (behavioural): the fact is disclosed with audience_ids=[B] (floor
   = 80 >= 50) and withheld with audience_ids=[B, C] (floor = min(80, 10)
   = 10 < 50). This asserts the floor itself, not merely that a parameter
   exists.
2. Rule 2: `audience_ids=[]` raises ValueError — an empty audience is a
   caller bug, never "disclose freely".
3. Rule 3 (regression): `audience_ids=None` and `audience_ids=[B]` (B is
   also the interlocutor here) produce byte-identical output — the
   single-auditor case is unchanged by construction.
4. Rule 4 (AST): `_npc_context_perception` is never called with the
   disclosure intensity — the two values stay unconflated downstream.
5. Rule 5 (vacuous-proof guard): fail if the fixture produced zero
   knowledge rows, or if the "disclosed" context is empty — a rule that
   passes because nothing was disclosed is not a passing rule.
"""
from __future__ import annotations

import ast
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
    """Point WORLD_ENGINE_DATABASE_URL at a fresh temp SQLite file BEFORE
    importing world_engine.db (module-level engine) — isolates this check
    from the real DB and from any other check already imported in-process."""
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


def _seed_fixture(engine):
    """NPC A with a knowledge row (share_threshold=50), auditor B (A->B
    intensity 80) and auditor C (A->C intensity 10), one location."""
    from sqlmodel import Session as DbSession

    from world_engine.models import (
        Character,
        Entity,
        Knowledge,
        Location,
        Relation,
        World,
    )

    with DbSession(engine) as session:
        world = World(name="Check World", is_active=True)
        session.add(world)
        session.commit()
        session.refresh(world)

        loc_entity = Entity(world_id=world.id, type="location", name="Loc")
        session.add(loc_entity)
        session.commit()
        session.refresh(loc_entity)
        session.add(Location(id=loc_entity.id))
        session.commit()

        def _make_npc(name: str) -> str:
            entity = Entity(world_id=world.id, type="character", name=name)
            session.add(entity)
            session.commit()
            session.refresh(entity)
            session.add(Character(
                id=entity.id, world_id=world.id, character_type="npc",
                current_location_id=loc_entity.id,
            ))
            session.commit()
            return entity.id

        a_id = _make_npc("A")
        b_id = _make_npc("B")
        c_id = _make_npc("C")

        session.add(Relation(
            world_id=world.id, entity_a_id=a_id, entity_b_id=b_id,
            type="friendship", direction="a_to_b", intensity=80,
        ))
        session.add(Relation(
            world_id=world.id, entity_a_id=a_id, entity_b_id=c_id,
            type="friendship", direction="a_to_b", intensity=10,
        ))
        session.commit()

        session.add(Knowledge(
            entity_id=a_id, subject="the plan", level="knows",
            content="Le plan se met en place demain.",
            is_secret=False, share_threshold=50,
        ))
        session.commit()

        return {
            "location_id": loc_entity.id,
            "a_id": a_id,
            "b_id": b_id,
            "c_id": c_id,
        }


def check_disclosure_floor() -> None:
    engine = _fresh_engine()
    fixture = _seed_fixture(engine)

    from sqlmodel import Session as DbSession

    from world_engine.context import assemble_npc_context

    with DbSession(engine) as session:
        disclosed = assemble_npc_context(
            fixture["a_id"], fixture["b_id"], fixture["location_id"], session,
            audience_ids=[fixture["b_id"]],
        )
        withheld = assemble_npc_context(
            fixture["a_id"], fixture["b_id"], fixture["location_id"], session,
            audience_ids=[fixture["b_id"], fixture["c_id"]],
        )

    if "plan se met en place" not in disclosed:
        fail("Rule 1: fact absent with audience_ids=[B] (trusted-only audience) — floor not applied correctly")
    if "plan se met en place" in withheld:
        fail("Rule 1: fact present with audience_ids=[B, C] — the distrusted bystander C did not gate disclosure")

    # ── Rule 5: vacuous-proof guard ──────────────────────────────────────
    with DbSession(engine) as session:
        from sqlmodel import select

        from world_engine.models import Knowledge
        knowledge_count = len(session.exec(
            select(Knowledge).where(Knowledge.entity_id == fixture["a_id"])
        ).all())
    if knowledge_count == 0:
        fail("Rule 5: fixture produced zero knowledge rows — vacuous fixture")
    if not disclosed.strip():
        fail("Rule 5: the 'disclosed' context is empty — vacuous fixture")

    # ── Rule 2: empty audience raises ────────────────────────────────────
    with DbSession(engine) as session:
        try:
            assemble_npc_context(
                fixture["a_id"], fixture["b_id"], fixture["location_id"], session,
                audience_ids=[],
            )
            fail("Rule 2: audience_ids=[] did not raise ValueError")
        except ValueError:
            pass

    # ── Rule 3: None vs [interlocutor] regression ────────────────────────
    with DbSession(engine) as session:
        via_none = assemble_npc_context(
            fixture["a_id"], fixture["b_id"], fixture["location_id"], session,
            audience_ids=None,
        )
        via_single = assemble_npc_context(
            fixture["a_id"], fixture["b_id"], fixture["location_id"], session,
            audience_ids=[fixture["b_id"]],
        )
    if via_none != via_single:
        fail("Rule 3: audience_ids=None and audience_ids=[interlocutor] are not byte-identical — regression")


def check_perception_never_conflated() -> None:
    """Rule 4 (AST): `_npc_context_perception` is called with `inter_intensity`,
    never with `disclosure_intensity` — the two values are not re-conflated
    downstream of the split."""
    tree = ast.parse((SRC / "world_engine" / "context.py").read_text(encoding="utf-8"))
    func = next(
        (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "assemble_npc_context"),
        None,
    )
    if func is None:
        fail("Rule 4: assemble_npc_context not found in context.py")
        return

    call = next(
        (
            n for n in ast.walk(func)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "_npc_context_perception"
        ),
        None,
    )
    if call is None:
        fail("Rule 4: no call to _npc_context_perception found in assemble_npc_context")
        return

    arg_names = {a.id for a in call.args if isinstance(a, ast.Name)}
    if "disclosure_intensity" in arg_names:
        fail("Rule 4: _npc_context_perception was called with disclosure_intensity — perception must stay keyed on the addressee")
    if "inter_intensity" not in arg_names:
        fail("Rule 4: _npc_context_perception was not called with inter_intensity — unexpected signature drift")


def main() -> int:
    check_disclosure_floor()
    check_perception_never_conflated()

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: context_disclosure_floor — worst-case-listener floor gates "
        "disclosure, perception stays keyed on the addressee, empty audience "
        "raises, single-auditor case is byte-identical to pre-v1.90"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
