"""G1 check for TICKET-0124 -- a draft fills the states its world asks for, and code decides what each answer names.

BRIEF-0124-G's rules (C-13, Gate (b) table 3 of LOT-0124), on a fixture
world: an active world « Brouillons » with a choice state « Rang » (holder
character, `F`/`E`, default `F`), an entity state « Esprit lié » (holder character, value
character), an entity state « Arme fétiche » (holder character, value item),
an integer state « Alerte » (holder location, default 0), the characters « Renard » and
« Maître Oren », a player character, a faction « Secte du Phoenix », a
location « Forge », and a second, inactive world holding one character.

DW1 -- `resolve_world_block` applies table 3 (fixture). One input per row,
   each giving exactly that row's output and, for a drop, exactly one note:
   a known state kept; an unknown or repeated state dropped; a choice
   matched through `normalize_surface` to its id and label, an unknown
   label dropped; an integer (int or string) kept, anything else dropped;
   an entity value resolved to its id, an unknown one with a creatable
   value type turned into an entity to create, one without dropped; a link
   kept, a link with an empty or non-social type dropped, a link naming no
   entity turned into an entity to create; `same_as` resolved, unresolved
   noted, `None` for a location; an entity to create kept, an existing name
   dropped, the derived ones before the model's, cut to three with a note.
DW2 -- `known_names_block` (fixture): the candidate ids first, then the
   non-player characters, the factions, the locations, each by name, no
   repeat, never a player character, at most 60 lines; `""` for a world
   with no entity.
DW3 -- the draft end to end (fixture, `entity_author.chat` stubbed): the
   user message asks `public.states (` and lists « Maître Oren » first; the
   system message (the seeded `pt-entity-generation` v1) carries the world
   frame and the state « Rang »; `draft["world"]` resolves `Rang` to `E`'s
   id, the link and `same_as` to Oren, « Ombre » to an entity to create.
   `generate_creation_draft` on a `creation` germ whose origin is « Kaelen »
   (`frère`) puts that link first.
   The literal `TO_CREATE_TYPES` equals `entity_extras.GERM_TYPES` and
   `routes/creator._ENTITY_CREATION_TYPES` (as sets).

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> str:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    return db_path


def _entity(db, world_id: str, entity_type: str, name: str, kind: str = "npc") -> str:
    from world_engine.models import Character, Entity, Location

    entity = Entity(world_id=world_id, type=entity_type, name=name)
    db.add(entity)
    db.flush()
    if entity_type == "character":
        db.add(Character(id=entity.id, world_id=world_id, character_type=kind))
    elif entity_type == "location":
        db.add(Location(id=entity.id))
    db.flush()
    return entity.id


def _fixture(engine) -> dict:
    from sqlmodel import Session

    from world_engine.attributes import attribute_view
    from world_engine.models import World
    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec, write_attribute_definition

    with Session(engine) as db:
        world = World(name="Brouillons", is_active=True)
        other = World(name="Ailleurs", is_active=False)
        empty = World(name="Vide", is_active=False)
        for row in (world, other, empty):
            db.add(row)
        db.flush()
        ids = {"world": world.id, "other": other.id, "empty": empty.id}

        def define(name, kind, holders, **extra):
            spec = DefinitionSpec(name=name, kind=kind, holder_types=holders, **extra)
            return write_attribute_definition(db, world_id=world.id, spec=spec).id

        ids["rang"] = define("Rang", "choice", ("character",), choices=(ChoiceSpec("F"), ChoiceSpec("E")), default="F")
        ids["esprit"] = define("Esprit lié", "entity", ("character",), value_types=("character",))
        ids["arme"] = define("Arme fétiche", "entity", ("character",), value_types=("item",))
        ids["alerte"] = define("Alerte", "integer", ("location",), default=0)
        ids["renard"] = _entity(db, world.id, "character", "Renard")
        ids["oren"] = _entity(db, world.id, "character", "Maître Oren")
        ids["pc"] = _entity(db, world.id, "character", "Aaron le joueur", kind="player")
        ids["secte"] = _entity(db, world.id, "faction", "Secte du Phoenix")
        ids["forge"] = _entity(db, world.id, "location", "Forge")
        ids["stranger"] = _entity(db, other.id, "character", "Étranger")
        db.commit()
        choices = {label: key for key, label in attribute_view(db, world.id, ids["rang"]).choices}
        ids["rang_e"] = choices["E"]
    return ids


def _resolve(engine, ids: dict, public_in: dict, entity_type: str = "character") -> tuple[dict, list]:
    from sqlmodel import Session

    from world_engine.draft_world import resolve_world_block

    notes: list[str] = []
    with Session(engine) as db:
        block = resolve_world_block(db, ids["world"], entity_type, public_in, "Kaelen", notes)
    return block, notes


def _dw1_cases(ids: dict) -> list[tuple]:
    """(row, entity_type, public_in, expected sub-block, expected note count)."""
    rang_e = {"key": ids["rang"], "name": "Rang", "kind": "choice", "value": ids["rang_e"], "label": "E"}
    esprit = {"key": ids["esprit"], "name": "Esprit lié", "kind": "entity",
              "value": ids["renard"], "label": "Renard"}
    oren_link = {"entity_id": ids["oren"], "name": "Maître Oren", "type": "élève", "note": "n"}

    def germ(name, entity_type="character", concept="", link_type=""):
        return {"name": name, "entity_type": entity_type, "concept": concept, "link_type": link_type}

    def ask(name, entity_type="character"):
        return {"name": name, "entity_type": entity_type, "concept": "", "link": ""}

    return [
        ("state kept", "character", {"states": [{"state": "rang", "value": "E"}]}, {"states": [rang_e]}, 0),
        ("state unknown", "character", {"states": [{"state": "Humeur", "value": "E"}]}, {"states": []}, 1),
        ("state repeated", "character",
         {"states": [{"state": "Rang", "value": "E"}, {"state": "Rang", "value": "F"}]}, {"states": [rang_e]}, 1),
        ("choice normalized", "character", {"states": [{"state": "Rang", "value": " e "}]}, {"states": [rang_e]}, 0),
        ("choice unknown", "character", {"states": [{"state": "Rang", "value": "Z"}]}, {"states": []}, 1),
        ("integer", "location", {"states": [{"state": "Alerte", "value": "4"}]},
         {"states": [{"key": ids["alerte"], "name": "Alerte", "kind": "integer", "value": 4, "label": "4"}]}, 0),
        ("integer invalid", "location", {"states": [{"state": "Alerte", "value": "beaucoup"}]}, {"states": []}, 1),
        ("entity resolved", "character", {"states": [{"state": "Esprit lié", "value": "renard"}]},
         {"states": [esprit]}, 0),
        ("entity to create", "character", {"states": [{"state": "Esprit lié", "value": "Loup gris"}]},
         {"states": [], "to_create": [germ("Loup gris", concept="Esprit lié de Kaelen", link_type="Esprit lié")]}, 0),
        ("entity dropped", "character", {"states": [{"state": "Arme fétiche", "value": "Lame"}]},
         {"states": [], "to_create": []}, 1),
        ("link kept", "character", {"links": [{"name": "maître oren", "type": "élève", "note": "n"}]},
         {"links": [oren_link]}, 0),
        ("link untyped", "character", {"links": [{"name": "Maître Oren", "type": ""}]}, {"links": []}, 1),
        ("link structural", "character", {"links": [{"name": "Forge", "type": "connects_to"}]}, {"links": []}, 1),
        ("link to create", "character", {"links": [{"name": "Ilse", "type": "sœur", "note": "aînée"}]},
         {"links": [], "to_create": [germ("Ilse", concept="aînée", link_type="sœur")]}, 0),
        ("same_as", "character", {"same_as": "Maître Oren"},
         {"same_as": {"entity_id": ids["oren"], "name": "Maître Oren"}}, 0),
        ("same_as player", "character", {"same_as": "Aaron le joueur"}, {"same_as": None}, 1),
        ("same_as location", "location", {"same_as": "Maître Oren"}, {"same_as": None}, 1),
        ("to_create kept", "character", {"to_create": [ask("Ombre")]}, {"to_create": [germ("Ombre")]}, 0),
        ("to_create exists", "character", {"to_create": [ask("Renard")]}, {"to_create": []}, 1),
        ("to_create order and cap", "character",
         {"links": [{"name": "Ilse", "type": "sœur"}], "to_create": [ask("Ombre"), ask("Brume", "location"),
                                                                     ask("Cendre", "faction")]},
         {"to_create": [germ("Ilse", link_type="sœur"), germ("Ombre"), germ("Brume", "location")]}, 1),
    ]


def check_dw1(engine, ids: dict) -> None:
    cases = _dw1_cases(ids)
    if not cases:
        fail("DW1 collected no case")
    for row, entity_type, public_in, expected, n_notes in cases:
        block, notes = _resolve(engine, ids, public_in, entity_type)
        got = {key: block[key] for key in expected}
        if got != expected:
            fail(f"DW1 {row}: expected {expected!r}, got {got!r}")
        if len(notes) != n_notes:
            fail(f"DW1 {row}: expected {n_notes} note(s), got {notes!r}")
    block, notes = _resolve(engine, ids, {"states": "Rang", "links": None, "to_create": [3]})
    if block != {"states": [], "links": [], "same_as": None, "to_create": []} or notes:
        fail(f"DW1 malformed inputs: {block!r}, notes {notes!r}")


def check_dw2(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.draft_world import MAX_KNOWN_NAMES, known_names_block
    from world_engine.models import World

    with Session(engine) as db:
        block = known_names_block(db, ids["world"], "character", (ids["forge"], ids["oren"]))
        expected = "\n".join([
            "Entités existantes que tu peux nommer (nom exact) :",
            "- Forge (lieu)", "- Maître Oren (personnage)", "- Renard (personnage)",
            "- Secte du Phoenix (faction)",
        ])
        if block != expected:
            fail(f"DW2 block:\n{block}")
        if known_names_block(db, ids["empty"], "character") != "":
            fail("DW2 a world with no entity lists something")
        crowd = World(name="Foule", is_active=False)
        db.add(crowd)
        db.flush()
        for n in range(MAX_KNOWN_NAMES + 5):
            _entity(db, crowd.id, "character", f"Passant {n:03d}")
        lines = known_names_block(db, crowd.id, "character").splitlines()
        if len(lines) != MAX_KNOWN_NAMES + 1:
            fail(f"DW2 a crowded world lists {len(lines) - 1} names")
        db.rollback()


def _stub_chat(calls: list):
    answer = json.dumps({
        "public": {"name": "Lame-Vive", "states": [{"state": "Rang", "value": "e"}],
                   "links": [{"name": "Maître Oren", "type": "élève", "note": ""}],
                   "same_as": "Maître Oren",
                   "to_create": [{"name": "Ombre", "entity_type": "character", "concept": "c", "link": "rival"}]},
        "secret": {},
    })

    def chat(messages, *args, **kwargs):
        calls.append(messages)
        return answer

    return chat


def _seed_template(engine) -> None:
    from sqlmodel import Session

    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import seed_pilot

    with Session(engine) as db:
        seed_pilot.upsert_prompt_template(
            db, "pt-entity-generation", world_id=None, name="Assistant de création d'entité",
            usage="entity_generation", system_prompt=seed_pilot.ENTITY_GENERATION_SYSTEM_PROMPT,
            user_template=seed_pilot.ENTITY_GENERATION_USER_TEMPLATE,
            variables=["entity_type", "type_fields", "brief"], destination="local",
        )
        db.commit()


def _dw3_draft(engine, ids: dict, calls: list) -> None:
    from sqlmodel import Session

    from world_engine import entity_author

    with Session(engine) as db:
        result = entity_author.generate_entity_draft(
            "character", "un professeur d'escrime", db, candidate_ids=(ids["oren"],))
    draft_calls = [c for c in calls if "Intention du créateur" in c[-1]["content"]]
    if not result.get("ok") or len(draft_calls) != 1:
        fail(f"DW3 the draft failed or called {len(draft_calls)} times: {result.get('error')}")
        return
    system, user = draft_calls[0][0]["content"], draft_calls[0][-1]["content"]
    header = "Entités existantes que tu peux nommer (nom exact) :\n"
    if "public.states (" not in user or header + "- Maître Oren (personnage)\n" not in user:
        fail(f"DW3 the user message lacks the world fields or Oren first:\n{user}")
    if "=== CADRE DU MONDE ===" not in system or "- Rang (un parmi : F, E" not in system:
        fail(f"DW3 the system message lacks the world frame:\n{system}")
    world = result["draft"].get("world", {})
    expected = {
        "states": [{"key": ids["rang"], "name": "Rang", "kind": "choice", "value": ids["rang_e"], "label": "E"}],
        "links": [{"entity_id": ids["oren"], "name": "Maître Oren", "type": "élève", "note": ""}],
        "same_as": {"entity_id": ids["oren"], "name": "Maître Oren"},
        "to_create": [{"name": "Ombre", "entity_type": "character", "concept": "c", "link_type": "rival"}],
    }
    if world != expected:
        fail(f"DW3 draft['world'] is {world!r}")


def _dw3_origin_link(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.cockpit.routes.creator import generate_creation_draft
    from world_engine.models import ProposedMutation

    with Session(engine) as db:
        kaelen = _entity(db, ids["world"], "character", "Kaelen")
        germ = ProposedMutation(
            world_id=ids["world"], source_type="creation", mutation_type="entity_creation",
            status="approved", proposed_by="creator_draft", rationale="r",
            payload={"entity_type": "character", "name": "Frère de Kaelen", "concept": "un frère",
                     "origin_entity_id": kaelen, "link_type": "frère"})
        db.add(germ)
        db.commit()
        answer = generate_creation_draft(germ.id, db)
    links = ((answer.get("draft") or {}).get("world") or {}).get("links") or []
    if not answer.get("ok") or not links or (links[0]["entity_id"], links[0]["type"]) != (kaelen, "frère"):
        fail(f"DW3 the creation germ's draft links are {links!r}")
    if len(links) != 2:
        fail(f"DW3 the origin link did not lead the model's link: {links!r}")


def check_dw3(engine, ids: dict) -> None:
    from world_engine import entity_author
    from world_engine.cockpit.crud.entity_extras import GERM_TYPES
    from world_engine.cockpit.routes.creator import _ENTITY_CREATION_TYPES
    from world_engine.draft_world import TO_CREATE_TYPES

    _seed_template(engine)
    calls: list = []
    real_chat = entity_author.chat
    entity_author.chat = _stub_chat(calls)
    try:
        _dw3_draft(engine, ids, calls)
        _dw3_origin_link(engine, ids)
    finally:
        entity_author.chat = real_chat
    if not (set(TO_CREATE_TYPES) == set(GERM_TYPES) == set(_ENTITY_CREATION_TYPES)) or not TO_CREATE_TYPES:
        fail(f"DW3 TO_CREATE_TYPES {TO_CREATE_TYPES} differs from GERM_TYPES or _ENTITY_CREATION_TYPES")


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    ids = _fixture(engine)
    rules = (("DW1", lambda: check_dw1(engine, ids)), ("DW2", lambda: check_dw2(engine, ids)),
             ("DW3", lambda: check_dw3(engine, ids)))
    for name, rule in rules:
        try:
            rule()
        except Exception as exc:  # a crash is that rule's failure, never a pass
            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: draft_world -- a draft is asked the states, links, same person and entities to create "
          "its world calls for, with the names it may cite; code resolves every state, link and name "
          "against the world's rows, turns an unknown name into an entity to create, caps them at three, "
          "and a creation germ's origin leads its links")
    return 0


if __name__ == "__main__":
    sys.exit(main())
