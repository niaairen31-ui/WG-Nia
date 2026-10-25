"""G1 check for TICKET-0126 (BRIEF-0126-G) -- the player's draft lives and is submitted only through the one check, and the creation routes stay in the public view.

Fixture: `perspective_isolation._build_world` made open to players (its
`open_to_players` set directly), a public visitable location `Port`, a
zone `Région` with its child `Quai`; a skill system `Arts` with three
definitions -- `Escrime` (visible, open), `Ombre` (invisible at
creation), `Nécromancie` (visible, requires a master); player profiles
through `POST /api/joueur/profils`.

PC1 catalogue -- `GET /api/joueur/creation/catalogue` answers C-14's keys;
   `skills` holds the four base domains, `Escrime` and `Nécromancie`, never
   `Ombre`; `places` are Port and Quai, never Région; `factions` are Guild
   and Guild2.
PC2 lifecycle -- `POST brouillon` 201, again 201 with the same id; a `PUT`
   with name, story, Port and Escrime 2 spends 1; a `PUT` with nine
   sketches -> 422 `Au plus 8 personnes d'ancrage.` and nothing changed; a
   `PUT` with a `master` sketch without a skill -> 422.
PC3 check_draft -- every `DRAFT_VIOLATION_CODES` code reached on its own
   draft state, alone, with its message verbatim: empty name, empty story,
   no place, Région as place, nine sketches written directly, Nécromancie 1
   without a master sketch, a sketch naming Shade, a membership in Cabal, a
   player character of the profile.
PC4 designer -- ping down -> 503 and one `creation_subject/unavailable`
   row; an unparsable subject -> 502 and one `creation_subject/parse_error`
   row; an unparsable design -> 502, `creation_subject/ok` and
   `creation_design/parse_error` rows; success -> 200, both `ok` rows asked
   by `player:<id>`, the designer's rank, designer sketches, the start place
   when the player had none; a second call replaces the designer rows and
   keeps the sketch the player edited in between (origin `player`).
PC5 submit -- with a violation `submitted: false`, status `draft`;
   `submit_draft` itself refuses violations; clean -> `submitted: true`,
   `submitted_at` set; then PUT, designer and submit -> 409
   `DRAFT_LOCKED_MESSAGE`; `GET brouillon` shows `submitted`.
PC6 refusals -- a closed world, an unknown profile, the creator user as a
   profile, no draft -> 404 with their messages; a profile holding a
   character -> 409 on `POST brouillon`; none of them journals.
PC7 static (code tokens only) -- `routes/player_creation.py`,
   `writes/pc_drafts.py`, `pc_draft_reads.py` hold no `chat(`,
   `World.is_active`, `_world_id(`, `lore_selectors` import or `CREATOR`;
   the route module holds no `write_usage_event` and every route path
   starts with `/api/joueur/creation/`; the writer adds no canon table model.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. `creation_designer.chat` and
`ollama_client.ping` are swapped and restored in `finally`. A case not
reached is a FAILURE.
"""
from __future__ import annotations

import ast
import io
import json
import os
import pathlib
import sys
import tempfile
import tokenize

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
PKG = SRC / "world_engine"
SCRIPTS = ROOT / "scripts"
CHECKS = pathlib.Path(__file__).resolve().parent

ROUTE_MODULE = PKG / "cockpit" / "routes" / "player_creation.py"
WRITER_MODULE = PKG / "writes" / "pc_drafts.py"
READS_MODULE = PKG / "pc_draft_reads.py"
FORBIDDEN = ("chat(", "World.is_active", "_world_id(", "lore_selectors", "CREATOR")
CANON_MODELS = {"Entity", "Character", "Skill", "Knowledge", "FactionMembership", "Relation"}
PREFIX = "/api/joueur/creation/"
CATALOGUE_KEYS = {"rules", "ranks", "skills", "places", "factions"}
SKILL_KEYS = {"skill_key", "name", "base_domain", "system", "description", "requires_master", "start_rank",
              "max_rank"}
