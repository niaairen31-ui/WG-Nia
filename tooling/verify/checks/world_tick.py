"""Structural gate for the world-tick briefing surface (TICKET-0014, BRIEF-0014-a).

The tick briefing is a conscious, logged exception to the secrets-excluded
doctrine (T1): it includes the NPC's own `is_secret` knowledge and secret
faction memberships with TRUE roles. That exception is confined to a named
set of call sites by static scan — never by convention (same mechanical
philosophy as `single_canon_write.py` and `npc_goal_read.py`).

Rule 1 (call-site allowlist): the identifier `assemble_tick_context` may
appear only in the modules named below. Rationale: the MJ boundary check
(rule 2) scans specific files for the identifier — an indirect call to the
tick builder from elsewhere would evade it (RECON-0014 F6).
Rule 2 (MJ/gathering boundary): `src/world_engine/context.py` and
`src/world_engine/gathering.py` contain NO reference to the identifier
`assemble_tick_context` anywhere.

Rule 3 (forced attribution, BRIEF-0014-b): the model payload is never the
source of `npc_id`/`entity_a_id` — no `.get("npc_id")`/`.get("entity_a_id")`
call anywhere in `tick.py`, and every dict-literal key `"npc_id"`/
`"entity_a_id"` maps to a bare `Name` value (the forced parameter), never a
`Call`/`Subscript` reading the raw item.
Rule 4 (guard branch, BRIEF-0014-b): `_find_applied_duplicate` in
`cockpit/app.py` references `mut.tick_id` — the tick scope exists (Y2,
closes RECON-0014 F2).
Rule 5 (Z3 floor + decoupling, BRIEF-0014-b): `tick.py` builds
`secret_subjects` as a set comprehension over `Knowledge` rows filtered on
`is_secret`, and compares against it with `in`; within
`_normalize_tick_item`, `is_secret` never appears on the LEFT side of an
assignment or dict-literal key whose value references `secret_subjects` or
`secret_derived` — the floor forces provenance only, never confidentiality.

Rule 6 (analyzer boundary, TICKET-0015/BRIEF-0015-a): `analyzer.py`'s
`_MUTATION_TYPE_MAP` dict literal maps no key to `"npc_move"` — movement is a
tick-only concept, never proposable from conversation analysis or
overhearing.
Rule 7 (interval-scaled radius, BRIEF-0015-a): `tick.py` defines
`INTERVAL_HOP_RADIUS` with EXACTLY the three verbatim interval-label keys,
and `_reachable_locations` references that identifier.
Rule 8 (single canon-write for movement, BRIEF-0015-a): `_apply_mutation` in
`cockpit/app.py` never assigns `current_location_id` directly — the write
must route through `write_character_location` — and its function body
references both `write_character_location` and `close_open_memberships`.

No DB, stdlib `ast` only.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
TICK_FILE = SRC / "world_engine" / "tick.py"
APP_FILE = SRC / "world_engine" / "cockpit" / "app.py"
ANALYZER_FILE = SRC / "world_engine" / "analyzer.py"

ALLOWED_MODULES = {
    "src/world_engine/tick.py",
    "src/world_engine/cockpit/app.py",
    "scripts/preview_tick_context.py",
}

BOUNDARY_FILES = {
    SRC / "world_engine" / "context.py",
    SRC / "world_engine" / "gathering.py",
}

_FORCED_FIELDS = ("npc_id", "entity_a_id", "from_location_id")

_INTERVAL_LABELS = {"quelques heures", "quelques jours", "quelques semaines"}

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _parse(path: pathlib.Path):
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        fail(f"{path}: SyntaxError: {exc}")
        return None


def _references_tick_context(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and sub.id == "assemble_tick_context":
            return True
        if isinstance(sub, ast.Attribute) and sub.attr == "assemble_tick_context":
            return True
        if isinstance(sub, ast.alias) and sub.name == "assemble_tick_context":
            return True
    return False


def check_call_site_allowlist() -> None:
    for path in sorted(SRC.rglob("*.py")) + sorted((ROOT / "scripts").rglob("*.py")) + sorted((ROOT / "tooling").rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if rel in ALLOWED_MODULES:
            continue
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "assemble_tick_context":
                fail(f"{rel}:{node.lineno} — assemble_tick_context referenced outside the allowlist")
            elif isinstance(node, ast.alias) and node.name == "assemble_tick_context":
                fail(f"{rel}:{node.lineno} — assemble_tick_context imported outside the allowlist")


def check_boundary_files() -> None:
    for path in BOUNDARY_FILES:
        if not path.exists():
            fail(f"{path} not found")
            continue
        tree = _parse(path)
        if tree is None:
            continue
        if _references_tick_context(tree):
            fail(f"{path.relative_to(ROOT)} — assemble_tick_context referenced; must stay tick-free")


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def check_forced_attribution() -> None:
    if not TICK_FILE.exists():
        fail(f"{TICK_FILE} not found")
        return
    tree = _parse(TICK_FILE)
    if tree is None:
        return
    rel = TICK_FILE.relative_to(ROOT).as_posix()

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value in _FORCED_FIELDS
        ):
            fail(
                f"{rel}:{node.lineno} — .get({node.args[0].value!r}) reads a forced-attribution "
                "field from a payload; must be forced from the parameter"
            )

        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value in _FORCED_FIELDS and not isinstance(value, ast.Name):
                    fail(
                        f"{rel}:{getattr(value, 'lineno', node.lineno)} — dict key {key.value!r} "
                        f"value is not a bare Name (forced parameter); found {type(value).__name__}"
                    )


def check_guard_branch() -> None:
    if not APP_FILE.exists():
        fail(f"{APP_FILE} not found")
        return
    tree = _parse(APP_FILE)
    if tree is None:
        return
    rel = APP_FILE.relative_to(ROOT).as_posix()

    func = _find_function(tree, "_find_applied_duplicate")
    if func is None:
        fail(f"{rel}: _find_applied_duplicate not found")
        return
    has_tick_id = any(
        isinstance(n, ast.Attribute) and n.attr == "tick_id" for n in ast.walk(func)
    )
    if not has_tick_id:
        fail(f"{rel}: _find_applied_duplicate has no tick_id-scoped branch")


def check_z3_floor() -> None:
    if not TICK_FILE.exists():
        fail(f"{TICK_FILE} not found")
        return
    tree = _parse(TICK_FILE)
    if tree is None:
        return
    rel = TICK_FILE.relative_to(ROOT).as_posix()

    # secret_subjects = {... for k in ... if ... is_secret ...} — a SetComp
    # bound to that name, filtered (somewhere in its subtree) on is_secret.
    built = False
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "secret_subjects" for t in node.targets)
            and isinstance(node.value, ast.SetComp)
        ):
            has_is_secret = any(
                (isinstance(sub, ast.Attribute) and sub.attr == "is_secret")
                or (isinstance(sub, ast.Constant) and sub.value == "is_secret")
                for sub in ast.walk(node.value)
            )
            if has_is_secret:
                built = True
    if not built:
        fail(f"{rel}: no `secret_subjects` set comprehension filtered on is_secret found")

    # A comparison (`in`/`not in`) against secret_subjects somewhere.
    compared = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            operands = [node.left, *node.comparators]
            if any(isinstance(o, ast.Name) and o.id == "secret_subjects" for o in operands):
                if any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops):
                    compared = True
    if not compared:
        fail(f"{rel}: no `in`/`not in` comparison against `secret_subjects` found")

    # Decoupling: within _normalize_tick_item, is_secret never assigned
    # (Name/Subscript target, or dict-literal key) from a value referencing
    # secret_subjects or secret_derived — the floor cannot set confidentiality.
    func = _find_function(tree, "_normalize_tick_item")
    if func is None:
        fail(f"{rel}: _normalize_tick_item not found")
        return

    def _references_forbidden(value_node: ast.AST) -> bool:
        return any(
            isinstance(n, ast.Name) and n.id in ("secret_subjects", "secret_derived")
            for n in ast.walk(value_node)
        )

    def _target_is_is_secret(target: ast.AST) -> bool:
        if isinstance(target, ast.Name) and target.id == "is_secret":
            return True
        if isinstance(target, ast.Subscript):
            sl = target.slice
            if isinstance(sl, ast.Constant) and sl.value == "is_secret":
                return True
        return False

    for node in ast.walk(func):
        if isinstance(node, ast.Assign):
            if any(_target_is_is_secret(t) for t in node.targets) and _references_forbidden(node.value):
                fail(f"{rel}:{node.lineno} — is_secret assigned from secret_subjects/secret_derived (floor must not set confidentiality)")
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value == "is_secret" and _references_forbidden(value):
                    fail(f"{rel}:{getattr(value, 'lineno', node.lineno)} — is_secret dict value references secret_subjects/secret_derived (floor must not set confidentiality)")


def _dict_assign_target(node: ast.AST):
    """Return (target_name, dict_node) for a module-level `NAME = {...}` or
    `NAME: T = {...}` assignment, else (None, None)."""
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id, node.value
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id, node.value
    return None, None


def check_analyzer_no_npc_move() -> None:
    if not ANALYZER_FILE.exists():
        fail(f"{ANALYZER_FILE} not found")
        return
    tree = _parse(ANALYZER_FILE)
    if tree is None:
        return
    rel = ANALYZER_FILE.relative_to(ROOT).as_posix()

    for node in ast.walk(tree):
        name, value = _dict_assign_target(node)
        if name != "_MUTATION_TYPE_MAP" or not isinstance(value, ast.Dict):
            continue
        for v in value.values:
            if isinstance(v, ast.Constant) and v.value == "npc_move":
                fail(
                    f"{rel}:{node.lineno} — _MUTATION_TYPE_MAP maps a key to "
                    "'npc_move'; movement is tick-only and must never enter the shared map"
                )


def check_interval_hop_radius() -> None:
    if not TICK_FILE.exists():
        fail(f"{TICK_FILE} not found")
        return
    tree = _parse(TICK_FILE)
    if tree is None:
        return
    rel = TICK_FILE.relative_to(ROOT).as_posix()

    found = False
    for node in ast.walk(tree):
        name, value = _dict_assign_target(node)
        if name != "INTERVAL_HOP_RADIUS" or not isinstance(value, ast.Dict):
            continue
        found = True
        keys = {k.value for k in value.keys if isinstance(k, ast.Constant)}
        if keys != _INTERVAL_LABELS:
            fail(
                f"{rel}:{node.lineno} — INTERVAL_HOP_RADIUS keys {sorted(keys)} "
                f"!= expected {sorted(_INTERVAL_LABELS)}"
            )
    if not found:
        fail(f"{rel}: INTERVAL_HOP_RADIUS constant map not found")

    func = _find_function(tree, "_reachable_locations")
    if func is None:
        fail(f"{rel}: _reachable_locations not found")
        return
    if not any(isinstance(n, ast.Name) and n.id == "INTERVAL_HOP_RADIUS" for n in ast.walk(func)):
        fail(f"{rel}: _reachable_locations does not reference INTERVAL_HOP_RADIUS")


def check_apply_mutation_location_write() -> None:
    if not APP_FILE.exists():
        fail(f"{APP_FILE} not found")
        return
    tree = _parse(APP_FILE)
    if tree is None:
        return
    rel = APP_FILE.relative_to(ROOT).as_posix()

    func = _find_function(tree, "_apply_mutation")
    if func is None:
        fail(f"{rel}: _apply_mutation not found")
        return

    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Attribute) and t.attr == "current_location_id" for t in node.targets
        ):
            fail(
                f"{rel}:{node.lineno} — direct current_location_id assignment in "
                "_apply_mutation; must route through write_character_location"
            )

    calls = {
        node.func.id
        for node in ast.walk(func)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    if "write_character_location" not in calls:
        fail(f"{rel}: _apply_mutation does not call write_character_location")
    if "close_open_memberships" not in calls:
        fail(f"{rel}: _apply_mutation does not call close_open_memberships")


def main() -> None:
    check_call_site_allowlist()
    check_boundary_files()
    check_forced_attribution()
    check_guard_branch()
    check_z3_floor()
    check_analyzer_no_npc_move()
    check_interval_hop_radius()
    check_apply_mutation_location_write()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: world-tick structural gate intact (rules 1-8)")
    sys.exit(0)


if __name__ == "__main__":
    main()
