"""G1 check for TICKET-0051, BRIEF-0051-e — the observation runner.

Builds a fresh temp-file SQLite DB (WORLD_ENGINE_DATABASE_URL set before any
world_engine import) so this check never touches Nia's real DB. The local
model is stubbed for determinism, dispatched by a marker string planted in
each stub PromptTemplate's system_prompt (local model sampling is not
deterministic, and this module makes several distinct templated calls per
beat that must be told apart).

Rules:
  1. (AST) Every observation_* write in observation_runner.py goes through
     observation_writes.py — no direct db.add(Observation...(...)).
  2. (AST) _beat_outcome's three branches are explicit returns, never a
     truthiness ternary.
  3. (behavioural) All intent calls forced to fail -> outcome='degraded',
     never 'silence', with a full set of observation_intent rows.
  4. (behavioural) A readiness-gate failure writes zero observation_run rows.
  5. (behavioural) A completed run writes zero conversation and zero
     conversation_message rows.
  6. (behavioural) A run's proposals are absent from list_mutations and
     reachable via observation_mutation_link.
  7. (behavioural) run_bounded never leaves a run 'running', including when
     an unhandled exception propagates.
  8. Vacuous-proof guard: zero beats or zero intent rows executed is FAIL.
"""
from __future__ import annotations

import ast
import json
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

RUNNER = SRC / "world_engine" / "observation_runner.py"

FAILURES: list[str] = []
_beats_executed = 0
_intents_written = 0


def fail(msg: str) -> None:
    FAILURES.append(msg)


# ── AST rules ────────────────────────────────────────────────────────────

_OBSERVATION_CLASSES = {
    "ObservationRun", "ObservationRunTemplate", "ObservationBeat",
    "ObservationIntent", "ObservationMutationLink",
}


def check_rule1_writes_through_chokepoint() -> None:
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add"):
            continue
        for arg in node.args:
            if not isinstance(arg, ast.Call):
                continue
            callee = arg.func
            name = callee.id if isinstance(callee, ast.Name) else getattr(callee, "attr", None)
            if name in _OBSERVATION_CLASSES:
                fail(f"Rule 1: direct db.add({name}(...)) at line {node.lineno} — must go through observation_writes.py")


