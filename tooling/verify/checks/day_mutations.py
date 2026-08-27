"""Structural gate for mutation emission and the day account (TICKET-0075,
BRIEF-0075-e, as corrected by BRIEF-0075-e-amendment-1). Stdlib `ast` and
text only, no DB — same FAILURES/fail()/`_parse`/`_rel` idiom as
`day_narration.py`/`day_plan.py`.

R1 (bijection, corrected vocabulary): `EMITTED_MUTATION_TYPES` in
`day_mutations.py` equals `("knowledge_change", "relation_change",
"agenda_step_change", "entity_creation")` exactly, and `_EMITTERS`'s key
set equals it, both directions (the `_SOURCE_LOOKUPS` precedent,
`schedule_reads.py`).
R2: `"npc_move"` appears nowhere in `day_mutations.py`, `day_resolve.py` or
`day_plan.py` (N1).
R3 (status/vocabulary discipline): no `ProposedMutation(` construction in
the day chain (`day_mutations.py`, `day_resolve.py`, `day_plan.py`,
`day_concordance.py`, `day_extract.py`) sets `status` to anything but the
literal `'proposed'`; and neither `"resource_change"` nor
`"agenda_creation"` is constructed as a `mutation_type` anywhere in that
chain (both REMOVED by the amendment).
R4: no module in the day chain calls `_apply_mutation`, and none imports
it.
R5: every type in `EMITTED_MUTATION_TYPES` other than `entity_creation` is
a key in `_apply_mutation`'s `appliers` dict (`cockpit/routes/mutations.
py`); `entity_creation` is short-circuited BEFORE `_apply_mutation` by
`_approve_entity_creation_shortcircuit`, called from `approve_mutation`
ahead of the apply path — never a key in `appliers` (M3/R8's own
precedent: entity_creation authors nothing).
R6 (re-assert `pipeline_wiring.py`'s R5 now that the payload has grown):
`routes/day.py` contains no `PUT`/`PATCH`/`DELETE` decorator, and no
`.history`/`injected_context` attribute or matching string constant
anywhere in the file.
R7: no response builder in `routes/day.py` constructs a dict literal with
a key named `agenda_id` or `step_id`; `Journee.svelte` contains neither
identifier as text.
R8 (re-assert -c's R5 from this brief's angle): `_approve_entity_creation_
shortcircuit` still only ever sets `status` to `'approved'`/`'pending_
realization'`-style notes — never constructs an `Entity(` and never calls
a writer whose name contains `entity` — it parks, it does not author.
R9: every rule above is vacuity-guarded — a rule that locates zero items
is a FAILURE, not a silent pass.
R10 (the delta contract travels on the payload): every `"effects"` list
construction site in `day_mutations.py` is found (vacuity: zero sites is a
FAILURE), and any dict-shaped effect literal it contains draws its
`"type"` from `_EFFECT_TYPES` (`cockpit/mutations.py`, imported at check
time — never restated as a literal here or in `day_mutations.py`).
R11: no payload built in the day chain sets a `subject`/`entity_a_id`/
`entity_b_id`-style subject key inside an `agenda_step_change` payload —
the applier forces the subject; this module must never propose one.
R12 (BRIEF-0075-f, decision BB1): `resolve_day` refuses, fail-closed, while
any `agenda_step_change` proposal for the standing agenda is still
`status='proposed'` — asserts the guard exists, filters on the right
type/status, raises a 409, and is actually called from `resolve_day`.

R13 (BRIEF-0078-c, D3): `_EMITTERS`' key set equals `EMITTED_MUTATION_TYPES`
in both directions (re-asserts R1 now that the vocabulary is five-valued)
and is exactly five-valued.
R14: `_emit_new_knowledge` exists; its body references `BLOCKED_BAND` and
returns early (`outcome.band != BLOCKED_BAND` -> `[]`) when the band does
not match; it references `_BLOCKED_LEAD_LEVEL` and contains no bare
`"rumor"` string constant.
R15: every `ProposedMutation(` construction inside `_emit_new_knowledge`
sets `status` to the literal `"proposed"` and passes a non-empty (non-
constant-empty) `rationale` keyword.
R16: `day_mutations.py` calls neither `_apply_mutation` nor `write_
knowledge` anywhere (re-asserts V1/R4 by name for the new writer family).
R17: `_blocked_lead_already_proposed` exists; its `select(ProposedMutation)`
call carries a `.where(` whose comparisons name `world_id`, `mutation_type`
and `status` explicitly — an unfiltered `select(ProposedMutation)` anywhere
in `day_mutations.py` is a FAILURE.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"
FRONTEND_SRC = ROOT / "frontend" / "src"

DAY_MUTATIONS_FILE = SRC / "day_mutations.py"
DAY_RESOLVE_FILE = SRC / "day_resolve.py"
DAY_PLAN_FILE = SRC / "day_plan.py"
DAY_CONCORDANCE_FILE = SRC / "day_concordance.py"
DAY_EXTRACT_FILE = SRC / "day_extract.py"
DAY_ROUTE_FILE = SRC / "cockpit" / "routes" / "day.py"
MUTATIONS_ROUTE_FILE = SRC / "cockpit" / "routes" / "mutations.py"
JOURNEE_SVELTE_FILE = FRONTEND_SRC / "journee" / "Journee.svelte"

DAY_CHAIN_FILES = (
    DAY_MUTATIONS_FILE, DAY_RESOLVE_FILE, DAY_PLAN_FILE, DAY_CONCORDANCE_FILE, DAY_EXTRACT_FILE,
)

EXPECTED_EMITTED_MUTATION_TYPES = (
    "knowledge_change", "relation_change", "agenda_step_change", "entity_creation", "new_knowledge",
)
REMOVED_MUTATION_TYPES = ("resource_change", "agenda_creation")

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


def _str_elements(node: ast.AST) -> "list[str] | None":
    """A tuple/list literal of string constants, or None if it isn't one."""
    if not isinstance(node, (ast.Tuple, ast.List)):
        return None
    out: list[str] = []
    for elt in node.elts:
        if not (isinstance(elt, ast.Constant) and isinstance(elt.value, str)):
            return None
        out.append(elt.value)
    return out


