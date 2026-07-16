"""Structural gate for the N1 doctrine on `npc_goal` (TICKET-0013, BRIEF-0013-a).

Goals are NPC interiority: read only by `assemble_npc_context` (this brief)
and, later, the initiative vote (BRIEF-0013-c). `assemble_mj_context` must
NEVER gain a `npc_goal` query — enforced here by static scan, not by
convention (same mechanical philosophy as `single_canon_write.py`).

Rule 1 (module allowlist): the identifier `NpcGoal` may appear only in the
modules named below.
Rule 2 (MJ boundary): no `Name`/`Attribute` node referencing `NpcGoal`, nor
the string literal `"npc_goal"`, may appear anywhere in `context.py` from
`assemble_mj_context`'s definition to the end of the file (everything after
it in this module is the MJ assembler block — see the file's own
"MJ context assembler" section header).

Rule 3 (D1 dialogue provenance gate, TICKET-0020/BRIEF-0020-b):
`context.py`'s `_goal_provenance_suffix` both calls
`read_public_membership_faction_ids` AND contains a comparison of
`owner_entity_id` against a bare `npc_id` Name — the two-part D1 gate (own
intrigue OR public membership) is structurally present, never an
unconditional render of dialogue goal provenance.

No DB, stdlib `ast` only.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
CONTEXT_FILE = SRC / "world_engine" / "context.py"

ALLOWED_MODULES = {
    # models.py -> models/ package (TICKET-0028, BRIEF-0028-c): NpcGoal is
    # defined in models/canon.py and re-exported through models/__init__.py's
    # import — both listed (relocation-not-broadening precedent).
    "src/world_engine/models/canon.py",
    "src/world_engine/models/__init__.py",
    "src/world_engine/writes/goals_agendas.py",
    "src/world_engine/context.py",
    "src/world_engine/cockpit/crud/goals.py",
    "src/world_engine/cockpit/crud/agendas.py",
    "src/world_engine/cockpit/routes/mutations.py",
    "src/world_engine/cockpit/play_stream.py",
    "src/world_engine/cockpit/mutations.py",
    "src/world_engine/tick.py",
    "src/world_engine/tick_context.py",
    "scripts/migrate_v1_69_npc_goal.py",
    "tooling/verify/checks/npc_goal_read.py",
}

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _parse(path: pathlib.Path):
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        fail(f"{path}: SyntaxError: {exc}")
        return None


def _references_npc_goal(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and sub.id == "NpcGoal":
            return True
        if isinstance(sub, ast.Attribute) and sub.attr == "NpcGoal":
            return True
        if isinstance(sub, ast.alias) and sub.name == "NpcGoal":
            return True
        if isinstance(sub, ast.Constant) and sub.value == "npc_goal":
            return True
    return False


def check_module_allowlist() -> None:
    for path in sorted(SRC.rglob("*.py")) + sorted((ROOT / "scripts").rglob("*.py")) + sorted((ROOT / "tooling").rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if rel in ALLOWED_MODULES:
            continue
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "NpcGoal":
                fail(f"{rel}:{node.lineno} — NpcGoal referenced outside the allowlist")
            elif isinstance(node, ast.alias) and node.name == "NpcGoal":
                fail(f"{rel}:{node.lineno} — NpcGoal imported outside the allowlist")


def check_mj_boundary() -> None:
    if not CONTEXT_FILE.exists():
        fail(f"{CONTEXT_FILE} not found")
        return
    tree = _parse(CONTEXT_FILE)
    if tree is None:
        return

    mj_start = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "assemble_mj_context":
            mj_start = node.lineno
            break
    if mj_start is None:
        fail("context.py: assemble_mj_context not found")
        return

    for node in tree.body:
        if getattr(node, "lineno", 0) < mj_start:
            continue
        if _references_npc_goal(node):
            fail(
                f"context.py:{node.lineno} — NpcGoal/'npc_goal' reference found in "
                "the MJ block (assemble_mj_context onward)"
            )


def check_dialogue_provenance_gate() -> None:
    if not CONTEXT_FILE.exists():
        fail(f"{CONTEXT_FILE} not found")
        return
    tree = _parse(CONTEXT_FILE)
    if tree is None:
        return
    rel = CONTEXT_FILE.relative_to(ROOT).as_posix()

    func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_goal_provenance_suffix":
            func = node
            break
    if func is None:
        fail(f"{rel}: _goal_provenance_suffix not found")
        return

    calls_accessor = any(
        isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "read_public_membership_faction_ids"
        for n in ast.walk(func)
    )
    if not calls_accessor:
        fail(f"{rel}: _goal_provenance_suffix never calls read_public_membership_faction_ids")

    def _compare_targets(node: ast.Compare) -> list[ast.AST]:
        return [node.left, *node.comparators]

    has_owner_npc_compare = any(
        isinstance(n, ast.Compare)
        and any(isinstance(o, ast.Attribute) and o.attr == "owner_entity_id" for o in _compare_targets(n))
        and any(isinstance(o, ast.Name) and o.id == "npc_id" for o in _compare_targets(n))
        for n in ast.walk(func)
    )
    if not has_owner_npc_compare:
        fail(f"{rel}: _goal_provenance_suffix has no owner_entity_id == npc_id comparison")


def main() -> None:
    check_module_allowlist()
    check_mj_boundary()
    check_dialogue_provenance_gate()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: npc_goal read boundary intact (N1), D1 provenance gate intact")
    sys.exit(0)


if __name__ == "__main__":
    main()