MESSAGES = {
    "name_missing": "Le personnage n'a pas de nom.",
    "story_missing": "L'histoire du personnage est vide.",
    "start_place_missing": "Choisis un lieu de départ.",
    "start_place_invalid": "Ce lieu de départ ne peut pas être choisi.",
    "too_many_sketches": "Au plus 8 personnes d'ancrage.",
    "master_without_sketch": "« Nécromancie » exige un maître : ajoute la personne qui te l'a enseignée.",
    "sketch_existing_invalid": "« L'ombre » : la personne choisie n'est pas connue de tous.",
    "membership_invalid": "Cette faction ne peut pas être choisie.",
    "pc_exists": "Ce joueur a déjà un personnage dans ce monde.",
}
SUBJECT = {"names": ["Hero"], "keywords": ["port"]}

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


def _seed_prompts(engine) -> None:
    from sqlmodel import Session

    sys.path.insert(0, str(SCRIPTS))
    import seed_pilot

    with Session(engine) as db:
        for entry in seed_pilot.CHARACTER_DESIGNER_PROMPT_HEADS:
            seed_pilot.upsert_prompt_template(db, **entry)
        db.commit()


def _add_location(db, wid: str, name: str, *, parent: str | None = None) -> str:
    from world_engine.models import Entity, Location

    entity = Entity(world_id=wid, type="location", name=name, is_public=True)
    db.add(entity)
    db.flush()
    db.add(Location(id=entity.id, parent_location_id=parent))
    db.flush()
    return entity.id


def _build(engine) -> dict:
    from sqlmodel import Session

    from world_engine.models import SkillDefinition, SkillSystem, User, World

    sys.path.insert(0, str(CHECKS))
    from perspective_isolation import _build_world

    ids = _build_world(engine)
    with Session(engine) as db:
        wid = ids["world"]
        world = db.get(World, wid)
        world.open_to_players = True
        db.add(world)
        closed = World(name="Fermé")
        db.add(closed)
        ids["port"] = _add_location(db, wid, "Port")
        ids["region"] = _add_location(db, wid, "Région")
        ids["quai"] = _add_location(db, wid, "Quai", parent=ids["region"])
        system = SkillSystem(world_id=wid, name="Arts")
        db.add(system)
        db.flush()
        for key, name, extra in (("escrime", "Escrime", {}),
                                 ("ombre", "Ombre", {"visible_at_creation": False}),
                                 ("necro", "Nécromancie", {"requires_master": True})):
            d = SkillDefinition(world_id=wid, system_id=system.id, name=name, base_domain="agility", **extra)
            db.add(d)
            db.flush()
            ids[key] = d.id
        db.add(User(id="user-creator", name="Creator", role="creator"))
        db.commit()
        ids["closed"] = closed.id
    return ids


def _events(engine) -> list[tuple[str, str, dict]]:
    from sqlmodel import Session, select

    from world_engine.models import LoreUsageEvent

    with Session(engine) as db:
        rows = db.exec(select(LoreUsageEvent).where(LoreUsageEvent.kind == "creation")
                       .order_by(LoreUsageEvent.created_at, LoreUsageEvent.id)).all()
        return [(r.step, r.outcome, r.payload) for r in rows]


def _key(profile: str, ids: dict) -> dict:
    return {"profile_id": profile, "world_id": ids["world"]}


def _save(client, profile: str, ids: dict, **fields):
    body = {**_key(profile, ids), "name": "Ilan", "story": "Ilan a grandi au port.",
            "start_location_id": ids["port"], "skills": [], "sketches": [], "memberships": [], "knowledge": []}
    body.update(fields)
    return client.put(PREFIX + "brouillon", json=body)


# ── PC1 ────────────────────────────────────────────────────────────────────


