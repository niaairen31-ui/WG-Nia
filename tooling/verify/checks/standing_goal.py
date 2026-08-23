"""Structural gate for `npc_goal.kind` (TICKET-0073, BRIEF-0073-b, G2/N1).

Standing rows (background occupation) share the `npc_goal` table with
volition rows but must never leak into a volition-shaped render or into a
model-closable goal match. Six rules, stdlib `ast` only, no DB — same
FAILURES/fail()/_report_and_exit idiom as `npc_goal_read.py`.

R1 (reader filter): each of the four in-scene readers filters every
`select(NpcGoal)` call chain on `NpcGoal.kind`.
R2 (anti-vacuity): zero readers located, or zero `select(NpcGoal)` calls
found across them, is a FAILURE, not a pass.
R3 (constraints present): `models/canon.py` declares both CHECK constraints.
R4 (vocabulary): `NPC_GOAL_KINDS` is defined and re-exported.
R5 (render separation): the standing section is its own thing, never H_GOALS.
R6 (reachability): the standing section and the initiative fragment are
both actually wired into their assemblers — R5 alone proves the constant
and function exist, not that anything reaches them.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

CANON_FILE = SRC / "models" / "canon.py"
GOALS_AGENDAS_FILE = SRC / "writes" / "goals_agendas.py"
WRITES_INIT_FILE = SRC / "writes" / "__init__.py"
CONTEXT_FILE = SRC / "context.py"
TICK_CONTEXT_FILE = SRC / "tick_context.py"
PLAY_INITIATIVE_FILE = SRC / "cockpit" / "play_initiative.py"
MUTATIONS_FILE = SRC / "cockpit" / "mutations.py"

# The four in-scene readers (mini-RECON, BRIEF-0073-b). A function not found
# at its named location is a FAILURE — it may have been renamed, and a
# renamed reader must be re-registered here deliberately.
READERS = (
    (CONTEXT_FILE, "_npc_context_goals"),
    (TICK_CONTEXT_FILE, "_tick_goals_block"),
    (PLAY_INITIATIVE_FILE, "_initiative_candidate_data"),
    (MUTATIONS_FILE, "_mutation_goal_change_close"),
)

FAILURES: list[str] = []
_TREE_CACHE: dict[pathlib.Path, ast.Module | None] = {}


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _parse(path: pathlib.Path) -> ast.Module | None:
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


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _is_select_npcgoal(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "select"
        and any(isinstance(a, ast.Name) and a.id == "NpcGoal" for a in node.args)
    )


def _chain_top(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> ast.AST:
    """Climb from a `select(NpcGoal)` call up through its own fluent chain
    (`.where(...).order_by(...).limit(...)`), stopping the instant the
    chain is consumed as an argument elsewhere (e.g. `session.exec(...)`)."""
    current = node
    while True:
        parent = parents.get(current)
        if parent is None:
            return current
        if isinstance(parent, ast.Attribute) and parent.value is current:
            current = parent
            continue
        if isinstance(parent, ast.Call) and parent.func is current:
            current = parent
            continue
        return current


def _has_kind_compare(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Compare):
            continue
        operands = [sub.left, *sub.comparators]
        for o in operands:
            if isinstance(o, ast.Attribute) and o.attr == "kind" and isinstance(o.value, ast.Name) and o.value.id == "NpcGoal":
                return True
    return False


def check_reader_filters() -> None:
    functions_located = 0
    total_select_calls = 0
    for path, func_name in READERS:
        tree = _parse(path)
        if tree is None:
            continue
        func = _find_function(tree, func_name)
        if func is None:
            fail(f"{_rel(path)}: reader function {func_name!r} not found")
            continue
        functions_located += 1
        parents = _parent_map(tree)
        select_calls = [n for n in ast.walk(func) if _is_select_npcgoal(n)]
        total_select_calls += len(select_calls)
        if not select_calls:
            fail(f"{_rel(path)}:{func.lineno} — {func_name}: no select(NpcGoal) call found")
            continue
        for call in select_calls:
            top = _chain_top(call, parents)
            if not _has_kind_compare(top):
                fail(
                    f"{_rel(path)}:{call.lineno} — {func_name}: a select(NpcGoal) "
                    "call chain has no NpcGoal.kind filter"
                )

    if functions_located == 0:
        fail("standing_goal: zero reader functions located across the four named readers")
    if total_select_calls == 0:
        fail("standing_goal: zero select(NpcGoal) calls found across the four named readers")


def check_constraints_present() -> None:
    tree = _parse(CANON_FILE)
    if tree is None:
        return
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "CheckConstraint":
            for kw in node.keywords:
                if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                    names.add(kw.value.value)
    for required in ("ck_npc_goal_kind", "ck_npc_goal_standing_horizon"):
        if required not in names:
            fail(f"{_rel(CANON_FILE)}: CheckConstraint {required!r} not found on NpcGoal")


def check_vocabulary() -> None:
    goals_tree = _parse(GOALS_AGENDAS_FILE)
    if goals_tree is not None:
        assigned = any(
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "NPC_GOAL_KINDS" for t in node.targets)
            for node in ast.walk(goals_tree)
        )
        if not assigned:
            fail(f"{_rel(GOALS_AGENDAS_FILE)}: NPC_GOAL_KINDS is not assigned")

    init_tree = _parse(WRITES_INIT_FILE)
    if init_tree is not None:
        imported = any(
            isinstance(node, ast.ImportFrom)
            and any(alias.name == "NPC_GOAL_KINDS" for alias in node.names)
            for node in ast.walk(init_tree)
        )
        if not imported:
            fail(f"{_rel(WRITES_INIT_FILE)}: NPC_GOAL_KINDS is not re-exported")


def check_render_separation() -> None:
    tree = _parse(CONTEXT_FILE)
    if tree is None:
        return
    assigns_h_standing = any(
        isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "H_STANDING" for t in node.targets)
        for node in ast.walk(tree)
    )
    if not assigns_h_standing:
        fail(f"{_rel(CONTEXT_FILE)}: H_STANDING is not assigned")

    func = _find_function(tree, "_npc_context_standing")
    if func is None:
        fail(f"{_rel(CONTEXT_FILE)}: _npc_context_standing not found")
        return
    references_h_goals = any(
        isinstance(node, ast.Name) and node.id == "H_GOALS" for node in ast.walk(func)
    )
    if references_h_goals:
        fail(f"{_rel(CONTEXT_FILE)}: _npc_context_standing references H_GOALS — must render under its own header")


def check_reachability() -> None:
    context_tree = _parse(CONTEXT_FILE)
    if context_tree is not None:
        assemble = _find_function(context_tree, "assemble_npc_context")
        if assemble is None:
            fail(f"{_rel(CONTEXT_FILE)}: assemble_npc_context not found")
        else:
            calls_standing = any(
                isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_npc_context_standing"
                for node in ast.walk(assemble)
            )
            if not calls_standing:
                fail(f"{_rel(CONTEXT_FILE)}: assemble_npc_context never calls _npc_context_standing")

    play_tree = _parse(PLAY_INITIATIVE_FILE)
    if play_tree is not None:
        signal_lines = _find_function(play_tree, "_initiative_signal_lines")
        if signal_lines is None:
            fail(f"{_rel(PLAY_INITIATIVE_FILE)}: _initiative_signal_lines not found")
        else:
            references_frag = any(
                isinstance(node, ast.Name) and node.id == "standing_frag" for node in ast.walk(signal_lines)
            )
            if not references_frag:
                fail(f"{_rel(PLAY_INITIATIVE_FILE)}: _initiative_signal_lines never references standing_frag")


def main() -> None:
    check_reader_filters()
    check_constraints_present()
    check_vocabulary()
    check_render_separation()
    check_reachability()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: standing_goal — npc_goal.kind reader filters, constraints, vocabulary and reachability intact")
    sys.exit(0)


if __name__ == "__main__":
    main()