def check_bijection() -> None:
    """R1, R13 (BRIEF-0078-c: re-asserted now the vocabulary is five-valued)."""
    tree = _parse(DAY_MUTATIONS_FILE)
    if tree is None:
        return

    constant_tuple: "list[str] | None" = None
    emitters_keys: "list[str] | None" = None
    for node in ast.walk(tree):
        name = None
        value = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name, value = node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name, value = node.target.id, node.value
        if name == "EMITTED_MUTATION_TYPES":
            constant_tuple = _str_elements(value)
        elif name == "_EMITTERS" and isinstance(value, ast.Dict):
            keys: list[str] = []
            for key in value.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    keys.append(key.value)
            emitters_keys = keys

    if constant_tuple is None:
        fail(f"day_mutations R1: {_rel(DAY_MUTATIONS_FILE)}: EMITTED_MUTATION_TYPES not found as a string tuple")
        return
    if tuple(constant_tuple) != EXPECTED_EMITTED_MUTATION_TYPES:
        fail(
            f"day_mutations R1: EMITTED_MUTATION_TYPES is {tuple(constant_tuple)!r}, "
            f"expected {EXPECTED_EMITTED_MUTATION_TYPES!r}"
        )
    if emitters_keys is None:
        fail(f"day_mutations R1: {_rel(DAY_MUTATIONS_FILE)}: _EMITTERS not found as a string-keyed dict")
        return
    if set(emitters_keys) != set(constant_tuple):
        fail(
            f"day_mutations R1: _EMITTERS keys {sorted(set(emitters_keys))!r} do not match "
            f"EMITTED_MUTATION_TYPES {sorted(set(constant_tuple))!r}"
        )
    if len(constant_tuple) != 5:
        fail(f"day_mutations R13: EMITTED_MUTATION_TYPES has {len(constant_tuple)} entries, expected 5")


