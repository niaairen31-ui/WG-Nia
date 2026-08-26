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
FAILURE, not a silent pass — EXCEPT R17, which is deliberately NOT
vacuity-guarded to require a find (see its own docstring).

--- BRIEF-0075-f (reconciliation and closure), as corrected by AMENDMENT 1 ---

Rather than a ninth check module, this brief extends the one that already
owns the plan path (its own Scope IN item 5). Continuing this file's OWN
numbering (R11+) to avoid colliding with BRIEF-0075-b's R1-R10 above; each
docstring also names the brief's OWN rule number for traceability.

R11 (brief R1): `day_reconcile.py` writes no canon — no `db.add(` of an
`Agenda`/`AgendaStep`, no `_apply_mutation` call, no `Agenda(`/`AgendaStep(`
construction.
R12 (brief R2): `RECONCILE_VERDICTS` is exactly `("continue", "modify",
"replace")`, and `day_reconcile_apply.py`'s dispatch dict
(`_reconcile_and_finalize`) has the identical key set, both directions.
(retargeted by TICKET-0077/BRIEF-0077-b after BRIEF-0077-a item 5 relocated
this function; the assertion is unchanged, only where it looks.)
R13 (brief R3): the citation validator compares against real `step_order`
values; `reconcile()` raises `LlmParseError` on a validation failure, and
never silently defaults `.get("verdict", "continue")`.
R14 (brief R4, REPLACED by AMENDMENT 1 — no longer asserts the absence of
`abandoned`): `day_reconcile.py` contains no `.delete(`, and `_finalize_
replace` (day_reconcile_apply.py) constructs no `ProposedMutation` at all.
(retargeted by TICKET-0077/BRIEF-0077-b after BRIEF-0077-a item 5 relocated
this function; the assertion is unchanged, only where it looks.)
R15 (brief R5): the S3 refusal from -b (`_guard_no_active_agenda`, "already
holds an active agenda") is gone from `routes/day.py`, and `plan_day` calls
`_load_standing_agenda` — the reconciliation path is wired where the
refusal used to be.
R16 (brief R6): `day_reconcile.py` references neither `AgendaStepRequirement`
nor `.cost` — it classifies intent, nothing else.
R17 (brief R7): any `ProposedMutation(` constructed by the reconciliation
path carries a `rationale` kwarg. Deliberately NOT vacuity-guarded to
require a find: R11/R14/R19 independently establish that the reconciliation
path constructs NO mutation at all under the current applier's capability
(AA2, S2) — zero sites is the correct, designed state; this rule exists to
catch a future regression, not to demand one exists.
R18 (brief R8, re-asserted from this angle): `day_reconcile.py` contains no
`'npc_move'` constant, no `ProposedMutation(status=...)` other than the
literal `'proposed'`, no `select(` against `NpcSchedule`, and no reference
to `current_location_id` — reconciliation reads no position.
R19 (brief R10, NEW): `_finalize_continue` (day_reconcile_apply.py)
constructs no `ProposedMutation` — a no-op verdict emits nothing.
(retargeted by TICKET-0077/BRIEF-0077-b after BRIEF-0077-a item 5 relocated
this function; the assertion is unchanged, only where it looks.)
R20 (brief R11, NEW, decision Z4): `PATCH /agendas/{agenda_id}`'s
reactivation branch (`_activate_lowest_pending_step_if_none_active`,
`cockpit/crud/agendas.py`) calls `write_agenda_step_status` for the
activation rather than assigning `.status` directly.
R21 (Scope OUT, re-asserted): `_mutation_apply_agenda_step_change`'s action
vocabulary is still exactly `("complete", "fail")` — Z4 exists precisely so
this never needs widening.

--- BRIEF-0077-b (verify gate retarget) ---

R22 (TICKET-0077, BRIEF-0077-b): the six reconciliation finalizers live in
`cockpit/day_reconcile_apply.py` and nowhere else. R12/R14/R19 each resolve
a function by name in a fixed file and report "not found" when it moves —
that is a correct failure, but a LATE one: it fires only after a relocation
has already merged. This rule proves the location itself, so a future move
is caught as a location change rather than as three unrelated "not found"
messages. It proves WHERE the functions are, not that their bodies are
correct — R12/R14/R19 still own that.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

DAY_PLAN_FILE = SRC / "day_plan.py"
DAY_RECONCILE_FILE = SRC / "day_reconcile.py"
CANON_FILE = SRC / "models" / "canon.py"
CONFIG_FILE = SRC / "models" / "config.py"
SCHEDULE_READS_FILE = SRC / "schedule_reads.py"
DAY_ROUTE_FILE = SRC / "cockpit" / "routes" / "day.py"
DAY_RECONCILE_APPLY_FILE = SRC / "cockpit" / "day_reconcile_apply.py"
CRUD_AGENDAS_FILE = SRC / "cockpit" / "crud" / "agendas.py"
MUTATIONS_FILE = SRC / "cockpit" / "mutations.py"

# AgendaStep/AgendaStepRequirement live in config.py, not canon.py (module_budget
# headroom, TICKET-0075/BRIEF-0075-b) — Agenda stays in canon.py.
_MODEL_FILES = (CANON_FILE, CONFIG_FILE)

EXPECTED_REQUIREMENT_TYPES = ("knowledge", "relation_gte", "resource", "location_reachable")
EXPECTED_RECONCILE_VERDICTS = ("continue", "modify", "replace")

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


# --- BRIEF-0075-f (reconciliation and closure), as corrected by AMENDMENT 1 ---

def check_reconcile_writes_nothing() -> None:
    """R11 (brief R1)."""
    tree = _parse(DAY_RECONCILE_FILE)
    if tree is None:
        fail(f"day_plan R11: {_rel(DAY_RECONCILE_FILE)} not found or unparsable")
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "_apply_mutation":
                fail(f"day_plan R11: {_rel(DAY_RECONCILE_FILE)}:{node.lineno} — calls _apply_mutation")
            elif node.func.id in ("Agenda", "AgendaStep"):
                fail(f"day_plan R11: {_rel(DAY_RECONCILE_FILE)}:{node.lineno} — constructs {node.func.id}(")
        if (
            isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add"
            and isinstance(node.func.value, ast.Name) and node.func.value.id == "db"
        ):
            fail(f"day_plan R11: {_rel(DAY_RECONCILE_FILE)}:{node.lineno} — calls db.add(")


def check_verdict_dispatch_bijection() -> None:
    """R12 (brief R2)."""
    tree = _parse(DAY_RECONCILE_FILE)
    if tree is None:
        return
    verdict_tuple = _tuple_assign(tree, "RECONCILE_VERDICTS")
    if verdict_tuple is None:
        fail(f"day_plan R12: {_rel(DAY_RECONCILE_FILE)}: RECONCILE_VERDICTS not found")
        return
    verdicts = tuple(e.value for e in verdict_tuple.elts if isinstance(e, ast.Constant))
    if verdicts != EXPECTED_RECONCILE_VERDICTS:
        fail(f"day_plan R12: RECONCILE_VERDICTS is {verdicts!r}, expected {EXPECTED_RECONCILE_VERDICTS!r}")

    route_tree = _parse(DAY_RECONCILE_APPLY_FILE)
    if route_tree is None:
        return
    fn = _find_function(route_tree, "_reconcile_and_finalize")
    if fn is None:
        fail(f"day_plan R12: {_rel(DAY_RECONCILE_APPLY_FILE)}: _reconcile_and_finalize not found")
        return
    handlers_dict = None
    for node in ast.walk(fn):
        name, value = None, None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name, value = node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name, value = node.target.id, node.value
        if name == "handlers" and isinstance(value, ast.Dict):
            handlers_dict = value
    if handlers_dict is None:
        fail(f"day_plan R12: {_rel(DAY_RECONCILE_APPLY_FILE)}: _reconcile_and_finalize has no 'handlers' dict literal")
        return
    handler_keys = {k.value for k in handlers_dict.keys if isinstance(k, ast.Constant)}
    if not handler_keys:
        fail(f"day_plan R12: {_rel(DAY_RECONCILE_APPLY_FILE)}: handlers dict located but holds zero keys")
        return
    if handler_keys != set(EXPECTED_RECONCILE_VERDICTS):
        fail(
            f"day_plan R12: handlers dict keys {sorted(handler_keys)!r} != "
            f"RECONCILE_VERDICTS {sorted(EXPECTED_RECONCILE_VERDICTS)!r}"
        )


def check_citation_validator_and_no_default() -> None:
    """R13 (brief R3)."""
    tree = _parse(DAY_RECONCILE_FILE)
    if tree is None:
        return
    fn = _find_function(tree, "reconcile")
    if fn is None:
        fail(f"day_plan R13: {_rel(DAY_RECONCILE_FILE)}: reconcile not found")
        return

    has_citation_check = any(
        isinstance(node, ast.Compare) and any(
            isinstance(c, ast.Attribute) and c.attr == "step_order" for c in ast.walk(node)
        )
        for node in ast.walk(fn)
    )
    if not has_citation_check:
        fail(f"day_plan R13: {_rel(DAY_RECONCILE_FILE)}: reconcile has no step_order citation comparison")

    for node in ast.walk(fn):
        if (
            isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get"
            and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "verdict"
            and len(node.args) > 1 and isinstance(node.args[1], ast.Constant) and node.args[1].value == "continue"
        ):
            fail(
                f"day_plan R13: {_rel(DAY_RECONCILE_FILE)}:{node.lineno} — "
                ".get('verdict', 'continue') silently defaults to continue"
            )

    raises_parse_error = any(
        isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)
        and isinstance(node.exc.func, ast.Attribute) and node.exc.func.attr == "LlmParseError"
        for node in ast.walk(fn)
    )
    if not raises_parse_error:
        fail(f"day_plan R13: {_rel(DAY_RECONCILE_FILE)}: reconcile never raises llm_parse.LlmParseError")


