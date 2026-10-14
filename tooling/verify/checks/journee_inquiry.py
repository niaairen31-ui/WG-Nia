"""G1 check for TICKET-0121 -- Journée routes a declaration to a quest.

BRIEF-0121-D's rules (K1, K1b, R1, T1 of the Journée quest designer): the
selection's third answer, the openers of a request, the inquiry band.

JI1 -- `select_plan` calls the model on every declaration, an empty plan
   list included: `{"selected": null, "route": "quest"}` gives
   `PlanSelection(None, "quest")`; `{"selected": 1, "route": "quest"}` over
   one plan gives that plan with route `plan`; `{"selected": null}` raises
   `LlmParseError`.
JI2 -- `finalize_inquiry_day` writes one agenda of one step `Se renseigner :
   ...` with no domain and no condition, one `route` request on it, the
   pass_play `resolving` with its `agenda_id`; the response says `inquiry`
   and carries no id.
JI3 -- `_finalize_plan` on three steps whose second needs a knowledge no one
   holds: two steps are written, `inquiry_cut == 1`, one `dropped` request
   on step 2.
JI4 -- `_finalize_plan` on two steps whose second needs to have met an
   unmet NPC: two steps, one `blocked` request on step 2; opening it again
   adds nothing.
JI5 -- `resolve_steps` on JI3's plan: step 1 `success`, step 2 `inquiry`,
   nothing after; `emit_mutations` proposes nothing for step 2;
   `close_inquiry_steps` completes step 2 with outcome `inquiry` and the
   agenda.
JI6 -- `BAND_MARKERS` and `BAND_LABELS_FR` have the same five keys and
   `assemble_beats` writes `[RECHERCHE]` for an inquiry step.
JI7 -- static: `day_resolve.py` imports `inquiry_step_ids` and no writer;
   `routes/day.py` stays under the module budget's caps.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB; the model call is a stub. A rule
that collects nothing fails.
"""
from __future__ import annotations

import ast
import json
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> None:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))


# --- fixture ---------------------------------------------------------------------

def _build(db) -> dict:
    from world_engine.models import Batch, Character, Entity, PassPlay, PromptTemplate, World
    from world_engine.models import Session as GameSession
    from world_engine.writes import write_prompt_version
    from world_engine.writes.prompts import write_prompt_variables

    ids: dict = {}
    world = World(name="Monde")
    db.add(world)
    db.flush()
    session = GameSession(world_id=world.id, number=1)
    db.add(session)
    hero = Entity(world_id=world.id, type="character", name="Heros")
    npc = Entity(world_id=world.id, type="character", name="Inconnu")
    db.add_all([hero, npc])
    db.flush()
    db.add(Character(id=hero.id, world_id=world.id, character_type="player"))
    db.add(Character(id=npc.id, world_id=world.id, character_type="npc"))
    db.flush()
    batch = Batch(session_id=session.id, day_number=1)
    db.add(batch)
    db.flush()
    template = PromptTemplate(id="pt-day-plan-select", name="select", usage="day_plan_select")
    db.add(template)
    db.flush()
    write_prompt_variables(db, template_id=template.id, variables=["plans", "declaration"])
    write_prompt_version(
        db, template_id=template.id, system_prompt="sys", user_template="{plans}\n{declaration}", note="fixture",
    )
    db.commit()
    ids.update(world=world.id, session=session.id, hero=hero.id, npc=npc.id, batch=batch.id)
    return ids


def _day(db, ids, text: str):
    from world_engine.models import PassPlay

    play = PassPlay(
        batch_id=ids["batch"], session_id=ids["session"], character_id=ids["hero"],
        declared_action=text, status="submitted",
    )
    db.add(play)
    db.commit()
    return play


def _character(db, ids):
    from world_engine.models import Character

    return db.get(Character, ids["hero"])


