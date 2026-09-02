"""Structural gate for the "two sanctioned canon-write paths" doctrine.

Walks every `.py` file under `src/`, statically finds every ORM write site
(`.add()`/`.delete()` on a Session-typed receiver, plus raw-SQL
`.execute()`/`.exec()` calls), attributes each site to the table it writes,
and fails if a CANON table (per canon_write_policy.txt's [CANON_TABLES]) is
written from a `path::function` not listed in [ALLOWED_SITES]. Sites on
non-canon (ephemeral/pipeline) tables are ignored. A write site that cannot
be attributed to any table at all is always a failure — RECON-0003 D1
confirmed zero dynamic-dispatch write sites exist in `src/` today, so an
unattributable site is new and must be made legible before merging.

Section 1 — the law (delegated from CLAUDE.md, TICKET-0071 BRIEF-0071-a):
two sanctioned canon-write paths for canon ROWS: `_apply_mutation` (AI
proposals, post-approval) and the creator CRUD, never elsewhere for an AI
proposal (`POST /api/entities/generate` accept reuses creator CRUD). A
THIRD, creator-only authority covers canon STRUCTURE:
`writes/schema.py::create_entity_type`, closed by this check plus
`runtime_ddl_guard.py`. The trait registry (`src/world_engine/traits.py`)
is code-source-of-truth for entity-type trait contracts — traits are
added via Claude Code, never hot-edited at runtime; every trait declares
exactly one reader form (`reader_callable` | `reader_guard` |
`reader_deferred`), enforced at construction, with `mutable_by_ai` the
sole `reader_deferred` exception. `socle_traits()` and `checkable_traits()`
partition `TRAITS` totally and disjointly: socle traits (`describable`)
are implicit on every entity_type and are never written as an
`entity_trait` row — enforced by `trait_registry_projection.py`. Each
trait also carries typed `ext_columns`: `ext_columns_for()` /
`form_fields_for()` are the single derivation of both the
`create_entity_type` DDL columns and the generated-form field-specs from
a trait selection, validated against `writes/schema.py::valid_col_types()`,
the pointer-fresh accessor for the closed DDL type enum; `describable`/
`knowable`/`mutable_by_ai` contribute zero ext columns. `POST
/api/entity-types` is the creator-direct route composing
`create_entity_type` with the `entity_trait` inserts in that same
transaction — rejecting non-checkable `trait_keys` and any slug colliding
with a static `ENTITY_TYPE_REGISTRY` key; `GET /api/entity-types` is the
single source of runtime types for the frontend, carrying `runtime_types`
and `checkable_traits` alongside the static `types`. Instance CRUD
generalizes the same `POST`/`GET`/`PUT /api/entities` routes: a governed
runtime type's `ext_*` row goes through
`cockpit/crud/entity_runtime.py`'s parameterized SQLAlchemy Core
insert/update/select against a reflected `Table` (never string
interpolation, never a second write authority) — `dynamic_ext_crud.py`
verifies the round-trip and the fail-closed 422 on an ungoverned slug;
`json_ui_boundary.py`'s fourth volet keeps that dynamic form surface
relational-only by importing `traits` directly.

Section 2 — hard deletes are a closed, named list (delegated from
CLAUDE.md, TICKET-0071 BRIEF-0071-a); any new hard-delete path must be
named here, never added silently. The list: `delete_world_cascade`
(broadest — every row scoped to a world, world row included);
`skill_definition` delete (one definition + its dependent `skill` rows);
creator-correction deletes `delete_relation`, `delete_knowledge` (each
discards the row's `change_history` with the row), `delete_discoverable_
detail`, `detach_fact_participant` (TICKET-0082, BRIEF-0082-b — a
`fact_participant` row carries no `change_history` of its own, arity
metadata only), and `write_faction_role(mode="delete")` (blocked while an
active membership holds the role) — creator-CRUD-only, never reachable
from any AI or play path. Full-replace config deletes (whole-set replace, not
single-row correction): `write_npc_prices`, `write_location_subculture`,
`write_world_laws`, `write_location_obstacles`, and `write_location_doors`
each `DELETE FROM` their table(s) scoped to one parent (NPC / location /
world / location / location) then re-insert the submitted set, in one
transaction — creator-CRUD and world-bootstrap only (`set_npc_prices`,
`set_location_subculture`, `create_world`, `set_location_geometry`,
`set_location_doors`), never reachable from any AI or play path. These
tables carry no `change_history` by design (metadata-config category);
the full-replace IS their write shape. No table may take a foreign key on
`door.id` — enforced by `door_terminal.py`. `cockpit/spatial_doors.py`
orchestrates door resolution and implements no math: distances,
thresholds and spawn offsets belong to `placement.py`, the sole
placement/distance authority — enforced by `door_terminal.py`.
`_perform_travel` has three callers, all in `routes/play.py`:
conversation-bound (in-fiction), creator god-mode, and door-gated
(`/api/spatial/travel`). The neighbour restriction is a property of the
in-fiction callers; the door-gated caller carries it through `door_id`.
`/api/spatial/travel` lives in `routes/play.py`, not `routes/spatial.py`,
because it writes. `location_type_catalog` reaches the creator surface
through exactly two routes, both `cockpit/crud/locations.py`: `GET
/api/location-types` (active-world scoped list) backs the Creation-mode
type picker's datalist (never a hardcoded vocab); `POST
/api/location-types` (`upsert_location_type`) is the
classification-prompt persist step — a location save gates on it whenever
the chosen type is uncataloged or `classification IS NULL`
(Interieur/Exterieur, once); it also carries `default_width`/
`default_height`, a per-type size template applied ONCE at a location's
creation and never retroactive to an existing location. `PUT
/api/entities/{id}/geometry` distinguishes a bounds key OMITTED from the
request body (preserved) from one sent as explicit `null` (cleared), via
`body.model_fields_set` — the one route in the codebase where
full-replace does not govern every field; the `obstacle` set beneath it
stays full-replace. `spatial_author._catalog_row` is the single catalog
read path — both `location_classification` and the size-template reader
resolve a `location_type` through it — and a location's birth bounds come
from that template ONLY at
`cockpit/crud/entities.py::_create_entity_core`, never from the update
path. `LOCATION_TYPE_ORDER` (index.html) stays the browse-tree bucket
order only, never the vocabulary. Every creator path that creates a
`connects_to` edge flows through `connect_locations` (`spatial_author.py`)
— write the edge then `materialize_doors` both endpoints: region commit
takes the bulk equivalent (`commit_region` collects touched location ids
from `written_links` and calls `materialize_doors` once before its single
commit); the manual adjacency route (`crud/relations.py::create_relation`,
`type == "connects_to"`) calls `connect_locations` directly; the room
batch atomic commit (`cockpit/routes/room_batch.py::commit_room_batch`,
report-only generation enforced by `room_batch_report_only.py`) calls it
once per edge (tree + confirmed supplementary), re-deriving each room's
`parent_room` against the accepted set server-side (never a client
cascade) and degrading a NULL-bounds/classification anchor's door(s) to
the origin rather than blocking. `write_relation` itself stays a pure
relation writer — never embeds materialization. Door kind
(interior-interior / boundary / exterior-exterior) is DERIVED, never
stored: `spatial_author.location_classification` is the ONLY
interior/exterior reader, resolving a location's `location_type` against
`location_type_catalog` case-insensitively. `commit_region`'s street-access
note (a BUILDING SHELL — interior with an exterior parent, or an interior
root — with no live exterior neighbour) is purely advisory: appended to
the response's `notes` list, never blocking the commit and never
mutating. Door coverage, door distinct-points, and type-vocab
classification are fail-closed G1 gates: `door_coverage.py` (every active
connects_to edge between active locations carries both directed door
rows), `door_distinct_points.py` (within one active location carrying
non-NULL, positive bounds, no two `door` rows share the same `(x, y)`;
NULL-bounds locations excluded), and `location_type_classified.py` (every
active location's `location_type` is catalogued with a non-NULL
classification). `materialize_doors` re-derives a door still sitting at
the exact bounds center (`placement.is_legacy_center`) onto the perimeter
on its next run; every other existing point, hand-placed or
already-perimeter, is reused verbatim.

No DB, stdlib `ast` only.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
# Retargeted (TICKET-0028, BRIEF-0028-c): models.py split into a models/
# package by schema stratum — same class->table attribution, walked across
# every file in the package instead of one flat module (relocation-not-
# broadening precedent, BRIEF-0027-c/-d).
MODELS_DIR = SRC / "world_engine" / "models"
POLICY_FILE = ROOT / "tooling" / "verify" / "canon_write_policy.txt"

WRITE_METHODS = {"add", "delete"}
EXEC_METHODS = {"execute", "exec"}
SQL_KEYWORD_RE = re.compile(r"\b(?:INSERT INTO|DELETE FROM|UPDATE)\b")
SQL_TABLE_RE = re.compile(r"\b(?:INSERT INTO|DELETE FROM|UPDATE)\s+(\S+)")
DYNAMIC_MARK = "\x00"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


# ── Policy file ────────────────────────────────────────────────────────────

def parse_policy(text: str):
    canon_tables: set[str] = set()
    allowed: dict[str, set[str]] = {}
    section = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        if section == "CANON_TABLES":
            canon_tables.update(line.split())
        elif section == "ALLOWED_SITES":
            parts = line.split()
            if len(parts) < 2:
                fail(f"canon_write_policy.txt: malformed ALLOWED_SITES line: {raw!r}")
                continue
            site, tables = parts[0], set(parts[1:])
            if site in allowed:
                fail(f"canon_write_policy.txt: duplicate ALLOWED_SITES entry {site!r}")
            allowed[site] = tables
    return canon_tables, allowed


# ── models/*.py: class name -> table name ───────────────────────────────────

def _build_model_tables_one(models_path: pathlib.Path) -> dict[str, str]:
    tree = ast.parse(models_path.read_text(encoding="utf-8"), filename=str(models_path))
    out: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        is_table = any(
            kw.arg == "table" and isinstance(kw.value, ast.Constant) and kw.value.value is True
            for kw in node.keywords
        )
        if not is_table:
            continue
        for stmt in node.body:
            if (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and stmt.targets[0].id == "__tablename__"
                and isinstance(stmt.value, ast.Constant)
                and isinstance(stmt.value.value, str)
            ):
                out[node.name] = stmt.value.value
                break
    return out


def build_model_tables(models_dir: pathlib.Path) -> dict[str, str]:
    """Union the class->table map across every file in the models/ package
    (canon.py, ephemeral.py, pipeline.py, __init__.py — __init__.py itself
    defines no table classes, so it contributes nothing here)."""
    out: dict[str, str] = {}
    for path in sorted(models_dir.glob("*.py")):
        out.update(_build_model_tables_one(path))
    return out


def _subscript_key(node: ast.Subscript):
    s = node.slice
    if isinstance(s, ast.Index):  # pragma: no cover — pre-3.9 AST shape
        s = s.value
    if isinstance(s, ast.Constant):
        return s.value
    return None


def build_file_model_tables(tree: ast.Module, model_tables: dict[str, str]) -> dict[str, str]:
    """Overlay import aliases (`from ..models import X as Y`) onto the global map."""
    out = dict(model_tables)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[-1] == "models":
            for alias in node.names:
                if alias.name in model_tables:
                    out[alias.asname or alias.name] = model_tables[alias.name]
    return out


def _registry_target_name(node):
    """Module-level `NAME = {...}` or `NAME: T = {...}` — return NAME's dict
    literal value, or None if this assignment isn't a plain-name dict literal."""
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id, node.value
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
        return node.target.id, node.value
    return None, None


