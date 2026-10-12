"""G1 check for TICKET-0119 -- one event editor for the journal, the review card and Lore; the card approves what the creator edited.

BRIEF-0119-D's rules (H1 and Y2 of the conditions series).

EY1 -- the editor's read (fixture, route function). `event_changes` answers
   `prefilled`: « Ouvrir »'s effect made concrete on the door in its role
   Cible, with its French `line` (« Porte : Ouvert -> oui »); `described`:
   each change given, with its line, None for one naming nothing of the
   world; a type of another world answers 404. It writes nothing.
EY2 -- the card's payload (fixture, `_apply_mutation`). A typed
   `event_creation` payload whose `scopes` is an empty list writes the event
   with no scope (not its type's `world` scope); one with its own scope
   writes that one; one with no `scopes` key writes its type's; one whose
   participant carries `secret: true` writes that participant's knowledge
   secret.
EY3 -- the surfaces (static). `EventEditor.svelte` edits `draft.changes`
   (its « Pré-remplir » calls `prefilledChanges`), offers a participant's
   secret only when `!isPlayer(`, and keeps `draft.newType`'s roles;
   `Evenements.svelte` renders `<EventEditor` with `withChanges={isNew}`;
   `QueueCard.svelte` renders `<EventEditor` for a typed proposal and
   approves `payloadFromDraft(`; `eventDraft.svelte.js` exports
   `draftFromPayload`, `payloadFromDraft` and `prefilledChanges`, which posts
   to `/api/events/changes`, and `eventDraftBody` sends `state_changes`
   only for a new event.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
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

    from world_engine.attributes import attribute_view
    from world_engine.event_vocab import type_view
    from world_engine.models import Character, Entity, Location, World
    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec, write_attribute_definition
    from world_engine.writes.event_types import EffectSpec, EventTypeSpec, RoleSpec, ScopeSpec, write_event_type

    with Session(engine) as db:
        other = World(name="Ailleurs", is_active=False)
        world = World(name="Éditeur", is_active=True)
        db.add_all([other, world])
        db.flush()
        ids = {"world": world.id, "other": other.id}
        for key, kind, name in (("millys", "character", "Millys"), ("ivo", "character", "Ivo"),
                                ("porte", "location", "Porte"), ("cour", "location", "Cour")):
            entity = Entity(world_id=world.id, type=kind, name=name)
            db.add(entity)
            db.flush()
            ids[key] = entity.id
            db.add(Character(id=entity.id, world_id=world.id, character_type="npc") if kind == "character"
                   else Location(id=entity.id))
        ouvert = write_attribute_definition(db, world_id=world.id, spec=DefinitionSpec(
            name="Ouvert", kind="choice", holder_types=("location",),
            choices=(ChoiceSpec("non"), ChoiceSpec("oui")), default="non"))
        db.flush()
        ids["ouvert"] = ouvert.id
        ids["oui"] = {label: key for key, label in attribute_view(db, world.id, ouvert.id).choices}["oui"]
        ouvrir = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
            name="Ouvrir", roles=(RoleSpec("Ouvreur", ("character",)), RoleSpec("Cible", ("location",))),
            scopes=(ScopeSpec("world"),), effects=(EffectSpec("Cible", ouvert.id, ids["oui"]),)))
        foreign = write_event_type(db, world_id=other.id, spec=EventTypeSpec(
            name="Ailleurs", roles=(RoleSpec("Qui", ("character",)),)))
        db.flush()
        ids["ouvrir"], ids["foreign"] = ouvrir.id, foreign.id
        for role in type_view(db, ouvrir.id).roles:
            ids[role.name] = role.id
        db.commit()
    return ids


def check_ey1(engine, ids: dict) -> None:
    from fastapi import HTTPException
    from sqlmodel import Session, func, select

    from world_engine.cockpit.crud import events as crud
    from world_engine.models import AttributeChange, Event

    with Session(engine) as db:
        before = (db.exec(select(func.count()).select_from(Event)).one(),
                  db.exec(select(func.count()).select_from(AttributeChange)).one())
        body = crud.ChangesBody(type_id=ids["ouvrir"], participants=[
            {"role_id": ids["Ouvreur"], "entity_id": ids["millys"]}, {"role_id": ids["Cible"], "entity_id": ids["porte"]}],
            changes=[{"entity_id": ids["cour"], "attribute": ids["ouvert"], "value": ids["oui"]},
                     {"entity_id": "nobody", "attribute": ids["ouvert"], "value": ids["oui"]}])
        answer = crud.event_changes(body, db)
        want = {"prefilled": [{"entity_id": ids["porte"], "attribute": ids["ouvert"], "mode": "set",
                               "value": ids["oui"], "line": "Porte : Ouvert -> oui"}],
                "described": [{"entity_id": ids["cour"], "attribute": ids["ouvert"], "mode": "set",
                               "value": ids["oui"], "line": "Cour : Ouvert -> oui"},
                              {"entity_id": "nobody", "attribute": ids["ouvert"], "mode": "set",
                               "value": ids["oui"], "line": None}]}
        if answer != want:
            fail(f"EY1: event_changes answered {answer}")
        try:
            crud.event_changes(crud.ChangesBody(type_id=ids["foreign"]), db)
            fail("EY1: a type of another world was answered")
        except HTTPException as exc:
            if exc.status_code != 404:
                fail(f"EY1: a type of another world answered {exc.status_code}")
        after = (db.exec(select(func.count()).select_from(Event)).one(),
                 db.exec(select(func.count()).select_from(AttributeChange)).one())
        if after != before:
            fail("EY1: event_changes wrote rows")


def check_ey2(engine, ids: dict) -> None:
    from sqlmodel import Session, select

    from world_engine.cockpit.routes.mutations import _apply_mutation
    from world_engine.models import Event, FactDefault, Knowledge, ProposedMutation
    from world_engine.writes.events import event_fact

    base = {"type_id": ids["ouvrir"], "participants": [{"role_id": ids["Ouvreur"], "entity_id": ids["millys"]}]}
    cases = (
        ("Sans portée", {"scopes": []}, []),
        ("Portée propre", {"scopes": [{"scope_type": "location", "scope_id": ids["cour"], "level": "rumor"}]},
         [("location", ids["cour"], "rumor")]),
        ("Celle du type", {}, [("world", None, "knows")]),
    )
    with Session(engine) as db:
        for title, extra, want in cases:
            mut = ProposedMutation(world_id=ids["world"], source_type="world_tick", tick_id="t",
                                   mutation_type="event_creation", target_table="event",
                                   payload={"title": title, **base, **extra}, status="approved")
            db.add(mut)
            db.flush()
            error = _apply_mutation(mut, db)
            db.commit()
            event = db.exec(select(Event).where(Event.title == title)).first()
            fact = event_fact(db, event.id) if event else None
            got = sorted((d.scope_type, d.scope_id, d.level) for d in db.exec(
                select(FactDefault).where(FactDefault.fact_id == (fact.id if fact else ""))))
            if error or got != want:
                fail(f"EY2: « {title} » gave {error!r}, scopes {got}")
        secret = ProposedMutation(world_id=ids["world"], source_type="world_tick", tick_id="t",
                                  mutation_type="event_creation", target_table="event", status="approved",
                                  payload={"title": "En secret", "type_id": ids["ouvrir"], "participants": [
                                      {"role_id": ids["Ouvreur"], "entity_id": ids["ivo"], "secret": True}]})
        db.add(secret)
        db.flush()
        error = _apply_mutation(secret, db)
        db.commit()
        event = db.exec(select(Event).where(Event.title == "En secret")).first()
        row = db.exec(select(Knowledge).where(Knowledge.entity_id == ids["ivo"], Knowledge.fact_id == (
            event_fact(db, event.id).id if event else ""))).first()
        if error or row is None or not row.is_secret:
            fail(f"EY2: a participant's secret on the card gave {error!r}, row {row and row.is_secret}")


def check_ey3() -> None:
    wanted = {
        "EventEditor.svelte": ("draft.changes", "prefilledChanges(draft)", "!isPlayer(", "draft.newType.roles"),
        "Evenements.svelte": ("<EventEditor", "withChanges={isNew}"),
        "QueueCard.svelte": ("<EventEditor", "payloadFromDraft(eventDraft"),
        "eventDraft.svelte.js": ("export function draftFromPayload", "export function payloadFromDraft",
                                 "export async function prefilledChanges", "'/api/events/changes'",
                                 "state_changes: isNew ? changesBody(draft) : []"),
    }
    for name, needles in wanted.items():
        path = FRONT / name
        if not path.exists():
            fail(f"EY3: {name} is missing")
            continue
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                fail(f"EY3: {name} lacks {needle}")


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    ids = _fixture(engine)
    rules = (("EY1", lambda: check_ey1(engine, ids)), ("EY2", lambda: check_ey2(engine, ids)), ("EY3", check_ey3))
    for name, rule in rules:
        try:
            rule()
        except Exception as exc:  # a crash is that rule's failure, never a pass
            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: event_editor -- one editor for the journal, the review card and Lore; it pre-fills an event's "
          "changes from its type; the card approves its edits, scopes and secrets included")
    return 0


if __name__ == "__main__":
    sys.exit(main())