def _steps(db, agenda_id):
    from sqlmodel import select

    from world_engine.models import AgendaStep

    return db.exec(select(AgendaStep).where(AgendaStep.agenda_id == agenda_id).order_by(AgendaStep.step_order)).all()


def _requests(db):
    from sqlmodel import select

    from world_engine.models import QuestRequest

    return db.exec(select(QuestRequest)).all()


def _no_ids(value, forbidden: set[str]) -> bool:
    text = json.dumps(value, default=str)
    return not any(i in text for i in forbidden)


# --- JI1 -------------------------------------------------------------------------

def check_ji1(db, ids) -> None:
    from world_engine import day_plan_select, ollama_client
    from world_engine.llm_parse import LlmParseError
    from world_engine.models import Agenda

    calls: list[int] = []
    answers: list[str] = []
    real = ollama_client.chat

    def stub(*args, **kwargs):
        calls.append(1)
        return answers.pop(0)

    ollama_client.chat = stub
    try:
        answers.append('{"selected": null, "route": "quest", "rationale": "x"}')
        got = day_plan_select.select_plan("je cherche le secret", [], db)
        if len(calls) != 1:
            fail(f"JI1: an empty plan list made {len(calls)} model calls, expected 1")
        if not isinstance(got, day_plan_select.PlanSelection) or got.agenda is not None or got.route != "quest":
            fail(f"JI1: empty list + quest answered {got!r}")

        agenda = Agenda(world_id=ids["world"], owner_entity_id=ids["hero"], title="Plan", status="paused")
        db.add(agenda)
        db.flush()
        answers.append('{"selected": 1, "route": "quest", "rationale": "x"}')
        got = day_plan_select.select_plan("je continue", [agenda], db)
        if got.agenda is not agenda or got.route != "plan":
            fail(f"JI1: a selected plan must carry route 'plan', got {got!r}")

        answers.append('{"selected": null, "rationale": "x"}')
        try:
            day_plan_select.select_plan("je cherche", [agenda], db)
            fail("JI1: a null selection without a route did not raise")
        except LlmParseError:
            pass
        answers.append('{"selected": null, "route": "autre", "rationale": "x"}')
        try:
            day_plan_select.select_plan("je cherche", [agenda], db)
            fail("JI1: an unknown route did not raise")
        except LlmParseError:
            pass
        db.rollback()
    finally:
        ollama_client.chat = real


# --- JI2 -------------------------------------------------------------------------

def check_ji2(db, ids) -> None:
    from world_engine.cockpit.day_plan_finalize import finalize_inquiry_day
    from world_engine.models import Agenda

    play = _day(db, ids, "Je cherche le secret de l'acier noir.")
    before = len(_requests(db))
    result = finalize_inquiry_day(ids["world"], _character(db, ids), play, play.declared_action, db)
    agenda = db.get(Agenda, play.agenda_id)
    steps = _steps(db, play.agenda_id) if agenda is not None else []
    if len(steps) != 1:
        fail(f"JI2: expected one step, found {len(steps)}")
        return
    step = steps[0]
    if not step.objective.startswith("Se renseigner : ") or step.domain is not None:
        fail(f"JI2: step is {step.objective!r} / domain {step.domain!r}")
    from sqlmodel import select

    from world_engine.models import Condition

    if db.exec(select(Condition).where(Condition.agenda_step_id == step.id)).first() is not None:
        fail("JI2: the inquiry step carries a condition")
    new = [r for r in _requests(db)]
    if len(new) != before + 1 or new[-1].trigger != "route" or new[-1].agenda_step_id != step.id:
        fail("JI2: expected exactly one `route` request on the step")
    if play.status != "resolving":
        fail(f"JI2: pass_play.status is {play.status!r}")
    if result.get("inquiry") is not True:
        fail("JI2: the response does not say inquiry")
    if not _no_ids(result, {agenda.id, step.id, play.id}):
        fail("JI2: the response carries an id")


# --- JI3 / JI4 -------------------------------------------------------------------

