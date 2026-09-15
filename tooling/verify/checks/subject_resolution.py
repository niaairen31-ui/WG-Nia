"""G1 check for TICKET-0087 (BRIEF-0087-b) — the `subject_entity_id`
validation chokepoint on the `new_knowledge` apply path.

Same idioms as `fact_spine.py`: AST scans for the purity assertions (no
model call, no direct DB write inside the resolver); a fresh temp-file
SQLite fixture (`WORLD_ENGINE_DATABASE_URL` set BEFORE any `world_engine`
import) built through the REAL sanctioned appliers
(`cockpit/mutations.py::_mutation_apply_new_knowledge`,
`writes/knowledge.py::write_knowledge`) for the behavioural assertions —
this check never touches Nia's real DB. `FAILURES` list, print FAIL lines,
`sys.exit(1)`; every assertion below always collects at least one concrete
item before judging it — never a silent, vacuous pass.

Four assertions:
  A1 (AST, purity): `subject_resolve.py` contains no `chat(` call and no
     `db.add(`.
  A2 (AST, no re-implemented rung): `subject_resolve.py` reaches canon
     ONLY through `lore_resolve.resolve_named` — every `select(` found
     directly in the module (there should be none; C-01/BRIEF-0087-a's
     contract is that it delegates every candidate lookup rather than
     querying itself) must be world-constrained among its `.where(`
     arguments, in the shape `lore_isolation.py`'s R2 already uses for
     `lore_selectors.py`. When — as the current, correct state — zero
     `select(` calls exist, the module must instead show at least one call
     to `resolve_named(` and zero `db.exec(`/`text(` calls, so the
     assertion always has something concrete to point at rather than
     trusting an empty scan.
  A3 (behavioural, refusal): a `subject_entity_id` naming an active entity
     of a DIFFERENT world is refused at apply — a non-`None` error string,
     zero `fact_participant` rows written. Healed with an in-world id:
     exactly one `fact_participant` row, `role IS NULL`, return `None`.
  A4 (behavioural, idempotency): the same in-world `subject_entity_id`
     attached to the same fact twice (via `write_knowledge`'s own
     `fact_id` re-entry path, the same chokepoint
     `_mutation_apply_new_knowledge` calls into) yields exactly one
     `fact_participant` row.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
SUBJECT_RESOLVE_FILE = SRC / "world_engine" / "subject_resolve.py"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _parse(path: pathlib.Path) -> "ast.Module | None":
    if not path.exists():
        fail(f"{_rel(path)}: file not found")
        return None
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        fail(f"{_rel(path)}: SyntaxError: {exc}")
        return None


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


def check_a1_purity() -> None:
    tree = _parse(SUBJECT_RESOLVE_FILE)
    if tree is None:
        return
    hits: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute) and func.attr == "add"
            and isinstance(func.value, ast.Name) and func.value.id == "db"
        ):
            hits.add("db.add(")
        elif isinstance(func, ast.Name) and func.id == "chat":
            hits.add("chat(")
    if hits:
        fail(
            f"subject_resolution A1: {_rel(SUBJECT_RESOLVE_FILE)} contains "
            f"forbidden call(s) {sorted(hits)!r} — must stay pure and read-only"
        )


def check_a2_no_reimplemented_rung() -> None:
    tree = _parse(SUBJECT_RESOLVE_FILE)
    if tree is None:
        return
    select_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "select"
    ]

    if select_calls:
        for node in select_calls:
            where_call = None
            for parent in ast.walk(tree):
                if not isinstance(parent, ast.Call):
                    continue
                if not (isinstance(parent.func, ast.Attribute) and parent.func.attr == "where"):
                    continue
                if any(sub is node for sub in ast.walk(parent.func.value)):
                    where_call = parent
                    break
            if where_call is None:
                fail(
                    f"subject_resolution A2: {_rel(SUBJECT_RESOLVE_FILE)}:{node.lineno} "
                    "— select( with no .where( call"
                )
                continue
            names_in_where = {
                sub.id if isinstance(sub, ast.Name) else sub.attr
                for sub in ast.walk(where_call)
                if isinstance(sub, (ast.Name, ast.Attribute))
            }
            if "world_id" not in names_in_where and "Entity" not in names_in_where:
                fail(
                    f"subject_resolution A2: {_rel(SUBJECT_RESOLVE_FILE)}:{node.lineno} — "
                    "select(...).where(...) references neither world_id nor a join to "
                    "Entity — not world-scoped at construction"
                )
        return

    # The correct, current state: subject_resolve.py re-implements no rung of
    # its own — it never calls select( directly at all. Assert THAT
    # concretely (at least one resolve_named( call, zero raw db.exec(/text(
    # bypasses) rather than treating an empty select( scan as a silent pass.
    resolve_named_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "resolve_named"
    ]
    if not resolve_named_calls:
        fail(
            f"subject_resolution A2: {_rel(SUBJECT_RESOLVE_FILE)} contains zero select( "
            "and zero resolve_named( calls — vacuous, the resolver reaches canon through neither path"
        )
    bypass_hits: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute) and func.attr == "exec"
            and isinstance(func.value, ast.Name) and func.value.id == "db"
        ):
            bypass_hits.add("db.exec(")
        elif isinstance(func, ast.Name) and func.id == "text":
            bypass_hits.add("text(")
    if bypass_hits:
        fail(
            f"subject_resolution A2: {_rel(SUBJECT_RESOLVE_FILE)} reaches canon through "
            f"{sorted(bypass_hits)!r} instead of lore_resolve.resolve_named — a re-implemented rung"
        )


def check_behavioural(engine) -> None:
    from sqlmodel import Session as DbSession, select

    from world_engine.cockpit.mutations import _mutation_apply_new_knowledge
    from world_engine.models import Entity, FactParticipant, ProposedMutation, World
    from world_engine.writes import write_knowledge

    with DbSession(engine) as session:
        world_a = World(name="World A", is_active=True)
        world_b = World(name="World B", is_active=False)
        session.add(world_a)
        session.add(world_b)
        session.commit()
        session.refresh(world_a)
        session.refresh(world_b)

        def _npc(world_id: str, name: str) -> str:
            entity = Entity(world_id=world_id, type="character", name=name)
            session.add(entity)
            session.commit()
            session.refresh(entity)
            return entity.id

        learner = _npc(world_a.id, "Learner")
        subject_in_world = _npc(world_a.id, "Maelis")
        subject_other_world = _npc(world_b.id, "Outsider")

        mut = ProposedMutation(
            world_id=world_a.id, source_type="conversation",
            mutation_type="new_knowledge", payload={}, status="proposed",
            proposed_by="check",
        )
        session.add(mut)
        session.commit()
        session.refresh(mut)

        # ── A3, negative: a subject_entity_id from a DIFFERENT world is refused,
        #    nothing written ─────────────────────────────────────────────────
        payload_cross_world = {
            "entity_id": learner, "subject": "s", "content": "c",
            "subject_entity_id": subject_other_world,
        }
        err = _mutation_apply_new_knowledge(mut, payload_cross_world, session)
        session.commit()
        if err is None:
            fail("subject_resolution A3: a subject_entity_id naming an entity of a DIFFERENT world was not refused")
        fp_after_refusal = session.exec(select(FactParticipant)).all()
        if fp_after_refusal:
            fail(
                f"subject_resolution A3: a refused subject_entity_id still wrote "
                f"{len(fp_after_refusal)} fact_participant row(s)"
            )

        # ── A3, heal: an in-world id applies, one participant, role NULL ────────
        payload_in_world = {
            "entity_id": learner, "subject": "s", "content": "c",
            "subject_entity_id": subject_in_world,
        }
        err2 = _mutation_apply_new_knowledge(mut, payload_in_world, session)
        session.commit()
        if err2 is not None:
            fail(f"subject_resolution A3: an in-world subject_entity_id was refused: {err2!r}")
        fps = session.exec(select(FactParticipant)).all()
        if len(fps) != 1:
            fail(f"subject_resolution A3: healed apply produced {len(fps)} fact_participant row(s), expected 1")
        else:
            if fps[0].entity_id != subject_in_world:
                fail(f"subject_resolution A3: fact_participant.entity_id={fps[0].entity_id!r}, expected {subject_in_world!r}")
            if fps[0].role is not None:
                fail(f"subject_resolution A3: fact_participant.role={fps[0].role!r}, expected NULL")

        # ── A4, idempotency: the same in-world id attached to the SAME fact a
        #    second time (a second knower on the same fact, R-03's shape) still
        #    yields exactly one participant row ────────────────────────────────
        fact_id = fps[0].fact_id
        second_learner = _npc(world_a.id, "Second Learner")
        write_knowledge(
            session, entity_id=second_learner, subject="s", fact_id=fact_id,
            subject_entity_ids=[subject_in_world],
        )
        session.commit()
        fps_after_second = session.exec(
            select(FactParticipant).where(FactParticipant.fact_id == fact_id)
        ).all()
        if len(fps_after_second) != 1:
            fail(
                f"subject_resolution A4: re-attaching the same subject_entity_id to the "
                f"same fact produced {len(fps_after_second)} fact_participant row(s), expected 1"
            )


def main() -> int:
    check_a1_purity()
    check_a2_no_reimplemented_rung()
    engine = _fresh_engine()
    check_behavioural(engine)

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: subject_resolution — subject_resolve.py stays pure and "
        "re-implements no rung; _mutation_apply_new_knowledge refuses a "
        "cross-world subject_entity_id and writes nothing, applies an "
        "in-world one idempotently"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
