"""Structural gate for the feasibility veto (TICKET-0075, BRIEF-0075-g,
decision Y1). Stdlib `ast` and text only, no DB — same FAILURES/fail()/
`_parse`/`_rel` idiom as `day_mutations.py`/`day_plan.py`.

R1: `clamp_verdict` (`day_feasibility.py`) is pure — no `db`, `select(`,
`chat(`, `datetime` or `randint` identifier anywhere in its body.
R2: `clamp_verdict` bounds `veto_retained` with an explicit `min(...)` call
— the clamp is real code, never a prompt instruction.
R3: `day_feasibility.py` writes nothing: no `db.add(`, no `.commit(`, no
`ProposedMutation(`.
R4: `routes/day.py`'s `_finalize_plan` calls the veto strictly AFTER
`budget_cut` — call ORDER, not merely presence of both.
R5: `day_feasibility.py` never references `REQUIREMENT_TYPES`,
`_EVALUATORS` or `evaluate_requirements` — the veto never touches a
requirement verdict.
R6: `clamp_verdict` has an "unavailable" branch that returns `VetoVerdict`
with `veto_retained` bound to the SAME name as its `python_retained`
parameter and `outcome="unavailable"` — Python's cut, left untouched.
R7: `day_feasibility` is a `PROMPT_REGISTRY` key with `call_sites` naming
`day_feasibility.py`.
R8: every rule above is vacuity-guarded — a rule that locates zero items is
a FAILURE, not a silent pass.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

DAY_FEASIBILITY_FILE = SRC / "day_feasibility.py"
DAY_ROUTE_FILE = SRC / "cockpit" / "routes" / "day.py"
PROMPT_REGISTRY_FILE = SRC / "prompt_registry.py"

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


def _find_function(tree: ast.AST, name: str) -> "ast.FunctionDef | None":
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


_FORBIDDEN_IDENTIFIERS = {"db", "select", "chat", "datetime", "randint"}


def check_clamp_is_pure() -> None:
    """R1."""
    tree = _parse(DAY_FEASIBILITY_FILE)
    if tree is None:
        return
    fn = _find_function(tree, "clamp_verdict")
    if fn is None:
        fail(f"day_feasibility R1: {_rel(DAY_FEASIBILITY_FILE)}: clamp_verdict not found")
        return
    found_any = False
    for node in ast.walk(fn):
        name = None
        if isinstance(node, ast.Name):
            name = node.id
        elif isinstance(node, ast.Attribute):
            name = node.attr
        if name is None:
            continue
        found_any = True
        if name in _FORBIDDEN_IDENTIFIERS:
            fail(
                f"day_feasibility R1: {_rel(DAY_FEASIBILITY_FILE)}:{node.lineno} — clamp_verdict "
                f"references {name!r}, which makes it impure"
            )
    if not found_any:
        fail("day_feasibility R1: clamp_verdict has zero identifiers to scan — vacuous")


def check_clamp_upper_bound() -> None:
    """R2."""
    tree = _parse(DAY_FEASIBILITY_FILE)
    if tree is None:
        return
    fn = _find_function(tree, "clamp_verdict")
    if fn is None:
        fail(f"day_feasibility R2: {_rel(DAY_FEASIBILITY_FILE)}: clamp_verdict not found")
        return
    min_calls = [
        node for node in ast.walk(fn)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "min"
    ]
    if not min_calls:
        fail(
            f"day_feasibility R2: {_rel(DAY_FEASIBILITY_FILE)}: clamp_verdict contains no explicit "
            "min(...) call — the upper bound must be real code, not a prompt instruction"
        )
        return
    # At least one min(...) call must be bounded by a parameter named
    # python_retained — the input count this function was handed, not an
    # unrelated literal.
    params = {a.arg for a in fn.args.args} | {a.arg for a in fn.args.kwonlyargs}
    if "python_retained" not in params:
        fail(f"day_feasibility R2: {_rel(DAY_FEASIBILITY_FILE)}: clamp_verdict has no python_retained parameter")
        return
    bounded = any(
        any(isinstance(arg, ast.Name) and arg.id == "python_retained" for arg in call.args)
        for call in min_calls
    )
    if not bounded:
        fail(
            f"day_feasibility R2: {_rel(DAY_FEASIBILITY_FILE)}: no min(...) call in clamp_verdict "
            "is bounded by python_retained"
        )


def check_writes_nothing() -> None:
    """R3."""
    tree = _parse(DAY_FEASIBILITY_FILE)
    if tree is None:
        return
    found_any = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            found_any = True
            if isinstance(node.func, ast.Name) and node.func.id == "ProposedMutation":
                fail(f"day_feasibility R3: {_rel(DAY_FEASIBILITY_FILE)}:{node.lineno} — constructs ProposedMutation")
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "add" and isinstance(node.func.value, ast.Name) and node.func.value.id == "db":
                    fail(f"day_feasibility R3: {_rel(DAY_FEASIBILITY_FILE)}:{node.lineno} — calls db.add(")
                if node.func.attr == "commit":
                    fail(f"day_feasibility R3: {_rel(DAY_FEASIBILITY_FILE)}:{node.lineno} — calls .commit(")
    if not found_any:
        fail(f"day_feasibility R3: {_rel(DAY_FEASIBILITY_FILE)}: zero calls found — vacuous")


def check_veto_after_budget_cut() -> None:
    """R4. Call ORDER inside `_finalize_plan`, not merely presence."""
    tree = _parse(DAY_ROUTE_FILE)
    if tree is None:
        return
    fn = _find_function(tree, "_finalize_plan")
    if fn is None:
        fail(f"day_feasibility R4: {_rel(DAY_ROUTE_FILE)}: _finalize_plan not found")
        return
    budget_cut_line = None
    veto_line = None
    for node in ast.walk(fn):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id == "budget_cut" and budget_cut_line is None:
            budget_cut_line = node.lineno
        if node.func.id == "feasibility_veto" and veto_line is None:
            veto_line = node.lineno
    if budget_cut_line is None:
        fail(f"day_feasibility R4: {_rel(DAY_ROUTE_FILE)}: _finalize_plan does not call budget_cut(")
        return
    if veto_line is None:
        fail(f"day_feasibility R4: {_rel(DAY_ROUTE_FILE)}: _finalize_plan does not call feasibility_veto(")
        return
    if not (veto_line > budget_cut_line):
        fail(
            f"day_feasibility R4: {_rel(DAY_ROUTE_FILE)}: feasibility_veto( at line {veto_line} does not "
            f"come after budget_cut( at line {budget_cut_line}"
        )


_FORBIDDEN_REQUIREMENT_NAMES = {"REQUIREMENT_TYPES", "_EVALUATORS", "evaluate_requirements"}


def check_never_touches_requirements() -> None:
    """R5."""
    tree = _parse(DAY_FEASIBILITY_FILE)
    if tree is None:
        return
    found_any = False
    for node in ast.walk(tree):
        name = None
        if isinstance(node, ast.Name):
            name = node.id
        elif isinstance(node, ast.Attribute):
            name = node.attr
        elif isinstance(node, ast.alias):
            name = node.name
        if name is None:
            continue
        found_any = True
        if name in _FORBIDDEN_REQUIREMENT_NAMES:
            fail(f"day_feasibility R5: {_rel(DAY_FEASIBILITY_FILE)}:{node.lineno} — references {name!r}")
    if not found_any:
        fail(f"day_feasibility R5: {_rel(DAY_FEASIBILITY_FILE)}: zero identifiers to scan — vacuous")


def check_unavailable_leaves_input_untouched() -> None:
    """R6."""
    tree = _parse(DAY_FEASIBILITY_FILE)
    if tree is None:
        return
    fn = _find_function(tree, "clamp_verdict")
    if fn is None:
        fail(f"day_feasibility R6: {_rel(DAY_FEASIBILITY_FILE)}: clamp_verdict not found")
        return

    veto_verdict_calls = [
        node for node in ast.walk(fn)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "VetoVerdict"
    ]
    if not veto_verdict_calls:
        fail(f"day_feasibility R6: {_rel(DAY_FEASIBILITY_FILE)}: clamp_verdict constructs no VetoVerdict(")
        return

    unavailable_branch_ok = False
    for call in veto_verdict_calls:
        kwargs = {kw.arg: kw.value for kw in call.keywords if kw.arg is not None}
        outcome = kwargs.get("outcome")
        if not (isinstance(outcome, ast.Constant) and outcome.value == "unavailable"):
            continue
        veto_retained = kwargs.get("veto_retained")
        python_retained = kwargs.get("python_retained")
        same_name = (
            isinstance(veto_retained, ast.Name) and isinstance(python_retained, ast.Name)
            and veto_retained.id == python_retained.id
        )
        if same_name:
            unavailable_branch_ok = True
    if not unavailable_branch_ok:
        fail(
            f"day_feasibility R6: {_rel(DAY_FEASIBILITY_FILE)}: no VetoVerdict(outcome='unavailable', ...) "
            "construction binds veto_retained to the same name as python_retained — Python's cut "
            "is not provably left untouched"
        )


def check_prompt_registry_entry() -> None:
    """R7."""
    tree = _parse(PROMPT_REGISTRY_FILE)
    if tree is None:
        return
    found = False
    for node in ast.walk(tree):
        target_name = None
        value = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name, value = node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name, value = node.target.id, node.value
        if target_name != "PROMPT_REGISTRY" or not isinstance(value, ast.Dict):
            continue
        for key, value in zip(value.keys, value.values):
            if not (isinstance(key, ast.Constant) and key.value == "day_feasibility"):
                continue
            found = True
            if not isinstance(value, ast.Call):
                fail(f"day_feasibility R7: {_rel(PROMPT_REGISTRY_FILE)}:{node.lineno} — 'day_feasibility' entry is not a PromptSpec(...) call")
                continue
            call_sites_kw = next((kw for kw in value.keywords if kw.arg == "call_sites"), None)
            if call_sites_kw is None or not isinstance(call_sites_kw.value, ast.Tuple):
                fail(f"day_feasibility R7: {_rel(PROMPT_REGISTRY_FILE)}: 'day_feasibility' entry has no call_sites tuple")
                continue
            names = [
                elt.value for elt in call_sites_kw.value.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            ]
            if not any("day_feasibility.py" in n for n in names):
                fail(
                    f"day_feasibility R7: {_rel(PROMPT_REGISTRY_FILE)}: 'day_feasibility' entry's "
                    f"call_sites {names!r} do not name day_feasibility.py"
                )
    if not found:
        fail(f"day_feasibility R7: {_rel(PROMPT_REGISTRY_FILE)}: PROMPT_REGISTRY has no 'day_feasibility' key")


def main() -> None:
    check_clamp_is_pure()
    check_clamp_upper_bound()
    check_writes_nothing()
    check_veto_after_budget_cut()
    check_never_touches_requirements()
    check_unavailable_leaves_input_untouched()
    check_prompt_registry_entry()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: day_feasibility — the clamp is pure and bounded, day_feasibility.py writes "
        "nothing, the veto runs after budget_cut, requirement verdicts are untouched, an "
        "unavailable verdict leaves Python's cut unchanged, and the PROMPT_REGISTRY entry is wired"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
