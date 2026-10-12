"""G1 check for TICKET-0119 -- what an event changes in the world: pre-filled from its type, written with it, all or none.

BRIEF-0119-C's rules (M-c, D3, E1 and F1 of the conditions series);
`event_effects.py` holds what a type declares.

EM1 -- the pre-fill (fixture). `type_changes` makes « Ouvrir »'s effect
   Cible -> Ouvert = oui concrete on the door in the role Cible; a sorte in
   that role changes nothing; « Usurper »'s Trône -> Occupé par takes the
   first entity in the role Usurpateur, and is left out when that role holds
   none; « Être repéré »'s Garnison -> Alerte + 1 keeps its mode.
EM2 -- the writer (fixture). `record_event` with three changes writes the
   event, then « Ouvert » of the door as a `changement` naming the event, the
   guild's « Alerte » added twice by two events (0 -> 1 -> 2), and Ivo's
   `État vital` -> `dead` on his character row, returned in
   `system_changes` with its before (`alive`); its `rows` name the event,
   its fact, each `attribute_value` and `attribute_change` it wrote.
EM3 -- all or nothing (fixture). Each refused with no event, fact or
   change written: an unknown state, `Magie`, a state that does not apply
   to the entity, a value not one of the state's choices, `add` on a
   choice, an entity value of a type the state may not name, one state of
   one entity twice, a vital state on a location, a location made active
   again, and a correction (`write_event_update`) carrying a change.
EM4 -- the system states (static and fixture). `writes/entity_states.py`'s
   `write_system_state` calls `close_open_memberships`; an entity made
   `destroyed` has its open `gathering_member` row closed (`left_at` set).
EM5 -- the approved proposal (fixture, `_apply_mutation`). A typed
   `event_creation` whose `state_changes` name Ivo's vital state writes the
   event and kills him, and its payload gains `applied_changes` with
   before and after; one whose change is refused answers `event_creation:`
   and writes no event and no change.
EM6 -- the producers pre-fill (fixture). Play's `typed_payload` of an
   « Ouvrir » proposal carries the door's change in `state_changes`; a
   proposal of a NEW type carries none. The journal's `create_event`
   writes a body's `state_changes`; `update_event` with one answers 422.

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

    from world_engine.attributes import attribute_view
    from world_engine.event_vocab import type_view
    from world_engine.models import Character, Entity, Faction, Location, World
    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec, write_attribute_definition
    from world_engine.writes.event_types import (
        EffectSpec,
        EventTypeSpec,
        RoleSpec,
        write_event_type,
        write_sorte,
    )

    with Session(engine) as db:
        world = World(name="Changements", is_active=True)
        db.add(world)
        db.flush()
        w = world.id
        ids = {"world": w}
        for key, kind, name in (("millys", "character", "Millys"), ("ivo", "character", "Ivo"),
                                ("ysa", "character", "Ysa"), ("porte", "location", "Porte du caveau"),
                                ("cour", "location", "Cour"), ("ruine", "location", "Ruine"),
                                ("guilde", "faction", "Garnison")):
            entity = Entity(world_id=w, type=kind, name=name, status="inactive" if key == "ruine" else "active")
            db.add(entity)
            db.flush()
            ids[key] = entity.id
            if kind == "character":
                db.add(Character(id=entity.id, world_id=w, character_type="npc"))
            elif kind == "location":
                db.add(Location(id=entity.id))
            else:
                db.add(Faction(id=entity.id))
        ouvert = write_attribute_definition(db, world_id=w, spec=DefinitionSpec(
            name="Ouvert", kind="choice", holder_types=("location",),
            choices=(ChoiceSpec("non"), ChoiceSpec("oui")), default="non"))
        occupe = write_attribute_definition(db, world_id=w, spec=DefinitionSpec(
            name="Occupé par", kind="entity", holder_types=("location",), value_types=("character",)))
        alerte = write_attribute_definition(db, world_id=w, spec=DefinitionSpec(
            name="Alerte", kind="integer", holder_types=("faction",), default=0))
        db.flush()
        choices = {label: key for key, label in attribute_view(db, w, ouvert.id).choices}
        ids.update(ouvert=ouvert.id, occupe=occupe.id, alerte=alerte.id, oui=choices["oui"], non=choices["non"])
        ids["loup"] = write_sorte(db, world_id=w, name="Loup").id
        types = {
            "ouvrir": EventTypeSpec(name="Ouvrir", roles=(
                RoleSpec("Ouvreur", ("character",)), RoleSpec("Cible", ("location",), accepts_sorte=True)),
                effects=(EffectSpec("Cible", ouvert.id, choices["oui"]),)),
            "usurper": EventTypeSpec(name="Usurper", roles=(
                RoleSpec("Usurpateur", ("character",)), RoleSpec("Trône", ("location",))),
                effects=(EffectSpec("Trône", occupe.id, "Usurpateur"),)),
            "reperer": EventTypeSpec(name="Être repéré", roles=(
                RoleSpec("Intrus", ("character",)), RoleSpec("Garnison", ("faction",))),
                effects=(EffectSpec("Garnison", alerte.id, 1, "add"),)),
            "tuer": EventTypeSpec(name="Tuer", roles=(
                RoleSpec("Tueur", ("character",)), RoleSpec("Victime", ("character",))),
                effects=(EffectSpec("Victime", "sys:vital_status", "dead"),)),
        }
        for key, spec in types.items():
            type_id = write_event_type(db, world_id=w, spec=spec).id
            ids[key] = type_id
            for role in type_view(db, type_id).roles:
                ids[f"{key}:{role.name}"] = role.id
        db.commit()
    return ids


def _counts(db) -> tuple[int, ...]:
    from sqlmodel import func, select

    from world_engine.models import AttributeChange, AttributeValue, Event, Fact

    return tuple(db.exec(select(func.count()).select_from(m)).one() for m in (Event, Fact, AttributeValue,
                                                                              AttributeChange))


def _spec(ids: dict, type_key: str, title: str, participants, changes=()):
    from world_engine.writes.events import EventSpec, ParticipantSpec, StateChangeSpec

    return EventSpec(type_id=ids[type_key], title=title,
                     participants=tuple(ParticipantSpec(role_id=ids[f"{type_key}:{r}"], entity_id=e, sorte_id=s)
                                        for r, e, s in participants),
                     changes=tuple(StateChangeSpec(*c) for c in changes))


def check_em1(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.event_changes import type_changes
    from world_engine.event_vocab import type_view

    w = ids["world"]
    with Session(engine) as db:
        got = (
            type_changes(db, w, type_view(db, ids["ouvrir"]), [(ids["ouvrir:Ouvreur"], ids["millys"]),
                                                              (ids["ouvrir:Cible"], ids["porte"])]),
            type_changes(db, w, type_view(db, ids["ouvrir"]), [(ids["ouvrir:Cible"], None)]),
            type_changes(db, w, type_view(db, ids["usurper"]), [(ids["usurper:Usurpateur"], ids["ysa"]),
                                                               (ids["usurper:Trône"], ids["cour"])]),
            type_changes(db, w, type_view(db, ids["usurper"]), [(ids["usurper:Trône"], ids["cour"])]),
            type_changes(db, w, type_view(db, ids["reperer"]), [(ids["reperer:Garnison"], ids["guilde"])]),
        )
    want = (
        [{"entity_id": ids["porte"], "attribute": ids["ouvert"], "mode": "set", "value": ids["oui"]}],
        [],
        [{"entity_id": ids["cour"], "attribute": ids["occupe"], "mode": "set", "value": ids["ysa"]}],
        [],
        [{"entity_id": ids["guilde"], "attribute": ids["alerte"], "mode": "add", "value": 1}],
    )
    if got != want:
        fail(f"EM1: the pre-filled changes are {got}")


def check_em2(engine, ids: dict) -> None:
    from sqlmodel import Session, select

    from world_engine.attributes import attribute_view, current_value
    from world_engine.models import AttributeChange, Character, Entity
    from world_engine.writes.events import record_event

    w = ids["world"]
    with Session(engine) as db:
        written = record_event(db, world_id=w, created_by="check", spec=_spec(
            ids, "tuer", "Millys ouvre et tue", [("Tueur", ids["millys"], None), ("Victime", ids["ivo"], None)],
            [(ids["porte"], ids["ouvert"], ids["oui"]), (ids["guilde"], ids["alerte"], 1, "add"),
             (ids["ivo"], "sys:vital_status", "dead")]))
        record_event(db, world_id=w, created_by="check", spec=_spec(
            ids, "reperer", "Repéré", [("Intrus", ids["millys"], None)], [(ids["guilde"], ids["alerte"], 1, "add")]))
        db.commit()
        changes = db.exec(select(AttributeChange).where(AttributeChange.event_id == written.event.id)).all()
        door = current_value(db, attribute_view(db, w, ids["ouvert"]), db.get(Entity, ids["porte"])).raw
        alert = current_value(db, attribute_view(db, w, ids["alerte"]), db.get(Entity, ids["guilde"])).raw
        if door != ids["oui"] or alert != 2 or len(changes) != 2 or any(c.kind != "changement" for c in changes):
            fail(f"EM2: door {door}, alert {alert}, the event's changes {[(c.kind, c.after_integer) for c in changes]}")
        if db.get(Character, ids["ivo"]).vital_status != "dead" or written.system_changes != [
                {"entity_id": ids["ivo"], "attribute": "sys:vital_status", "before": "alive", "after": "dead"}]:
            fail(f"EM2: Ivo's vital state is {db.get(Character, ids['ivo']).vital_status}, "
                 f"system changes {written.system_changes}")
        tables = sorted({table for table, _id, _action in written.rows})
        if tables != ["attribute_change", "attribute_value", "event", "event_participant", "fact", "knowledge"]:
            fail(f"EM2: the rows written name {tables}")


def check_em3(engine, ids: dict) -> None:
    from sqlmodel import Session, select

    from world_engine.models import Event
    from world_engine.writes.events import record_event, write_event_update

    w = ids["world"]
    door = [("Ouvreur", ids["millys"], None), ("Cible", ids["porte"], None)]
    refused = (
        ("an unknown state", [(ids["porte"], "nope", ids["oui"])]),
        ("Magie", [(ids["porte"], "sys:magic_status", "active")]),
        ("a state that does not apply", [(ids["millys"], ids["ouvert"], ids["oui"])]),
        ("a value not a choice", [(ids["porte"], ids["ouvert"], "peut-être")]),
        ("add on a choice", [(ids["porte"], ids["ouvert"], ids["oui"], "add")]),
        ("an entity value of the wrong type", [(ids["cour"], ids["occupe"], ids["guilde"])]),
        ("one state twice", [(ids["porte"], ids["ouvert"], ids["oui"]), (ids["porte"], ids["ouvert"], ids["non"])]),
        ("a vital state on a location", [(ids["porte"], "sys:vital_status", "dead")]),
        ("a location made active again", [(ids["ruine"], "sys:status", "active")]),
    )
    with Session(engine) as db:
        for label, changes in refused:
            before = _counts(db)
            try:
                record_event(db, world_id=w, created_by="check", spec=_spec(ids, "ouvrir", label, door, changes))
                fail(f"EM3: {label} was not refused")
            except ValueError:
                pass
            db.rollback()
            if _counts(db) != before:
                fail(f"EM3: {label} was refused but wrote rows")
        event = db.exec(select(Event).where(Event.world_id == w)).first()
        before = _counts(db)
        try:
            write_event_update(db, event=event, changed_by="check", spec=_spec(
                ids, "tuer", event.title, [("Tueur", ids["millys"], None), ("Victime", ids["ivo"], None)],
                [(ids["porte"], ids["ouvert"], ids["non"])]))
            fail("EM3: a correction carrying a change was not refused")
        except ValueError:
            pass
        db.rollback()
        if _counts(db) != before:
            fail("EM3: the refused correction wrote rows")


def check_em4(engine, ids: dict) -> None:
    from sqlmodel import Session, select

    from world_engine.models import Gathering, GatheringMember, Session as PlaySession
    from world_engine.writes.events import record_event

    tree = ast.parse((SRC / "writes" / "entity_states.py").read_text(encoding="utf-8"))
    func = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "write_system_state"), None)
    calls = {n.func.id for n in ast.walk(func) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)} \
        if func else set()
    if "close_open_memberships" not in calls:
        fail("EM4: write_system_state does not call close_open_memberships")
    w = ids["world"]
    with Session(engine) as db:
        play = PlaySession(world_id=w, number=1)
        db.add(play)
        db.flush()
        gathering = Gathering(world_id=w, session_id=play.id, location_id=ids["porte"])
        db.add(gathering)
        db.flush()
        member = GatheringMember(gathering_id=gathering.id, entity_id=ids["ysa"])
        db.add(member)
        db.commit()
        record_event(db, world_id=w, created_by="check", spec=_spec(
            ids, "ouvrir", "Ysa part", [("Ouvreur", ids["ysa"], None)], [(ids["ysa"], "sys:status", "missing")]))
        db.commit()
        left = db.exec(select(GatheringMember).where(GatheringMember.id == member.id)).first()
        if left is None or left.left_at is None:
            fail("EM4: an entity made missing keeps its open gathering membership")


def _mutation(db, world_id: str, payload: dict):
    from world_engine.models import ProposedMutation

    mut = ProposedMutation(world_id=world_id, source_type="world_tick", tick_id="t", mutation_type="event_creation",
                           target_table="event", payload=payload, status="approved")
    db.add(mut)
    db.flush()
    return mut


def check_em5(engine, ids: dict) -> None:
    from sqlmodel import Session, select

    from world_engine.cockpit.routes.mutations import _apply_mutation
    from world_engine.models import Character, Event

    w = ids["world"]
    with Session(engine) as db:
        db.get(Character, ids["ivo"]).vital_status = "alive"
        db.commit()
        mut = _mutation(db, w, {"title": "Millys tue Ivo", "type_id": ids["tuer"], "participants": [
            {"role_id": ids["tuer:Tueur"], "entity_id": ids["millys"]},
            {"role_id": ids["tuer:Victime"], "entity_id": ids["ivo"]}],
            "state_changes": [{"entity_id": ids["ivo"], "attribute": "sys:vital_status", "mode": "set",
                               "value": "dead"}]})
        error = _apply_mutation(mut, db)
        db.commit()
        if error or db.get(Character, ids["ivo"]).vital_status != "dead" or mut.payload.get("applied_changes") != [
                {"entity_id": ids["ivo"], "attribute": "sys:vital_status", "before": "alive", "after": "dead"}]:
            fail(f"EM5: an approved kill gave {error!r}, payload {mut.payload.get('applied_changes')}")
        before = _counts(db)
        bad = _mutation(db, w, {"title": "Mal", "type_id": ids["tuer"], "participants": [],
                                "state_changes": [{"entity_id": ids["porte"], "attribute": "sys:magic_status",
                                                   "value": "active"}]})
        with db.begin_nested():
            answer = _apply_mutation(bad, db)
        db.rollback()
        if not (answer or "").startswith("event_creation:") or _counts(db) != before:
            fail(f"EM5: a refused change answered {answer!r}, counts {before} -> {_counts(db)}")
        if db.exec(select(Event).where(Event.title == "Mal")).first() is not None:
            fail("EM5: a refused change wrote its event")


def check_em6(engine, ids: dict) -> None:
    from fastapi import HTTPException
    from sqlmodel import Session

    from world_engine.attributes import attribute_view, current_value
    from world_engine.cockpit.crud import events as crud
    from world_engine.event_analysis import analysis_vocabulary, typed_payload
    from world_engine.models import Entity

    w = ids["world"]
    with Session(engine) as db:
        vocab = analysis_vocabulary(db, w)
        code = vocab.codes.code_of(ids["ouvrir"])
        typed = typed_payload(db, w, {"title": "La porte cède", "event_type": code, "participants": [
            {"role": "Ouvreur", "entity_id": ids["millys"]}, {"role": "Cible", "entity_id": ids["cour"]}]}, vocab)
        if not typed or typed.get("state_changes") != [
                {"entity_id": ids["cour"], "attribute": ids["ouvert"], "mode": "set", "value": ids["oui"]}]:
            fail(f"EM6: Play's typed payload carries {typed and typed.get('state_changes')}")
        fresh = typed_payload(db, w, {"title": "x", "new_type": {"name": "Briser", "roles": [
            {"name": "Briseur", "for": ["character"]}]}, "participants": [
            {"role": "Briseur", "entity_id": ids["millys"]}]}, vocab)
        if not fresh or "state_changes" in fresh:
            fail(f"EM6: a new type's payload is {fresh}")
        body = crud.EventBody(title="Ouvrir la cour", type_id=ids["ouvrir"], participants=[
            {"role_id": ids["ouvrir:Cible"], "entity_id": ids["cour"]}],
            state_changes=[{"entity_id": ids["cour"], "attribute": ids["ouvert"], "value": ids["oui"]}])
        made = crud.create_event(body, db)
        state = current_value(db, attribute_view(db, w, ids["ouvert"]), db.get(Entity, ids["cour"]))
        if state.raw != ids["oui"] or state.is_default:
            fail(f"EM6: the journal's state_changes wrote {state}")
        try:
            crud.update_event(made["id"], body, db)
            fail("EM6: update_event with a change was not refused")
        except HTTPException as exc:
            if exc.status_code != 422:
                fail(f"EM6: update_event with a change answered {exc.status_code}")


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    ids = _fixture(engine)
    rules = (
        ("EM1", lambda: check_em1(engine, ids)), ("EM2", lambda: check_em2(engine, ids)),
        ("EM3", lambda: check_em3(engine, ids)), ("EM4", lambda: check_em4(engine, ids)),
        ("EM5", lambda: check_em5(engine, ids)), ("EM6", lambda: check_em6(engine, ids)),
    )
    for name, rule in rules:
        try:
            rule()
        except Exception as exc:  # a crash is that rule's failure, never a pass
            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: event_changes -- an event's type pre-fills what it changes in the world; an event writes its "
          "changes with it, all or none, each naming it; the vital state and the status are written by their own "
          "writer, closing a gathering seat, and an approved proposal keeps their before and after")
    return 0


if __name__ == "__main__":
    sys.exit(main())
