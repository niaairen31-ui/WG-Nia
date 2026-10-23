"""G1 check for TICKET-0126 (BRIEF-0126-F) -- the character designer reads only the public view of the chosen world, retries once against the one check, and keeps every rule of its resolution table.

CD1 -- the premise of a chosen world. Two worlds, W1 active and W2 not,
   each with a description: `world_premise(db, "player", world_id=W2)`
   names W2 and not W1; without `world_id` it names W1; `call_json` with
   `world_id=W2` sends a system message holding `Monde : <W2 name>`.
CD2 -- the creation lore, on `perspective_isolation._build_world` plus a
   public visitable location (Port), a public zone (Région) with one child
   location (Quai), and a non-public location (Caverne):
   `gather_creation_lore(names=["Hero", "Shade", "Nobody"],
   keywords=["tunnel"])` keeps Hero in `people` and not Shade; the lines
   hold Hero's identity line and no identity line for Shade or Nobody; the
   only `tunnel` line is F6's public text, never F7's; `places` are exactly
   Port and Quai; `factions` are exactly Guild and Guild2.
CD3 -- static. `creation_lore.py` and `creation_designer.py` hold none of
   `CREATOR`, `NameScope("creator"`, `include_creator_only`,
   `entity_dossier`, `who_knows_about`, `world_factions`, `World.is_active`,
   `_world_id(`, `db.add(`, `.commit(`, `.flush(`, nor `facts_mentioning(`
   outside `public_facts_mentioning(`; neither imports from
   `lore_selectors`.
CD4 -- `subject` then `design` on a draft added directly (status `draft`,
   two player sketches), `creation_designer.chat` stubbed:
   a. a subject, a design over the pool, a valid retry: two design calls,
      `violations == ()`, the retry's user message holds `Erreurs de ta
      réponse précédente :`;
   b. a subject, two designs over the pool: `violations` non-empty, exactly
      two design calls;
   c. designs exercising every row of LOT-0126 case table (b)-3: each
      outcome and each note verbatim (skills, sketches, the start place
      matched / unknown / null, memberships, knowledge, notes);
   d. an `OllamaError` reply propagates from `subject`; an unparsable
      design reply raises `LlmParseError`.
CD5 -- `PROMPT_REGISTRY` holds both usages with `premise == "player"` and
   C-09's call sites; `seed_pilot.CHARACTER_DESIGNER_PROMPT_HEADS` holds
   exactly C-09's ids, usages and variables;
   `scripts/apply_ticket_0126_designer_prompts.py` exists and names the
   tuple.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A case not reached is a FAILURE.
"""
from __future__ import annotations

import ast
import json
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
PKG = SRC / "world_engine"
SCRIPTS = ROOT / "scripts"
CHECKS = pathlib.Path(__file__).resolve().parent
DELIVERY = SCRIPTS / "apply_ticket_0126_designer_prompts.py"

STATIC_MODULES = ("creation_lore.py", "creation_designer.py")
FORBIDDEN = ("CREATOR", 'NameScope("creator"', "include_creator_only", "entity_dossier", "who_knows_about",
             "world_factions", "World.is_active", "_world_id(", "db.add(", ".commit(", ".flush(")
EXPECTED_HEADS = {
    "pt-creation-subject": ("creation_subject", ["character_name", "backstory"]),
    "pt-creation-design": ("creation_design", ["character_name", "backstory", "skills", "player_choices", "rules",
                                               "lore", "people", "places", "factions", "errors"]),
}
EXPECTED_SITES = {
    "creation_subject": ("src/world_engine/creation_designer.py:_subject_call",),
    "creation_design": ("src/world_engine/creation_designer.py:_design_call",),
}
DESIGN_MARK = "COMPÉTENCES (code"
RETRY_MARK = "Erreurs de ta réponse précédente :"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{pathlib.Path(tmp_dir) / 'check.db'}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]
    from sqlmodel import SQLModel

    import world_engine.models  # noqa: F401 -- registers every table
    from world_engine.db import engine

    SQLModel.metadata.create_all(engine)
    return engine


