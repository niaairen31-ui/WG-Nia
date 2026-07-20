"""G1 check: NPC link agent staging strata (TICKET-0036, BRIEF-0036-a).

`link_batch` / `link_batch_row` are EPHEMERAL stratum (models/ephemeral.py
NOTE): never canon, never a `proposed_mutation`, never creator-CRUD-reviewed.
Two structural guarantees, both fail-closed:

  1. `link_batch`/`link_batch_row` appear in NEITHER
     `canon_write_policy.txt` NOR any `src/world_engine/writes/` module —
     the commit path (0036-c) must route through `write_relation` /
     `write_knowledge` only, never a bespoke link_batch write site.
  2. The `LinkBatch`/`LinkBatchRow` model classes are referenced (imported
     or named) ONLY from the narrow module set that legitimately touches
     this stratum: `cockpit/routes/link_agent.py`, `link_author.py`,
     `models/ephemeral.py` (definition), `models/__init__.py` (package
     re-export surface, same as every other model), and `cockpit/app.py`
     (the retention purge).

Vacuous-proof: if the policy file or the model definitions are missing,
that is a FAILURE, not a silent pass — there is nothing to structurally
guarantee against.

No DB, stdlib `ast` only.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
WRITES_DIR = SRC / "world_engine" / "writes"
POLICY_FILE = ROOT / "tooling" / "verify" / "canon_write_policy.txt"
MODELS_FILE = SRC / "world_engine" / "models" / "ephemeral.py"

STRATA_TABLES = ("link_batch", "link_batch_row")
STRATA_MODELS = {"LinkBatch", "LinkBatchRow"}

ALLOWED_REFERENCE_FILES = {
    "src/world_engine/cockpit/routes/link_agent.py",
    "src/world_engine/link_author.py",
    "src/world_engine/models/ephemeral.py",
    "src/world_engine/models/__init__.py",
    "src/world_engine/cockpit/app.py",
}

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit() -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: link_agent_strata — link_batch/link_batch_row stay ephemeral and narrowly scoped")
    sys.exit(0)


def _check_policy_file() -> None:
    if not POLICY_FILE.exists():
        fail(f"{POLICY_FILE} not found — nothing to structurally guarantee")
        return
    text = POLICY_FILE.read_text(encoding="utf-8")
    for table in STRATA_TABLES:
        if table in text:
            fail(f"{POLICY_FILE}: {table!r} must never appear in canon_write_policy.txt")


def _check_writes_dir() -> None:
    if not WRITES_DIR.is_dir():
        fail(f"{WRITES_DIR} not found")
        return
    for path in sorted(WRITES_DIR.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for table in STRATA_TABLES:
            if table in text:
                rel = path.relative_to(ROOT).as_posix()
                fail(f"{rel}: {table!r} must never appear in a writes/ module")


def _referenced_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in STRATA_MODELS:
            names.add(node.id)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in STRATA_MODELS:
                    names.add(alias.name)
    return names


def _check_reference_scope() -> bool:
    if not MODELS_FILE.exists():
        fail(f"{MODELS_FILE} not found — LinkBatch/LinkBatchRow are not defined")
        return False

    tree = ast.parse(MODELS_FILE.read_text(encoding="utf-8"), filename=str(MODELS_FILE))
    defined = {
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name in STRATA_MODELS
    }
    if defined != STRATA_MODELS:
        fail(f"{MODELS_FILE}: expected both {sorted(STRATA_MODELS)}, found {sorted(defined)}")
        return False

    found_any = False
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        try:
            file_tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            fail(f"{path}: SyntaxError: {exc}")
            continue
        refs = _referenced_names(file_tree)
        if not refs:
            continue
        found_any = True
        if rel not in ALLOWED_REFERENCE_FILES:
            fail(f"{rel}: references {sorted(refs)} outside the allowed link-agent module set")
    return found_any


def main() -> None:
    _check_policy_file()
    _check_writes_dir()
    found_any = _check_reference_scope()
    if not FAILURES and not found_any:
        fail("zero LinkBatch/LinkBatchRow references found anywhere — vacuous proof, not a pass")
    _report_and_exit()


if __name__ == "__main__":
    main()
