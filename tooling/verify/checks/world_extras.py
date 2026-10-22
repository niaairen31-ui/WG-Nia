"""G1 check for TICKET-0124 -- a create carries the states, links and germs the creator kept, all in one transaction or none.

BRIEF-0124-E's rules (C-09, C-10 of LOT-0124), the route functions of
`cockpit/crud/entities.py` called directly on a fixture world: an active
world, a character « Maître Oren », a choice state « Rang » (holder
character, `F`/`E`, default `F`), an entity state « Esprit lié » (holder
character, value character), a character « Renard » (its value), and a
second, inactive world holding one character.

EX1 -- the extras land (fixture). `create_entity` of a character « Kaelen »
   with two states (`Rang` = `E`, `Esprit lié` = Renard), one relation to
   Oren of type `élève` and two germs (« Ombre », and « Maître Oren », a
   name already active) writes two `attribute_value` rows for Kaelen and
   two `attribute_change` rows `kind="correction"`,
   `changed_by="creator_crud"`; one `relation` Kaelen -> Oren of type
   `élève`; one `proposed_mutation` `entity_creation`, `approved`,
   `source_type="creation"`, `proposed_by="creator_draft"`, with
   `pass_play_id`, `conversation_id` and `tick_id` all NULL, its payload's
   keys exactly C-10's draft germ and `origin_entity_id` Kaelen's id; the
   response's `world_extras.germs_skipped` names « Maître Oren ».
EX2 -- everything or nothing (fixture). Each of: a state key
   `sys:vital_status`; a relation of type `connects_to`; a relation to the
   inactive world's character; a germ of type `item` -- answers 422, and
   afterwards no entity of that request's name and no `attribute_value`,
   `relation` or `proposed_mutation` row was added.
EX3 -- create only (fixture). `update_entity` with a non-empty `states`
   answers 422 and writes nothing; a create without the three keys makes
   one entity and answers `world_extras` all zero.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]

FAILURES: list[str] = []
DRAFT_GERM_KEYS = {"entity_type", "name", "concept", "origin_entity_id", "link_type"}


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> str:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    return db_path


def _character(name: str, **extras):
    from world_engine.cockpit.crud.entities import EntityWriteBody

    return EntityWriteBody(entity={"type": "character", "name": name},
                           extension={"character_type": "npc"}, **extras)


def _fixture(engine) -> dict:
    from sqlmodel import Session

    from world_engine.attributes import attribute_view
    from world_engine.cockpit.crud.entities import create_entity
    from world_engine.models import Character, Entity, World
    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec, write_attribute_definition

    with Session(engine) as db:
        world = World(name="Extras", is_active=True)
        other = World(name="Ailleurs", is_active=False)
        db.add(world)
        db.add(other)
        db.flush()
        stranger = Entity(world_id=other.id, type="character", name="Étranger")
        db.add(stranger)
        db.flush()
        db.add(Character(id=stranger.id, world_id=other.id, character_type="npc"))
        rang = write_attribute_definition(db, world_id=world.id, spec=DefinitionSpec(
            name="Rang", kind="choice", holder_types=("character",),
            choices=(ChoiceSpec("F"), ChoiceSpec("E")), default="F"))
        esprit = write_attribute_definition(db, world_id=world.id, spec=DefinitionSpec(
            name="Esprit lié", kind="entity", holder_types=("character",), value_types=("character",)))
        db.commit()
        choices = dict((label, key) for key, label in attribute_view(db, world.id, rang.id).choices)
        ids = {"world": world.id, "stranger": stranger.id, "rang": rang.id, "esprit": esprit.id,
               "rang_e": choices["E"]}
        ids["oren"] = create_entity(_character("Maître Oren"), db)["id"]
        ids["renard"] = create_entity(_character("Renard"), db)["id"]
    return ids


def _count(db, model) -> int:
    from sqlmodel import func, select

    return db.exec(select(func.count()).select_from(model)).one()


def _counts(db) -> tuple[int, ...]:
    from world_engine.models import AttributeValue, ProposedMutation, Relation

    return tuple(_count(db, m) for m in (AttributeValue, Relation, ProposedMutation))


def _named(db, name: str) -> int:
    from sqlmodel import select

    from world_engine.models import Entity

    return len(db.exec(select(Entity).where(Entity.name == name)).all())


def check_ex1(engine, ids: dict) -> None:
    from sqlmodel import Session, select

    from world_engine.cockpit.crud.entities import create_entity
    from world_engine.models import AttributeChange, AttributeValue, ProposedMutation, Relation

    with Session(engine) as db:
        made = create_entity(_character(
            "Kaelen",
            states=[{"key": ids["rang"], "value": ids["rang_e"]}, {"key": ids["esprit"], "value": ids["renard"]}],
            relations=[{"other_entity_id": ids["oren"], "type": "élève", "notes": "n"}],
            germs=[{"name": "Ombre", "entity_type": "character", "concept": "c", "link_type": "frère"},
                   {"name": "Maître Oren", "entity_type": "character", "concept": "", "link_type": ""}],
        ), db)
        kaelen = made["id"]
        values = db.exec(select(AttributeValue).where(AttributeValue.entity_id == kaelen)).all()
        changes = db.exec(select(AttributeChange).where(
            AttributeChange.value_id.in_([v.id for v in values]))).all()
        if len(values) != 2 or len(changes) != 2 or any(
                (c.kind, c.changed_by) != ("correction", "creator_crud") for c in changes):
            fail(f"EX1: {len(values)} values and changes {[(c.kind, c.changed_by) for c in changes]}")
        links = db.exec(select(Relation).where(Relation.entity_a_id == kaelen)).all()
        if [(r.entity_b_id, r.type) for r in links] != [(ids["oren"], "élève")]:
            fail(f"EX1: Kaelen's relations are {[(r.entity_b_id, r.type) for r in links]}")
        germs = db.exec(select(ProposedMutation).where(ProposedMutation.proposed_by == "creator_draft")).all()
        if len(germs) != 1:
            fail(f"EX1: {len(germs)} creator_draft germs")
        for germ in germs:
            shape = (germ.mutation_type, germ.status, germ.source_type, germ.pass_play_id,
                     germ.conversation_id, germ.tick_id)
            if shape != ("entity_creation", "approved", "creation", None, None, None):
                fail(f"EX1: the germ row reads {shape}")
            payload = germ.payload if isinstance(germ.payload, dict) else {}
            if set(payload) != DRAFT_GERM_KEYS or payload.get("origin_entity_id") != kaelen:
                fail(f"EX1: the germ payload is {payload}")
        skipped = [g.get("name") for g in made.get("world_extras", {}).get("germs_skipped", [])]
        if skipped != ["Maître Oren"]:
            fail(f"EX1: germs_skipped names {skipped}")


def check_ex2(engine, ids: dict) -> None:
    from fastapi import HTTPException
    from sqlmodel import Session

    from world_engine.cockpit.crud.entities import create_entity

    cases = (
        ("Refus-sys", {"states": [{"key": "sys:vital_status", "value": "dead"}]}),
        ("Refus-carte", {"relations": [{"other_entity_id": ids["oren"], "type": "connects_to"}]}),
        ("Refus-monde", {"relations": [{"other_entity_id": ids["stranger"], "type": "ami"}]}),
        ("Refus-objet", {"germs": [{"name": "Lame", "entity_type": "item", "concept": "", "link_type": ""}]}),
    )
    with Session(engine) as db:
        for name, extras in cases:
            before = _counts(db)
            try:
                create_entity(_character(name, **extras), db)
                fail(f"EX2: {name} was accepted")
            except HTTPException as exc:
                if exc.status_code != 422:
                    fail(f"EX2: {name} answered {exc.status_code}")
            db.rollback()
            if _named(db, name) or _counts(db) != before:
                fail(f"EX2: {name} was refused after writing a row")


def check_ex3(engine, ids: dict) -> None:
    from fastapi import HTTPException
    from sqlmodel import Session

    from world_engine.cockpit.crud.entities import create_entity, update_entity

    with Session(engine) as db:
        before = _counts(db)
        body = _character("Renard", states=[{"key": ids["rang"], "value": ids["rang_e"]}])
        try:
            update_entity(ids["renard"], body, db)
            fail("EX3: update_entity accepted states")
        except HTTPException as exc:
            if exc.status_code != 422:
                fail(f"EX3: update_entity with states answered {exc.status_code}")
        db.rollback()
        if _counts(db) != before:
            fail("EX3: the refused update wrote a row")
        made = create_entity(_character("Sans-extras"), db)
        extras = made.get("world_extras")
        if _named(db, "Sans-extras") != 1 or extras != {"states": 0, "relations": 0, "germs": [],
                                                       "germs_skipped": []}:
            fail(f"EX3: a plain create answered world_extras {extras}")


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    ids = _fixture(engine)
    rules = (("EX1", lambda: check_ex1(engine, ids)), ("EX2", lambda: check_ex2(engine, ids)),
             ("EX3", lambda: check_ex3(engine, ids)))
    for name, rule in rules:
        try:
            rule()
        except Exception as exc:  # a crash is that rule's failure, never a pass
            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: world_extras -- a create writes the states, social links and ticked germs the creator "
          "kept in its own transaction, approved germs as creator_draft with their origin; any refusal "
          "is a 422 that leaves nothing; an update carries none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
