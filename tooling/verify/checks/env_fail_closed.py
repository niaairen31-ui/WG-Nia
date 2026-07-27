"""G1 check: db.py's engine URL resolver is fail-closed (TICKET-0049, BRIEF-0049-a/d).

AST-only, same discipline as `import_cycle.py`: no DB, no execution of
`src/world_engine/db.py`. Statically proves the `_resolve_database_url()`
contract landed in BRIEF-0049-a still holds:

- no `os.getenv(...)` call anywhere in the module supplies a default
  argument (the exact shape of the old implicit-prod-default bug);
- the unresolved path (neither an explicit URL nor a recognized
  `WORLD_ENGINE_ENV`) raises, and its message contains "Refusing to start";
- the `WORLD_ENGINE_ENV == "test"` branch resolves to a path distinct from
  the `"prod"` branch and containing a `"test"` path segment.

Vacuous-proof: a missing `db.py`, or a resolver function that can't be
found, is a FAILURE, never a silent pass.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
DB_PY = ROOT / "src" / "world_engine" / "db.py"
RESOLVER_NAME = "_resolve_database_url"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit() -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: env_fail_closed — db.py resolver has no implicit default and raises when unresolved")
    sys.exit(0)


def _is_os_getenv_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "getenv"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "os"
    )


def _compares_to_string(test: ast.AST, value: str) -> bool:
    return (
        isinstance(test, ast.Compare)
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.Eq)
        and len(test.comparators) == 1
        and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value == value
    )


def main() -> None:
    if not DB_PY.exists():
        fail(f"{DB_PY} does not exist")
        _report_and_exit()
        return

    text = DB_PY.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(DB_PY))
    except SyntaxError as exc:
        fail(f"{DB_PY}: SyntaxError: {exc}")
        _report_and_exit()
        return

    # No os.getenv(...) call anywhere in the module may carry a default arg.
    for node in ast.walk(tree):
        if _is_os_getenv_call(node) and len(node.args) > 1:
            fail(
                f"{DB_PY}: os.getenv call at line {node.lineno} passes a "
                "default argument — implicit-default shape reintroduced"
            )

    resolver = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == RESOLVER_NAME
        ),
        None,
    )
    if resolver is None:
        fail(f"{DB_PY}: resolver function {RESOLVER_NAME}() not found")
        _report_and_exit()
        return

    # A Raise must exist at the resolver's top level (the fallthrough,
    # unresolved path) — not nested only inside a branch that always returns.
    raise_node = next(
        (stmt for stmt in resolver.body if isinstance(stmt, ast.Raise)), None
    )
    if raise_node is None:
        fail(f"{DB_PY}: no top-level raise in {RESOLVER_NAME}() — unresolved path may not fail closed")
    else:
        raise_src = ast.unparse(raise_node)
        if "Refusing to start" not in raise_src:
            fail(
                f"{DB_PY}: raise at line {raise_node.lineno} does not contain "
                "'Refusing to start'"
            )

    # Module-level simple assignments (`NAME = <expr>`), so a returned
    # `_TEST_DB_PATH`-style reference can be resolved to its underlying
    # path-building expression rather than just the local variable name.
    module_assigns: dict[str, str] = {}
    for stmt in tree.body:
        if (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
        ):
            module_assigns[stmt.targets[0].id] = ast.unparse(stmt.value)

    def _resolved_path_source(expr: ast.expr) -> str:
        """The returned expression's source, plus the source of any
        module-level name it references (resolves e.g. `_TEST_DB_PATH`)."""
        parts = [ast.unparse(expr)]
        for name_node in ast.walk(expr):
            if isinstance(name_node, ast.Name) and name_node.id in module_assigns:
                parts.append(module_assigns[name_node.id])
        return " ".join(parts)

    # Locate the prod/test branches: `if <name> == "prod":` / `== "test":`.
    prod_return_src: str | None = None
    test_return_src: str | None = None
    for node in ast.walk(resolver):
        if not isinstance(node, ast.If):
            continue
        ret = next((s for s in node.body if isinstance(s, ast.Return)), None)
        if ret is None or ret.value is None:
            continue
        if _compares_to_string(node.test, "prod"):
            prod_return_src = _resolved_path_source(ret.value)
        elif _compares_to_string(node.test, "test"):
            test_return_src = _resolved_path_source(ret.value)

    if prod_return_src is None:
        fail(f"{DB_PY}: no `== \"prod\"` branch found in {RESOLVER_NAME}()")
    if test_return_src is None:
        fail(f"{DB_PY}: no `== \"test\"` branch found in {RESOLVER_NAME}()")
    if prod_return_src is not None and test_return_src is not None:
        if "test" not in test_return_src.lower():
            fail(
                f"{DB_PY}: the \"test\" branch's resolved path "
                f"({test_return_src!r}) contains no 'test' path segment"
            )
        if prod_return_src == test_return_src:
            fail(f"{DB_PY}: prod and test branches resolve to the same path")

    _report_and_exit()


if __name__ == "__main__":
    main()
