"""G1 check: named-rung extraction for the lore consultation resolver
(TICKET-0085, BRIEF-0085-a). Stdlib `ast` and text only, no DB — same
FAILURES/fail()/`_parse`/`_rel` idiom as `day_concordance.py`'s check.

R1 (purity): `lore_resolve.py` contains no `db.add(`, no `.commit(`, no
`chat(` — a lookup cannot hallucinate an id, and this module never writes.
R2 (no casting): `lore_resolve.py` contains none of the identifiers
`_cast_one`, `CAST_PRECEDENCE`, `who_is_at`, `Character` — casting is play
semantics and does not exist on this path.
R3 (bijection): `NAMED_RUNGS` and `_NAMED_RUNG_LOOKUPS` are in bijection —
the same one-tuple/one-dict idiom as `MATCHING_RUNGS`/`_RUNG_LOOKUPS`.
R4 (world scoping at construction): every `select(` in `lore_resolve.py` has
`world_id` among its `.where(` arguments — never a post-fetch filter.
R5 (no duplicate normalizer): `_normalize_surface` no longer appears as a
`def` in `day_concordance.py` — it moved to `lore_resolve.normalize_surface`
and is imported back, never duplicated.

Every rule above is vacuity-guarded — a rule that locates zero items is a
FAILURE, not a silent pass.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

LORE_RESOLVE_FILE = SRC / "lore_resolve.py"
DAY_CONCORDANCE_FILE = SRC / "day_concordance.py"

_FORBIDDEN_CASTING_NAMES = {"_cast_one", "CAST_PRECEDENCE", "who_is_at", "Character"}

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


def check_purity() -> None:
    """AST-based, not text search: this module's own docstring legitimately
    NAMES `db.add(`/`.commit(`/`chat(` in prose (documenting that it
    contains none) — a raw-text scan would false-positive on its own
    doctrine note, same lesson as `day_concordance.py`'s R1."""
    tree = _parse(LORE_RESOLVE_FILE)
    if tree is None:
        return
    hits: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute) and func.attr in ("add", "commit")
            and isinstance(func.value, ast.Name) and func.value.id == "db"
        ):
            hits.add(f"db.{func.attr}(")
        elif isinstance(func, ast.Name) and func.id == "chat":
            hits.add("chat(")
    if hits:
        fail(f"lore_resolve R1: {_rel(LORE_RESOLVE_FILE)} contains forbidden call(s) {sorted(hits)!r} — must stay a pure read module")


def check_no_casting() -> None:
    tree = _parse(LORE_RESOLVE_FILE)
    if tree is None:
        return
    found: set[str] = set()
    for node in ast.walk(tree):
        name = None
        if isinstance(node, ast.Name):
            name = node.id
        elif isinstance(node, ast.Attribute):
            name = node.attr
        if name in _FORBIDDEN_CASTING_NAMES:
            found.add(name)
    if found:
        fail(
            f"lore_resolve R2: {_rel(LORE_RESOLVE_FILE)} references forbidden casting identifier(s) "
            f"{sorted(found)!r} — casting is play semantics and does not exist on this path"
        )


def check_named_rung_bijection() -> None:
    tree = _parse(LORE_RESOLVE_FILE)
    if tree is None:
        return
    rungs_tuple = _tuple_assign(tree, "NAMED_RUNGS")
    if rungs_tuple is None:
        fail(f"lore_resolve R3: {_rel(LORE_RESOLVE_FILE)}: NAMED_RUNGS tuple not found")
        return
    rung_names = {e.value for e in rungs_tuple.elts if isinstance(e, ast.Constant)}
    if not rung_names:
        fail("lore_resolve R3: NAMED_RUNGS located but holds zero values")
        return

    lookups = _named_dict(tree, "_NAMED_RUNG_LOOKUPS")
    if lookups is None:
        fail(f"lore_resolve R3: {_rel(LORE_RESOLVE_FILE)}: _NAMED_RUNG_LOOKUPS dict literal not found")
        return
    lookup_keys = {k.value for k in lookups.keys if isinstance(k, ast.Constant)}
    if not lookup_keys:
        fail("lore_resolve R3: _NAMED_RUNG_LOOKUPS located but holds zero keys")
        return

    missing = rung_names - lookup_keys
    if missing:
        fail(f"lore_resolve R3: NAMED_RUNGS value(s) {sorted(missing)!r} have no _NAMED_RUNG_LOOKUPS key")
    orphan = lookup_keys - rung_names
    if orphan:
        fail(f"lore_resolve R3: _NAMED_RUNG_LOOKUPS key(s) {sorted(orphan)!r} are not in NAMED_RUNGS")


def check_world_scoped_at_construction() -> None:
    tree = _parse(LORE_RESOLVE_FILE)
    if tree is None:
        return
    select_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "select"
    ]
    if not select_calls:
        fail(f"lore_resolve R4: {_rel(LORE_RESOLVE_FILE)} contains zero select( calls — vacuous")
        return

    for node in select_calls:
        # Walk up from the select( call to the enclosing `.where(...)` call,
        # if any, and require `world_id` to appear among ITS arguments —
        # never merely somewhere in the surrounding function (a post-fetch
        # filter would satisfy that laxer test without satisfying R4's
        # intent).
        where_call = None
        current = node
        for parent in ast.walk(tree):
            if not isinstance(parent, ast.Call):
                continue
            if not (isinstance(parent.func, ast.Attribute) and parent.func.attr == "where"):
                continue
            if parent.func.value is current:
                where_call = parent
                break
        if where_call is None:
            fail(f"lore_resolve R4: {_rel(LORE_RESOLVE_FILE)}:{node.lineno} — select( with no .where( call")
            continue
        names_in_where = {
            sub.id if isinstance(sub, ast.Name) else sub.attr
            for sub in ast.walk(where_call)
            if isinstance(sub, (ast.Name, ast.Attribute))
        }
        if "world_id" not in names_in_where:
            fail(
                f"lore_resolve R4: {_rel(LORE_RESOLVE_FILE)}:{node.lineno} — "
                "select(...).where(...) does not reference world_id — not world-scoped at construction"
            )


def check_no_duplicate_normalizer() -> None:
    tree = _parse(DAY_CONCORDANCE_FILE)
    if tree is None:
        return
    func = _find_function(tree, "_normalize_surface")
    if func is not None:
        fail(
            f"lore_resolve R5: {_rel(DAY_CONCORDANCE_FILE)} still defines _normalize_surface — "
            "it must be imported from lore_resolve, never duplicated"
        )


def main() -> None:
    check_purity()
    check_no_casting()
    check_named_rung_bijection()
    check_world_scoped_at_construction()
    check_no_duplicate_normalizer()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: lore_resolve — purity, no casting, the named-rung bijection, world scoping "
        "at construction, and the no-duplicate-normalizer guard are all intact"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
