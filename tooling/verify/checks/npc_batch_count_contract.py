"""G1 check: NPC group agent exact-count invariant (TICKET-0037,
BRIEF-0037-b/c). AST-based, stdlib only, on the door_terminal.py idiom: a
missing target file or function is a FAILURE, never a vacuous pass.

A batch run must produce exactly sum(count) staged rows OR per-line
failure notes — never a silent shortfall. No floor or top-up construct
(BRIEF-39/40's retired pattern) may exist in the NPC group author; the
run count is a loop-per-count structure, and the commit route refuses a
partial batch outright. Four assertions:

  a. `src/world_engine/npc_group_author.py` contains none of the retired
     floor/top-up vocabulary tokens.
  b. `_line_units` (the run's flattened unit order) contains a `for` loop
     over `range(...)` keyed on a line's `"count"` field — one unit per
     count, by construction, no clamp.
  c. `create_npc_batch` (`cockpit/routes/npc_agent.py`) accumulates
     `npcs_total` via a plain `total += count` — no `min(`/`max(` wrapping
     `count` or `total` anywhere in the function.
  d. The commit route guards on `npcs_done != npcs_total` (or `==`) and
     raises/returns on the mismatch branch — a short run can never reach
     commit silently.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
AUTHOR_FILE = ROOT / "src" / "world_engine" / "npc_group_author.py"
ROUTE_FILE = ROOT / "src" / "world_engine" / "cockpit" / "routes" / "npc_agent.py"

FORBIDDEN_TOKENS = ("floor", "topup", "top_up", "top-up", "deficit", "clamp")

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _parse(path: pathlib.Path) -> ast.AST | None:
    if not path.exists():
        fail(f"{path} does not exist")
        return None
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        fail(f"{path}: SyntaxError: {exc}")
        return None


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def check_no_floor_topup_vocabulary() -> None:
    if not AUTHOR_FILE.exists():
        fail(f"{AUTHOR_FILE} does not exist")
        return
    text_lower = AUTHOR_FILE.read_text(encoding="utf-8").lower()
    rel = AUTHOR_FILE.relative_to(ROOT).as_posix()
    for token in FORBIDDEN_TOKENS:
        if token in text_lower:
            fail(f"{rel} still contains retired floor/top-up vocabulary: {token!r}")


def check_line_units_loop_per_count(tree: ast.AST) -> None:
    """`_line_units` may express the per-count loop as an `ast.For` or as a
    comprehension's `ast.comprehension` clause (both expose `.iter`) —
    either counts, as long as it ranges over a line's `"count"` field."""
    func = _find_function(tree, "_line_units")
    if func is None:
        fail(f"{AUTHOR_FILE}: _line_units is not defined")
        return

    found = False
    for node in ast.walk(func):
        if not isinstance(node, (ast.For, ast.comprehension)):
            continue
        it = node.iter
        if not (isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range"):
            continue
        for arg in it.args:
            if isinstance(arg, ast.Subscript) and isinstance(arg.slice, ast.Constant) and arg.slice.value == "count":
                found = True

    if not found:
        fail(
            f"{AUTHOR_FILE}: _line_units has no for-loop/comprehension over "
            'range(...["count"]) — the one-unit-per-count structure was not found'
        )


def check_total_accumulation_unclamped(tree: ast.AST) -> None:
    func = _find_function(tree, "create_npc_batch")
    if func is None:
        fail(f"{ROUTE_FILE}: create_npc_batch is not defined")
        return

    has_aug_assign = any(
        isinstance(node, ast.AugAssign)
        and isinstance(node.op, ast.Add)
        and isinstance(node.target, ast.Name)
        and node.target.id == "total"
        for node in ast.walk(func)
    )
    if not has_aug_assign:
        fail(f"{ROUTE_FILE}: create_npc_batch has no 'total += ...' accumulation")

    for node in ast.walk(func):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("min", "max"):
            fail(
                f"{ROUTE_FILE}:{node.lineno} — create_npc_batch calls "
                f"{node.func.id}(...) near the count accumulation; the count "
                "contract must be un-clamped"
            )


def check_no_partial_commit_guard(tree: ast.AST) -> None:
    func = _find_function(tree, "_commit_npc_batch")
    if func is None:
        fail(f"{ROUTE_FILE}: _commit_npc_batch is not defined")
        return

    found = False
    for node in ast.walk(func):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not isinstance(test, ast.Compare) or len(test.ops) != 1:
            continue
        if not isinstance(test.ops[0], (ast.NotEq, ast.Eq)):
            continue

        def _attr_name(expr: ast.expr) -> str | None:
            return expr.attr if isinstance(expr, ast.Attribute) else None

        names = {_attr_name(test.left), _attr_name(test.comparators[0])}
        if "npcs_done" in names and "npcs_total" in names:
            has_raise_or_return = any(isinstance(sub, (ast.Raise, ast.Return)) for sub in ast.walk(node))
            if has_raise_or_return:
                found = True

    if not found:
        fail(
            f"{ROUTE_FILE}: _commit_npc_batch has no guard comparing "
            "npcs_done/npcs_total that raises or returns on mismatch"
        )


def main() -> int:
    check_no_floor_topup_vocabulary()

    author_tree = _parse(AUTHOR_FILE)
    if author_tree is not None:
        check_line_units_loop_per_count(author_tree)

    route_tree = _parse(ROUTE_FILE)
    if route_tree is not None:
        check_total_accumulation_unclamped(route_tree)
        check_no_partial_commit_guard(route_tree)

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: npc_batch_count_contract — loop-per-count run order, "
        "un-clamped total, no-partial-commit guard, no floor/top-up vocabulary"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