def build_registries(tree: ast.Module, file_model_tables: dict[str, str]) -> dict[str, set[str]]:
    """Module-level `NAME = {key: {..., "model": ModelClass, ...}, ...}` dict
    literals — resolves dynamic-dispatch-by-registry-lookup (e.g.
    `ENTITY_TYPE_REGISTRY[entity_type]["model"]`) to the union of every table
    the registry can produce."""
    registries: dict[str, set[str]] = {}
    for node in tree.body:
        name, value = _registry_target_name(node)
        if name is None or not isinstance(value, ast.Dict):
            continue
        tables: set[str] = set()
        for v in value.values:
            if not isinstance(v, ast.Dict):
                continue
            for k2, v2 in zip(v.keys, v.values):
                if (
                    isinstance(k2, ast.Constant) and k2.value == "model"
                    and isinstance(v2, ast.Name) and v2.id in file_model_tables
                ):
                    tables.add(file_model_tables[v2.id])
        if tables:
            registries[name] = tables
    return registries


def resolve_annotation_tables(ann, model_tables: dict[str, str]):
    """A type annotation naming a table class, either directly (`Entity`) or
    through one level of generic wrapping (`list[Entity]`, `List[Entity]`,
    `Optional[Entity]`, ...). Used both for `x: list[Model] = []` locals and
    for `-> list[Model]` return annotations — in both cases the resulting
    table set describes the ELEMENT type, which is what a `for` loop over the
    value (or over the call result) binds to."""
    if isinstance(ann, ast.Name) and ann.id in model_tables:
        return {model_tables[ann.id]}
    if isinstance(ann, ast.Subscript):
        slice_node = ann.slice
        if isinstance(slice_node, ast.Index):  # pragma: no cover — pre-3.9 AST shape
            slice_node = slice_node.value
        if isinstance(slice_node, ast.Name) and slice_node.id in model_tables:
            return {model_tables[slice_node.id]}
    return None


