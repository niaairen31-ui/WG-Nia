"""G1 check for TICKET-0119 -- the world tick proposes typed events: the world's types by code, participants by role and name; never a new type.

BRIEF-0119-E's rules (A1, M-c and R1 of the conditions series).

ET1 -- the prompt (static and fixture). The seed's tick events texts hold
   each new fragment of `WORLD_TICK_EVENTS_FRAGMENTS_0119` exactly once; the
   head's variables (`WORLD_TICK_EVENTS_VARIABLES`) are exactly the user
   template's placeholders, `event_types` and `sortes` among them.
   `apply_ticket_0119_tick_prompt.py`, on a head holding the former texts
   and variables, writes one version equal to the seed's with its
   variables; a second run is unchanged; on a head the creator edited where
   a fragment stood, her edit is kept and the fragment reported.
ET2 -- the call (fixture). `_tick_call_scope_model`, its model call
   replaced, sends a user message holding the coded type line of « Chasse »
   and the sorte « Loup », and no placeholder left.
ET3 -- typed items (fixture, `_normalize_scope_event` on a location
   scope). An item naming « Chasse » by code, its hunter by name (a roster
   member) and its prey by sorte, with a quantity, becomes a typed
   `event_creation`: the type's id, the hunter's entity id in his role, the
   sorte by id, the quantity, the scope as its place, and the type's
   effects pre-filled in `state_changes`; a participant named by an active
   entity outside the roster is kept; a name nobody bears is left out with
   a note; an unknown code drops the item with a note.
ET4 -- never a new type (fixture). An item with a `new_type` and no
   `event_type` keeps the former untyped shape (`type`,
   `knowledge_status`, `involved_entities`) with a note -- no `new_type` in
   its payload; an item with neither keeps the untyped shape too.
ET5 -- wiring (static). `tick._tick_scope_setup` reads
   `analysis_vocabulary` once into `setup["vocab"]`, which the scope call and
   the normalizer receive; `tick_events.py` imports nothing from `writes`.

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
SCRIPT = ROOT / "scripts" / "apply_ticket_0119_tick_prompt.py"
HEAD = "pt-world-tick-events"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> None:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))


# --- ET1 -----------------------------------------------------------------------

def _texts() -> dict[str, str]:
    import seed_pilot

    return {"system_prompt": seed_pilot.WORLD_TICK_EVENTS_SYSTEM_PROMPT,
            "user_template": seed_pilot.WORLD_TICK_EVENTS_USER_TEMPLATE}


def _former_texts() -> dict[str, str]:
    import seed_pilot

    texts = _texts()
    for field, old, new in seed_pilot.WORLD_TICK_EVENTS_FRAGMENTS_0119:
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
        db.add(PromptTemplate(id=HEAD, name="tick events", usage="world_tick_events", world_id=None,
                              destination="local"))
        db.flush()
        write_prompt_variables(db, template_id=HEAD, variables=["event_context", "interval_label"])
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


def check_et1() -> None:
    import seed_pilot

    texts = _texts()
    fragments = seed_pilot.WORLD_TICK_EVENTS_FRAGMENTS_0119
    if not fragments:
        fail("ET1: WORLD_TICK_EVENTS_FRAGMENTS_0119 is empty")
    for field, _old, new in fragments:
        if texts[field].count(new) != 1:
            fail(f"ET1: the fragment {new[:40]!r} stands {texts[field].count(new)} time(s) in the seed's {field}")
    used = set(re.findall(r"\{([a-z_]+)\}", texts["user_template"]))
    if used != set(seed_pilot.WORLD_TICK_EVENTS_VARIABLES) or not {"event_types", "sortes"} <= used:
        fail(f"ET1: variables {seed_pilot.WORLD_TICK_EVENTS_VARIABLES}, template {sorted(used)}")
    seed = (texts["system_prompt"], texts["user_template"])
    result, state = _run(_prompt_db(_former_texts()))
    if result.returncode != 0 or state[0] != 2 or state[1:3] != seed \
            or state[3] != set(seed_pilot.WORLD_TICK_EVENTS_VARIABLES):
        fail(f"ET1: the delivery gave v{state[0]}, seed text {state[1:3] == seed}, variables {state[3]}: "
             f"{result.stdout.strip()[-200:]} {result.stderr.strip()[-300:]}")
    db_path = _prompt_db(_former_texts())
    _run(db_path)
    again, state = _run(db_path)
    if again.returncode != 0 or "unchanged" not in again.stdout or state[0] != 2:
        fail(f"ET1: a second run: {again.stdout.strip()[-200:]}")
    edited = _former_texts()
    _field, lost, _new = fragments[0]
    edited["system_prompt"] = edited["system_prompt"].replace(lost, "(retouché à la main)")
    result, state = _run(_prompt_db(edited))
    if result.returncode != 0 or "fragment not found" not in result.stdout or "(retouché à la main)" not in state[1] \
            or "{event_types}" not in state[2]:
        fail(f"ET1: an edited head gave v{state[0]}: {result.stdout.strip()[-300:]}")


# --- fixture -------------------------------------------------------------------

def _world(engine) -> dict:
    from sqlmodel import Session

    from world_engine.event_vocab import type_view
    from world_engine.models import Character, Entity, Location, PromptTemplate, World
    from world_engine.writes.attributes import DefinitionSpec, write_attribute_definition
    from world_engine.writes.event_types import EffectSpec, EventTypeSpec, RoleSpec, write_event_type, write_sorte
    from world_engine.writes.prompts import write_prompt_variables, write_prompt_version

    import seed_pilot

    with Session(engine) as db:
        world = World(name="Tick", is_active=True)
        db.add(world)
        db.flush()
        ids = {"world": world.id}
        for key, kind, name in (("foret", "location", "Forêt"), ("brakk", "character", "Brakk"),
                                ("ysa", "character", "Ysa")):
            row = Entity(world_id=world.id, type=kind, name=name)
            db.add(row)
            db.flush()
            ids[key] = row.id
            db.add(Character(id=row.id, world_id=world.id, character_type="npc", current_location_id=None)
                   if kind == "character" else Location(id=row.id))
        fatigue = write_attribute_definition(db, world_id=world.id, spec=DefinitionSpec(
            name="Fatigue", kind="integer", holder_types=("character",), default=0))
        chasse = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
            name="Chasse", counts_quantity=True,
            roles=(RoleSpec("Chasseur", ("character",)), RoleSpec("Proie", ("character",), accepts_sorte=True)),
            effects=(EffectSpec("Chasseur", fatigue.id, 1, "add"),)))
        ids["loup"] = write_sorte(db, world_id=world.id, name="Loup").id
        ids["chasse"], ids["fatigue"] = chasse.id, fatigue.id
        for role in type_view(db, chasse.id).roles:
            ids[role.name] = role.id
        db.add(PromptTemplate(id=HEAD, name="tick events", usage="world_tick_events", world_id=None,
                              destination="local"))
        db.flush()
        write_prompt_variables(db, template_id=HEAD, variables=list(seed_pilot.WORLD_TICK_EVENTS_VARIABLES))
        write_prompt_version(db, template_id=HEAD, note="seed", **_texts())
        db.commit()
    return ids


def check_et2(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine import ollama_client, tick
    from world_engine.event_analysis import analysis_vocabulary

    sent: list = []

    def fake_chat(messages, **_kwargs):
        sent.append(messages)
        return "[]"

    real = tick.ollama_client.chat
    tick.ollama_client.chat = fake_chat
    try:
        with Session(engine) as db:
            vocab = analysis_vocabulary(db, ids["world"])
            tick._tick_call_scope_model(db, "BRIEF", "trois jours", ollama_client.DEFAULT_MODEL, "h", vocab)
    finally:
        tick.ollama_client.chat = real
    user = sent[0][1]["content"] if sent else ""
    if "Chasse" not in user or "Loup" not in user or "t1" not in user or re.search(r"\{[a-z_]+\}", user):
        fail(f"ET2: the tick's user message is {user[-300:]!r}")


def _normalize(db, ids: dict, item: dict, notes: list):
    from world_engine.event_analysis import analysis_vocabulary
    from world_engine.tick_normalize import _normalize_scope_event

    return _normalize_scope_event(
        item, scope_type="location", scope_id=ids["foret"], roster={"brakk": ids["brakk"]}, locations={},
        agendas_index={}, actives={"brakk": ids["brakk"], "ysa": ids["ysa"]}, db=db, notes=notes,
        vocab=analysis_vocabulary(db, ids["world"]), world_id=ids["world"])


def check_et3(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.event_analysis import analysis_vocabulary

    with Session(engine) as db:
        code = analysis_vocabulary(db, ids["world"]).codes.code_of(ids["chasse"])
        notes: list = []
        item = {"mutation_type": "event_creation", "rationale": "r", "payload": {
            "title": "La chasse", "event_type": code, "quantity": 3, "participants": [
                {"role": "Chasseur", "name": "Brakk"}, {"role": "Chasseur", "name": "Ysa"},
                {"role": "Chasseur", "name": "Personne"}, {"role": "Proie", "sorte": "Loup"}]}}
        out = _normalize(db, ids, item, notes)
        payload = out["payload"] if out else {}
        got = (payload.get("type_id"), payload.get("quantity"), payload.get("location_id"),
               [(p["role_id"], p["entity_id"], p["sorte_id"]) for p in payload.get("participants", [])],
               payload.get("state_changes"))
        want = (ids["chasse"], 3, ids["foret"],
                [(ids["Chasseur"], ids["brakk"], None), (ids["Chasseur"], ids["ysa"], None),
                 (ids["Proie"], None, ids["loup"])],
                [{"entity_id": ids["brakk"], "attribute": ids["fatigue"], "mode": "add", "value": 1},
                 {"entity_id": ids["ysa"], "attribute": ids["fatigue"], "mode": "add", "value": 1}])
        if out is None or out["mutation_type"] != "event_creation" or got != want:
            fail(f"ET3: a typed item gave {got}")
        if not any("Personne" in n for n in notes):
            fail(f"ET3: an unresolved name left no note: {notes}")
        notes = []
        dropped = _normalize(db, ids, {"mutation_type": "event_creation", "payload": {
            "title": "Inconnue", "event_type": "t99", "participants": []}}, notes)
        if dropped is not None or not any("t99" in n for n in notes):
            fail(f"ET3: an unknown code gave {dropped}, notes {notes}")


def check_et4(engine, ids: dict) -> None:
    from sqlmodel import Session

    with Session(engine) as db:
        notes: list = []
        out = _normalize(db, ids, {"mutation_type": "event_creation", "payload": {
            "title": "Un pacte", "new_type": {"name": "Pacte", "roles": [{"name": "Partie", "for": ["character"]}]},
            "type": "political", "knowledge_status": "secret", "involved_entities": ["Brakk"]}}, notes)
        payload = out["payload"] if out else {}
        if "new_type" in payload or payload.get("type") != "political" or payload.get("involved_entities") != [
                ids["brakk"]] or not any("A1" in n for n in notes):
            fail(f"ET4: a new type gave {payload}, notes {notes}")
        plain = _normalize(db, ids, {"mutation_type": "event_creation", "payload": {
            "title": "Une rumeur", "type": "social", "knowledge_status": "public", "involved_entities": []}}, [])
        if not plain or plain["payload"].get("type") != "social" or "type_id" in plain["payload"]:
            fail(f"ET4: an untyped item gave {plain}")


def check_et5() -> None:
    source = (SRC / "tick.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    setup = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_tick_scope_setup"),
                 None)
    body = ast.get_source_segment(source, setup) if setup else ""
    if body.count('setup["vocab"] = analysis_vocabulary(db, setup["world_id"])') != 1:
        fail("ET5: _tick_scope_setup does not read the vocabulary once")
    if 'setup.get("vocab")' not in source or source.count('setup.get("vocab")') < 2:
        fail("ET5: the scope call and the normalizer do not both receive setup['vocab']")
    events = ast.parse((SRC / "tick_events.py").read_text(encoding="utf-8"))
    for node in ast.walk(events):
        if isinstance(node, ast.ImportFrom) and node.module and "writes" in node.module:
            fail(f"ET5: tick_events.py imports {node.module}")


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    try:
        check_et1()
    except Exception as exc:  # a crash is a failure, never a pass
        fail(f"ET1: crashed -- {type(exc).__name__}: {exc}")
    try:
        ids = _world(engine)
    except Exception as exc:  # a crash is a failure, never a pass
        fail(f"ET2-ET4: the fixture crashed -- {type(exc).__name__}: {exc}")
        ids = None
    for name, rule in (("ET2", check_et2), ("ET3", check_et3), ("ET4", check_et4)):
        if ids is None:
            break
        try:
            rule(engine, ids)
        except Exception as exc:  # a crash is a failure, never a pass
            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
    check_et5()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: event_tick -- the world tick shows the model the world's event types and sortes, reads its events "
          "by code, role and name into typed proposals with their changes pre-filled, never proposes a new type, "
          "and its prompt is delivered fragment by fragment")
    return 0


if __name__ == "__main__":
    sys.exit(main())
