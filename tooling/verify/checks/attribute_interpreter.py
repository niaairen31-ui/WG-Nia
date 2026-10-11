"""G1 check for TICKET-0113 -- the condition interpreter reads and writes states: the `a` list, the attribute leaf, the prompt delivered fragment by fragment.

The lot adds its pieces brief by brief; this check grows with it (the
`conditions.py` precedent). Each brief adds its rules here in the same
commit. The interpreter's own rules stay `condition_interpreter.py`'s
(TICKET-0112).

AD1 -- the shape (BRIEF-0113-D, static and import). `CODE_LISTS` reads
   `attribute` from the `a` list; `prompt_values` gives `attributes`; the
   head's variables are exactly its template's placeholders and
   `attributes` is one; every fragment of `CONDITION_INTERPRET_FRAGMENTS`
   stands once in the 0112 text of its field and its new text once in the
   seed's; the seed's texts are the 0112 texts with the fragments applied;
   `UNSUPPORTED_NOTES_FR["state"]` sends the creator to « Création ›
   États »; `apply_ticket_0113_condition_prompt.py` reads the fragments and
   embeds no prompt text.
AD2 -- context and form (fixture). `build_context` codes every active
   attribute -- the system ones, then the world's, a hidden one included --
   in the `a` list, each line naming its kind, its labels or value types
   and the types it applies to. A tree of `attribute` leaves -- a choice on
   the doer, an integer on a fixed place, an entity on a fixed item, the
   same with anyone, `sys:vital_status` on a fixed character -- encodes to
   the model's form (a choice by its label, an entity value by `e` code)
   and reads back, bound and validated, to the same tree.
AD3 -- interpretation (fixture, `condition_interpreter.chat` stubbed). A
   choice named by its label in another case, an integer by its threshold,
   an entity value by its name and a place as subject are `proposed` as the
   expected leaves; a label the attribute does not have is refused with the
   attribute's labels, then retried; an entity value two characters bear
   is `needs_choice` and the pick lands in `target_entity_id`; a missing
   state listed as `state` gives the note that sends to « Création ›
   États ».
AD4 -- delivery (`scripts/apply_ticket_0113_condition_prompt.py`, fixture
   database). On a head holding the 0112 text and variables, it writes one
   new version whose text is the seed's and declares `attributes`; a second
   run prints « unchanged » and writes nothing; on a head whose text lost
   one fragment, the others are applied and the lost one is reported.

AE1 -- the shape (BRIEF-0113-E, static and import). The journal's
   `PAYLOAD_KEYS` hold `definitions`; the head declares `entity_types`;
   applying every fragment to the seed's texts changes nothing (no fragment
   touches another's); `write_condition` cleans its tree with no unsaved
   attribute; the offer body carries `unsaved_attributes`; the editor sends
   them (`questOffers.svelte.js`), passes them to every condition
   (`QuestOffers.svelte`) and the interpreter (`ConditionEditor.svelte`),
   whose card renders `<AttributeDefinitionForm` and sends the confirmed
   `definitions` with `inserted`.
AE2 -- proposing (fixture, `condition_interpreter.chat` stubbed). An answer
   defining « Ouverte » (a choice for places) whose leaf names it by
   `{"define": ...}` is `proposed`, the leaf on `new:n1` with its label, the
   definition listed with no near attribute and named in the French lines;
   a definition « maudite » is `needs_choice` with « Maudit » near; picking
   « Maudit » moves the leaf onto it, its label read back to its choice,
   the proposal kept as `adopted` with its key;
   picking `new` keeps the definition; a definition the writer refuses is
   refused, then retried with its error; a draft's unsaved attribute is
   listed in `a` and named by its code.
AE3 -- confirming and saving (route functions). `inserted` with the
   definition retouched keeps both forms in the journal (`confirmed`);
   with a definition whose labels no longer hold the leaf, 422 and nothing
   moves. Saving the offer with the unsaved attribute writes it once, the
   condition stored on its id and its choice's id, the draft `saved` as
   proposed; an unsaved attribute no condition names is not written; a
   condition naming one the body does not carry answers 422 and writes
   nothing.

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
SCRIPT = ROOT / "scripts" / "apply_ticket_0113_condition_prompt.py"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> str:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))
    return db_path


class _Stub:
    def __init__(self, replies):
        self.replies, self.messages = list(replies), []

    def __call__(self, messages, **kwargs):
        self.messages.append(messages)
        reply = self.replies.pop(0)
        return reply if isinstance(reply, str) else json.dumps(reply)


# --- AD1 -------------------------------------------------------------------------

def check_ad1() -> None:
    import seed_pilot

    from world_engine import condition_interpreter as ci
    from world_engine.fact_refs import CodedRefs

    if ci.CODE_LISTS.get("attribute") != "a":
        fail(f"AD1: CODE_LISTS is {ci.CODE_LISTS}")
    empty = CodedRefs(codes={}, lines=())
    ctx = ci.InterpreterContext(entity_lines=(), lists={k: empty for k in "efqsa"}, current=None)
    keys = set(ci.prompt_values(ctx, "eligibility", "x", []))
    head = seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS[0]
    used = set(re.findall(r"\{([a-z_]+)\}", head["user_template"]))
    if used != set(head["variables"]) or used != keys or "attributes" not in used:
        fail(f"AD1: variables {sorted(head['variables'])}, template {sorted(used)}, values {sorted(keys)}")
    fragments = seed_pilot.CONDITION_INTERPRET_FRAGMENTS
    if not fragments:
        fail("AD1: CONDITION_INTERPRET_FRAGMENTS is empty")
    old = {"system_prompt": seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT_0112,
           "user_template": seed_pilot.CONDITION_INTERPRET_USER_TEMPLATE_0112}
    new = {"system_prompt": seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT,
           "user_template": seed_pilot.CONDITION_INTERPRET_USER_TEMPLATE}
    for field, before, after in fragments:
        if old[field].count(before) != 1 or new[field].count(after) != 1:
            fail(f"AD1: the fragment {before[:40]!r} stands {old[field].count(before)} time(s) in the 0112 "
                 f"{field}, its new text {new[field].count(after)} time(s) in the seed's")
    for field in old:
        if seed_pilot.with_condition_fragments(field, old[field]) != new[field]:
            fail(f"AD1: the seed's {field} is not the 0112 text with the fragments applied")
    if "Création › États" not in ci.UNSUPPORTED_NOTES_FR["state"]:
        fail(f"AD1: the state note reads {ci.UNSUPPORTED_NOTES_FR['state']!r}")
    script = SCRIPT.read_text(encoding="utf-8") if SCRIPT.exists() else ""
    if "CONDITION_INTERPRET_FRAGMENTS" not in script or "Tu " in script or "ÉTATS." in script:
        fail("AD1: the delivery script does not read the fragments, or embeds prompt text")


# --- fixture ---------------------------------------------------------------------

def _entity(db, world_id: str, kind: str, name: str) -> str:
    from world_engine.models import Character, Entity, Item, Location

    row = Entity(world_id=world_id, type=kind, name=name)
    db.add(row)
    db.flush()
    db.add({"character": lambda: Character(id=row.id, world_id=world_id, character_type="npc"),
            "item": lambda: Item(id=row.id), "location": lambda: Location(id=row.id)}[kind]())
    db.flush()
    return row.id


def _world(engine) -> dict:
    from sqlmodel import Session

    from world_engine.models import World
    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec, write_attribute_definition

    with Session(engine) as db:
        world = World(name="Interprète AD", is_active=False)
        db.add(world)
        db.flush()
        ids = {"world": world.id}
        for key, kind, name in (("garde", "character", "Garde Brennar"), ("ysa1", "character", "Ysa"),
                                ("ysa2", "character", "Ysa"), ("trone", "item", "Trône de fer"),
                                ("crypte", "location", "Crypte")):
            ids[key] = _entity(db, world.id, kind, name)
        for key, spec in (
            ("maudit", DefinitionSpec(name="Maudit", kind="choice", holder_types=("character", "item"),
                                      choices=(ChoiceSpec("non"), ChoiceSpec("oui")), default="non")),
            ("alerte", DefinitionSpec(name="Niveau d'alerte", kind="integer", holder_types=("location",),
                                      default=0)),
            ("occupe", DefinitionSpec(name="Occupé par", kind="entity", holder_types=("item",),
                                      value_types=("character",))),
            ("marque", DefinitionSpec(name="Marqué", kind="choice", holder_types=("character",),
                                      choices=(ChoiceSpec("non"), ChoiceSpec("oui")), default="non",
                                      is_hidden=True)),
        ):
            ids[key] = write_attribute_definition(db, world_id=world.id, spec=spec).id
        db.commit()
    return ids


def _seed_prompt(db) -> None:
    import seed_pilot

    from world_engine.models import PromptTemplate

    for head in seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS:
        if db.get(PromptTemplate, head["id"]) is None:
            seed_pilot.upsert_prompt_template(db, **dict(head))
    db.commit()


def _choice(db, world: str, key: str, label: str) -> str:
    from world_engine.attributes import attribute_view

    return next(k for k, l in attribute_view(db, world, key).choices if l == label)


def _leafd(**kw) -> dict:
    base = {"op": "leaf", "type": "attribute", "subject_role": "doer", "subject_entity_id": None,
            "target_entity_id": None, "target_key": None, "threshold": None, "value": None}
    base.update(kw)
    if kw.get("subject_entity_id"):
        base["subject_role"] = None
    return base


def _tree(db, ids) -> dict:
    oui = _choice(db, ids["world"], ids["maudit"], "oui")
    return {"op": "all", "children": [
        _leafd(target_key=ids["maudit"], value=oui),
        _leafd(subject_entity_id=ids["crypte"], target_key=ids["alerte"], threshold=3),
        _leafd(subject_entity_id=ids["trone"], target_key=ids["occupe"], target_entity_id=ids["garde"]),
        _leafd(subject_entity_id=ids["trone"], target_key=ids["occupe"]),
        _leafd(subject_entity_id=ids["garde"], target_key="sys:vital_status", value="dead"),
    ]}


# --- AD2 -------------------------------------------------------------------------

def check_ad2(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine import condition_interpreter as ci
    from world_engine.conditions import node_from_dict, node_to_dict

    with Session(engine) as db:
        tree = node_from_dict(_tree(db, ids))
        ctx = ci.build_context(db, ids["world"], "Le trône est occupé", tree)
        coded = list(ctx.lists["a"].codes.values())
        if coded[:3] != ["sys:vital_status", "sys:status", "sys:magic_status"] \
                or not {ids["maudit"], ids["alerte"], ids["occupe"], ids["marque"]} <= set(coded):
            fail(f"AD2: the a list codes {coded}")
        lines = " | ".join(ctx.lists["a"].lines)
        for needle in ("Maudit (choix : non, oui ; pour : personnage, objet)", "Niveau d'alerte (nombre",
                       "Occupé par (une entité : personnage", "État vital (système ; choix : en vie"):
            if needle not in lines:
                fail(f"AD2: the a list lacks {needle!r}: {lines}")
        encoded = ctx.current
        leaves = encoded["children"] if encoded else []
        if len(leaves) != 5 or leaves[0]["value"] != "oui" or leaves[2]["value"] != {"code": "e3"} \
                or leaves[3]["value"] is not None or not str(leaves[0]["target"]["code"]).startswith("a"):
            fail(f"AD2: the tree encodes as {encoded}")
        reading = ci.read_answer(db, ids["world"], encoded, ctx)
        back, errors = ci.validate(db, ids["world"], reading.pending) if not reading.errors else (None,
                                                                                                    reading.errors)
        if errors or node_to_dict(back) != node_to_dict(tree):
            fail(f"AD2: the tree reads back as {node_to_dict(back)} ({errors})")


# --- AD3 -------------------------------------------------------------------------

def _run(ci, db, ids, replies, instruction="Le trône est occupé par Ysa"):
    stub, original = _Stub(replies), ci.chat
    ci.chat = stub
    try:
        return ci.interpret(db, ids["world"], "eligibility", instruction, None, []), stub
    finally:
        ci.chat = original


def _answer(condition, unsupported=()) -> str:
    return json.dumps({"condition": condition, "unsupported": list(unsupported)}, ensure_ascii=False)


def _ml(code, subject="doer", threshold=None, value=None) -> dict:
    return {"op": "leaf", "form": "attribute", "subject": subject, "target": {"code": code},
            "threshold": threshold, "value": value}


def check_ad3(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine import condition_interpreter as ci
    from world_engine.conditions import node_to_dict

    with Session(engine) as db:
        _seed_prompt(db)
        ctx = ci.build_context(db, ids["world"], "x", None)
        code = {key: c for c, key in ctx.lists["a"].codes.items()}
        oui = _choice(db, ids["world"], ids["maudit"], "oui")
        answer = {"op": "all", "children": [
            _ml(code[ids["maudit"]], value="OUI"),
            _ml(code[ids["alerte"]], subject={"name": "Crypte", "kind": "place"}, threshold=3),
            _ml(code[ids["occupe"]], subject={"name": "Trône de fer", "kind": "object"},
                value={"name": "Garde Brennar", "kind": "person"}),
        ]}
        result, _ = _run(ci, db, ids, [_answer(answer)])
        want = {"op": "all", "children": [
            _leafd(target_key=ids["maudit"], value=oui),
            _leafd(subject_entity_id=ids["crypte"], target_key=ids["alerte"], threshold=3),
            _leafd(subject_entity_id=ids["trone"], target_key=ids["occupe"], target_entity_id=ids["garde"])]}
        if result.outcome != "proposed" or node_to_dict(result.tree) != want:
            fail(f"AD3: {result.outcome}, {node_to_dict(result.tree)}, {result.errors}")
        bad = {"op": "all", "children": [_ml(code[ids["maudit"]], value="peut-être")]}
        good = {"op": "all", "children": [_ml(code[ids["maudit"]], value="oui")]}
        result, stub = _run(ci, db, ids, [_answer(bad), _answer(good)])
        second = stub.messages[1][1]["content"] if len(stub.messages) == 2 else ""
        if result.outcome != "proposed" or not result.retried or "libellés : non, oui" not in second:
            fail(f"AD3: an unknown label gave {result.outcome}, retried {result.retried}")
        ysa = {"op": "all", "children": [_ml(code[ids["occupe"]], subject={"name": "Trône de fer",
                                                                             "kind": "object"},
                                             value={"name": "Ysa", "kind": "person"})]}
        result, _ = _run(ci, db, ids, [_answer(ysa)])
        ref = next((m["ref"] for m in result.mentions if m["status"] == "ambiguous"), None)
        if result.outcome != "needs_choice" or ref is None:
            fail(f"AD3: an ambiguous entity value gave {result.outcome}")
        else:
            done = ci.resolve(db, ids["world"], result.pending, result.mentions, result.notes, {ref: ids["ysa2"]})
            leaf = node_to_dict(done.tree)["children"][0] if done.tree else {}
            if done.outcome != "proposed" or leaf.get("target_entity_id") != ids["ysa2"]:
                fail(f"AD3: the pick gave {done.outcome}, {leaf}")
        result, _ = _run(ci, db, ids, [_answer(None, [{"text": "la porte est ouverte", "kind": "state"}])])
        if not any("Création › États" in n for n in result.notes):
            fail(f"AD3: a missing state gave the notes {result.notes}")


# --- AD4 -------------------------------------------------------------------------

def _run_script(db_path: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    return subprocess.run([sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True,
                          cwd=str(ROOT), timeout=120)


def _prompt_db(system_prompt: str) -> str:
    import seed_pilot
    from sqlalchemy import create_engine
    from sqlmodel import Session, SQLModel

    from world_engine.models import PromptTemplate
    from world_engine.writes.prompts import write_prompt_variables, write_prompt_version

    head = dict(seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS[0])
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "prompt.db")
    eng = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(eng)
    with Session(eng) as db:
        db.add(PromptTemplate(id=head["id"], name=head["name"], usage=head["usage"], world_id=None,
                              destination=head["destination"]))
        db.flush()
        write_prompt_variables(db, template_id=head["id"],
                               variables=[v for v in head["variables"] if v != "attributes"])
        write_prompt_version(db, template_id=head["id"], system_prompt=system_prompt,
                             user_template=seed_pilot.CONDITION_INTERPRET_USER_TEMPLATE_0112, note="seed v1")
        db.commit()
    eng.dispose()
    return db_path


def _current(db_path: str):
    from sqlalchemy import create_engine
    from sqlmodel import Session

    from world_engine.models import PromptTemplate, PromptVariable
    from world_engine.prompt_store import current_prompt
    from sqlmodel import select

    eng = create_engine(f"sqlite:///{db_path}")
    with Session(eng) as db:
        head = db.get(PromptTemplate, "pt-condition-interpret")
        version = current_prompt(db, head)
        names = set(db.exec(select(PromptVariable.name)).all())
        state = (version.version_number, version.system_prompt, version.user_template, names)
    eng.dispose()
    return state


def check_ad4() -> None:
    import seed_pilot

    db_path = _prompt_db(seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT_0112)
    result = _run_script(db_path)
    number, system, user, names = _current(db_path)
    if result.returncode != 0 or number != 2 or system != seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT \
            or user != seed_pilot.CONDITION_INTERPRET_USER_TEMPLATE or "attributes" not in names:
        fail(f"AD4: exit {result.returncode}, v{number}, seed text {system == seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT}"
             f"/{user == seed_pilot.CONDITION_INTERPRET_USER_TEMPLATE}: {result.stdout.strip()[-200:]}")
    again = _run_script(db_path)
    if again.returncode != 0 or "unchanged" not in again.stdout or _current(db_path)[0] != 2:
        fail(f"AD4: a second run: {again.stdout.strip()[-200:]}")
    _field, lost, _new = seed_pilot.CONDITION_INTERPRET_FRAGMENTS[0]
    edited = seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT_0112.replace(lost, "(retouché à la main)")
    db_path = _prompt_db(edited)
    result = _run_script(db_path)
    number, system, user, _names = _current(db_path)
    if result.returncode != 0 or number != 2 or "fragment not found" not in result.stdout \
            or "(retouché à la main)" not in system or "{attributes}" not in user:
        fail(f"AD4: an edited head gave v{number}: {result.stdout.strip()[-300:]}")


# --- AE1 -------------------------------------------------------------------------

def check_ae1() -> None:
    import ast

    import seed_pilot

    from world_engine.cockpit.routes.quests import OfferBody
    from world_engine.writes.condition_drafts import PAYLOAD_KEYS

    if "definitions" not in PAYLOAD_KEYS:
        fail(f"AE1: PAYLOAD_KEYS is {sorted(PAYLOAD_KEYS)}")
    if "entity_types" not in seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS[0]["variables"]:
        fail("AE1: the head does not declare entity_types")
    for field, text in (("system_prompt", seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT),
                        ("user_template", seed_pilot.CONDITION_INTERPRET_USER_TEMPLATE)):
        if seed_pilot.with_condition_fragments(field, text) != text:
            fail(f"AE1: applying the fragments to the seed's {field} changes it: one fragment touches another")
    tree = ast.parse((ROOT / "src" / "world_engine" / "writes" / "conditions.py").read_text(encoding="utf-8"))
    write = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "write_condition"), None)
    calls = [c for c in ast.walk(write) if isinstance(c, ast.Call) and getattr(c.func, "id", "") == "clean_condition"] \
        if write else []
    if len(calls) != 1 or calls[0].keywords:
        fail("AE1: write_condition does not clean its tree with no unsaved attribute")
    if "unsaved_attributes" not in OfferBody.model_fields:
        fail("AE1: OfferBody carries no unsaved_attributes")
    front = ROOT / "frontend" / "src" / "creation"
    needles = {
        "questOffers.svelte.js": ("unsaved_attributes: draft.unsavedAttributes",),
        "QuestOffers.svelte": ("unsaved={draft.unsavedAttributes}",),
        "ConditionEditor.svelte": ("<ConditionInterpreter {cond} {role} {unsaved}", "withUnsaved(choices, unsaved)"),
        "ConditionInterpreter.svelte": ("<AttributeDefinitionForm",),
        "conditionInterpreter.svelte.js": ("decide(state, 'inserted', { definitions",),
    }
    for name, wanted in needles.items():
        text = (front / name).read_text(encoding="utf-8") if (front / name).exists() else ""
        for needle in wanted:
            if needle not in text:
                fail(f"AE1: {name} lacks {needle}")
    if (front / "QuestOffers.svelte").read_text(encoding="utf-8").count("unsaved={draft.unsavedAttributes}") != 3:
        fail("AE1: QuestOffers.svelte does not pass the unsaved attributes to its three conditions")


# --- AE2 -------------------------------------------------------------------------

def _define(ref, name, kind="choice", for_=("location",), choices=("non", "oui"), default="non"):
    return {"ref": ref, "name": name, "kind": kind, "for": list(for_), "choices": list(choices),
            "default": default, "hidden": False}


def _parsed(condition, define=()) -> str:
    return json.dumps({"condition": condition, "unsupported": [], "define": list(define)}, ensure_ascii=False)


def _open_leaf():
    return {"op": "leaf", "form": "attribute", "subject": {"name": "Crypte", "kind": "place"},
            "target": {"define": "d1"}, "threshold": None, "value": "oui"}


def check_ae2(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine import condition_interpreter as ci
    from world_engine.attribute_proposals import UnsavedAttribute
    from world_engine.conditions import node_to_dict
    from world_engine.quest_reads import condition_view
    from world_engine.attribute_proposals import unsaved_views, spec_from_dict
    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec

    with Session(engine) as db:
        _seed_prompt(db)
        result, _ = _run(ci, db, ids, [_parsed({"op": "all", "children": [_open_leaf()]},
                                                [_define("d1", "Ouverte")])])
        leaf = node_to_dict(result.tree)["children"][0] if result.tree else {}
        defs = result.definitions
        if result.outcome != "proposed" or leaf.get("target_key") != "new:n1" or leaf.get("value") != "oui" \
                or len(defs) != 1 or defs[0]["near"] or defs[0]["definition"]["name"] != "Ouverte":
            fail(f"AE2: a defined state gave {result.outcome}, {leaf}, {defs}, {result.errors}")
        else:
            views = unsaved_views([UnsavedAttribute(ref=d["ref"], spec=spec_from_dict(d["definition"])) for d in defs])
            lines = " ".join(l["text"] for l in condition_view(db, result.tree, views)["lines"])
            if "Ouverte : oui" not in lines:
                fail(f"AE2: the French lines read {lines!r}")
        cursed = {"op": "leaf", "form": "attribute", "subject": "doer", "target": {"define": "d1"},
                  "threshold": None, "value": "oui"}
        near_answer = _parsed({"op": "all", "children": [cursed]},
                              [_define("d1", "maudite", for_=("character",))])
        result, _ = _run(ci, db, ids, [near_answer])
        near = result.definitions[0]["near"] if result.definitions else []
        if result.outcome != "needs_choice" or ids["maudit"] not in [n["key"] for n in near]:
            fail(f"AE2: a near name gave {result.outcome}, near {near}")
        else:
            oui = _choice(db, ids["world"], ids["maudit"], "oui")
            used = ci.resolve(db, ids["world"], result.pending, result.mentions, result.notes,
                              {"n1": ids["maudit"]}, tuple(result.definitions))
            moved = node_to_dict(used.tree)["children"][0] if used.tree else {}
            if used.outcome != "proposed" or (moved.get("target_key"), moved.get("value")) != (ids["maudit"], oui) \
                    or [d.get("adopted") for d in used.definitions] != [ids["maudit"]]:
                fail(f"AE2: picking Maudit gave {used.outcome}, {moved}, {used.definitions}")
            kept = ci.resolve(db, ids["world"], result.pending, result.mentions, result.notes, {"n1": "new"},
                              tuple(result.definitions))
            if kept.outcome != "proposed" or len(kept.definitions) != 1:
                fail(f"AE2: creating it gave {kept.outcome}, {kept.definitions}")
        bad = _parsed({"op": "all", "children": [_open_leaf()]}, [_define("d1", "Ouverte", choices=("oui",),
                                                                           default="oui")])
        good = _parsed({"op": "all", "children": [_open_leaf()]}, [_define("d1", "Ouverte")])
        result, stub = _run(ci, db, ids, [bad, good])
        second = stub.messages[1][1]["content"] if len(stub.messages) == 2 else ""
        if result.outcome != "proposed" or not result.retried or "at least two labels" not in second:
            fail(f"AE2: a refused definition gave {result.outcome}, retried {result.retried}")
        unsaved = (UnsavedAttribute(ref="n1", spec=DefinitionSpec(
            name="Brisé", kind="choice", holder_types=("item",), choices=(ChoiceSpec("non"), ChoiceSpec("oui")),
            default="non")),)
        ctx = ci.build_context(db, ids["world"], "x", None, unsaved)
        code = next((c for c, key in ctx.lists["a"].codes.items() if key == "new:n1"), None)
        broken = {"op": "leaf", "form": "attribute", "subject": {"name": "Trône de fer", "kind": "object"},
                  "target": {"code": code}, "threshold": None, "value": "oui"}
        stub, original = _Stub([_parsed({"op": "all", "children": [broken]})]), ci.chat
        ci.chat = stub
        try:
            result = ci.interpret(db, ids["world"], "eligibility", "Le trône est brisé", None, [], unsaved)
        finally:
            ci.chat = original
        leaf = node_to_dict(result.tree)["children"][0] if result.tree else {}
        if code is None or "à créer" not in " ".join(ctx.lists["a"].lines) or result.outcome != "proposed" \
                or leaf.get("target_key") != "new:n1":
            fail(f"AE2: a draft's unsaved attribute gave {code}, {result.outcome}, {leaf}, {result.errors}")


# --- AE3 -------------------------------------------------------------------------

def check_ae3(engine, ids: dict) -> None:
    from fastapi import HTTPException
    from sqlmodel import Session, func, select

    from world_engine import condition_interpreter as ci
    from world_engine.cockpit.routes import attributes as attr_routes
    from world_engine.cockpit.routes import conditions as routes
    from world_engine.cockpit.routes import quests
    from world_engine.models import AttributeDefinition, ConditionDraft, ConditionNode, World

    def unsaved(ref, name, labels=("non", "oui")):
        return attr_routes.UnsavedBody(ref=ref, definition=attr_routes.DefinitionBody(
            name=name, kind="choice", holder_types=["location"], default=labels[0],
            choices=[attr_routes.ChoiceBody(label=l) for l in labels]))

    def count(model) -> int:
        return db.exec(select(func.count()).select_from(model)).one()

    with Session(engine) as db:
        _seed_prompt(db)
        db.get(World, ids["world"]).is_active = True
        db.commit()
        stub, original = _Stub([_parsed({"op": "all", "children": [_open_leaf()]}, [_define("d1", "Ouverte")])]), ci.chat
        ci.chat = stub
        try:
            answer = routes.interpret(routes.InterpretBody(instruction="La crypte est ouverte", role="eligibility"),
                                      db=db)
        finally:
            ci.chat = original
        draft_id = answer["draft_id"]
        try:
            routes.decide(draft_id, routes.DecisionBody(decision="inserted", definitions=[
                unsaved("n1", "Ouverte", ("fermée", "ouverte"))]), db=db)
            fail("AE3: a definition whose labels no longer hold the leaf was accepted")
        except HTTPException as exc:
            if exc.status_code != 422 or db.get(ConditionDraft, draft_id).outcome != "proposed":
                fail(f"AE3: a broken confirmation answered {exc.status_code}")
        routes.decide(draft_id, routes.DecisionBody(decision="inserted", definitions=[unsaved("n1", "Ouvert")]),
                      db=db)
        stored = db.get(ConditionDraft, draft_id).payload["definitions"][0]
        if stored["definition"]["name"] != "Ouverte" or stored.get("confirmed", {}).get("name") != "Ouvert":
            fail(f"AE3: the journal keeps {stored}")
        before = (count(AttributeDefinition), count(ConditionNode))
        tree = answer["view"]["tree"]
        step = [quests.OfferStepBody(objective="Entrer", cost=1)]
        orphan = quests.OfferBody(giver_entity_id=ids["garde"], title="Orpheline", eligibility={
            "op": "all", "children": [{**tree["children"][0], "target_key": "new:n9"}]},
            unsaved_attributes=[unsaved("n1", "Ouvert")], steps=step)
        try:
            quests.create_offer(orphan, db=db)
            fail("AE3: a condition naming an attribute the body does not carry was saved")
        except HTTPException as exc:
            if exc.status_code != 422 or (count(AttributeDefinition), count(ConditionNode)) != before:
                fail(f"AE3: an orphan key answered {exc.status_code} or wrote rows")
        body = quests.OfferBody(giver_entity_id=ids["garde"], title="La crypte", eligibility=tree,
                                eligibility_draft_id=draft_id, steps=step,
                                unsaved_attributes=[unsaved("n1", "Ouvert"), unsaved("n2", "Inutile")])
        saved = quests.create_offer(body, db=db)
        made = db.exec(select(AttributeDefinition).where(AttributeDefinition.name == "Ouvert")).all()
        if len(made) != 1 or db.exec(select(AttributeDefinition).where(AttributeDefinition.name == "Inutile")).first():
            fail(f"AE3: the save wrote {[d.name for d in made]} (and Inutile?)")
        else:
            leaf = saved["eligibility"]["tree"]["children"][0]
            oui = _choice(db, ids["world"], made[0].id, "oui")
            if (leaf["target_key"], leaf["value"]) != (made[0].id, oui):
                fail(f"AE3: the saved leaf is {leaf}")
        draft = db.get(ConditionDraft, draft_id)
        if (draft.outcome, draft.saved_as_proposed) != ("saved", True):
            fail(f"AE3: the draft reads {draft.outcome}, {draft.saved_as_proposed}")
        db.get(World, ids["world"]).is_active = False
        db.commit()


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    ids = _world(engine)
    for name, rule in (("AD1", check_ad1), ("AD2", lambda: check_ad2(engine, ids)),
                       ("AD3", lambda: check_ad3(engine, ids)), ("AD4", check_ad4),
                       ("AE1", check_ae1), ("AE2", lambda: check_ae2(engine, ids)),
                       ("AE3", lambda: check_ae3(engine, ids))):
        try:
            rule()
        except Exception as exc:  # a crash is that rule's failure, never a pass
            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: attribute_interpreter -- the interpreter shows the model every attribute by code, writes "
          "an attribute leaf by label, threshold or name and reads it back, proposes a missing state the "
          "creator confirms -- a near one picked, never duplicated -- written with the offer's save, and its "
          "prompt is delivered fragment by fragment, keeping the creator's edits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