def build_return_types(tree: ast.Module, file_model_tables: dict[str, str]) -> dict[str, set[str]]:
    """Helper functions whose return annotation names a table class, directly
    or through `list[...]` — lets attribution follow through a same-file
    accessor helper without interprocedural analysis."""
    out: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            tables = resolve_annotation_tables(node.returns, file_model_tables)
            if tables:
                out[node.name] = tables
    return out


def augment_return_types_with_imports(tree: ast.Module, own_return_types: dict[str, set[str]], global_return_types: dict[str, set[str]]) -> dict[str, set[str]]:
    """Overlay cross-module function imports (`from ..analyzer import
    analyze_overhearing as _analyze_overhearing`) so a local alias of an
    imported helper resolves the same way a same-file helper does."""
    out = dict(own_return_types)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[-1] != "models":
            for alias in node.names:
                if alias.name in global_return_types:
                    out[alias.asname or alias.name] = global_return_types[alias.name]
    return out


# ── Per-function site collection ────────────────────────────────────────────

class FunctionScanner:
    def __init__(self, model_tables, registries, return_types):
        self.model_tables = model_tables
        self.registries = registries
        self.return_types = return_types

    def resolve(self, expr, var_tables):
        if expr is None:
            return None
        if isinstance(expr, ast.Name):
            if expr.id in self.model_tables:
                return {self.model_tables[expr.id]}
            return var_tables.get(expr.id)
        if isinstance(expr, ast.Call):
            func = expr.func
            if isinstance(func, ast.Name):
                if func.id in self.model_tables:
                    return {self.model_tables[func.id]}
                if func.id in self.return_types:
                    return self.return_types[func.id]
                return var_tables.get(func.id)
            if isinstance(func, ast.Attribute):
                if func.attr == "get" and expr.args:
                    return self.resolve(expr.args[0], var_tables)
                if func.attr in ("exec", "execute"):
                    for sub in ast.walk(expr):
                        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) \
                                and sub.func.id == "select" and sub.args:
                            return self.resolve(sub.args[0], var_tables)
                    return None
                # chained call, e.g. X.where(...).first()/.all()/.order_by(...)
                return self.resolve(func.value, var_tables)
            return None
        if isinstance(expr, ast.Subscript):
            key = _subscript_key(expr)
            if key == "model":
                base = expr.value
                while isinstance(base, ast.Subscript):
                    base = base.value
                if isinstance(base, ast.Name) and base.id in self.registries:
                    return self.registries[base.id]
            return None
        if isinstance(expr, ast.Attribute):
            return self.resolve(expr.value, var_tables)
        return None

    def resolve_annotation(self, ann):
        return resolve_annotation_tables(ann, self.model_tables)

    def scan_function(self, fn_node, base_sessions):
        var_tables: dict[str, "set[str] | None"] = {}
        args = list(fn_node.args.posonlyargs) + list(fn_node.args.args) + list(fn_node.args.kwonlyargs)
        for a in args:
            tables = resolve_annotation_tables(a.annotation, self.model_tables)
            if tables:
                var_tables[a.arg] = tables
        session_names = set(base_sessions)
        sites: list[dict] = []
        self._walk_stmts(fn_node.body, var_tables, session_names, sites)
        return sites

    def _walk_stmts(self, stmts, var_tables, session_names, sites):
        for stmt in stmts:
            if isinstance(stmt, ast.Assign):
                value_tables = self.resolve(stmt.value, var_tables)
                for tgt in stmt.targets:
                    if isinstance(tgt, ast.Name):
                        var_tables[tgt.id] = value_tables
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                ann_tables = self.resolve_annotation(stmt.annotation)
                val_tables = self.resolve(stmt.value, var_tables) if stmt.value is not None else None
                var_tables[stmt.target.id] = val_tables or ann_tables
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                self._handle_call(stmt.value, var_tables, session_names, sites, stmt.lineno)
            elif isinstance(stmt, ast.For):
                iter_tables = self.resolve(stmt.iter, var_tables)
                if isinstance(stmt.target, ast.Name):
                    var_tables[stmt.target.id] = iter_tables
                self._walk_stmts(stmt.body, var_tables, session_names, sites)
                self._walk_stmts(stmt.orelse, var_tables, session_names, sites)
            elif isinstance(stmt, ast.While):
                self._walk_stmts(stmt.body, var_tables, session_names, sites)
                self._walk_stmts(stmt.orelse, var_tables, session_names, sites)
            elif isinstance(stmt, ast.If):
                self._walk_stmts(stmt.body, var_tables, session_names, sites)
                self._walk_stmts(stmt.orelse, var_tables, session_names, sites)
            elif isinstance(stmt, ast.Try):
                self._walk_stmts(stmt.body, var_tables, session_names, sites)
                for h in stmt.handlers:
                    self._walk_stmts(h.body, var_tables, session_names, sites)
                self._walk_stmts(stmt.orelse, var_tables, session_names, sites)
                self._walk_stmts(stmt.finalbody, var_tables, session_names, sites)
            elif isinstance(stmt, ast.With):
                for item in stmt.items:
                    cexpr = item.context_expr
                    if (
                        isinstance(item.optional_vars, ast.Name)
                        and isinstance(cexpr, ast.Call)
                        and isinstance(cexpr.func, ast.Name)
                        and cexpr.func.id == "Session"
                    ):
                        session_names.add(item.optional_vars.id)
                self._walk_stmts(stmt.body, var_tables, session_names, sites)
            # FunctionDef/AsyncFunctionDef/ClassDef: handled as their own unit
            # elsewhere — never descended into here.

    def _handle_call(self, call, var_tables, session_names, sites, lineno):
        func = call.func
        if not isinstance(func, ast.Attribute):
            return
        if not (isinstance(func.value, ast.Name) and func.value.id in session_names):
            return
        attr = func.attr
        if attr in WRITE_METHODS:
            arg = call.args[0] if call.args else None
            tables = self.resolve(arg, var_tables) if arg is not None else None
            sites.append({"line": lineno, "tables": tables, "raw": False})
        elif attr in EXEC_METHODS:
            arg = call.args[0] if call.args else None
            sql_text = _render_sql_text(arg) if arg is not None else None
            if sql_text is None or not SQL_KEYWORD_RE.search(sql_text):
                return
            table = _extract_sql_table(sql_text)
            sites.append({"line": lineno, "tables": ({table} if table else None), "raw": True})


