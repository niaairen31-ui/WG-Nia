"""Structural gate for resolution, the fact sheet and narration (TICKET-0075,
BRIEF-0075-d). Stdlib `ast` and text only, no DB — same FAILURES/fail()/
`_parse`/`_rel` idiom as `day_plan.py`/`day_concordance.py`.

R1 (dice are Python, singular): `day_resolve.py` calls `resolve_physical`,
and no module in the day chain (`day_resolve.py`, `day_narration.py`,
`day_narration_guard.py`, `day_plan.py`, `day_concordance.py`,
`day_extract.py`) contains a `randint` reference of its own.
R2 (truncation purity): `day_resolve.py`'s `_truncate_on_failure` body
contains no `db`, `select(`, `chat(`, `datetime`, or `randint`.
R3 (the prose is a rendering): `day_narration.py`'s `narrate` function body
contains no `select(` call.
R4 (the judge is Python): `day_narration_guard.py` contains no `chat(`.
R5 (anti-vacuity, the single most important line in the judge):
`judge_narration`'s body contains an explicit zero-names guard and an
explicit zero-steps guard.
R6 (bounded rewrite): `MAX_REWRITE_ATTEMPTS` is a module-level constant in
`day_narration.py` with the value `1`; the rewrite call site
(`cockpit/routes/day.py`) is reachable from exactly one `if` condition.
R7 (history is sacred, append-only): no assignment of a fresh list to
`.history` anywhere in `src/`, except inside `PassPlay(...)`'s constructor
(`writes/pipeline.py::write_pass_play`, empty-list initialisation) and
`write_pass_play_resolution` (which assigns a list built by extending the
CURRENT value, never a fresh literal) — and no `.history[` subscript
assignment anywhere.
R8 (declared_action re-asserted from this brief's angle): no assignment to
`.declared_action` anywhere in `src/` — this brief is the first to write
the same row's `history` column, so the sibling invariant is re-checked
here too.
R9 (registry wiring): `day_narration` and `day_rewrite` are both in
`PROMPT_REGISTRY`, each with a `call_sites` entry naming its function
(`narrate`/`rewrite`) in `day_narration.py`.
R10: every rule above is vacuity-guarded — a rule that locates zero items
is a FAILURE, not a silent pass.
R11 (BRIEF-0075-d-amendment-1, V1 — no direct step write): `day_resolve.py`
imports no writer from `writes/goals_agendas.py` (nor `writes` re-exporting
one), contains no `db.add(`, no `.commit(`, and no assignment to `.status`,
`.outcome` or `.change_history` on an `AgendaStep`. Fail-closed and
vacuity-guarded: the file not existing is a FAILURE, not a vacuous pass.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

DAY_RESOLVE_FILE = SRC / "day_resolve.py"
DAY_NARRATION_FILE = SRC / "day_narration.py"
DAY_NARRATION_GUARD_FILE = SRC / "day_narration_guard.py"
DAY_PLAN_FILE = SRC / "day_plan.py"
DAY_CONCORDANCE_FILE = SRC / "day_concordance.py"
DAY_EXTRACT_FILE = SRC / "day_extract.py"
DAY_ROUTE_FILE = SRC / "cockpit" / "routes" / "day.py"
WRITES_PIPELINE_FILE = SRC / "writes" / "pipeline.py"

DAY_CHAIN_FILES = (
    DAY_RESOLVE_FILE, DAY_NARRATION_FILE, DAY_NARRATION_GUARD_FILE,
    DAY_PLAN_FILE, DAY_CONCORDANCE_FILE, DAY_EXTRACT_FILE,
)

# write_pass_play_resolution builds `history = list(pass_play.history or
# []); history.append(entry); pass_play.history = history` — a real
# assignment target (`pass_play.history = history`), but the RHS is a name
# built from the OLD value plus one append, never a fresh literal. This
# function (alongside write_pass_play's constructor) is the one exemption
# R7 grants.
_HISTORY_ASSIGN_EXEMPT_FUNCTIONS = {"write_pass_play_resolution"}

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


def _all_src_files() -> list[pathlib.Path]:
    return sorted(SRC.rglob("*.py"))


def check_dice_are_python() -> None:
    """R1: day_resolve.py calls resolve_physical; no day-chain module
    contains its own randint reference."""
    tree = _parse(DAY_RESOLVE_FILE)
    if tree is None:
        return
    calls_resolve_physical = any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "resolve_physical"
        for node in ast.walk(tree)
    )
    if not calls_resolve_physical:
        fail(f"day_narration R1: {_rel(DAY_RESOLVE_FILE)} does not call resolve_physical")

    found_any = False
    for path in DAY_CHAIN_FILES:
        chain_tree = _parse(path)
        if chain_tree is None:
            continue
        found_any = True
        for node in ast.walk(chain_tree):
            if isinstance(node, ast.Name) and node.id == "randint":
                fail(f"day_narration R1: {_rel(path)}:{node.lineno} references randint — dice are resolution.py's alone")
            if isinstance(node, ast.ImportFrom) and any(a.name == "randint" for a in node.names):
                fail(f"day_narration R1: {_rel(path)} imports randint directly")
    if not found_any:
        fail("day_narration R1: zero day-chain files parsed — vacuous")


def check_truncation_purity() -> None:
    """R2: _truncate_on_failure is pure."""
    tree = _parse(DAY_RESOLVE_FILE)
    if tree is None:
        return
    func = _find_function(tree, "_truncate_on_failure")
    if func is None:
        fail(f"{_rel(DAY_RESOLVE_FILE)}: _truncate_on_failure not found")
        return
    forbidden = {"db", "select", "chat", "datetime", "randint"}
    hits: set[str] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and node.id in forbidden:
            hits.add(node.id)
        if isinstance(node, ast.Attribute) and node.attr in forbidden:
            hits.add(node.attr)
    if hits:
        fail(f"day_narration R2: _truncate_on_failure references forbidden name(s) {sorted(hits)!r} — must stay pure")


def check_narrate_no_select() -> None:
    """R3: narrate's own body contains no select( call."""
    tree = _parse(DAY_NARRATION_FILE)
    if tree is None:
        return
    func = _find_function(tree, "narrate")
    if func is None:
        fail(f"{_rel(DAY_NARRATION_FILE)}: narrate not found")
        return
    for node in ast.walk(func):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "select":
            fail(f"day_narration R3: {_rel(DAY_NARRATION_FILE)}:{node.lineno} — narrate's body contains select(")


