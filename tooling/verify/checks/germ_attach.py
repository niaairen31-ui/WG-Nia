"""G1 check for TICKET-0124 -- a germ says where it comes from, and can join an existing character instead of creating one.

BRIEF-0124-F's rules (C-10, C-11, C-12 of LOT-0124), on a fixture world:
three locations « Terrain d'entraînement », « Cour » and « Tour » linked
Terrain -- Cour -- Tour by `link_locations` (`connects_to`); at Terrain an
NPC « Maître des épées », an archived NPC « Dormant » and the player
character; at Cour an NPC « Voisin »; at Tour an NPC « Lointain »; a second
world holding one NPC « Étranger »; one session, batch and pass-play.

GA1 -- the Journée germ (E1). `emit_germs` over the pass-play declaring
   `Je vais à la forge. Je cherche un professeur d'escrime pour apprendre.`
   with one unmatched inferred person (`un professeur d'escrime`) anchored
   at Terrain: its payload's `source_sentence` is the second sentence and
   its `anchor_name` « Terrain d'entraînement ». A mention found in no
   sentence gives the declaration, 300 characters at most.
GA2 -- the composed brief (C-10). `_compose_entity_creation_brief` writes
   « Lieu : Terrain d'entraînement. » and « Mentionné ainsi : « ... » » for a
   new Journée payload; « Lieu : <name>. » and never the id for a pre-0124
   Journée payload (`anchor` == `candidate_location_id`); a tick payload's
   prose `anchor` as is; « Lié à <origin> (<link_type>). » for a draft germ.
GA3 -- the pending list, the candidates, attach (C-11, Gate (b) tables 4
   and 5). `list_pending_creations` labels a tick, a Journée, a draft and a
   conversation germ `tick`, `journee`, `creation`, `conversation` and
   carries `anchor_name`, `source_sentence`, `origin_entity_id`,
   `origin_name`, `link_type`. `germ_candidates` on the Terrain germ lists
   exactly « Maître des épées » (« au même lieu ») and « Voisin » (« lieu
   voisin »); a location germ lists nothing. `attach` answers 409 for a
   missing row, another mutation type, a proposed germ and a realized one;
   422 for a missing, archived, other-world or other-type entity; then a
   valid attach leaves the row `applied`, `target_table == "entity"`,
   `target_id` and `created_entity_id` the character, the note « rattaché à
   une entité existante », and no new `entity` row.
GA4 -- the « Germes » metric (C-12). `compute_metrics` over the fixture
   world: the `germs` metric's `Journée` group counts one attached, one
   realized in a new entity, one proposed; its `Brouillon` group one
   awaiting realization; a scope dated after today counts nothing.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile
from datetime import datetime, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[3]

FAILURES: list[str] = []
DECLARATION = "Je vais à la forge. Je cherche un professeur d'escrime pour apprendre."
SENTENCE = "Je cherche un professeur d'escrime pour apprendre."
PENDING_KEYS = {"anchor_name", "source_sentence", "origin_entity_id", "origin_name", "link_type"}


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> str:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    return db_path


def _place(db, world_id: str, name: str) -> str:
    from world_engine.models import Entity, Location

    entity = Entity(world_id=world_id, type="location", name=name)
    db.add(entity)
    db.flush()
    db.add(Location(id=entity.id))
    db.flush()
    return entity.id


def _person(db, world_id: str, name: str, location_id, kind: str = "npc", status: str = "active") -> str:
    from world_engine.models import Character, Entity

    entity = Entity(world_id=world_id, type="character", name=name, status=status)
    db.add(entity)
    db.flush()
    db.add(Character(id=entity.id, world_id=world_id, character_type=kind, current_location_id=location_id))
    db.flush()
    return entity.id


def _fixture(engine) -> dict:
    from sqlmodel import Session

    from world_engine.models import Session as SessionRow
    from world_engine.models import World
    from world_engine.spatial_author import link_locations
    from world_engine.writes.pipeline import write_batch, write_pass_play

    with Session(engine) as db:
        world = World(name="Germes", is_active=True)
        other = World(name="Ailleurs", is_active=False)
        db.add(world)
        db.add(other)
        db.flush()
        ids = {"world": world.id}
        ids["terrain"] = _place(db, world.id, "Terrain d'entraînement")
        ids["cour"] = _place(db, world.id, "Cour")
        ids["tour"] = _place(db, world.id, "Tour")
        for a, b in (("terrain", "cour"), ("cour", "tour")):
            link_locations(db, world_id=world.id, entity_a_id=ids[a], entity_b_id=ids[b], changed_by="creator_crud")
        ids["maitre"] = _person(db, world.id, "Maître des épées", ids["terrain"])
        ids["dormant"] = _person(db, world.id, "Dormant", ids["terrain"], status="archived")
        ids["pc"] = _person(db, world.id, "Le joueur", ids["terrain"], kind="player")
        ids["voisin"] = _person(db, world.id, "Voisin", ids["cour"])
        ids["lointain"] = _person(db, world.id, "Lointain", ids["tour"])
        ids["etranger"] = _person(db, other.id, "Étranger", None)
        session = SessionRow(world_id=world.id, number=1)
        db.add(session)
        db.flush()
        batch = write_batch(db, session_id=session.id, changed_by="creator_crud")
        db.add(batch)
        db.flush()
        pass_play = write_pass_play(db, batch_id=batch.id, session_id=session.id, character_id=ids["pc"],
                                    declared_action=DECLARATION)
        db.add(pass_play)
        db.commit()
        ids["pass_play"] = pass_play.id
    return ids


def _unmatched(surface_form: str, role_hint: str, location_id):
    from world_engine.day_concordance import UnmatchedMention
    from world_engine.day_extract import Mention

    return UnmatchedMention(
        mention=Mention(category="person", surface_form=surface_form, kind="inferred", role_hint=role_hint),
        rungs_tried=("occupation", "presence"), candidate_location_id=location_id)


def check_ga1(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.day_concordance import emit_germs
    from world_engine.models import PassPlay

    with Session(engine) as db:
        pass_play = db.get(PassPlay, ids["pass_play"])
        germs = emit_germs((_unmatched("un professeur d'escrime", "professeur d'escrime", ids["terrain"]),),
                           pass_play, db)
        if len(germs) != 1:
            fail(f"GA1: emit_germs made {len(germs)} germs, expected 1")
            return
        payload = germs[0].payload
        if payload.get("source_sentence") != SENTENCE:
            fail(f"GA1: source_sentence is {payload.get('source_sentence')!r}")
        if payload.get("anchor_name") != "Terrain d'entraînement":
            fail(f"GA1: anchor_name is {payload.get('anchor_name')!r}")
        long_declaration = "Je flâne au marché sans but précis " * 12
        stray = PassPlay(id="stray", character_id=ids["pc"], declared_action=long_declaration)
        others = emit_germs((_unmatched("un forgeron", "forgeron", None),), stray, db)
        sentence = others[0].payload.get("source_sentence") if others else None
        if sentence != long_declaration.strip()[:300] or len(sentence) > 300:
            fail(f"GA1: a mention found in no sentence gave {sentence!r}")
        ids["journee_payload"] = dict(payload)


def check_ga2(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.cockpit.routes.creator import _compose_entity_creation_brief as compose

    with Session(engine) as db:
        fresh = compose(ids["journee_payload"], db)
        if "Lieu : Terrain d'entraînement." not in fresh or f"Mentionné ainsi : « {SENTENCE} »." not in fresh:
            fail(f"GA2: a new Journée germ composes {fresh!r}")
        old = {"entity_type": "character", "name": "forgeron", "concept": "Rôle à pourvoir : forgeron.",
               "anchor": ids["terrain"], "candidate_location_id": ids["terrain"]}
        old_brief = compose(old, db)
        if "Lieu : Terrain d'entraînement." not in old_brief or ids["terrain"] in old_brief:
            fail(f"GA2: a pre-0124 Journée germ composes {old_brief!r}")
        tick = compose({"entity_type": "location", "name": "Gué", "anchor": "près du moulin"}, db)
        if "près du moulin." not in tick or "Lieu :" in tick:
            fail(f"GA2: a tick germ composes {tick!r}")
        draft = compose({"entity_type": "character", "name": "Ombre", "concept": "c",
                         "origin_entity_id": ids["maitre"], "link_type": "frère"}, db)
        if "Lié à Maître des épées (frère)." not in draft:
            fail(f"GA2: a draft germ composes {draft!r}")


def _germ(db, ids: dict, payload: dict, status: str = "approved", **fields) -> str:
    from world_engine.models import ProposedMutation

    fields.setdefault("source_type", "pass_play")
    mut = ProposedMutation(world_id=ids["world"], mutation_type=fields.pop("mutation_type", "entity_creation"),
                           payload=payload, status=status, proposed_by="local_ai", **fields)
    db.add(mut)
    db.flush()
    return mut.id


def _germs(engine, ids: dict) -> dict:
    from sqlmodel import Session

    journee = ids["journee_payload"]
    character = {"entity_type": "character", "name": "x", "concept": "c"}
    with Session(engine) as db:
        rows = {
            "journee": _germ(db, ids, dict(journee), pass_play_id=ids["pass_play"]),
            "tick": _germ(db, ids, {"entity_type": "location", "name": "Gué", "anchor": "près du moulin"},
                          source_type="world_tick", tick_id="tick-1"),
            "creation": _germ(db, ids, {**character, "origin_entity_id": ids["voisin"], "link_type": "frère"},
                              source_type="creation"),
            "conversation": _germ(db, ids, dict(character), source_type="conversation"),
            "proposed": _germ(db, ids, dict(journee), status="proposed", pass_play_id=ids["pass_play"]),
            "applied": _germ(db, ids, {**journee, "created_entity_id": ids["voisin"]}, status="applied",
                             pass_play_id=ids["pass_play"]),
            "realized": _germ(db, ids, {**journee, "created_entity_id": ids["voisin"]},
                              pass_play_id=ids["pass_play"]),
            "other_type": _germ(db, ids, dict(character), mutation_type="relation_change"),
        }
        db.commit()
    return rows


def _status(call) -> int:
    from fastapi import HTTPException

    try:
        call()
    except HTTPException as exc:
        return exc.status_code
    return 200


def check_ga3(engine, ids: dict, germs: dict) -> None:
    from sqlmodel import Session, func, select

    from world_engine.cockpit.routes.creator import (
        GermAttachBody, attach_germ, germ_candidates, list_pending_creations)
    from world_engine.models import Entity, ProposedMutation

    with Session(engine) as db:
        pending = {item["mutation_id"]: item for item in list_pending_creations(db)}
        for key in ("tick", "journee", "creation", "conversation"):
            item = pending.get(germs[key])
            if item is None or item["source"] != {"journee": "journee"}.get(key, key) or not PENDING_KEYS <= set(item):
                fail(f"GA3: the {key} germ is pending as {item}")
        if pending.get(germs["creation"], {}).get("origin_name") != "Voisin":
            fail("GA3: the draft germ's origin_name is not « Voisin »")
        listed = [(c["name"], c["reason"]) for c in germ_candidates(db, db.get(ProposedMutation, germs["journee"]))]
        if listed != [("Maître des épées", "au même lieu"), ("Voisin", "lieu voisin")]:
            fail(f"GA3: the Terrain germ's candidates are {listed}")
        if germ_candidates(db, db.get(ProposedMutation, germs["tick"])) != []:
            fail("GA3: a location germ has candidates")

    def attach(key_or_id: str, entity_id: str) -> int:
        with Session(engine) as db:
            return _status(lambda: attach_germ(germs.get(key_or_id, key_or_id), GermAttachBody(entity_id=entity_id), db))

    for key in ("missing-row", "other_type", "proposed", "realized"):
        if attach(key, ids["maitre"]) != 409:
            fail(f"GA3: attach on the {key} germ is not a 409")
    for label, entity_id in (("missing", "no-such-entity"), ("archived", ids["dormant"]),
                             ("other-world", ids["etranger"]), ("other-type", ids["terrain"])):
        if attach("journee", entity_id) != 422:
            fail(f"GA3: attach to the {label} entity is not a 422")
    with Session(engine) as db:
        before = db.exec(select(func.count()).select_from(Entity)).one()
    if attach("journee", ids["maitre"]) != 200:
        fail("GA3: a valid attach did not answer 200")
    with Session(engine) as db:
        mut = db.get(ProposedMutation, germs["journee"])
        after = db.exec(select(func.count()).select_from(Entity)).one()
        state = (mut.status, mut.target_table, mut.target_id, mut.payload.get("created_entity_id"))
        if state != ("applied", "entity", ids["maitre"], ids["maitre"]):
            fail(f"GA3: the attached germ is {state}")
        if "rattaché à une entité existante" not in (mut.creator_notes or ""):
            fail(f"GA3: the attached germ's notes are {mut.creator_notes!r}")
        if after != before:
            fail(f"GA3: attach changed the entity count {before} -> {after}")


def check_ga4(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.dashboard_metrics import Scope, compute_metrics

    def rows(scope: Scope) -> dict:
        with Session(engine) as db:
            metric = next(m for m in compute_metrics(db, scope) if m["key"] == "germs")
        return {(r["group"], r["label"]): r["value"] for r in metric["rows"]}

    counted = rows(Scope(world_ids=(ids["world"],)))
    expected = {("Journée", "Rattachés à une fiche existante"): 1, ("Journée", "Réalisés en nouvelle fiche"): 1,
                ("Journée", "Proposés"): 1, ("Brouillon", "En attente de réalisation"): 1}
    for key, value in expected.items():
        if counted.get(key) != value:
            fail(f"GA4: {key} counts {counted.get(key)}, expected {value}")
    later = rows(Scope(world_ids=(ids["world"],), since=datetime.now() + timedelta(days=2)))
    if later:
        fail(f"GA4: a scope after today counts {later}")


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    ids = _fixture(engine)
    state: dict = {}
    rules = (("GA1", lambda: check_ga1(engine, ids)), ("GA2", lambda: check_ga2(engine, ids)),
             ("GA3", lambda: check_ga3(engine, ids, state.setdefault("germs", _germs(engine, ids)))),
             ("GA4", lambda: check_ga4(engine, ids)))
    for name, rule in rules:
        try:
            rule()
        except Exception as exc:  # a crash is that rule's failure, never a pass
            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: germ_attach -- a Journée germ keeps its sentence and its place's name, the brief names the "
          "place, the pending list names the source, a germ lists the characters it could be and joins one "
          "without a new entity, and the Germes metric counts it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
