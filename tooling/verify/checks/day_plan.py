"""Structural gate for the day-plan emission-and-budget step (TICKET-0075,
BRIEF-0075-b). Stdlib `ast` and text only, no DB — same FAILURES/fail()/
`_parse`/`_tuple_assign` idiom as `npc_schedule.py`.

R1 (evaluator bijection, `_SOURCE_LOOKUPS` precedent): `_EVALUATORS`' key set
equals `REQUIREMENT_TYPES` exactly, in both directions.
R2 (type vocabulary): `agenda_step_requirement`'s `type` CHECK
(`ck_agenda_step_requirement_type`) quotes exactly `REQUIREMENT_TYPES`'s four
values.
R3 (shape CHECK): `ck_agenda_step_requirement_shape` exists and its
expression mentions all six (type, column) pairs from the per-type shape
rule.
R4 (budget derivation): `DAY_BUDGET_SLOTS` is a `len(...)` derivation, never
a numeric literal.
R5 (P2 / positional read exclusion): `day_plan.py` contains no reference to
`current_phase`, and no `select(` against `NpcSchedule`.
R6 (the positional wall, BRIEF-0074-a-amendment-1 — the single most important
check in this brief): `Agenda`/`AgendaStep` declare no location-named field,
and `schedule_reads.py` references neither `Agenda`, `AgendaStep` nor
`AgendaStepRequirement`.
R7 (purity): `budget_cut`'s body contains no `db`, `select(`, `chat(`,
`datetime`, or `randint`.
R8 (parse + registry wiring): `emit_plan` routes through `llm_parse`, and
`day_plan` appears in `PROMPT_REGISTRY` with a `call_sites` entry naming it.
R9 (named bounds): `MAX_PLAN_STEPS`/`DAY_BUDGET_SLOTS` are module-level
constants; the route references `DAY_BUDGET_SLOTS` rather than restating it.
R10 (BRIEF-0075-b-amendment-1 — D1 made structural for this consumer):
`day_plan.py` imports none of the sibling `connects_to` readers
(`_location_neighbours`, `_reachable_locations`, `_live_neighbour_ids`), and
declares its own `_day_reachable_ids` BFS. Do NOT add a check asserting
`day_plan.py` REUSES an existing traversal — that would encode the
superseded original instruction.

Every rule carries an anti-vacuity guard: a rule that locates zero items is a
FAILURE, not a silent pass.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

DAY_PLAN_FILE = SRC / "day_plan.py"
CANON_FILE = SRC / "models" / "canon.py"
CONFIG_FILE = SRC / "models" / "config.py"
SCHEDULE_READS_FILE = SRC / "schedule_reads.py"
DAY_ROUTE_FILE = SRC / "cockpit" / "routes" / "day.py"

# AgendaStep/AgendaStepRequirement live in config.py, not canon.py (module_budget
# headroom, TICKET-0075/BRIEF-0075-b) — Agenda stays in canon.py.
_MODEL_FILES = (CANON_FILE, CONFIG_FILE)

EXPECTED_REQUIREMENT_TYPES = ("knowledge", "relation_gte", "resource", "location_reachable")

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


def _find_class(tree: ast.AST, name: str) -> "ast.ClassDef | None":
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    return None


def _tuple_assign(tree: ast.AST, name: str) -> "ast.Tuple | None":
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if not any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
                continue
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            if not (isinstance(node.target, ast.Name) and node.target.id == name):
                continue
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


def _check_constraint_texts(tree: ast.AST) -> dict[str, str]:
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "CheckConstraint"):
            continue
        name = None
        for kw in node.keywords:
            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                name = kw.value.value
        expr = node.args[0].value if node.args and isinstance(node.args[0], ast.Constant) else None
        if name is not None and isinstance(expr, str):
            out[name] = expr
    return out


def check_evaluator_bijection() -> None:
    tree = _parse(DAY_PLAN_FILE)
    if tree is None:
        return
    req_tuple = _tuple_assign(tree, "REQUIREMENT_TYPES")
    if req_tuple is None:
        fail(f"{_rel(DAY_PLAN_FILE)}: REQUIREMENT_TYPES tuple not found")
        return
    req_types = {e.value for e in req_tuple.elts if isinstance(e, ast.Constant)}
    if not req_types:
        fail(f"{_rel(DAY_PLAN_FILE)}: REQUIREMENT_TYPES located but holds zero values")
        return

    evaluators = _named_dict(tree, "_EVALUATORS")
    if evaluators is None:
        fail(f"{_rel(DAY_PLAN_FILE)}: _EVALUATORS dict literal not found")
        return
    evaluator_keys = {k.value for k in evaluators.keys if isinstance(k, ast.Constant)}
    if not evaluator_keys:
        fail(f"{_rel(DAY_PLAN_FILE)}: _EVALUATORS located but holds zero keys")
        return

    missing = req_types - evaluator_keys
    if missing:
        fail(f"day_plan R1: REQUIREMENT_TYPES value(s) {sorted(missing)!r} have no _EVALUATORS key")
    orphan = evaluator_keys - req_types
    if orphan:
        fail(f"day_plan R1: _EVALUATORS key(s) {sorted(orphan)!r} are not in REQUIREMENT_TYPES")


def _all_check_constraints() -> dict[str, str]:
    found: dict[str, str] = {}
    for path in _MODEL_FILES:
        tree = _parse(path)
        if tree is not None:
            found.update(_check_constraint_texts(tree))
    return found


def check_type_constraint() -> None:
    constraints = _all_check_constraints()
    if not constraints:
        fail("day_plan: zero CheckConstraint declarations located across canon.py/config.py")
        return
    expr = constraints.get("ck_agenda_step_requirement_type")
    if expr is None:
        fail("day_plan: CheckConstraint 'ck_agenda_step_requirement_type' not found in canon.py/config.py")
        return
    quoted = set(re.findall(r"'([^']*)'", expr))
    if quoted != set(EXPECTED_REQUIREMENT_TYPES):
        fail(
            f"day_plan R2: ck_agenda_step_requirement_type quotes {sorted(quoted)!r}, "
            f"expected {sorted(EXPECTED_REQUIREMENT_TYPES)!r}"
        )


def check_shape_constraint() -> None:
    constraints = _all_check_constraints()
    expr = constraints.get("ck_agenda_step_requirement_shape")
    if expr is None:
        fail("day_plan: CheckConstraint 'ck_agenda_step_requirement_shape' not found in canon.py/config.py")
        return

    required_pairs = [
        ("relation_gte", "target_entity_id"),
        ("location_reachable", "target_entity_id"),
        ("knowledge", "target_key"),
        ("resource", "target_key"),
        ("relation_gte", "threshold"),
        ("resource", "threshold"),
    ]
    missing = [pair for pair in required_pairs if pair[0] not in expr or pair[1] not in expr]
    if missing:
        fail(f"day_plan R3: ck_agenda_step_requirement_shape missing condition(s) {missing!r}")


def check_budget_derivation() -> None:
    tree = _parse(DAY_PLAN_FILE)
    if tree is None:
        return
    for node in tree.body:
        target_name = None
        value = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name, value = node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name, value = node.target.id, node.value
        if target_name != "DAY_BUDGET_SLOTS":
            continue
        if isinstance(value, ast.Constant) and isinstance(value.value, int):
            fail(f"{_rel(DAY_PLAN_FILE)}: DAY_BUDGET_SLOTS is a numeric literal ({value.value!r}), not derived")
        elif not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "len"):
            fail(f"{_rel(DAY_PLAN_FILE)}: DAY_BUDGET_SLOTS is not a len(...) derivation")
        return
    fail(f"{_rel(DAY_PLAN_FILE)}: DAY_BUDGET_SLOTS assignment not found")


def check_no_phase_or_schedule_reads() -> None:
    text = _read_text(DAY_PLAN_FILE)
    if text is None:
        return
    if "current_phase" in text:
        fail(f"{_rel(DAY_PLAN_FILE)}: references current_phase — P2 forbids this")
    if re.search(r"select\(\s*NpcSchedule", text):
        fail(f"{_rel(DAY_PLAN_FILE)}: contains a select( against NpcSchedule — positional reads stay in schedule_reads.py")


def check_positional_wall() -> None:
    # Agenda lives in canon.py; AgendaStep was relocated to config.py for
    # module_budget headroom (TICKET-0075/BRIEF-0075-b) — check each in its
    # actual file rather than assuming both still share canon.py.
    class_locations = {"Agenda": CANON_FILE, "AgendaStep": CONFIG_FILE}
    found_any = False
    for cls_name, path in class_locations.items():
        tree = _parse(path)
        if tree is None:
            continue
        cls = _find_class(tree, cls_name)
        if cls is None:
            fail(f"{_rel(path)}: {cls_name} class not found")
            continue
        found_any = True
        field_names = {
            node.target.id for node in cls.body
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        }
        if not field_names:
            fail(f"{_rel(path)}: {cls_name} declares zero annotated fields")
            continue
        location_fields = {n for n in field_names if "location" in n.lower()}
        if location_fields:
            fail(
                f"day_plan R6: {cls_name} declares location-named field(s) {sorted(location_fields)!r} — "
                "the positional wall (BRIEF-0074-a-amendment-1) is broken"
            )
    if not found_any:
        fail("day_plan R6: neither Agenda nor AgendaStep located — vacuous")

    # AST-based, not text search: schedule_reads.py's own comments legitimately
    # NAME AgendaStep/Agenda in prose (documenting why they're absent) —
    # a raw-text scan would false-positive on its own doctrine note. Comments
    # never enter the AST; docstrings do (as ast.Constant string values), so
    # walking for real ast.Name/ast.alias references correctly ignores both
    # comments and any string literal that merely mentions the word.
    schedule_reads_tree = _parse(SCHEDULE_READS_FILE)
    if schedule_reads_tree is not None:
        forbidden_names = {"Agenda", "AgendaStep", "AgendaStepRequirement"}
        for node in ast.walk(schedule_reads_tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in forbidden_names:
                        fail(
                            f"{_rel(SCHEDULE_READS_FILE)}: imports {alias.name!r} — the positional "
                            "wall (BRIEF-0074-a-amendment-1) forbids any agenda import here"
                        )
            elif isinstance(node, ast.Name) and node.id in forbidden_names:
                fail(
                    f"{_rel(SCHEDULE_READS_FILE)}: references {node.id!r} — the positional wall "
                    "(BRIEF-0074-a-amendment-1) forbids any agenda import here"
                )


def check_budget_cut_purity() -> None:
    tree = _parse(DAY_PLAN_FILE)
    if tree is None:
        return
    func = _find_function(tree, "budget_cut")
    if func is None:
        fail(f"{_rel(DAY_PLAN_FILE)}: budget_cut not found")
        return
    forbidden = {"db", "select", "chat", "datetime", "randint"}
    hits: set[str] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and node.id in forbidden:
            hits.add(node.id)
        if isinstance(node, ast.Attribute) and node.attr in forbidden:
            hits.add(node.attr)
    if hits:
        fail(f"day_plan R7: budget_cut references forbidden name(s) {sorted(hits)!r} — must stay pure")


def check_emit_plan_wiring() -> None:
    tree = _parse(DAY_PLAN_FILE)
    if tree is None:
        return
    func = _find_function(tree, "emit_plan")
    if func is None:
        fail(f"{_rel(DAY_PLAN_FILE)}: emit_plan not found")
    else:
        uses_llm_parse = any(
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "llm_parse"
            for node in ast.walk(func)
        )
        if not uses_llm_parse:
            fail(f"{_rel(DAY_PLAN_FILE)}: emit_plan does not route its parse through llm_parse")

    sys.path.insert(0, str(ROOT / "src"))
    from world_engine import prompt_registry  # noqa: E402

    entry = prompt_registry.PROMPT_REGISTRY.get("day_plan")
    if entry is None:
        fail("day_plan R8: PROMPT_REGISTRY has no 'day_plan' entry")
        return
    call_sites = getattr(entry, "call_sites", ())
    if not call_sites:
        fail("day_plan R8: PROMPT_REGISTRY['day_plan'].call_sites is empty")
    elif not any("emit_plan" in site for site in call_sites):
        fail(f"day_plan R8: PROMPT_REGISTRY['day_plan'].call_sites does not name emit_plan: {call_sites!r}")


def check_bounds_constants() -> None:
    tree = _parse(DAY_PLAN_FILE)
    if tree is None:
        return
    names_found: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names_found.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names_found.add(node.target.id)
    missing = {"MAX_PLAN_STEPS", "DAY_BUDGET_SLOTS"} - names_found
    if missing:
        fail(f"day_plan R9: module-level constant(s) missing from day_plan.py: {sorted(missing)!r}")

    route_text = _read_text(DAY_ROUTE_FILE)
    if route_text is not None and "DAY_BUDGET_SLOTS" not in route_text:
        fail(f"{_rel(DAY_ROUTE_FILE)}: does not reference DAY_BUDGET_SLOTS — bounds must not be restated as literals")


def check_no_traversal_reuse() -> None:
    """R10 (BRIEF-0075-b-amendment-1): `day_plan.py` declares its OWN
    `connects_to` BFS rather than importing a sibling reader — decision D1
    (BRIEF-19) made structural for this consumer. Do NOT turn this into a
    check that day_plan.py REUSES an existing traversal — that was the
    superseded instruction the amendment corrected."""
    tree = _parse(DAY_PLAN_FILE)
    if tree is None:
        return

    forbidden = {"_location_neighbours", "_reachable_locations", "_live_neighbour_ids"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in forbidden:
                    fail(
                        f"{_rel(DAY_PLAN_FILE)}: imports {alias.name!r} — decision D1 forbids "
                        "reusing a sibling connects_to reader"
                    )
        if isinstance(node, ast.Name) and node.id in forbidden:
            fail(f"{_rel(DAY_PLAN_FILE)}: references {node.id!r} — decision D1 forbids reusing a sibling reader")

    func = _find_function(tree, "_day_reachable_ids")
    if func is None:
        fail(f"{_rel(DAY_PLAN_FILE)}: _day_reachable_ids not found — day_plan.py must declare its own BFS (D1)")
        return

    has_loop = any(isinstance(n, (ast.While, ast.For)) for n in ast.walk(func))
    if not has_loop:
        fail(f"{_rel(DAY_PLAN_FILE)}: _day_reachable_ids contains no loop — not a real traversal")

    references_connects_to = any(
        isinstance(n, ast.Constant) and n.value == "connects_to" for n in ast.walk(func)
    )
    if not references_connects_to:
        fail(f"{_rel(DAY_PLAN_FILE)}: _day_reachable_ids does not reference 'connects_to'")


def main() -> None:
    check_evaluator_bijection()
    check_type_constraint()
    check_shape_constraint()
    check_budget_derivation()
    check_no_phase_or_schedule_reads()
    check_positional_wall()
    check_budget_cut_purity()
    check_emit_plan_wiring()
    check_bounds_constants()
    check_no_traversal_reuse()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: day_plan — evaluator bijection, requirement CHECKs, budget derivation, "
        "P2/positional exclusion, the positional wall, budget_cut purity, emit_plan "
        "wiring, named bounds, and the D1 traversal-independence gate are all intact"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
