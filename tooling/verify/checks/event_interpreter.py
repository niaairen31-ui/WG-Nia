"""G1 check for TICKET-0114 -- the condition interpreter reads the world's event types and sortes and writes an event leaf.

BRIEF-0114-F's rules (EI1-EI4), then BRIEF-0114-G's (EI5-EI7).

EI1 -- the prompt (static and import). `CODE_LISTS["event"]` is `t`; the
   head declares `event_types` and `sortes`, its template uses exactly its
   variables and `prompt_values` gives exactly those; the seed's system
   prompt holds the « ÉVÉNEMENTS. » paragraph and no longer calls « ce qui
   s'est passé » unsupported; the event note names « Vocabulaire du monde »;
   `apply_ticket_0114_condition_prompt.py` imports `apply_fragments` from
   the 0113 script and embeds no prompt text.
EI2 -- context and round trip (fixture). The `t` list shows each active
   type with its roles, what each takes and whether it counts a quantity;
   the prompt's `sortes` names the world's sortes. A current tree holding
   an event leaf -- a role, a place, `since` step, a sorte filter and an
   entity filter -- encodes with the role and the sorte by name, the place
   and the entity by `e` code, and reads back (`read_answer`, `validate`)
   to the same tree.
EI3 -- reading (fixture). An unknown role, an unknown sorte and an unknown
   window are each an error naming the right ones; a filter naming an
   ambiguous person waits (`needs_choice`) and the creator's pick binds it.
EI4 -- interpret and delivery (fixture, stubbed model). A model answer
   with an event leaf is `proposed` as the tree it says, the message
   carrying the `t` list. On a head holding the 0113 text and variables,
   the delivery script writes one new version equal to the seed's, its
   variables the seed's; a second run is unchanged.
EI5 -- proposals (fixture, stubbed model). An answer proposing a type in
   `define_events` and two sortes in `define_sortes`, its leaf naming them
   by ref, waits (`needs_choice`) with two proposals -- the type `v1` with
   its cleaned definition and the types whose name is near, the sorte
   `o1` --, the sorte the world already has (« loup ») bound silently to
   it; nothing is written. A proposal the writer refuses (a role of an
   unknown entity type) is an error; a leaf naming an unknown ref is one.
EI6 -- binding (fixture). Once the creator created the type and the sorte,
   `resolve` with their ids gives the tree, the role names read on the
   type; a ref without a pick, or a pick that is no type of the world, is a
   `ValueError`; a near type picked whose roles lack the leaf's is
   `refused`, the error naming its roles. Through the routes, the journal
   keeps the proposals (`vocabulary`) and `resolve` reads them back.
EI7 -- the card (static). `ConditionInterpreter.svelte` shows a card per
   proposal with `EventTypeForm` and `createVocab`;
   `conditionInterpreter.svelte.js` creates through `/api/event-types` and
   `/api/event-sortes` and sends each card's pick as a binding.

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
SCRIPT = ROOT / "scripts" / "apply_ticket_0114_condition_prompt.py"
EVENT_FRAGMENT_MARKS = ("ÉVÉNEMENTS.", "{event_types}", "define_events")

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> None:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))


class _Stub:
    def __init__(self, replies):
        self.replies, self.messages = list(replies), []

    def __call__(self, messages, **kwargs):
        self.messages.append(messages)
        reply = self.replies.pop(0)
        return reply if isinstance(reply, str) else json.dumps(reply)


# --- EI1 -----------------------------------------------------------------------

def check_ei1() -> None:
    import seed_pilot

    from world_engine import condition_interpreter as ci
    from world_engine.fact_refs import CodedRefs

    if ci.CODE_LISTS.get("event") != "t":
        fail(f"EI1: CODE_LISTS is {ci.CODE_LISTS}")
    head = seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS[0]
    used = set(re.findall(r"\{([a-z_]+)\}", head["user_template"]))
    empty = CodedRefs(codes={}, lines=())
    keys = set(ci.prompt_values(ci.InterpreterContext(entity_lines=(), lists={k: empty for k in "efqsat"},
                                                      current=None), "eligibility", "x", []))
    if not {"event_types", "sortes"} <= used or used != set(head["variables"]) or used != keys:
        fail(f"EI1: variables {sorted(head['variables'])}, template {sorted(used)}, values {sorted(keys)}")
    system = seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT
    if "ÉVÉNEMENTS. La forme event" not in system or "ce qui s'est passé" in system:
        fail("EI1: the seed's system prompt does not teach the event form, or still calls it unsupported")
    if "Vocabulaire du monde" not in ci.UNSUPPORTED_NOTES_FR["event"]:
        fail(f"EI1: the event note reads {ci.UNSUPPORTED_NOTES_FR['event']!r}")
    script = SCRIPT.read_text(encoding="utf-8") if SCRIPT.exists() else ""
    if "from apply_ticket_0113_condition_prompt import HEAD, apply_fragments" not in script \
            or "Tu " in script or "ÉVÉNEMENTS." in script:
        fail("EI1: the delivery script does not reuse the 0113 delivery, or embeds prompt text")


# --- fixture -------------------------------------------------------------------

def _world(engine) -> dict:
    import seed_pilot
    from sqlmodel import Session

    from world_engine.event_vocab import type_view
    from world_engine.models import Character, Entity, Location, PromptTemplate, World
    from world_engine.writes.event_types import EventTypeSpec, RoleSpec, write_event_type, write_sorte

    with Session(engine) as db:
        world = World(name="Interprète EI", is_active=False)
        db.add(world)
        db.flush()
        ids = {"world": world.id}
        for key, kind, name in (("foret", "location", "Forêt"), ("brakk", "character", "Brakk"),
                                ("ysa1", "character", "Ysa"), ("ysa2", "character", "Ysa")):
            row = Entity(world_id=world.id, type=kind, name=name)
            db.add(row)
            db.flush()
            ids[key] = row.id
            db.add(Location(id=row.id) if kind == "location" else Character(id=row.id, world_id=world.id,
                                                                            character_type="npc"))
        ids["loup"] = write_sorte(db, world_id=world.id, name="Loup").id
        ids["ours"] = write_sorte(db, world_id=world.id, name="Ours").id
        chasse = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
            name="Chasse", counts_quantity=True,
            roles=(RoleSpec("Chasseur", ("character",)), RoleSpec("Proie", ("character",), accepts_sorte=True),
                   RoleSpec("Témoin", ("character",)))))
        ids["chasse"] = chasse.id
        view = type_view(db, chasse.id)
        ids["chasseur"], ids["proie"], ids["temoin"] = (r.id for r in view.roles)
        for head in seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS:
            if db.get(PromptTemplate, head["id"]) is None:
                seed_pilot.upsert_prompt_template(db, **dict(head))
        db.commit()
    return ids


def _leaf(ids: dict, **kw) -> dict:
    base = {"op": "leaf", "type": "event", "subject_role": "doer", "subject_entity_id": None,
            "target_entity_id": ids["foret"], "target_key": ids["chasse"], "threshold": 3,
            "value": ids["chasseur"], "since": "step",
            "filters": [{"role_id": ids["proie"], "entity_id": None, "sorte_id": ids["loup"]},
                        {"role_id": ids["temoin"], "entity_id": ids["brakk"], "sorte_id": None}]}
    base.update(kw)
    return base


def _model_leaf(**kw) -> dict:
    base = {"op": "leaf", "form": "event", "subject": "doer", "target": {"code": "t1"}, "value": "chasseur",
            "threshold": 3, "place": {"name": "Forêt", "kind": "place"}, "since": "step",
            "with": [{"role": "proie", "sorte": "loup"}, {"role": "Témoin", "name": "Brakk", "kind": "person"}]}
    base.update(kw)
    return base


# --- EI2 -----------------------------------------------------------------------

def check_ei2(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine import condition_interpreter as ci
    from world_engine.conditions import node_from_dict, node_to_dict

    with Session(engine) as db:
        tree = node_from_dict({"op": "all", "children": [_leaf(ids)]})
        ctx = ci.build_context(db, ids["world"], "Il a chassé", tree)
        lines = " | ".join(ctx.lists["t"].lines)
        want = "t1 — Chasse (rôles : Chasseur — personnage ; Proie — personnage ou une sorte ; Témoin — " \
               "personnage ; compte une quantité)"
        if want not in lines:
            fail(f"EI2: the t list reads {lines!r}")
        if ci.prompt_values(ctx, "completion", "x", [])["sortes"] != "Loup, Ours":
            fail(f"EI2: sortes reads {ci.prompt_values(ctx, 'completion', 'x', [])['sortes']!r}")
        leaf = ctx.current["children"][0] if ctx.current else {}
        if leaf.get("value") != "Chasseur" or leaf.get("since") != "step" or leaf.get("target") != {"code": "t1"} \
                or leaf.get("with", [{}])[0] != {"role": "Proie", "sorte": "Loup"} \
                or "code" not in (leaf.get("with") or [{}, {}])[1] or "code" not in (leaf.get("place") or {}):
            fail(f"EI2: the leaf encodes as {leaf}")
        reading = ci.read_answer(db, ids["world"], ctx.current, ctx)
        back, errors = ci.validate(db, ids["world"], reading.pending) if not reading.errors \
            else (None, reading.errors)
        if errors or node_to_dict(back) != node_to_dict(tree):
            fail(f"EI2: the tree reads back as {node_to_dict(back)} ({errors})")


# --- EI3 -----------------------------------------------------------------------

def check_ei3(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine import condition_interpreter as ci
    from world_engine.conditions import node_to_dict

    with Session(engine) as db:
        ctx = ci.build_context(db, ids["world"], "x", None)
        for what, raw, needle in (
            ("an unknown role", _model_leaf(value="pisteur"), "rôles : Chasseur, Proie, Témoin"),
            ("an unknown sorte", _model_leaf(**{"with": [{"role": "proie", "sorte": "dragon"}]}),
             "sortes : Loup, Ours"),
            ("an unknown window", _model_leaf(since="jadis"), "fenêtre inconnue"),
        ):
            reading = ci.read_answer(db, ids["world"], {"op": "all", "children": [raw]}, ctx)
            if not any(needle in e for e in reading.errors):
                fail(f"EI3: {what} gave {reading.errors}")
        raw = _model_leaf(**{"with": [{"role": "témoin", "name": "Ysa", "kind": "person"}]})
        stub, original = _Stub([{"condition": {"op": "all", "children": [raw]}, "unsupported": []}]), ci.chat
        ci.chat = stub
        try:
            result = ci.interpret(db, ids["world"], "completion", "Ysa l'a vu", None, [])
        finally:
            ci.chat = original
        ysa = next((m for m in result.mentions if m["name"] == "Ysa"), None)
        if result.outcome != "needs_choice" or ysa is None or ysa["status"] != "ambiguous":
            fail(f"EI3: an ambiguous witness gave {result.outcome}, {result.mentions}")
            return
        bound = ci.resolve(db, ids["world"], result.pending, result.mentions, [], {ysa["ref"]: ids["ysa2"]})
        leaf = node_to_dict(bound.tree)["children"][0] if bound.tree else {}
        if bound.outcome != "proposed" or leaf.get("filters") != [
                {"role_id": ids["temoin"], "entity_id": ids["ysa2"], "sorte_id": None}]:
            fail(f"EI3: the pick gave {bound.outcome}, {leaf}, {bound.errors}")


# --- EI4 -----------------------------------------------------------------------

def check_ei4(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine import condition_interpreter as ci
    from world_engine.conditions import node_to_dict

    with Session(engine) as db:
        stub, original = _Stub([{"condition": {"op": "all", "children": [_model_leaf()]},
                                 "unsupported": []}]), ci.chat
        ci.chat = stub
        try:
            result = ci.interpret(db, ids["world"], "completion", "A chassé 3 loups devant Brakk", None, [])
        finally:
            ci.chat = original
        got = node_to_dict(result.tree)
        if result.outcome != "proposed" or got != {"op": "all", "children": [_leaf(ids)]}:
            fail(f"EI4: interpret gave {result.outcome}, {got}, {result.errors}")
        sent = json.dumps(stub.messages, ensure_ascii=False)
        if "t1 — Chasse" not in sent or "Loup, Ours" not in sent:
            fail("EI4: the message does not carry the t list and the sortes")
    _check_delivery()


def _prompt_db() -> str:
    import seed_pilot
    from sqlalchemy import create_engine
    from sqlmodel import Session, SQLModel

    from world_engine.models import PromptTemplate
    from world_engine.writes.prompts import write_prompt_variables, write_prompt_version

    head = seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS[0]
    texts = {"system_prompt": seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT_0112,
             "user_template": seed_pilot.CONDITION_INTERPRET_USER_TEMPLATE_0112}
    for field, old, new in seed_pilot.CONDITION_INTERPRET_FRAGMENTS:
        if not any(mark in new for mark in EVENT_FRAGMENT_MARKS):
            texts[field] = texts[field].replace(old, new)
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "prompt.db")
    eng = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(eng)
    with Session(eng) as db:
        db.add(PromptTemplate(id=head["id"], name=head["name"], usage=head["usage"], world_id=None,
                              destination=head["destination"]))
        db.flush()
        write_prompt_variables(db, template_id=head["id"], variables=[
            v for v in head["variables"] if v not in ("event_types", "sortes")])
        write_prompt_version(db, template_id=head["id"], note="0113", **texts)
        db.commit()
    eng.dispose()
    return db_path


def _check_delivery() -> None:
    import seed_pilot
    from sqlalchemy import create_engine
    from sqlmodel import Session, select

    from world_engine.models import PromptTemplate, PromptVariable
    from world_engine.prompt_store import current_prompt

    db_path = _prompt_db()
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    runs = [subprocess.run([sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True,
                           cwd=str(ROOT), timeout=60) for _ in range(2)]
    eng = create_engine(f"sqlite:///{db_path}")
    with Session(eng) as db:
        version = current_prompt(db, db.get(PromptTemplate, "pt-condition-interpret"))
        names = set(db.exec(select(PromptVariable.name)).all())
        state = (version.version_number, version.system_prompt, version.user_template)
    eng.dispose()
    if runs[0].returncode != 0 or state != (2, seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT,
                                            seed_pilot.CONDITION_INTERPRET_USER_TEMPLATE) \
            or not {"event_types", "sortes"} <= names:
        fail(f"EI4: the delivery gave v{state[0]}, seed text {state[1:] == (seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT, seed_pilot.CONDITION_INTERPRET_USER_TEMPLATE)}: "
             f"{runs[0].stdout.strip()[-200:]} {runs[0].stderr.strip()[-200:]}")
    if runs[1].returncode != 0 or "unchanged" not in runs[1].stdout:
        fail(f"EI4: a second run: {runs[1].stdout.strip()[-200:]}")


# --- EI5 / EI6 -----------------------------------------------------------------

def _proposing_answer(**leaf) -> dict:
    raw = _model_leaf(target={"define": "d1"}, value="piégeur", place=None,
                      **{"with": [{"role": "proie", "sorte": {"define": "s1"}}]})
    raw.update(leaf)
    return {"condition": {"op": "all", "children": [raw]}, "unsupported": [],
            "define_events": [{"ref": "d1", "name": "Chasses", "domain": "nope", "quantity": True,
                               "roles": [{"name": "Piégeur", "for": ["character"]},
                                         {"name": "Proie", "for": ["character"], "sorte": True}]}],
            "define_sortes": [{"ref": "s1", "name": "Lapin"}, {"ref": "s2", "name": "loup"}]}


def _interpret(ci, db, ids, answer):
    stub, original = _Stub([answer, answer]), ci.chat
    ci.chat = stub
    try:
        return ci.interpret(db, ids["world"], "completion", "A piégé des lapins", None, [])
    finally:
        ci.chat = original


def check_ei5(engine, ids: dict) -> None:
    from sqlmodel import Session, func, select

    from world_engine import condition_interpreter as ci
    from world_engine.models import EventSorte, EventType

    with Session(engine) as db:
        before = (db.exec(select(func.count()).select_from(EventType)).one(),
                  db.exec(select(func.count()).select_from(EventSorte)).one())
        result = _interpret(ci, db, ids, _proposing_answer(**{"with": [
            {"role": "proie", "sorte": {"define": "s1"}}, {"role": "Piégeur", "sorte": {"define": "s2"}}]}))
        kinds = [(v["ref"], v["kind"]) for v in result.vocabulary]
        piege = result.vocabulary[0] if result.vocabulary else {}
        if result.outcome != "needs_choice" or kinds != [("v1", "type"), ("o1", "sorte")] \
                or piege.get("definition", {}).get("domain") != "other" \
                or [r["name"] for r in piege.get("definition", {}).get("roles", [])] != ["Piégeur", "Proie"] \
                or "Chasse" not in [n["name"] for n in piege.get("near", [])]:
            fail(f"EI5: the proposals read {result.outcome}, {result.vocabulary}, {result.errors}")
        leaf = result.pending["children"][0] if result.pending else {}
        if leaf.get("type_define") != "v1" or leaf.get("role_name") != "piégeur" \
                or [f.get("sorte_define") or f.get("sorte_id") for f in leaf.get("filters", [])] != ["o1", ids["loup"]]:
            fail(f"EI5: the pending leaf is {leaf}")
        after = (db.exec(select(func.count()).select_from(EventType)).one(),
                 db.exec(select(func.count()).select_from(EventSorte)).one())
        if after != before:
            fail(f"EI5: reading the proposals wrote {before} -> {after}")
        bad = _proposing_answer()
        bad["define_events"][0]["roles"][0]["for"] = ["dragon"]
        refused = _interpret(ci, db, ids, bad)
        if refused.outcome != "refused" or not any("Chasses" in e for e in refused.errors):
            fail(f"EI5: a broken proposal gave {refused.outcome}, {refused.errors}")
        unknown = _interpret(ci, db, ids, _proposing_answer(target={"define": "d9"}))
        if not any("d9" in e for e in unknown.errors):
            fail(f"EI5: an unknown ref gave {unknown.errors}")
        db.rollback()


def check_ei6(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine import condition_interpreter as ci
    from world_engine.conditions import node_to_dict
    from world_engine.event_vocab import type_view
    from world_engine.writes.event_types import EventTypeSpec, RoleSpec, write_event_type, write_sorte

    with Session(engine) as db:
        result = _interpret(ci, db, ids, _proposing_answer())
        created = write_event_type(db, world_id=ids["world"], spec=EventTypeSpec(
            name="Chasses", counts_quantity=True,
            roles=(RoleSpec("Piégeur", ("character",)), RoleSpec("Proie", ("character",), accepts_sorte=True))))
        lapin = write_sorte(db, world_id=ids["world"], name="Lapin").id
        roles = {r.name: r.id for r in type_view(db, created.id).roles}
        args = (db, ids["world"], result.pending, result.mentions, [])
        bound = ci.resolve(*args, {"v1": created.id, "o1": lapin}, (), (), tuple(result.vocabulary))
        leaf = node_to_dict(bound.tree)["children"][0] if bound.tree else {}
        if bound.outcome != "proposed" or leaf.get("target_key") != created.id or leaf.get("value") != roles["Piégeur"] \
                or leaf.get("filters") != [{"role_id": roles["Proie"], "entity_id": None, "sorte_id": lapin}]:
            fail(f"EI6: binding gave {bound.outcome}, {leaf}, {bound.errors}")
        for what, picks in (("no pick", {"o1": lapin}), ("a foreign pick", {"v1": ids["loup"], "o1": lapin})):
            try:
                ci.resolve(*args, picks, (), (), tuple(result.vocabulary))
                fail(f"EI6: {what} was accepted")
            except ValueError:
                pass
        near = ci.resolve(*args, {"v1": ids["chasse"], "o1": lapin}, (), (), tuple(result.vocabulary))
        if near.outcome != "refused" or not any("Chasseur, Proie, Témoin" in e for e in near.errors):
            fail(f"EI6: a near type without the role gave {near.outcome}, {near.errors}")
        db.rollback()
    _check_routes(engine, ids)


def _check_routes(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine import condition_interpreter as ci
    from world_engine.cockpit.routes import conditions as routes
    from world_engine.models import ConditionDraft, World
    from world_engine.writes.event_types import EventTypeSpec, RoleSpec, write_event_type, write_sorte

    with Session(engine) as db:
        world = db.get(World, ids["world"])
        world.is_active = True
        db.add(world)
        db.commit()
        stub, original = _Stub([_proposing_answer()]), ci.chat
        ci.chat = stub
        try:
            answer = routes.interpret(routes.InterpretBody(instruction="A piégé des lapins", role="completion"),
                                      db=db)
        finally:
            ci.chat = original
        stored = db.get(ConditionDraft, answer["draft_id"]).payload.get("vocabulary") or []
        if [v["ref"] for v in answer.get("vocabulary", [])] != ["v1", "o1"] or len(stored) != 2:
            fail(f"EI6: the route answered {answer.get('vocabulary')}, the journal keeps {stored}")
            return
        created = write_event_type(db, world_id=ids["world"], spec=EventTypeSpec(
            name="Chasses", roles=(RoleSpec("Piégeur", ("character",)),
                                            RoleSpec("Proie", ("character",), accepts_sorte=True)))).id
        lapin = write_sorte(db, world_id=ids["world"], name="Lapin").id
        db.commit()
        bound = routes.resolve(answer["draft_id"], routes.ResolveBody(bindings={"v1": created, "o1": lapin}), db=db)
        if bound["outcome"] != "proposed" or not bound["view"]:
            fail(f"EI6: the resolve route gave {bound['outcome']}, {bound['errors']}")


# --- EI7 -----------------------------------------------------------------------

def check_ei7() -> None:
    front = ROOT / "frontend" / "src" / "creation"
    wants = {
        "ConditionInterpreter.svelte": ("<EventTypeForm", "createVocab(card)", "s.vocab"),
        "conditionInterpreter.svelte.js": ("'/api/event-types'", "'/api/event-sortes'",
                                           "for (const card of state.vocab) bindings[card.ref] = card.pick;"),
    }
    for name, needles in wants.items():
        text = (front / name).read_text(encoding="utf-8") if (front / name).exists() else ""
        for needle in needles:
            if needle not in text:
                fail(f"EI7: {name} lacks {needle!r}")


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    check_ei1()
    ids = _world(engine)
    for check in (check_ei2, check_ei3, check_ei4, check_ei5, check_ei6):
        try:
            check(engine, ids)
        except Exception as exc:  # a crash is a failure, never a pass
            fail(f"{check.__name__}: crashed: {type(exc).__name__}: {exc}")
    check_ei7()
    for msg in FAILURES:
        print(f"FAIL: {msg}")
    if FAILURES:
        return 1
    print("PASS: event_interpreter -- the interpreter shows the model the world's event types with their roles "
          "and its sortes, writes an event leaf by role, place, window and filters and reads it back, waits for "
          "a pick on an ambiguous name, proposes a missing type or sorte the creator creates or picks -- nothing "
          "written before -- and its prompt is delivered fragment by fragment")
    return 0


if __name__ == "__main__":
    sys.exit(main())