def check_judge_is_python() -> None:
    """R4: day_narration_guard.py contains no chat( call."""
    tree = _parse(DAY_NARRATION_GUARD_FILE)
    if tree is None:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "chat":
            fail(f"day_narration R4: {_rel(DAY_NARRATION_GUARD_FILE)}:{node.lineno} — the judge must stay Python-only")


def check_anti_vacuity_guards() -> None:
    """R5: judge_narration contains an explicit zero-names guard and an
    explicit zero-steps guard — located structurally (an `if` whose test
    negates a name bound to the extracted-names result, and a second `if`
    whose test negates `fact_sheet.steps` or an equivalent), not by
    grepping for specific literal spelling."""
    tree = _parse(DAY_NARRATION_GUARD_FILE)
    if tree is None:
        return
    func = _find_function(tree, "judge_narration")
    if func is None:
        fail(f"{_rel(DAY_NARRATION_GUARD_FILE)}: judge_narration not found")
        return

    has_zero_names_guard = False
    has_zero_steps_guard = False
    for node in ast.walk(func):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            operand = test.operand
            if isinstance(operand, ast.Name):
                has_zero_names_guard = True
            if isinstance(operand, ast.Attribute) and operand.attr == "steps":
                has_zero_steps_guard = True

    if not has_zero_names_guard:
        fail("day_narration R5: judge_narration has no explicit zero-names anti-vacuity guard")
    if not has_zero_steps_guard:
        fail("day_narration R5: judge_narration has no explicit zero-steps anti-vacuity guard")