def check_rule2_outcome_explicit() -> None:
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    func = next(
        (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_beat_outcome"), None,
    )
    if func is None:
        fail("Rule 2: _beat_outcome function not found")
        return
    returned = {
        n.value.value for n in ast.walk(func)
        if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
    }
    missing = {"acted", "silence", "degraded"} - returned
    if missing:
        fail(f"Rule 2: _beat_outcome missing explicit branch(es) for {sorted(missing)}, got {sorted(returned)}")
    for n in ast.walk(func):
        if isinstance(n, ast.IfExp):
            fail(f"Rule 2: _beat_outcome uses a ternary (truthiness shorthand) at line {n.lineno}")


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


def _seed_fixture(engine, *, npc_count: int = 3):
    from sqlmodel import Session as DbSession
    from world_engine import writes as _writes
    from world_engine.models import Character, Entity, Location, NpcGoal, PromptTemplate, World

    with DbSession(engine) as session:
        world = World(name="Runner Check World", is_active=True)
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
            entity = Entity(world_id=world.id, type="character", name=f"NPC{i}", description=f"PNJ numéro {i}.")
            session.add(entity)
            session.commit()
            session.refresh(entity)
            session.add(Character(
                id=entity.id, world_id=world.id, character_type="npc",
                current_location_id=loc_entity.id, vital_status="alive",
            ))
            session.add(NpcGoal(
                world_id=world.id, npc_id=entity.id, description="Un but.",
                horizon="short", status="active",
            ))
            session.commit()
            npc_ids.append(entity.id)

        def _seed_template(usage: str, marker: str) -> str:
            head = PromptTemplate(world_id=None, name=f"check-{usage}", usage=usage, is_active=True)
            session.add(head)
            session.commit()
            session.refresh(head)
            _writes.write_prompt_version(
                session, template_id=head.id,
                system_prompt=f"{marker} pas de placeholder ici.",
                user_template="pas de placeholder ici non plus",
            )
            return head.id

        _seed_template("observation_intent", "STUB_INTENT_MARKER")
        _seed_template("npc_initiative_act", "STUB_ACT_MARKER")
        _seed_template("npc_dialogue", "STUB_DIALOGUE_MARKER")
        _seed_template("conversation_analysis", "STUB_WINDOW_MARKER")
        _seed_template("overhearing_classification", "STUB_OVERHEAR_MARKER")

        return {"world_id": world.id, "location_id": loc_entity.id, "npc_ids": npc_ids}


def _stub_chat(*, fail_intents: bool = False, act_first: bool = True, window_items=None):
    """Dispatches on a marker string in the system prompt (messages[0]) —
    see module docstring. `act_first`: the first intent call in each beat
    answers act=true (urgency 80); every other candidate declines."""
    from world_engine import ollama_client as oc

    state = {"intent_calls": 0}

    def _chat(messages, model=None, host=None, timeout=300.0, format=None, options=None):
        system = messages[0]["content"]
        if "STUB_INTENT_MARKER" in system:
            if fail_intents:
                raise oc.OllamaError("stub forced failure")
            idx = state["intent_calls"]
            state["intent_calls"] += 1
            if act_first and idx % 3 == 0:
                return json.dumps({"act": True, "urgency": 80, "target": "", "why": "raison de test"})
            return json.dumps({"act": False})
        if "STUB_ACT_MARKER" in system:
            return json.dumps({"act_text": "Une réplique de test.", "move": False})
        if "STUB_WINDOW_MARKER" in system:
            return json.dumps(window_items if window_items is not None else [])
        if "STUB_OVERHEAR_MARKER" in system:
            return "[]"
        return "{}"

    return _chat


# ── Rule 3 ──────────────────────────────────────────────────────────────

def check_rule3_degraded_not_silence(fixture, engine) -> None:
    global _beats_executed, _intents_written
    from sqlmodel import Session as DbSession
    from world_engine import ollama_client as oc
    from world_engine import observation_runner as runner
    from world_engine.models import ObservationIntent

    original_chat = oc.chat
    oc.chat = _stub_chat(fail_intents=True)
    try:
        with DbSession(engine) as session:
            run, failures = runner.start_run(
                fixture["world_id"], fixture["location_id"], session,
                max_beats=5, quiescence_limit=5,
            )
        if run is None:
            fail(f"Rule 3: start_run refused a healthy fixture: {failures}")
            return
        from sqlmodel import select as _select
        with DbSession(engine) as session:
            beat = runner.run_one_beat(run.id, session)
            beat_id, beat_outcome = beat.id, beat.outcome
            intents = list(session.exec(_select(ObservationIntent).where(ObservationIntent.beat_id == beat.id)))
            intent_statuses = [i.call_status for i in intents]
        _beats_executed += 1
    finally:
        oc.chat = original_chat

    if beat_outcome != "degraded":
        fail(f"Rule 3: expected outcome='degraded' when every intent call fails, got {beat_outcome!r}")

    _intents_written += len(intents)
    if len(intents) != len(fixture["npc_ids"]):
        fail(f"Rule 3: expected {len(fixture['npc_ids'])} observation_intent rows, got {len(intents)}")
    if any(status == "ok" for status in intent_statuses):
        fail("Rule 3: a forced-failure fixture produced a call_status='ok' intent row")


# ── Rule 4 ──────────────────────────────────────────────────────────────

def check_rule4_readiness_gate_zero_rows(engine) -> None:
    from sqlmodel import Session as DbSession, select
    from world_engine import observation_runner as runner
    from world_engine.models import Character, Entity, NpcGoal, ObservationRun, World

    with DbSession(engine) as session:
        world = World(name="Gate Check World", is_active=False)
        session.add(world)
        session.commit()
        session.refresh(world)

        loc = Entity(world_id=world.id, type="location", name="Solo", description="Une pièce vide.")
        session.add(loc)
        session.commit()
        session.refresh(loc)
        from world_engine.models import Location
        session.add(Location(id=loc.id))
        session.commit()

        npc_entity = Entity(world_id=world.id, type="character", name="Solitaire", description="Seul·e.")
        session.add(npc_entity)
        session.commit()
        session.refresh(npc_entity)
        session.add(Character(
            id=npc_entity.id, world_id=world.id, character_type="npc",
            current_location_id=loc.id, vital_status="alive",
        ))
        session.add(NpcGoal(
            world_id=world.id, npc_id=npc_entity.id, description="But solitaire.",
            horizon="short", status="active",
        ))
        session.commit()

        before = session.exec(select(ObservationRun)).all()
        run, failures = runner.start_run(world.id, loc.id, session)
        after = session.exec(select(ObservationRun)).all()

    if run is not None:
        fail("Rule 4: start_run against a 1-NPC location did not refuse")
    if not failures:
        fail("Rule 4: a refused run reported zero failure reasons")
    if len(after) != len(before):
        fail(f"Rule 4: a readiness-gate failure wrote {len(after) - len(before)} observation_run row(s)")


# ── Rule 5 / 6 / 7 (a completed run, exercised end to end) ──────────────

def check_rules_5_6_7(fixture, engine) -> None:
    global _beats_executed, _intents_written
    from sqlmodel import Session as DbSession, select
    from world_engine import ollama_client as oc
    from world_engine import observation_runner as runner
    from world_engine.models import Conversation, ConversationMessage, ObservationMutationLink

    npc_ids = fixture["npc_ids"]
    window_items = [{
        "mutation_type": "new_knowledge",
        "payload": {
            "entity_id": npc_ids[1], "subject": "observed_test_subject",
            "level": "rumor", "content": "un fait observé", "source": "conversation",
        },
    }]

    original_chat = oc.chat
    oc.chat = _stub_chat(act_first=True, window_items=window_items)
    try:
        with DbSession(engine) as session:
            run, failures = runner.start_run(
                fixture["world_id"], fixture["location_id"], session,
                max_beats=1, quiescence_limit=1,
            )
        if run is None:
            fail(f"Rule 5/6: start_run refused a healthy fixture: {failures}")
            return
        with DbSession(engine) as session:
            closed = runner.run_bounded(run.id, session)
            closed_id, closed_status = closed.id, closed.status
        _beats_executed += 1
    finally:
        oc.chat = original_chat

    if closed_status != "completed":
        fail(f"Rule 5/6: expected a max_beats=1 run to complete, got status={closed_status!r}")

    with DbSession(engine) as session:
        conv_count = len(session.exec(select(Conversation)).all())
        msg_count = len(session.exec(select(ConversationMessage)).all())
    if conv_count != 0:
        fail(f"Rule 5: observed run left {conv_count} conversation row(s)")
    if msg_count != 0:
        fail(f"Rule 5: observed run left {msg_count} conversation_message row(s)")

    with DbSession(engine) as session:
        links = session.exec(
            select(ObservationMutationLink).where(ObservationMutationLink.run_id == closed_id)
        ).all()
    if not links:
        fail("Rule 6: a run with a well-formed window proposal wrote zero observation_mutation_link rows")
    else:
        from world_engine.cockpit.routes.mutations import list_mutations
        with DbSession(engine) as session:
            visible = list_mutations(status="proposed", db=session)
        linked_ids = {link.mutation_id for link in links}
        leaked = linked_ids & {m["id"] for m in visible}
        if leaked:
            fail(f"Rule 6: observed-run mutation(s) {leaked} leaked into list_mutations")


def check_rule7_never_left_running(fixture, engine) -> None:
    from sqlmodel import Session as DbSession
    from world_engine import ollama_client as oc
    from world_engine import observation_runner as runner

    original_chat = oc.chat
    original_arbitrate = runner.arbitrate
    oc.chat = _stub_chat(act_first=True)

    def _boom(*a, **kw):
        raise RuntimeError("Rule 7 injected failure")

    runner.arbitrate = _boom
    try:
        with DbSession(engine) as session:
            run, failures = runner.start_run(
                fixture["world_id"], fixture["location_id"], session,
                max_beats=5, quiescence_limit=5,
            )
        if run is None:
            fail(f"Rule 7: start_run refused a healthy fixture: {failures}")
            return
        raised = False
        try:
            with DbSession(engine) as session:
                runner.run_bounded(run.id, session)
        except RuntimeError:
            raised = True
        if not raised:
            fail("Rule 7: run_bounded swallowed an unhandled exception instead of propagating it")
    finally:
        oc.chat = original_chat
        runner.arbitrate = original_arbitrate

    from world_engine.models import ObservationRun
    with DbSession(engine) as session:
        closed = session.get(ObservationRun, run.id)
    if closed.status == "running":
        fail("Rule 7: run left status='running' after run_bounded raised")
    if closed.status != "failed" or closed.stop_reason != "error":
        fail(f"Rule 7: expected status='failed'/stop_reason='error', got {closed.status!r}/{closed.stop_reason!r}")


def main() -> int:
    check_rule1_writes_through_chokepoint()
    check_rule2_outcome_explicit()

    engine = _fresh_engine()
    fixture = _seed_fixture(engine)
    check_rule3_degraded_not_silence(fixture, engine)
    check_rule4_readiness_gate_zero_rows(engine)
    check_rules_5_6_7(fixture, engine)
    check_rule7_never_left_running(fixture, engine)

    if _beats_executed == 0 or _intents_written == 0:
        fail(f"Vacuous-proof guard: {_beats_executed} beat(s) / {_intents_written} intent row(s) executed")

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        f"PASS: observation_runner — {_beats_executed} beat(s) executed, "
        f"{_intents_written} intent row(s) written across the fixtures"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
