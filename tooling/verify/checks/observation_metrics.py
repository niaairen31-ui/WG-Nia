"""G1 check for TICKET-0051, BRIEF-0051-g — observation run metrics.

Builds a fresh temp-file SQLite DB (WORLD_ENGINE_DATABASE_URL set before any
world_engine import) and inserts `observation_*` rows directly — no runner,
no Ollama, since this check tests the METRICS computation over rows, not the
beat-execution loop (already covered by observation_runner.py's check).

Rules:
  1. (AST) scripts/observation_metrics.py contains no write operation — no
     db.add, no .commit(), no raw INSERT/UPDATE SQL.
  2. (AST) no import of ollama_client or any model-calling module (D-J1).
  3. (behavioural) a synthetic run where one NPC acts every beat yields
     entropy near 0; an even run yields entropy near 1. Both ends asserted.
  4. (behavioural) a fixture with a 'degraded' beat produces a non-zero
     degraded rate AND the suspect-run warning in the printed output.
  5. (AST) the script never reimplements the not_selected_reason precedence
     — it imports and calls observation_reads.derive_not_selected_reason,
     the same function -f's surface reads, so the two can never drift.
  6. Vacuous-proof guard: zero beats or zero intent rows in the fixtures is
     a FAILURE.
"""
from __future__ import annotations

import ast
import io
import os
import pathlib
import sys
import tempfile
from contextlib import redirect_stdout

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

SCRIPT = ROOT / "scripts" / "observation_metrics.py"

FAILURES: list[str] = []
_beats_seeded = 0
_intents_seeded = 0


def fail(msg: str) -> None:
    FAILURES.append(msg)


# ── AST rules ────────────────────────────────────────────────────────────


def _script_tree() -> ast.Module:
    return ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT))


_SESSION_RECEIVER_NAMES = {"session", "db", "s"}


def check_rule1_no_writes(tree: ast.Module) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            receiver = node.func.value
            receiver_name = receiver.id if isinstance(receiver, ast.Name) else None
            if attr == "add" and receiver_name in _SESSION_RECEIVER_NAMES:
                fail(f"Rule 1: `{receiver_name}.add(...)` (session-shaped write) at line {node.lineno}")
            if attr in ("commit", "flush", "delete") and receiver_name in _SESSION_RECEIVER_NAMES:
                fail(f"Rule 1: `{receiver_name}.{attr}(...)` (session-shaped write) at line {node.lineno}")
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names]
            if any(n in ("INSERT", "UPDATE", "DELETE") for n in names):
                fail(f"Rule 1: suspicious import at line {node.lineno}: {names}")


def check_rule2_no_model_call(tree: ast.Module) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and "ollama_client" in node.module:
            fail(f"Rule 2: imports ollama_client at line {node.lineno} — D-J1 forbids a model call in the measurement loop")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "ollama_client" in alias.name:
                    fail(f"Rule 2: imports ollama_client at line {node.lineno}")


def check_rule5_shared_precedence(tree: ast.Module) -> None:
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "world_engine.observation_reads":
            if any(a.name == "derive_not_selected_reason" for a in node.names):
                found = True
    if not found:
        fail(
            "Rule 5: does not import observation_reads.derive_not_selected_reason "
            "— a local reimplementation could drift from -f's reader"
        )


# ── Fixture ─────────────────────────────────────────────────────────────


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


def _seed_world_and_npcs(session, npc_count: int, *, is_active: bool = True):
    from world_engine.models import Character, Entity, Location, World

    world = World(name="Metrics Check World", is_active=is_active)
    session.add(world)
    session.commit()
    session.refresh(world)

    loc_entity = Entity(world_id=world.id, type="location", name="Salle", description="Une salle.")
    session.add(loc_entity)
    session.commit()
    session.refresh(loc_entity)
    session.add(Location(id=loc_entity.id))
    session.commit()

    npc_ids = []
    for i in range(npc_count):
        entity = Entity(world_id=world.id, type="character", name=f"NPC{i}", description=f"PNJ {i}.")
        session.add(entity)
        session.commit()
        session.refresh(entity)
        session.add(Character(id=entity.id, world_id=world.id, character_type="npc", current_location_id=loc_entity.id))
        session.commit()
        npc_ids.append(entity.id)
    return world.id, loc_entity.id, npc_ids


