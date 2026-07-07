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
    "src/world_engine/models.py",
    "src/world_engine/writes.py",
    "src/world_engine/context.py",
    "src/world_engine/cockpit/crud.py",
    "src/world_engine/cockpit/app.py",
    "src/world_engine/tick.py",
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


def main() -> None:
    check_module_allowlist()
    check_mj_boundary()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: npc_goal read boundary intact (N1)")
    sys.exit(0)


if __name__ == "__main__":
    main()
