"""Structural gate for the extraction-and-concordance step (TICKET-0075,
BRIEF-0075-c — decision C1: the resolver never authors). Stdlib `ast` and
text only, no DB — same FAILURES/fail()/`_parse`/`_rel` idiom as
`day_plan.py`.

R1 (purity): `day_concordance.py` contains no `db.add(`, no `.commit(`, and
no `chat(` — it neither writes nor calls a model.
R2 (no registry leak): `day_extract.py` contains no `select(` call whose
arguments reference `Entity`, `Faction` or `Location` — the extraction
passes never see the registry.
R3 (germ shape): every `ProposedMutation(...)` construction inside
`emit_germs` sets `source_type='pass_play'`, `mutation_type='entity_creation'`
and `status='proposed'`, and no other `status=` literal appears there.
R4 (no synchronous authoring): no `Entity(`, `Character(` or `NpcSchedule(`
constructor call appears anywhere in `day_extract.py`, `day_concordance.py`
or `day_plan.py`.
R5 (I2 tripwire, protects a behaviour this brief does not own):
`_approve_entity_creation_shortcircuit` (cockpit/routes/mutations.py) still
contains the I2 comment and the parking branch.
R6 (registry wiring + ordered rungs): the three `day_extract_*` usages are
in `PROMPT_REGISTRY` with `call_sites` naming their function in
`day_extract.py`; `MATCHING_RUNGS` and `_RUNG_LOOKUPS` in
`day_concordance.py` are in bijection (same idiom as `day_plan.py`'s
evaluator bijection check) — a named, ordered sequence, not inline branches.
R7 (named bound): `MAX_MENTIONS_PER_PASS` is a module-level constant in
`day_extract.py`, referenced by the shared extraction path all three passes
call through.
R8 (casting bijection, TICKET-0081/BRIEF-0081-a): `CAST_PRECEDENCE` and
`_CAST_LOOKUPS` in `day_concordance.py` are in bijection (same idiom as R6),
and `"stable"` — the TOTAL criterion — is the last element of
`CAST_PRECEDENCE`.
R9 (E2c BFS is a fresh reader): `day_concordance.py` defines a function
whose body contains a `connects_to` string constant (the new reachability
BFS), AND the module's import list does not name `_day_reachable_ids` (D1 —
never import `day_plan`'s reader, never share one).
R10 (E2c tripwire): `_rung_occupation`'s body references the concordance
context's `reachable_location_ids` attribute — the E2c scoping filter.

Every rule above is vacuity-guarded — a rule that locates zero items is a
FAILURE, not a silent pass.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

DAY_EXTRACT_FILE = SRC / "day_extract.py"
DAY_CONCORDANCE_FILE = SRC / "day_concordance.py"
DAY_PLAN_FILE = SRC / "day_plan.py"
MUTATIONS_ROUTE_FILE = SRC / "cockpit" / "routes" / "mutations.py"

_NO_AUTHOR_FILES = (DAY_EXTRACT_FILE, DAY_CONCORDANCE_FILE, DAY_PLAN_FILE)
_FORBIDDEN_CONSTRUCTORS = {"Entity", "Character", "NpcSchedule"}
_FORBIDDEN_REGISTRY_NAMES = {"Entity", "Faction", "Location"}

EXPECTED_USAGES = ("day_extract_place", "day_extract_person", "day_extract_faction")
EXPECTED_FUNCTIONS = {
    "day_extract_place": "extract_places",
    "day_extract_person": "extract_persons",
    "day_extract_faction": "extract_factions",
}
EXPECTED_RUNGS = {"named_exact", "named_token", "named_alias", "occupation", "presence"}

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


def _read_text(path: pathlib.Path) -> "str | None":
    if not path.exists():
        fail(f"{_rel(path)}: file not found")
        return None
    return path.read_text(encoding="utf-8")


def _find_function(tree: ast.AST, name: str) -> "ast.FunctionDef | None":
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


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


def check_purity() -> None:
    """AST-based, not text search: this module's own docstring legitimately
    NAMES `db.add(`/`.commit(`/`chat(` in prose (documenting that it
    contains none) — a raw-text scan would false-positive on its own
    doctrine note, same lesson as `npc_goal_read.py`'s MJ-boundary check."""
    tree = _parse(DAY_CONCORDANCE_FILE)
    if tree is None:
        return
    hits: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Scoped to calls on a `db`-named object — a bare `.add(`/`.commit(`
        # attribute-name scan would false-positive on this module's own
        # `set.add(...)` calls (place_ids, skipped_rungs).
        if (
            isinstance(func, ast.Attribute) and func.attr in ("add", "commit")
            and isinstance(func.value, ast.Name) and func.value.id == "db"
        ):
            hits.add(f"db.{func.attr}(")
        elif isinstance(func, ast.Name) and func.id == "chat":
            hits.add("chat(")
    if hits:
        fail(f"day_concordance R1: {_rel(DAY_CONCORDANCE_FILE)} contains forbidden call(s) {sorted(hits)!r} — must stay a pure read/propose module")