def rule_pc1(client, ana: str, ids: dict) -> int:
    resp = client.get(PREFIX + "catalogue", params=_key(ana, ids))
    if resp.status_code != 200:
        fail(f"PC1 catalogue answered {resp.status_code}: {resp.text[:200]}")
        return 0
    body = resp.json()
    if set(body) != CATALOGUE_KEYS:
        fail(f"PC1 catalogue keys {sorted(body)}")
    if len(body.get("ranks", [])) != 6:
        fail(f"PC1 ranks {body.get('ranks')!r}")
    keys = [s["skill_key"] for s in body.get("skills", [])]
    if keys != ["physical", "agility", "perception", "composure", ids["escrime"], ids["necro"]]:
        fail(f"PC1 skills {keys!r}")
    if ids["ombre"] in keys:
        fail("PC1 the invisible skill Ombre is in the catalogue")
    if any(set(s) != SKILL_KEYS for s in body.get("skills", [])):
        fail("PC1 a skill row's keys differ from C-14")
    if [s.get("system") for s in body.get("skills", [])][4:] != ["Arts", "Arts"]:
        fail("PC1 a visible skill does not carry its system")
    places = {p["entity_id"] for p in body.get("places", [])}
    if places != {ids["port"], ids["quai"]}:
        fail(f"PC1 places {places!r}")
    factions = [f["name"] for f in body.get("factions", [])]
    if factions != ["Guild", "Guild2"]:
        fail(f"PC1 factions {factions!r}")
    return 1


# ── PC2 ────────────────────────────────────────────────────────────────────


def rule_pc2(client, ana: str, ids: dict) -> int:
    reached = 0
    first = client.post(PREFIX + "brouillon", json=_key(ana, ids))
    again = client.post(PREFIX + "brouillon", json=_key(ana, ids))
    if first.status_code != 201 or again.status_code != 201:
        fail(f"PC2 POST brouillon answered {first.status_code}, {again.status_code}")
        return 0
    if first.json()["draft"]["id"] != again.json()["draft"]["id"]:
        fail("PC2 a second POST opened a second draft")
    reached += 1
    saved = _save(client, ana, ids, skills=[{"skill_key": ids["escrime"], "rank": 2}])
    if saved.status_code != 200 or saved.json()["verdict"]["spent"] != 1:
        fail(f"PC2 PUT answered {saved.status_code}: {saved.text[:200]}")
    elif saved.json()["draft"]["story"] != "Ilan a grandi au port.":
        fail("PC2 the story was not saved")
    reached += 1
    nine = [{"name": f"P{n}", "kind": "other"} for n in range(9)]
    too_many = _save(client, ana, ids, name="Autre", sketches=nine)
    after = client.get(PREFIX + "brouillon", params=_key(ana, ids)).json()["draft"]
    if too_many.status_code != 422 or too_many.json().get("detail") != "Au plus 8 personnes d'ancrage.":
        fail(f"PC2 nine sketches answered {too_many.status_code}: {too_many.text[:200]}")
    elif after["name"] != "Ilan" or after["sketches"]:
        fail("PC2 a refused PUT changed the draft")
    reached += 1
    master = _save(client, ana, ids, sketches=[{"name": "Maître", "kind": "master"}])
    if master.status_code != 422:
        fail(f"PC2 a master without a skill answered {master.status_code}")
    reached += 1
    return 1 if reached == 4 else 0


# ── PC3 ────────────────────────────────────────────────────────────────────


def _reset(db, draft, ids: dict) -> None:
    from sqlmodel import select

    from world_engine.models import PcDraftMembership, PcDraftSketch, PcDraftSkill

    for model in (PcDraftSkill, PcDraftSketch, PcDraftMembership):
        for row in db.exec(select(model).where(model.draft_id == draft.id)).all():
            db.delete(row)
    draft.name, draft.story = "Ilan", "Ilan a grandi au port."
    draft.start_location_id, draft.start_location_set_by = ids["port"], "player"
    db.add(draft)
    db.flush()


