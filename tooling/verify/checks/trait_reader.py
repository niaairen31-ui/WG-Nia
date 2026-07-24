"""G1 check: "no structure without a reader" (E2), mechanized (C1, TICKET-0045,
BRIEF-0045-c).

Imports the trait registry (`world_engine.traits`) and resolves every
declared trait's reader by its form:

- **reader_callable** ("module:function"): the module imports and the
  function is a callable attribute on it.
- **reader_guard** (module, column): the module's own source text carries
  the column name in a filter position (`column == False` / `column = FALSE`)
  — proof that the exclusion is a query-construction filter, not a mention.
- **reader_deferred**: tolerated ONLY for the trait named `mutable_by_ai`,
  ONLY with the exact value `TICKET-0047`. Any other trait claiming a
  deferred reader is a FAIL — the single named exception to E2.

Registry import IS permitted here (unlike module_budget.py / import_cycle.py,
which stay AST-only): traits.py is pure declarations with no side effects, so
importing it (and the reader modules it points at) never touches a database
or performs I/O. Vacuous-proof: zero traits examined is a FAIL, and the
registry must carry at least the five canonical traits.
"""
from __future__ import annotations

import ast
import importlib
import inspect
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(assertions: int) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(f"PASS: trait_reader — {assertions} traits, all readers resolve")
    sys.exit(0)


def _resolve_callable(trait_key: str, dotted: str) -> None:
    if ":" not in dotted:
        fail(f"trait {trait_key!r}: reader_callable {dotted!r} is not in 'module:function' form")
        return
    module_name, func_name = dotted.split(":", 1)
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001 - any import failure is a named FAIL
        fail(f"trait {trait_key!r}: reader_callable {dotted!r} — module import failed: {exc}")
        return
    func = getattr(module, func_name, None)
    if func is None:
        fail(f"trait {trait_key!r}: reader_callable {dotted!r} — no attribute {func_name!r} on {module_name!r}")
        return
    if not callable(func):
        fail(f"trait {trait_key!r}: reader_callable {dotted!r} — {func_name!r} is not callable")


_GUARD_RE_TEMPLATE = r"{col}\s*==\s*False|{col}\s*=\s*FALSE"


def _code_only(source: str) -> str:
    """Strip docstrings and comments so the guard regex can only match real
    filter code — a bare mention of the column in prose (e.g. a docstring
    narrating `is_secret = FALSE` in backticks) must not satisfy the check."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source
    docstrings = [
        doc
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        for doc in [ast.get_docstring(node, clean=False)]
        if doc
    ]
    stripped = source
    for doc in docstrings:
        stripped = stripped.replace(doc, "")
    return re.sub(r"#.*", "", stripped)


def _resolve_guard(trait_key: str, module_name: str, column_name: str) -> None:
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001
        fail(f"trait {trait_key!r}: reader_guard module {module_name!r} — import failed: {exc}")
        return
    try:
        source = inspect.getsource(module)
    except (OSError, TypeError) as exc:
        fail(f"trait {trait_key!r}: reader_guard module {module_name!r} — source unavailable: {exc}")
        return
    code = _code_only(source)
    pattern = _GUARD_RE_TEMPLATE.format(col=re.escape(column_name))
    if not re.search(pattern, code):
        fail(
            f"trait {trait_key!r}: reader_guard column {column_name!r} not found in a "
            f"filter position ('{column_name} == False') in module {module_name!r}"
        )


def _resolve_deferred(trait_key: str, deferred: str) -> None:
    if trait_key != "mutable_by_ai":
        fail(f"trait {trait_key!r}: only mutable_by_ai may defer its reader (reader_deferred={deferred!r})")
        return
    if deferred != "TICKET-0047":
        fail(f"trait {trait_key!r}: reader_deferred must be exactly 'TICKET-0047', got {deferred!r}")


def main() -> None:
    sys.path.insert(0, str(SRC))
    try:
        from world_engine import traits
    except Exception as exc:  # noqa: BLE001 - a malformed TraitDef fails construction here, desired
        fail(f"world_engine.traits failed to import: {exc}")
        _report_and_exit(0)
        return

    if len(traits.TRAITS) < 5:
        fail(f"vacuous-proof: expected >= 5 canonical traits, found {len(traits.TRAITS)}")

    assertions = 0
    for trait in traits.TRAITS:
        assertions += 1
        forms = (trait.reader_callable, trait.reader_guard, trait.reader_deferred)
        present = [form for form in forms if form is not None]
        if len(present) != 1:
            fail(f"trait {trait.key!r}: exactly one reader form must be set, found {len(present)}")
            continue

        if trait.reader_callable is not None:
            _resolve_callable(trait.key, trait.reader_callable)
        elif trait.reader_guard is not None:
            module_name, column_name = trait.reader_guard
            _resolve_guard(trait.key, module_name, column_name)
        else:
            _resolve_deferred(trait.key, trait.reader_deferred)  # type: ignore[arg-type]

    if assertions == 0:
        fail("vacuous-proof: zero traits examined — parse broken, not repo clean")

    _report_and_exit(assertions)


if __name__ == "__main__":
    main()
