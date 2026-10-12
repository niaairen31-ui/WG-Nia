"""G1 check for TICKET-0114 -- Play's analyzer proposes typed events, and may propose their type, approved with the event.

BRIEF-0114-H's rules.

EH1 -- the prompt (static and fixture). The seed's analysis texts hold each
   new fragment of `CONVERSATION_ANALYSIS_FRAGMENTS_0114` exactly once and
   no longer the untyped `event_creation` shape; the head's variables
   (`CONVERSATION_ANALYSIS_VARIABLES`) are exactly the user template's
   placeholders and `AnalysisVocabulary.prompt_values` fills the two new
   ones. `apply_ticket_0114_analysis_prompt.py`, on a head holding the
   former texts and variables, writes one version equal to the seed's with
   its variables; a second run is unchanged; on a head the creator edited
   where a fragment stood, her edit is kept and the fragment reported.
EH2 -- reading the proposal (fixture). `typed_payload` of an
   `event_creation` naming a type by code keeps its id and name, each
   participant by role -- an entity the role accepts, a sorte of the world
   by id, a sorte it lacks by name --, and the quantity when the type
   counts one; it leaves out a participant whose role the type lacks, an
   entity of another type or world, and a quantity the type does not
   count; an unknown code drops the proposal; a proposed type (`new_type`)
   is kept cleaned, its roles named, no id; a proposed type the writer
   refuses drops it; a `new_type` named as a type the world has is that
   type; a payload naming no type is returned unchanged.
EH3 -- applying (fixture). An approved proposal with a proposed type and a
   sorte the world lacks writes the type, the sorte and the event with its
   participants in their roles; a second one proposing the same type uses
   it, no second type; one whose proposed type the writer refuses answers
   an `event_creation:` error and, its savepoint rolled back, writes
   nothing.
EH4 -- wiring (static). `analyze_transcript` reads `analysis_vocabulary`
   once and hands it to the model call and to the builder;
   `QueueCard.svelte` shows a typed event (`eventSummary`) and a proposed
   type's badge.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import ast
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"
SCRIPT = ROOT / "scripts" / "apply_ticket_0114_analysis_prompt.py"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> None:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))


# --- EH1 -----------------------------------------------------------------------

def _former_texts() -> dict[str, str]:
    import seed_pilot

    texts = {"system_prompt": seed_pilot.CONVERSATION_ANALYSIS_SYSTEM_PROMPT,
             "user_template": seed_pilot.CONVERSATION_ANALYSIS_USER_TEMPLATE}
    for field, old, new in seed_pilot.CONVERSATION_ANALYSIS_FRAGMENTS_0114:
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
        db.add(PromptTemplate(id="pt-conversation-analysis", name="analysis", usage="conversation_analysis",
                              world_id=None, destination="local"))
        db.flush()
        write_prompt_variables(db, template_id="pt-conversation-analysis",
                               variables=["transcript", "injected_context"])
        write_prompt_version(db, template_id="pt-conversation-analysis", note="former", **texts)
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
        version = current_prompt(db, db.get(PromptTemplate, "pt-conversation-analysis"))
        state = (version.version_number, version.system_prompt, version.user_template,
                 set(db.exec(select(PromptVariable.name)).all()))
    eng.dispose()
    return result, state


def check_eh1() -> None:
    import seed_pilot

    from world_engine.event_analysis import AnalysisVocabulary
    from world_engine.fact_refs import CodedRefs

    texts = {"system_prompt": seed_pilot.CONVERSATION_ANALYSIS_SYSTEM_PROMPT,
             "user_template": seed_pilot.CONVERSATION_ANALYSIS_USER_TEMPLATE}
    fragments = seed_pilot.CONVERSATION_ANALYSIS_FRAGMENTS_0114
    if not fragments:
        fail("EH1: CONVERSATION_ANALYSIS_FRAGMENTS_0114 is empty")
    for field, old, new in fragments:
        if texts[field].count(new) != 1:
            fail(f"EH1: the fragment {new[:40]!r} stands {texts[field].count(new)} time(s) in the seed's {field}")
    if '"type":"social|political|other","involved_entities"' in texts["system_prompt"]:
        fail("EH1: the seed still teaches the untyped event_creation shape")
    used = set(re.findall(r"\{([a-z_]+)\}", texts["user_template"]))
    values = AnalysisVocabulary(codes=CodedRefs(codes={}, lines=())).prompt_values()
    if used != set(seed_pilot.CONVERSATION_ANALYSIS_VARIABLES) or not set(values) <= used:
        fail(f"EH1: variables {seed_pilot.CONVERSATION_ANALYSIS_VARIABLES}, template {sorted(used)}, "
             f"values {sorted(values)}")
    seed = (texts["system_prompt"], texts["user_template"])
    result, state = _run(_prompt_db(_former_texts()))
    if result.returncode != 0 or state[0] != 2 or state[1:3] != seed \
            or state[3] != set(seed_pilot.CONVERSATION_ANALYSIS_VARIABLES):
        fail(f"EH1: the delivery gave v{state[0]}, seed text {state[1:3] == seed}, variables {state[3]}: "
             f"{result.stdout.strip()[-200:]} {result.stderr.strip()[-300:]}")
    db_path = _prompt_db(_former_texts())
    again, state = _run(db_path)
    again, state = _run(db_path)
    if again.returncode != 0 or "unchanged" not in again.stdout or state[0] != 2:
        fail(f"EH1: a second run: {again.stdout.strip()[-200:]}")
    edited = _former_texts()
    _field, lost, _new = fragments[0]
    edited["system_prompt"] = edited["system_prompt"].replace(lost, "(retouché à la main)")
    result, state = _run(_prompt_db(edited))
    if result.returncode != 0 or "fragment not found" not in result.stdout or "(retouché à la main)" not in state[1] \
            or "{event_types}" not in state[2]:
        fail(f"EH1: an edited head gave v{state[0]}: {result.stdout.strip()[-300:]}")


# --- fixture -------------------------------------------------------------------

def _world(engine) -> dict:
    from sqlmodel import Session

    from world_engine.event_vocab import type_view
    from world_engine.models import Character, Entity, Location, World
    from world_engine.writes.event_types import EventTypeSpec, RoleSpec, write_event_type, write_sorte

    with Session(engine) as db:
        ids = {}
        for key, name in (("world", "Analyse EH"), ("other", "Ailleurs")):
            world = World(name=name, is_active=key == "world")
            db.add(world)
            db.flush()
            ids[key] = world.id
        for key, kind, name, world in (("foret", "location", "Forêt", "world"), ("mira", "character", "Mira", "world"),
                                       ("brakk", "character", "Brakk", "world"),
                                       ("etranger", "character", "Étranger", "other")):
            row = Entity(world_id=ids[world], type=kind, name=name)
            db.add(row)
            db.flush()
            ids[key] = row.id
            db.add(Location(id=row.id) if kind == "location" else Character(id=row.id, world_id=ids[world],
                                                                            character_type="npc"))
        ids["loup"] = write_sorte(db, world_id=ids["world"], name="Loup").id
        chasse = write_event_type(db, world_id=ids["world"], spec=EventTypeSpec(
            name="Chasse", counts_quantity=True,
            roles=(RoleSpec("Chasseur", ("character",)), RoleSpec("Proie", ("character",), accepts_sorte=True))))
        duel = write_event_type(db, world_id=ids["world"], spec=EventTypeSpec(
            name="Duel", roles=(RoleSpec("Adversaire", ("character",)),)))
        ids.update(chasse=chasse.id, duel=duel.id)
        ids["chasseur"], ids["proie"] = (r.id for r in type_view(db, chasse.id).roles)
        db.commit()
    return ids


def _new_type(**over) -> dict:
    raw = {"name": "Piéger", "domain": "criminal", "quantity": True,
           "roles": [{"name": "piégeur", "for": ["character"]}, {"name": "proie", "for": ["character"],
                                                                 "sorte": True}]}
    raw.update(over)
    return raw


# --- EH2 -----------------------------------------------------------------------

def check_eh2(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.event_analysis import analysis_vocabulary, typed_payload

    with Session(engine) as db:
        vocab = analysis_vocabulary(db, ids["world"])
        if "t1 — Chasse (rôles : Chasseur — personnage ; Proie — personnage ou une sorte ; compte une quantité)" \
                not in vocab.codes.lines or vocab.prompt_values()["sortes"] != "Loup":
            fail(f"EH2: the vocabulary reads {vocab.codes.lines}, {vocab.prompt_values()}")
        out = typed_payload(db, ids["world"], {
            "title": "Mira chasse", "event_type": "t1", "quantity": 3, "location_id": ids["foret"],
            "participants": [{"role": "chasseur", "entity_id": ids["mira"]}, {"role": "proie", "sorte": "loup"},
                             {"role": "proie", "sorte": "Ours"}, {"role": "témoin", "entity_id": ids["brakk"]},
                             {"role": "chasseur", "entity_id": ids["foret"]},
                             {"role": "chasseur", "entity_id": ids["etranger"]}]}, vocab)
        got = [(p["role_id"], p["entity_id"], p["sorte_id"], p["sorte_name"]) for p in (out or {}).get(
            "participants", [])]
        if out is None or out["type_id"] != ids["chasse"] or out["type_name"] != "Chasse" or out["quantity"] != 3 \
                or out["location_id"] != ids["foret"] or got != [
                    (ids["chasseur"], ids["mira"], None, None), (ids["proie"], None, ids["loup"], "Loup"),
                    (ids["proie"], None, None, "Ours")]:
            fail(f"EH2: a typed proposal reads {out}")
        duel = typed_payload(db, ids["world"], {"title": "Duel", "event_type": "t2", "quantity": 4,
                                                "participants": []}, vocab)
        if duel is None or duel["quantity"] is not None:
            fail(f"EH2: a type that counts nothing kept {duel}")
        if typed_payload(db, ids["world"], {"title": "?", "event_type": "t9"}, vocab) is not None:
            fail("EH2: an unknown type code was kept")
        new = typed_payload(db, ids["world"], {"title": "Mira piège", "new_type": _new_type(), "participants": [
            {"role": "Piégeur", "entity_id": ids["mira"]}, {"role": "proie", "sorte": "Lapin"}]}, vocab)
        if new is None or new["type_id"] is not None or new.get("new_type", {}).get("name") != "Piéger" \
                or [(p["role_id"], p["role"]) for p in new["participants"]] != [(None, "piégeur"), (None, "proie")]:
            fail(f"EH2: a proposed type reads {new}")
        if typed_payload(db, ids["world"], {"title": "?", "new_type": _new_type(roles=[{"name": "x",
                                                                                         "for": ["dragon"]}])},
                         vocab) is not None:
            fail("EH2: a proposed type the writer refuses was kept")
        same = typed_payload(db, ids["world"], {"title": "?", "new_type": _new_type(name="chasse")}, vocab)
        if same is None or same["type_id"] != ids["chasse"] or "new_type" in same:
            fail(f"EH2: a proposed type the world has reads {same}")
        untyped = {"title": "La fête", "type": "social", "involved_entities": [ids["mira"]]}
        if typed_payload(db, ids["world"], dict(untyped), vocab) != untyped:
            fail("EH2: an untyped payload was changed")


# --- EH3 -----------------------------------------------------------------------

def check_eh3(engine, ids: dict) -> None:
    from sqlmodel import Session, func, select

    from world_engine.cockpit.routes.mutations import _apply_mutation
    from world_engine.event_analysis import analysis_vocabulary, typed_payload
    from world_engine.event_vocab import type_view
    from world_engine.models import Event, EventParticipant, EventSorte, EventType, ProposedMutation

    def mutation(db, payload):
        mut = ProposedMutation(world_id=ids["world"], source_type="conversation", mutation_type="event_creation",
                               target_table="event", payload=payload, status="approved")
        db.add(mut)
        db.flush()
        return mut

    def count(db, model):
        return db.exec(select(func.count()).select_from(model)).one()

    with Session(engine) as db:
        vocab = analysis_vocabulary(db, ids["world"])
        payload = typed_payload(db, ids["world"], {"title": "Mira piège trois lapins", "new_type": _new_type(),
                                                   "quantity": 3, "participants": [
            {"role": "piégeur", "entity_id": ids["mira"]}, {"role": "proie", "sorte": "Lapin"}]}, vocab)
        with db.begin_nested():
            error = _apply_mutation(mutation(db, payload), db)
        db.commit()
        event = db.exec(select(Event).where(Event.title == "Mira piège trois lapins")).first()
        view = type_view(db, event.type_id) if event else None
        rows = {(p.role_id, p.entity_id, p.sorte_id) for p in db.exec(select(EventParticipant).where(
            EventParticipant.event_id == (event.id if event else "")))}
        lapin = db.exec(select(EventSorte).where(EventSorte.name == "Lapin")).first()
        roles = {r.name: r.id for r in view.roles} if view else {}
        if error or view is None or view.name != "Piéger" or lapin is None or event.quantity != 3 \
                or rows != {(roles.get("piégeur"), ids["mira"], None), (roles.get("proie"), None, lapin.id)}:
            fail(f"EH3: a proposed type gave {error!r}, type {view and view.name}, participants {rows}")
        types = count(db, EventType)
        with db.begin_nested():
            again = _apply_mutation(mutation(db, dict(payload, title="Brakk piège")), db)
        db.commit()
        if again or count(db, EventType) != types:
            fail(f"EH3: the same proposed type twice gave {again!r}, {count(db, EventType) - types} more type(s)")
        before = (count(db, EventType), count(db, Event), count(db, EventSorte))
        broken = dict(payload, title="Cassé", new_type=dict(payload["new_type"], name="Braconner",
                                                            roles=[{"name": "x", "entity_types": ["dragon"]}]))
        broken["participants"] = [{"role": "proie", "sorte_name": "Renard"}]
        answer = None
        try:
            with db.begin_nested():
                answer = _apply_mutation(mutation(db, broken), db)
                if answer:
                    raise RuntimeError(answer)
        except RuntimeError:
            pass
        db.commit()
        if not (answer or "").startswith("event_creation:") \
                or (count(db, EventType), count(db, Event), count(db, EventSorte)) != before:
            fail(f"EH3: a refused proposed type answered {answer!r} and wrote "
                 f"{(count(db, EventType), count(db, Event), count(db, EventSorte))} from {before}")


# --- EH4 -----------------------------------------------------------------------

def _function(path: pathlib.Path, name: str) -> str:
    source = path.read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(source, node) or ""
    return ""


def check_eh4() -> None:
    body = _function(SRC / "analyzer_transcript.py", "analyze_transcript")
    if body.count("analysis_vocabulary(db, world_id)") != 1 or "model, host, vocab)" not in body \
            or "covered_keys, vocab," not in body:
        fail("EH4: analyze_transcript does not hand one vocabulary to the call and the builder")
    card = (ROOT / "frontend" / "src" / "creation" / "QueueCard.svelte").read_text(encoding="utf-8")
    for needle in ("function eventSummary(m)", "nouveau type — validé avec l'événement"):
        if needle not in card:
            fail(f"EH4: QueueCard.svelte lacks {needle!r}")


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    check_eh1()
    ids = _world(engine)
    for check in (check_eh2, check_eh3):
        try:
            check(engine, ids)
        except Exception as exc:  # a crash is a failure, never a pass
            fail(f"{check.__name__}: crashed: {type(exc).__name__}: {exc}")
    check_eh4()
    for msg in FAILURES:
        print(f"FAIL: {msg}")
    if FAILURES:
        return 1
    print("PASS: event_analyzer -- Play's analyzer reads the world's event types by code and its sortes, proposes "
          "an event by type and role, fail-closed, and may propose its type, written with the event in one "
          "savepoint; its prompt is delivered fragment by fragment")
    return 0


if __name__ == "__main__":
    sys.exit(main())
