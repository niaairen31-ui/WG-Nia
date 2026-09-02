"""Structural gate for the declaration rewrite (TICKET-0081, BRIEF-0081-b —
decisions A2'/B2/J2). Stdlib `ast` and text only, no DB — same
FAILURES/fail()/`_rel`/`_parse`/`ROOT = parents[3]` idiom as
`day_concordance.py`.

W1 (purity): `day_rewrite.py` imports no `ollama_client` and constructs no
model from a named forbidden set (`Entity`, `Character`, `NpcSchedule`,
`ProposedMutation`).
W2 (append-only): no assignment anywhere in `src/` targets an attribute of a
`DayRewrite`/`DayMentionResolution` instance, and neither name appears as
the argument of a `db.delete(`.
W3 (retirement): `plan_context` has no remaining definition, import or
reference anywhere in `src/`.
W4 (signature): `emit_plan`'s signature no longer names `concordance_summary`.
W5 (world scope): every `select(` in `day_concordance.py` or `day_rewrite.py`
carries a `world_id` reference somewhere in its enclosing statement.
W6 (no resolve-time extraction): `routes/day.py` calls `extract_places`/
`extract_persons`/`extract_factions` exactly once each — the plan-time
sites only; the resolve path reads the trace instead.

Every rule above is vacuity-guarded — a rule that locates zero items where
items are expected is a FAILURE, not a silent pass. W2 and W3 are
absence-rules: finding zero VIOLATIONS is the pass, guarded instead by
requiring the positive fact (a construction of each model, respectively)
to actually exist in the tree before trusting the absence.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

DAY_REWRITE_FILE = SRC / "day_rewrite.py"
DAY_CONCORDANCE_FILE = SRC / "day_concordance.py"
DAY_PLAN_FILE = SRC / "day_plan.py"
DAY_ROUTE_FILE = SRC / "cockpit" / "routes" / "day.py"

_FORBIDDEN_CONSTRUCTORS = {"Entity", "Character", "NpcSchedule", "ProposedMutation"}
_TRACKED_MODELS = {"DayRewrite", "DayMentionResolution"}
_EXTRACT_FUNCS = {"extract_places", "extract_persons", "extract_factions"}

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


def _all_src_files() -> list[pathlib.Path]:
    return sorted(SRC.rglob("*.py"))


# ── W1 ───────────────────────────────────────────────────────────────────

def check_purity() -> None:
    tree = _parse(DAY_REWRITE_FILE)
    if tree is None:
        return
    functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    if not functions:
        fail(f"day_rewrite W1: {_rel(DAY_REWRITE_FILE)} defines zero functions — vacuous")
        return

    imports_ollama = any(
        (isinstance(n, ast.ImportFrom) and (n.module or "").endswith("ollama_client"))
        or (isinstance(n, ast.Import) and any(a.name.endswith("ollama_client") for a in n.names))
        for n in ast.walk(tree)
    )
    if imports_ollama:
        fail(f"day_rewrite W1: {_rel(DAY_REWRITE_FILE)} imports ollama_client — must stay model-free")

    constructs = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FORBIDDEN_CONSTRUCTORS
    }
    if constructs:
        fail(f"day_rewrite W1: {_rel(DAY_REWRITE_FILE)} constructs forbidden model(s) {sorted(constructs)!r}")


# ── W2 ───────────────────────────────────────────────────────────────────

def _tracked_names(tree: ast.Module) -> set[str]:
    """Local names bound to a `DayRewrite`/`DayMentionResolution` instance:
    a direct constructor call, a `db.get(DayRewrite, ...)` read, or a `for`
    target iterating a `select(DayRewrite)`-shaped query result."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            bound = False
            if isinstance(call.func, ast.Name) and call.func.id in _TRACKED_MODELS:
                bound = True
            elif isinstance(call.func, ast.Attribute) and call.func.attr == "get" and call.args:
                first = call.args[0]
                if isinstance(first, ast.Name) and first.id in _TRACKED_MODELS:
                    bound = True
            if bound:
                names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            if any(isinstance(sub, ast.Name) and sub.id in _TRACKED_MODELS for sub in ast.walk(node.iter)):
                names.add(node.target.id)
    return names


