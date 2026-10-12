"""G1 check for TICKET-0114 -- the event journal's writer: an event, its participants by role, its fact, who learns it.

BRIEF-0114-C's rules (`event_journal.py` holds BRIEF-0114-A/B's).

EC1 -- the writer (fixture). `write_event` writes « Brakk tue 3 loups dans
   la Forêt » (type « Tuer », counting; Brakk as `tueur`, the sorte « Loup »
   as `victime`): one event row with its type and quantity, two
   participants in order, one fact on it with facet `evenement` and the
   text « title — description », the type's `location` scope made the
   Forêt at `rumor` (its `rencontre` scope on the victim makes nothing: a
   sorte has met no one), and Brakk's knowledge row at `knows`, not
   secret. A « Pacte » (participants secret by default, a `faction` scope
   on its role) between an NPC, the PC and a faction: the NPC's row is
   secret, the PC's never (INV-07), even asked; the faction is a scope at
   `knows`, and holds no knowledge row. A spec's own `scopes` replace the
   type's; an empty tuple means no one.
EC2 -- refusals (fixture), each with no row written: an unknown type, a
   retired type, an empty title, a place that is not a location, a quantity
   on a type that counts none, a quantity of 0, a role of another type, an
   entity of a type the role does not accept, a sorte in a role that takes
   none, a role filled by both an entity and a sorte, one participant twice
   in one role, an unknown scope, a `world` scope naming an entity, a
   `faction` scope naming a character.
EC3 -- a correction (fixture). `write_event_update` rewrites the title: the
   fact's text follows, its history holds the former text with the kind
   `correction`; a participant added gets his knowledge row; a participant
   made secret has his row secret; the scopes are replaced whole; taking a
   participant away, or changing the type, is refused with no row changed.
EC4 -- the approved proposal (fixture, `_apply_mutation`). A typed
   `event_creation` payload writes its event, typed, with its participants;
   an untyped one (`type: 'social'`, `involved_entities`, `knowledge_status:
   'public'`) is typed « Social » (made for the world), its entities take
   the role « Impliqué », and its fact has a `world` scope at `knows`; a
   `secret` one has none. A payload whose role is unknown returns an
   `event_creation:` error and writes no event.
EC5 -- the routes (fixture, route functions). `create_event` answers the
   event with its type, participants (role, name, secret) and scopes;
   `update_event` corrects it; a refusal answers 422 and writes nothing; an
   unknown event is 404.
EC6 -- the sheet (static). `EVENT_FIELDS` names `title`, `description`,
   `location_id` and nothing else; `crud/events.py` and
   `cockpit/mutations.py`'s `event_creation` applier name no
   `knowledge_status` and no `EventEntity`; `Evenements.svelte` renders the
   shared `EventEditor.svelte` on its draft (TICKET-0119), which renders the
   type select `event-f-type_id`, the quantity, each role's participants with
   their secret, and the scopes; `Sheet.svelte` sends
   `eventDraftBody(isNewSave)`; `eventDraft.svelte.js` exports
   `eventDraftBody` and never removes a `saved` participant.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"
FRONT = ROOT / "frontend" / "src" / "creation"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> None:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))


def _fixture(engine) -> dict:
    from sqlmodel import Session

    from world_engine.models import Character, Entity, Faction, Location, World
    from world_engine.writes.event_types import (
        EventTypeSpec, RoleSpec, ScopeSpec, set_event_type_status, write_event_type, write_sorte,
    )

    with Session(engine) as db:
        world = World(name="Journal", is_active=True)
        db.add(world)
        db.flush()
        ids = {"world": world.id}
        for key, kind, name in (("brakk", "character", "Brakk"), ("ysa", "character", "Ysa"),
                                ("mira", "character", "Mira"), ("foret", "location", "Forêt"),
                                ("guilde", "faction", "Guilde")):
            entity = Entity(world_id=world.id, type=kind, name=name)
            db.add(entity)
            db.flush()
            ids[key] = entity.id
            if kind == "character":
                db.add(Character(id=entity.id, world_id=world.id,
                                 character_type="player" if key == "mira" else "npc"))
            elif kind == "location":
                db.add(Location(id=entity.id))
            else:
                db.add(Faction(id=entity.id))
        ids["loup"] = write_sorte(db, world_id=world.id, name="Loup").id
        tuer = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
            name="Tuer", domain="military", counts_quantity=True,
            roles=(RoleSpec("tueur", ("character",)), RoleSpec("victime", ("character",), accepts_sorte=True)),
            scopes=(ScopeSpec("location", level="rumor"), ScopeSpec("rencontre", role="victime"))))
        pacte = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
            name="Pacte", domain="political", participants_secret=True,
            roles=(RoleSpec("partie", ("character", "faction")),),
            scopes=(ScopeSpec("faction", role="partie"),)))
        vieux = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
            name="Vieux", roles=(RoleSpec("x", ("character",)),)))
        set_event_type_status(db, world_id=world.id, type_id=vieux.id, status="retired")
        db.flush()
        from world_engine.event_vocab import type_view
        ids["tuer"], ids["pacte"], ids["vieux"] = tuer.id, pacte.id, vieux.id
        tv, pv = type_view(db, tuer.id), type_view(db, pacte.id)
        ids["tueur"], ids["victime"], ids["partie"] = tv.roles[0].id, tv.roles[1].id, pv.roles[0].id
        db.commit()
    return ids


def _counts(db) -> tuple[int, ...]:
    from sqlmodel import func, select

    from world_engine import models

    return tuple(db.exec(select(func.count()).select_from(m)).one() for m in (
        models.Event, models.EventParticipant, models.Fact, models.FactDefault, models.Knowledge))


def _refused(db, label: str, rule: str, call) -> None:
    before = _counts(db)
    try:
        call()
    except ValueError:
        db.rollback()
        if _counts(db) != before:
            fail(f"{rule}: {label} was refused after writing a row")
        return
    db.rollback()
    fail(f"{rule}: {label} was accepted")


def _knowledge(db, entity_id: str, fact_id: str):
    from sqlmodel import select

    from world_engine.models import Knowledge

    return db.exec(select(Knowledge).where(Knowledge.entity_id == entity_id, Knowledge.fact_id == fact_id)).first()


def _scopes(db, fact_id: str) -> list:
    from sqlmodel import select

    from world_engine.models import FactDefault

    return sorted((r.scope_type, r.scope_id, r.level) for r in db.exec(
        select(FactDefault).where(FactDefault.fact_id == fact_id)).all())


def _hunt(ids, **fields):
    from world_engine.writes.events import EventSpec, ParticipantSpec

    base = dict(type_id=ids["tuer"], title="Brakk tue 3 loups", description="Dans la Forêt.",
                location_id=ids["foret"], quantity=3,
                participants=(ParticipantSpec(ids["tueur"], entity_id=ids["brakk"]),
                              ParticipantSpec(ids["victime"], sorte_id=ids["loup"])))
    base.update(fields)
    return EventSpec(**base)


def check_ec1(engine, ids: dict) -> dict:
    from sqlmodel import Session, select

    from world_engine.models import EventParticipant
    from world_engine.writes.events import EventScopeSpec, EventSpec, ParticipantSpec, event_fact, write_event

    made = {}
    with Session(engine) as db:
        hunt = write_event(db, world_id=ids["world"], spec=_hunt(ids), created_by="check")
        db.commit()
        made["hunt"] = hunt.id
        rows = db.exec(select(EventParticipant).where(EventParticipant.event_id == hunt.id)
                       .order_by(EventParticipant.position)).all()
        if (hunt.type_id, hunt.quantity) != (ids["tuer"], 3) or \
                [(r.role_id, r.entity_id, r.sorte_id) for r in rows] != [
                    (ids["tueur"], ids["brakk"], None), (ids["victime"], None, ids["loup"])]:
            fail(f"EC1: the hunt reads {hunt.type_id}/{hunt.quantity} with {[(r.entity_id, r.sorte_id) for r in rows]}")
        fact = event_fact(db, hunt.id)
        if fact is None or fact.facet != "evenement" or fact.content_raw != "Brakk tue 3 loups — Dans la Forêt.":
            fail(f"EC1: the hunt's fact is {fact and (fact.facet, fact.content_raw)}")
        if fact and _scopes(db, fact.id) != [("location", ids["foret"], "rumor")]:
            fail(f"EC1: the hunt's scopes are {_scopes(db, fact.id)}")
        known = _knowledge(db, ids["brakk"], fact.id) if fact else None
        if known is None or known.level != "knows" or known.is_secret:
            fail(f"EC1: Brakk holds {known and (known.level, known.is_secret)}")
        pact = write_event(db, world_id=ids["world"], created_by="check", spec=EventSpec(
            type_id=ids["pacte"], title="Le pacte",
            participants=(ParticipantSpec(ids["partie"], entity_id=ids["ysa"]),
                          ParticipantSpec(ids["partie"], entity_id=ids["mira"], secret=True),
                          ParticipantSpec(ids["partie"], entity_id=ids["guilde"]))))
        db.commit()
        made["pact"] = pact.id
        pf = event_fact(db, pact.id)
        ysa, mira, guilde = (_knowledge(db, ids[k], pf.id) for k in ("ysa", "mira", "guilde"))
        if ysa is None or not ysa.is_secret or mira is None or mira.is_secret or guilde is not None:
            fail(f"EC1: the pact's knowledge is ysa {ysa and ysa.is_secret}, mira {mira and mira.is_secret}, "
                 f"guilde {guilde}")
        if _scopes(db, pf.id) != [("faction", ids["guilde"], "knows")]:
            fail(f"EC1: the pact's scopes are {_scopes(db, pf.id)}")
        own = write_event(db, world_id=ids["world"], created_by="check", spec=_hunt(
            ids, title="Une chasse", scopes=(EventScopeSpec("world", None, "rumor"),)))
        none = write_event(db, world_id=ids["world"], created_by="check", spec=_hunt(ids, title="Une autre", scopes=()))
        db.commit()
        if _scopes(db, event_fact(db, own.id).id) != [("world", None, "rumor")] or \
                _scopes(db, event_fact(db, none.id).id):
            fail("EC1: a spec's own scopes did not replace the type's")
    return made


def check_ec2(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.writes.events import EventScopeSpec, ParticipantSpec, write_event

    tueur, victime, partie = ids["tueur"], ids["victime"], ids["partie"]
    cases = {
        "an unknown type": _hunt(ids, type_id="nope"),
        "a retired type": _hunt(ids, type_id=ids["vieux"], quantity=None, participants=()),
        "an empty title": _hunt(ids, title="  "),
        "a place that is not a location": _hunt(ids, location_id=ids["brakk"]),
        "a quantity on a type that counts none": _hunt(ids, type_id=ids["pacte"], participants=()),
        "a quantity of 0": _hunt(ids, quantity=0),
        "a role of another type": _hunt(ids, participants=(ParticipantSpec(partie, entity_id=ids["brakk"]),)),
        "an entity the role does not accept": _hunt(ids, participants=(ParticipantSpec(tueur, entity_id=ids["foret"]),)),
        "a sorte in a role that takes none": _hunt(ids, participants=(ParticipantSpec(tueur, sorte_id=ids["loup"]),)),
        "an entity and a sorte at once": _hunt(ids, participants=(
            ParticipantSpec(victime, entity_id=ids["ysa"], sorte_id=ids["loup"]),)),
        "one participant twice": _hunt(ids, participants=(ParticipantSpec(tueur, entity_id=ids["brakk"]),
                                                          ParticipantSpec(tueur, entity_id=ids["brakk"]))),
        "an unknown scope": _hunt(ids, scopes=(EventScopeSpec("planet", None, "knows"),)),
        "a world scope naming an entity": _hunt(ids, scopes=(EventScopeSpec("world", ids["brakk"], "knows"),)),
        "a faction scope naming a character": _hunt(ids, scopes=(EventScopeSpec("faction", ids["brakk"], "knows"),)),
    }
    with Session(engine) as db:
        for label, spec in cases.items():
            _refused(db, label, "EC2", lambda spec=spec: write_event(db, world_id=ids["world"], spec=spec,
                                                                     created_by="check"))


def check_ec3(engine, ids: dict, made: dict) -> None:
    from sqlmodel import Session

    from world_engine.models import Event
    from world_engine.writes.events import EventScopeSpec, ParticipantSpec, event_fact, write_event_update

    with Session(engine) as db:
        hunt = db.get(Event, made["hunt"])
        kept = (ParticipantSpec(ids["tueur"], entity_id=ids["brakk"], secret=True),
                ParticipantSpec(ids["victime"], sorte_id=ids["loup"]))
        write_event_update(db, event=hunt, changed_by="check", spec=_hunt(
            ids, title="Brakk tue 4 loups", quantity=4,
            participants=kept + (ParticipantSpec(ids["tueur"], entity_id=ids["ysa"]),),
            scopes=(EventScopeSpec("world", None, "rumor"),)))
        db.commit()
        fact = event_fact(db, hunt.id)
        history = fact.change_history or []
        if fact.content_raw != "Brakk tue 4 loups — Dans la Forêt." or not history or \
                history[-1].get("kind") != "correction" or history[-1].get("content") != "Brakk tue 3 loups — Dans la Forêt.":
            fail(f"EC3: the corrected fact reads {fact.content_raw!r}, history {history[-1:]}")
        brakk, ysa = _knowledge(db, ids["brakk"], fact.id), _knowledge(db, ids["ysa"], fact.id)
        if brakk is None or not brakk.is_secret or ysa is None:
            fail(f"EC3: after the correction Brakk is secret {brakk and brakk.is_secret}, Ysa holds {ysa}")
        if _scopes(db, fact.id) != [("world", None, "rumor")]:
            fail(f"EC3: the scopes are {_scopes(db, fact.id)}")
        for label, spec in {
            "taking a participant away": _hunt(ids, participants=kept[:1]),
            "changing the type": _hunt(ids, type_id=ids["pacte"], quantity=None, participants=()),
        }.items():
            _refused(db, label, "EC3", lambda spec=spec: write_event_update(db, event=db.get(Event, made["hunt"]),
                                                                            spec=spec, changed_by="check"))


def _mutation(db, world_id: str, payload: dict):
    from world_engine.models import ProposedMutation

    mut = ProposedMutation(world_id=world_id, source_type="world_tick", tick_id="t", mutation_type="event_creation",
                           target_table="event", payload=payload, status="approved")
    db.add(mut)
    db.flush()
    return mut


def check_ec4(engine, ids: dict) -> None:
    from sqlmodel import Session, func, select

    from world_engine.cockpit.routes.mutations import _apply_mutation
    from world_engine.event_vocab import DOMAIN_ROLE_FR, type_view
    from world_engine.models import Event, EventParticipant
    from world_engine.writes.events import event_fact

    world = ids["world"]
    with Session(engine) as db:
        typed = _mutation(db, world, {"title": "Ysa tue un loup", "type_id": ids["tuer"], "quantity": 1,
                                      "participants": [{"role_id": ids["tueur"], "entity_id": ids["ysa"]},
                                                       {"role_id": ids["victime"], "sorte_id": ids["loup"]}]})
        error = _apply_mutation(typed, db)
        db.commit()
        event = db.exec(select(Event).where(Event.title == "Ysa tue un loup")).first()
        if error or event is None or event.type_id != ids["tuer"] or db.exec(select(func.count()).select_from(
                EventParticipant).where(EventParticipant.event_id == event.id)).one() != 2:
            fail(f"EC4: a typed payload gave {error!r}, event {event}")
        public = _mutation(db, world, {"title": "La fête", "type": "social", "knowledge_status": "public",
                                       "involved_entities": [ids["brakk"], ids["guilde"]]})
        secret = _mutation(db, world, {"title": "Le complot", "type": "social", "knowledge_status": "secret",
                                       "involved_entities": [ids["brakk"]]})
        errors = (_apply_mutation(public, db), _apply_mutation(secret, db))
        db.commit()
        fete = db.exec(select(Event).where(Event.title == "La fête")).first()
        complot = db.exec(select(Event).where(Event.title == "Le complot")).first()
        view = type_view(db, fete.type_id) if fete else None
        roles = {p.entity_id: p.role_id for p in db.exec(select(EventParticipant).where(
            EventParticipant.event_id == (fete.id if fete else "")))}
        if any(errors) or view is None or view.name != "Social" or [r.name for r in view.roles] != [DOMAIN_ROLE_FR] \
                or set(roles) != {ids["brakk"], ids["guilde"]}:
            fail(f"EC4: untyped payloads gave {errors}, type {view and view.name}, participants {roles}")
        if fete and _scopes(db, event_fact(db, fete.id).id) != [("world", None, "knows")]:
            fail("EC4: a public untyped payload's fact has no world scope at knows")
        if complot and _scopes(db, event_fact(db, complot.id).id):
            fail("EC4: a secret untyped payload's fact has scopes")
        before = db.exec(select(func.count()).select_from(Event)).one()
        bad = _mutation(db, world, {"title": "X", "type_id": ids["tuer"],
                                    "participants": [{"role_id": "nope", "entity_id": ids["ysa"]}]})
        with db.begin_nested():
            answer = _apply_mutation(bad, db)
        if not (answer or "").startswith("event_creation:"):
            fail(f"EC4: an unknown role answered {answer!r}")
        db.rollback()
        if db.exec(select(func.count()).select_from(Event)).one() != before:
            fail("EC4: an unknown role wrote an event")


def check_ec5(engine, ids: dict) -> None:
    from fastapi import HTTPException
    from sqlmodel import Session, func, select

    from world_engine.cockpit.crud import events as routes
    from world_engine.models import Event

    with Session(engine) as db:
        body = routes.EventBody(title="Mira croise un loup", type_id=ids["tuer"], location_id=ids["foret"], quantity=1,
                                participants=[routes.ParticipantBody(role_id=ids["tueur"], entity_id=ids["mira"]),
                                              routes.ParticipantBody(role_id=ids["victime"], sorte_id=ids["loup"])])
        made = routes.create_event(body, db)
        names = [(p["role_name"], p["name"], p["secret"]) for p in made["participants"]]
        if made["type_name"] != "Tuer" or names != [("tueur", "Mira", False), ("victime", "Loup", None)] \
                or [s["scope_type"] for s in made["scopes"]] != ["location"]:
            fail(f"EC5: create_event answered {made['type_name']}, {names}, {made['scopes']}")
        body.title = "Mira chasse un loup"
        if routes.update_event(made["id"], body, db)["title"] != "Mira chasse un loup":
            fail("EC5: update_event did not correct the title")
        before = db.exec(select(func.count()).select_from(Event)).one()
        for label, call in (("a refused event", lambda: routes.create_event(routes.EventBody(
                title=" ", type_id=ids["tuer"]), db)),
                            ("an unknown event", lambda: routes.get_event("nope", db))):
            try:
                call()
                fail(f"EC5: {label} was answered")
            except HTTPException as exc:
                want = 404 if "unknown" in label else 422
                if exc.status_code != want:
                    fail(f"EC5: {label} answered {exc.status_code}")
        if db.exec(select(func.count()).select_from(Event)).one() != before:
            fail("EC5: a refused event wrote a row")


def _function_source(path: pathlib.Path, name: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(path.read_text(encoding="utf-8"), node) or ""
    return ""


def check_ec6() -> None:
    from world_engine.cockpit.crud._shared import EVENT_FIELDS

    if [f["name"] for f in EVENT_FIELDS] != ["title", "description", "location_id"]:
        fail(f"EC6: EVENT_FIELDS names {[f['name'] for f in EVENT_FIELDS]}")
    crud = (SRC / "cockpit" / "crud" / "events.py").read_text(encoding="utf-8")
    applier = _function_source(SRC / "cockpit" / "mutations.py", "_mutation_apply_event_creation")
    if not applier:
        fail("EC6: _mutation_apply_event_creation is missing")
    for name, text in (("crud/events.py", crud), ("the event_creation applier", applier)):
        for needle in ("knowledge_status", "EventEntity"):
            if needle in text:
                fail(f"EC6: {name} names {needle}")
    # TICKET-0119 (BRIEF-0119-D): the sheet's editing moved into the shared
    # EventEditor.svelte, which Evenements.svelte renders on its draft.
    needles = {
        "Evenements.svelte": ("<EventEditor draft={eventDraftState}",),
        "EventEditor.svelte": ('id="event-f-type_id"', 'id="event-f-quantity"', "bind:checked={p.secret}",
                               "draft.scopes", "role.accepts_sorte"),
        "Sheet.svelte": ("eventDraftBody(isNewSave)",),
        "eventDraft.svelte.js": ("export function eventDraftBody", "!draft.participants[i].saved"),
    }
    for name, wanted in needles.items():
        path = FRONT / name
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        for needle in wanted:
            if needle not in text:
                fail(f"EC6: {name} lacks {needle}")


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    ids = _fixture(engine)
    state: dict = {}

    def ec1() -> None:
        state.update(check_ec1(engine, ids))

    rules = (("EC1", ec1), ("EC2", lambda: check_ec2(engine, ids)), ("EC3", lambda: check_ec3(engine, ids, state)),
             ("EC4", lambda: check_ec4(engine, ids)), ("EC5", lambda: check_ec5(engine, ids)), ("EC6", check_ec6))
    for name, rule in rules:
        try:
            rule()
        except Exception as exc:  # a crash is that rule's failure, never a pass
            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: event_writes -- an event is written with its type, its participants by role, its fact, the "
          "type's scopes made concrete and its participants' knowledge, secret each as said; a correction "
          "keeps its type and its participants; an approved proposal, typed or not, is written the same way")
    return 0


if __name__ == "__main__":
    sys.exit(main())
