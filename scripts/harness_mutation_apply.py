"""Disposable record/replay harness for `_apply_mutation` (BRIEF-0027-c).

Proves the `_apply_mutation` decomposition (app.py -> cockpit/mutations.py)
is behavior-preserving. Disposable: deleted at TICKET-0027 stage g along
with the transition baselines it exists to protect (sibling of
`harness_say_replay.py`, same DB-copy discipline — never the live DB).
`print` is fine here — this script lives in scripts/, never in src/.

Unlike `say`, applying a stored proposal involves NO model call, so there
is nothing to record from Ollama — record mode's only job is to snapshot
the live DB, synthesize one `proposed_mutation` proposal per mutation type
(inserting supporting canon rows first where none exist, e.g. an active
`npc_goal`/`agenda` to act on), apply each through the exact production
path (`db.begin_nested()` + `_apply_mutation`, mirroring `approve_mutation`
in app.py), and capture normalized before/after dumps of every touched
table plus each apply's returned error string (None on success).

Replay mode restores the exact DB snapshot the record run started from,
re-applies the SAME (already-resolved) proposals, and diffs the write-sets
against the recorded fixtures. Empty diff = PASS. One proposal
(`goal_change create_short` with a dangling `agenda_id`) is deliberately
invalid — `write_goal_agenda_link` raises inside the SAVEPOINT after
`write_npc_goal` has already added a row, so a passing replay also proves
the SAVEPOINT rolls back that partial write (zero residual `npc_goal` rows
for it).

Usage:
    python scripts/harness_mutation_apply.py record
    python scripts/harness_mutation_apply.py replay
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Optional

FIXTURE_DIR = Path(__file__).parent / "harness_mutation_fixtures"
WORKDB_PATH = FIXTURE_DIR / "workdb.sqlite"
PRESTATE_PATH = FIXTURE_DIR / "pre_state.sqlite"
RESULTS_PATH = FIXTURE_DIR / "apply_results.json"
DUMPS_PATH = FIXTURE_DIR / "db_dumps.json"

LIVE_DB_PATH = Path.home() / ".world_engine" / "world_engine.db"

WORLD_ID = "verkhaal"
LOC_TAVERN = "loc-dernier-verre"
LOC_OTHER = "8e2bc0ec-09b4-4a17-9b69-74212671796d"  # La Mer Rouge
FAC_GUARD = "fac-guard"
NPC_MAELIS = "npc-maelis"
NPC_REIKE = "npc-reike"
NPC_SENNA = "npc-senna"
PLAYER = "char-player"
ITEM_DAGUE = "item-dague"
KNOWLEDGE_ROW = "kn-maelis-incidents"  # level "partial"

DUMP_TABLES = [
    "entity", "character", "item", "knowledge", "relation", "ledger",
    "npc_goal", "goal_agenda_link", "agenda", "agenda_step", "event",
    "event_entity", "gathering_member",
]

_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_TS_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(\+\d{2}:\d{2}|Z)?"
)


def _sqlite_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()
    source = sqlite3.connect(src)
    target = sqlite3.connect(dst)
    try:
        source.backup(target)
    finally:
        source.close()
        target.close()


def _prepare_workdb(mode: str) -> None:
    if mode == "record":
        if not LIVE_DB_PATH.exists():
            raise SystemExit(f"Live DB not found at {LIVE_DB_PATH}")
        _sqlite_copy(LIVE_DB_PATH, WORKDB_PATH)
        _sqlite_copy(LIVE_DB_PATH, PRESTATE_PATH)
    else:
        if not PRESTATE_PATH.exists():
            raise SystemExit(
                f"No recorded pre-state at {PRESTATE_PATH} — run `record` first."
            )
        _sqlite_copy(PRESTATE_PATH, WORKDB_PATH)


def _normalize_text(value: str, mapping: dict[tuple[str, str], str]) -> str:
    def repl_uuid(m: re.Match) -> str:
        key = ("uuid", m.group(0))
        if key not in mapping:
            mapping[key] = f"<uuid:{len(mapping)}>"
        return mapping[key]

    def repl_ts(m: re.Match) -> str:
        key = ("ts", m.group(0))
        if key not in mapping:
            mapping[key] = f"<ts:{len(mapping)}>"
        return mapping[key]

    value = _UUID_RE.sub(repl_uuid, value)
    value = _TS_RE.sub(repl_ts, value)
    return value


def _dump_db(db_path: Path) -> dict[str, list[dict]]:
    """Normalized snapshot of every table a mutation apply can touch.
    Traversal order is fixed (table list order, rowid order, sorted column
    names) so the placeholder mapping for volatile values (UUIDs,
    timestamps) is assigned identically whenever the underlying writes are
    structurally identical — which is exactly the property being tested."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    mapping: dict[tuple[str, str], str] = {}
    dump: dict[str, list[dict]] = {}
    for table in DUMP_TABLES:
        cur = con.execute(f"SELECT *, rowid FROM {table} ORDER BY rowid")
        rows = []
        for row in cur.fetchall():
            d = dict(row)
            d.pop("rowid", None)
            norm = {}
            for k in sorted(d.keys()):
                v = d[k]
                norm[k] = _normalize_text(v, mapping) if isinstance(v, str) else v
            rows.append(norm)
        dump[table] = rows
    con.close()
    return dump