def rule_pc3(engine, client, ids: dict) -> int:
    from sqlmodel import Session

    from world_engine.creation_check import DRAFT_VIOLATION_CODES, check_draft
    from world_engine.models import (
        Character, Entity, PcDraft, PcDraftMembership, PcDraftSketch, PcDraftSkill,
    )

    bea = client.post("/api/joueur/profils", json={"name": "Bea"}).json()["id"]
    draft_id = client.post(PREFIX + "brouillon", json=_key(bea, ids)).json()["draft"]["id"]
    wid = ids["world"]

    def sketch(draft, position, name, **kw):
        return PcDraftSketch(draft_id=draft.id, world_id=wid, position=position, name=name,
                             kind=kw.pop("kind", "other"), origin="player", **kw)

    cases = {
        "name_missing": lambda db, d: setattr(d, "name", " "),
        "story_missing": lambda db, d: setattr(d, "story", ""),
        "start_place_missing": lambda db, d: setattr(d, "start_location_id", None),
        "start_place_invalid": lambda db, d: setattr(d, "start_location_id", ids["region"]),
        "too_many_sketches": lambda db, d: [db.add(sketch(d, n, f"P{n}")) for n in range(9)],
        "master_without_sketch": lambda db, d: db.add(PcDraftSkill(
            draft_id=d.id, world_id=wid, skill_key=ids["necro"], player_rank=1)),
        "sketch_existing_invalid": lambda db, d: db.add(sketch(d, 0, "L'ombre", existing_entity_id=ids["shade"])),
        "membership_invalid": lambda db, d: db.add(PcDraftMembership(
            draft_id=d.id, world_id=wid, faction_id=ids["cabal"], origin="player")),
    }
    seen = set()
    with Session(engine) as db:
        draft = db.get(PcDraft, draft_id)
        _reset(db, draft, ids)
        if check_draft(db, draft):
            fail(f"PC3 the clean draft has violations {check_draft(db, draft)!r}")
        for code, mutate in cases.items():
            _reset(db, draft, ids)
            mutate(db, draft)
            db.flush()
            found = [(v.code, v.message) for v in check_draft(db, draft)]
            if found != [(code, MESSAGES[code])]:
                fail(f"PC3 {code}: check_draft found {found!r}")
            seen.add(code)
        _reset(db, draft, ids)
        pc = Entity(world_id=wid, type="character", name="Bea PJ")
        db.add(pc)
        db.flush()
        db.add(Character(id=pc.id, world_id=wid, character_type="player", user_id=bea))
        db.flush()
        found = [(v.code, v.message) for v in check_draft(db, draft)]
        if found != [("pc_exists", MESSAGES["pc_exists"])]:
            fail(f"PC3 pc_exists: check_draft found {found!r}")
        seen.add("pc_exists")
        db.commit()
    if seen != set(DRAFT_VIOLATION_CODES):
        fail(f"PC3 codes not reached: {sorted(set(DRAFT_VIOLATION_CODES) - seen)}")
    ids["bea"] = bea
    return 1


# ── PC4 ────────────────────────────────────────────────────────────────────


def _design(*, sketch: str = "Mentor") -> dict:
    # Listed codes: s1-s4 the base domains, s5 Escrime, s6 Nécromancie (Ombre is never listed).
    return {"skills": [{"skill": "s5", "rank": 2, "reason": "au port"}],
            "sketches": [{"name": sketch, "kind": "other", "role": "ami"}],
            "start_place": "Port", "memberships": [{"faction": "Guild"}],
            "knowledge": [{"level": "rumor", "content": "On parle du port"}], "notes": []}


