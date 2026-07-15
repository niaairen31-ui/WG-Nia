"""G1 checks for TICKET-0011 (BRIEF-0011-a) — prompt_version table, single
read accessor, single write shape, versioned edit API.

No live Ollama required, no HTTP layer required (crud.py route functions are
called directly with an explicit `db` session — avoids depending on
`fastapi.testclient`/`httpx`, which is not guaranteed installed here).

Uses a fresh temp-file SQLite DB (WORLD_ENGINE_DATABASE_URL set before any
world_engine import) so this check never touches Nia's real DB.

1. Schema: `prompt_version` exists with UNIQUE(prompt_template_id,
   version_number); `prompt_template` no longer has system_prompt /
   user_template / version columns.
2. Static scan: `PromptVersion` (the class) is imported/referenced only in
   models.py, prompt_store.py, writes/prompts.py, and the migration script.
3. Static scan: raw SQL referencing the `prompt_version` table (inside a
   `text(...)` call) appears only in models.py's `__tablename__` and the
   migration script.
4. Static scan: no `Session.add(PromptVersion(...))` outside
   writes/prompts.py::write_prompt_version (the migration script uses raw
   SQL, not the ORM class, so it never triggers this pattern in the first
   place).
5. Static scan: no UPDATE/DELETE SQL statement ever targets `prompt_version`
   anywhere (append-only by construction) — no allowlist, this must be
   universally true.
6. Static scan (H1): no `.format(` call on a `user_template`/`system_prompt`
   attribute anywhere under src/.
7. Live: `write_prompt_version` computes version_number = MAX+1; C1
   fail-closed on an undeclared placeholder (nothing written); the PATCH
   text route (crud.update_prompt_text) returns 422 and leaves the version
   list unchanged; a valid PATCH appends a new version.
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
MIGRATION = ROOT / "scripts" / "migrate_v1_68_prompt_version.py"

# Files allowed to reference the PromptVersion class / prompt_version table.
# `writes.py` -> `writes/prompts.py` (TICKET-0028, BRIEF-0028-b): anchor
# relocated, assertions unchanged (relocation-not-broadening precedent).
ALLOWED_FILES = {
    (SRC / "world_engine" / "models.py").resolve(),
    (SRC / "world_engine" / "prompt_store.py").resolve(),
    (SRC / "world_engine" / "writes" / "prompts.py").resolve(),
    MIGRATION.resolve(),
}

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


# ── Static scans ─────────────────────────────────────────────────────────

def _iter_py_files():
    yield from sorted(SRC.rglob("*.py"))
    if MIGRATION.exists():
        yield MIGRATION


def _render_sql_text(node):
    """Best-effort flatten of a string/f-string AST node to text."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant):
                parts.append(str(v.value))
            else:
                parts.append("")  # dynamic piece — ignored for keyword matching
        return "".join(parts)
    return None


def check_class_reference_allowlist() -> None:
    for path in _iter_py_files():
        resolved = path.resolve()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            fail(f"{path}: SyntaxError: {exc}")
            continue
        for node in ast.walk(tree):
            hit = None
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "PromptVersion":
                        hit = node.lineno
            elif isinstance(node, ast.Name) and node.id == "PromptVersion":
                hit = node.lineno
            elif isinstance(node, ast.Attribute) and node.attr == "PromptVersion":
                hit = node.lineno
            if hit is not None and resolved not in ALLOWED_FILES:
                fail(f"{path}:{hit} references PromptVersion outside the allowlist")


def check_sql_table_reference_allowlist() -> None:
    """Raw SQL naming the `prompt_version` table, inside a `text(...)` call,
    only where allowlisted."""
    for path in _iter_py_files():
        resolved = path.resolve()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "text"):
                continue
            if not node.args:
                continue
            rendered = _render_sql_text(node.args[0])
            if rendered and re.search(r"\bprompt_version\b", rendered) and resolved not in ALLOWED_FILES:
                fail(f"{path}:{node.lineno} raw SQL references prompt_version outside the allowlist")


def check_single_write_shape() -> None:
    """No `Session.add(PromptVersion(...))` outside writes/prompts.py::write_prompt_version."""
    writes_path = (SRC / "world_engine" / "writes" / "prompts.py").resolve()
    for path in _iter_py_files():
        resolved = path.resolve()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for node in ast.walk(fn):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add"):
                    continue
                if not node.args:
                    continue
                arg = node.args[0]
                is_prompt_version_ctor = isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "PromptVersion"
                if is_prompt_version_ctor and not (resolved == writes_path and fn.name == "write_prompt_version"):
                    fail(f"{path}:{node.lineno} adds a PromptVersion row outside writes/prompts.py::write_prompt_version")


def check_append_only() -> None:
    """No UPDATE/DELETE SQL statement ever targets prompt_version — no allowlist."""
    pattern = re.compile(r"\b(UPDATE|DELETE\s+FROM)\s+prompt_version\b", re.IGNORECASE)
    for path in _iter_py_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if pattern.search(text):
            fail(f"{path}: contains an UPDATE/DELETE statement targeting prompt_version")