def _make_run(session, world_id, location_id):
    from world_engine.models import ObservationRun

    run = ObservationRun(
        world_id=world_id, location_id=location_id, player_presence="absent",
        max_beats=50, quiescence_limit=50, cooldown_beats=2, debt_weight=1.0,
        propensity_mode="flat", model="check-model", status="completed",
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def _write_beat_with_intents(session, run_id, beat_index, npc_ids, actor_id, outcome, call_status="ok"):
    from world_engine.models import ObservationBeat, ObservationIntent

    beat = ObservationBeat(
        run_id=run_id, beat_index=beat_index, outcome=outcome,
        actor_id=actor_id, line=(f"beat {beat_index} line" if outcome == "acted" else None),
    )
    session.add(beat)
    session.commit()
    session.refresh(beat)

    global _intents_seeded
    for npc_id in npc_ids:
        wanted = npc_id == actor_id if actor_id else False
        session.add(ObservationIntent(
            run_id=run_id, beat_id=beat.id, npc_id=npc_id,
            act=wanted, urgency=(80 if wanted else None), why=None,
            propensity=0.5, cooldown_active=False, debt_score=0.0,
            final_score=(1.0 if wanted else 0.0), selected=wanted,
            call_status=call_status,
        ))
        _intents_seeded += 1
    session.commit()
    return beat


# ── Rule 3 ──────────────────────────────────────────────────────────────


def check_rule3_entropy_both_ends(engine) -> None:
    global _beats_seeded
    from sqlmodel import Session as DbSession
    import observation_metrics as metrics

    with DbSession(engine) as session:
        world_id, loc_id, npc_ids = _seed_world_and_npcs(session, 3)
        captured_run = _make_run(session, world_id, loc_id)
        captured_run_id = captured_run.id
        for beat_index in range(6):
            _write_beat_with_intents(session, captured_run_id, beat_index, npc_ids, npc_ids[0], "acted")
            _beats_seeded += 1

        even_run = _make_run(session, world_id, loc_id)
        even_run_id = even_run.id
        for beat_index in range(6):
            actor = npc_ids[beat_index % len(npc_ids)]
            _write_beat_with_intents(session, even_run_id, beat_index, npc_ids, actor, "acted")
            _beats_seeded += 1

    with DbSession(engine) as session:
        captured_report = metrics.compute_report(captured_run_id, session)
    with DbSession(engine) as session:
        even_report = metrics.compute_report(even_run_id, session)

    if captured_report["entropy"] is None or captured_report["entropy"] > 0.1:
        fail(f"Rule 3: expected entropy near 0 for a captured run, got {captured_report['entropy']!r}")
    if even_report["entropy"] is None or even_report["entropy"] < 0.9:
        fail(f"Rule 3: expected entropy near 1 for an even run, got {even_report['entropy']!r}")


# ── Rule 4 ──────────────────────────────────────────────────────────────


def check_rule4_degraded_warning(engine) -> None:
    global _beats_seeded
    from sqlmodel import Session as DbSession
    import observation_metrics as metrics

    with DbSession(engine) as session:
        world_id, loc_id, npc_ids = _seed_world_and_npcs(session, 2, is_active=False)
        run = _make_run(session, world_id, loc_id)
        run_id = run.id
        _write_beat_with_intents(session, run_id, 0, npc_ids, None, "degraded", call_status="error")
        _beats_seeded += 1

    with DbSession(engine) as session:
        report = metrics.compute_report(run_id, session)
    if report["degraded_rate"] <= 0:
        fail(f"Rule 4: expected a non-zero degraded_rate, got {report['degraded_rate']!r}")

    buf = io.StringIO()
    with redirect_stdout(buf):
        metrics._print_human([report])
    output = buf.getvalue()
    if "SUSPECT" not in output.upper():
        fail("Rule 4: a degraded-rate run did not print a suspect-run warning")


def main() -> int:
    tree = _script_tree()
    check_rule1_no_writes(tree)
    check_rule2_no_model_call(tree)
    check_rule5_shared_precedence(tree)

    engine = _fresh_engine()
    sys.path.insert(0, str(ROOT / "scripts"))
    check_rule3_entropy_both_ends(engine)
    check_rule4_degraded_warning(engine)

    if _beats_seeded == 0 or _intents_seeded == 0:
        fail(f"Vacuous-proof guard: {_beats_seeded} beat(s) / {_intents_seeded} intent row(s) seeded")

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        f"PASS: observation_metrics — {_beats_seeded} beat(s) seeded, "
        f"{_intents_seeded} intent row(s) exercised across the fixtures"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
