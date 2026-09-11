"""G1 check for TICKET-0084 (BRIEF-0084-c) — `skill_resolution` is
append-only and non-canon.

Three volets:
  1. Static (AST), same `_tracked_names`/attribute-assignment/`db.delete(`
     technique as `day_rewrite.py`'s W2: no assignment anywhere in `src/`
     targets an attribute of a `SkillResolution` instance, and the name
     never appears as the argument of a `db.delete(`.
  2. Static (text): `skill_resolution` is absent from
     `canon_write_policy.txt`'s `[CANON_TABLES]` section.
  3. DB-backed (fresh temp-file SQLite fixture, same idiom as
     `skill_system_shape.py`/`fact_spine.py` — never touches Nia's real
     DB): every row satisfies the shape CHECK (`base` carries `base_domain`
     only, `matched` carries `skill_definition_id` only, `unmatched`
     carries neither).

Vacuous pass (zero SkillResolution construction sites found in `src/` AND
zero rows examined in the fixture) is a FAIL, never a silent pass.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"
POLICY_FILE = ROOT / "tooling" / "verify" / "canon_write_policy.txt"

_TRACKED_MODELS = {"SkillResolution"}

FAILURES: list[str] = []
_TREE_CACHE: dict[pathlib.Path, "ast.Module | None"] = {}


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _parse(path: pathlib.Path) -> "ast.Module | None":
    if path in _TREE_CACHE:
        return _TREE_CACHE[path]
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        fail(f"{_rel(path)}: SyntaxError: {exc}")
        tree = None
    _TREE_CACHE[path] = tree
    return tree


def _all_src_files() -> list[pathlib.Path]:
    return sorted(SRC.rglob("*.py"))


# ── 1. Append-only (AST) ─────────────────────────────────────────────────

def _tracked_names(tree: ast.Module) -> set[str]:
    """Local names bound to a `SkillResolution` instance: a direct
    constructor call, a `db.get(SkillResolution, ...)` read, or a `for`
    target iterating a `select(SkillResolution)`-shaped query result."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            bound = False
            if isinstance(call.func, ast.Name) and call.func.id in _TRACKED_MODELS:
                bound = True
            elif isinstance(call.func, ast.Attribute) and call.func.attr == "get" and call.args:
                first = call.args[0]
                if isinstance(first, ast.Name) and first.id in _TRACKED_MODELS:
                    bound = True
            if bound:
                names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            if any(isinstance(sub, ast.Name) and sub.id in _TRACKED_MODELS for sub in ast.walk(node.iter)):
                names.add(node.target.id)
    return names


def check_append_only() -> bool:
    """Returns whether at least one SkillResolution construction was found."""
    found_construction = False
    for path in _all_src_files():
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _TRACKED_MODELS:
                found_construction = True

        names = _tracked_names(tree)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in targets:
                    if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id in names:
                        fail(
                            f"skill_resolution_append_only: {_rel(path)}:{node.lineno} — attribute "
                            f"assignment on a tracked SkillResolution instance ({t.value.id}.{t.attr} = ...)"
                        )
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "delete":
                for arg in node.args:
                    if isinstance(arg, ast.Name) and (arg.id in _TRACKED_MODELS or arg.id in names):
                        fail(
                            f"skill_resolution_append_only: {_rel(path)}:{node.lineno} — "
                            f"db.delete({arg.id}) on a tracked model/name"
                        )
    return found_construction


# ── 2. Non-canon (text) ──────────────────────────────────────────────────

def check_not_canon_table() -> None:
    if not POLICY_FILE.exists():
        fail(f"{_rel(POLICY_FILE)} not found")
        return
    section = None
    canon_tables: set[str] = set()
    for raw in POLICY_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        if section == "CANON_TABLES":
            canon_tables.update(line.split())
    if not canon_tables:
        fail("vacuous-proof: zero CANON_TABLES collected from canon_write_policy.txt")
        return
    if "skill_resolution" in canon_tables:
        fail("skill_resolution must NOT appear in canon_write_policy.txt's [CANON_TABLES] — it is not canon")


# ── 3. Shape CHECK (DB fixture) ──────────────────────────────────────────

def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    db_path = pathlib.Path(tmp_dir) / "check.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    sys.path.insert(0, str(ROOT / "src"))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]

    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def _shape_ok(verdict: str, base_domain, skill_definition_id) -> bool:
    if verdict == "base":
        return base_domain is not None and skill_definition_id is None
    if verdict == "matched":
        return skill_definition_id is not None and base_domain is None
    if verdict == "unmatched":
        return base_domain is None and skill_definition_id is None
    return False


def check_row_shapes() -> int:
    """Returns the number of rows examined."""
    engine = _fresh_engine()
    from sqlmodel import Session as DbSession, select

    from world_engine.models import Conversation, Entity, SkillDefinition, SkillResolution, World
    from world_engine.models import Session as WorldSession

    with DbSession(engine) as db:
        world = World(name="Check World", is_active=True)
        db.add(world)
        db.commit()
        db.refresh(world)

        session_row = WorldSession(world_id=world.id, number=1)
        db.add(session_row)
        db.commit()
        db.refresh(session_row)

        player = Entity(world_id=world.id, type="character", name="Player")
        db.add(player)
        db.commit()
        db.refresh(player)

        conv = Conversation(world_id=world.id, session_id=session_row.id, player_id=player.id)
        db.add(conv)
        db.commit()
        db.refresh(conv)

        skill_def = SkillDefinition(world_id=world.id, name="Crochetage", base_domain="agility")
        db.add(skill_def)
        db.commit()
        db.refresh(skill_def)

        db.add(SkillResolution(
            world_id=world.id, conversation_id=conv.id,
            surface_form="physical", verdict="base", base_domain="physical",
        ))
        db.add(SkillResolution(
            world_id=world.id, conversation_id=conv.id,
            surface_form="Crochetage", verdict="matched", skill_definition_id=skill_def.id,
        ))
        db.add(SkillResolution(
            world_id=world.id, conversation_id=conv.id,
            surface_form="voler", verdict="unmatched",
        ))
        db.commit()

        rows = db.exec(select(SkillResolution)).all()

    examined = 0
    for row in rows:
        examined += 1
        if not _shape_ok(row.verdict, row.base_domain, row.skill_definition_id):
            fail(
                f"skill_resolution_append_only: row {row.id} violates the shape CHECK "
                f"(verdict={row.verdict!r}, base_domain={row.base_domain!r}, "
                f"skill_definition_id={row.skill_definition_id!r})"
            )
    return examined


def main() -> int:
    found_construction = check_append_only()
    check_not_canon_table()
    examined_rows = check_row_shapes()

    if not found_construction and examined_rows == 0:
        fail(
            "vacuous-proof: zero SkillResolution construction sites in src/ AND "
            "zero rows examined — the check tested nothing"
        )

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: skill_resolution_append_only — no update/delete site targets "
        "skill_resolution, it is absent from [CANON_TABLES], and every "
        "examined row satisfies the shape CHECK"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
