"""G1 check for TICKET-0121 -- the quest designer, its proposal, its applier (INV-63).

BRIEF-0121-E's rules (C1, D1, F1, G1, H2, V1 of the Journée quest designer):

QD1 -- a request whose subject the lore does not hold: `design` -> `asking`, one model call (the
   subject), no `condition_draft`, no proposal.
QD2 -- a world with an NPC knowing a secret fact and a scripted offer (two steps, one cost in money,
   givers [the NPC, an unknown name]): one `quest_offer_creation` proposal by `local_ai_quest_designer`,
   sourced from the request's pass_play, every key of C-10, one giver suggestion and a note for the
   other, the fact in `secret_fact_ids`, one `condition_draft` per non-null condition (attempt id =
   the request's), the request `proposed` with its `mutation_id`; a condition that defines a new
   state is in `pending_drafts` with `answer.outcome == "proposed"`, its tree null
   (AMENDMENT-0121-01, D-05).
QD3 -- an objective repeating four words of the secret fact: one flag on `steps.1.objective`;
   approving with a giver and `flags_confirmed` false leaves the proposal `approved` with the error and
   writes no offer; with `flags_confirmed` true -> `applied`, one offer with that giver, `target_id`
   its id, the request's `offer_id` (INV-63). D-02 (AMENDMENT-0121-01): a draft the approved payload
   names that was already `inserted` ends `saved`; a draft of the request it no longer names keeps
   its outcome.
QD4 -- a condition naming an ambiguous name: its tree null, one `pending_drafts` entry whose answer
   is `needs_choice`; approving -> « Des conditions attendent encore un choix. », nothing written.
QD5 -- a first answer with a refused condition (an unknown form), the second fixed: two design
   calls, the second carrying the error; the proposal comes from the second. Approving it leaves
   every draft of the first answer neither `inserted` nor `saved` (D-02).
QD6 -- `covered` naming an open offer's code -> the request `covered`, its `offer_id` that offer;
   `unknown` -> `asking` with the note.
QD7 -- the routes: `/design` on `writing_lore` -> 409; `/answer` `absent` on `asking` ->
   `writing_lore` and « <subject> n'existe pas dans ce monde. <text> »; `already` with an entity ->
   `new`; `/drop` on a pending proposal -> 409; the Lore commit with `quest_request_id` on a
   `writing_lore` request -> `new` with `lore_entry_id`, on a `new` request -> 422, nothing written.
QD8 -- static: INV-01 names the quest designer; INV-63 exists with its marker; `PRODUCERS` holds the
   value; `PROMPT_REGISTRY` holds both usages on `_author_model`; the applier is in `appliers`.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any world_engine import) --
never Nia's DB; the model (`quest_designer.chat`) is a stub returning scripted JSON; rows go through
the real writers. A rule that collects nothing fails.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

FAILURES: list[str] = []
SECRET = "Le secret de l'acier noir tient dans la trempe du fer"


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> None:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))


# --- the stubbed model -----------------------------------------------------------

class Stub:
    """Scripted answers by usage (read from the system prompt); an entry may be a callable of the user
    message. Every call is recorded."""

    def __init__(self) -> None:
        self.script: dict[str, list] = {"subject": [], "design": []}
        self.calls: list[tuple[str, str]] = []

    def __call__(self, messages, model=None, format=None, **_kw) -> str:
        system, user = messages[0]["content"], messages[1]["content"]
        usage = "subject" if system.startswith("Tu prépares une quête") else "design"
        self.calls.append((usage, user))
        answer = self.script[usage].pop(0)
        return json.dumps(answer(user) if callable(answer) else answer, ensure_ascii=False)


STUB = Stub()


def _leaf(form, target=None, **extra) -> dict:
    return {"op": "leaf", "form": form, "subject": "doer", "target": target, "threshold": None,
            "value": None, **extra}


def _cond(phrase, *leaves) -> dict:
    return {"phrase": phrase, "condition": {"op": "all", "children": list(leaves)}, "define": [],
            "define_events": [], "define_sortes": [], "unsupported": []}


def _subject(subject="le secret de l'acier noir", keywords=("acier", "noir"), names=("Orvane",)) -> dict:
    return {"subject": subject, "keywords": list(keywords), "names": list(names)}


def _step(objective, completion=None, cost=1, domain=None) -> dict:
    return {"objective": objective, "cost": cost, "domain": domain, "prerequisite": None,
            "completion": completion, "failure": None}


def _design(*steps, title="L'énigme du fer noir", givers=("Orvane",), terms=(), outcome="offer", **extra):
    return {"outcome": outcome, "covered_by": None, "unknown": None, "title": title,
            "summary": "Trouve celui qui connaît la trempe.", "givers": list(givers), "eligibility": None,
            "steps": list(steps), "terms": list(terms), "notes": [], **extra}


def _code(user: str, label: str, prefix: str) -> str:
    found = re.search(rf"({prefix}\d+) — {re.escape(label)}", user)
    return found.group(1) if found else "x0"


# --- fixture ---------------------------------------------------------------------

def _build(db) -> dict:
    from world_engine.conditions import all_of
    from world_engine.day_plan import PlanStep
    from world_engine.models import Batch, Character, Entity, Fact, PassPlay, World
    from world_engine.models import Session as GameSession
    from world_engine.writes import attach_participants, create_fact, write_knowledge, write_quest_offer

    ids: dict = {}
    world = World(name="Monde QD", is_active=True)
    db.add(world)
    db.flush()
    session = GameSession(world_id=world.id, number=1)
    db.add(session)
    db.flush()

    def character(name: str, kind: str = "npc") -> str:
        entity = Entity(world_id=world.id, type="character", name=name)
        db.add(entity)
        db.flush()
        db.add(Character(id=entity.id, world_id=world.id, character_type=kind))
        db.flush()
        return entity.id

    ids["hero"] = character("Heros", "player")
    ids["npc"] = character("Orvane")
    ids["marek1"], ids["marek2"] = character("Marek"), character("Marek")
    batch = Batch(session_id=session.id, day_number=3)
    db.add(batch)
    db.flush()
    play = PassPlay(batch_id=batch.id, session_id=session.id, character_id=ids["hero"],
                    declared_action="Je veux le secret de l'acier noir.", status="submitted")
    db.add(play)
    db.flush()
    fact = create_fact(db, world_id=world.id, content=SECRET, created_by="check", facet="information")
    db.flush()
    attach_participants(db, fact=db.get(Fact, fact.id), entity_ids=[ids["npc"]])
    write_knowledge(db, entity_id=ids["npc"], fact_id=fact.id, level="knows", is_secret=True, changed_by="check")
    offer = write_quest_offer(
        db, world_id=world.id, offer=None, giver_entity_id=ids["npc"], title="Livrer le fer", summary=None,
        repeatable=False, status="open", eligibility=None,
        steps=[PlanStep(objective="Porter le fer", cost=1, domain=None)])
    db.commit()
    ids.update(world=world.id, session=session.id, batch=batch.id, play=play.id, fact=fact.id,
               offer=offer.id, counter=0)
    return ids


def _request(db, ids, declaration="Je veux le secret de l'acier noir."):
    from world_engine.models import Agenda, AgendaStep
    from world_engine.writes.quest_requests import open_request

    ids["counter"] += 1
    agenda = Agenda(world_id=ids["world"], owner_entity_id=ids["hero"], title=f"Plan {ids['counter']}")
    db.add(agenda)
    db.flush()
    step = AgendaStep(agenda_id=agenda.id, step_order=1, objective=declaration)
    db.add(step)
    db.flush()
    request = open_request(db, world_id=ids["world"], character_id=ids["hero"], pass_play_id=ids["play"],
                           trigger="route", declaration=declaration, agenda_step_id=step.id)
    db.commit()
    return request


def _drafts(db, request):
    from sqlmodel import select

    from world_engine.models import ConditionDraft

    return db.exec(select(ConditionDraft).where(ConditionDraft.attempt_id == request.id)).all()


def _run(db, request, subject, *designs):
    from world_engine import quest_designer

    STUB.calls.clear()
    STUB.script = {"subject": [subject], "design": list(designs)}
    result = quest_designer.design(db, request, [])
    db.commit()
    return result


def _approve(db, mut, payload):
    from world_engine.cockpit.routes.mutations import ApproveBody, approve_mutation

    return approve_mutation(mut.id, ApproveBody(payload=json.dumps(payload)), db)


def _offers(db, ids, title):
    from sqlmodel import select

    from world_engine.models import QuestOffer

    return db.exec(select(QuestOffer).where(QuestOffer.world_id == ids["world"], QuestOffer.title == title)).all()


# --- QD1 ---------------------------------------------------------------------------

def check_qd1(db, ids) -> object:
    from world_engine.models import ProposedMutation
    from sqlmodel import select

    request = _request(db, ids, "Je cherche les dragons-zombies.")
    before = len(db.exec(select(ProposedMutation)).all())
    result = _run(db, request, _subject("les dragons-zombies", ("dragons", "zombies"), ()))
    if result.outcome != "asking" or request.status != "asking" or request.subject != "les dragons-zombies":
        fail(f"QD1: outcome {result.outcome!r}, request {request.status!r}/{request.subject!r}")
    if len(STUB.calls) != 1 or STUB.calls[0][0] != "subject":
        fail(f"QD1: model calls {[c[0] for c in STUB.calls]}, expected the subject alone")
    if _drafts(db, request) or len(db.exec(select(ProposedMutation)).all()) != before:
        fail("QD1: a draft or a proposal was written")
    return request


# --- QD2 / QD3 -----------------------------------------------------------------------

def _defined_state() -> dict:
    """A condition proposing a new state (AMENDMENT-0121-01, D-05): proposed, yet pending."""
    return {**_cond("Être reconnu par la guilde", _leaf("attribute", {"define": "d1"}, value="oui")),
            "define": [{"ref": "d1", "name": "Reconnu par la guilde", "kind": "choice", "for": ["character"],
                        "choices": ["non", "oui"], "default": "non", "hidden": False}]}


def _offer_answers(repeat: bool = False, define: bool = False):
    def second(user: str) -> dict:
        code = _code(user, "Le secret", "f")
        objective = ("Apprendre que le secret de l'acier noir tient dans la trempe" if repeat
                     else "Apprendre la trempe auprès de lui")
        first = _step("Rencontrer Orvane", _cond("Avoir rencontré Orvane", _leaf(
            "has_met", {"name": "Orvane", "kind": "person"})))
        if define:
            first["failure"] = _defined_state()
        return _design(
            first,
            _step(objective, _cond("Connaître le secret", _leaf("knowledge", {"code": code})), 2, "perception"),
            givers=("Orvane", "Zorglub"),
            terms=({"direction": "cost", "currency": "money", "target": None, "amount": 10, "level": None},))
    return second


def check_qd2(db, ids) -> object:
    from world_engine.models import ProposedMutation

    request = _request(db, ids)
    result = _run(db, request, _subject(), _offer_answers(define=True))
    mut = result.mutation
    if result.outcome != "proposed" or mut is None:
        fail(f"QD2: outcome {result.outcome!r}, notes {result.notes}")
        return request
    keys = {"request_id", "character_id", "subject", "giver_entity_id", "contact_entity_id", "giver_suggestions",
            "title", "summary", "repeatable", "status", "eligibility", "eligibility_draft_id", "steps", "terms",
            "unsaved_attributes", "pending_drafts", "notes", "consulted_fact_ids", "secret_fact_ids", "flags",
            "flags_confirmed"}
    row = db.get(ProposedMutation, mut.id)
    payload = row.payload
    if (row.proposed_by != "local_ai_quest_designer" or row.mutation_type != "quest_offer_creation"
            or row.pass_play_id != ids["play"] or row.status != "proposed" or row.source_type != "pass_play"):
        fail(f"QD2: the row is {row.proposed_by!r}/{row.mutation_type!r}/{row.status!r}")
    if set(payload) != keys:
        fail(f"QD2: payload keys differ: {sorted(set(payload) ^ keys)}")
        return request
    if [g["entity_id"] for g in payload["giver_suggestions"]] != [ids["npc"]] or not any(
            "Zorglub" in n for n in payload["notes"]):
        fail(f"QD2: givers {payload['giver_suggestions']}, notes {payload['notes']}")
    if ids["fact"] not in payload["secret_fact_ids"]:
        fail("QD2: the secret fact is not in secret_fact_ids")
    drafts = _drafts(db, request)
    if len(drafts) != 3 or any(d.outcome != "proposed" for d in drafts):
        fail(f"QD2: {len(drafts)} drafts ({[d.outcome for d in drafts]}), expected 3 proposed")
    steps = payload["steps"]
    if len(steps) != 2 or any(s["completion"] is None or not s["completion_draft_id"] for s in steps):
        fail("QD2: a step lost its completion tree or draft id")
    if len(payload["terms"]) != 1 or payload["terms"][0]["amount"] != 10:
        fail(f"QD2: terms {payload['terms']}")
    if request.status != "proposed" or request.mutation_id != mut.id or request.subject != "le secret de l'acier noir":
        fail(f"QD2: request {request.status!r}, mutation_id {request.mutation_id!r}")
    if payload["flags"]:
        fail(f"QD2: flags {payload['flags']} on a clean offer")
    pending = payload["pending_drafts"]
    if [p["where"] for p in pending] != ["steps.0.failure"] or pending[0]["answer"].get("outcome") != "proposed"             or steps[0]["failure"] is not None or steps[0]["failure_draft_id"] is not None:
        fail(f"QD2: a defined state is not pending as proposed: {[(p['where'], p['answer'].get('outcome')) for p in pending]}")
    return request


def check_qd3(db, ids) -> None:
    from sqlmodel import select

    from world_engine.models import ConditionDraft, ProposedMutation, QuestRequest

    request = _request(db, ids)
    title = "Le fer et sa trempe"
    answers = _offer_answers(repeat=True)
    result = _run(db, request, _subject(), lambda user: {**answers(user), "title": title})
    mut = result.mutation
    if mut is None:
        fail(f"QD3: no proposal ({result.outcome!r})")
        return
    payload = dict(db.get(ProposedMutation, mut.id).payload)
    if [f["path"] for f in payload["flags"]] != ["steps.1.objective"] or payload["flags"][0]["fact_id"] != ids["fact"]:
        fail(f"QD3: flags {payload['flags']}")
    # a lone giver is not enough: the flag stands until the creator confirms
    first = _approve(db, mut, {**payload, "giver_entity_id": ids["npc"], "flags_confirmed": False})
    if first.get("status") != "approved" or "Confirme" not in str(first.get("error")) or _offers(db, ids, title):
        fail(f"QD3: unconfirmed flag -> {first.get('status')!r} / {first.get('error')!r}")
    # the applier recomputes: a payload that emptied its own flags list still refuses
    cheat = _approve(db, mut, {**payload, "giver_entity_id": ids["npc"], "flags": [], "flags_confirmed": False})
    if cheat.get("status") != "approved" or _offers(db, ids, title):
        fail("QD3: an emptied flags list let the applier write")
    no_giver = _approve(db, mut, {**payload, "flags_confirmed": True})
    if no_giver.get("status") != "approved" or "donneur" not in str(no_giver.get("error")) or _offers(db, ids, title):
        fail(f"QD3: no giver -> {no_giver.get('status')!r} / {no_giver.get('error')!r}")
    # D-02: a draft the payload names that the creator already inserted (the card) ends saved; a draft
    # of this request the approved payload no longer names keeps its outcome.
    from world_engine.writes.condition_drafts import move_condition_draft

    inserted_id = payload["steps"][0]["completion_draft_id"]
    unnamed_id = payload["steps"][1]["completion_draft_id"]
    move_condition_draft(db, db.get(ConditionDraft, inserted_id), "inserted")
    db.commit()
    steps = [dict(payload["steps"][0]), {**payload["steps"][1], "completion_draft_id": None}]
    done = _approve(db, mut, {**payload, "steps": steps, "giver_entity_id": ids["npc"], "flags_confirmed": True})
    offers = _offers(db, ids, title)
    if done.get("status") != "applied" or len(offers) != 1 or offers[0].giver_entity_id != ids["npc"]:
        fail(f"QD3: confirmed -> {done.get('status')!r} / {done.get('error')!r}, {len(offers)} offer(s)")
        return
    db.refresh(mut)
    db.refresh(request)
    if mut.target_id != offers[0].id or request.offer_id != offers[0].id or request.status != "proposed":
        fail("QD3: target_id or the request's offer_id is not the written offer")
    states = {d.id: d.outcome for d in _drafts(db, request)}
    if states.get(inserted_id) != "saved":
        fail(f"QD3: the named draft inserted before approval is {states.get(inserted_id)!r}, expected saved")
    if states.get(unnamed_id) != "proposed":
        fail(f"QD3: a draft the payload does not name became {states.get(unnamed_id)!r}")
    if db.get(QuestRequest, request.id).offer_id != offers[0].id:
        fail("QD3: the request does not hold its offer")


# --- QD4 -----------------------------------------------------------------------------

def check_qd4(db, ids) -> None:
    from world_engine.models import ProposedMutation

    request = _request(db, ids)
    result = _run(db, request, _subject(), _design(
        _step("Retrouver Marek", _cond("Avoir rencontré Marek", _leaf("has_met", {"name": "Marek", "kind": "person"}))),
        title="Marek"))
    mut = result.mutation
    if mut is None:
        fail(f"QD4: no proposal ({result.outcome!r})")
        return
    payload = dict(db.get(ProposedMutation, mut.id).payload)
    pending = payload["pending_drafts"]
    if payload["steps"][0]["completion"] is not None or len(pending) != 1 \
            or pending[0]["answer"].get("outcome") != "needs_choice" or pending[0]["where"] != "steps.0.completion":
        fail(f"QD4: pending {[(p['where'], p['answer'].get('outcome')) for p in pending]}")
    out = _approve(db, mut, {**payload, "giver_entity_id": ids["npc"]})
    if out.get("status") != "approved" or out.get("error") != "Des conditions attendent encore un choix." \
            or _offers(db, ids, "Marek"):
        fail(f"QD4: approving -> {out.get('status')!r} / {out.get('error')!r}")


# --- QD5 -----------------------------------------------------------------------------

def check_qd5(db, ids) -> None:
    request = _request(db, ids)
    bad = _design(_step("Aller à la forge", _cond("Téléporté", _leaf("teleport", {"name": "Orvane", "kind": "person"}))),
                  _step("Voir Orvane", _cond("Avoir rencontré Orvane", _leaf(
                      "has_met", {"name": "Orvane", "kind": "person"}))), title="Première réponse")
    good = _design(_step("Aller à la forge", _cond("Avoir rencontré Orvane", _leaf(
        "has_met", {"name": "Orvane", "kind": "person"}))), title="Seconde réponse")
    result = _run(db, request, _subject(), bad, good)
    designs = [c for c in STUB.calls if c[0] == "design"]
    if len(designs) != 2 or "steps.0.completion" not in designs[1][1]:
        fail(f"QD5: {len(designs)} design call(s); the second carries the error: "
             f"{'steps.0.completion' in (designs[1][1] if len(designs) > 1 else '')}")
    if result.mutation is None or result.mutation.payload["title"] != "Seconde réponse":
        fail(f"QD5: proposal {result.outcome!r}, not from the second answer")
        return
    # D-02: approving the second answer's offer leaves every draft of the first answer as written.
    first = [d for d in _drafts(db, request) if not d.retried]
    if not any(d.outcome == "proposed" for d in first):
        fail(f"QD5: the first answer journaled no proposed draft ({[d.outcome for d in first]})")
    out = _approve(db, result.mutation, {**result.mutation.payload, "giver_entity_id": ids["npc"]})
    if out.get("status") != "applied":
        fail(f"QD5: approving the second answer -> {out.get('status')!r} / {out.get('error')!r}")
    for d in first:
        db.refresh(d)
    if any(d.outcome in ("inserted", "saved") for d in first):
        fail(f"QD5: a first-answer draft moved: {[d.outcome for d in first]}")


# --- QD6 -----------------------------------------------------------------------------

def check_qd6(db, ids) -> object:
    request = _request(db, ids)
    result = _run(db, request, _subject(), lambda user: {
        "outcome": "covered", "covered_by": _code(user, "Livrer le fer", "q"), "unknown": None})
    if result.outcome != "covered" or request.status != "covered" or request.offer_id != ids["offer"]:
        fail(f"QD6: covered -> {result.outcome!r}/{request.status!r}/{request.offer_id!r}")
    other = _request(db, ids)
    result = _run(db, other, _subject(), {"outcome": "unknown", "covered_by": None,
                                          "unknown": "Le lore ne dit pas où est la forge."})
    if result.outcome != "asking" or other.status != "asking" or other.note != "Le lore ne dit pas où est la forge.":
        fail(f"QD6: unknown -> {result.outcome!r}/{other.status!r}/{other.note!r}")
    return other


# --- QD7 -----------------------------------------------------------------------------

def check_qd7(db, ids, asking, proposed, covered) -> None:
    from fastapi import HTTPException
    from sqlmodel import select

    from world_engine.cockpit.routes import lore_write
    from world_engine.cockpit.routes import quest_requests as routes
    from world_engine.models import LoreEntry

    def status_of(call) -> int:
        try:
            call()
        except HTTPException as exc:
            return exc.status_code
        return 200

    out = routes.answer(asking.id, routes.AnswerBody(answer="absent", text="Aucun n'a jamais été vu."), db)
    want = "les dragons-zombies n'existe pas dans ce monde. Aucun n'a jamais été vu."
    if out["request"]["status"] != "writing_lore" or out["statement"] != want:
        fail(f"QD7: absent -> {out['request']['status']!r} / {out['statement']!r}")
    if status_of(lambda: routes.design(asking.id, db)) != 409:
        fail("QD7: /design on a writing_lore request is not 409")
    if status_of(lambda: routes.answer(asking.id, routes.AnswerBody(answer="exists", text="x"), db)) != 409:
        fail("QD7: /answer on a writing_lore request is not 409")
    if status_of(lambda: routes.drop(proposed.id, db)) != 409:
        fail("QD7: /drop on a pending proposal is not 409")
    seen = routes.answer(covered.id, routes.AnswerBody(answer="already", entity_id=ids["npc"]), db)
    if seen["request"]["status"] != "new" or seen["statement"] is not None:
        fail(f"QD7: already -> {seen['request']['status']!r}")
    listing = routes.list_requests(db)
    if not listing or any(r["status"] == "dropped" for r in listing):
        fail("QD7: the listing is empty or shows a dropped request")
    proposal = {"statement": "Les dragons-zombies n'existent pas.", "facts": [{
        "ref": "f1", "action": "create", "facet": "information",
        "content": "Les dragons-zombies n'existent pas."}]}
    entries = len(db.exec(select(LoreEntry)).all())
    refused = status_of(lambda: lore_write.write_commit(
        lore_write.CommitBody(proposal=proposal, quest_request_id=seen["request"]["id"]), db))
    if refused != 422 or len(db.exec(select(LoreEntry)).all()) != entries:
        fail(f"QD7: a Lore commit on a `new` request -> {refused}, entries {entries} -> "
             f"{len(db.exec(select(LoreEntry)).all())}")
    ok = lore_write.write_commit(lore_write.CommitBody(proposal=proposal, quest_request_id=asking.id), db)
    db.refresh(asking)
    if asking.status != "new" or asking.lore_entry_id != ok.get("entry_id") or not asking.lore_entry_id:
        fail(f"QD7: commit -> request {asking.status!r}, lore_entry_id {asking.lore_entry_id!r}")
    dropped = routes.drop(covered.id, db)
    if dropped["status"] != "dropped":
        fail("QD7: /drop on a `new` request did not drop it")


# --- QD8 -----------------------------------------------------------------------------

def check_qd8() -> None:
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    if "(Lore question, names panel, writing panel, condition interpreter, quest designer)" not in claude:
        fail("QD8: INV-01 does not name the quest designer")
    rules = (ROOT / ".claude" / "rules" / "mutation-pipeline.md").read_text(encoding="utf-8")
    law = re.search(r"- \*\*INV-63\*\*.*?(?=\n- \*\*INV-|\Z)", rules, re.S)
    if law is None or "-- enforced by `quest_designer.py`" not in law.group(0) \
            or "prose_guard.flags" not in law.group(0):
        fail("QD8: INV-63 is missing or lacks its marker")
    from world_engine.prompt_registry import PROMPT_REGISTRY, _author_model
    from world_engine.proposal_producers import PRODUCERS

    if "local_ai_quest_designer" not in PRODUCERS:
        fail("QD8: PRODUCERS lacks local_ai_quest_designer")
    for usage in ("quest_subject", "quest_design"):
        spec = PROMPT_REGISTRY.get(usage)
        if spec is None or spec.default_model is not _author_model or spec.surface != "authoring":
            fail(f"QD8: PROMPT_REGISTRY[{usage!r}] is missing or off the authoring model")
    routes = (SRC / "cockpit" / "routes" / "mutations.py").read_text(encoding="utf-8")
    if '"quest_offer_creation": _mutations._mutation_apply_quest_offer_creation' not in routes:
        fail("QD8: the applier is not in `appliers`")
    app = (SRC / "cockpit" / "app.py").read_text(encoding="utf-8")
    if "app.include_router(_routes_quest_requests.router)" not in app:
        fail("QD8: app.py does not mount the quest requests router")


def main() -> None:
    _fresh_db()
    from sqlmodel import Session, SQLModel

    from world_engine import models  # noqa: F401 -- registers every table
    from world_engine import quest_designer
    from world_engine.db import engine

    quest_designer.chat = STUB
    SQLModel.metadata.create_all(engine)
    import seed_pilot

    with Session(engine) as db:
        for entry in seed_pilot.QUEST_DESIGNER_PROMPT_HEADS:
            seed_pilot.upsert_prompt_template(db, **entry)
        db.commit()
        ids = _build(db)
        asking = check_qd1(db, ids)
        proposed = check_qd2(db, ids)
        check_qd3(db, ids)
        check_qd4(db, ids)
        check_qd5(db, ids)
        covered = check_qd6(db, ids)
        check_qd7(db, ids, asking, proposed, covered)
    check_qd8()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: quest_designer -- a request the lore cannot answer asks the creator, a covered or unknown "
          "one says so, an offer is proposed with its conditions journaled, its givers suggested and its "
          "secrets flagged, and the applier writes it through Création's save only with a giver, no "
          "condition waiting and every flag confirmed")


if __name__ == "__main__":
    main()