def _plan(db, ids, steps):
    from world_engine import day_plans
    from world_engine.cockpit.day_plan_finalize import _finalize_plan

    play = _day(db, ids, "Je fais plusieurs choses.")
    day_plans.park_active_plan(_character(db, ids), db)  # as plan_day does: one active plan per character
    result = _finalize_plan(ids["world"], _character(db, ids), play, steps, db)
    return play, result


def _step(objective, *, requirements=()):
    from world_engine.conditions import all_of
    from world_engine.day_plan import PlanStep

    return PlanStep(objective=objective, cost=1, domain=None, prerequisite=all_of(list(requirements)) if requirements else None)


def check_ji3(db, ids) -> dict:
    from world_engine.condition_forms import RequirementSpec

    ghost = RequirementSpec(type="knowledge", target_key="fait-que-personne-ne-tient")
    play, result = _plan(db, ids, [_step("Aller au marché"), _step("Apprendre le secret", requirements=[ghost]), _step("Forger la lame")])
    steps = _steps(db, play.agenda_id)
    if len(steps) != 2:
        fail(f"JI3: expected 2 steps written, found {len(steps)}")
        return {}
    if result.get("inquiry_cut") != 1:
        fail(f"JI3: inquiry_cut is {result.get('inquiry_cut')!r}, expected 1")
    mine = [r for r in _requests(db) if r.agenda_step_id in {s.id for s in steps}]
    if len(mine) != 1 or mine[0].trigger != "dropped" or mine[0].agenda_step_id != steps[1].id:
        fail(f"JI3: expected one `dropped` request on step 2, got {[(r.trigger, r.agenda_step_id) for r in mine]}")
    return {"play": play, "steps": steps}


def check_ji4(db, ids) -> None:
    from world_engine.condition_forms import RequirementSpec
    from world_engine.writes.quest_requests import open_request

    met = RequirementSpec(type="has_met", target_entity_id=ids["npc"])
    play, result = _plan(db, ids, [_step("Se reposer"), _step("Parler à l'inconnu", requirements=[met])])
    steps = _steps(db, play.agenda_id)
    mine = [r for r in _requests(db) if r.agenda_step_id in {s.id for s in steps}]
    if len(steps) != 2 or len(mine) != 1 or mine[0].trigger != "blocked" or mine[0].agenda_step_id != steps[1].id:
        fail(f"JI4: expected 2 steps and one `blocked` request on step 2, got {len(steps)} / {[(r.trigger) for r in mine]}")
        return
    open_request(
        db, world_id=ids["world"], character_id=ids["hero"], pass_play_id=play.id,
        trigger="blocked", declaration=steps[1].objective, agenda_step_id=steps[1].id,
    )
    again = [r for r in _requests(db) if r.agenda_step_id in {s.id for s in steps}]
    if len(again) != 1:
        fail("JI4: a second opening added a request")


# --- JI5 / JI6 -------------------------------------------------------------------

