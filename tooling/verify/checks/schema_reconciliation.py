"""G1 check: physical-table reconciliation mechanism guard (TICKET-0044,
BRIEF-0044-d — C2 plane 2). AST-based, no DB — the ACCOUNTING is a runtime
concern (it depends on the live DB's actual tables); this guards only that
the MECHANISM is present and single-sourced, mirroring
`single_canon_write.py`'s static-AST precedent. Scans
`src/world_engine/schema_reconcile.py` for four fail-closed assertions:

  1. The three functions `static_table_names`, `registered_runtime_tables`,
     `unaccounted_tables` are all defined.
  2. `static_table_names` references `SQLModel.metadata` somewhere in its
     body — never a hardcoded literal table-name set.
  3. The `"ext_"` literal appears nowhere in the module but inside a
     docstring — the module must import `EXT_PREFIX` from
     `writes/schema.py` (single source), never redefine the prefix.
  4. `cockpit/app.py` imports `schema_reconcile` (the boot-guard wiring).

Zero parsed assertions is itself a FAILURE (vacuous-proof), never a silent
pass.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
RECONCILE_FILE = ROOT / "src" / "world_engine" / "schema_reconcile.py"
APP_FILE = ROOT / "src" / "world_engine" / "cockpit" / "app.py"

REQUIRED_FUNCTIONS = {"static_table_names", "registered_runtime_tables", "unaccounted_tables"}
EXT_LITERAL = "ext_"

FAILURES: list[str] = []
ASSERTIONS = 0


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _mark(n: int = 1) -> None:
    global ASSERTIONS
    ASSERTIONS += n


def _report_and_exit() -> None:
    if ASSERTIONS == 0:
        fail("zero parsed assertions — vacuous proof, check is broken not the repo clean")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: schema_reconciliation — mechanism present, SQLModel.metadata-sourced, "
        "EXT_PREFIX single-sourced, boot-wired"
    )
    sys.exit(0)


def _docstring_nodes(tree: ast.Module) -> set:
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                out.add(id(body[0].value))
    return out


def _string_constants(tree: ast.Module, skip_ids: set):
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip_ids:
            yield node


def check_functions_defined(tree: ast.Module) -> None:
    defined = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for name in sorted(REQUIRED_FUNCTIONS):
        _mark()
        if name not in defined:
            fail(f"{RECONCILE_FILE.name} does not define required function {name!r}")


def check_static_source(tree: ast.Module) -> None:
    fn = next(
        (n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
         and n.name == "static_table_names"),
        None,
    )
    _mark()
    if fn is None:
        fail("static_table_names is not defined — cannot check its SQLModel.metadata source")
        return
    source = ast.unparse(fn)
    if "SQLModel" not in source or "metadata" not in source:
        fail("static_table_names does not reference SQLModel.metadata — looks like a hardcoded literal set")


def check_ext_single_source(tree: ast.Module, docstrings: set) -> None:
    has_import = any(
        isinstance(node, ast.ImportFrom) and node.module and node.module.endswith("writes.schema")
        and any(alias.name == "EXT_PREFIX" for alias in node.names)
        for node in ast.walk(tree)
    )
    _mark()
    if not has_import:
        fail("EXT_PREFIX is not imported from writes/schema.py — single-source violation")
    for const in _string_constants(tree, docstrings):
        _mark()
        if EXT_LITERAL in const.value:
            fail(
                f"{RECONCILE_FILE.name}:{const.lineno} — {EXT_LITERAL!r} literal outside "
                "a docstring / the EXT_PREFIX import"
            )


def check_boot_wiring() -> None:
    _mark()
    if not APP_FILE.exists():
        fail(f"{APP_FILE} not found")
        return
    app_tree = ast.parse(APP_FILE.read_text(encoding="utf-8"), filename=str(APP_FILE))
    imports_reconcile = any(
        isinstance(node, ast.ImportFrom)
        and ((node.module and "schema_reconcile" in node.module)
             or any(alias.name == "schema_reconcile" for alias in node.names))
        for node in ast.walk(app_tree)
    )
    if not imports_reconcile:
        fail(f"{APP_FILE.name} does not import schema_reconcile — boot-guard wiring is missing")


def main() -> None:
    if not RECONCILE_FILE.exists():
        fail(f"{RECONCILE_FILE} not found")
        _report_and_exit()
        return
    try:
        tree = ast.parse(RECONCILE_FILE.read_text(encoding="utf-8"), filename=str(RECONCILE_FILE))
    except SyntaxError as exc:
        fail(f"{RECONCILE_FILE}: SyntaxError: {exc}")
        _report_and_exit()
        return

    docstrings = _docstring_nodes(tree)
    check_functions_defined(tree)
    check_static_source(tree)
    check_ext_single_source(tree, docstrings)
    check_boot_wiring()

    _report_and_exit()


if __name__ == "__main__":
    main()