class _Stub:
    def __init__(self, replies):
        self.replies, self.messages = list(replies), []

    def __call__(self, messages, **kwargs):
        self.messages.append(messages)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply if isinstance(reply, str) else json.dumps(reply)

    def design_messages(self) -> list[list[dict]]:
        return [m for m in self.messages if DESIGN_MARK in m[1]["content"]]


def _swap(module, stub):
    original = module.chat
    module.chat = stub
    return original


def _seed_prompts(engine) -> None:
    from sqlmodel import Session

    sys.path.insert(0, str(SCRIPTS))
    import seed_pilot

    with Session(engine) as db:
        for entry in seed_pilot.CHARACTER_DESIGNER_PROMPT_HEADS:
            seed_pilot.upsert_prompt_template(db, **entry)
        db.commit()


# ── CD1 ────────────────────────────────────────────────────────────────────


def rule_cd1(engine) -> int:
    from sqlmodel import Session

    from world_engine import prompt_call
    from world_engine.models import World
    from world_engine.world_premise import world_premise

    reached = 0
    with Session(engine) as db:
        w1 = World(name="Premier Monde", description="Un monde actif.", is_active=True)
        w2 = World(name="Second Monde", description="Un monde choisi.")
        db.add(w1)
        db.add(w2)
        db.commit()
        chosen = world_premise(db, "player", world_id=w2.id)
        if "Monde : Second Monde" not in chosen or "Premier Monde" in chosen:
            fail(f"CD1 the premise of W2 is {chosen!r}")
        active = world_premise(db, "player")
        if "Monde : Premier Monde" not in active:
            fail(f"CD1 the premise without world_id is {active!r}")
        reached += 1
        stub = _Stub([{"names": [], "keywords": []}])
        prompt_call.call_json(db, "creation_subject", {"character_name": "X", "backstory": "Y"}, None, stub,
                              world_id=w2.id)
        system = stub.messages[0][0]["content"] if stub.messages else ""
        if "Monde : Second Monde" not in system:
            fail(f"CD1 call_json with world_id=W2 sent the system message {system[:200]!r}")
        w1.is_active = False
        db.add(w1)
        db.commit()
        reached += 1
    return reached


# ── CD2 ────────────────────────────────────────────────────────────────────


def _add_location(db, wid: str, name: str, *, public: bool = True, parent: str | None = None) -> str:
    from world_engine.models import Entity, Location

    entity = Entity(world_id=wid, type="location", name=name, is_public=public)
    db.add(entity)
    db.flush()
    db.add(Location(id=entity.id, parent_location_id=parent))
    db.flush()
    return entity.id


def _build(engine) -> dict:
    from sqlmodel import Session

    sys.path.insert(0, str(CHECKS))
    from perspective_isolation import _build_world

    ids = _build_world(engine)
    with Session(engine) as db:
        wid = ids["world"]
        ids["port"] = _add_location(db, wid, "Port")
        ids["region"] = _add_location(db, wid, "Région")
        ids["quai"] = _add_location(db, wid, "Quai", parent=ids["region"])
        ids["caverne"] = _add_location(db, wid, "Caverne", public=False)
        db.commit()
    return ids