def check_no_format_on_template_text() -> None:
    """H1: no `.format(` call on a user_template/system_prompt attribute."""
    pattern = re.compile(r"(user_template|system_prompt)\.format\(")
    for path in sorted(SRC.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                fail(f"{path}:{lineno} calls .format() on template text — H1 violation")


# ── Schema check ─────────────────────────────────────────────────────────

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


def check_schema(engine) -> None:
    from sqlalchemy import inspect

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "prompt_version" not in tables:
        fail("prompt_version table does not exist")
        return

    pv_columns = {c["name"] for c in inspector.get_columns("prompt_version")}
    for col in ("id", "prompt_template_id", "version_number", "system_prompt", "user_template", "note", "created_at"):
        if col not in pv_columns:
            fail(f"prompt_version missing column {col!r}")

    indexes = inspector.get_indexes("prompt_version")
    unique_head_number = any(
        idx["unique"] and set(idx["column_names"]) == {"prompt_template_id", "version_number"}
        for idx in indexes
    )
    if not unique_head_number:
        fail("prompt_version has no UNIQUE(prompt_template_id, version_number) index")

    pt_columns = {c["name"] for c in inspector.get_columns("prompt_template")}
    for dropped in ("system_prompt", "user_template", "version"):
        if dropped in pt_columns:
            fail(f"prompt_template still has column {dropped!r} — F1 drop not applied")


# ── Live behavior ─────────────────────────────────────────────────────────

def check_live_behavior(engine) -> None:
    from sqlmodel import Session

    from world_engine.cockpit import crud
    from world_engine.models import PromptTemplate
    from world_engine.prompt_store import current_prompt, list_versions
    from world_engine.writes import PromptValidationError, write_prompt_variables, write_prompt_version
    from fastapi import HTTPException

    with Session(engine) as db:
        head = PromptTemplate(name="check-fixture", usage="npc_dialogue")
        db.add(head)
        db.flush()
        write_prompt_variables(db, template_id=head.id, variables=["player_line"])
        v1 = write_prompt_version(
            db, template_id=head.id, system_prompt="Hello {player_line}",
            user_template="{player_line}", note="v1",
        )
        db.commit()
        if v1.version_number != 1:
            fail(f"write_prompt_version: expected version_number=1, got {v1.version_number}")

        resolved = current_prompt(db, head)
        if resolved.version_number != 1:
            fail("current_prompt did not return the only existing version")

        # C1 fail-closed: undeclared placeholder -> raises, nothing written.
        try:
            write_prompt_version(
                db, template_id=head.id, system_prompt="Hello {typo_var}",
                user_template="{player_line}",
            )
            fail("write_prompt_version accepted an undeclared placeholder — C1 violated")
        except PromptValidationError as exc:
            if "typo_var" not in exc.offending:
                fail(f"PromptValidationError did not name the offending placeholder: {exc.offending}")
        db.rollback()

        if len(list_versions(db, head.id)) != 1:
            fail("a version was written despite the C1 validation failure")

        # PATCH route, called directly (no HTTP layer): valid edit -> v2.
        body = crud.PromptTextBody(system_prompt="Hi {player_line}", user_template="{player_line}")
        result = crud.update_prompt_text(head.id, body, db)
        if result["version_number"] != 2:
            fail(f"PATCH text: expected version_number=2, got {result['version_number']}")

        # PATCH route: undeclared placeholder -> 422, version list unchanged.
        bad_body = crud.PromptTextBody(system_prompt="Hi {oops}", user_template="{player_line}")
        try:
            crud.update_prompt_text(head.id, bad_body, db)
            fail("PATCH text accepted an undeclared placeholder — expected 422")
        except HTTPException as exc:
            if exc.status_code != 422:
                fail(f"PATCH text with bad placeholder: expected 422, got {exc.status_code}")
        versions_after = list_versions(db, head.id)
        if len(versions_after) != 2:
            fail(f"PATCH text: version count changed after a rejected save (got {len(versions_after)})")

        # Restore: appends a new version equal to v1's text.
        restore_result = crud.restore_prompt_version(head.id, 1, db)
        if restore_result["version_number"] != 3:
            fail(f"restore: expected version_number=3, got {restore_result['version_number']}")
        v3 = current_prompt(db, head)
        if v3.system_prompt != v1.system_prompt or v3.user_template != v1.user_template:
            fail("restore did not copy v1's text verbatim")


def main() -> int:
    check_class_reference_allowlist()
    check_sql_table_reference_allowlist()
    check_single_write_shape()
    check_append_only()
    check_no_format_on_template_text()

    engine = _fresh_engine()
    check_schema(engine)
    check_live_behavior(engine)

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: prompt_version schema, single accessor/write-shape allowlists, "
        "append-only, H1, and the versioned edit API (PATCH/versions/restore, "
        "C1 fail-closed)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