def check_replace_writes_nothing() -> None:
    """R14 (brief R4, REPLACED by AMENDMENT 1)."""
    tree = _parse(DAY_RECONCILE_FILE)
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "delete":
                fail(f"day_plan R14: {_rel(DAY_RECONCILE_FILE)}:{node.lineno} — calls .delete(")

    route_tree = _parse(DAY_RECONCILE_APPLY_FILE)
    if route_tree is None:
        return
    fn = _find_function(route_tree, "_finalize_replace")
    if fn is None:
        fail(f"day_plan R14: {_rel(DAY_RECONCILE_APPLY_FILE)}: _finalize_replace not found")
        return
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "ProposedMutation":
            fail(f"day_plan R14: {_rel(DAY_RECONCILE_APPLY_FILE)}:{node.lineno} — _finalize_replace constructs ProposedMutation")


def check_s3_refusal_replaced() -> None:
    """R15 (brief R5). The old refusal's raise message was an f-string
    (`ast.JoinedStr`, interpolating `character.id`) — scanned as such so a
    docstring PROSE mention of the same phrase (describing the new
    behavior) is never a false positive."""
    tree = _parse(DAY_ROUTE_FILE)
    if tree is None:
        return
    if _find_function(tree, "_guard_no_active_agenda") is not None:
        fail(f"day_plan R15: {_rel(DAY_ROUTE_FILE)}: _guard_no_active_agenda still defined")
    for node in ast.walk(tree):
        if not isinstance(node, ast.JoinedStr):
            continue
        joined = "".join(v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str))
        if "already holds an active agenda" in joined:
            fail(f"day_plan R15: {_rel(DAY_ROUTE_FILE)}:{node.lineno} — the S3 refusal f-string is still present")

    plan_fn = _find_function(tree, "plan_day")
    if plan_fn is None:
        fail(f"day_plan R15: {_rel(DAY_ROUTE_FILE)}: plan_day not found")
        return
    calls_standing_lookup = any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_load_standing_agenda"
        for node in ast.walk(plan_fn)
    )
    if not calls_standing_lookup:
        fail(f"day_plan R15: {_rel(DAY_ROUTE_FILE)}: plan_day does not call _load_standing_agenda")