def _apply_one(db, world_id: str, mutation_type: str, payload: dict, label: str) -> Optional[str]:
    """Insert a `proposed` mutation row and apply it through the exact
    production path (`approve_mutation`'s SAVEPOINT discipline in app.py),
    returning the error string (None on success). Mirrors `approve_mutation`
    rather than calling `_apply_mutation` bare, so the harness proves the
    same rollback semantics real approvals get."""
    from world_engine.cockpit.routes.mutations import _apply_mutation
    from world_engine.models import ProposedMutation

    mut = ProposedMutation(
        world_id=world_id,
        source_type="conversation",
        mutation_type=mutation_type,
        payload=payload,
        status="proposed",
        proposed_by="harness",
    )
    db.add(mut)
    db.flush()

    error: Optional[str] = None
    try:
        with db.begin_nested():
            error = _apply_mutation(mut, db)
            if error:
                raise RuntimeError(error)
        mut.status = "applied"
    except Exception as exc:
        error = error or str(exc)
        mut.status = "approved"
    db.add(mut)
    db.commit()
    print(f"  [{label}] -> {'OK' if error is None else 'error: ' + error}")
    return error


def _run(mode: str) -> bool:
    from sqlmodel import Session
    from world_engine.db import engine

    results: dict[str, Optional[str]] = {}
    dumps: dict[str, Any] = {}

    with Session(engine) as db:
        dumps["before"] = _dump_db(WORKDB_PATH)

        # agenda_creation must apply before the step/delegation proposals
        # can be built (their payloads need its real generated ids) — so
        # proposals are built and applied in two passes, exactly mirroring
        # the dependency a human creator's approval order would have.
        head = [
            ("relation_change", "relation_change", {
                "entity_a_id": NPC_MAELIS, "entity_b_id": NPC_REIKE,
                "relation_type": "trust", "intensity_delta": 10,
            }),
            ("new_knowledge", "new_knowledge", {
                "entity_id": NPC_SENNA, "subject": "harness_test_subject",
                "level": "rumor", "content": "Harness-authored test knowledge.",
                "source": "conversation", "is_secret": False,
            }),
            ("status_change", "status_change", {
                "entity_id": NPC_SENNA, "status": "active",
            }),
            ("item_update", "item_update", {
                "item_id": ITEM_DAGUE, "equipped": False,
            }),
            ("knowledge_change", "knowledge_change", {
                "entity_id": NPC_MAELIS, "subject": "local_magic_incidents",
                "to_level": "knows", "source": "conversation",
            }),
            ("goal_change create_short", "goal_change", {
                "npc_id": NPC_MAELIS, "action": "create_short",
                "goal": "Harness test goal for BRIEF-0027-c",
            }),
            ("goal_change complete", "goal_change", {
                "npc_id": NPC_MAELIS, "action": "complete",
                "goal": "Harness test goal for BRIEF-0027-c",
            }),
            ("npc_move", "npc_move", {
                "npc_id": NPC_MAELIS, "from_location_id": LOC_TAVERN,
                "to_location_id": LOC_OTHER,
            }),
            ("event_creation", "event_creation", {
                "title": "Harness Test Event", "description": "Harness-authored test event.",
                "type": "local_magic_incidents", "knowledge_status": "secret",
                "involved_entities": [NPC_MAELIS], "location_id": LOC_TAVERN,
            }),
            ("resource_change", "resource_change", {
                "entity_id": PLAYER, "amount": 50, "reason": "harness test income",
            }),
            ("agenda_creation", "agenda_creation", {
                "owner_entity_id": FAC_GUARD, "title": "Harness Test Agenda",
                "steps": ["Harness step one", "Harness step two"],
            }),
        ]
        for label, mutation_type, payload in head:
            results[label] = _apply_one(db, WORLD_ID, mutation_type, payload, label)
            dumps[f"after_{label}"] = _dump_db(WORKDB_PATH)

        from sqlmodel import select
        from world_engine.models import Agenda, AgendaStep
        agenda = db.exec(
            select(Agenda).where(Agenda.world_id == WORLD_ID, Agenda.title == "Harness Test Agenda")
        ).first()
        step1 = db.exec(
            select(AgendaStep).where(AgendaStep.agenda_id == agenda.id, AgendaStep.step_order == 1)
        ).first()

        tail = [
            ("agenda_step_change", "agenda_step_change", {
                "step_id": step1.id, "action": "complete",
            }),
            ("agenda_delegation", "agenda_delegation", {
                "npc_id": NPC_REIKE, "goal": "Harness delegation goal", "horizon": "short",
                "agenda_id": agenda.id,
            }),
            ("goal_change create_short FAILING", "goal_change", {
                "npc_id": NPC_SENNA, "action": "create_short",
                "goal": "Harness failing goal (should roll back)",
                "agenda_id": "nonexistent-agenda-id-xyz",
            }),
        ]
        for label, mutation_type, payload in tail:
            results[label] = _apply_one(db, WORLD_ID, mutation_type, payload, label)
            dumps[f"after_{label}"] = _dump_db(WORKDB_PATH)

    if mode == "record":
        FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
        RESULTS_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        DUMPS_PATH.write_text(json.dumps(dumps, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"RECORD: {len(results)} proposals applied, fixtures written to {FIXTURE_DIR}")
        return True

    recorded_results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    recorded_dumps = json.loads(DUMPS_PATH.read_text(encoding="utf-8"))

    ok = True
    for key in recorded_results:
        if results.get(key) != recorded_results[key]:
            ok = False
            print(f"FAIL: apply result diverged at {key!r}")
            print(f"  recorded: {recorded_results[key]!r}")
            print(f"  replayed: {results.get(key)!r}")

    for key in recorded_dumps:
        if dumps.get(key) != recorded_dumps[key]:
            ok = False
            print(f"FAIL: DB dump diverged at {key}")
            for table in DUMP_TABLES:
                if dumps.get(key, {}).get(table) != recorded_dumps[key].get(table):
                    print(f"  table={table}")
                    print(f"    recorded: {recorded_dumps[key].get(table)}")
                    print(f"    replayed: {dumps.get(key, {}).get(table)}")

    print("REPLAY: PASS — empty diff on apply results and DB writes" if ok else "REPLAY: FAIL — see diffs above")
    return ok


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("record", "replay"):
        raise SystemExit(__doc__)
    mode = sys.argv[1]
    _prepare_workdb(mode)
    # Point the engine at the disposable copy BEFORE any world_engine import,
    # so db.py binds to it instead of the live DB.
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{WORKDB_PATH}"

    ok = _run(mode)
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
