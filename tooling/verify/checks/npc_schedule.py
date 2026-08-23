"""Structural gate for `npc_schedule` / `world.current_phase` (TICKET-0074,
BRIEF-0074-a). Stdlib `ast` only, no DB — same FAILURES/fail()/
_report_and_exit idiom as `standing_goal.py`.

R1 (vocabulary): `SCHEDULE_PHASES` is a module-level tuple in
`models/schedule.py` holding EXACTLY the four named phases, in order.
R2 (constraints): `ck_npc_schedule_phase` and `ck_world_current_phase` both
exist, and each constraint expression quotes exactly `SCHEDULE_PHASES`'s
four values and no other literal.
R3 (precedence bijection, pure read): `PRESENT_PRECEDENCE` and
`FUTURE_PRECEDENCE` are module-level tuples in `schedule_reads.py`; every
name in both is a key of `_SOURCE_LOOKUPS` and every key appears in at
least one tuple (the bijection this also uses to structurally forbid a
resurrected `"agenda_step"` term); `where_is`'s own body contains no
`select(` call.
R4 (unknown terminal, T-D2): both precedence tuples end with `"unknown"`;
the `"unknown"` lookup's body is a bare `return None`; `where_is` contains
no `raise` anywhere in its body.
R5 (table shape, S-I1): `NpcSchedule` declares
`idx_npc_schedule_npc_phase` (unique) and `idx_npc_schedule_location_phase`,
and declares no `change_history` field.
R6 (write-site registration, single-write-site): `npc_schedule` is in
`[CANON_TABLES]`, exactly ONE `[ALLOWED_SITES]` line maps to it, and
`write_npc_schedule`'s DELETE is parameterized on `npc_id` — never an
unscoped `DELETE FROM npc_schedule`.
R7 (reader shape, no-structure-without-a-reader): `Resolution` carries the
five named fields; `where_is`, `who_is_at`, `unresolved_npcs` all exist
with an `is_present` keyword-only parameter.

Every rule carries an anti-vacuity guard: a rule that locates zero items is
a FAILURE, not a silent pass.

R9-R11 and R4b (BRIEF-0074-b amendment — Creation surfaces): the frontend
mount seam and the bare-write structural guarantee.
R9 (read-only panel): `SchedulePanel.svelte` contains no `method:` value
among POST/PUT/PATCH/DELETE.
R10 (mount reachability): `Sheet.svelte` both imports and mounts each of
`ScheduleEditor` and `SchedulePanel`, and each mount sits inside its named
`{#if}` branch guard (dispatch-site existence proves an event fires, not
that a listener hears it — applied here to mounts).
R11 (single vocabulary source): every phase `<select>` under `frontend/src/`
builds its options from an `{#each}` over the one named `SCHEDULE_PHASES`
constant (`frontend/src/creation/schedule.js`), never from inline phase
literals.
R4b (the bare write, T-A1 condition 2): `PUT /api/world/phase`'s handler
(`cockpit/routes/creator.py::set_world_phase`) calls nothing beyond a fixed
allowlist — its world-resolution helper, its validation helper, the session
`add`/`commit`, and its response builder.

R12 (BRIEF-0074-c amendment — L1 concordance reachability): proves the
concordance test is REACHED, not merely that it exists.
`_standing_is_concordant` is defined in `context.py` and its body
references `where_is`; `_npc_context_standing`'s body calls
`_standing_is_concordant`; `assemble_npc_context`'s body calls
`_npc_context_standing` with at least three positional arguments;
`_npc_context_standing` has exactly one call site across `src/`.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

SCHEDULE_FILE = SRC / "models" / "schedule.py"
CANON_FILE = SRC / "models" / "canon.py"
SCHEDULE_READS_FILE = SRC / "schedule_reads.py"
CONFIG_WRITES_FILE = SRC / "writes" / "config.py"
CONTEXT_FILE = SRC / "context.py"
POLICY_FILE = ROOT / "tooling" / "verify" / "canon_write_policy.txt"

FRONTEND_SRC = ROOT / "frontend" / "src"
CREATION_SRC = FRONTEND_SRC / "creation"
SHEET_FILE = CREATION_SRC / "Sheet.svelte"
SCHEDULE_PANEL_FILE = CREATION_SRC / "SchedulePanel.svelte"
SCHEDULE_JS_FILE = CREATION_SRC / "schedule.js"
CREATOR_ROUTES_FILE = SRC / "cockpit" / "routes" / "creator.py"

EXPECTED_PHASES = ("matin", "apres-midi", "soir", "nuit")

NPC_SHEET_GUARD = "!isNew && type === 'character' && tabKey === 'npc'"
LOCATION_SHEET_GUARD = "!isNew && type === 'location'"

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


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _find_class(tree: ast.AST, name: str) -> ast.ClassDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    return None


def _tuple_assign(tree: ast.AST, name: str) -> ast.Tuple | None:
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


def check_vocabulary() -> None:
    tree = _parse(SCHEDULE_FILE)
    if tree is None:
        return
    tup = _tuple_assign(tree, "SCHEDULE_PHASES")
    if tup is None:
        fail(f"{_rel(SCHEDULE_FILE)}: SCHEDULE_PHASES tuple not found")
        return
    values = [e.value for e in tup.elts if isinstance(e, ast.Constant)]
    if not values:
        fail(f"{_rel(SCHEDULE_FILE)}: SCHEDULE_PHASES located but holds zero string literals")
        return
    if tuple(values) != EXPECTED_PHASES:
        fail(f"{_rel(SCHEDULE_FILE)}: SCHEDULE_PHASES = {tuple(values)!r}, expected {EXPECTED_PHASES!r}")


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


def check_constraints() -> None:
    found: dict[str, str] = {}
    schedule_tree = _parse(SCHEDULE_FILE)
    if schedule_tree is not None:
        found.update(_check_constraint_texts(schedule_tree))
    canon_tree = _parse(CANON_FILE)
    if canon_tree is not None:
        found.update(_check_constraint_texts(canon_tree))

    if not found:
        fail("npc_schedule: zero CheckConstraint declarations located across schedule.py/canon.py")
        return

    for required in ("ck_npc_schedule_phase", "ck_world_current_phase"):
        expr = found.get(required)
        if expr is None:
            fail(f"npc_schedule: CheckConstraint {required!r} not found")
            continue
        quoted = set(re.findall(r"'([^']*)'", expr))
        if quoted != set(EXPECTED_PHASES):
            fail(f"npc_schedule: {required!r} quotes {sorted(quoted)!r}, expected {sorted(EXPECTED_PHASES)!r}")


def check_precedence_bijection() -> None:
    tree = _parse(SCHEDULE_READS_FILE)
    if tree is None:
        return

    present = _tuple_assign(tree, "PRESENT_PRECEDENCE")
    future = _tuple_assign(tree, "FUTURE_PRECEDENCE")
    if present is None:
        fail(f"{_rel(SCHEDULE_READS_FILE)}: PRESENT_PRECEDENCE tuple not found")
    if future is None:
        fail(f"{_rel(SCHEDULE_READS_FILE)}: FUTURE_PRECEDENCE tuple not found")
    if present is None or future is None:
        return

    present_names = [e.value for e in present.elts if isinstance(e, ast.Constant)]
    future_names = [e.value for e in future.elts if isinstance(e, ast.Constant)]
    if not present_names or not future_names:
        fail("npc_schedule: PRESENT_PRECEDENCE/FUTURE_PRECEDENCE located but hold zero names")
        return

    lookups_dict = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "_SOURCE_LOOKUPS":
            lookups_dict = node.value
        elif isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_SOURCE_LOOKUPS" for t in node.targets
        ):
            lookups_dict = node.value
    if not isinstance(lookups_dict, ast.Dict):
        fail(f"{_rel(SCHEDULE_READS_FILE)}: _SOURCE_LOOKUPS dict literal not found")
        return
    lookup_keys = {k.value for k in lookups_dict.keys if isinstance(k, ast.Constant)}
    if not lookup_keys:
        fail(f"{_rel(SCHEDULE_READS_FILE)}: _SOURCE_LOOKUPS located but holds zero keys")
        return

    tuple_names = set(present_names) | set(future_names)
    missing_keys = tuple_names - lookup_keys
    if missing_keys:
        fail(f"npc_schedule: precedence name(s) {sorted(missing_keys)!r} have no _SOURCE_LOOKUPS key")
    orphan_keys = lookup_keys - tuple_names
    if orphan_keys:
        fail(f"npc_schedule: _SOURCE_LOOKUPS key(s) {sorted(orphan_keys)!r} appear in neither precedence tuple")

    where_is = _find_function(tree, "where_is")
    if where_is is None:
        fail(f"{_rel(SCHEDULE_READS_FILE)}: where_is not found")
        return
    select_calls = [
        n for n in ast.walk(where_is)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "select"
    ]
    if select_calls:
        fail(f"{_rel(SCHEDULE_READS_FILE)}:{where_is.lineno} — where_is contains a select( call")


def check_unknown_terminal() -> None:
    tree = _parse(SCHEDULE_READS_FILE)
    if tree is None:
        return

    for tuple_name in ("PRESENT_PRECEDENCE", "FUTURE_PRECEDENCE"):
        tup = _tuple_assign(tree, tuple_name)
        if tup is None or not tup.elts:
            continue
        last = tup.elts[-1]
        if not (isinstance(last, ast.Constant) and last.value == "unknown"):
            fail(f"{_rel(SCHEDULE_READS_FILE)}: {tuple_name} does not end with 'unknown'")

    unknown_func = _find_function(tree, "_lookup_unknown")
    if unknown_func is None:
        fail(f"{_rel(SCHEDULE_READS_FILE)}: _lookup_unknown not found")
    else:
        body = [n for n in unknown_func.body if not isinstance(n, ast.Expr)]
        if len(body) != 1 or not (
            isinstance(body[0], ast.Return)
            and isinstance(body[0].value, ast.Constant)
            and body[0].value.value is None
        ):
            fail(f"{_rel(SCHEDULE_READS_FILE)}: _lookup_unknown does not unconditionally return None")

    where_is = _find_function(tree, "where_is")
    if where_is is not None:
        raises = [n for n in ast.walk(where_is) if isinstance(n, ast.Raise)]
        if raises:
            fail(f"{_rel(SCHEDULE_READS_FILE)}:{where_is.lineno} — where_is contains a raise on what must be a no-raise path")


def check_table_shape() -> None:
    tree = _parse(SCHEDULE_FILE)
    if tree is None:
        return
    cls = _find_class(tree, "NpcSchedule")
    if cls is None:
        fail(f"{_rel(SCHEDULE_FILE)}: NpcSchedule class not found")
        return

    index_names: set[str] = set()
    unique_flags: dict[str, bool] = {}
    for node in ast.walk(cls):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Index":
            if node.args and isinstance(node.args[0], ast.Constant):
                idx_name = node.args[0].value
                is_unique = any(
                    kw.arg == "unique" and isinstance(kw.value, ast.Constant) and kw.value.value is True
                    for kw in node.keywords
                )
                index_names.add(idx_name)
                unique_flags[idx_name] = is_unique
    if not index_names:
        fail(f"{_rel(SCHEDULE_FILE)}: NpcSchedule declares zero Index() entries")
        return

    if "idx_npc_schedule_npc_phase" not in index_names:
        fail(f"{_rel(SCHEDULE_FILE)}: NpcSchedule missing idx_npc_schedule_npc_phase")
    elif not unique_flags.get("idx_npc_schedule_npc_phase"):
        fail(f"{_rel(SCHEDULE_FILE)}: idx_npc_schedule_npc_phase is not unique")
    if "idx_npc_schedule_location_phase" not in index_names:
        fail(f"{_rel(SCHEDULE_FILE)}: NpcSchedule missing idx_npc_schedule_location_phase")

    field_names = {
        target.id
        for node in cls.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        for target in [node.target]
    }
    if not field_names:
        fail(f"{_rel(SCHEDULE_FILE)}: NpcSchedule declares zero annotated fields")
        return
    if "change_history" in field_names:
        fail(f"{_rel(SCHEDULE_FILE)}: NpcSchedule declares change_history — S-I1 forbids it on this table")


def check_write_site_registration() -> None:
    if not POLICY_FILE.exists():
        fail(f"{_rel(POLICY_FILE)}: file not found")
        return
    lines = POLICY_FILE.read_text(encoding="utf-8").splitlines()

    section = None
    canon_tables: set[str] = set()
    site_lines: list[tuple[str, set[str]]] = []
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if section == "CANON_TABLES":
            canon_tables.update(line.split())
        elif section == "ALLOWED_SITES":
            parts = line.split()
            if len(parts) >= 2:
                site_lines.append((parts[0], set(parts[1:])))

    if "npc_schedule" not in canon_tables:
        fail(f"{_rel(POLICY_FILE)}: npc_schedule is not listed in [CANON_TABLES]")

    matching = [site for site, tables in site_lines if "npc_schedule" in tables]
    if len(matching) == 0:
        fail(f"{_rel(POLICY_FILE)}: no [ALLOWED_SITES] line maps to npc_schedule")
    elif len(matching) > 1:
        fail(f"{_rel(POLICY_FILE)}: {len(matching)} [ALLOWED_SITES] lines map to npc_schedule, expected exactly 1")

    tree = _parse(CONFIG_WRITES_FILE)
    if tree is None:
        return
    func = _find_function(tree, "write_npc_schedule")
    if func is None:
        fail(f"{_rel(CONFIG_WRITES_FILE)}: write_npc_schedule not found")
        return

    delete_calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "execute"
        and n.args
        and isinstance(n.args[0], ast.Call)
        and isinstance(n.args[0].func, ast.Name)
        and n.args[0].func.id == "text"
        and n.args[0].args
        and isinstance(n.args[0].args[0], ast.Constant)
        and "DELETE" in str(n.args[0].args[0].value).upper()
        and "npc_schedule" in str(n.args[0].args[0].value)
    ]
    if not delete_calls:
        fail(f"{_rel(CONFIG_WRITES_FILE)}: write_npc_schedule has no db.execute(text(...DELETE...npc_schedule...)) call")
        return
    for call in delete_calls:
        sql = call.args[0].args[0].value
        if "WHERE npc_id = :npc_id" not in sql:
            fail(
                f"{_rel(CONFIG_WRITES_FILE)}:{call.lineno} — write_npc_schedule's DELETE is not "
                "parameterized on npc_id ('WHERE npc_id = :npc_id' not found)"
            )


def check_reader_shape() -> None:
    tree = _parse(SCHEDULE_READS_FILE)
    if tree is None:
        return

    cls = _find_class(tree, "Resolution")
    if cls is None:
        fail(f"{_rel(SCHEDULE_READS_FILE)}: Resolution class not found")
    else:
        field_names = {
            node.target.id for node in cls.body
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        }
        if not field_names:
            fail(f"{_rel(SCHEDULE_READS_FILE)}: Resolution declares zero annotated fields")
        else:
            missing = {"npc_id", "phase", "location_id", "source", "standing_goal_id"} - field_names
            if missing:
                fail(f"{_rel(SCHEDULE_READS_FILE)}: Resolution is missing field(s) {sorted(missing)!r}")

    found_readers = 0
    for func_name in ("where_is", "who_is_at", "unresolved_npcs"):
        func = _find_function(tree, func_name)
        if func is None:
            fail(f"{_rel(SCHEDULE_READS_FILE)}: {func_name} not found")
            continue
        found_readers += 1
        kwonly_names = {a.arg for a in func.args.kwonlyargs}
        if "is_present" not in kwonly_names:
            fail(f"{_rel(SCHEDULE_READS_FILE)}: {func_name} has no keyword-only is_present parameter")
    if found_readers == 0:
        fail("npc_schedule: zero of where_is/who_is_at/unresolved_npcs located")


def _read_text(path: pathlib.Path) -> "str | None":
    if not path.exists():
        fail(f"{_rel(path)}: file not found")
        return None
    return path.read_text(encoding="utf-8")


def check_read_only_panel() -> None:
    """R9 (BRIEF-0074-b): `SchedulePanel.svelte` contains no `method:` value
    among POST/PUT/PATCH/DELETE. Zero fetch calls found is fine (a bare
    `fetch(url)` defaults to GET) — the file not existing is the failure."""
    text = _read_text(SCHEDULE_PANEL_FILE)
    if text is None:
        return
    hit = re.search(r"method:\s*['\"](POST|PUT|PATCH|DELETE)['\"]", text)
    if hit:
        fail(f"{_rel(SCHEDULE_PANEL_FILE)}: contains a {hit.group(1)} method literal — the F1 panel must be read-only")


def _svelte_if_blocks(text: str, condition_literal: str) -> list[str]:
    """Every `{#if <condition_literal>}...{/if}` block's full source, brace-
    balanced against nested `{#if}`/`{/if}` pairs. The same literal condition
    string opens more than one block in Sheet.svelte (Tarifs, Objectifs,
    Horaire all share the NPC guard) — callers check membership across ALL
    of them, never just the first."""
    marker = "{#if " + condition_literal + "}"
    blocks: list[str] = []
    search_from = 0
    while True:
        start = text.find(marker, search_from)
        if start == -1:
            break
        pos = start + len(marker)
        depth = 1
        while depth > 0:
            next_if = text.find("{#if", pos)
            next_end = text.find("{/if}", pos)
            if next_end == -1:
                pos = len(text)
                break
            if next_if != -1 and next_if < next_end:
                depth += 1
                pos = next_if + 4
            else:
                depth -= 1
                pos = next_end + 5
        blocks.append(text[start:pos])
        search_from = pos
    return blocks


def check_mount_reachability() -> None:
    """R10 (BRIEF-0074-b): `Sheet.svelte` both imports and mounts each of
    `ScheduleEditor`/`SchedulePanel`, and each mount sits inside its named
    `{#if}` branch guard — dispatch-site existence proves an event fires,
    not that a listener hears it, applied here to mounts. An import without
    a mount, or a mount without an import, is a FAILURE."""
    text = _read_text(SHEET_FILE)
    if text is None:
        return
    for name, guard in (("ScheduleEditor", NPC_SHEET_GUARD), ("SchedulePanel", LOCATION_SHEET_GUARD)):
        imported = re.search(rf"import\s+{name}\s+from\s+['\"]\./{name}\.svelte['\"]", text) is not None
        if not imported:
            fail(f"{_rel(SHEET_FILE)}: {name} is not imported")
        blocks = _svelte_if_blocks(text, guard)
        if not blocks:
            fail(f"{_rel(SHEET_FILE)}: no {{#if {guard}}} branch found")
            continue
        if not any(f"<{name}" in block for block in blocks):
            fail(f"{_rel(SHEET_FILE)}: {name} is not mounted inside its named {{#if {guard}}} branch")


def check_single_vocabulary_source() -> None:
    """R11 (BRIEF-0074-b, retargeted from standing_goal.py's R8): every phase
    `<select>` under `frontend/src/` builds its options from an `{#each
    SCHEDULE_PHASES}` loop over the one named constant
    (`frontend/src/creation/schedule.js`), never from inline phase literals.
    Zero such `<select>` elements located is a FAILURE."""
    svelte_files = sorted(FRONTEND_SRC.rglob("*.svelte"))
    if not svelte_files:
        fail(f"{_rel(FRONTEND_SRC)}: zero .svelte files found — vacuous scan")
        return

    each_hits = 0
    for path in svelte_files:
        text = path.read_text(encoding="utf-8")
        for block in text.split("<select")[1:]:
            select_body = block.split("</select>", 1)[0]
            literal_hits = sum(
                1 for lit in EXPECTED_PHASES
                if f"'{lit}'" in select_body or f'"{lit}"' in select_body
            )
            has_named_loop = re.search(r"\{#each\s+SCHEDULE_PHASES\s+as\s+\w+", select_body) is not None
            if has_named_loop:
                each_hits += 1
                continue
            if literal_hits >= 2:
                fail(
                    f"{_rel(path)}: <select> options include {literal_hits} inline phase literal(s), "
                    "not an {#each SCHEDULE_PHASES} loop"
                )

    if each_hits == 0:
        fail("npc_schedule R11: zero <select> elements built from an {#each SCHEDULE_PHASES} loop located")

    schedule_js = _read_text(SCHEDULE_JS_FILE)
    if schedule_js is not None and "export const SCHEDULE_PHASES" not in schedule_js:
        fail(f"{_rel(SCHEDULE_JS_FILE)}: SCHEDULE_PHASES is not exported")


_R4B_ALLOWED_NAMES = {"_active_world_row", "_validate_world_phase", "_world_phase_dict"}
_R4B_ALLOWED_ATTRS = {"add", "commit"}


def check_bare_phase_write() -> None:
    """R4b (BRIEF-0074-b, T-A1 condition 2 made structural): `PUT
    /api/world/phase`'s handler body calls nothing beyond its
    world-resolution helper, its validation helper, the session
    `add`/`commit`, and its response builder. Only the function's own BODY
    statements are walked — its decorator and signature defaults are not —
    so `@router.put(...)` and `Depends(get_session)` are never mistaken for
    a body call."""
    tree = _parse(CREATOR_ROUTES_FILE)
    if tree is None:
        return

    target: ast.FunctionDef | None = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for deco in node.decorator_list:
            if (
                isinstance(deco, ast.Call)
                and isinstance(deco.func, ast.Attribute)
                and deco.func.attr == "put"
                and deco.args
                and isinstance(deco.args[0], ast.Constant)
                and deco.args[0].value == "/api/world/phase"
            ):
                target = node
    if target is None:
        fail(f"{_rel(CREATOR_ROUTES_FILE)}: PUT /api/world/phase handler not found")
        return

    calls_seen = 0
    for stmt in target.body:
        for node in ast.walk(stmt):
            if not isinstance(node, ast.Call):
                continue
            calls_seen += 1
            func = node.func
            if isinstance(func, ast.Name):
                if func.id not in _R4B_ALLOWED_NAMES:
                    fail(
                        f"{_rel(CREATOR_ROUTES_FILE)}:{node.lineno} — set_world_phase calls "
                        f"{func.id!r}, outside the allowlist {sorted(_R4B_ALLOWED_NAMES)!r}"
                    )
            elif isinstance(func, ast.Attribute):
                if func.attr not in _R4B_ALLOWED_ATTRS:
                    fail(
                        f"{_rel(CREATOR_ROUTES_FILE)}:{node.lineno} — set_world_phase calls "
                        f".{func.attr}(...), outside the allowlist {sorted(_R4B_ALLOWED_ATTRS)!r}"
                    )
            else:
                fail(f"{_rel(CREATOR_ROUTES_FILE)}:{node.lineno} — set_world_phase contains an unrecognized call shape")
    if calls_seen == 0:
        fail(f"{_rel(CREATOR_ROUTES_FILE)}: set_world_phase's body contains zero calls — vacuous")


def check_concordance_reachability() -> None:
    """R12 (BRIEF-0074-c): proves the concordance test is REACHED, not merely
    that it exists — the "dispatch-site existence proves an event fires but
    not that a listener hears it" lesson, applied to `_standing_is_concordant`.
    Any of the four targets not located is a FAILURE."""
    tree = _parse(CONTEXT_FILE)
    if tree is None:
        return

    concordant_func = _find_function(tree, "_standing_is_concordant")
    if concordant_func is None:
        fail(f"{_rel(CONTEXT_FILE)}: _standing_is_concordant not found")
    else:
        references_where_is = any(
            isinstance(node, ast.Name) and node.id == "where_is" for node in ast.walk(concordant_func)
        )
        if not references_where_is:
            fail(f"{_rel(CONTEXT_FILE)}: _standing_is_concordant does not reference where_is")

    standing_func = _find_function(tree, "_npc_context_standing")
    if standing_func is None:
        fail(f"{_rel(CONTEXT_FILE)}: _npc_context_standing not found")
    else:
        calls_concordant = any(
            isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_standing_is_concordant"
            for node in ast.walk(standing_func)
        )
        if not calls_concordant:
            fail(f"{_rel(CONTEXT_FILE)}: _npc_context_standing does not call _standing_is_concordant")

    assemble_func = _find_function(tree, "assemble_npc_context")
    if assemble_func is None:
        fail(f"{_rel(CONTEXT_FILE)}: assemble_npc_context not found")
    else:
        found_call = False
        for node in ast.walk(assemble_func):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_npc_context_standing":
                found_call = True
                if len(node.args) < 3:
                    fail(
                        f"{_rel(CONTEXT_FILE)}:{node.lineno} — assemble_npc_context calls "
                        f"_npc_context_standing with {len(node.args)} positional argument(s), expected >= 3"
                    )
        if not found_call:
            fail(f"{_rel(CONTEXT_FILE)}: assemble_npc_context never calls _npc_context_standing")

    call_sites = 0
    for path in sorted(SRC.rglob("*.py")):
        file_tree = _parse(path)
        if file_tree is None:
            continue
        for node in ast.walk(file_tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_npc_context_standing":
                call_sites += 1
    if call_sites == 0:
        fail("npc_schedule R12: zero call sites of _npc_context_standing located across src/ — vacuous")
    elif call_sites != 1:
        fail(f"npc_schedule R12: _npc_context_standing has {call_sites} call site(s) across src/, expected exactly 1")


def main() -> None:
    check_vocabulary()
    check_constraints()
    check_precedence_bijection()
    check_unknown_terminal()
    check_table_shape()
    check_write_site_registration()
    check_reader_shape()
    check_read_only_panel()
    check_mount_reachability()
    check_single_vocabulary_source()
    check_bare_phase_write()
    check_concordance_reachability()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: npc_schedule — vocabulary, constraints, precedence bijection, table shape, "
        "write-site registration, read-only panel, mount reachability, vocabulary source, "
        "the bare phase write and the concordance reachability are all intact"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