def check_append_only() -> None:
    found_construction = False
    for path in _all_src_files():
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _TRACKED_MODELS:
                found_construction = True

        names = _tracked_names(tree)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in targets:
                    if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id in names:
                        fail(
                            f"day_rewrite W2: {_rel(path)}:{node.lineno} — attribute assignment on a "
                            f"tracked DayRewrite/DayMentionResolution instance ({t.value.id}.{t.attr} = ...)"
                        )
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "delete":
                for arg in node.args:
                    if isinstance(arg, ast.Name) and (arg.id in _TRACKED_MODELS or arg.id in names):
                        fail(f"day_rewrite W2: {_rel(path)}:{node.lineno} — db.delete({arg.id}) on a tracked model/name")

    if not found_construction:
        fail("day_rewrite W2: zero DayRewrite/DayMentionResolution constructions found in src/ — vacuous")


# ── W3 ───────────────────────────────────────────────────────────────────

def check_plan_context_retired() -> None:
    for path in _all_src_files():
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "plan_context":
                fail(f"day_rewrite W3: {_rel(path)}:{node.lineno} — plan_context still defined")
            elif isinstance(node, ast.ImportFrom) and any(a.name == "plan_context" for a in node.names):
                fail(f"day_rewrite W3: {_rel(path)}:{node.lineno} — plan_context still imported")
            elif isinstance(node, ast.Name) and node.id == "plan_context":
                fail(f"day_rewrite W3: {_rel(path)}:{node.lineno} — plan_context still referenced")


# ── W4 ───────────────────────────────────────────────────────────────────

def check_emit_plan_signature() -> None:
    tree = _parse(DAY_PLAN_FILE)
    if tree is None:
        return
    func = _find_function(tree, "emit_plan")
    if func is None:
        fail(f"day_rewrite W4: {_rel(DAY_PLAN_FILE)}: emit_plan not found")
        return
    arg_names = {a.arg for a in func.args.args} | {a.arg for a in func.args.kwonlyargs}
    if "concordance_summary" in arg_names:
        fail("day_rewrite W4: emit_plan's signature still names concordance_summary")


# ── W5 ───────────────────────────────────────────────────────────────────

def _enclosing_statement(node: ast.AST, parent_map: dict) -> "ast.stmt | None":
    cur = node
    while cur is not None and not isinstance(cur, ast.stmt):
        cur = parent_map.get(cur)
    return cur


def check_world_scope() -> None:
    for file_path in (DAY_CONCORDANCE_FILE, DAY_REWRITE_FILE):
        tree = _parse(file_path)
        if tree is None:
            continue
        parent_map: dict = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parent_map[child] = node

        select_calls = [
            n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "select"
        ]
        if not select_calls:
            fail(f"day_rewrite W5: {_rel(file_path)} contains zero select( calls — vacuous")
            continue

        for call in select_calls:
            stmt = _enclosing_statement(call, parent_map)
            if stmt is None:
                fail(f"day_rewrite W5: {_rel(file_path)}:{call.lineno} — select( has no enclosing statement")
                continue
            has_world_id = any(
                isinstance(sub, ast.Attribute) and sub.attr == "world_id" for sub in ast.walk(stmt)
            )
            if not has_world_id:
                fail(
                    f"day_rewrite W5: {_rel(file_path)}:{call.lineno} — select( lacks a world_id "
                    "reference in its enclosing statement"
                )


# ── W6 ───────────────────────────────────────────────────────────────────

def check_no_resolve_time_extraction() -> None:
    tree = _parse(DAY_ROUTE_FILE)
    if tree is None:
        return
    calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _EXTRACT_FUNCS
    ]
    if not calls:
        fail(f"day_rewrite W6: zero extract_*() calls found in {_rel(DAY_ROUTE_FILE)} — vacuous")
        return
    found = sorted({c.func.id for c in calls})
    if found != sorted(_EXTRACT_FUNCS):
        fail(f"day_rewrite W6: expected all three extract_* functions called, got {found!r}")
    if len(calls) != 3:
        fail(
            f"day_rewrite W6: expected exactly 3 extract_*() calls (plan-time only) in "
            f"{_rel(DAY_ROUTE_FILE)}, found {len(calls)} — a resolve-time call has crept back in"
        )


def main() -> None:
    check_purity()
    check_append_only()
    check_plan_context_retired()
    check_emit_plan_signature()
    check_world_scope()
    check_no_resolve_time_extraction()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: day_rewrite — W1 purity, W2 append-only, W3 plan_context retirement, "
        "W4 emit_plan signature, W5 world scope, and W6 no resolve-time extraction are all intact"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