def _render_sql_text(node):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "text" and node.args:
        node = node.args[0]
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant):
                parts.append(str(v.value))
            else:
                parts.append(DYNAMIC_MARK)
        return "".join(parts)
    return None


def _extract_sql_table(sql_text: str):
    m = SQL_TABLE_RE.search(sql_text)
    if not m:
        return None
    token = m.group(1)
    if DYNAMIC_MARK in token:
        return None
    return token.strip()


# ── Function discovery (source order, closure-aware) ────────────────────────

def collect_functions(tree: ast.Module):
    """Yield (FunctionDef, inherited_session_param_names) for every function
    in the module, including nested ones — each is its own attribution unit
    (function-grain), but nested functions inherit the enclosing function's
    Session-typed parameters (Python closures do)."""
    out = []

    def session_params(node):
        names = set()
        args = list(node.args.posonlyargs) + list(node.args.args) + list(node.args.kwonlyargs)
        for a in args:
            if isinstance(a.annotation, ast.Name) and a.annotation.id in ("Session", "DbSession"):
                names.add(a.arg)
        return names

    def visit(node, inherited):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn_sessions = inherited | session_params(child)
                out.append((child, fn_sessions))
                visit(child, fn_sessions)
            else:
                visit(child, inherited)

    visit(tree, frozenset())
    return out


