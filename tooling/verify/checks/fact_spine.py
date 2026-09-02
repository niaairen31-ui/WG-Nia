"""G1 check for TICKET-0082 (BRIEF-0082-b) — the fact spine invariants.

DB-backed, self-contained fresh temp-file SQLite fixture (WORLD_ENGINE_
DATABASE_URL set BEFORE any world_engine import) — same idiom as
door_coverage.py / location_type_classified.py, so this check never touches
Nia's real DB. FAILURES list, print FAIL lines, sys.exit(1); zero rows
collected for any of the three DB assertions is a FAIL, never a vacuous
pass (single_canon_write.py / door_terminal.py idiom) — demonstrated below
by building fixture data through the REAL sanctioned writers
(`writes/facts.py::create_fact`/`attach_participants`,
`writes/knowledge.py::write_knowledge`), breaking one case on purpose to
prove the FAIL path names it, then healing it to prove PASS returns.

Four assertions:
  1. No `fact_participant` row whose `fact` has any typed FK non-NULL.
  2. No `knowledge` row with NULL `fact_id`.
  3. Every `fact.default_level` and every `knowledge.level` value is in the
     six-value vocabulary — read from `writes/knowledge.py`'s
     `KNOWLEDGE_LEVELS`, never a re-typed literal set here.
  4. AST scan: no `db.add(Fact(...))` / `db.add(FactParticipant(...))` /
     `sa_insert` against those tables outside `writes/facts.py`.
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


def _scan_participant_typed_violations(session):
    """(examined, violations) — every fact_participant row, and whether its
    fact carries any typed FK. The query concretely runs every time."""
    from sqlmodel import select

    from world_engine.models import Fact, FactParticipant

    rows = session.exec(
        select(FactParticipant, Fact).join(Fact, Fact.id == FactParticipant.fact_id)
    ).all()
    violations = [
        (p.fact_id, p.entity_id)
        for p, f in rows
        if f.relation_id is not None or f.event_id is not None or f.world_law_id is not None
    ]
    return len(rows), violations


def _scan_null_fact_id(session):
    from sqlmodel import select

    from world_engine.models import Knowledge

    rows = session.exec(select(Knowledge)).all()
    nulls = [k.id for k in rows if not k.fact_id]
    return len(rows), nulls


def _scan_level_vocabulary(session):
    from sqlmodel import select

    from world_engine.models import Fact, Knowledge
    from world_engine.writes.knowledge import KNOWLEDGE_LEVELS

    examined = 0
    violations: list[str] = []
    for f in session.exec(select(Fact)).all():
        examined += 1
        if f.default_level not in KNOWLEDGE_LEVELS:
            violations.append(f"fact {f.id} default_level={f.default_level!r}")
    for k in session.exec(select(Knowledge)).all():
        examined += 1
        if k.level not in KNOWLEDGE_LEVELS:
            violations.append(f"knowledge {k.id} level={k.level!r}")
    return examined, violations


def check_db_fixture(engine) -> None:
    from sqlmodel import Session as DbSession, select

    from world_engine.models import Entity, FactParticipant, Knowledge, World
    from world_engine.writes import attach_participants, create_fact, write_knowledge
    from world_engine.writes.relations import write_relation

    with DbSession(engine) as session:
        world = World(name="Check World", is_active=True)
        session.add(world)
        session.commit()
        session.refresh(world)
        world_id = world.id

        def _npc(name: str) -> str:
            entity = Entity(world_id=world_id, type="character", name=name)
            session.add(entity)
            session.commit()
            session.refresh(entity)
            return entity.id

        a, b, c, d = (_npc(n) for n in ("A", "B", "C", "D"))

        rel = write_relation(
            session, mode="set", world_id=world_id, entity_a_id=a, entity_b_id=b,
            type="ally", value=50, direction="mutual",
        )
        session.commit()
        typed_fact = create_fact(
            session, world_id=world_id, content="A and B are allies",
            created_by="check", relation_id=rel.id,
        )
        session.commit()

        free_fact = create_fact(
            session, world_id=world_id, content="a shared secret", created_by="check",
        )
        session.commit()
        attach_participants(session, fact=free_fact, entity_ids=[a, b, c], role="conspirator")
        session.commit()

        write_knowledge(session, entity_id=d, subject="a shared secret", level="rumor", fact_id=free_fact.id)
        write_knowledge(session, entity_id=d, subject="unrelated gossip", level="knows")
        session.commit()

        # ── Positive: no participant on a typed fact, no NULL fact_id, every level valid ──
        examined_p, violations_p = _scan_participant_typed_violations(session)
        if examined_p == 0:
            fail("vacuous-proof: zero fact_participant rows examined on a freshly seeded fixture")
        if violations_p:
            fail(f"unexpected participant(s) on a typed fact before the deliberate break: {violations_p}")

        examined_k, nulls_k = _scan_null_fact_id(session)
        if examined_k == 0:
            fail("vacuous-proof: zero knowledge rows examined on a freshly seeded fixture")
        if nulls_k:
            fail(f"unexpected NULL knowledge.fact_id before any tampering: {nulls_k}")

        examined_l, violations_l = _scan_level_vocabulary(session)
        if examined_l == 0:
            fail("vacuous-proof: zero fact/knowledge level values examined on a freshly seeded fixture")
        if violations_l:
            fail(f"unexpected out-of-vocabulary level(s) before the deliberate break: {violations_l}")

        # ── Negative: attach a participant to a TYPED fact on purpose (bypassing
        #    attach_participants, which would raise) -> FAILs naming it ──────────
        session.add(FactParticipant(world_id=world_id, fact_id=typed_fact.id, entity_id=c))
        session.commit()
        _, violations_after_break = _scan_participant_typed_violations(session)
        if not any(fid == typed_fact.id for fid, _ in violations_after_break):
            fail(f"a participant attached to a typed fact did not surface as a violation: {violations_after_break}")

        # ── Heal -> green again ──────────────────────────────────────────────────
        bad_row = session.exec(
            select(FactParticipant).where(
                FactParticipant.fact_id == typed_fact.id, FactParticipant.entity_id == c,
            )
        ).first()
        session.delete(bad_row)
        session.commit()
        _, violations_restored = _scan_participant_typed_violations(session)
        if violations_restored:
            fail(f"participant/typed-fact violation still present after healing: {violations_restored}")

        # ── Negative: an out-of-vocabulary knowledge.level (no DB CHECK guards
        #    this column) -> FAILs naming it, then heals ────────────────────────
        gossip = session.exec(
            select(Knowledge).where(Knowledge.entity_id == d, Knowledge.subject == "unrelated gossip")
        ).first()
        gossip.level = "omniscient"
        session.add(gossip)
        session.commit()
        _, violations_level_broken = _scan_level_vocabulary(session)
        if not any(gossip.id in v for v in violations_level_broken):
            fail(f"an out-of-vocabulary knowledge.level did not surface as a violation: {violations_level_broken}")
        gossip.level = "knows"
        session.add(gossip)
        session.commit()
        _, violations_level_restored = _scan_level_vocabulary(session)
        if violations_level_restored:
            fail(f"level-vocabulary violation still present after healing: {violations_level_restored}")


# Relative to SRC (`src/`), matching `path.relative_to(SRC).as_posix()` below.
FACTS_WRITE_FILE = "world_engine/writes/facts.py"


def _var_to_class(tree: ast.Module) -> dict[str, str]:
    """File-wide (not function-scoped — a looser net than
    single_canon_write.py on purpose, defense in depth) map of
    `name = ClassName(...)` assignments, so `db.add(fact)` resolves back to
    `Fact` the same way `db.add(Fact(...))` would."""
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign) and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
        ):
            out[node.targets[0].id] = node.value.func.id
    return out


def _resolve_call_name(node: ast.AST, var_to_class: dict[str, str]):
    """Best-effort literal class name behind an argument: `Fact(...)` ->
    "Fact", a bare `Fact` name, a local variable previously assigned
    `Fact(...)` (via `var_to_class`), or `X.__table__` (the
    `sa_insert(X)` call-shape `entity_runtime.py` uses)."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node, ast.Name):
        return var_to_class.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def check_single_write_chokepoint() -> None:
    """AST scan: every `db.add(Fact(...))` / `db.add(FactParticipant(...))`,
    plus every `sa_insert(Fact)` / `sa_insert(FactParticipant)`-shaped call
    (the `entity_runtime.py::sa_insert(table).values(...)` convention),
    must live in `writes/facts.py`. Vacuous-proof: the two legitimate
    `.add(...)` sites (create_fact, attach_participants) must be found.

    This is a literal-name heuristic, the same class of gap
    single_canon_write.py documents as its R3 blind spot: a write reached
    through a registry/alias/dynamic dispatch defeats both scans
    identically. Nothing in this codebase currently reaches `fact`/
    `fact_participant` through that pattern (grepped: `sa_insert` appears
    only in `entity_runtime.py`, targeting `ext_*` tables) — reported here
    rather than silently trusted as coverage (BRIEF-0082-b STOP condition).
    """
    targets = {"Fact", "FactParticipant"}
    add_sites = 0
    outside: list[str] = []

    for path in sorted(SRC.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            fail(f"{path}: SyntaxError: {exc}")
            continue
        rel = path.relative_to(SRC).as_posix()
        var_to_class = _var_to_class(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Attribute) and node.func.attr == "add":
                for arg in node.args:
                    name = _resolve_call_name(arg, var_to_class)
                    if name in targets:
                        add_sites += 1
                        if rel != FACTS_WRITE_FILE:
                            outside.append(f"{rel}:{node.lineno} — db.add({name}(...))")
            elif isinstance(node.func, ast.Name) and node.func.id == "sa_insert":
                for arg in node.args:
                    name = _resolve_call_name(arg, var_to_class)
                    if name in targets and rel != FACTS_WRITE_FILE:
                        outside.append(f"{rel}:{node.lineno} — sa_insert({name})")

    if add_sites == 0:
        fail("vacuous-proof: zero db.add(Fact(...)/FactParticipant(...)) sites found in src/ — scan is broken, not the repo clean")
    if outside:
        for msg in outside:
            fail(f"fact/fact_participant write site outside {FACTS_WRITE_FILE}: {msg}")


def main() -> int:
    engine = _fresh_engine()
    check_db_fixture(engine)
    check_single_write_chokepoint()

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: fact_spine — no participant on a typed fact, no NULL "
        "knowledge.fact_id, every fact/knowledge level in vocabulary, "
        "and Fact/FactParticipant writes stay inside writes/facts.py"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