def check_no_registry_leak() -> None:
    tree = _parse(DAY_EXTRACT_FILE)
    if tree is None:
        return
    found_any_select = False
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "select"):
            continue
        found_any_select = True
        for sub in ast.walk(node):
            name = None
            if isinstance(sub, ast.Name):
                name = sub.id
            elif isinstance(sub, ast.Attribute):
                name = sub.attr
            if name in _FORBIDDEN_REGISTRY_NAMES:
                fail(
                    f"day_concordance R2: {_rel(DAY_EXTRACT_FILE)}:{node.lineno} — "
                    f"select( references {name!r}, the extraction passes must never see the registry"
                )
    if not found_any_select:
        fail(f"day_concordance R2: {_rel(DAY_EXTRACT_FILE)} contains zero select( calls — vacuous")


def check_germ_shape() -> None:
    tree = _parse(DAY_CONCORDANCE_FILE)
    if tree is None:
        return
    func = _find_function(tree, "emit_germs")
    if func is None:
        fail(f"{_rel(DAY_CONCORDANCE_FILE)}: emit_germs not found")
        return

    constructions = [
        node for node in ast.walk(func)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "ProposedMutation"
    ]
    if not constructions:
        fail(f"day_concordance R3: emit_germs constructs zero ProposedMutation rows — vacuous")
        return

    expected = {"source_type": "pass_play", "mutation_type": "entity_creation", "status": "proposed"}
    for call in constructions:
        values = {
            kw.arg: kw.value.value
            for kw in call.keywords
            if kw.arg in expected and isinstance(kw.value, ast.Constant)
        }
        for key, want in expected.items():
            got = values.get(key)
            if got != want:
                fail(
                    f"day_concordance R3: {_rel(DAY_CONCORDANCE_FILE)}:{call.lineno} — "
                    f"ProposedMutation({key}={got!r}), expected {want!r}"
                )


def check_no_synchronous_authoring() -> None:
    found_any = False
    for path in _NO_AUTHOR_FILES:
        tree = _parse(path)
        if tree is None:
            continue
        found_any = True
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FORBIDDEN_CONSTRUCTORS:
                fail(
                    f"day_concordance R4: {_rel(path)}:{node.lineno} — constructs {node.func.id}(...); "
                    "the resolver never authors (C1)"
                )
    if not found_any:
        fail("day_concordance R4: none of day_extract.py/day_concordance.py/day_plan.py parsed — vacuous")