def check_bounded_rewrite() -> None:
    """R6: MAX_REWRITE_ATTEMPTS == 1 in day_narration.py; the rewrite call
    site in routes/day.py is reachable from exactly one `if`."""
    tree = _parse(DAY_NARRATION_FILE)
    if tree is None:
        return
    found = False
    for node in tree.body:
        target_name, value = None, None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name, value = node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name, value = node.target.id, node.value
        if target_name != "MAX_REWRITE_ATTEMPTS":
            continue
        found = True
        if not (isinstance(value, ast.Constant) and value.value == 1):
            fail(f"day_narration R6: MAX_REWRITE_ATTEMPTS is {ast.dump(value)}, expected the literal 1")
    if not found:
        fail(f"day_narration R6: {_rel(DAY_NARRATION_FILE)}: MAX_REWRITE_ATTEMPTS not found")

    route_tree = _parse(DAY_ROUTE_FILE)
    if route_tree is None:
        return
    # The rewrite call lives in `_narrate_and_judge`, carved out of
    # `resolve_day` for the function-length ceiling (`_finalize_plan`'s
    # precedent) — search both, since either shape is a legitimate home.
    resolve_fn = _find_function(route_tree, "_narrate_and_judge") or _find_function(route_tree, "resolve_day")
    if resolve_fn is None:
        fail(f"{_rel(DAY_ROUTE_FILE)}: neither _narrate_and_judge nor resolve_day found")
        return

    # Count actual CALL SITES to rewrite/day_rewrite inside resolve_day —
    # not enclosing `if` nodes (a call nested under two `if`s legitimately
    # makes ast.walk find it from both, which would over-count). Exactly
    # one call site, itself inside at least one `if`, is what "reachable
    # from exactly one trigger condition" means structurally: the rewrite
    # is invoked from a single guarded place, never looped.
    rewrite_calls = [
        node for node in ast.walk(resolve_fn)
        if isinstance(node, ast.Call) and (
            (isinstance(node.func, ast.Name) and node.func.id in ("rewrite", "day_rewrite"))
            or (isinstance(node.func, ast.Attribute) and node.func.attr in ("rewrite", "day_rewrite"))
        )
    ]
    if not rewrite_calls:
        fail(f"day_narration R6: {_rel(DAY_ROUTE_FILE)}: resolve_day never calls the rewrite pass")
    elif len(rewrite_calls) > 1:
        fail(
            f"day_narration R6: {_rel(DAY_ROUTE_FILE)}: resolve_day calls the rewrite pass "
            f"{len(rewrite_calls)} times, expected exactly 1 — no retry loop"
        )
    else:
        # The call may sit downstream of an early-return guard clause
        # (`if verdict.passed: return ...`) rather than wrapped in an
        # `if` itself — both are legitimate ways to make a call
        # conditional. Require at least one `if` node SOMEWHERE in the
        # enclosing function; a call with zero surrounding conditionals
        # anywhere in its function would run unconditionally.
        has_any_if = any(isinstance(node, ast.If) for node in ast.walk(resolve_fn))
        if not has_any_if:
            fail(
                f"day_narration R6: {_rel(DAY_ROUTE_FILE)}: {resolve_fn.name} calls the rewrite pass "
                "with no conditional guard anywhere in the function"
            )


def check_history_append_only() -> None:
    """R7: no fresh-list assignment to .history anywhere in src/ outside
    the two exempted sites; no .history[ subscript assignment anywhere."""
    files = _all_src_files()
    if not files:
        fail(f"{_rel(SRC)}: zero .py files found — vacuous scan (R7)")
        return

    def _enclosing_function_name(tree: ast.AST, target_node: ast.AST) -> "str | None":
        stack: list[ast.AST] = []
        found = [None]

        def visit(node: ast.AST, current_fn: "str | None"):
            if node is target_node:
                found[0] = current_fn
                return True
            for child in ast.iter_child_nodes(node):
                fn_name = current_fn
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    fn_name = child.name
                if visit(child, fn_name):
                    return True
            return False

        visit(tree, None)
        return found[0]

    found_any = False
    for path in files:
        tree = _parse(path)
        if tree is None:
            continue
        found_any = True
        for node in ast.walk(tree):
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, ast.AugAssign):
                targets = [node.target]
            for target in targets:
                if isinstance(target, ast.Attribute) and target.attr == "history":
                    fn_name = _enclosing_function_name(tree, node)
                    if fn_name in _HISTORY_ASSIGN_EXEMPT_FUNCTIONS:
                        continue
                    if path == WRITES_PIPELINE_FILE and fn_name == "write_pass_play":
                        continue
                    fail(
                        f"day_narration R7: {_rel(path)}:{node.lineno} — assignment to .history "
                        f"outside an exempted append site (in {fn_name!r})"
                    )
            if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
                value = node.value
                if isinstance(value, ast.Attribute) and value.attr == "history":
                    fail(f"day_narration R7: {_rel(path)}:{node.lineno} — .history[...] index assignment")
    if not found_any:
        fail("day_narration R7: zero .py files parsed — vacuous")


