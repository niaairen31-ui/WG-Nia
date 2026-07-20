"""G1 check: NPC link agent staging strata (TICKET-0036, BRIEF-0036-a,
BRIEF-0036-b).

`link_batch` / `link_batch_row` are EPHEMERAL stratum (models/ephemeral.py
NOTE): never canon, never a `proposed_mutation`, never creator-CRUD-reviewed.
Three structural guarantees, all fail-closed:

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
  3. D3 (BRIEF-0036-b): every staged knowledge payload's "subject" key is
     built in exactly ONE function in `link_author.py`, as a code-stamped
     f-string carrying the `npc:` literal prefix — never a passthrough of
     the model's own `item.get(...)` output. The model proposes a
     "holder"; code alone derives "subject".

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
LINK_AUTHOR_FILE = SRC / "world_engine" / "link_author.py"

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


class _SubjectKeyVisitor(ast.NodeVisitor):
    """Finds every dict literal `"subject": <value>` and tags it with its
    innermost enclosing function name."""

    def __init__(self) -> None:
        self.func_stack: list[str] = []
        self.hits: list[tuple[str, ast.AST]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.func_stack.append(node.name)
        self.generic_visit(node)
        self.func_stack.pop()

    def visit_Dict(self, node: ast.Dict) -> None:
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and key.value == "subject":
                fname = self.func_stack[-1] if self.func_stack else "<module>"
                self.hits.append((fname, value))
        self.generic_visit(node)


def _check_knowledge_subject_stamp() -> None:
    """D3: the "subject" key of a staged knowledge payload must be built in
    exactly one function, as an f-string carrying the `npc:` stamp — never
    a passthrough of the model's own `item.get(...)` output."""
    if not LINK_AUTHOR_FILE.exists():
        fail(f"{LINK_AUTHOR_FILE} not found — D3 subject stamp cannot be verified")
        return

    tree = ast.parse(LINK_AUTHOR_FILE.read_text(encoding="utf-8"), filename=str(LINK_AUTHOR_FILE))
    visitor = _SubjectKeyVisitor()
    visitor.visit(tree)

    if not visitor.hits:
        fail(f"{LINK_AUTHOR_FILE}: no 'subject' key construction found for a knowledge payload — vacuous proof, not a pass")
        return

    functions = {fname for fname, _ in visitor.hits}
    if len(functions) != 1:
        fail(
            f"{LINK_AUTHOR_FILE}: 'subject' key constructed in multiple functions "
            f"{sorted(functions)} — D3 stamp must be a single chokepoint"
        )

    for fname, value_node in visitor.hits:
        if not isinstance(value_node, ast.JoinedStr):
            fail(f"{LINK_AUTHOR_FILE}:{value_node.lineno} in {fname}(): 'subject' value is not an f-string — D3 stamp must be code-derived")
            continue
        literal_parts = [v.value for v in value_node.values if isinstance(v, ast.Constant)]
        if not any(part.startswith("npc:") for part in literal_parts):
            fail(f"{LINK_AUTHOR_FILE}:{value_node.lineno} in {fname}(): 'subject' f-string does not carry the 'npc:' stamp literal")
        for sub in ast.walk(value_node):
            if (
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Attribute)
                and sub.func.attr == "get"
                and isinstance(sub.func.value, ast.Name)
                and sub.func.value.id == "item"
            ):
                fail(f"{LINK_AUTHOR_FILE}:{value_node.lineno} in {fname}(): 'subject' reads item.get(...) — the model must never supply the subject")


def main() -> None:
    _check_policy_file()
    _check_writes_dir()
    found_any = _check_reference_scope()
    if not FAILURES and not found_any:
        fail("zero LinkBatch/LinkBatchRow references found anywhere — vacuous proof, not a pass")
    _check_knowledge_subject_stamp()
    _report_and_exit()


if __name__ == "__main__":
    main()
