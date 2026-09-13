"""G1 check: isolation guarantees for the lore consultation surface
(TICKET-0085, BRIEF-0085-b and BRIEF-0085-c). Stdlib `ast` and text only,
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
R4 (purity, restated for the model-bearing half): `lore_selectors.py` and
`lore_query.py` still contain no `chat(` now that `lore_plan.py` exists --
the model lives in `lore_plan.py` only.
R5 (planner never reads canon): `lore_plan.py` contains no `select(`
against `Knowledge`, `Relation`, `NpcGoal` or `FactionMembership` -- the
planner never sees canon content, only the question and the selector list.
R6 (thin route): `cockpit/routes/lore.py` contains no `chat(` and no
`select(` -- the route orchestrates and validates, matching the
`routes/observation.py` doctrine.
R7 (no re-draft on resolve): the `/api/lore/resolve` handler's AST contains
no call to `draft_plan` -- disambiguation cannot shift the question.
R8 (selector description coverage): the key set of `lore_plan.py`'s
`_SELECTOR_DESCRIPTIONS` equals `lore_selectors.py`'s `SELECTORS`.
R9 (category vocabulary parity): the category literals in `lore_plan.py`'s
`_MENTION_CATEGORIES` equal the key set of `lore_resolve.py`'s
`_CATEGORY_ENTITY_TYPE`.
R15 (prompt loader scoped to prompt tables): every `select(` in
`lore_prompt.py` references only `PromptTemplate`/`PromptVersion` -- the
module that owns the Session for this chantier's prompt resolution must
never become a canon door by a later edit.

Every rule above is vacuity-guarded — a rule that locates zero items is a
FAILURE, not a silent pass. (R5-R7 are negative-existence checks over a
possibly-empty search space, not "at least one match" checks, so they carry
no vacuity guard of their own -- finding nothing IS the pass.)
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

LORE_SELECTORS_FILE = SRC / "lore_selectors.py"
LORE_QUERY_FILE = SRC / "lore_query.py"
LORE_PLAN_FILE = SRC / "lore_plan.py"
LORE_RESOLVE_FILE = SRC / "lore_resolve.py"
LORE_ROUTE_FILE = SRC / "cockpit" / "routes" / "lore.py"
LORE_PROMPT_FILE = SRC / "lore_prompt.py"
PURITY_FILES = (LORE_SELECTORS_FILE, LORE_QUERY_FILE)

_ALLOWED_PROMPT_MODELS = {"PromptTemplate", "PromptVersion"}

_FORBIDDEN_CANON_MODELS = {"Knowledge", "Relation", "NpcGoal", "FactionMembership"}

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
    """Same idiom as `lore_resolve.py`'s check: the tuple literal assigned
    to a module-level name, or None if `name` isn't a tuple literal."""
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
    """Same idiom as `lore_resolve.py`'s check: the dict literal assigned to
    a module-level name (last assignment wins), or None."""
    result = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            result = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            result = node.value
    return result if isinstance(result, ast.Dict) else None


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


def check_deterministic_half_still_pure() -> None:
    """R4: re-affirms R1's `chat(` absence now that `lore_plan.py` exists
    and does contain a model call -- guards against a future edit moving
    the call site into the deterministic half instead of deleting it there."""
    for path in PURITY_FILES:
        tree = _parse(path)
        if tree is None:
            continue
        hits = any(
            isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "chat"
            for node in ast.walk(tree)
        )
        if hits:
            fail(f"lore_isolation R4: {_rel(path)} contains chat( -- the model lives in lore_plan.py only")


def check_planner_never_reads_canon() -> None:
    """R5: no `select(` in `lore_plan.py` names `Knowledge`, `Relation`,
    `NpcGoal` or `FactionMembership` anywhere in its subtree. A negative
    existence check over a file with zero select( calls at all is the
    expected, passing state -- not a scanner malfunction (see module
    docstring)."""
    tree = _parse(LORE_PLAN_FILE)
    if tree is None:
        return
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "select"):
            continue
        names_in_call = {
            sub.id for sub in ast.walk(node) if isinstance(sub, ast.Name)
        } | {
            sub.attr for sub in ast.walk(node) if isinstance(sub, ast.Attribute)
        }
        forbidden = names_in_call & _FORBIDDEN_CANON_MODELS
        if forbidden:
            fail(
                f"lore_isolation R5: {_rel(LORE_PLAN_FILE)}:{node.lineno} -- "
                f"select( references canon model(s) {sorted(forbidden)!r} -- the planner never sees canon content"
            )


def check_route_is_thin() -> None:
    """R6: `cockpit/routes/lore.py` contains no `chat(` and no `select(`."""
    tree = _parse(LORE_ROUTE_FILE)
    if tree is None:
        return
    hits: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("chat", "select"):
            hits.add(f"{node.func.id}(")
    if hits:
        fail(
            f"lore_isolation R6: {_rel(LORE_ROUTE_FILE)} contains forbidden call(s) {sorted(hits)!r} -- "
            "the route orchestrates and validates, matching the routes/observation.py doctrine"
        )


def check_resolve_never_redrafts() -> None:
    """R7: the `/api/lore/resolve` handler's AST contains no call to
    `draft_plan` -- disambiguation cannot shift the question."""
    tree = _parse(LORE_ROUTE_FILE)
    if tree is None:
        return
    target: "ast.FunctionDef | None" = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "post"
                and any(isinstance(a, ast.Constant) and a.value == "/api/lore/resolve" for a in decorator.args)
            ):
                target = node
                break
        if target is not None:
            break
    if target is None:
        fail(f"lore_isolation R7: no route handler decorated with @router.post(\"/api/lore/resolve\") found in {_rel(LORE_ROUTE_FILE)}")
        return
    for node in ast.walk(target):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else None)
        if name == "draft_plan":
            fail(
                f"lore_isolation R7: {_rel(LORE_ROUTE_FILE)}:{node.lineno} -- "
                "the /api/lore/resolve handler calls draft_plan; it must reuse the client-held plan, never re-draft it"
            )