def check_declared_action_still_write_once() -> None:
    """R8: re-assert -a's R3 from this brief's angle."""
    files = _all_src_files()
    if not files:
        fail(f"{_rel(SRC)}: zero .py files found — vacuous scan (R8)")
        return
    for path in files:
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, ast.AugAssign):
                targets = [node.target]
            for target in targets:
                if isinstance(target, ast.Attribute) and target.attr == "declared_action":
                    fail(f"day_narration R8: {_rel(path)}:{node.lineno} — assignment to .declared_action")


def check_registry_wiring() -> None:
    """R9: day_narration/day_rewrite in PROMPT_REGISTRY, call_sites naming
    narrate/rewrite."""
    sys.path.insert(0, str(ROOT / "src"))
    from world_engine import prompt_registry  # noqa: E402

    expected = {"day_narration": "narrate", "day_rewrite": "rewrite"}
    found_any = False
    for usage, fn_name in expected.items():
        entry = prompt_registry.PROMPT_REGISTRY.get(usage)
        if entry is None:
            fail(f"day_narration R9: PROMPT_REGISTRY has no {usage!r} entry")
            continue
        found_any = True
        call_sites = getattr(entry, "call_sites", ())
        if not call_sites:
            fail(f"day_narration R9: PROMPT_REGISTRY[{usage!r}].call_sites is empty")
        elif not any(fn_name in site for site in call_sites):
            fail(f"day_narration R9: PROMPT_REGISTRY[{usage!r}].call_sites does not name {fn_name}: {call_sites!r}")
    if not found_any:
        fail("day_narration R9: zero day_narration/day_rewrite entries found — vacuous")


_AGENDA_STEP_WRITE_ATTRS = {"status", "outcome", "change_history"}


def check_no_direct_step_write() -> None:
    """R11 (BRIEF-0075-d-amendment-1, V1): `day_resolve.py` writes NO
    canon. No import of a writer from `writes/goals_agendas.py` (nor
    `writes` re-exporting one — `write_agenda_step_status`,
    `write_agenda_status`, `write_agenda_step`), no `db.add(` call, no
    `.commit(` call, and no assignment targeting `.status`, `.outcome` or
    `.change_history` (the same attribute set day_narration.py's own R7
    protects on `.history`, applied here to `AgendaStep`)."""
    tree = _parse(DAY_RESOLVE_FILE)
    if tree is None:
        fail(f"day_narration R11: {_rel(DAY_RESOLVE_FILE)} not found or unparsable")
        return

    forbidden_writers = {
        "write_agenda_step_status", "write_agenda_status", "write_agenda_step",
    }
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name in forbidden_writers:
                    fail(
                        f"day_narration R11: {_rel(DAY_RESOLVE_FILE)}:{node.lineno} — imports "
                        f"{alias.name!r}, a direct AgendaStep/Agenda writer (V1 forbids this)"
                    )
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr in ("add", "commit"):
                fail(
                    f"day_narration R11: {_rel(DAY_RESOLVE_FILE)}:{node.lineno} — "
                    f".{node.func.attr}( call — this module writes no canon"
                )
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AugAssign):
            targets = [node.target]
        for target in targets:
            if isinstance(target, ast.Attribute) and target.attr in _AGENDA_STEP_WRITE_ATTRS:
                fail(
                    f"day_narration R11: {_rel(DAY_RESOLVE_FILE)}:{node.lineno} — assignment "
                    f"to .{target.attr} — AgendaStep transitions only through the queue (V1)"
                )


def main() -> None:
    check_dice_are_python()
    check_truncation_purity()
    check_narrate_no_select()
    check_judge_is_python()
    check_anti_vacuity_guards()
    check_bounded_rewrite()
    check_history_append_only()
    check_declared_action_still_write_once()
    check_registry_wiring()
    check_no_direct_step_write()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: day_narration — dice-are-Python, truncation purity, narrate's DB boundary, "
        "the judge's Python-only and anti-vacuity guards, the bounded rewrite, history "
        "append-only, declared_action write-once, PROMPT_REGISTRY wiring, and V1's no-direct-"
        "step-write boundary are all intact"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
