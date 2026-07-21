"""G1 check: NPC group agent staging retention purge (TICKET-0037,
BRIEF-0037-a). AST-based, stdlib only, on the door_terminal.py idiom: a
missing target file or function is a FAILURE, never a vacuous pass.

Three assertions against `src/world_engine/cockpit/app.py`:
  a. `purge_closed_npc_batches` is defined and calls the shared
     `_purge_closed_batches` helper with `(db, NpcBatch, NpcBatchRow, ...)`
     — the same call shape as the link agent's sibling,
     `purge_closed_link_batches` (TICKET-0036).
  b. `_purge_closed_batches` retains the 2 most recently closed batches
     (`.offset(2)` on the closed_at-descending query) before purging the
     rest — last-2 retention, shared by both agents.
  c. A `@app.on_event("startup")` handler calls `purge_closed_npc_batches`
     — the purge actually runs at boot, not just exists as dead code.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_FILE = ROOT / "src" / "world_engine" / "cockpit" / "app.py"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _parse() -> ast.AST | None:
    if not APP_FILE.exists():
        fail(f"{APP_FILE} does not exist")
        return None
    try:
        return ast.parse(APP_FILE.read_text(encoding="utf-8"), filename=str(APP_FILE))
    except SyntaxError as exc:
        fail(f"{APP_FILE}: SyntaxError: {exc}")
        return None


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _calls_shared_purge_with_npc_batch(func: ast.FunctionDef) -> bool:
    for node in ast.walk(func):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id != "_purge_closed_batches":
            continue
        arg_names = {a.id for a in node.args if isinstance(a, ast.Name)}
        if "NpcBatch" in arg_names and "NpcBatchRow" in arg_names:
            return True
    return False


def check_purge_closed_npc_batches(tree: ast.AST) -> None:
    func = _find_function(tree, "purge_closed_npc_batches")
    if func is None:
        fail(f"{APP_FILE}: purge_closed_npc_batches is not defined")
        return
    if not _calls_shared_purge_with_npc_batch(func):
        fail(
            f"{APP_FILE}: purge_closed_npc_batches does not call "
            "_purge_closed_batches(db, NpcBatch, NpcBatchRow, ...)"
        )


def check_last_two_retention(tree: ast.AST) -> None:
    func = _find_function(tree, "_purge_closed_batches")
    if func is None:
        fail(f"{APP_FILE}: _purge_closed_batches is not defined")
        return
    found_offset_two = False
    for node in ast.walk(func):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "offset":
            if any(isinstance(a, ast.Constant) and a.value == 2 for a in node.args):
                found_offset_two = True
    if not found_offset_two:
        fail(f"{APP_FILE}: _purge_closed_batches does not .offset(2) — last-2 retention not found")


def check_startup_wiring(tree: ast.AST) -> None:
    found = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        has_startup_decorator = any(
            (isinstance(d, ast.Attribute) and d.attr == "on_event")
            or (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "on_event")
            for d in node.decorator_list
        )
        if not has_startup_decorator:
            continue
        for sub in ast.walk(node):
            if (
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Name)
                and sub.func.id == "purge_closed_npc_batches"
            ):
                found = True
    if not found:
        fail(f"{APP_FILE}: no @app.on_event('startup') handler calls purge_closed_npc_batches")


def main() -> int:
    tree = _parse()
    if tree is not None:
        check_purge_closed_npc_batches(tree)
        check_last_two_retention(tree)
        check_startup_wiring(tree)

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: npc_batch_purge — purge_closed_npc_batches wired to the shared "
        "last-2-retention helper and called at startup"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