def check_reconcile_no_cost_or_requirement_reads() -> None:
    """R16 (brief R6)."""
    tree = _parse(DAY_RECONCILE_FILE)
    if tree is None:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "AgendaStepRequirement":
            fail(f"day_plan R16: {_rel(DAY_RECONCILE_FILE)}:{node.lineno} — references AgendaStepRequirement")
        if isinstance(node, ast.Attribute) and node.attr == "cost":
            fail(f"day_plan R16: {_rel(DAY_RECONCILE_FILE)}:{node.lineno} — references .cost")


def check_reconcile_mutation_rationale() -> None:
    """R17 (brief R7). Deliberately NOT vacuity-guarded to require a
    find — see the module docstring."""
    for path in (DAY_RECONCILE_FILE, DAY_ROUTE_FILE):
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "ProposedMutation"):
                continue
            rationale_kw = next((kw for kw in node.keywords if kw.arg == "rationale"), None)
            if rationale_kw is None:
                fail(f"day_plan R17: {_rel(path)}:{node.lineno} — ProposedMutation( has no rationale kwarg")
            elif isinstance(rationale_kw.value, ast.Constant) and not str(rationale_kw.value.value).strip():
                fail(f"day_plan R17: {_rel(path)}:{node.lineno} — ProposedMutation( rationale is empty")