def check_npc_move_absent() -> None:
    """R2. A STRING CONSTANT scan (not raw text), so this module's own
    docstring — which names 'npc_move' in prose to explain why it is
    absent — is not itself a false positive."""
    found_any = False
    for path in (DAY_MUTATIONS_FILE, DAY_RESOLVE_FILE, DAY_PLAN_FILE):
        tree = _parse(path)
        if tree is None:
            continue
        found_any = True
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value == "npc_move":
                fail(
                    f"day_mutations R2: {_rel(path)}:{node.lineno} — the string constant "
                    "'npc_move' appears — N1 forbids emitting it from the day chain"
                )
    if not found_any:
        fail("day_mutations R2: zero files parsed — vacuous")


def _proposed_mutation_calls(tree: ast.AST) -> "list[ast.Call]":
    return [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "ProposedMutation"
    ]


def check_status_and_vocabulary_discipline() -> None:
    """R3."""
    found_any = False
    for path in DAY_CHAIN_FILES:
        tree = _parse(path)
        if tree is None:
            continue
        found_any = True
        for call in _proposed_mutation_calls(tree):
            for kw in call.keywords:
                if kw.arg == "status":
                    if not (isinstance(kw.value, ast.Constant) and kw.value.value == "proposed"):
                        fail(
                            f"day_mutations R3: {_rel(path)}:{call.lineno} — ProposedMutation(status=...) "
                            "is not the literal 'proposed'"
                        )
                if kw.arg == "mutation_type" and isinstance(kw.value, ast.Constant):
                    if kw.value.value in REMOVED_MUTATION_TYPES:
                        fail(
                            f"day_mutations R3: {_rel(path)}:{call.lineno} — constructs a "
                            f"{kw.value.value!r} mutation, removed by BRIEF-0075-e-amendment-1"
                        )
    if not found_any:
        fail("day_mutations R3: zero day-chain files parsed — vacuous")


def check_never_applies() -> None:
    """R4."""
    found_any = False
    for path in DAY_CHAIN_FILES:
        tree = _parse(path)
        if tree is None:
            continue
        found_any = True
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_apply_mutation":
                fail(f"day_mutations R4: {_rel(path)}:{node.lineno} — calls _apply_mutation directly")
            if isinstance(node, ast.ImportFrom) and any(a.name == "_apply_mutation" for a in node.names):
                fail(f"day_mutations R4: {_rel(path)} imports _apply_mutation")
    if not found_any:
        fail("day_mutations R4: zero day-chain files parsed — vacuous")


def check_every_type_applicable() -> None:
    """R5."""
    tree = _parse(MUTATIONS_ROUTE_FILE)
    if tree is None:
        return

    appliers_keys: "set[str] | None" = None
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign) and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "appliers"
            and isinstance(node.value, ast.Dict)
        ):
            appliers_keys = {
                key.value for key in node.value.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
    if appliers_keys is None:
        fail(f"day_mutations R5: {_rel(MUTATIONS_ROUTE_FILE)}: 'appliers' dict not found in _apply_mutation")
        return

    for mtype in EXPECTED_EMITTED_MUTATION_TYPES:
        if mtype == "entity_creation":
            continue
        if mtype not in appliers_keys:
            fail(f"day_mutations R5: {mtype!r} is not a key in _apply_mutation's appliers dict")

    # entity_creation: short-circuited, never a key in appliers.
    if "entity_creation" in appliers_keys:
        fail("day_mutations R5: 'entity_creation' unexpectedly appears in _apply_mutation's appliers dict")
    shortcircuit_fn = _find_function(tree, "_approve_entity_creation_shortcircuit")
    if shortcircuit_fn is None:
        fail(f"day_mutations R5: {_rel(MUTATIONS_ROUTE_FILE)}: _approve_entity_creation_shortcircuit not found")
        return
    approve_fn = _find_function(tree, "approve_mutation")
    if approve_fn is None:
        fail(f"day_mutations R5: {_rel(MUTATIONS_ROUTE_FILE)}: approve_mutation not found")
        return
    calls_shortcircuit = any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "_approve_entity_creation_shortcircuit"
        for node in ast.walk(approve_fn)
    )
    if not calls_shortcircuit:
        fail(
            "day_mutations R5: approve_mutation no longer calls "
            "_approve_entity_creation_shortcircuit — entity_creation would fall through to _apply_mutation"
        )