def rule_pc4(engine, client, ana: str, ids: dict, cd, ollama_client) -> int:
    from world_engine.llm_parse import LlmParseError  # noqa: F401 -- the stub's error is a reply

    reached = 0
    url, key = PREFIX + "concepteur", _key(ana, ids)
    _save(client, ana, ids, start_location_id=None, skills=[{"skill_key": ids["escrime"], "rank": 2}])

    def down(*args, **kwargs):
        raise ollama_client.OllamaError("down")

    before = len(_events(engine))
    ollama_client.ping = down
    resp = client.post(url, json=key)
    ollama_client.ping = lambda *a, **k: []
    rows = _events(engine)[before:]
    if resp.status_code != 503 or [(s, o) for s, o, _ in rows] != [("creation_subject", "unavailable")]:
        fail(f"PC4 ping down: {resp.status_code}, rows {[(s, o) for s, o, _ in rows]}")
    else:
        reached += 1

    cd.chat = _Stub(["pas du json"])
    before = len(_events(engine))
    resp = client.post(url, json=key)
    rows = _events(engine)[before:]
    if resp.status_code != 502 or [(s, o) for s, o, _ in rows] != [("creation_subject", "parse_error")]:
        fail(f"PC4 unparsable subject: {resp.status_code}, rows {[(s, o) for s, o, _ in rows]}")
    else:
        reached += 1

    cd.chat = _Stub([SUBJECT, "pas du json"])
    before = len(_events(engine))
    resp = client.post(url, json=key)
    rows = _events(engine)[before:]
    if resp.status_code != 502 or [(s, o) for s, o, _ in rows] != [
            ("creation_subject", "ok"), ("creation_design", "parse_error")]:
        fail(f"PC4 unparsable design: {resp.status_code}, rows {[(s, o) for s, o, _ in rows]}")
    else:
        reached += 1

    cd.chat = _Stub([SUBJECT, _design()])
    before = len(_events(engine))
    resp = client.post(url, json=key)
    rows = _events(engine)[before:]
    if resp.status_code != 200:
        fail(f"PC4 success answered {resp.status_code}: {resp.text[:300]}")
        return reached
    draft = resp.json()["draft"]
    if [(s, o) for s, o, _ in rows] != [("creation_subject", "ok"), ("creation_design", "ok")]:
        fail(f"PC4 success rows {[(s, o) for s, o, _ in rows]}")
    elif any(p["asked_by"] != f"player:{ana}" for _, _, p in rows):
        fail("PC4 a row is not asked by the player")
    escrime = [s for s in draft["skills"] if s["skill_key"] == ids["escrime"]]
    if not escrime or escrime[0]["designer_rank"] != 2 or escrime[0]["player_rank"] != 2:
        fail(f"PC4 the designer's rank is {escrime!r}")
    if [(s["name"], s["origin"]) for s in draft["sketches"]] != [("Mentor", "designer")]:
        fail(f"PC4 sketches {draft['sketches']!r}")
    if (draft["start_location"] or {}).get("entity_id") != ids["port"] or draft["start_location_set_by"] != "designer":
        fail(f"PC4 the start place is {draft['start_location']!r}, set by {draft['start_location_set_by']!r}")
    if "designer" not in resp.json():
        fail("PC4 the answer has no designer part")
    reached += 1

    mentor = draft["sketches"][0]
    edited = dict(mentor, role="vieil ami")
    edited.pop("existing_entity")
    _save(client, ana, ids, start_location_id=ids["port"], skills=[{"skill_key": ids["escrime"], "rank": 2}],
          sketches=[{k: edited[k] for k in ("id", "name", "role", "sentence", "group_label", "kind", "skill_key")}])
    cd.chat = _Stub([SUBJECT, _design(sketch="Rival")])
    resp = client.post(url, json=key)
    sketches = [(s["name"], s["role"], s["origin"]) for s in resp.json()["draft"]["sketches"]]
    if resp.status_code != 200 or sketches != [("Mentor", "vieil ami", "player"), ("Rival", "ami", "designer")]:
        fail(f"PC4 a second design gave {resp.status_code}, sketches {sketches!r}")
    else:
        reached += 1
    return reached


# ── PC5 ────────────────────────────────────────────────────────────────────


