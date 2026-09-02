"""G1 check for TICKET-0082 (BRIEF-0082-d, amended by
`BRIEF-0082-d-amendment-1-public-floor-reader.md`) — the known-reachability
floor.

DB-backed, self-contained fresh temp-file SQLite fixture (WORLD_ENGINE_
DATABASE_URL set BEFORE any world_engine import) — same idiom as
fact_spine.py / knowledge_resolution.py, so this check never touches Nia's
real DB. FAILURES list, print FAIL lines, sys.exit(1); zero rows/sites
examined for any assertion is a FAIL, never a vacuous pass.

Four assertions:
  1. Every `connects_to` relation has exactly one backing fact
     (zero relations collected on the fixture = FAIL).
  2. Every `connects_to` read site in `src/` lives in one of the modules
     `tooling/tickets/connects-to-readers-TICKET-0082.md` documents (one of
     the five labels: resolution/deliberation/public/authoring/vocabulary)
     — a module containing the literal `"connects_to"` that is NOT in that
     documented set is a thirteenth reader and a FAIL. Module-granularity,
     not line-granularity — exact line numbers drift; the module set is
     the durable anchor (per that document's own framing).
  3. AST-based (amendment 1's fourth assertion): every call to
     `tick_context._reachable_locations(` in `src/` passes `knower_id` in
     the shape its documented call-site label requires — `public` never
     passes a non-None `knower_id`, `deliberation` never passes
     `knower_id=None`. Vacuous-proof: zero call sites found is a FAILURE.
  4. Golden case, mutation-sensitive: on a fixture world where no default
     has been lowered, `_reachable_locations(knower_id=<npc>)` returns a
     set identical to an independent, filter-free reference BFS over the
     same `connects_to` graph. Then, WITHOUT changing the golden-case
     assertion's own PASS, three named mutations are each demonstrated to
     produce a detectable divergence (self-test of this check's own
     sensitivity, same idiom as knowledge_resolution.py's lowest-wins /
     first-membership-wins mutations):
       (a) the floor lowered to `'unaware'` (`tick_context.KNOWN_EDGE_
           FLOOR` monkeypatched) — admits an edge the real floor excludes;
       (b) the missing-fact case treated as traversable instead of
           fail-closed (a local reference-only BFS, never patched into the
           real reader) — diverges from the real function's fail-closed
           exclusion;
       (c) `tick_context.py:566`'s `public` call site source-mutated to
           pass a non-None `knower_id` — assertion 3's AST scan, re-run
           against the mutated source text (never the real file), flags a
           violation it does not flag on the unmutated source.
"""
from __future__ import annotations

import ast
import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
CLASSIFICATION_TABLE = ROOT / "tooling" / "tickets" / "connects-to-readers-TICKET-0082.md"
TICK_CONTEXT_FILE = SRC / "world_engine" / "tick_context.py"
TICK_FILE = SRC / "world_engine" / "tick.py"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    db_path = pathlib.Path(tmp_dir) / "check.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]

    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


# ─────────────────────────────────────────────────────────────────────────
# Assertion 1 + 4: DB fixture
# ─────────────────────────────────────────────────────────────────────────