# ── Driver ───────────────────────────────────────────────────────────────────

def _parse(path: pathlib.Path):
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        fail(f"{path}: SyntaxError: {exc}")
        return None


def check_file(path: pathlib.Path, tree: ast.Module, model_tables, global_return_types, canon_tables, allowed_sites):
    rel = path.relative_to(ROOT).as_posix()
    file_model_tables = build_file_model_tables(tree, model_tables)
    registries = build_registries(tree, file_model_tables)
    own_return_types = build_return_types(tree, file_model_tables)
    return_types = augment_return_types_with_imports(tree, own_return_types, global_return_types)
    scanner = FunctionScanner(file_model_tables, registries, return_types)

    for fn_node, base_sessions in collect_functions(tree):
        site_key = f"{rel}::{fn_node.name}"
        allowed_tables = allowed_sites.get(site_key)
        if allowed_tables == {"*"}:
            continue  # wildcard-allowed function — every write inside is sanctioned

        for site in scanner.scan_function(fn_node, base_sessions):
            tables = site["tables"]
            if tables is None:
                fail(f"{site_key} — unattributable write site (line {site['line']})")
                continue
            for table in sorted(tables):
                if table not in canon_tables:
                    continue
                if allowed_tables is None or table not in allowed_tables:
                    fail(f"{site_key} writes {table} — not in canon_write_policy.txt")


