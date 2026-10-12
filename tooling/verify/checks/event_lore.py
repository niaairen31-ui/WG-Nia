"""G1 check for TICKET-0119 -- Lore declares events: in the writing panel's proposal, and by a button straight to the journal.

BRIEF-0119-G's rules (U1, G3 and M-c of the conditions series).

EL1 -- the prompt (static and fixture). The seed's Lore proposal texts hold
   each new fragment of `LORE_PROPOSAL_FRAGMENTS_0119` exactly once; the
   proposal head's variables (`LORE_PROPOSAL_VARIABLES`, the head of
   `LORE_WRITE_PROMPT_HEADS`) are exactly its user template's placeholders,
   `event_types` and `sortes` among them. `apply_ticket_0119_lore_prompt.py`,
   on a head holding the former texts and variables, writes one version
   equal to the seed's with its variables; a second run is unchanged; on a
   head the creator edited where a fragment stood, her edit is kept and the
   fragment reported.
EL2 -- the draft (fixture, the model call replaced). `draft_proposal`
   reads an event naming « Ouvrir » by code: its type, its participants by
   role -- a matched entity by its ref, a sorte of the world by id --, its
   place by ref, and its changes pre-filled on the matched door, by ref; an
   event proposing a type keeps `new_type`, its roles by name; an unknown
   code, an unknown role and a sorte the world lacks each leave a note, the
   event or the participant dropped.
EL3 -- the commit (fixture). A proposal creating « Cave » and holding an
   event whose participant, place and change name it by ref writes the
   event with « Cave »'s new id in its role and as its place, sets its
   « Ouvert » as a `changement` naming the event, and records the `event`,
   its `fact`, its `event_participant`, the `attribute_value` and the
   `attribute_change` against the entry; `list_entries` labels the event by
   its title. An event still carrying `new_type`, and an event whose change
   the writer refuses, each refuse the whole proposal: nothing is written.
EL4 -- the panel (static). `WritePanel.svelte` renders `<EventEditor` for
   the draft's events with `canPrefill={false}`, a proposed type's
   `<EventTypeForm` and « Créer ce type », and the « Déclarer un événement »
   button; `writePanel.svelte.js` exports `eventEntities`,
   `createProposedType`, `openDeclare` and `saveDeclared`, sends the events
   in the proposal (`events:`) and saves a declared event with
   `eventBodyFrom(`.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "apply_ticket_0119_lore_prompt.py"
LORE = ROOT / "frontend" / "src" / "lore"
HEAD = "pt-lore-statement-to-proposal"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> None:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))


# --- EL1 -----------------------------------------------------------------------

def _texts() -> dict[str, str]:
    import seed_pilot

    return {"system_prompt": seed_pilot.LORE_STATEMENT_TO_PROPOSAL_SYSTEM_PROMPT,
            "user_template": seed_pilot.LORE_STATEMENT_TO_PROPOSAL_USER_TEMPLATE}


def _former_texts() -> dict[str, str]:
    import seed_pilot

    texts = _texts()
    for field, old, new in seed_pilot.LORE_PROPOSAL_FRAGMENTS_0119:
        texts[field] = texts[field].replace(new, old)
    return texts


def _prompt_db(texts: dict[str, str]) -> str:
    from sqlalchemy import create_engine
    from sqlmodel import Session, SQLModel

    from world_engine.models import PromptTemplate
    from world_engine.writes.prompts import write_prompt_variables, write_prompt_version

    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "prompt.db")
    eng = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(eng)
    with Session(eng) as db:
        db.add(PromptTemplate(id=HEAD, name="lore", usage="lore_statement_to_proposal", world_id=None,
                              destination="local"))
        db.flush()
        write_prompt_variables(db, template_id=HEAD, variables=["facets", "entities", "facts", "statement",
                                                                 "answers"])
        write_prompt_version(db, template_id=HEAD, note="former", **texts)
        db.commit()
    eng.dispose()
    return db_path


def _run(db_path: str):
    from sqlalchemy import create_engine
    from sqlmodel import Session, select

    from world_engine.models import PromptTemplate, PromptVariable
    from world_engine.prompt_store import current_prompt

    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    result = subprocess.run([sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True,
                            cwd=str(ROOT), timeout=60)
    eng = create_engine(f"sqlite:///{db_path}")
    with Session(eng) as db:
        version = current_prompt(db, db.get(PromptTemplate, HEAD))
        state = (version.version_number, version.system_prompt, version.user_template,
                 set(db.exec(select(PromptVariable.name)).all()))
    eng.dispose()
    return result, state


def check_el1() -> None:
    import seed_pilot

    texts = _texts()
    fragments = seed_pilot.LORE_PROPOSAL_FRAGMENTS_0119
    if not fragments:
        fail("EL1: LORE_PROPOSAL_FRAGMENTS_0119 is empty")
    for field, _old, new in fragments:
        if texts[field].count(new) != 1:
            fail(f"EL1: the fragment {new[:40]!r} stands {texts[field].count(new)} time(s) in the seed's {field}")
    used = set(re.findall(r"\{([a-z_]+)\}", texts["user_template"]))
    head = next((h for h in seed_pilot.LORE_WRITE_PROMPT_HEADS if h["id"] == HEAD), {})
    if used != set(seed_pilot.LORE_PROPOSAL_VARIABLES) or set(head.get("variables", [])) != used \
            or not {"event_types", "sortes"} <= used:
        fail(f"EL1: variables {seed_pilot.LORE_PROPOSAL_VARIABLES}, head {head.get('variables')}, "
             f"template {sorted(used)}")
    seed = (texts["system_prompt"], texts["user_template"])
    result, state = _run(_prompt_db(_former_texts()))
    if result.returncode != 0 or state[0] != 2 or state[1:3] != seed \
            or state[3] != set(seed_pilot.LORE_PROPOSAL_VARIABLES):
        fail(f"EL1: the delivery gave v{state[0]}, seed text {state[1:3] == seed}, variables {state[3]}: "
             f"{result.stdout.strip()[-200:]} {result.stderr.strip()[-300:]}")
    db_path = _prompt_db(_former_texts())
    _run(db_path)
    again, state = _run(db_path)
    if again.returncode != 0 or "unchanged" not in again.stdout or state[0] != 2:
        fail(f"EL1: a second run: {again.stdout.strip()[-200:]}")
    edited = _former_texts()
    field, lost, _new = fragments[-1]
    edited[field] = edited[field].replace(lost, "(retouché à la main)")
    result, state = _run(_prompt_db(edited))
    if result.returncode != 0 or "fragment not found" not in result.stdout or "(retouché à la main)" not in state[2]:
        fail(f"EL1: an edited head gave v{state[0]}: {result.stdout.strip()[-300:]}")


# --- fixture -------------------------------------------------------------------

def _world(engine) -> dict:
    from sqlmodel import Session

    import seed_pilot
    from world_engine.attributes import attribute_view
    from world_engine.event_vocab import type_view
    from world_engine.models import Character, Entity, Location, PromptTemplate, World
    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec, write_attribute_definition
    from world_engine.writes.event_types import EffectSpec, EventTypeSpec, RoleSpec, write_event_type, write_sorte

    with Session(engine) as db:
        for head in seed_pilot.LORE_WRITE_PROMPT_HEADS:
            if db.get(PromptTemplate, head["id"]) is None:
                seed_pilot.upsert_prompt_template(db, **dict(head))
        world = World(name="Lore EL", is_active=True)
        db.add(world)
        db.flush()
        ids = {"world": world.id}
        for key, kind, name in (("millys", "character", "Millys"), ("porte", "location", "Porte Noire")):
            row = Entity(world_id=world.id, type=kind, name=name)
            db.add(row)
            db.flush()
            ids[key] = row.id
            db.add(Character(id=row.id, world_id=world.id, character_type="npc") if kind == "character"
                   else Location(id=row.id))
        ouvert = write_attribute_definition(db, world_id=world.id, spec=DefinitionSpec(
            name="Ouvert", kind="choice", holder_types=("location",),
            choices=(ChoiceSpec("non"), ChoiceSpec("oui")), default="non"))
        db.flush()
        ids["ouvert"] = ouvert.id
        ids["oui"] = {label: key for key, label in attribute_view(db, world.id, ouvert.id).choices}["oui"]
        ouvrir = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
            name="Ouvrir", roles=(RoleSpec("Ouvreur", ("character",)),
                                  RoleSpec("Cible", ("location",), accepts_sorte=True)),
            effects=(EffectSpec("Cible", ouvert.id, ids["oui"]),)))
        ids["ouvrir"] = ouvrir.id
        ids["ombre"] = write_sorte(db, world_id=world.id, name="Ombre").id
        for role in type_view(db, ouvrir.id).roles:
            ids[role.name] = role.id
        db.commit()
    return ids


class _Stub:
    def __init__(self, replies: list) -> None:
        self.replies = list(replies)

    def __call__(self, messages, **_kwargs):
        return json.dumps(self.replies.pop(0))


def check_el2(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine import lore_write_draft as lwd
    from world_engine.event_analysis import analysis_vocabulary

    with Session(engine) as db:
        code = analysis_vocabulary(db, ids["world"]).codes.code_of(ids["ouvrir"])
        reply = {"entities": [{"ref": "e1", "name": "Millys", "category": "person"},
                              {"ref": "e2", "name": "Porte Noire", "category": "place"}],
                 "facts": [], "memberships": [], "controls": [],
                 "events": [
                     {"event_type": code, "title": "Millys ouvre la Porte Noire", "place_ref": "e2",
                      "participants": [{"role": "Ouvreur", "ref": "e1"}, {"role": "Cible", "ref": "e2"},
                                       {"role": "Cible", "sorte": "Ombre"}, {"role": "Témoin", "ref": "e1"},
                                       {"role": "Cible", "sorte": "Brume"}]},
                     {"new_type": {"name": "Sceller", "roles": [{"name": "Scelleur", "for": ["character"]}]},
                      "title": "Le sceau", "participants": [{"role": "Scelleur", "ref": "e1"}]},
                     {"event_type": "t99", "title": "Rien"}]}
        original = lwd.chat
        lwd.chat = _Stub([reply])
        try:
            draft = lwd.draft_proposal(db, ids["world"], "Millys ouvre la Porte Noire.")
        finally:
            lwd.chat = original
    events = draft.get("events", [])
    first = events[0] if events else {}
    got = (first.get("type_id"), first.get("location_ref"),
           [(p["role_id"], p["entity_ref"], p["sorte_id"]) for p in first.get("participants", [])],
           first.get("state_changes"))
    want = (ids["ouvrir"], "e2", [(ids["Ouvreur"], "e1", None), (ids["Cible"], "e2", None),
                                  (ids["Cible"], None, ids["ombre"])],
            [{"entity_ref": "e2", "attribute": ids["ouvert"], "mode": "set", "value": ids["oui"]}])
    if len(events) != 2 or got != want:
        fail(f"EL2: the draft's events are {len(events)}, the first {got}")
    second = events[1] if len(events) > 1 else {}
    if not second.get("new_type") or [p["role"] for p in second.get("participants", [])] != ["Scelleur"]:
        fail(f"EL2: a proposed type's event is {second}")
    notes = " | ".join(draft.get("notes", []))
    for needle in ("t99", "Témoin", "Brume"):
        if needle not in notes:
            fail(f"EL2: no note names {needle}: {notes}")


def _counts(db) -> tuple[int, ...]:
    from sqlmodel import func, select

    from world_engine.models import AttributeChange, Entity, Event, LoreEntry

    return tuple(db.exec(select(func.count()).select_from(m)).one() for m in (Entity, Event, AttributeChange,
                                                                              LoreEntry))


def _creator(db):
    from world_engine.models import Entity, Location

    def create(name: str, entity_type: str):
        entity = Entity(world_id=_creator.world, type=entity_type, name=name)
        db.add(entity)
        db.flush()
        if entity_type == "location":
            db.add(Location(id=entity.id))
            db.flush()
        return entity
    return create


def _proposal(ids: dict, **event) -> dict:
    base = {"ref": "v1", "type_id": ids["ouvrir"], "title": "Millys ouvre la Cave", "location_ref": "e2",
            "participants": [{"role_id": ids["Ouvreur"], "entity_ref": "e1"},
                             {"role_id": ids["Cible"], "entity_ref": "e2"}],
            "state_changes": [{"entity_ref": "e2", "attribute": ids["ouvert"], "value": ids["oui"]}]}
    base.update(event)
    return {"statement": "Millys ouvre la Cave.", "entities": [
        {"ref": "e1", "action": "existing", "entity_id": ids["millys"]},
        {"ref": "e2", "action": "create", "name": "Cave", "type": "location"}],
        "facts": [], "memberships": [], "controls": [], "events": [base]}


def check_el3(engine, ids: dict) -> None:
    from sqlmodel import Session, select

    from world_engine import lore_write_apply as lwa
    from world_engine.attributes import attribute_view, current_value
    from world_engine.lore_write_read import list_entries
    from world_engine.models import AttributeChange, Entity, Event, EventParticipant, LoreEntryRow

    _creator.world = ids["world"]
    with Session(engine) as db:
        result = lwa.apply_proposal(db, ids["world"], _proposal(ids), _creator(db))
        db.commit()
        cave = db.exec(select(Entity).where(Entity.name == "Cave")).first()
        event = db.exec(select(Event).where(Event.title == "Millys ouvre la Cave")).first()
        roles = {(p.role_id, p.entity_id) for p in db.exec(select(EventParticipant).where(
            EventParticipant.event_id == (event.id if event else "")))}
        state = current_value(db, attribute_view(db, ids["world"], ids["ouvert"]), cave) if cave else None
        change = db.exec(select(AttributeChange).where(AttributeChange.event_id == (event.id if event else ""))).first()
        if event is None or cave is None or event.location_id != cave.id \
                or roles != {(ids["Ouvreur"], ids["millys"]), (ids["Cible"], cave.id)} \
                or state is None or state.raw != ids["oui"] or change is None or change.kind != "changement":
            fail(f"EL3: the commit wrote event {event}, roles {roles}, state {state}, change {change}")
        tables = set(db.exec(select(LoreEntryRow.row_table).where(LoreEntryRow.entry_id == result.entry_id)).all())
        if not {"event", "fact", "event_participant", "attribute_value", "attribute_change"} <= tables:
            fail(f"EL3: the entry records {sorted(tables)}")
        labels = [r["label"] for e in list_entries(db, ids["world"]) for r in e["rows"] if r["row_table"] == "event"]
        if labels != ["Millys ouvre la Cave"]:
            fail(f"EL3: the history labels the event {labels}")
        for label, bad in (("a proposed type", _proposal(ids, title="Autre", new_type={"name": "Sceller"})),
                           ("a refused change", _proposal(ids, title="Autre", state_changes=[
                               {"entity_ref": "e1", "attribute": ids["ouvert"], "value": ids["oui"]}]))):
            before = _counts(db)
            try:
                lwa.apply_proposal(db, ids["world"], bad, _creator(db))
                fail(f"EL3: {label} was not refused")
            except lwa.ProposalError:
                pass
            db.rollback()
            if _counts(db) != before:
                fail(f"EL3: {label} was refused but wrote rows")


def check_el4() -> None:
    wanted = {
        "WritePanel.svelte": ("<EventEditor draft={ev}", "canPrefill={false}", "<EventTypeForm",
                              "Créer ce type", "Déclarer un événement"),
        "writePanel.svelte.js": ("export function eventEntities", "export function createProposedType",
                                 "export function openDeclare", "export async function saveDeclared",
                                 "events: (draft.events || [])", "eventBodyFrom(draft, true)"),
    }
    for name, needles in wanted.items():
        path = LORE / name
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        if not text:
            fail(f"EL4: {name} is missing")
        for needle in needles:
            if needle not in text:
                fail(f"EL4: {name} lacks {needle}")


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    try:
        check_el1()
    except Exception as exc:  # a crash is a failure, never a pass
        fail(f"EL1: crashed -- {type(exc).__name__}: {exc}")
    try:
        ids = _world(engine)
    except Exception as exc:  # a crash is a failure, never a pass
        fail(f"EL2-EL3: the fixture crashed -- {type(exc).__name__}: {exc}")
        ids = None
    for name, rule in (("EL2", check_el2), ("EL3", check_el3)):
        if ids is None:
            break
        try:
            rule(engine, ids)
        except Exception as exc:  # a crash is a failure, never a pass
            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
    check_el4()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: event_lore -- Lore's proposal reads the world's event types and declares events by type, role and "
          "ref, its changes pre-filled; a proposed type is created before the commit; the commit writes each event "
          "through the journal's writer, every row recorded, all or nothing; a button declares one straight to "
          "the journal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