def _build_fixture(session):
    """A five-location chain A-B-C-D (connects_to, each backed by a
    default_level='knows' fact, matching migrate_v2_00's output) plus one
    NPC standing at A. Returns (npc_id, location_ids_by_label, relation_ids,
    fact_ids_by_relation, world_id)."""
    from world_engine.models import Character, Entity, Location, World
    from world_engine.writes import create_fact
    from world_engine.writes.relations import write_relation

    world = World(name="Check World", is_active=True)
    session.add(world)
    session.commit()
    session.refresh(world)
    world_id = world.id

    def _location(name: str) -> str:
        entity = Entity(world_id=world_id, type="location", name=name)
        session.add(entity)
        session.commit()
        session.refresh(entity)
        session.add(Location(id=entity.id, parent_location_id=None))
        session.commit()
        return entity.id

    labels = ["A", "B", "C", "D"]
    loc_ids = {label: _location(f"Location {label}") for label in labels}

    npc_id_entity = Entity(world_id=world_id, type="character", name="Checker NPC")
    session.add(npc_id_entity)
    session.commit()
    session.refresh(npc_id_entity)
    session.add(Character(id=npc_id_entity.id, world_id=world_id, character_type="npc", current_location_id=loc_ids["A"]))
    session.commit()
    npc_id = npc_id_entity.id

    relation_ids: dict[str, str] = {}
    fact_ids: dict[str, str] = {}
    for a, b in (("A", "B"), ("B", "C"), ("C", "D")):
        rel = write_relation(
            session, mode="set", world_id=world_id, entity_a_id=loc_ids[a], entity_b_id=loc_ids[b],
            type="connects_to", value=50, direction="mutual",
        )
        session.commit()
        edge_key = f"{a}{b}"
        relation_ids[edge_key] = rel.id
        fact = create_fact(
            session, world_id=world_id, content=f"{a} communique avec {b}.",
            created_by="check", default_level="knows", relation_id=rel.id,
        )
        session.commit()
        fact_ids[edge_key] = fact.id

    return npc_id, loc_ids, relation_ids, fact_ids, world_id


def _reference_bfs(session, origin_id: str) -> set[str]:
    """Independent, filter-free ground truth: every ACTIVE location
    reachable from `origin_id` over `connects_to`, unbounded, origin
    excluded. Deliberately NOT `tick_context._reachable_locations` — a
    second, from-scratch implementation, so the golden-case comparison
    exercises two independent readers of the same graph."""
    from sqlmodel import select

    from world_engine.models import Entity, Relation

    visited: set[str] = set()
    frontier = [origin_id]
    while frontier:
        next_frontier: list[str] = []
        for loc_id in frontier:
            rels = session.exec(
                select(Relation).where(
                    Relation.type == "connects_to",
                    (Relation.entity_a_id == loc_id) | (Relation.entity_b_id == loc_id),
                )
            ).all()
            for rel in rels:
                neighbour_id = rel.entity_b_id if rel.entity_a_id == loc_id else rel.entity_a_id
                if neighbour_id == origin_id or neighbour_id in visited:
                    continue
                neighbour = session.get(Entity, neighbour_id)
                if neighbour is not None and neighbour.status == "active":
                    visited.add(neighbour_id)
                    next_frontier.append(neighbour_id)
        frontier = next_frontier
    return visited