def rule_pc5(engine, client, ana: str, ids: dict, cd) -> int:
    from sqlmodel import Session

    from world_engine.creation_check import Violation
    from world_engine.models import PcDraft
    from world_engine.writes.pc_drafts import DRAFT_LOCKED_MESSAGE, submit_draft

    reached = 0
    key = _key(ana, ids)
    _save(client, ana, ids, name="", skills=[{"skill_key": ids["escrime"], "rank": 2}])
    resp = client.post(PREFIX + "soumettre", json=key)
    if resp.status_code != 200 or resp.json().get("submitted") is not False or resp.json()["draft"]["status"] != "draft":
        fail(f"PC5 a draft with a violation: {resp.status_code} {resp.text[:200]}")
    else:
        reached += 1

    draft_id = resp.json()["draft"]["id"]
    with Session(engine) as db:
        draft = db.get(PcDraft, draft_id)
        try:
            submit_draft(db, draft, (Violation("name_missing", None, "x"),))
            fail("PC5 submit_draft accepted a violation")
        except ValueError:
            reached += 1
        db.rollback()

    _save(client, ana, ids, skills=[{"skill_key": ids["escrime"], "rank": 2}])
    resp = client.post(PREFIX + "soumettre", json=key)
    body = resp.json()
    if resp.status_code != 200 or body.get("submitted") is not True or not body["draft"]["submitted_at"]:
        fail(f"PC5 a clean draft: {resp.status_code} {resp.text[:300]}")
    else:
        reached += 1
    cd.chat = _Stub([SUBJECT, _design()])
    locked = [_save(client, ana, ids), client.post(PREFIX + "concepteur", json=key),
              client.post(PREFIX + "soumettre", json=key)]
    if [(r.status_code, r.json().get("detail")) for r in locked] != [(409, DRAFT_LOCKED_MESSAGE)] * 3:
        fail(f"PC5 a submitted draft answered {[(r.status_code, r.json().get('detail')) for r in locked]}")
    else:
        reached += 1
    shown = client.get(PREFIX + "brouillon", params=key).json()["draft"]
    if shown["status"] != "submitted":
        fail(f"PC5 GET brouillon shows {shown['status']!r}")
    else:
        reached += 1
    return 1 if reached == 5 else 0


# ── PC6 ────────────────────────────────────────────────────────────────────


def rule_pc6(engine, client, ids: dict) -> int:
    from world_engine.cockpit.routes.player import PROFILE_NOT_FOUND, WORLD_NOT_FOUND
    from world_engine.cockpit.routes.player_creation import NO_DRAFT

    cara = client.post("/api/joueur/profils", json={"name": "Cara"}).json()["id"]
    before = len(_events(engine))
    cases = [
        (client.get(PREFIX + "catalogue", params={"profile_id": cara, "world_id": ids["closed"]}),
         404, WORLD_NOT_FOUND),
        (client.post(PREFIX + "brouillon", json={"profile_id": cara, "world_id": "nowhere"}), 404, WORLD_NOT_FOUND),
        (client.post(PREFIX + "brouillon", json=_key("nobody", ids)), 404, PROFILE_NOT_FOUND),
        (client.post(PREFIX + "brouillon", json=_key("user-creator", ids)), 404, PROFILE_NOT_FOUND),
        (_save(client, cara, ids), 404, NO_DRAFT),
        (client.post(PREFIX + "concepteur", json=_key(cara, ids)), 404, NO_DRAFT),
        (client.post(PREFIX + "soumettre", json=_key(cara, ids)), 404, NO_DRAFT),
        (client.post(PREFIX + "brouillon", json=_key(ids["bea"], ids)), 409, MESSAGES["pc_exists"]),
    ]
    for index, (resp, status, detail) in enumerate(cases):
        if resp.status_code != status or resp.json().get("detail") != detail:
            fail(f"PC6 case {index}: {resp.status_code} {resp.text[:160]}")
    if len(_events(engine)) != before:
        fail("PC6 a refusal was journaled")
    return 1