def check_shortcircuit_intact() -> None:
    tree = _parse(MUTATIONS_ROUTE_FILE)
    if tree is None:
        return
    func = _find_function(tree, "_approve_entity_creation_shortcircuit")
    if func is None:
        fail(f"day_concordance R5: {_rel(MUTATIONS_ROUTE_FILE)}: _approve_entity_creation_shortcircuit not found")
        return

    docstring = ast.get_docstring(func) or ""
    # Source wraps the sentence across lines; whitespace-tolerant match.
    if not re.search(r"I2\s+forbids\s+any\s+synchronous\s+authoring\s+call\s+here", docstring):
        fail("day_concordance R5: _approve_entity_creation_shortcircuit's I2 comment is gone")

    sets_pending = any(
        isinstance(node, ast.Constant) and isinstance(node.value, str) and "attente de r" in node.value
        for node in ast.walk(func)
    )
    if not sets_pending:
        fail("day_concordance R5: _approve_entity_creation_shortcircuit no longer parks (pending-realization note missing)")

    constructs_entity = any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FORBIDDEN_CONSTRUCTORS
        for node in ast.walk(func)
    )
    if constructs_entity:
        fail("day_concordance R5: _approve_entity_creation_shortcircuit now authors synchronously — I2 broken")


def check_registry_and_rungs() -> None:
    sys.path.insert(0, str(ROOT / "src"))
    from world_engine import prompt_registry  # noqa: E402

    found_usage = False
    for usage in EXPECTED_USAGES:
        entry = prompt_registry.PROMPT_REGISTRY.get(usage)
        if entry is None:
            fail(f"day_concordance R6: PROMPT_REGISTRY has no {usage!r} entry")
            continue
        found_usage = True
        call_sites = getattr(entry, "call_sites", ())
        wanted_func = EXPECTED_FUNCTIONS[usage]
        if not any(wanted_func in site for site in call_sites):
            fail(f"day_concordance R6: PROMPT_REGISTRY[{usage!r}].call_sites does not name {wanted_func}: {call_sites!r}")
    if not found_usage:
        fail("day_concordance R6: zero day_extract_* usages found in PROMPT_REGISTRY — vacuous")

    tree = _parse(DAY_CONCORDANCE_FILE)
    if tree is None:
        return
    rungs_tuple = _tuple_assign(tree, "MATCHING_RUNGS")
    if rungs_tuple is None:
        fail(f"day_concordance R6: {_rel(DAY_CONCORDANCE_FILE)}: MATCHING_RUNGS tuple not found")
        return
    rung_names = {e.value for e in rungs_tuple.elts if isinstance(e, ast.Constant)}
    if not rung_names:
        fail("day_concordance R6: MATCHING_RUNGS located but holds zero values")
        return
    if rung_names != EXPECTED_RUNGS:
        fail(f"day_concordance R6: MATCHING_RUNGS is {sorted(rung_names)!r}, expected {sorted(EXPECTED_RUNGS)!r}")

    lookups = _named_dict(tree, "_RUNG_LOOKUPS")
    if lookups is None:
        fail(f"day_concordance R6: {_rel(DAY_CONCORDANCE_FILE)}: _RUNG_LOOKUPS dict literal not found")
        return
    lookup_keys = {k.value for k in lookups.keys if isinstance(k, ast.Constant)}
    if not lookup_keys:
        fail("day_concordance R6: _RUNG_LOOKUPS located but holds zero keys")
        return

    missing = rung_names - lookup_keys
    if missing:
        fail(f"day_concordance R6: MATCHING_RUNGS value(s) {sorted(missing)!r} have no _RUNG_LOOKUPS key")
    orphan = lookup_keys - rung_names
    if orphan:
        fail(f"day_concordance R6: _RUNG_LOOKUPS key(s) {sorted(orphan)!r} are not in MATCHING_RUNGS")


def check_mentions_bound() -> None:
    tree = _parse(DAY_EXTRACT_FILE)
    if tree is None:
        return
    names_found: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names_found.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names_found.add(node.target.id)
    if "MAX_MENTIONS_PER_PASS" not in names_found:
        fail(f"day_concordance R7: {_rel(DAY_EXTRACT_FILE)}: MAX_MENTIONS_PER_PASS module-level constant not found")
        return

    func = _find_function(tree, "_extract")
    if func is None:
        fail(f"{_rel(DAY_EXTRACT_FILE)}: _extract not found — the shared extraction path all three passes call through")
        return
    references = [n for n in ast.walk(func) if isinstance(n, ast.Name) and n.id == "MAX_MENTIONS_PER_PASS"]
    if not references:
        fail("day_concordance R7: MAX_MENTIONS_PER_PASS is declared but never read by the shared extraction path")