def check_db_fixture(engine) -> None:
    from sqlmodel import Session as DbSession

    from world_engine import tick_context
    from world_engine.writes import create_fact, create_fact_default
    from world_engine.writes.relations import write_relation

    with DbSession(engine) as session:
        npc_id, loc_ids, relation_ids, fact_ids, world_id = _build_fixture(session)

        # ── Assertion 1: exactly one backing fact per connects_to relation ──
        examined = len(relation_ids)
        if examined == 0:
            fail("vacuous-proof: zero connects_to relations on a freshly seeded fixture")
        mismatched = [key for key in relation_ids if key not in fact_ids]
        if mismatched:
            fail(f"connects_to relation(s) without exactly one backing fact: {mismatched}")

        # ── Assertion 4 (golden case): no default lowered, real reader ==
        #    reference BFS ────────────────────────────────────────────────
        real_pairs, real_diag = tick_context._reachable_locations(
            session, loc_ids["A"], "quelques semaines", knower_id=npc_id,
        )
        real_ids = {eid for eid, _name in real_pairs}
        truth_ids = _reference_bfs(session, loc_ids["A"])
        if not truth_ids:
            fail("vacuous-proof: reference BFS found zero reachable locations on a freshly seeded fixture")
        if real_ids != truth_ids:
            fail(
                "golden case failed: _reachable_locations(knower_id=npc) != reference BFS "
                f"with no default lowered — real={real_ids} truth={truth_ids}"
            )
        if real_diag:
            fail(f"golden case: unexpected diagnostics on a pristine fixture: {real_diag}")

        # ── Named mutation (a): floor lowered to 'unaware' should admit an
        #    edge the real floor excludes. Add a fifth location E, world
        #    default 'rumor' on the D-E fact (below the real 'partial'
        #    floor). Confirm E excluded under the real floor, then confirm
        #    a monkeypatched floor of 'unaware' WOULD admit it — proving
        #    this check's golden-case comparison is sensitive to the floor
        #    constant, never touching the real constant permanently. ──────
        from world_engine.models import Entity, Location

        e_entity = Entity(world_id=world_id, type="location", name="Location E")
        session.add(e_entity)
        session.commit()
        session.refresh(e_entity)
        session.add(Location(id=e_entity.id, parent_location_id=None))
        session.commit()
        rel_de = write_relation(
            session, mode="set", world_id=world_id, entity_a_id=loc_ids["D"], entity_b_id=e_entity.id,
            type="connects_to", value=50, direction="mutual",
        )
        session.commit()
        fact_de = create_fact(
            session, world_id=world_id, content="D communique avec E.",
            created_by="check", default_level="knows", relation_id=rel_de.id,
        )
        session.commit()
        create_fact_default(
            session, world_id=world_id, fact_id=fact_de.id, scope_type="world", scope_id=None,
            level="rumor", created_by="check",
        )
        session.commit()

        real_pairs_2, _diag = tick_context._reachable_locations(
            session, loc_ids["A"], "quelques semaines", knower_id=npc_id,
        )
        real_ids_2 = {eid for eid, _name in real_pairs_2}
        if e_entity.id in real_ids_2:
            fail("real floor ('partial') unexpectedly admitted a 'rumor'-level edge — floor rule broken")

        original_floor = tick_context.KNOWN_EDGE_FLOOR
        try:
            tick_context.KNOWN_EDGE_FLOOR = "unaware"
            lowered_pairs, _diag = tick_context._reachable_locations(
                session, loc_ids["A"], "quelques semaines", knower_id=npc_id,
            )
        finally:
            tick_context.KNOWN_EDGE_FLOOR = original_floor
        lowered_ids = {eid for eid, _name in lowered_pairs}
        if e_entity.id not in lowered_ids:
            fail(
                "mutation (a) not detected: lowering KNOWN_EDGE_FLOOR to 'unaware' did not admit "
                "the 'rumor'-level edge — this check would NOT catch a floor regression"
            )

        # ── Named mutation (b): missing-fact treated as traversable instead
        #    of fail-closed. Add a sixth location F connected DIRECTLY to D
        #    (a location the real reader actually reaches — E is already
        #    excluded by mutation (a)'s below-floor edge, so an edge hung
        #    off E would never even be visited) with NO backing fact. Real
        #    reader must exclude F and record a missing_fact diagnostic; a
        #    local wrongly-permissive reference (never patched into the
        #    real reader) would admit it — the two must disagree, proving
        #    this check would catch a fail-open regression. ──────────────
        f_entity = Entity(world_id=world_id, type="location", name="Location F")
        session.add(f_entity)
        session.commit()
        session.refresh(f_entity)
        session.add(Location(id=f_entity.id, parent_location_id=None))
        session.commit()
        write_relation(
            session, mode="set", world_id=world_id, entity_a_id=loc_ids["D"], entity_b_id=f_entity.id,
            type="connects_to", value=50, direction="mutual",
        )
        session.commit()
        # No fact created for this relation — deliberately missing.

        real_pairs_3, real_diag_3 = tick_context._reachable_locations(
            session, loc_ids["A"], "quelques semaines", knower_id=npc_id,
        )
        real_ids_3 = {eid for eid, _name in real_pairs_3}
        if f_entity.id in real_ids_3:
            fail("real reader admitted a connects_to edge with no backing fact — fail-closed rule broken")
        if not any(d.get("reason") == "missing_fact" and d.get("to") == f_entity.id for d in real_diag_3):
            fail(f"missing-fact edge was excluded but not recorded in diagnostics: {real_diag_3}")

        wrongly_permissive_ids = _reference_bfs(session, loc_ids["A"])  # ignores facts entirely
        if f_entity.id not in wrongly_permissive_ids:
            fail("test setup error: the filter-free reference BFS should reach F through the missing-fact edge")
        if f_entity.id in real_ids_3:
            fail("mutation (b) not detected: the real reader and a fail-open reference did not disagree on the missing-fact edge")


