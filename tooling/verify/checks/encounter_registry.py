"""G1 check: the encounter registry (TICKET-0091, BRIEF-0091-C, gate (e)).

`rencontre` is non-canon bookkeeping with exactly one writer
(`src/world_engine/encounters.py`), never updated, never deleted, fed by
every live encounter site. Four rules:

R1 (AST) -- no `Rencontre(` call anywhere under `src/` or `scripts/`
   outside `src/world_engine/encounters.py` and
   `scripts/apply_ticket_0091_encounters.py`.
R2 -- no mutation of an existing row: the text `UPDATE rencontre` /
   `DELETE FROM rencontre` (case-insensitive) appears nowhere in `src/`;
   no SQLAlchemy `update(Rencontre ...)` / `delete(Rencontre ...)` call
   anywhere in `src/`; and `encounters.py` itself calls no `.delete(`,
   `.merge(` nor `update(`. (A blanket `.delete(` ban over `src/` would hit
   every sanctioned hard delete; the ban is scoped to the one table.)
R3 (AST) -- each named live function calls one of `record_encounter`,
   `record_encounters_among`, `record_gathering_join`, directly or through
   a helper defined in the same module (transitive within that module, so
   a function kept under the 80-line ceiling by a helper still counts).
R4 (fixture, temp SQLite) -- idempotent pair (either order), self pair
   ignored, invalid source refused, `acquaintances`/`have_met` agree; a
   social relation A->B then B->A yields one row; two NPC schedules at the
   same `(location, phase)` yield one row.

A named file or function missing from disk is a FAILURE; zero rows
examined in R4 is a FAILURE (vacuous-proof guard).
"""
from __future__ import annotations

import ast
import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
PKG = SRC / "world_engine"
SCRIPTS = ROOT / "scripts"

WRITER = PKG / "encounters.py"
BACKFILL = SCRIPTS / "apply_ticket_0091_encounters.py"
RECORDERS = {"record_encounter", "record_encounters_among", "record_gathering_join"}

# (module path relative to the package, function name)
LIVE_SITES = (
    ("cockpit/routes/scene.py", "enter_scene"),
    ("gathering.py", "generate_gatherings"),
    ("gathering.py", "migrate_npc"),
    ("cockpit/play.py", "_join_gathering"),
    ("cockpit/routes/play.py", "start_conversation"),
    ("writes/config.py", "write_npc_schedule"),
    ("writes/relations.py", "_on_relation_born"),
)

