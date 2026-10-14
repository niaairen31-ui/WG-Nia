"""G1 check for TICKET-0114 -- a condition counts the events its subject lived, and a quest step says when it has failed.

BRIEF-0114-E's rules.

EE1 -- vocabulary and mirrors (static and import). `event` is in
   `REQUIREMENT_TYPES`, `KEY_TARGET_TYPES`, `THRESHOLD_TYPES` and
   `ANY_SUBJECT_TYPES`, never in `MODEL_REQUIREMENT_TYPES`;
   `conditions.EVENT_FORM` equals `event_vocab.EVENT_FORM`; the
   interpreter's `TARGET_HINTS_FR` and `condition_text.FORM_PHRASES_FR`
   have an `event` line; `SINCE_LABELS_FR` and the editor's
   `EVENT_WINDOWS` (`frontend/src/creation/questRequirements.js`) each hold
   exactly `models.CONDITION_WINDOWS`; `CONDITION_ROLES` holds `failure`.
EE2 -- the writer (fixture). `clean_leaf` keeps an `event` leaf with its
   type, its role, 1 when no count is said and `always` when no window is,
   and refuses: an unknown type, a role of another type, a role that does
   not take the fixed subject's type, a place that is no location, a
   filter's role named twice, a sorte on a role that takes none, an
   unknown window. `write_condition` then `read_condition` give back its
   window and its filters; an eligibility with a `quest` window is refused.
EE3 -- counting (fixture). Mira hunted three wolves in the Clairière (under
   the Forêt), two in the Ville, four bears in the Forêt; Brakk seven
   wolves, secretly; Mira fought one duel. « Chasse, chasseur, proie =
   loup » counts 5 for Mira (5 met, 6 not), 3 at the Forêt (its Clairière
   counts), 9 with any role and no filter, 7 for Brakk; a `Duel` with no
   quantity counts 1. Since the quest (accepted between the first two
   hunts) it counts 6; since the step (started after the second) 4; a
   step never started counts from the quest; with no quest, a `quest`
   window is `unknown`.
EE4 -- what a player sees (fixture). The leaf « Brakk a chassé un loup »
   is met for the canon and unmet for Mira, who never learned it, counting
   0; Mira's own hunts recount to 5 from the facts she knows
   (`known_event_facts`); with no known facts the leaf is `unknown`.
EE5 -- failure and step start (fixture and static). An offer step's
   `failure` condition is written, copied on acceptance to the agenda step,
   whose `started_at` is set; activating a pending step sets its own;
   `quest_reads.player_quests` shows the failure lines and `failure_met`.
   Only `quest_reads.py` and `writes/quests.py` read or write a `failure`
   condition -- nothing acts on it.
EE6 -- the editor (static). `REQUIREMENT_FORMS.event` lists `eventTypes`;
   `QuestRequirementRow.svelte` edits the role, the place, the window and
   the filters; `OfferEditor.svelte` (TICKET-0121) has a `failure` editor;
   `questOffers.svelte.js` sends `failure` and `failure_draft_id`;
   Journée's `QuestPanel.svelte` shows `failure_met`; the editor's choices
   carry `event_types` and `sortes`.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import os
import pathlib
import re
import sys
import tempfile
from datetime import UTC, datetime, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"
FRONT = ROOT / "frontend" / "src"

FAILURES: list[str] = []
NOW = datetime.now(UTC)


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> None:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))


def _read(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"cannot read {path}: {exc}")
        return ""


# --- EE1 -----------------------------------------------------------------------

def check_ee1() -> None:
    from world_engine import condition_forms, condition_interpreter, condition_text, conditions, event_vocab
    from world_engine.models import CONDITION_ROLES, CONDITION_WINDOWS

    for group in ("REQUIREMENT_TYPES", "KEY_TARGET_TYPES", "THRESHOLD_TYPES", "ANY_SUBJECT_TYPES"):
        if "event" not in getattr(condition_forms, group):
            fail(f"EE1: `event` is not in {group}")
    if "event" in condition_forms.MODEL_REQUIREMENT_TYPES:
        fail("EE1: the model's day plan may emit `event`")
    if conditions.EVENT_FORM != event_vocab.EVENT_FORM or conditions.EVENT_FORM != "event":
        fail(f"EE1: EVENT_FORM is {conditions.EVENT_FORM!r} / {event_vocab.EVENT_FORM!r}")
    if "event" not in condition_interpreter.TARGET_HINTS_FR or "event" not in condition_text.FORM_PHRASES_FR:
        fail("EE1: the interpreter's hints or the French phrases have no `event` line")
    if tuple(condition_text.SINCE_LABELS_FR) != tuple(CONDITION_WINDOWS):
        fail(f"EE1: SINCE_LABELS_FR is {tuple(condition_text.SINCE_LABELS_FR)}, windows {CONDITION_WINDOWS}")
    js = _read(FRONT / "creation" / "questRequirements.js")
    block = re.search(r"export const EVENT_WINDOWS = \{(.*?)\};", js, re.S)
    keys = tuple(re.findall(r"^\s*(\w+):", block.group(1), re.M)) if block else ()
    if keys != tuple(CONDITION_WINDOWS):
        fail(f"EE1: the editor's EVENT_WINDOWS are {keys}, windows {CONDITION_WINDOWS}")
    if "failure" not in CONDITION_ROLES:
        fail(f"EE1: CONDITION_ROLES is {CONDITION_ROLES}")


# --- fixture -------------------------------------------------------------------

def _fixture(engine) -> dict:
    from sqlmodel import Session

    from world_engine.event_vocab import type_view
    from world_engine.models import Character, Entity, Location, World
    from world_engine.writes.event_types import EventTypeSpec, RoleSpec, write_event_type, write_sorte
    from world_engine.writes.events import EventScopeSpec, EventSpec, ParticipantSpec, write_event

    with Session(engine) as db:
        world = World(name="Chasses", is_active=True)
        db.add(world)
        db.flush()
        ids = {"world": world.id}
        for key, kind, name in (("foret", "location", "Forêt"), ("clairiere", "location", "Clairière"),
                                ("ville", "location", "Ville"), ("mira", "character", "Mira"),
                                ("brakk", "character", "Brakk"), ("odo", "character", "Odo")):
            entity = Entity(world_id=world.id, type=kind, name=name)
            db.add(entity)
            db.flush()
            ids[key] = entity.id
        db.add(Location(id=ids["foret"]))
        db.add(Location(id=ids["ville"]))
        db.flush()
        db.add(Location(id=ids["clairiere"], parent_location_id=ids["foret"]))
        for key in ("mira", "brakk", "odo"):
            db.add(Character(id=ids[key], world_id=world.id, character_type="player" if key == "mira" else "npc",
                             current_location_id=ids["ville"]))
        ids["loup"] = write_sorte(db, world_id=world.id, name="Loup").id
        ids["ours"] = write_sorte(db, world_id=world.id, name="Ours").id
        chasse = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
            name="Chasse", counts_quantity=True,
            roles=(RoleSpec("Chasseur", ("character",)), RoleSpec("Proie", ("character",), accepts_sorte=True))))
        duel = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
            name="Duel", roles=(RoleSpec("Adversaire", ("character",)),)))
        autre = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
            name="Fête", roles=(RoleSpec("Invité", ("location",)),)))
        ids.update(chasse=chasse.id, duel=duel.id, fete=autre.id)
        view = type_view(db, chasse.id)
        ids["chasseur"], ids["proie"] = view.roles[0].id, view.roles[1].id
        ids["adversaire"] = type_view(db, duel.id).roles[0].id
        ids["invite"] = type_view(db, autre.id).roles[0].id
        hunts = (
            ("mira", "loup", 3, "clairiere", 10), ("mira", "loup", 2, "ville", 5), ("mira", "ours", 4, "foret", 1),
            ("brakk", "loup", 7, "foret", 3),
        )
        for who, prey, qty, place, hours in hunts:
            event = write_event(db, world_id=world.id, created_by="check", spec=EventSpec(
                type_id=chasse.id, title=f"{who} chasse", quantity=qty, location_id=ids[place], scopes=(),
                participants=(ParticipantSpec(ids["chasseur"], entity_id=ids[who], secret=who == "brakk"),
                              ParticipantSpec(ids["proie"], sorte_id=ids[prey]))))
            event.recorded_at = NOW - timedelta(hours=hours)
            db.add(event)
        write_event(db, world_id=world.id, created_by="check", spec=EventSpec(
            type_id=duel.id, title="Un duel", scopes=(),
            participants=(ParticipantSpec(ids["adversaire"], entity_id=ids["mira"]),)))
        db.commit()
    return ids


def _leaf(ids: dict, **kw):
    from world_engine.condition_forms import EventFilter, RequirementSpec

    filters = tuple(EventFilter(*f) if isinstance(f, tuple) else f for f in kw.pop("filters", ()))
    base = dict(type="event", subject_role="doer", subject_entity_id=None, target_entity_id=None,
                target_key=ids["chasse"], threshold=None, value=ids["chasseur"], since=None, filters=filters)
    base.update(kw)
    return RequirementSpec(**base)


def _wolf(ids: dict) -> tuple:
    return ((ids["proie"], None, ids["loup"]),)


# --- EE2 -----------------------------------------------------------------------

def check_ee2(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.conditions import ConditionTree, read_condition
    from world_engine.models import Agenda, AgendaStep, QuestOffer
    from world_engine.writes.conditions import clean_leaf, write_condition

    with Session(engine) as db:
        kept = clean_leaf(db, ids["world"], _leaf(ids, filters=_wolf(ids)))
        if (kept.threshold, kept.since, kept.value, len(kept.filters)) != (1, "always", ids["chasseur"], 1):
            fail(f"EE2: a plain event leaf is kept as {kept}")
        refused = {
            "an unknown type": _leaf(ids, target_key="nope"),
            "a role of another type": _leaf(ids, value=ids["adversaire"]),
            "a role that does not take the subject": _leaf(ids, target_key=ids["fete"], value=ids["invite"],
                                                            subject_role=None, subject_entity_id=ids["mira"]),
            "a place that is no location": _leaf(ids, target_entity_id=ids["odo"]),
            "a role named twice": _leaf(ids, filters=((ids["chasseur"], ids["odo"], None),)),
            "a sorte on a role that takes none": _leaf(ids, value=None, filters=((ids["chasseur"], None,
                                                                                  ids["loup"]),)),
            "an unknown window": _leaf(ids, since="forever"),
        }
        for what, req in refused.items():
            try:
                clean_leaf(db, ids["world"], req)
                fail(f"EE2: clean_leaf accepts {what}")
            except ValueError:
                pass
        agenda = Agenda(world_id=ids["world"], owner_entity_id=ids["mira"], title="t", status="paused")
        db.add(agenda)
        db.flush()
        step = AgendaStep(agenda_id=agenda.id, step_order=1, objective="o", status="pending")
        db.add(step)
        db.flush()
        tree = ConditionTree(op="leaf", leaf=_leaf(ids, since="step", threshold=2, filters=_wolf(ids)))
        write_condition(db, world_id=ids["world"], role="completion", tree=tree, agenda_step_id=step.id)
        back = read_condition(db, role="completion", agenda_step_id=step.id)
        leaf = back.leaf if back is not None and back.op == "leaf" else (back.children[0].leaf if back else None)
        if leaf is None or leaf.since != "step" or [(f.role_id, f.sorte_id) for f in leaf.filters] != [
                (ids["proie"], ids["loup"])]:
            fail(f"EE2: the stored leaf reads back as {leaf}")
        offer = QuestOffer(world_id=ids["world"], giver_entity_id=ids["odo"], title="o", change_history=[])
        db.add(offer)
        db.flush()
        try:
            write_condition(db, world_id=ids["world"], role="eligibility", quest_offer_id=offer.id,
                            tree=ConditionTree(op="leaf", leaf=_leaf(ids, since="quest")))
            fail("EE2: an eligibility counting since the quest is accepted")
        except ValueError:
            pass
        db.rollback()


# --- EE3 / EE4 -----------------------------------------------------------------

def _judge(db, ids: dict, req, **bind):
    from world_engine.conditions import Bindings, ConditionTree, evaluate
    from world_engine.models import Character

    doer = db.get(Character, ids["mira"])
    return evaluate(ConditionTree(op="leaf", leaf=req), Bindings(doer=doer, giver_id=ids["brakk"], **bind), db)


def check_ee3(engine, ids: dict) -> None:
    from sqlmodel import Session

    cases = (
        ("wolves", dict(threshold=5, filters=_wolf(ids)), {}, ("met", 5)),
        ("six wolves", dict(threshold=6, filters=_wolf(ids)), {}, ("unmet", 5)),
        ("wolves at the Forêt", dict(threshold=1, filters=_wolf(ids), target_entity_id=ids["foret"]), {},
         ("met", 3)),
        ("any role", dict(threshold=1, value=None), {}, ("met", 9)),
        ("Brakk's wolves", dict(threshold=1, subject_role="giver", filters=_wolf(ids)), {}, ("met", 7)),
        ("a duel", dict(threshold=1, target_key=ids["duel"], value=None), {}, ("met", 1)),
        ("since the quest", dict(threshold=1, since="quest"), {"quest_since": NOW - timedelta(hours=6)},
         ("met", 6)),
        ("since the step", dict(threshold=1, since="step"),
         {"quest_since": NOW - timedelta(hours=6), "step_since": NOW - timedelta(hours=2)}, ("met", 4)),
        ("a step never started", dict(threshold=1, since="step"), {"quest_since": NOW - timedelta(hours=6)},
         ("met", 6)),
    )
    with Session(engine) as db:
        for what, kw, bind, (state, count) in cases:
            node = _judge(db, ids, _leaf(ids, **kw), **bind)
            got = (node.state, node.verdict.current if node.verdict else None)
            if got != (state, count):
                fail(f"EE3: {what} judges {got}, not {(state, count)}")
        node = _judge(db, ids, _leaf(ids, threshold=1, since="quest"))
        if node.state != "unknown":
            fail(f"EE3: a `quest` window with no quest judges {node.state}")


def check_ee4(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.conditions import known_event_facts

    with Session(engine) as db:
        brakk = _judge(db, ids, _leaf(ids, threshold=1, subject_role="giver", filters=_wolf(ids)))
        seen = brakk.seen_by(ids["mira"], known_event_facts(db, brakk, ids["mira"]))
        if brakk.state != "met" or seen.state != "unmet" or seen.verdict.current != 0:
            fail(f"EE4: Brakk's secret hunt reads {brakk.state} then {seen.state} for Mira")
        own = _judge(db, ids, _leaf(ids, threshold=5, filters=_wolf(ids)))
        mine = own.seen_by(ids["mira"], known_event_facts(db, own, ids["mira"]))
        if mine.state != "met" or mine.verdict.current != 5:
            fail(f"EE4: Mira's own hunts recount to {mine.state} {mine.verdict and mine.verdict.current}")
        if own.seen_by(ids["mira"]).state != "unknown":
            fail("EE4: with no known facts, an event leaf is not `unknown`")


# --- EE5 -----------------------------------------------------------------------

def check_ee5(engine, ids: dict) -> None:
    from sqlmodel import Session, select

    from world_engine.conditions import ConditionTree, node_to_dict, read_condition
    from world_engine.day_plan import PlanStep
    from world_engine.models import AgendaStep, Character
    from world_engine.quest_reads import player_quests
    from world_engine.writes.goals_agendas import write_agenda_step_status
    from world_engine.writes.quests import accept_quest, write_quest_offer

    failure = ConditionTree(op="leaf", leaf=_leaf(ids, threshold=1, target_key=ids["duel"], value=None,
                                                  since="step"))
    with Session(engine) as db:
        offer = write_quest_offer(
            db, world_id=ids["world"], offer=None, giver_entity_id=ids["odo"], title="La chasse",
            summary=None, repeatable=False, status="open", eligibility=None,
            steps=[PlanStep("Chasser", 1, None, failure=failure), PlanStep("Rentrer", 1, None)])
        db.flush()
        quest = accept_quest(db, offer=offer, character=db.get(Character, ids["mira"]))
        db.commit()
        steps = db.exec(select(AgendaStep).where(AgendaStep.agenda_id == quest.agenda_id)
                        .order_by(AgendaStep.step_order)).all()
        copied = read_condition(db, role="failure", agenda_step_id=steps[0].id)
        stored = node_to_dict(copied) if copied is not None else {}
        stored = stored["children"][0] if "children" in stored else stored
        if stored.get("since") != "step":
            fail(f"EE5: the accepted step's failure is {copied}")
        if steps[0].started_at is None or steps[1].started_at is not None:
            fail(f"EE5: started_at is {steps[0].started_at} / {steps[1].started_at}")
        view = player_quests(db.get(Character, ids["mira"]), db)
        first = view[0]["steps"][0] if view else {}
        if not first.get("failure") or first.get("failure_met") is not False:
            fail(f"EE5: Journée shows the failure as {first.get('failure')}, met {first.get('failure_met')}")
        write_agenda_step_status(db, step=steps[0], status="completed")
        db.refresh(steps[1])
        if steps[1].status == "active" and steps[1].started_at is None:
            fail("EE5: the next step became active without a start")
        if steps[1].status != "active":
            write_agenda_step_status(db, step=steps[1], status="active")
            if steps[1].started_at is None:
                fail("EE5: activating a pending step leaves started_at empty")
        db.rollback()
    readers = sorted(p.relative_to(SRC).as_posix() for p in SRC.rglob("*.py")
                     if re.search(r"role=\"failure\"", p.read_text(encoding="utf-8")))
    if readers != ["quest_reads.py", "writes/quests.py"]:
        fail(f"EE5: a failure condition is read or written by {readers}")


# --- EE6 -----------------------------------------------------------------------

def check_ee6() -> None:
    wants = {
        FRONT / "creation" / "questRequirements.js": (
            "event: { label: 'A vécu l’événement', list: 'eventTypes', column: 'key', threshold: true }",),
        FRONT / "creation" / "QuestRequirementRow.svelte": ("fillerOptions", "EVENT_WINDOWS", "req.since",
                                                           "req.filters", "n’importe quel rôle"),
        FRONT / "creation" / "OfferEditor.svelte": ('role="failure"',),
        FRONT / "creation" / "questOffers.svelte.js": ("failure: conditionBody(s.failure)", "failure_draft_id"),
        FRONT / "journee" / "QuestPanel.svelte": ("step.failure_met",),
        SRC / "quest_reads.py": ('"event_types":', '"sortes":'),
    }
    for path, needles in wants.items():
        text = _read(path)
        for needle in needles:
            if needle not in text:
                fail(f"EE6: {path.name} lacks {needle!r}")


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    check_ee1()
    ids = _fixture(engine)
    for check in (check_ee2, check_ee3, check_ee4, check_ee5):
        try:
            check(engine, ids)
        except Exception as exc:  # a crash is a failure, never a pass
            fail(f"{check.__name__}: crashed: {type(exc).__name__}: {exc}")
    check_ee6()
    for msg in FAILURES:
        print(f"FAIL: {msg}")
    if FAILURES:
        return 1
    print("PASS: event_conditions -- a condition counts the events its subject lived, by type, role, place, "
          "window and filters, summing quantities; a player counts only those he knows; a quest step says "
          "when it has failed, shown and never acting; the offer editor writes both")
    return 0


if __name__ == "__main__":
    sys.exit(main())
