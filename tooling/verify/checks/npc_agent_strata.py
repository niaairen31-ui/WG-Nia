"""G1 check: NPC group agent staging strata (TICKET-0037, BRIEF-0037-a/c).

`npc_batch` / `npc_batch_row` are EPHEMERAL stratum (models/ephemeral.py
NOTE): never canon, never a `proposed_mutation`, never creator-CRUD-reviewed.
Three structural guarantees, all fail-closed (sibling of
`link_agent_strata.py`; guarantee 3 there — the D3 subject-stamp scan — has
no analogue here, since this agent stages knowledge payloads verbatim from
`generate_entity_draft`, not a code-stamped subject key):

  1. `npc_batch`/`npc_batch_row` appear in NEITHER `canon_write_policy.txt`
     NOR any `src/world_engine/writes/` module — this agent adds zero
     bespoke canon write sites; the commit path (BRIEF-0037-c) rides
     already-allowed sites instead (guarantee 3).
  2. The `NpcBatch`/`NpcBatchRow` model classes are referenced (imported or
     named) ONLY from the narrow module set that legitimately touches this
     stratum: `cockpit/routes/npc_agent.py`, `npc_group_author.py`,
     `models/ephemeral.py` (definition), `models/__init__.py` (package
     re-export surface, same as every other model), and `cockpit/app.py`
     (the retention purge).
  3. BRIEF-0037-c: `cockpit/routes/npc_agent.py` and `npc_group_author.py`
     contain no direct `db.add(Entity(...))` / `db.add(Character(...))` /
     `db.add(FactionMembership(...))` / `db.add(Knowledge(...))` /
     `db.add(NpcGoal(...))` and no raw SQL INSERT/UPDATE touching those
     tables — the commit path (`_commit_npc_batch`/`_commit_npc_row`) is
     structurally forced through `_crud._create_entity_core` /
     `_crud._create_knowledge_core` / `write_npc_goal`, same as every other
     creator-direct-authority write.

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
NPC_AGENT_ROUTES_FILE = SRC / "world_engine" / "cockpit" / "routes" / "npc_agent.py"
NPC_GROUP_AUTHOR_FILE = SRC / "world_engine" / "npc_group_author.py"

STRATA_TABLES = ("npc_batch", "npc_batch_row")
STRATA_MODELS = {"NpcBatch", "NpcBatchRow"}

ALLOWED_REFERENCE_FILES = {
    "src/world_engine/cockpit/routes/npc_agent.py",
    "src/world_engine/npc_group_author.py",
    "src/world_engine/models/ephemeral.py",
    "src/world_engine/models/__init__.py",
    "src/world_engine/cockpit/app.py",
}

# BRIEF-0037-c: the only two files where the commit logic lives. No canon
# Entity()/Character()/FactionMembership()/Knowledge()/NpcGoal() construction
# or raw SQL is permitted here — everything routes through
# `_crud._create_entity_core` / `_crud._create_knowledge_core` /
# `write_npc_goal` (link_agent_strata.py precedent, guarantee 4 there).
DIRECT_WRITE_SCAN_FILES = {
    "src/world_engine/cockpit/routes/npc_agent.py": NPC_AGENT_ROUTES_FILE,
    "src/world_engine/npc_group_author.py": NPC_GROUP_AUTHOR_FILE,
}
_CANON_MODEL_NAMES = {"Entity", "Character", "FactionMembership", "Knowledge", "NpcGoal"}

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit() -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: npc_agent_strata — npc_batch/npc_batch_row stay ephemeral and narrowly scoped")
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
        fail(f"{MODELS_FILE} not found — NpcBatch/NpcBatchRow are not defined")
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
            fail(f"{rel}: references {sorted(refs)} outside the allowed NPC-agent module set")
    return found_any


class _DirectWriteVisitor(ast.NodeVisitor):
    """Flags `db.add(Entity(...))` / `db.add(Character(...))` /
    `db.add(FactionMembership(...))` / `db.add(Knowledge(...))` /
    `db.add(NpcGoal(...))` and raw SQL `text(...)` strings that INSERT/
    UPDATE any of those tables."""

    def __init__(self) -> None:
        self.hits: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "add"
            and node.args
            and isinstance(node.args[0], ast.Call)
            and isinstance(node.args[0].func, ast.Name)
            and node.args[0].func.id in _CANON_MODEL_NAMES
        ):
            self.hits.append(
                f"line {node.lineno}: db.add({node.args[0].func.id}(...)) — "
                "direct canon write bypasses _create_entity_core/_create_knowledge_core/write_npc_goal"
            )
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "text"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            sql = node.args[0].value.upper()
            if ("INSERT" in sql or "UPDATE" in sql) and any(
                table.upper() in sql
                for table in ("ENTITY", "CHARACTER", "FACTION_MEMBERSHIP", "KNOWLEDGE", "NPC_GOAL")
            ):
                self.hits.append(f"line {node.lineno}: raw SQL text(...) touching a canon table")
        self.generic_visit(node)


def _check_no_direct_canon_write() -> None:
    for rel, path in DIRECT_WRITE_SCAN_FILES.items():
        if not path.exists():
            fail(f"{path} not found — direct-canon-write guarantee cannot be verified")
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = _DirectWriteVisitor()
        visitor.visit(tree)
        for hit in visitor.hits:
            fail(f"{rel}: {hit}")


def main() -> None:
    _check_policy_file()
    _check_writes_dir()
    found_any = _check_reference_scope()
    if not FAILURES and not found_any:
        fail("zero NpcBatch/NpcBatchRow references found anywhere — vacuous proof, not a pass")
    _check_no_direct_canon_write()
    _report_and_exit()


if __name__ == "__main__":
    main()