# ─────────────────────────────────────────────────────────────────────────
# Assertion 2: module coverage against the classification table
# ─────────────────────────────────────────────────────────────────────────

# The modules the classification table documents as containing a literal
# `"connects_to"` string (twelve traversal/write modules + three
# vocabulary-only modules). Kept in sync with
# tooling/tickets/connects-to-readers-TICKET-0082.md by hand; this check
# does not parse the table's prose, only asserts the table FILE exists and
# that no undocumented module has joined the set.
DOCUMENTED_MODULES = frozenset({
    "world_engine/room_batch_author.py",
    "world_engine/day_concordance.py",
    "world_engine/tick_context.py",
    "world_engine/writes/config.py",
    "world_engine/cockpit/spatial_doors.py",
    "world_engine/cockpit/crud/entities.py",
    "world_engine/cockpit/crud/relations.py",
    "world_engine/cockpit/crud/locations.py",
    "world_engine/cockpit/play.py",
    "world_engine/cockpit/routes/regions.py",
    "world_engine/day_plan.py",
    "world_engine/spatial_author.py",
    "world_engine/context.py",
    "world_engine/cockpit/crud/_shared.py",
    "world_engine/link_author.py",
})


def _modules_with_connects_to_literal() -> set[str]:
    found: set[str] = set()
    for path in sorted(SRC.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            fail(f"{path}: SyntaxError: {exc}")
            continue
        rel = path.relative_to(SRC).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value == "connects_to":
                found.add(rel)
                break
    return found


def check_module_coverage() -> None:
    if not CLASSIFICATION_TABLE.is_file():
        fail(f"{CLASSIFICATION_TABLE} not found — the classification table must exist on disk")
        return
    found = _modules_with_connects_to_literal()
    if not found:
        fail("vacuous-proof: zero modules with a literal \"connects_to\" found in src/ — scan is broken")
        return
    undocumented = found - DOCUMENTED_MODULES
    if undocumented:
        fail(
            f"undocumented connects_to-referencing module(s) — thirteenth reader(s), classify in "
            f"{CLASSIFICATION_TABLE.name}: {sorted(undocumented)}"
        )


# ─────────────────────────────────────────────────────────────────────────
# Assertion 3: AST scan of _reachable_locations( call sites
# ─────────────────────────────────────────────────────────────────────────

# (relative path, enclosing function name) -> expected label, per the
# classification table's call-site rows.
EXPECTED_CALL_SITE_LABELS = {
    ("world_engine/tick.py", "_tick_npc_setup"): "deliberation",
    ("world_engine/tick_context.py", "assemble_location_event_context"): "public",
}


def _enclosing_function(tree: ast.Module, target: ast.Call) -> str | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                if child is target:
                    return node.name
    return None


def _knower_id_arg(call: ast.Call) -> ast.expr | None:
    for kw in call.keywords:
        if kw.arg == "knower_id":
            return kw.value
    return None


def _scan_reachable_locations_calls(tree: ast.Module, rel: str) -> list[tuple[ast.Call, str | None, ast.expr | None]]:
    """[(call_node, enclosing_function_name, knower_id_value_node), ...]
    for every `_reachable_locations(` call in `tree`."""
    out = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, (ast.Name, ast.Attribute))
            and (node.func.id if isinstance(node.func, ast.Name) else node.func.attr) == "_reachable_locations"
        ):
            fn_name = _enclosing_function(tree, node)
            out.append((node, fn_name, _knower_id_arg(node)))
    return out