# ── PC7 ────────────────────────────────────────────────────────────────────


def _code(path: pathlib.Path) -> str:
    """The module's code tokens: strings and comments dropped."""
    kept = [tok.string for tok in tokenize.generate_tokens(io.StringIO(path.read_text(encoding="utf-8")).readline)
            if tok.type not in (tokenize.STRING, tokenize.COMMENT)]
    return "".join(kept)


def rule_pc7() -> int:
    reached = 0
    for path in (ROUTE_MODULE, WRITER_MODULE, READS_MODULE):
        if not path.exists():
            fail(f"PC7 {path.name} missing")
            continue
        code = _code(path)
        for needle in FORBIDDEN:
            if needle.replace(" ", "") in code:
                fail(f"PC7 {path.name} holds {needle}")
        reached += 1
    if ROUTE_MODULE.exists():
        if "write_usage_event" in _code(ROUTE_MODULE):
            fail("PC7 the route module calls write_usage_event")
        tree = ast.parse(ROUTE_MODULE.read_text(encoding="utf-8"))
        paths = [deco.args[0].value for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                 for deco in node.decorator_list
                 if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute)
                 and isinstance(deco.func.value, ast.Name) and deco.func.value.id == "router"
                 and deco.args and isinstance(deco.args[0], ast.Constant)]
        if not paths:
            fail("PC7 no route path found in player_creation.py")
        for path in paths:
            if not path.startswith(PREFIX):
                fail(f"PC7 route path {path!r} is outside {PREFIX}")
        reached += 1
    if WRITER_MODULE.exists():
        tree = ast.parse(WRITER_MODULE.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add"
                    and node.args and isinstance(node.args[0], ast.Call)
                    and isinstance(node.args[0].func, ast.Name) and node.args[0].func.id in CANON_MODELS):
                fail(f"PC7 the writer adds a canon {node.args[0].func.id}")
        reached += 1
    return 1 if reached == 5 else 0


def main() -> int:
    engine = _fresh_engine()
    _seed_prompts(engine)
    from fastapi.testclient import TestClient

    from world_engine import creation_designer as cd
    from world_engine import ollama_client
    from world_engine.cockpit.app import app

    ids = _build(engine)
    client = TestClient(app, base_url="http://127.0.0.1")
    original_chat, original_ping = cd.chat, ollama_client.ping
    ollama_client.ping = lambda *a, **k: []
    plan_count = 7
    reached = {}
    try:
        ana = client.post("/api/joueur/profils", json={"name": "Ana"}).json()["id"]
        plan = (
            ("PC1", lambda: rule_pc1(client, ana, ids), 1),
            ("PC2", lambda: rule_pc2(client, ana, ids), 1),
            ("PC3", lambda: rule_pc3(engine, client, ids), 1),
            ("PC4", lambda: rule_pc4(engine, client, ana, ids, cd, ollama_client), 5),
            ("PC5", lambda: rule_pc5(engine, client, ana, ids, cd), 1),
            ("PC6", lambda: rule_pc6(engine, client, ids), 1),
            ("PC7", rule_pc7, 1),
        )
        for name, rule, count in plan:
            got = 0
            try:
                got = rule()
            except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
                fail(f"{name} raised {type(exc).__name__}: {exc}")
            reached[name] = got
            if got != count:
                fail(f"{name} reached {got} of its {count} cases")
    finally:
        cd.chat, ollama_client.ping = original_chat, original_ping
    if len(reached) != plan_count:
        fail(f"{len(reached)} of {plan_count} rules ran")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: player_creation -- the catalogue in the public view, a draft opened once and saved whole, "
          "every draft violation alone, the designer journaled on every outcome, submission only through "
          "check_draft, refusals unjournaled, the creation modules held to the player's door")
    return 0


if __name__ == "__main__":
    sys.exit(main())