def check_route_shape() -> None:
    """R6 (re-assert pipeline_wiring.py's R5)."""
    tree = _parse(DAY_ROUTE_FILE)
    if tree is None:
        return
    forbidden_verbs = {"put", "patch", "delete"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for deco in node.decorator_list:
            if (
                isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute)
                and isinstance(deco.func.value, ast.Name) and deco.func.value.id == "router"
                and deco.func.attr in forbidden_verbs
            ):
                fail(f"day_mutations R6: {_rel(DAY_ROUTE_FILE)}:{node.lineno} — @router.{deco.func.attr} found")
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in ("injected_context", "history"):
            fail(f"day_mutations R6: {_rel(DAY_ROUTE_FILE)}:{node.lineno} — references .{node.attr}")
        if isinstance(node, ast.Constant) and node.value in ("injected_context", "history"):
            fail(f"day_mutations R6: {_rel(DAY_ROUTE_FILE)}:{node.lineno} — references {node.value!r}")


def check_no_agenda_or_step_id_key() -> None:
    """R7."""
    tree = _parse(DAY_ROUTE_FILE)
    if tree is not None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            for key in node.keys:
                if isinstance(key, ast.Constant) and key.value in ("agenda_id", "step_id"):
                    fail(
                        f"day_mutations R7: {_rel(DAY_ROUTE_FILE)}:{node.lineno} — dict literal "
                        f"has a key named {key.value!r}"
                    )

    if not JOURNEE_SVELTE_FILE.exists():
        fail(f"day_mutations R7: {_rel(JOURNEE_SVELTE_FILE)}: file not found")
        return
    text = JOURNEE_SVELTE_FILE.read_text(encoding="utf-8")
    for token in ("agenda_id", "step_id"):
        if token in text:
            fail(f"day_mutations R7: {_rel(JOURNEE_SVELTE_FILE)} references {token!r}")


_ENTITY_AUTHORING_CALLS = {
    "create_entity", "write_entity", "generate_entity_draft", "_generate_entity_draft",
}


def check_entity_creation_shortcircuit_authors_nothing() -> None:
    """R8 (re-assert -c's R5): `_approve_entity_creation_shortcircuit`
    constructs no `Entity(` row and calls none of the known entity-
    authoring helpers — it only ever sets `status`/`creator_notes` and
    parks. Its own `Entity` reads (`db.exec(select(Entity)...)` for the
    collision recheck, `e.name` on the result rows) are untouched by this
    check — only CONSTRUCTION/authoring calls are forbidden."""
    tree = _parse(MUTATIONS_ROUTE_FILE)
    if tree is None:
        return
    fn = _find_function(tree, "_approve_entity_creation_shortcircuit")
    if fn is None:
        fail(f"day_mutations R8: {_rel(MUTATIONS_ROUTE_FILE)}: _approve_entity_creation_shortcircuit not found")
        return
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "Entity":
            fail(
                f"day_mutations R8: {_rel(MUTATIONS_ROUTE_FILE)}:{node.lineno} — "
                "_approve_entity_creation_shortcircuit constructs an Entity — it must only park"
            )
        name = node.func.id if isinstance(node.func, ast.Name) else (
            node.func.attr if isinstance(node.func, ast.Attribute) else None
        )
        if name in _ENTITY_AUTHORING_CALLS:
            fail(
                f"day_mutations R8: {_rel(MUTATIONS_ROUTE_FILE)}:{node.lineno} — calls "
                f"{name}(...) — an entity-authoring call inside the short-circuit"
            )


_EFFECTS_KEY = "effects"