def rule_cd2(engine, ids: dict) -> int:
    from sqlmodel import Session

    from world_engine.creation_lore import gather_creation_lore

    ids.update(_build(engine))
    wid, text = ids["world"], ids["text"]
    with Session(engine) as db:
        lore = gather_creation_lore(db, wid, names=["Hero", "Shade", "Nobody"], keywords=["tunnel"])
    people = {p["entity_id"] for p in lore.people}
    if ids["hero"] not in people or ids["shade"] in people:
        fail(f"CD2 people are {lore.people!r}")
    if "— Hero (character)" not in lore.lines:
        fail(f"CD2 Hero's identity line is missing from {lore.lines!r}")
    for name in ("Shade", "Nobody"):
        if any(line.startswith(f"— {name} ") for line in lore.lines):
            fail(f"CD2 an identity line names {name}")
    tunnel = [line for line in lore.lines if "tunnel" in line]
    if tunnel != [f"• {text['F6']}"]:
        fail(f"CD2 the tunnel lines are {tunnel!r}, expected F6's only")
    if any(text["F7"] in line for line in lore.lines):
        fail("CD2 F7 (not public) reaches the lore")
    if {p["entity_id"] for p in lore.places} != {ids["port"], ids["quai"]}:
        fail(f"CD2 places are {[p['name'] for p in lore.places]}, expected Port and Quai")
    if {f["name"] for f in lore.factions} != {"Guild", "Guild2"}:
        fail(f"CD2 factions are {[f['name'] for f in lore.factions]}, expected Guild and Guild2")
    return 1


# ── CD3 ────────────────────────────────────────────────────────────────────


def rule_cd3() -> int:
    reached = 0
    for name in STATIC_MODULES:
        path = PKG / name
        if not path.exists():
            fail(f"CD3 {name} missing")
            continue
        text = path.read_text(encoding="utf-8")
        for needle in FORBIDDEN:
            if needle in text:
                fail(f"CD3 {name} contains {needle!r}")
        if text.count("facts_mentioning(") != text.count("public_facts_mentioning("):
            fail(f"CD3 {name} calls facts_mentioning( outside public_facts_mentioning(")
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("lore_selectors"):
                fail(f"CD3 {name} imports from lore_selectors")
            if isinstance(node, ast.Import) and any(a.name.endswith("lore_selectors") for a in node.names):
                fail(f"CD3 {name} imports lore_selectors")
        reached += 1
    return reached


# ── CD4 ────────────────────────────────────────────────────────────────────