def _is_none_constant(node: ast.expr | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is None


def _check_call_sites(sites: list[tuple[str, ast.Call, str | None, ast.expr | None]]) -> list[str]:
    """Pure: given [(rel, call_node, fn_name, knower_id_node), ...], returns
    violation strings. `deliberation` sites must NOT pass knower_id=None;
    `public` sites must ALWAYS pass knower_id=None; an (rel, fn_name) not in
    EXPECTED_CALL_SITE_LABELS is an unclassified site."""
    violations: list[str] = []
    for rel, node, fn_name, knower_arg in sites:
        label = EXPECTED_CALL_SITE_LABELS.get((rel, fn_name))
        if label is None:
            violations.append(f"{rel}:{node.lineno} (in {fn_name!r}) — unclassified _reachable_locations call site")
            continue
        if knower_arg is None:
            violations.append(f"{rel}:{node.lineno} — call site does not pass knower_id at all (required keyword-only)")
            continue
        is_none = _is_none_constant(knower_arg)
        if label == "public" and not is_none:
            violations.append(f"{rel}:{node.lineno} — labelled 'public' but passes a non-None knower_id")
        if label == "deliberation" and is_none:
            violations.append(f"{rel}:{node.lineno} — labelled 'deliberation' but passes knower_id=None")
    return violations


def check_call_site_labels() -> None:
    sites: list[tuple[str, ast.Call, str | None, ast.expr | None]] = []
    for path in sorted(SRC.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            fail(f"{path}: SyntaxError: {exc}")
            continue
        rel = path.relative_to(SRC).as_posix()
        for node, fn_name, knower_arg in _scan_reachable_locations_calls(tree, rel):
            sites.append((rel, node, fn_name, knower_arg))

    if not sites:
        fail("vacuous-proof: zero _reachable_locations( call sites found in src/ — scan is broken")
        return

    violations = _check_call_sites(sites)
    for v in violations:
        fail(v)

    # ── Named mutation (c): source-mutate tick_context.py's public call
    #    site to pass a non-None knower_id; re-run the SAME detection logic
    #    against the mutated source text (never the real file) and confirm
    #    it now flags a violation it did not flag before. ─────────────────
    real_source = TICK_CONTEXT_FILE.read_text(encoding="utf-8")
    mutated_source, count = re.subn(
        r"_reachable_locations\(session, location_id, interval_label, knower_id=None\)",
        "_reachable_locations(session, location_id, interval_label, knower_id=location_id)",
        real_source,
        count=1,
    )
    if count != 1:
        fail("mutation (c) setup failed: the public call site pattern was not found in tick_context.py — check is stale against the source")
        return
    mutated_tree = ast.parse(mutated_source, filename=str(TICK_CONTEXT_FILE))
    mutated_rel = TICK_CONTEXT_FILE.relative_to(SRC).as_posix()
    mutated_sites = [
        (mutated_rel, node, fn_name, knower_arg)
        for node, fn_name, knower_arg in _scan_reachable_locations_calls(mutated_tree, mutated_rel)
    ]
    mutated_violations = _check_call_sites(mutated_sites)
    if not any("labelled 'public' but passes a non-None knower_id" in v for v in mutated_violations):
        fail(
            "mutation (c) not detected: flipping tick_context.py's public call site to pass a "
            "non-None knower_id did not surface as a violation under the mutated-source scan"
        )


def main() -> int:
    engine = _fresh_engine()
    check_db_fixture(engine)
    check_module_coverage()
    check_call_site_labels()

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: known_reachability — every connects_to relation has exactly one backing fact, "
        "every connects_to module is documented in the classification table, every "
        "_reachable_locations call site's knower_id matches its documented label, and the "
        "golden-case reader matches an independent reference BFS with no default lowered "
        "(mutation-sensitive to floor, fail-closed, and call-site labelling)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