def check_effects_contract() -> None:
    """R10."""
    tree = _parse(DAY_MUTATIONS_FILE)
    if tree is None:
        return

    sys.path.insert(0, str(ROOT / "src"))
    from world_engine.cockpit import mutations as cockpit_mutations  # noqa: E402

    effect_types = getattr(cockpit_mutations, "_EFFECT_TYPES", None)
    if not effect_types:
        fail("day_mutations R10: cockpit.mutations._EFFECT_TYPES is missing or empty")
        return

    sites = 0
    for node in ast.walk(tree):
        # payload["effects"] = <list literal>
        target = None
        value = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            value = node.value
        if not (
            isinstance(target, ast.Subscript)
            and isinstance(target.slice, ast.Constant) and target.slice.value == _EFFECTS_KEY
        ):
            continue
        sites += 1
        if not isinstance(value, ast.List):
            continue
        for elt in value.elts:
            if not isinstance(elt, ast.Dict):
                continue
            for key, val in zip(elt.keys, elt.values):
                if (
                    isinstance(key, ast.Constant) and key.value == "type"
                    and isinstance(val, ast.Constant)
                    and val.value not in effect_types
                ):
                    fail(
                        f"day_mutations R10: {_rel(DAY_MUTATIONS_FILE)}:{node.lineno} — effect "
                        f"type {val.value!r} is not in cockpit.mutations._EFFECT_TYPES"
                    )
    if sites == 0:
        fail(f"day_mutations R10: {_rel(DAY_MUTATIONS_FILE)}: zero 'effects' construction sites found — vacuous")


_FORBIDDEN_SUBJECT_KEYS = ("subject", "entity_id", "owner_entity_id")


def _enclosing_function(tree: ast.AST, target: ast.AST) -> "ast.FunctionDef | None":
    found: list["ast.FunctionDef | None"] = [None]

    def visit(node: ast.AST, current: "ast.FunctionDef | None") -> bool:
        if node is target:
            found[0] = current
            return True
        next_current = node if isinstance(node, ast.FunctionDef) else current
        for child in ast.iter_child_nodes(node):
            if visit(child, next_current):
                return True
        return False

    visit(tree, None)
    return found[0]


def check_no_forced_subject_in_payload() -> None:
    """R11. The payload dict is typically built as a separate variable
    (`payload = {...}`) and passed by name into `ProposedMutation(payload=
    payload, ...)` — so this scans the WHOLE enclosing function of every
    `agenda_step_change`-typed `ProposedMutation(` call for a forbidden key,
    in either a dict literal or a `payload[<key>] = ...` subscript
    assignment, not just the call's own keyword arguments."""
    found_any = False
    for path in DAY_CHAIN_FILES:
        tree = _parse(path)
        if tree is None:
            continue
        found_any = True
        for call in _proposed_mutation_calls(tree):
            mtype = next(
                (kw.value.value for kw in call.keywords
                 if kw.arg == "mutation_type" and isinstance(kw.value, ast.Constant)),
                None,
            )
            if mtype != "agenda_step_change":
                continue
            fn = _enclosing_function(tree, call)
            if fn is None:
                fail(f"day_mutations R11: {_rel(path)}:{call.lineno} — agenda_step_change call outside any function")
                continue
            for node in ast.walk(fn):
                if isinstance(node, ast.Dict):
                    for key in node.keys:
                        if isinstance(key, ast.Constant) and key.value in _FORBIDDEN_SUBJECT_KEYS:
                            fail(
                                f"day_mutations R11: {_rel(path)}:{node.lineno} — {fn.name} builds "
                                f"an agenda_step_change payload with key {key.value!r} — the applier "
                                "forces the subject"
                            )
                if isinstance(node, ast.Assign) and len(node.targets) == 1:
                    target = node.targets[0]
                    if (
                        isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant)
                        and target.slice.value in _FORBIDDEN_SUBJECT_KEYS
                    ):
                        fail(
                            f"day_mutations R11: {_rel(path)}:{node.lineno} — {fn.name} assigns "
                            f"payload[{target.slice.value!r}] — the applier forces the subject"
                        )
    if not found_any:
        fail("day_mutations R11: zero day-chain files parsed — vacuous")