def check_reconcile_npc_move_status_position() -> None:
    """R18 (brief R8, re-asserted)."""
    tree = _parse(DAY_RECONCILE_FILE)
    text = _read_text(DAY_RECONCILE_FILE)
    if tree is None or text is None:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == "npc_move":
            fail(f"day_plan R18: {_rel(DAY_RECONCILE_FILE)}:{node.lineno} — references 'npc_move'")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "ProposedMutation":
            for kw in node.keywords:
                if kw.arg == "status" and not (isinstance(kw.value, ast.Constant) and kw.value.value == "proposed"):
                    fail(
                        f"day_plan R18: {_rel(DAY_RECONCILE_FILE)}:{node.lineno} — "
                        "ProposedMutation(status=...) is not the literal 'proposed'"
                    )
    if re.search(r"select\(\s*NpcSchedule", text):
        fail(f"day_plan R18: {_rel(DAY_RECONCILE_FILE)}: select( against NpcSchedule")
    if "current_location_id" in text:
        fail(f"day_plan R18: {_rel(DAY_RECONCILE_FILE)}: references current_location_id")


def check_continue_constructs_nothing() -> None:
    """R19 (brief R10, NEW)."""
    tree = _parse(DAY_RECONCILE_APPLY_FILE)
    if tree is None:
        return
    fn = _find_function(tree, "_finalize_continue")
    if fn is None:
        fail(f"day_plan R19: {_rel(DAY_RECONCILE_APPLY_FILE)}: _finalize_continue not found")
        return
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "ProposedMutation":
            fail(f"day_plan R19: {_rel(DAY_RECONCILE_APPLY_FILE)}:{node.lineno} — _finalize_continue constructs ProposedMutation")


def check_z4_activation_uses_writer() -> None:
    """R20 (brief R11, NEW, decision Z4)."""
    tree = _parse(CRUD_AGENDAS_FILE)
    if tree is None:
        fail(f"day_plan R20: {_rel(CRUD_AGENDAS_FILE)} not found or unparsable")
        return
    fn = _find_function(tree, "_activate_lowest_pending_step_if_none_active")
    if fn is None:
        fail(f"day_plan R20: {_rel(CRUD_AGENDAS_FILE)}: _activate_lowest_pending_step_if_none_active not found")
        return
    calls_writer = any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "write_agenda_step_status"
        for node in ast.walk(fn)
    )
    if not calls_writer:
        fail(f"day_plan R20: {_rel(CRUD_AGENDAS_FILE)}: activation branch does not call write_agenda_step_status")
    for node in ast.walk(fn):
        if (
            isinstance(node, ast.Assign) and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Attribute) and node.targets[0].attr == "status"
        ):
            fail(
                f"day_plan R20: {_rel(CRUD_AGENDAS_FILE)}:{node.lineno} — assigns .status directly, "
                "bypassing write_agenda_step_status"
            )