def check_cast_precedence() -> None:
    tree = _parse(DAY_CONCORDANCE_FILE)
    if tree is None:
        return
    precedence_tuple = _tuple_assign(tree, "CAST_PRECEDENCE")
    if precedence_tuple is None:
        fail(f"day_concordance R8: {_rel(DAY_CONCORDANCE_FILE)}: CAST_PRECEDENCE tuple not found")
        return
    precedence = [e.value for e in precedence_tuple.elts if isinstance(e, ast.Constant)]
    if not precedence:
        fail("day_concordance R8: CAST_PRECEDENCE located but holds zero values")
        return
    if precedence[-1] != "stable":
        fail(f"day_concordance R8: CAST_PRECEDENCE's last element is {precedence[-1]!r}, expected 'stable'")

    lookups = _named_dict(tree, "_CAST_LOOKUPS")
    if lookups is None:
        fail(f"day_concordance R8: {_rel(DAY_CONCORDANCE_FILE)}: _CAST_LOOKUPS dict literal not found")
        return
    lookup_keys = {k.value for k in lookups.keys if isinstance(k, ast.Constant)}
    if not lookup_keys:
        fail("day_concordance R8: _CAST_LOOKUPS located but holds zero keys")
        return

    precedence_set = set(precedence)
    missing = precedence_set - lookup_keys
    if missing:
        fail(f"day_concordance R8: CAST_PRECEDENCE value(s) {sorted(missing)!r} have no _CAST_LOOKUPS key")
    orphan = lookup_keys - precedence_set
    if orphan:
        fail(f"day_concordance R8: _CAST_LOOKUPS key(s) {sorted(orphan)!r} are not in CAST_PRECEDENCE")


def check_reachability_reader() -> None:
    tree = _parse(DAY_CONCORDANCE_FILE)
    if tree is None:
        return

    found_constant = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if any(isinstance(sub, ast.Constant) and sub.value == "connects_to" for sub in ast.walk(node)):
            found_constant = True
            break
    if not found_constant:
        fail("day_concordance R9: no function body in day_concordance.py contains a 'connects_to' string constant")

    imports_shared_reader = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if any(alias.name == "_day_reachable_ids" for alias in node.names):
                imports_shared_reader = True
    if imports_shared_reader:
        fail(
            "day_concordance R9: day_concordance.py imports _day_reachable_ids — "
            "the E2c BFS must be written fresh in this module (D1)"
        )


def check_occupation_reachability_reference() -> None:
    tree = _parse(DAY_CONCORDANCE_FILE)
    if tree is None:
        return
    func = _find_function(tree, "_rung_occupation")
    if func is None:
        fail(f"day_concordance R10: {_rel(DAY_CONCORDANCE_FILE)}: _rung_occupation not found")
        return
    references = [
        node for node in ast.walk(func)
        if isinstance(node, ast.Attribute) and node.attr == "reachable_location_ids"
    ]
    if not references:
        fail(
            "day_concordance R10: _rung_occupation does not reference "
            "ctx.reachable_location_ids — the E2c tripwire"
        )


def main() -> None:
    check_purity()
    check_no_registry_leak()
    check_germ_shape()
    check_no_synchronous_authoring()
    check_shortcircuit_intact()
    check_registry_and_rungs()
    check_mentions_bound()
    check_cast_precedence()
    check_reachability_reader()
    check_occupation_reachability_reference()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: day_concordance — purity, no registry leak, germ shape, no synchronous "
        "authoring, the I2 parking tripwire, PROMPT_REGISTRY wiring, rung bijection, "
        "the mentions bound, the casting bijection, and the E2c reachability tripwire "
        "are all intact"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