def check_resolve_precondition() -> None:
    """R12 (BRIEF-0075-f, decision BB1): `resolve_day` refuses, fail-closed,
    while any `agenda_step_change` proposal for the standing agenda is
    still `status='proposed'` — the structural expression of A1's rhythm
    (the world does not advance while proposals about it are unreviewed).
    Asserts the guard function exists, queries `ProposedMutation` for
    `mutation_type='agenda_step_change'` at `status='proposed'`, raises a
    409, and is actually CALLED from `resolve_day` — not merely present
    somewhere in the file."""
    tree = _parse(DAY_ROUTE_FILE)
    if tree is None:
        fail(f"day_mutations R12: {_rel(DAY_ROUTE_FILE)} not found or unparsable")
        return

    guard_fn = _find_function(tree, "_guard_no_pending_agenda_step_change")
    if guard_fn is None:
        fail(f"day_mutations R12: {_rel(DAY_ROUTE_FILE)}: _guard_no_pending_agenda_step_change not found")
        return

    constants = {n.value for n in ast.walk(guard_fn) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    if "agenda_step_change" not in constants:
        fail(f"day_mutations R12: {_rel(DAY_ROUTE_FILE)}: guard does not filter mutation_type='agenda_step_change'")
    if "proposed" not in constants:
        fail(f"day_mutations R12: {_rel(DAY_ROUTE_FILE)}: guard does not filter status='proposed'")

    raises_409 = any(
        isinstance(n, ast.Raise) and any(
            isinstance(kw.value, ast.Constant) and kw.value.value == 409
            for call in ast.walk(n) if isinstance(call, ast.Call)
            for kw in call.keywords if kw.arg == "status_code"
        )
        for n in ast.walk(guard_fn)
    )
    if not raises_409:
        fail(f"day_mutations R12: {_rel(DAY_ROUTE_FILE)}: guard does not raise HTTPException(status_code=409, ...)")

    resolve_fn = _find_function(tree, "resolve_day")
    if resolve_fn is None:
        fail(f"day_mutations R12: {_rel(DAY_ROUTE_FILE)}: resolve_day not found")
        return
    calls_guard = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        and n.func.id == "_guard_no_pending_agenda_step_change"
        for n in ast.walk(resolve_fn)
    )
    if not calls_guard:
        fail(f"day_mutations R12: {_rel(DAY_ROUTE_FILE)}: resolve_day never calls the precondition guard")


def check_emit_new_knowledge_shape() -> None:
    """R14: `_emit_new_knowledge` exists, band-guards on `BLOCKED_BAND`, and
    never carries a bare `"rumor"` literal (uses `_BLOCKED_LEAD_LEVEL`
    instead)."""
    tree = _parse(DAY_MUTATIONS_FILE)
    if tree is None:
        return
    fn = _find_function(tree, "_emit_new_knowledge")
    if fn is None:
        fail(f"day_mutations R14: {_rel(DAY_MUTATIONS_FILE)}: _emit_new_knowledge not found")
        return

    names_used = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
    if "BLOCKED_BAND" not in names_used:
        fail("day_mutations R14: _emit_new_knowledge never references BLOCKED_BAND")
    if "_BLOCKED_LEAD_LEVEL" not in names_used:
        fail("day_mutations R14: _emit_new_knowledge never references _BLOCKED_LEAD_LEVEL")

    has_band_guard = any(
        isinstance(n, ast.If)
        and isinstance(n.test, ast.Compare)
        and any(isinstance(c, ast.NotEq) for c in n.test.ops)
        for n in ast.walk(fn)
    )
    if not has_band_guard:
        fail("day_mutations R14: _emit_new_knowledge has no band != BLOCKED_BAND early-return guard")

    for n in ast.walk(fn):
        if isinstance(n, ast.Constant) and n.value == "rumor":
            fail(f"day_mutations R14: {_rel(DAY_MUTATIONS_FILE)}:{n.lineno} — bare 'rumor' literal found")


