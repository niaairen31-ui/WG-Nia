"""Structural gate for the `visit` table (TICKET-0016, BRIEF-0016-a).

Rule 1 (append-only + single writer, RECON-0016 F8): `Visit(` constructor
calls appear only in `src/world_engine/cockpit/app.py`; no `db.delete()`
call receives a Visit-derived value; no attribute is assigned on a
Visit-derived target anywhere — a visit row is written once, at insert, and
never touched again (same mechanical philosophy as `single_canon_write.py`
and `world_tick.py`'s call-site allowlist).

Rule 2 (structural exclusion): `_compute_return_delta` (cockpit/app.py) —
the function housing the delta's `select(Event)` call — references
`knowledge_status` somewhere in its body (same spirit as the
secret-exclusion checks on the assemblers).

No DB, stdlib `ast` only.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
APP_FILE = SRC / "world_engine" / "cockpit" / "app.py"

ALLOWED_CONSTRUCTOR_MODULES = {
    "src/world_engine/cockpit/app.py",
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


def _is_visit_expr(node: ast.AST) -> bool:
    """True if `node`'s subtree names `Visit` anywhere — covers `Visit(...)`,
    `select(Visit)...`, `db.get(Visit, ...)`."""
    return any(isinstance(sub, ast.Name) and sub.id == "Visit" for sub in ast.walk(node))


def check_constructor_allowlist_and_append_only() -> None:
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        tree = _parse(path)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "Visit"
                and rel not in ALLOWED_CONSTRUCTOR_MODULES
            ):
                fail(f"{rel}:{node.lineno} — Visit(...) constructed outside the allowlist")

        for fn_node in ast.walk(tree):
            if not isinstance(fn_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            visit_vars: set[str] = set()
            for node in ast.walk(fn_node):
                if isinstance(node, ast.Assign) and _is_visit_expr(node.value):
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name):
                            visit_vars.add(tgt.id)
                elif (
                    isinstance(node, ast.AnnAssign)
                    and node.value is not None
                    and _is_visit_expr(node.value)
                    and isinstance(node.target, ast.Name)
                ):
                    visit_vars.add(node.target.id)

            for node in ast.walk(fn_node):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "delete"
                    and node.args
                    and isinstance(node.args[0], ast.Name)
                    and node.args[0].id in visit_vars
                ):
                    fail(f"{rel}:{node.lineno} — db.delete() receives a Visit-derived value; visit is append-only")
                if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Attribute)
                    and isinstance(t.value, ast.Name)
                    and t.value.id in visit_vars
                    for t in node.targets
                ):
                    fail(f"{rel}:{node.lineno} — attribute assigned on a Visit-derived target; visit is append-only")


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def check_event_structural_exclusion() -> None:
    if not APP_FILE.exists():
        fail(f"{APP_FILE} not found")
        return
    tree = _parse(APP_FILE)
    if tree is None:
        return
    rel = APP_FILE.relative_to(ROOT).as_posix()

    func = _find_function(tree, "_compute_return_delta")
    if func is None:
        fail(f"{rel}: _compute_return_delta not found")
        return

    has_knowledge_status = any(
        isinstance(n, ast.Attribute) and n.attr == "knowledge_status" for n in ast.walk(func)
    )
    if not has_knowledge_status:
        fail(f"{rel}: _compute_return_delta does not reference knowledge_status — structural exclusion missing")


def main() -> None:
    check_constructor_allowlist_and_append_only()
    check_event_structural_exclusion()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: visit_delta — append-only + single writer, event structural exclusion intact")
    sys.exit(0)


if __name__ == "__main__":
    main()
