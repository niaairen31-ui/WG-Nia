"""Structural gate for the parked-plan socle (TICKET-0077, BRIEF-0077-a).
AST-based, no DB — same FAILURES/fail()/main idiom as `standing_goal.py`.

R1 (vocabulary): the `ck_agenda_status` CheckConstraint SQL in
`models/canon.py` contains exactly the five values
`active|paused|completed|failed|abandoned`.
R2 (no cascade): `_AGENDA_GOAL_CASCADE_MAP`'s key set is exactly
`{completed, failed, abandoned}` — `paused` absent.
R3 (chokepoint, both sites): `write_agenda` and `write_agenda_status` each
contain a comparison against the string literal `"character"` AND an
`Agenda.status == "active"` existence-query comparison. Zero functions
collected is a FAILURE, not a pass.
R4 (reader exists): `PassPlay` declares `agenda_id`, and at least one
module outside `src/world_engine/models/` references `pass_play.agenda_id`
or `PassPlay.agenda_id`. Zero readers is a FAILURE.
R5 (direct-write posture): `day_plans.py` contains no `ProposedMutation`
reference and no string literal `"proposed"` — checked, not trusted.
R6 (vacuity): any rule above that collected zero items is a FAILURE in its
own right.
R7 (repair at the transition, TICKET-0080, BRIEF-0080-a): `write_agenda_status`
in `writes/goals_agendas.py` contains at least one call to
`_activate_lowest_pending_step_if_none_active`. Zero is a FAILURE.
R8 (single definition, TICKET-0080, BRIEF-0080-a): exactly one FunctionDef
named `_activate_lowest_pending_step_if_none_active` exists anywhere under
`src/world_engine/`, and it lives in `writes/goals_agendas.py`. Zero, or two
or more, is a FAILURE.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

CANON_FILE = SRC / "models" / "canon.py"
PIPELINE_FILE = SRC / "models" / "pipeline.py"
GOALS_AGENDAS_FILE = SRC / "writes" / "goals_agendas.py"
DAY_PLANS_FILE = SRC / "day_plans.py"

EXPECTED_STATUS_VALUES = {"active", "paused", "completed", "failed", "abandoned"}
EXPECTED_CASCADE_KEYS = {"completed", "failed", "abandoned"}
GUARD_FUNCTIONS = ("write_agenda", "write_agenda_status")
ACTIVATION_HELPER = "_activate_lowest_pending_step_if_none_active"

FAILURES: list[str] = []
_ITEM_COUNTS: dict[str, int] = {}
_TREE_CACHE: dict[pathlib.Path, "ast.Module | None"] = {}


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _record(rule: str, count: int) -> None:
    _ITEM_COUNTS[rule] = _ITEM_COUNTS.get(rule, 0) + count


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


def _find_function(tree: ast.AST, name: str) -> "ast.FunctionDef | None":
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def check_status_vocabulary() -> None:
    """R1."""
    tree = _parse(CANON_FILE)
    if tree is None:
        return
    found: set[str] | None = None
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "CheckConstraint"):
            continue
        name_kw = next((kw for kw in node.keywords if kw.arg == "name"), None)
        if name_kw is None or not (isinstance(name_kw.value, ast.Constant) and name_kw.value.value == "ck_agenda_status"):
            continue
        sql_arg = node.args[0] if node.args else None
        if not (isinstance(sql_arg, ast.Constant) and isinstance(sql_arg.value, str)):
            fail(f"{_rel(CANON_FILE)}:{node.lineno} — ck_agenda_status CheckConstraint's SQL is not a string literal")
            return
        # Extract the quoted values inside "status IN (...)".
        values = {v.strip("'\"") for v in sql_arg.value.split("(", 1)[-1].rstrip(")").split(",")}
        found = values
    if found is None:
        fail(f"{_rel(CANON_FILE)}: ck_agenda_status CheckConstraint not found on Agenda")
        return
    _record("R1", len(found))
    if found != EXPECTED_STATUS_VALUES:
        fail(
            f"{_rel(CANON_FILE)}: ck_agenda_status values {sorted(found)} != expected "
            f"{sorted(EXPECTED_STATUS_VALUES)}"
        )


def check_no_cascade_on_paused() -> None:
    """R2."""
    tree = _parse(GOALS_AGENDAS_FILE)
    if tree is None:
        return
    keys: set[str] | None = None
    for node in tree.body:
        target_name = None
        value = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name, value = node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name, value = node.target.id, node.value
        if target_name == "_AGENDA_GOAL_CASCADE_MAP" and isinstance(value, ast.Dict):
            keys = {
                k.value for k in value.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)
            }
    if keys is None:
        fail(f"{_rel(GOALS_AGENDAS_FILE)}: _AGENDA_GOAL_CASCADE_MAP dict literal not found")
        return
    _record("R2", len(keys))
    if keys != EXPECTED_CASCADE_KEYS:
        fail(
            f"{_rel(GOALS_AGENDAS_FILE)}: _AGENDA_GOAL_CASCADE_MAP keys {sorted(keys)} != expected "
            f"{sorted(EXPECTED_CASCADE_KEYS)} — 'paused' must stay absent"
        )


def _compare_operands(node: ast.Compare) -> list[ast.AST]:
    return [node.left, *node.comparators]


def _has_character_literal(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Compare):
            for operand in _compare_operands(sub):
                if isinstance(operand, ast.Constant) and operand.value == "character":
                    return True
    return False


def _has_agenda_status_active_compare(node: ast.AST) -> bool:
    """An `Agenda.status == "active"` (or reversed) comparison — the
    existence-query shape both guard sites share."""
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Compare):
            continue
        operands = _compare_operands(sub)
        has_status_attr = any(
            isinstance(o, ast.Attribute) and o.attr == "status"
            and isinstance(o.value, ast.Name) and o.value.id == "Agenda"
            for o in operands
        )
        has_active_literal = any(isinstance(o, ast.Constant) and o.value == "active" for o in operands)
        if has_status_attr and has_active_literal:
            return True
    return False


def check_guard_replayed_at_both_sites() -> None:
    """R3."""
    tree = _parse(GOALS_AGENDAS_FILE)
    if tree is None:
        return
    functions_located = 0
    for name in GUARD_FUNCTIONS:
        func = _find_function(tree, name)
        if func is None:
            fail(f"{_rel(GOALS_AGENDAS_FILE)}: guard function {name!r} not found")
            continue
        functions_located += 1
        if not _has_character_literal(func):
            fail(f"{_rel(GOALS_AGENDAS_FILE)}:{func.lineno} — {name}: no comparison against the literal 'character'")
        if not _has_agenda_status_active_compare(func):
            fail(
                f"{_rel(GOALS_AGENDAS_FILE)}:{func.lineno} — {name}: no Agenda.status == 'active' "
                "existence-query comparison found"
            )
    _record("R3", functions_located)
    if functions_located == 0:
        fail(f"{_rel(GOALS_AGENDAS_FILE)}: zero guard functions located across {GUARD_FUNCTIONS}")


def check_pass_play_agenda_id_has_reader() -> None:
    """R4."""
    tree = _parse(PIPELINE_FILE)
    if tree is None:
        return
    declared = False
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "agenda_id":
            declared = True
            break
    if not declared:
        fail(f"{_rel(PIPELINE_FILE)}: PassPlay does not declare agenda_id")
        return

    readers = 0
    for path in sorted(SRC.rglob("*.py")):
        rel = _rel(path)
        if rel.startswith("src/world_engine/models/"):
            continue
        tree2 = _parse(path)
        if tree2 is None:
            continue
        for node in ast.walk(tree2):
            if isinstance(node, ast.Attribute) and node.attr == "agenda_id":
                base = node.value
                if isinstance(base, ast.Name) and base.id in ("pass_play", "PassPlay"):
                    readers += 1
    _record("R4", readers)
    if readers == 0:
        fail("parked_plan_guard R4: zero readers of pass_play.agenda_id found outside models/")


def check_direct_write_posture() -> None:
    """R5."""
    tree = _parse(DAY_PLANS_FILE)
    if tree is None:
        return
    found_any = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "ProposedMutation":
            fail(f"{_rel(DAY_PLANS_FILE)}:{node.lineno} — references ProposedMutation, breaking the direct-write posture")
        if isinstance(node, ast.Attribute) and node.attr == "ProposedMutation":
            fail(f"{_rel(DAY_PLANS_FILE)}:{node.lineno} — references ProposedMutation, breaking the direct-write posture")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found_any += 1
            if node.value == "proposed":
                fail(f"{_rel(DAY_PLANS_FILE)}:{node.lineno} — string literal 'proposed' found, breaking the direct-write posture")
    _record("R5", found_any)


def check_repair_bound_to_transition() -> None:
    """R7."""
    tree = _parse(GOALS_AGENDAS_FILE)
    if tree is None:
        return
    func = _find_function(tree, "write_agenda_status")
    if func is None:
        fail(f"{_rel(GOALS_AGENDAS_FILE)}: write_agenda_status not found")
        return
    n_calls_found = sum(
        1
        for node in ast.walk(func)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == ACTIVATION_HELPER
    )
    _record("R7", n_calls_found)
    if n_calls_found == 0:
        fail(
            f"{_rel(GOALS_AGENDAS_FILE)}:{func.lineno} — write_agenda_status calls "
            f"{ACTIVATION_HELPER!r} zero times"
        )


def check_single_activation_helper_definition() -> None:
    """R8."""
    found: list[str] = []
    n_files_scanned = 0
    for path in sorted(SRC.rglob("*.py")):
        n_files_scanned += 1
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == ACTIVATION_HELPER:
                found.append(f"{_rel(path)}:{node.lineno}")
    _record("R8", n_files_scanned)
    if len(found) == 0:
        fail(f"parked_plan_guard R8: no definition of {ACTIVATION_HELPER!r} found under {_rel(SRC)}")
    elif len(found) > 1:
        fail(f"parked_plan_guard R8: {len(found)} definitions of {ACTIVATION_HELPER!r} found: {', '.join(found)}")
    elif not found[0].startswith(_rel(GOALS_AGENDAS_FILE)):
        fail(f"parked_plan_guard R8: sole definition of {ACTIVATION_HELPER!r} is not in goals_agendas.py: {found[0]}")


def check_vacuity() -> None:
    """R6."""
    for rule, count in _ITEM_COUNTS.items():
        if count == 0:
            fail(f"parked_plan_guard R6: rule {rule} collected zero items — vacuous")


def main() -> None:
    check_status_vocabulary()
    check_no_cascade_on_paused()
    check_guard_replayed_at_both_sites()
    check_pass_play_agenda_id_has_reader()
    check_direct_write_posture()
    check_repair_bound_to_transition()
    check_single_activation_helper_definition()
    check_vacuity()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: parked_plan_guard — agenda.status vocabulary, no-cascade-on-paused, the one-active "
        "guard at both canon-write sites, pass_play.agenda_id's reader, day_plans.py's "
        "direct-write posture, the R7 repair-at-the-transition call, and the R8 single definition "
        "of the activation helper all hold"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