def main() -> None:
    if not POLICY_FILE.exists():
        fail(f"{POLICY_FILE} not found")
        _report_and_exit()
        return
    if not MODELS_DIR.is_dir():
        fail(f"{MODELS_DIR} not found")
        _report_and_exit()
        return

    canon_tables, allowed_sites = parse_policy(POLICY_FILE.read_text(encoding="utf-8"))
    model_tables = build_model_tables(MODELS_DIR)

    paths = sorted(SRC.rglob("*.py"))
    trees: dict[pathlib.Path, ast.Module] = {}
    global_return_types: dict[str, set[str]] = {}

    # Pass 1: parse every file, collect each file's OWN return-type facts
    # (same-file helper functions) into a cross-file lookup — needed before
    # pass 2 can resolve an import alias of a helper defined elsewhere.
    for path in paths:
        tree = _parse(path)
        if tree is None:
            continue
        trees[path] = tree
        file_model_tables = build_file_model_tables(tree, model_tables)
        for fn_name, tables in build_return_types(tree, file_model_tables).items():
            global_return_types.setdefault(fn_name, tables)

    # Pass 2: full attribution per file, now with cross-file return types available.
    for path, tree in trees.items():
        check_file(path, tree, model_tables, global_return_types, canon_tables, allowed_sites)

    _report_and_exit()


def _report_and_exit() -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: no canon write outside a sanctioned site")
    sys.exit(0)


if __name__ == "__main__":
    main()