def _add_skills_and_draft(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.models import PcDraft, PcDraftSketch, SkillDefinition, User

    with Session(engine) as db:
        wid = ids["world"]
        lame = SkillDefinition(world_id=wid, name="Lame", base_domain="agility")
        voix = SkillDefinition(world_id=wid, name="Voix", base_domain="composure", requires_master=True)
        db.add(lame)
        db.add(voix)
        user = User(name="Joueuse")
        db.add(user)
        db.flush()
        draft = PcDraft(world_id=wid, user_id=user.id, name="Ilan", backstory="Ilan a grandi au port.")
        db.add(draft)
        db.flush()
        for position, name in enumerate(("Sa mère", "Son frère")):
            db.add(PcDraftSketch(draft_id=draft.id, world_id=wid, position=position, name=name,
                                 kind="family", origin="player"))
        db.commit()
        ids["lame"], ids["voix"], ids["draft"] = lame.id, voix.id, draft.id


# Listed codes on this world: s1-s4 the base domains (physical, agility,
# perception, composure), s5 Lame, s6 Voix (start sheet order, no system).
_OVER_POOL = {"skills": [{"skill": "s5", "rank": 5, "reason": "trop"}], "sketches": [], "start_place": None,
              "memberships": [], "knowledge": [], "notes": []}
_VALID = {"skills": [{"skill": "s5", "rank": 2, "reason": "au port"}], "sketches": [], "start_place": None,
          "memberships": [], "knowledge": [], "notes": []}
_EVERY_ROW = {
    "skills": [
        {"skill": "s5", "rank": 2, "reason": "au port"},
        {"skill": "s99", "rank": 1},
        {"skill": "s1", "rank": 9},
        {"skill": "s5", "rank": 3},
        {"skill": "s6", "rank": 1, "reason": "son maître"},
    ],
    "sketches": [
        "pas un objet",
        {"name": "  "},
        {"name": "Tante", "kind": "weird", "role": "tante", "sentence": "s", "group": "sa famille"},
        {"name": "Maître Voix", "kind": "master", "skill": "s6"},
        {"name": "Faux maître", "kind": "master", "skill": "s5"},
        {"name": "Le héros", "kind": "other", "existing": "Hero"},
        {"name": "L'ombre", "kind": "other", "existing": "Shade"},
        {"name": "Voisin", "kind": "other"},
        {"name": "Passeur", "kind": "other"},
    ],
    "start_place": "port",
    "memberships": [{"faction": "guild", "role": "recrue"}, {"faction": "Cabal"}, {"faction": "Guild"}],
    "knowledge": [{"level": "weird", "content": "Une rumeur"}, {"level": "knows", "content": ""}]
    + [{"level": "knows", "content": f"Fait {n}"} for n in range(10)],
    "notes": ["Belle histoire", "", 3],
}
_EVERY_ROW_NOTES = (
    "Belle histoire",
    "Compétence inconnue écartée : s99.",
    "Rang invalide écarté pour « physical ».",
    "Une personne sans nom a été écartée.",
    "Une personne sans nom a été écartée.",
    "« Faux maître » : maître sans compétence connue, gardé comme « autre ».",
    "1 personne(s) proposée(s) écartée(s) : 8 au plus.",
    "Faction inconnue écartée : Cabal.",
)


def _run(engine, ids: dict, replies, *, subject_first: bool = True):
    from sqlmodel import Session

    from world_engine import creation_designer as cd
    from world_engine.models import PcDraft

    stub = _Stub(replies)
    original = _swap(cd, stub)
    try:
        with Session(engine) as db:
            draft = db.get(PcDraft, ids["draft"])
            names, keywords = cd.subject(db, draft, []) if subject_first else ((), ())
            return cd.design(db, draft, names, keywords, []), stub
    finally:
        cd.chat = original


def _cd4_retry(engine, ids: dict) -> int:
    subject = {"names": ["Hero"], "keywords": ["port"]}
    result, stub = _run(engine, ids, [subject, _OVER_POOL, _VALID])
    designs = stub.design_messages()
    if len(designs) != 2 or result.violations != ():
        fail(f"CD4a {len(designs)} design call(s), violations {result.violations!r}")
    elif RETRY_MARK not in designs[1][1]["content"] or RETRY_MARK in designs[0][1]["content"]:
        fail("CD4a the retry's user message lacks the previous errors")
    if result.names != ("Hero",) or result.keywords != ("port",):
        fail(f"CD4a subject gave {result.names!r}, {result.keywords!r}")

    result, stub = _run(engine, ids, [subject, _OVER_POOL, _OVER_POOL])
    if len(stub.design_messages()) != 2 or not result.violations:
        fail(f"CD4b {len(stub.design_messages())} design call(s), violations {result.violations!r}")
    return 2


def _cd4_every_row(engine, ids: dict) -> int:
    result, _ = _run(engine, ids, [_EVERY_ROW], subject_first=False)
    skills = [(s.skill_key, s.rank, s.reason) for s in result.skills]
    if skills != [(ids["lame"], 2, "au port"), (ids["voix"], 1, "son maître")]:
        fail(f"CD4c skills are {skills!r}")
    sketches = [(s.name, s.kind, s.skill_key, s.existing_entity_id, s.group_label) for s in result.sketches]
    want = [("Tante", "other", None, None, "sa famille"), ("Maître Voix", "master", ids["voix"], None, ""),
            ("Faux maître", "other", None, None, ""), ("Le héros", "other", None, ids["hero"], ""),
            ("L'ombre", "other", None, None, ""), ("Voisin", "other", None, None, "")]
    if sketches != want:
        fail(f"CD4c sketches are {sketches!r}")
    if result.start_location_id != ids["port"]:
        fail(f"CD4c the start place is {result.start_location_id!r}, expected Port")
    if [(m.faction_id, m.role) for m in result.memberships] != [(ids["guild"], "recrue")]:
        fail(f"CD4c memberships are {result.memberships!r}")
    knowledge = [(k.level, k.content) for k in result.knowledge]
    if knowledge != [("rumor", "Une rumeur")] + [("knows", f"Fait {n}") for n in range(9)]:
        fail(f"CD4c knowledge is {knowledge!r}")
    if result.notes != _EVERY_ROW_NOTES:
        fail(f"CD4c notes are {result.notes!r}")

    unknown = {**_VALID, "start_place": "Atlantide"}
    result, _ = _run(engine, ids, [unknown], subject_first=False)
    if result.start_location_id is not None or result.notes != ("Lieu de départ inconnu écarté : Atlantide.",):
        fail(f"CD4c an unknown start place gave {result.start_location_id!r}, {result.notes!r}")
    for value in (None, ""):
        result, _ = _run(engine, ids, [{**_VALID, "start_place": value}], subject_first=False)
        if result.start_location_id is not None or result.notes:
            fail(f"CD4c a start place {value!r} gave {result.start_location_id!r}, {result.notes!r}")
    return 1


def _cd4_errors(engine, ids: dict) -> int:
    from world_engine.llm_parse import LlmParseError
    from world_engine.ollama_client import OllamaError

    try:
        _run(engine, ids, [OllamaError("down")])
        fail("CD4d an OllamaError did not propagate")
    except OllamaError:
        pass
    try:
        _run(engine, ids, ["pas du json"], subject_first=False)
        fail("CD4d an unparsable design reply raised nothing")
    except LlmParseError:
        pass
    return 1


def rule_cd4(engine, ids: dict) -> int:
    _add_skills_and_draft(engine, ids)
    return _cd4_retry(engine, ids) + _cd4_every_row(engine, ids) + _cd4_errors(engine, ids)


# ── CD5 ────────────────────────────────────────────────────────────────────


def rule_cd5() -> int:
    from world_engine.prompt_registry import PROMPT_REGISTRY

    sys.path.insert(0, str(SCRIPTS))
    import seed_pilot

    for usage, sites in EXPECTED_SITES.items():
        spec = PROMPT_REGISTRY.get(usage)
        if spec is None:
            fail(f"CD5 PROMPT_REGISTRY lacks {usage}")
        elif spec.premise != "player" or tuple(spec.call_sites) != sites:
            fail(f"CD5 {usage}: premise {spec.premise!r}, call sites {spec.call_sites!r}")
    heads = {h["id"]: (h["usage"], list(h["variables"])) for h in seed_pilot.CHARACTER_DESIGNER_PROMPT_HEADS}
    if heads != EXPECTED_HEADS:
        fail(f"CD5 CHARACTER_DESIGNER_PROMPT_HEADS is {heads!r}")
    if not DELIVERY.exists():
        fail("CD5 scripts/apply_ticket_0126_designer_prompts.py missing")
    elif "CHARACTER_DESIGNER_PROMPT_HEADS" not in DELIVERY.read_text(encoding="utf-8"):
        fail("CD5 the delivery script does not name CHARACTER_DESIGNER_PROMPT_HEADS")
    return 1


def main() -> int:
    engine = _fresh_engine()
    _seed_prompts(engine)
    ids: dict = {}
    plan = (
        (rule_cd1, 2, (engine,)),
        (rule_cd2, 1, (engine, ids)),
        (rule_cd3, 2, ()),
        (rule_cd4, 4, (engine, ids)),
        (rule_cd5, 1, ()),
    )
    for index, (rule, count, args) in enumerate(plan, start=1):
        reached = 0
        try:
            reached = rule(*args)
        except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
            fail(f"CD{index} raised {type(exc).__name__}: {exc}")
        if reached != count:
            fail(f"CD{index} reached {reached} of its {count} cases")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: creation_designer -- the premise of the chosen world, the creation lore on the public view only, "
          "the subject and the design with one retry against check_creation, every row of the resolution "
          "table, the two player-regime prompts seeded and delivered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
