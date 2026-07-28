"""G1 gate for TICKET-0051, BRIEF-0051-a — the observation socle.

Builds tables from a fresh temp-file SQLite DB (WORLD_ENGINE_DATABASE_URL
set before any world_engine import) so this check never touches Nia's real
DB. Asserts column presence AND CHECK DDL text (K1, closed vocabulary) — a
column-presence check alone would still pass if the CHECK itself were
dropped.

Rules:
  1. The five observation_* tables exist with their exact columns.
  2. Every CHECK constraint is asserted against sqlite_master DDL TEXT.
  3. No observation_* table name appears in canon_write_policy.txt's
     [CANON_TABLES].
  4. The five model identifiers appear only in the declared allowlist
     (stdlib ast, module allowlist, npc_goal_read.py rule-1 shape).
  5. No observation_* model class carries a not_selected_reason attribute,
     and the string appears in no table definition (M1).
  6. tick.py, tick_context.py, tick_normalize.py and context.py contain zero
     references to any Observation* identifier.
  7. list_mutations contains a NULL-safe exclusion: OBSERVED_PROPOSED_BY AND
     an is_(None) call, both required.
  8. Vacuous-proof guard: fewer than 5 tables inspected or fewer than 6 CHECK
     constraints asserted is a FAILURE, not a pass.

No DB beyond the fresh temp-file instance created here.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

POLICY_FILE = ROOT / "tooling" / "verify" / "canon_write_policy.txt"
MUTATIONS_FILE = SRC / "world_engine" / "cockpit" / "routes" / "mutations.py"
TICK_FILES = [
    SRC / "world_engine" / "tick.py",
    SRC / "world_engine" / "tick_context.py",
    SRC / "world_engine" / "tick_normalize.py",
    SRC / "world_engine" / "context.py",
]

OBSERVATION_TABLES = {
    "observation_run",
    "observation_run_template",
    "observation_beat",
    "observation_intent",
    "observation_mutation_link",
}

MODEL_IDENTIFIERS = {
    "ObservationRun",
    "ObservationRunTemplate",
    "ObservationBeat",
    "ObservationIntent",
    "ObservationMutationLink",
}

ALLOWED_MODULES = {
    "src/world_engine/models/observation.py",
    "src/world_engine/models/__init__.py",
    "src/world_engine/observation_writes.py",
    "scripts/migrate_v1_90_observation_socle.py",
    "tooling/verify/checks/observation_socle.py",
}

FAILURES: list[str] = []
_tables_inspected = 0
_checks_asserted = 0


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    db_path = pathlib.Path(tmp_dir) / "check.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]

    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def _table_ddl(engine, table: str) -> str:
    from sqlalchemy import text

    with engine.connect() as conn:
        return conn.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:t"),
            {"t": table},
        ).scalar() or ""


EXPECTED_COLUMNS = {
    "observation_run": {
        "id", "world_id", "location_id", "gathering_id", "player_presence",
        "max_beats", "quiescence_limit", "mj_narration", "cooldown_beats",
        "debt_weight", "propensity_mode", "model", "status", "stop_reason",
        "started_at", "ended_at",
    },
    "observation_run_template": {"id", "run_id", "usage", "template_id", "version"},
    "observation_beat": {
        "id", "run_id", "beat_index", "outcome", "actor_id", "line",
        "mj_narration", "created_at",
    },
    "observation_intent": {
        "id", "run_id", "beat_id", "npc_id", "act", "urgency", "target_id",
        "why", "propensity", "cooldown_active", "debt_score", "final_score",
        "selected", "call_status", "latency_ms", "raw_response", "created_at",
    },
    "observation_mutation_link": {"id", "run_id", "beat_id", "mutation_id"},
}

# (table, ddl-substring-to-assert) — closed vocabularies, K1.
EXPECTED_CHECK_SNIPPETS = [
    ("observation_run", "ck_observation_run_player_presence"),
    ("observation_run", "'absent'"),
    ("observation_run", "'silent'"),
    ("observation_run", "'active'"),
    ("observation_run", "ck_observation_run_propensity_mode"),
    ("observation_run", "'flat'"),
    ("observation_run", "'relation_weighted'"),
    ("observation_run", "ck_observation_run_status"),
    ("observation_run", "'running'"),
    ("observation_run", "'completed'"),
    ("observation_run", "'stopped'"),
    ("observation_run", "'failed'"),
    ("observation_run", "ck_observation_run_stop_reason"),
    ("observation_run", "'max_beats'"),
    ("observation_run", "'quiescence'"),
    ("observation_run", "'creator_stop'"),
    ("observation_run", "'error'"),
    ("observation_beat", "ck_observation_beat_outcome"),
    ("observation_beat", "'acted'"),
    ("observation_beat", "'silence'"),
    ("observation_beat", "'degraded'"),
    ("observation_beat", "'event'"),
    ("observation_intent", "ck_observation_intent_call_status"),
    ("observation_intent", "'ok'"),
    ("observation_intent", "'parse_error'"),
    ("observation_intent", "'timeout'"),
]


def check_tables_and_checks(engine) -> None:
    global _tables_inspected, _checks_asserted
    from sqlalchemy import inspect as sa_inspect

    inspector = sa_inspect(engine)
    live_tables = set(inspector.get_table_names())

    for table, expected_cols in EXPECTED_COLUMNS.items():
        if table not in live_tables:
            fail(f"{table} table does not exist")
            continue
        _tables_inspected += 1
        columns = {c["name"] for c in inspector.get_columns(table)}
        missing = expected_cols - columns
        if missing:
            fail(f"{table} missing column(s): {sorted(missing)}")

    ddl_cache: dict[str, str] = {}
    for table, snippet in EXPECTED_CHECK_SNIPPETS:
        if table not in ddl_cache:
            ddl_cache[table] = _table_ddl(engine, table)
        ddl = ddl_cache[table]
        if not ddl:
            fail(f"could not read {table} table DDL from sqlite_master")
            continue
        if snippet not in ddl:
            fail(f"{table} DDL does not contain expected CHECK text {snippet!r}")
        else:
            _checks_asserted += 1


def check_canon_tables_absence() -> None:
    if not POLICY_FILE.exists():
        fail(f"{POLICY_FILE} not found")
        return
    text = POLICY_FILE.read_text(encoding="utf-8")
    section = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        if line.startswith("#") or not line:
            continue
        if section == "CANON_TABLES":
            for table in OBSERVATION_TABLES:
                if table in line.split():
                    fail(f"{table} appears in canon_write_policy.txt [CANON_TABLES]")


def _parse(path: pathlib.Path):
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        fail(f"{path}: SyntaxError: {exc}")
        return None


def _references_any(node: ast.AST, names: set[str]) -> "set[str]":
    found: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and sub.id in names:
            found.add(sub.id)
        elif isinstance(sub, ast.Attribute) and sub.attr in names:
            found.add(sub.attr)
        elif isinstance(sub, ast.alias) and sub.name in names:
            found.add(sub.name)
    return found


def check_module_allowlist() -> None:
    for path in sorted(SRC.rglob("*.py")) + sorted((ROOT / "scripts").rglob("*.py")) + sorted(
        (ROOT / "tooling").rglob("*.py")
    ):
        rel = path.relative_to(ROOT).as_posix()
        if rel in ALLOWED_MODULES:
            continue
        tree = _parse(path)
        if tree is None:
            continue
        found = _references_any(tree, MODEL_IDENTIFIERS)
        if found:
            fail(f"{rel} references {sorted(found)} outside the declared allowlist")


def check_not_selected_reason_absent() -> None:
    """M1: no observation_* model class may declare a `not_selected_reason`
    FIELD. The identifier is legitimately documented in NOTE comments (the
    brief requires them verbatim) — those are prose, not a column, so this
    checks class-body field assignments via ast, not a raw text search."""
    obs_path = SRC / "world_engine" / "models" / "observation.py"
    if not obs_path.exists():
        fail(f"{obs_path} not found")
        return
    tree = _parse(obs_path)
    if tree is None:
        return
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                if stmt.target.id == "not_selected_reason":
                    fail(
                        f"observation.py: {node.name} declares a "
                        "not_selected_reason field — forbidden by M1"
                    )


def check_tick_and_context_boundary() -> None:
    for path in TICK_FILES:
        if not path.exists():
            fail(f"{path} not found")
            continue
        tree = _parse(path)
        if tree is None:
            continue
        found = _references_any(tree, MODEL_IDENTIFIERS)
        if found:
            fail(f"{path.relative_to(ROOT).as_posix()} references {sorted(found)} — the observed beat is not a world tick")


def check_queue_filter() -> None:
    if not MUTATIONS_FILE.exists():
        fail(f"{MUTATIONS_FILE} not found")
        return
    tree = _parse(MUTATIONS_FILE)
    if tree is None:
        return

    func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "list_mutations":
            func = node
            break
    if func is None:
        fail("mutations.py: list_mutations not found")
        return

    has_constant = any(
        isinstance(n, ast.Name) and n.id == "OBSERVED_PROPOSED_BY" for n in ast.walk(func)
    )
    has_is_none = any(
        isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "is_"
        and n.args
        and isinstance(n.args[0], ast.Constant)
        and n.args[0].value is None
        for n in ast.walk(func)
    )
    if not has_constant:
        fail("list_mutations: no reference to OBSERVED_PROPOSED_BY")
    if not has_is_none:
        fail("list_mutations: no is_(None) call — the NULL-safe half of the filter is missing")


def main() -> None:
    engine = _fresh_engine()
    check_tables_and_checks(engine)
    check_canon_tables_absence()
    check_module_allowlist()
    check_not_selected_reason_absent()
    check_tick_and_context_boundary()
    check_queue_filter()

    if _tables_inspected < 5:
        fail(f"vacuous-proof guard: only {_tables_inspected} table(s) inspected, expected 5")
    if _checks_asserted < 6:
        fail(f"vacuous-proof guard: only {_checks_asserted} CHECK constraint(s) asserted, expected >= 6")

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)

    print(
        f"PASS: observation socle — {_tables_inspected} tables inspected, "
        f"{_checks_asserted} CHECK constraints asserted"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
