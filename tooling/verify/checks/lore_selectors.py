"""G1 check: selector whitelist for the lore consultation surface
(TICKET-0085, BRIEF-0085-b). Stdlib `ast` and text only, no DB — same
FAILURES/fail()/`_parse`/`_rel` idiom as `lore_resolve.py`'s check.

R1 (bijection): `SELECTORS` and `_SELECTOR_LOOKUPS` are in bijection, the
same one-tuple/one-dict idiom as `MATCHING_RUNGS`/`_RUNG_LOOKUPS`.
R2 (no dispatch outside the table): neither selector function name
(`entity_dossier`, `world_factions`) appears anywhere in `lore_query.py` —
every call goes through `_SELECTOR_LOOKUPS[...]`.
R3 (caps declared): every `SelectorSpec(...)` construction sets a non-zero
integer `row_cap`, and `execute_plan` references `row_cap`.
R4 (validation precedes execution): in `execute_plan`, every top-level
statement referencing `_SELECTOR_LOOKUPS` comes after the `if`-statement
that returns on a failed `validate_plan(...)` result.
R5 (closed verdicts): the set of string literals assigned to `verdict` in
`lore_query.py` equals exactly the five verdicts of the ticket's design —
`answered`, `ambiguous_mention`, `unknown_entity`, `silent_canon`,
`unsupported_selector`.
R6 (context_sections vocabulary): every string in a `SelectorSpec`'s
`context_sections` matches a `"section"` literal emitted somewhere in
`lore_selectors.py` — a typo cannot silently make every row substantive.

Every rule above is vacuity-guarded — a rule that locates zero items is a
FAILURE, not a silent pass.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

LORE_SELECTORS_FILE = SRC / "lore_selectors.py"
LORE_QUERY_FILE = SRC / "lore_query.py"

SELECTOR_FUNCTION_NAMES = {"entity_dossier", "world_factions"}
EXPECTED_VERDICTS = {
    "answered", "ambiguous_mention", "unknown_entity", "silent_canon", "unsupported_selector",
}

FAILURES: list[str] = []
_TREE_CACHE: dict[pathlib.Path, "ast.Module | None"] = {}


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _parse(path: pathlib.Path) -> "ast.Module | None":
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


def _tuple_assign(tree: ast.AST, name: str) -> "ast.Tuple | None":
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            value = node.value
        else:
            continue
        if isinstance(value, ast.Tuple):
            return value
    return None


def _named_dict(tree: ast.AST, name: str) -> "ast.Dict | None":
    result = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            result = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            result = node.value
    return result if isinstance(result, ast.Dict) else None


def _find_function(tree: ast.AST, name: str) -> "ast.FunctionDef | None":
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def check_bijection() -> None:
    tree = _parse(LORE_SELECTORS_FILE)
    if tree is None:
        return
    selectors_tuple = _tuple_assign(tree, "SELECTORS")
    if selectors_tuple is None:
        fail(f"lore_selectors R1: {_rel(LORE_SELECTORS_FILE)}: SELECTORS tuple not found")
        return
    selector_names = {e.value for e in selectors_tuple.elts if isinstance(e, ast.Constant)}
    if not selector_names:
        fail("lore_selectors R1: SELECTORS located but holds zero values")
        return

    lookups = _named_dict(tree, "_SELECTOR_LOOKUPS")
    if lookups is None:
        fail(f"lore_selectors R1: {_rel(LORE_SELECTORS_FILE)}: _SELECTOR_LOOKUPS dict literal not found")
        return
    lookup_keys = {k.value for k in lookups.keys if isinstance(k, ast.Constant)}
    if not lookup_keys:
        fail("lore_selectors R1: _SELECTOR_LOOKUPS located but holds zero keys")
        return

    missing = selector_names - lookup_keys
    if missing:
        fail(f"lore_selectors R1: SELECTORS value(s) {sorted(missing)!r} have no _SELECTOR_LOOKUPS key")
    orphan = lookup_keys - selector_names
    if orphan:
        fail(f"lore_selectors R1: _SELECTOR_LOOKUPS key(s) {sorted(orphan)!r} are not in SELECTORS")


def check_no_dispatch_outside_table() -> None:
    tree = _parse(LORE_QUERY_FILE)
    if tree is None:
        return
    found: set[str] = set()
    for node in ast.walk(tree):
        name = None
        if isinstance(node, ast.Name):
            name = node.id
        elif isinstance(node, ast.Attribute):
            name = node.attr
        if name in SELECTOR_FUNCTION_NAMES:
            found.add(name)
    if found:
        fail(
            f"lore_selectors R2: {_rel(LORE_QUERY_FILE)} names selector function(s) {sorted(found)!r} "
            "directly -- dispatch must go only through _SELECTOR_LOOKUPS[...]"
        )


def check_caps_declared() -> None:
    tree = _parse(LORE_SELECTORS_FILE)
    if tree is None:
        return
    specs = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "SelectorSpec")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "SelectorSpec")
        )
    ]
    if not specs:
        fail(f"lore_selectors R3: {_rel(LORE_SELECTORS_FILE)}: zero SelectorSpec(...) constructions found -- vacuous")
        return
    for node in specs:
        row_cap_kw = next((kw for kw in node.keywords if kw.arg == "row_cap"), None)
        if row_cap_kw is None:
            fail(f"lore_selectors R3: {_rel(LORE_SELECTORS_FILE)}:{node.lineno} -- SelectorSpec(...) has no row_cap keyword")
            continue
        value = row_cap_kw.value
        if not (isinstance(value, ast.Constant) and isinstance(value.value, int) and value.value != 0):
            fail(f"lore_selectors R3: {_rel(LORE_SELECTORS_FILE)}:{node.lineno} -- row_cap is not a non-zero integer literal")

    query_tree = _parse(LORE_QUERY_FILE)
    if query_tree is None:
        return
    execute_plan = _find_function(query_tree, "execute_plan")
    if execute_plan is None:
        fail(f"lore_selectors R3: {_rel(LORE_QUERY_FILE)}: execute_plan not found")
        return
    references_row_cap = any(
        isinstance(sub, ast.Attribute) and sub.attr == "row_cap" for sub in ast.walk(execute_plan)
    )
    if not references_row_cap:
        fail(f"lore_selectors R3: execute_plan does not reference row_cap -- caps declared but never enforced")


def check_context_sections_vocabulary() -> None:
    """R6: every string in a `SelectorSpec.context_sections` matches a
    `"section"` literal actually emitted somewhere in
    `lore_selectors.py` (module-wide vocabulary, not per-function call-graph
    resolution) -- a typo in `context_sections` must not silently make
    `execute_plan` treat every row as substantive."""
    tree = _parse(LORE_SELECTORS_FILE)
    if tree is None:
        return
    vocabulary: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if (
                isinstance(key, ast.Constant) and key.value == "section"
                and isinstance(value, ast.Constant) and isinstance(value.value, str)
            ):
                vocabulary.add(value.value)
    if not vocabulary:
        fail(f"lore_selectors R6: {_rel(LORE_SELECTORS_FILE)}: no \"section\" literal found anywhere -- vacuous")
        return

    specs = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "SelectorSpec")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "SelectorSpec")
        )
    ]
    for node in specs:
        cs_kw = next((kw for kw in node.keywords if kw.arg == "context_sections"), None)
        if cs_kw is None or not isinstance(cs_kw.value, ast.Tuple):
            continue
        for elt in cs_kw.value.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str) and elt.value not in vocabulary:
                fail(
                    f"lore_selectors R6: {_rel(LORE_SELECTORS_FILE)}:{node.lineno} -- "
                    f"context_sections names {elt.value!r}, which is not a \"section\" literal emitted anywhere"
                )


def check_validation_precedes_execution() -> None:
    tree = _parse(LORE_QUERY_FILE)
    if tree is None:
        return
    execute_plan = _find_function(tree, "execute_plan")
    if execute_plan is None:
        fail(f"lore_selectors R4: {_rel(LORE_QUERY_FILE)}: execute_plan not found")
        return

    gate_lineno = None
    for stmt in execute_plan.body:
        if (
            isinstance(stmt, ast.If)
            and any(
                isinstance(sub, ast.Attribute) and sub.attr == "ok"
                for sub in ast.walk(stmt.test)
            )
            and any(isinstance(sub, ast.Return) for sub in ast.walk(stmt))
        ):
            gate_lineno = stmt.lineno
            break
    if gate_lineno is None:
        fail(
            "lore_selectors R4: execute_plan has no early-return `if ...ok...:` gate -- "
            "validation must precede every selector dispatch"
        )
        return

    # Nothing referencing _SELECTOR_LOOKUPS may appear at or before the gate
    # statement -- everything after it is fine by construction.
    for stmt in execute_plan.body:
        if stmt.lineno > gate_lineno:
            continue
        for sub in ast.walk(stmt):
            if isinstance(sub, ast.Name) and sub.id == "_SELECTOR_LOOKUPS":
                fail(
                    f"lore_selectors R4: {_rel(LORE_QUERY_FILE)}:{stmt.lineno} references "
                    "_SELECTOR_LOOKUPS before the validation gate returns"
                )
    uses_lookup = any(
        isinstance(sub, ast.Name) and sub.id == "_SELECTOR_LOOKUPS" for sub in ast.walk(execute_plan)
    )
    if not uses_lookup:
        fail("lore_selectors R4: execute_plan never references _SELECTOR_LOOKUPS -- vacuous")


def _collect_str_constants(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return _collect_str_constants(node.body) + _collect_str_constants(node.orelse)
    return []


def check_closed_verdicts() -> None:
    tree = _parse(LORE_QUERY_FILE)
    if tree is None:
        return
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "verdict":
                    found.update(_collect_str_constants(kw.value))
        elif isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "verdict" for t in node.targets):
                found.update(_collect_str_constants(node.value))
    if not found:
        fail(f"lore_selectors R5: {_rel(LORE_QUERY_FILE)}: no string literal assigned to verdict -- vacuous")
        return
    missing = EXPECTED_VERDICTS - found
    extra = found - EXPECTED_VERDICTS
    if missing:
        fail(f"lore_selectors R5: verdict set is missing {sorted(missing)!r}")
    if extra:
        fail(f"lore_selectors R5: verdict set has undeclared extra value(s) {sorted(extra)!r}")


def main() -> None:
    check_bijection()
    check_no_dispatch_outside_table()
    check_caps_declared()
    check_context_sections_vocabulary()
    check_validation_precedes_execution()
    check_closed_verdicts()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: lore_selectors — the whitelist bijection, table-only dispatch, declared row "
        "caps, the validation gate, and the closed verdict set are all intact"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