def check_selector_description_coverage() -> None:
    """R8: `lore_plan.py`'s `_SELECTOR_DESCRIPTIONS` key set equals
    `lore_selectors.py`'s `SELECTORS`."""
    plan_tree = _parse(LORE_PLAN_FILE)
    selectors_tree = _parse(LORE_SELECTORS_FILE)
    if plan_tree is None or selectors_tree is None:
        return
    descriptions = _named_dict(plan_tree, "_SELECTOR_DESCRIPTIONS")
    if descriptions is None:
        fail(f"lore_isolation R8: {_rel(LORE_PLAN_FILE)}: _SELECTOR_DESCRIPTIONS dict literal not found")
        return
    description_keys = {k.value for k in descriptions.keys if isinstance(k, ast.Constant)}
    if not description_keys:
        fail("lore_isolation R8: _SELECTOR_DESCRIPTIONS located but holds zero keys")
        return

    selectors_tuple = _tuple_assign(selectors_tree, "SELECTORS")
    if selectors_tuple is None:
        fail(f"lore_isolation R8: {_rel(LORE_SELECTORS_FILE)}: SELECTORS tuple not found")
        return
    selector_values = {e.value for e in selectors_tuple.elts if isinstance(e, ast.Constant)}
    if not selector_values:
        fail("lore_isolation R8: SELECTORS located but holds zero values")
        return

    missing = selector_values - description_keys
    if missing:
        fail(f"lore_isolation R8: SELECTORS value(s) {sorted(missing)!r} have no _SELECTOR_DESCRIPTIONS entry")
    orphan = description_keys - selector_values
    if orphan:
        fail(f"lore_isolation R8: _SELECTOR_DESCRIPTIONS key(s) {sorted(orphan)!r} are not in SELECTORS")


def check_category_vocabulary_parity() -> None:
    """R9: `lore_plan.py`'s `_MENTION_CATEGORIES` equals the key set of
    `lore_resolve.py`'s `_CATEGORY_ENTITY_TYPE`."""
    plan_tree = _parse(LORE_PLAN_FILE)
    resolve_tree = _parse(LORE_RESOLVE_FILE)
    if plan_tree is None or resolve_tree is None:
        return
    categories_tuple = _tuple_assign(plan_tree, "_MENTION_CATEGORIES")
    if categories_tuple is None:
        fail(f"lore_isolation R9: {_rel(LORE_PLAN_FILE)}: _MENTION_CATEGORIES tuple not found")
        return
    category_values = {e.value for e in categories_tuple.elts if isinstance(e, ast.Constant)}
    if not category_values:
        fail("lore_isolation R9: _MENTION_CATEGORIES located but holds zero values")
        return

    entity_type_dict = _named_dict(resolve_tree, "_CATEGORY_ENTITY_TYPE")
    if entity_type_dict is None:
        fail(f"lore_isolation R9: {_rel(LORE_RESOLVE_FILE)}: _CATEGORY_ENTITY_TYPE dict literal not found")
        return
    entity_type_keys = {k.value for k in entity_type_dict.keys if isinstance(k, ast.Constant)}
    if not entity_type_keys:
        fail("lore_isolation R9: _CATEGORY_ENTITY_TYPE located but holds zero keys")
        return

    missing = entity_type_keys - category_values
    if missing:
        fail(f"lore_isolation R9: _CATEGORY_ENTITY_TYPE key(s) {sorted(missing)!r} are missing from _MENTION_CATEGORIES")
    orphan = category_values - entity_type_keys
    if orphan:
        fail(f"lore_isolation R9: _MENTION_CATEGORIES value(s) {sorted(orphan)!r} are not in _CATEGORY_ENTITY_TYPE")


def check_prompt_loader_scoped_to_prompt_tables() -> None:
    """R15: every `select(` in `lore_prompt.py` references only
    `PromptTemplate`/`PromptVersion` -- the module that owns the Session for
    this chantier's prompt resolution must never become a canon door by a
    later edit."""
    tree = _parse(LORE_PROMPT_FILE)
    if tree is None:
        return
    select_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "select"
    ]
    if not select_calls:
        fail(f"lore_isolation R15: {_rel(LORE_PROMPT_FILE)} contains zero select( calls -- vacuous")
        return
    for node in select_calls:
        names = {
            sub.id for sub in ast.walk(node)
            if isinstance(sub, ast.Name) and sub.id[:1].isupper()
        }
        forbidden = names - _ALLOWED_PROMPT_MODELS
        if forbidden:
            fail(
                f"lore_isolation R15: {_rel(LORE_PROMPT_FILE)}:{node.lineno} -- "
                f"select( references non-prompt model(s) {sorted(forbidden)!r} -- "
                "the prompt loader must never become a canon door"
            )


def main() -> None:
    check_purity()
    check_world_scoped_at_construction()
    check_no_discoverable_detail()
    check_deterministic_half_still_pure()
    check_planner_never_reads_canon()
    check_route_is_thin()
    check_resolve_never_redrafts()
    check_selector_description_coverage()
    check_category_vocabulary_parity()
    check_prompt_loader_scoped_to_prompt_tables()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: lore_isolation — purity (R1, R4), world scoping at construction (R2), "
        "the discoverable_detail exclusion (R3), the planner's canon-blindness (R5), "
        "the route's thinness (R6), the no-redraft-on-resolve guard (R7), the "
        "selector/category vocabulary parity checks (R8, R9), and the prompt loader's "
        "scoping to prompt tables (R15) are all intact"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