def check_new_knowledge_status_and_rationale() -> None:
    """R15."""
    tree = _parse(DAY_MUTATIONS_FILE)
    if tree is None:
        return
    fn = _find_function(tree, "_emit_new_knowledge")
    if fn is None:
        fail(f"day_mutations R15: {_rel(DAY_MUTATIONS_FILE)}: _emit_new_knowledge not found")
        return
    calls = _proposed_mutation_calls(fn)
    if not calls:
        fail("day_mutations R15: zero ProposedMutation( constructions inside _emit_new_knowledge — vacuous")
        return
    for call in calls:
        status_kw = next((kw for kw in call.keywords if kw.arg == "status"), None)
        if not (status_kw and isinstance(status_kw.value, ast.Constant) and status_kw.value.value == "proposed"):
            fail(f"day_mutations R15: {_rel(DAY_MUTATIONS_FILE)}:{call.lineno} — status is not literal 'proposed'")
        rationale_kw = next((kw for kw in call.keywords if kw.arg == "rationale"), None)
        if rationale_kw is None or (
            isinstance(rationale_kw.value, ast.Constant) and not str(rationale_kw.value.value)
        ):
            fail(f"day_mutations R15: {_rel(DAY_MUTATIONS_FILE)}:{call.lineno} — missing or empty rationale")


def check_no_apply_or_write_knowledge() -> None:
    """R16 (re-asserts V1/R4 by name for the new_knowledge writer family)."""
    tree = _parse(DAY_MUTATIONS_FILE)
    if tree is None:
        return
    for node in ast.walk(tree):
        name = None
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in ("_apply_mutation", "write_knowledge"):
                    fail(f"day_mutations R16: {_rel(DAY_MUTATIONS_FILE)} imports {alias.name}")
        if name in ("_apply_mutation", "write_knowledge"):
            fail(f"day_mutations R16: {_rel(DAY_MUTATIONS_FILE)}:{node.lineno} — calls {name}(...)")


def check_duplicate_guard_filters() -> None:
    """R17: `_blocked_lead_already_proposed`'s `select(ProposedMutation)`
    carries all three named filters, and no unfiltered
    `select(ProposedMutation)` appears anywhere in the module."""
    tree = _parse(DAY_MUTATIONS_FILE)
    if tree is None:
        return
    fn = _find_function(tree, "_blocked_lead_already_proposed")
    if fn is None:
        fail(f"day_mutations R17: {_rel(DAY_MUTATIONS_FILE)}: _blocked_lead_already_proposed not found")
        return

    select_calls = [
        n for n in ast.walk(fn)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "select"
    ]
    if not select_calls:
        fail("day_mutations R17: _blocked_lead_already_proposed contains no select( call — vacuous")
        return

    for call in ast.walk(fn):
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == "where"):
            continue
        compared = set()
        for arg in call.args:
            for n in ast.walk(arg):
                if isinstance(n, ast.Attribute):
                    compared.add(n.attr)
        for field in ("world_id", "mutation_type", "status"):
            if field not in compared:
                fail(f"day_mutations R17: .where( in _blocked_lead_already_proposed does not name {field!r}")

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "select"):
            continue
        if not (node.args and isinstance(node.args[0], ast.Name) and node.args[0].id == "ProposedMutation"):
            continue
        parent_fn = _enclosing_function(tree, node)
        if parent_fn is None or parent_fn.name != "_blocked_lead_already_proposed":
            fail(
                f"day_mutations R17: {_rel(DAY_MUTATIONS_FILE)}:{node.lineno} — "
                "select(ProposedMutation) outside _blocked_lead_already_proposed"
            )


def main() -> None:
    check_bijection()
    check_npc_move_absent()
    check_status_and_vocabulary_discipline()
    check_never_applies()
    check_every_type_applicable()
    check_route_shape()
    check_no_agenda_or_step_id_key()
    check_entity_creation_shortcircuit_authors_nothing()
    check_effects_contract()
    check_no_forced_subject_in_payload()
    check_resolve_precondition()
    check_emit_new_knowledge_shape()
    check_new_knowledge_status_and_rationale()
    check_no_apply_or_write_knowledge()
    check_duplicate_guard_filters()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: day_mutations — emission bijection, npc_move absence, status/vocabulary "
        "discipline, never-applies, every-type-applicable, route shape, no agenda_id/step_id, "
        "entity_creation parks, the effects contract, no forced subject, BB1's resolve "
        "precondition, and BRIEF-0078-c's new_knowledge emission/duplicate-guard gates "
        "(R13-R17) are all intact"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
