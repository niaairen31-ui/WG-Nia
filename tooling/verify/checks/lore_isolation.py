"""G1 check: isolation guarantees for the lore consultation surface's
deterministic half (TICKET-0085, BRIEF-0085-b). Stdlib `ast` and text only,
no DB — same FAILURES/fail()/`_parse`/`_rel` idiom as `lore_resolve.py`'s
check.

R1 (purity): `lore_selectors.py` and `lore_query.py` contain no `chat(`, no
`db.add(`, no `.commit(` -- this is a read-only pipeline half; no model call
and no write exists on it.
R2 (world scoping at construction): every `select(` in `lore_selectors.py`
has a world constraint among its `.where(` arguments, or joins `Entity`
with one.
R3 (no discoverable_detail): no `discoverable_detail` identifier appears in
`lore_selectors.py` -- that table is structurally excluded from every
assembler, without exception, and this module is no exception either.

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
PURITY_FILES = (LORE_SELECTORS_FILE, LORE_QUERY_FILE)

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


def check_purity() -> None:
    """AST-based, not text search: this module's own docstring legitimately
    NAMES `db.add(`/`.commit(`/`chat(` in prose -- a raw-text scan would
    false-positive on its own doctrine note, same lesson as
    `lore_resolve.py`'s R1."""
    for path in PURITY_FILES:
        tree = _parse(path)
        if tree is None:
            continue
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
            fail(f"lore_isolation R1: {_rel(path)} contains forbidden call(s) {sorted(hits)!r} -- must stay pure and read-only")


def check_world_scoped_at_construction() -> None:
    tree = _parse(LORE_SELECTORS_FILE)
    if tree is None:
        return
    select_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "select"
    ]
    if not select_calls:
        fail(f"lore_isolation R2: {_rel(LORE_SELECTORS_FILE)} contains zero select( calls -- vacuous")
        return

    for node in select_calls:
        # Walk up from the select( call to the enclosing `.where(...)` call,
        # if any, and require `world_id` (or a join to Entity carrying it)
        # to appear among ITS arguments -- never merely somewhere in the
        # surrounding function, which would allow a post-fetch filter to
        # satisfy a laxer test without satisfying R2's intent. The select(
        # may sit behind an intervening `.join(...)` in the fluent chain
        # (`select(X).join(Y, ...).where(...)`), so membership in the
        # receiver subtree is checked rather than direct identity.
        where_call = None
        for parent in ast.walk(tree):
            if not isinstance(parent, ast.Call):
                continue
            if not (isinstance(parent.func, ast.Attribute) and parent.func.attr == "where"):
                continue
            if any(sub is node for sub in ast.walk(parent.func.value)):
                where_call = parent
                break
        if where_call is None:
            fail(f"lore_isolation R2: {_rel(LORE_SELECTORS_FILE)}:{node.lineno} -- select( with no .where( call")
            continue
        names_in_where = {
            sub.id if isinstance(sub, ast.Name) else sub.attr
            for sub in ast.walk(where_call)
            if isinstance(sub, (ast.Name, ast.Attribute))
        }
        if "world_id" not in names_in_where and "Entity" not in names_in_where:
            fail(
                f"lore_isolation R2: {_rel(LORE_SELECTORS_FILE)}:{node.lineno} -- "
                "select(...).where(...) references neither world_id nor a join to Entity -- not world-scoped at construction"
            )


def check_no_discoverable_detail() -> None:
    source = LORE_SELECTORS_FILE.read_text(encoding="utf-8") if LORE_SELECTORS_FILE.exists() else None
    if source is None:
        fail(f"lore_isolation R3: {_rel(LORE_SELECTORS_FILE)}: file not found")
        return
    if "discoverable_detail" in source.lower():
        fail(
            f"lore_isolation R3: {_rel(LORE_SELECTORS_FILE)} references discoverable_detail -- "
            "that table is structurally excluded from every assembler, without exception"
        )


def main() -> None:
    check_purity()
    check_world_scoped_at_construction()
    check_no_discoverable_detail()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: lore_isolation — purity, world scoping at construction, and the "
        "discoverable_detail exclusion are all intact"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
