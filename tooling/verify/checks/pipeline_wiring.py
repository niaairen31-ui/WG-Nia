"""Structural gate for the day-declaration socle (TICKET-0075, BRIEF-0075-a).
Stdlib `ast` only, no DB — same FAILURES/fail()/print-all-then-exit idiom as
`npc_schedule.py`.

R1 (no-reader violation clearing): `Batch` and `PassPlay` each have at least
one importer in `src/` outside `models/__init__.py`.
R2 (table shape, U1): `Batch.__table_args__` declares a unique index over
exactly `("session_id", "day_number")`.
R3 (history is sacred, write-once): no assignment to any `.declared_action`
attribute anywhere in `src/`, and no `declared_action` key in any
`update()`/`setattr()` call. The one legal write is the `PassPlay(...)`
constructor inside `writes/pipeline.py`.
R4 (no restated literal): `MAX_DECLARATION_CHARS` and `PASS_PLAY_STATUSES`
are module-level constants in `writes/pipeline.py`, and `routes/day.py`
reads the bound from there rather than restating the literal `4000`.
R5 (fail-closed, no mutation path): `routes/day.py` contains no
`PUT`/`PATCH`/`DELETE` decorator, and no response builder in it references
`injected_context` or `history`.
R6: vacuity guard — the module count scanned, the constant count found and
the route count found are each asserted non-zero, with the failure message
naming which one came back empty.

Every rule carries an anti-vacuity guard: a rule that locates zero items is
a FAILURE, not a silent pass.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

MODELS_INIT_FILE = SRC / "models" / "__init__.py"
PIPELINE_MODEL_FILE = SRC / "models" / "pipeline.py"
WRITES_PIPELINE_FILE = SRC / "writes" / "pipeline.py"
DAY_ROUTES_FILE = SRC / "cockpit" / "routes" / "day.py"

EXPECTED_DAY_INDEX_COLUMNS = ("session_id", "day_number")

FAILURES: list[str] = []
_TREE_CACHE: dict[pathlib.Path, ast.Module | None] = {}


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _parse(path: pathlib.Path) -> ast.Module | None:
    if path in _TREE_CACHE:
        return _TREE_CACHE[path]
    if not path.exists():
        fail(f"{_rel(path)}: file not found")
        _TREE_CACHE[path] = None
        return None
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        fail(f"{_rel(path)}: SyntaxError: {exc}")
        tree = None
    _TREE_CACHE[path] = tree
    return tree


def _find_class(tree: ast.AST, name: str) -> ast.ClassDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    return None


def _all_src_files() -> list[pathlib.Path]:
    return sorted(SRC.rglob("*.py"))


def check_readers_exist() -> int:
    """R1: at least one importer of each of `Batch`/`PassPlay` in `src/`,
    outside `models/__init__.py`. Returns the number of files scanned, for
    the R6 vacuity guard."""
    files = _all_src_files()
    if not files:
        fail(f"{_rel(SRC)}: zero .py files found — vacuous scan")
        return 0

    importers: dict[str, set[pathlib.Path]] = {"Batch": set(), "PassPlay": set()}
    for path in files:
        if path == MODELS_INIT_FILE:
            continue
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in importers:
                importers[node.id].add(path)

    for name, paths in importers.items():
        if not paths:
            fail(
                f"{name}: zero importers found in src/ outside "
                f"{_rel(MODELS_INIT_FILE)} — the no-reader violation is not cleared"
            )

    return len(files)


def check_batch_table_shape() -> None:
    """R2: `Batch.__table_args__` declares a unique index over exactly
    `(session_id, day_number)`."""
    tree = _parse(PIPELINE_MODEL_FILE)
    if tree is None:
        return
    cls = _find_class(tree, "Batch")
    if cls is None:
        fail(f"{_rel(PIPELINE_MODEL_FILE)}: Batch class not found")
        return

    found_index = False
    for node in ast.walk(cls):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Index"):
            continue
        if not (node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "idx_batch_session_day"):
            continue
        found_index = True
        column_args = [a.value for a in node.args[1:] if isinstance(a, ast.Constant)]
        is_unique = any(
            kw.arg == "unique" and isinstance(kw.value, ast.Constant) and kw.value.value is True
            for kw in node.keywords
        )
        if tuple(column_args) != EXPECTED_DAY_INDEX_COLUMNS:
            fail(
                f"{_rel(PIPELINE_MODEL_FILE)}: idx_batch_session_day covers "
                f"{tuple(column_args)!r}, expected {EXPECTED_DAY_INDEX_COLUMNS!r}"
            )
        if not is_unique:
            fail(f"{_rel(PIPELINE_MODEL_FILE)}: idx_batch_session_day is not unique")
    if not found_index:
        fail(f"{_rel(PIPELINE_MODEL_FILE)}: Batch declares no idx_batch_session_day Index()")


def check_declared_action_write_once() -> None:
    """R3: no `.declared_action` attribute assignment, no `setattr(...,
    'declared_action', ...)`, no `declared_action` key in an `update()` call,
    anywhere in `src/`. The one legal write is the `PassPlay(...)`
    constructor keyword inside writes/pipeline.py, which none of these
    patterns match."""
    files = _all_src_files()
    if not files:
        fail(f"{_rel(SRC)}: zero .py files found — vacuous scan (R3)")
        return

    for path in files:
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, ast.AugAssign):
                targets = [node.target]
            for target in targets:
                if isinstance(target, ast.Attribute) and target.attr == "declared_action":
                    fail(
                        f"{_rel(path)}:{node.lineno} — assignment to .declared_action "
                        "outside the PassPlay(...) constructor"
                    )

            if isinstance(node, ast.Call):
                if (
                    isinstance(node.func, ast.Name) and node.func.id == "setattr"
                    and len(node.args) >= 2
                    and isinstance(node.args[1], ast.Constant)
                    and node.args[1].value == "declared_action"
                ):
                    fail(f"{_rel(path)}:{node.lineno} — setattr(..., 'declared_action', ...) call")
                if isinstance(node.func, ast.Attribute) and node.func.attr == "update":
                    for kw in node.keywords:
                        if kw.arg == "declared_action":
                            fail(f"{_rel(path)}:{node.lineno} — .update(declared_action=...) call")
                    for arg in node.args:
                        if isinstance(arg, ast.Dict):
                            for key in arg.keys:
                                if isinstance(key, ast.Constant) and key.value == "declared_action":
                                    fail(f"{_rel(path)}:{node.lineno} — .update({{'declared_action': ...}}) call")


def check_no_restated_bound() -> None:
    """R4: MAX_DECLARATION_CHARS and PASS_PLAY_STATUSES are module-level
    constants in writes/pipeline.py; routes/day.py reads MAX_DECLARATION_CHARS
    from there rather than restating the literal `4000`."""
    tree = _parse(WRITES_PIPELINE_FILE)
    constants_found: set[str] = set()
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in ("MAX_DECLARATION_CHARS", "PASS_PLAY_STATUSES"):
                        constants_found.add(target.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.target.id in ("MAX_DECLARATION_CHARS", "PASS_PLAY_STATUSES"):
                    constants_found.add(node.target.id)

    for required in ("MAX_DECLARATION_CHARS", "PASS_PLAY_STATUSES"):
        if required not in constants_found:
            fail(f"{_rel(WRITES_PIPELINE_FILE)}: {required} not found as a module-level constant")

    route_tree = _parse(DAY_ROUTES_FILE)
    if route_tree is None:
        return
    references_bound = any(
        isinstance(node, ast.Name) and node.id == "MAX_DECLARATION_CHARS"
        for node in ast.walk(route_tree)
    )
    if not references_bound:
        fail(f"{_rel(DAY_ROUTES_FILE)}: does not reference MAX_DECLARATION_CHARS — restates the bound instead")

    restates_literal = any(
        isinstance(node, ast.Constant) and node.value == 4000
        for node in ast.walk(route_tree)
    )
    if restates_literal:
        fail(f"{_rel(DAY_ROUTES_FILE)}: contains a literal 4000 — restates the bound instead of reading it")

    return len(constants_found)


def check_route_shape() -> int:
    """R5: no PUT/PATCH/DELETE decorator in routes/day.py, and no response
    builder in it references injected_context or history. Returns the
    number of `@router.<verb>` routes found, for the R6 vacuity guard."""
    tree = _parse(DAY_ROUTES_FILE)
    if tree is None:
        return 0

    forbidden_verbs = {"put", "patch", "delete"}
    route_count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for deco in node.decorator_list:
            if (
                isinstance(deco, ast.Call)
                and isinstance(deco.func, ast.Attribute)
                and isinstance(deco.func.value, ast.Name)
                and deco.func.value.id == "router"
            ):
                if deco.func.attr in forbidden_verbs:
                    fail(
                        f"{_rel(DAY_ROUTES_FILE)}:{node.lineno} — @router.{deco.func.attr} "
                        "decorator found; day.py must expose no PUT/PATCH/DELETE"
                    )
                elif deco.func.attr in ("get", "post"):
                    route_count += 1

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in ("injected_context", "history"):
            fail(
                f"{_rel(DAY_ROUTES_FILE)}:{node.lineno} — references .{node.attr}, "
                "which must never cross into a response body"
            )
        if isinstance(node, ast.Constant) and node.value in ("injected_context", "history"):
            fail(
                f"{_rel(DAY_ROUTES_FILE)}:{node.lineno} — references {node.value!r}, "
                "which must never cross into a response body"
            )

    if route_count == 0:
        fail(f"{_rel(DAY_ROUTES_FILE)}: zero GET/POST routes found — vacuous scan")

    return route_count


def main() -> None:
    module_count = check_readers_exist()
    check_batch_table_shape()
    check_declared_action_write_once()
    constant_count = check_no_restated_bound() or 0
    route_count = check_route_shape()

    if module_count == 0:
        fail("R6: module count scanned came back empty")
    if constant_count == 0:
        fail("R6: constant count found came back empty")
    if route_count == 0:
        fail("R6: route count found came back empty")

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: pipeline_wiring — readers exist, batch table shape, declared_action "
        "write-once, no restated bound, route shape and the vacuity guard are all intact"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