FAILURES: list[str] = []
COUNTS: dict[str, int] = {}


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _parse(path: pathlib.Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        fail(f"cannot parse {path.relative_to(ROOT)}: {exc}")
        return None


def _py_files() -> list[pathlib.Path]:
    return sorted(SRC.rglob("*.py")) + sorted(SCRIPTS.rglob("*.py"))


def rule_r1() -> None:
    allowed = {WRITER.resolve(), BACKFILL.resolve()}
    scanned = 0
    for path in _py_files():
        tree = _parse(path)
        if tree is None:
            continue
        scanned += 1
        if path.resolve() in allowed:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _call_name(node) == "Rencontre":
                fail(f"R1 {path.relative_to(ROOT)}:{node.lineno} constructs Rencontre outside the writer")
    COUNTS["r1"] = scanned


_SQL_MUTATION = re.compile(r"\b(UPDATE\s+rencontre|DELETE\s+FROM\s+rencontre)\b", re.IGNORECASE)


def rule_r2() -> None:
    scanned = 0
    for path in sorted(SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        scanned += 1
        for m in _SQL_MUTATION.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            fail(f"R2 {path.relative_to(ROOT)}:{line} mutates rencontre via SQL ({m.group(0)!r})")
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node)
            if name in ("update", "delete") and any(
                isinstance(a, ast.Name) and a.id == "Rencontre" for a in node.args
            ):
                fail(f"R2 {path.relative_to(ROOT)}:{node.lineno} {name}(Rencontre) call")
            if path.resolve() == WRITER.resolve() and name in ("delete", "merge", "update"):
                fail(f"R2 encounters.py:{node.lineno} calls .{name}(")
    if not WRITER.exists():
        fail("R2 src/world_engine/encounters.py is missing")
    COUNTS["r2"] = scanned


def _module_functions(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    return {
        n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _reaches_recorder(fn_name: str, funcs: dict[str, ast.FunctionDef]) -> bool:
    seen: set[str] = set()
    stack = [fn_name]
    while stack:
        name = stack.pop()
        if name in seen or name not in funcs:
            continue
        seen.add(name)
        for node in ast.walk(funcs[name]):
            if isinstance(node, ast.Call):
                called = _call_name(node)
                if called in RECORDERS:
                    return True
                if isinstance(node.func, ast.Name) and called in funcs:
                    stack.append(called)
    return False


def rule_r3() -> None:
    checked = 0
    for rel, fn in LIVE_SITES:
        path = PKG / rel
        if not path.exists():
            fail(f"R3 {rel} is missing")
            continue
        tree = _parse(path)
        if tree is None:
            continue
        funcs = _module_functions(tree)
        if fn not in funcs:
            fail(f"R3 {rel}::{fn} is missing")
            continue
        checked += 1
        if not _reaches_recorder(fn, funcs):
            fail(f"R3 {rel}::{fn} records no encounter")
    COUNTS["r3"] = checked


def _fresh_engine():
    db_path = pathlib.Path(tempfile.mkdtemp()) / "check.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def _seed(session):
    from world_engine.models import Entity, World

    world = World(name="Check World", is_active=True)
    session.add(world)
    session.commit()
    session.refresh(world)
    ids: dict[str, str] = {}
    for label, etype in (("A", "character"), ("B", "character"), ("C", "character"),
                         ("D", "character"), ("L", "location")):
        entity = Entity(world_id=world.id, type=etype, name=f"Entity {label}")
        session.add(entity)
        session.commit()
        session.refresh(entity)
        ids[label] = entity.id
    return world.id, ids


def _pair_rows(session, a_id: str, b_id: str) -> int:
    from sqlmodel import select

    from world_engine.models import Rencontre

    lo, hi = sorted((a_id, b_id))
    return len(session.exec(
        select(Rencontre).where(Rencontre.entity_lo_id == lo, Rencontre.entity_hi_id == hi)
    ).all())


def _fixture_writer(session, world_id, ids) -> int:
    from world_engine.encounters import (
        acquaintances, have_met, record_encounter, record_encounters_among,
    )

    observed = 0
    first = record_encounter(session, world_id=world_id, a_id=ids["A"], b_id=ids["B"], source="visit")
    again = record_encounter(session, world_id=world_id, a_id=ids["B"], b_id=ids["A"], source="conversation")
    selfp = record_encounter(session, world_id=world_id, a_id=ids["A"], b_id=ids["A"], source="visit")
    session.commit()
    if first is None:
        fail("R4 first encounter of {A, B} created no row")
    if again is not None:
        fail("R4 reversed repeat of {A, B} created a second row")
    if selfp is not None:
        fail("R4 self pair created a row")
    if _pair_rows(session, ids["A"], ids["B"]) != 1:
        fail("R4 {A, B} does not have exactly one row")
    if first is not None and first.source != "visit":
        fail(f"R4 earliest source not kept: {first.source!r}")
    try:
        record_encounter(session, world_id=world_id, a_id=ids["A"], b_id=ids["C"], source="bogus")
    except ValueError:
        session.rollback()
    else:
        session.rollback()
        fail("R4 invalid source was accepted")
    made = record_encounters_among(
        session, world_id=world_id, entity_ids=[ids["A"], ids["B"], ids["C"], ids["C"]],
        source="gathering",
    )
    session.commit()
    if made != 2:
        fail(f"R4 record_encounters_among over {{A, B, C}} made {made} rows, expected 2")
    if acquaintances(session, ids["A"]) != {ids["B"], ids["C"]}:
        fail("R4 acquaintances(A) != {B, C}")
    if not have_met(session, ids["C"], ids["B"]) or have_met(session, ids["A"], ids["D"]):
        fail("R4 have_met disagrees with the registry")
    observed += 5
    return observed


def _fixture_relation(session, world_id, ids) -> int:
    from world_engine.writes.relations import write_relation

    for a, b in (("A", "D"), ("D", "A")):
        write_relation(
            session, mode="set", world_id=world_id, entity_a_id=ids[a],
            entity_b_id=ids[b], type="ally", value=60,
        )
        session.commit()
    rows = _pair_rows(session, ids["A"], ids["D"])
    if rows != 1:
        fail(f"R4 social relation A->D then D->A left {rows} rencontre rows, expected 1")
    return 2


def _fixture_schedule(session, world_id, ids) -> int:
    from world_engine.writes.config import write_npc_schedule

    slot = [{"phase": "soir", "location_id": ids["L"]}]
    for npc in ("B", "D"):
        for row in write_npc_schedule(
            session, world_id=world_id, npc_id=ids[npc], rows=slot, changed_by="check",
        ):
            session.add(row)
        session.commit()
    rows = _pair_rows(session, ids["B"], ids["D"])
    if rows != 1:
        fail(f"R4 two schedules at one (location, phase) left {rows} rows, expected 1")
    return 2


def rule_r4() -> None:
    engine = _fresh_engine()
    from sqlmodel import Session as DbSession

    with DbSession(engine) as session:
        world_id, ids = _seed(session)
        COUNTS["r4"] = (
            _fixture_writer(session, world_id, ids)
            + _fixture_relation(session, world_id, ids)
            + _fixture_schedule(session, world_id, ids)
        )


def main() -> int:
    rule_r1()
    rule_r2()
    rule_r3()
    rule_r4()
    for key in ("r1", "r2", "r3", "r4"):
        if not COUNTS.get(key):
            fail(f"({key}) vacuous-proof: zero items examined")
    if COUNTS.get("r3") is not None and COUNTS["r3"] != len(LIVE_SITES):
        fail(f"R3 examined {COUNTS['r3']} of {len(LIVE_SITES)} live sites")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: encounter_registry — "
        f"R1 single constructor [{COUNTS['r1']} files], "
        f"R2 no update/delete [{COUNTS['r2']} files], "
        f"R3 live sites record [{COUNTS['r3']} functions], "
        f"R4 fixture [{COUNTS['r4']} observations]"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