def check_applier_action_vocabulary_unwidened() -> None:
    """R21 (Scope OUT, re-asserted)."""
    tree = _parse(MUTATIONS_FILE)
    if tree is None:
        fail(f"day_plan R21: {_rel(MUTATIONS_FILE)} not found or unparsable")
        return
    fn = _find_function(tree, "_mutation_apply_agenda_step_change")
    if fn is None:
        fail(f"day_plan R21: {_rel(MUTATIONS_FILE)}: _mutation_apply_agenda_step_change not found")
        return
    found = False
    for node in ast.walk(fn):
        if isinstance(node, ast.Compare) and len(node.comparators) == 1 and isinstance(node.comparators[0], ast.Tuple):
            values = tuple(e.value for e in node.comparators[0].elts if isinstance(e, ast.Constant))
            if values:
                found = True
                if values != ("complete", "fail"):
                    fail(f"day_plan R21: {_rel(MUTATIONS_FILE)}: action tuple is {values!r}, expected ('complete', 'fail')")
    if not found:
        fail(f"day_plan R21: {_rel(MUTATIONS_FILE)}: no 'action in (...)' comparison found")


def check_reconcile_finalizers_located() -> None:
    """R22 (TICKET-0077, BRIEF-0077-b): the six reconciliation finalizers
    live in `cockpit/day_reconcile_apply.py` and nowhere else. Proves
    location only — R12/R14/R19 still own the correctness of each body."""
    names = (
        "_reconcile_and_finalize",
        "_finalize_continue",
        "_finalize_modify",
        "_finalize_replace",
        "_reconciliation_dict",
        "_revised_plan_matches_remaining",
    )
    route_tree = _parse(DAY_ROUTE_FILE)
    apply_tree = _parse(DAY_RECONCILE_APPLY_FILE)
    located_any = False
    for name in names:
        in_route = route_tree is not None and _find_function(route_tree, name) is not None
        in_apply = apply_tree is not None and _find_function(apply_tree, name) is not None
        if in_route and in_apply:
            fail(f"day_plan R22: {name} is defined in both {_rel(DAY_ROUTE_FILE)} and {_rel(DAY_RECONCILE_APPLY_FILE)}")
            located_any = True
            continue
        if not in_route and not in_apply:
            fail(f"day_plan R22: {name} not found in {_rel(DAY_ROUTE_FILE)} or {_rel(DAY_RECONCILE_APPLY_FILE)}")
            continue
        located_any = True
        if in_route:
            fail(f"day_plan R22: {name} is defined in {_rel(DAY_ROUTE_FILE)}, expected {_rel(DAY_RECONCILE_APPLY_FILE)}")
    if not located_any:
        fail("day_plan R22: zero reconciliation finalizers located across both files")


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
    check_reconcile_writes_nothing()
    check_verdict_dispatch_bijection()
    check_citation_validator_and_no_default()
    check_replace_writes_nothing()
    check_s3_refusal_replaced()
    check_reconcile_no_cost_or_requirement_reads()
    check_reconcile_mutation_rationale()
    check_reconcile_npc_move_status_position()
    check_continue_constructs_nothing()
    check_z4_activation_uses_writer()
    check_applier_action_vocabulary_unwidened()
    check_reconcile_finalizers_located()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: day_plan — evaluator bijection, requirement CHECKs, budget derivation, "
        "P2/positional exclusion, the positional wall, budget_cut purity, emit_plan "
        "wiring, named bounds, the D1 traversal-independence gate, BRIEF-0075-f's "
        "reconciliation/Z4/AA2 gates (R11-R21), and R22's finalizer-location gate "
        "are all intact"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