def check_ji5(db, ids, ji3: dict) -> None:
    from world_engine.cockpit.day_plan_finalize import close_inquiry_steps
    from world_engine.day_mutations import emit_mutations
    from world_engine.day_resolve import INQUIRY_BAND, resolve_steps
    from world_engine.models import Agenda

    if not ji3:
        fail("JI5: JI3 produced no plan to resolve")
        return
    play, steps = ji3["play"], ji3["steps"]
    agenda = db.get(Agenda, play.agenda_id)
    character = _character(db, ids)
    outcomes = resolve_steps(agenda, character, db)
    bands = [o.band for o in outcomes]
    if bands != ["success", INQUIRY_BAND]:
        fail(f"JI5: bands are {bands!r}, expected ['success', 'inquiry']")
        return
    inquiry = [o for o in outcomes if o.band == INQUIRY_BAND]
    if inquiry[0].verdict is not None:
        fail("JI5: the inquiry outcome was rolled")
    if emit_mutations(inquiry, play, character, db):
        fail("JI5: emit_mutations proposed something for an inquiry step")
    close_inquiry_steps(outcomes, agenda, db)
    db.flush()
    step2 = db.get(type(steps[1]), steps[1].id)
    if step2.status != "completed" or step2.outcome != "inquiry":
        fail(f"JI5: step 2 is {step2.status!r}/{step2.outcome!r}")
    step1 = db.get(type(steps[0]), steps[0].id)
    if step1.status == "completed":
        fail("JI5: step 1 was closed by the inquiry closer")
    if agenda.status == "completed":
        fail("JI5: the agenda completed with a step still open")
    # the lone-step case: nothing pending/active left -> the agenda completes
    from world_engine.cockpit.day_plan_finalize import finalize_inquiry_day

    from world_engine import day_plans

    play2 = _day(db, ids, "Je cherche une autre chose.")
    day_plans.park_active_plan(character, db)
    finalize_inquiry_day(ids["world"], character, play2, play2.declared_action, db)
    agenda2 = db.get(Agenda, play2.agenda_id)
    out2 = resolve_steps(agenda2, character, db)
    close_inquiry_steps(out2, agenda2, db)
    if agenda2.status != "completed":
        fail(f"JI5: a lone inquiry step left its agenda {agenda2.status!r}")
    if resolve_steps(agenda2, character, db):
        fail("JI5: a closed inquiry step was walked again")


def check_ji6() -> None:
    from world_engine.day_narration import BAND_LABELS_FR, BAND_MARKERS, assemble_beats
    from world_engine.day_resolve import INQUIRY_BAND, FactSheet, StepFact

    if set(BAND_MARKERS) != set(BAND_LABELS_FR) or len(BAND_MARKERS) != 5:
        fail(f"JI6: marker keys {sorted(BAND_MARKERS)} / label keys {sorted(BAND_LABELS_FR)}")
    if BAND_MARKERS.get(INQUIRY_BAND) != "[RECHERCHE]":
        fail("JI6: the inquiry band has no [RECHERCHE] marker")
        return
    sheet = FactSheet(
        world_id="w", day_number=1, character_name="Heros",
        steps=(StepFact(objective="Se renseigner : x", band=INQUIRY_BAND, dice=None, modifier=None, total=None),),
        npcs=(), locations=(), role_hints=(),
    )
    prose = assemble_beats(json.dumps({"etapes": ["Il fouille les archives."]}), sheet)
    if not prose.startswith("[RECHERCHE]"):
        fail(f"JI6: assemble_beats wrote {prose!r}")


# --- JI7 -------------------------------------------------------------------------

def check_ji7() -> None:
    tree = ast.parse((SRC / "day_resolve.py").read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.update(a.name for a in node.names)
    if "inquiry_step_ids" not in imported:
        fail("JI7: day_resolve.py does not import inquiry_step_ids")
    writers = sorted(n for n in imported if n.startswith("write_"))
    if writers:
        fail(f"JI7: day_resolve.py imports writer(s) {writers}")
    route = SRC / "cockpit" / "routes" / "day.py"
    text = route.read_text(encoding="utf-8")
    lines = len(text.splitlines())
    functions = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(ast.parse(text)))
    if lines > 1000 or functions > 40:
        fail(f"JI7: routes/day.py has {lines} lines / {functions} functions (caps 1000 / 40)")


def main() -> None:
    _fresh_db()
    from sqlmodel import Session, SQLModel

    from world_engine import models  # noqa: F401 -- registers every table
    from world_engine.db import engine

    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        ids = _build(db)
        check_ji1(db, ids)
        check_ji2(db, ids)
        ji3 = check_ji3(db, ids)
        check_ji5(db, ids, ji3)
        check_ji4(db, ids)
    check_ji6()
    check_ji7()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: journee_inquiry -- the selection routes, a blocked or unanchored step opens a request, "
          "and an inquiry day is narrated without dice and closed without a proposal")


if __name__ == "__main__":
    main()
