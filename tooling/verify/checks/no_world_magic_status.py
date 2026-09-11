"""G1 check for TICKET-0084 (BRIEF-0084-e) — `world.magic_status` is gone.

`world.magic_status` was removed in schema v2.03: it had no reader, no
creator surface, and one writer (`scripts/seed_pilot.py`); `skill_system`
row presence now answers "does magic exist here" (B3, TICKET-0084).
`location.magic_status` is NOT touched by that decision and remains
legitimate — so every assertion here is paired with a twin assertion that
the location counterpart is untouched, proving the check discriminates
rather than just matching the bare string "magic_status" (a check that
cannot discriminate is worse than no check; a pass with zero paired
evidence is a vacuous pass, treated as FAIL).

Three assertions:
  1. The `World` model (canon.py) carries no `magic_status` column in a
     freshly built schema — and `Location` still does.
  2. The `CREATE TABLE world (...)` block of `world-engine-schema.md` does
     not mention `magic_status` — and the `CREATE TABLE location (...)`
     block still does.
  3. No AST-visible construction of `World` — a literal `World(...)` call,
     or the `get_or_create(session, m.World, id, **kwargs)` idiom used by
     the seed scripts — passes a `magic_status` keyword, anywhere under
     `src/` or `scripts/`.
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
SCHEMA_DOC = ROOT / "world-engine-schema.md"

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


def _check_model_columns(inspector) -> None:
    world_cols = {c["name"] for c in inspector.get_columns("world")}
    location_cols = {c["name"] for c in inspector.get_columns("location")}
    if not world_cols:
        fail("vacuous-proof: zero columns collected on world — table missing or check is broken")
        return
    if not location_cols:
        fail("vacuous-proof: zero columns collected on location — table missing or check is broken")
        return
    if "magic_status" in world_cols:
        fail("world model still carries a magic_status column")
    if "magic_status" not in location_cols:
        fail(
            "discrimination check failed: location.magic_status is gone too — "
            "this step must not touch it, only world.magic_status"
        )


def _extract_create_table_block(text: str, table: str) -> str | None:
    match = re.search(rf"CREATE TABLE {table} \((.*?)\n\);", text, re.DOTALL)
    return match.group(1) if match else None


def _check_schema_doc() -> None:
    if not SCHEMA_DOC.exists():
        fail(f"vacuous-proof: schema doc not found at {SCHEMA_DOC}")
        return
    text = SCHEMA_DOC.read_text(encoding="utf-8")

    world_block = _extract_create_table_block(text, "world")
    if world_block is None:
        fail("vacuous-proof: could not locate CREATE TABLE world block in schema doc")
        return
    if "magic_status" in world_block:
        fail("world-engine-schema.md still lists magic_status inside the CREATE TABLE world block")

    location_block = _extract_create_table_block(text, "location")
    if location_block is None:
        fail("vacuous-proof: could not locate CREATE TABLE location block in schema doc")
        return
    if "magic_status" not in location_block:
        fail(
            "discrimination check failed: CREATE TABLE location block lost "
            "magic_status too — this step must not touch it"
        )


def _call_target_name(func: ast.expr) -> str | None:
    """Resolve a Call's func to a bare identifier — 'World' for both
    World(...) and m.World / models.World attribute forms."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _positional_target_name(node: ast.expr) -> str | None:
    """Resolve a bare positional argument like `m.World` / `models.World` /
    `World` (the get_or_create(session, model, id, **fields) idiom)."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _check_constructions() -> None:
    py_files = sorted(SRC.rglob("*.py")) + sorted((ROOT / "scripts").rglob("*.py"))
    if not py_files:
        fail("vacuous-proof: zero .py files scanned under src/ or scripts/")
        return

    examined_calls = 0
    for path in py_files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            target = _call_target_name(node.func)
            offending_kwargs = None

            if target == "World":
                examined_calls += 1
                offending_kwargs = node.keywords
            elif target == "get_or_create" and len(node.args) >= 2 and _positional_target_name(node.args[1]) == "World":
                examined_calls += 1
                offending_kwargs = node.keywords

            if offending_kwargs is None:
                continue
            for kw in offending_kwargs:
                if kw.arg == "magic_status":
                    fail(
                        f"{path.relative_to(ROOT)}:{node.lineno} constructs World(...) "
                        "with a magic_status keyword"
                    )

    if examined_calls == 0:
        fail(
            "vacuous-proof: zero World construction call sites found under src/ or "
            "scripts/ — expected at least one (creator.py's POST /api/worlds)"
        )


def main() -> int:
    engine = _fresh_engine()
    from sqlalchemy import inspect

    inspector = inspect(engine)

    _check_model_columns(inspector)
    _check_schema_doc()
    _check_constructions()

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: no_world_magic_status — world.magic_status is absent from the "
        "model, the schema doc, and every World construction site, while "
        "location.magic_status remains untouched"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
