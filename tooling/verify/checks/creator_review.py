"""G1 check for TICKET-0129 -- the creator reviews a submitted character: the one check of her final version, her choices beside the player's version, the return with a note.

Fixture (BRIEF-0129-C): an active world open to players; locations `Port`
(public), `Cave` (not public), zone `Région` with child `Quai`; a system
with `Nécromancie` (requires a master) and `Lame` (open); characters
`Vieux` (NPC, Nécromancie at rank 5), `Garde` (NPC, no rank 5), `Ombre`
(NPC, not public); factions `Guild` (active) and `Ancienne` (not active);
profiles Ana and Bea (`create_player_profile`); `Étranger`, a character of
a second world. Canon fixture rows go in through the models; the draft is
written through `writes/pc_drafts.py`.

CR1 -- `check_review`. Ana's clean submitted draft (name, story, Port,
   Nécromancie 1, a `master` sketch attached to Vieux, a `family` sketch to
   create, a membership in Guild) answers `()`. Each state below, alone on
   that draft (changed in a session then rolled back), gives exactly the
   listed codes with C-05's messages: empty name -> `name_missing`; empty
   story -> `story_missing`; no place on either column ->
   `start_place_missing`; review place `Région` -> `review_place_invalid`;
   Lame 5 -> `check_creation`'s own list; nine sketches ->
   `too_many_sketches`; the master sketch dropped -> `master_without_sketch`;
   the family sketch undecided -> `sketch_undecided`; the family sketch
   attached to `Étranger` (the FK forbids an unknown id) -> `attach_invalid`;
   two sketches attached to Garde -> `attach_duplicate` on the second; the
   master attached to Garde -> `master_not_master`; relation type
   `connects_to` -> `relation_type_invalid`; the membership on `Ancienne` ->
   `membership_invalid`; Bea holding a player character in the world ->
   `world_has_pc` alone; Ana holding one -> `pc_exists, world_has_pc`.
   Review place `Cave` (not public) and the master attached to `Ombre` once
   Ombre is a Maître -> no violation (the review reads all the lore). Every
   code of `REVIEW_VIOLATION_CODES` is reached.
CR2 -- routes. `GET /api/pc-reviews/{id}` answers exactly C-08's keys;
   `choices.relation_types` is the social subset of `RELATION_TYPES`;
   `choices.places` holds Port, Cave, Quai and not Région;
   `choices.characters` holds Vieux, Garde, Ombre and no player character;
   `choices.masters` maps Nécromancie to `[Vieux]`; `groups` lists the
   family's group with `lot: None`. `PUT` with a place, every sketch's
   action and a dropped membership -> 200, the GET shape shows them,
   `verdict.violations` empty; an unknown sketch id, action `x`, intensity
   0 -> 422 with C-06's messages and nothing changed; Bea's `draft`-status
   draft -> 404; a submitted draft of a non-active world -> 404.
CR3 -- return. `POST renvoyer` with an empty note -> 422 `Écris une note
   pour le joueur.`; with a note -> 200, status `returned`, `creator_note`
   stripped; `GET /api/pc-drafts` no longer lists it; `PUT
   /api/pc-reviews/{id}` on it -> 404; the player's `GET
   /api/joueur/creation/brouillon` answers it with `status: "returned"`, the
   note, and exactly `draft_view`'s keys (C-13, no review key); the
   player's `PUT` -> 200; `_writable` on the `returned` draft raises
   nothing; `soumettre` -> `submitted: true`; the review columns of the
   sketches the player kept are unchanged.
CR4 -- static (code tokens). `pc_draft_reads.py` and
   `routes/player_creation.py` contain no `review_`; every path of
   `routes/pc_review.py` starts with `/api/pc-reviews/` or
   `/api/pc-profiles`; `routes/pc_review.py` and `pc_review_reads.py` contain
   no `chat(` and no `public_view(`; the body of `check_review` (by `ast`)
   calls no `public_view`; `app.py` holds
   `app.include_router(_routes_pc_review.router)`.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A case not reached is a FAILURE.
"""
from __future__ import annotations

import ast
import io
import os
import pathlib
import sys
import tempfile
import tokenize

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
PKG = SRC / "world_engine"
REVIEW_ROUTES = PKG / "cockpit" / "routes" / "pc_review.py"
REVIEW_READS = PKG / "pc_review_reads.py"
PLAYER_READS = PKG / "pc_draft_reads.py"
PLAYER_ROUTES = PKG / "cockpit" / "routes" / "player_creation.py"
CHECK_MODULE = PKG / "creation_check.py"
APP_PY = PKG / "cockpit" / "app.py"
INCLUDE_LINE = "app.include_router(_routes_pc_review.router)"
GET_KEYS = {"draft", "player_name", "review", "choices", "verdict", "skill_names", "ranks", "groups",
            "blockers"}
# draft_view's keys (C-13 of TICKET-0126): the player's shape.
DRAFT_VIEW_KEYS = {"id", "world_id", "status", "name", "story", "start_location", "start_location_set_by",
                   "creator_note", "submitted_at", "skills", "sketches", "memberships", "knowledge"}

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


# C-05's messages, by code (the review codes and the draft codes check_review reuses).
MESSAGES = {
    "name_missing": "Le personnage n'a pas de nom.",
    "story_missing": "L'histoire du personnage est vide.",
    "start_place_missing": "Choisis un lieu de départ.",
    "review_place_invalid": "Ce lieu de départ ne peut pas être choisi.",
    "too_many_sketches": "Au plus 8 personnes d'ancrage.",
    "master_without_sketch": "« Nécromancie » exige un maître : ajoute la personne qui te l'a enseignée.",
    "sketch_undecided": "« Sœur » : choisis de créer cette personne, de la rattacher ou de l'écarter.",
    "attach_invalid": "« Sœur » : le personnage choisi n'existe pas dans ce monde.",
    "attach_duplicate": "« Cousin » : ce personnage est déjà choisi pour une autre personne.",
    "master_not_master": "« Maître Os » n'est pas Maître en « Nécromancie ».",
    "relation_type_invalid": "« Sœur » : le lien « connects_to » ne peut pas être choisi.",
    "membership_invalid": "Cette faction ne peut pas être choisie.",
    "pc_exists": "Ce joueur a déjà un personnage dans ce monde.",
    "world_has_pc": "Ce monde a déjà un personnage joueur : l'approbation attend le sélecteur « PJ actif ».",
}


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


def _entity(db, world_id: str, kind: str, name: str, *, public: bool = True, status: str = "active") -> str:
    from world_engine.models import Entity

    entity = Entity(world_id=world_id, type=kind, name=name, is_public=public, status=status)
    db.add(entity)
    db.flush()
    return entity.id


def _location(db, world_id: str, name: str, *, public: bool = True, parent: str | None = None) -> str:
    from world_engine.models import Location

    entity_id = _entity(db, world_id, "location", name, public=public)
    db.add(Location(id=entity_id, parent_location_id=parent))
    db.flush()
    return entity_id


def _npc(db, world_id: str, name: str, *, public: bool = True) -> str:
    from world_engine.models import Character

    entity_id = _entity(db, world_id, "character", name, public=public)
    db.add(Character(id=entity_id, world_id=world_id, character_type="npc"))
    db.flush()
    return entity_id


def _faction(db, world_id: str, name: str, *, status: str = "active") -> str:
    from world_engine.models import Faction

    entity_id = _entity(db, world_id, "faction", name, status=status)
    db.add(Faction(id=entity_id))
    db.flush()
    return entity_id


def _world(db) -> dict:
    from world_engine.models import SkillDefinition, SkillSystem, World
    from world_engine.writes.characters import write_skill_row
    from world_engine.writes.users import create_player_profile

    world = World(name="Revue", is_active=True, open_to_players=True)
    other = World(name="Ailleurs", is_active=False, open_to_players=False)
    db.add(world)
    db.add(other)
    db.flush()
    ids = {"world": world.id, "other": other.id}
    ids["port"] = _location(db, world.id, "Port")
    ids["cave"] = _location(db, world.id, "Cave", public=False)
    ids["region"] = _location(db, world.id, "Région")
    ids["quai"] = _location(db, world.id, "Quai", parent=ids["region"])
    system = SkillSystem(world_id=world.id, name="Arts")
    db.add(system)
    db.flush()
    necro = SkillDefinition(world_id=world.id, name="Nécromancie", base_domain="composure",
                            system_id=system.id, requires_master=True)
    lame = SkillDefinition(world_id=world.id, name="Lame", base_domain="agility", system_id=system.id)
    db.add(necro)
    db.add(lame)
    db.flush()
    ids["necro"], ids["lame"] = necro.id, lame.id
    ids["vieux"] = _npc(db, world.id, "Vieux")
    ids["garde"] = _npc(db, world.id, "Garde")
    ids["ombre"] = _npc(db, world.id, "Ombre", public=False)
    ids["etranger"] = _npc(db, other.id, "Étranger")
    write_skill_row(db, character_id=ids["vieux"], rank=5, skill_definition_id=necro.id)
    ids["guild"] = _faction(db, world.id, "Guild")
    ids["ancienne"] = _faction(db, world.id, "Ancienne", status="archived")
    ids["ana"] = create_player_profile(db, "Ana").id
    ids["bea"] = create_player_profile(db, "Bea").id
    return ids


def _side_drafts(db, ids: dict) -> None:
    """Bea's draft still in `draft` status; Ana's submitted draft in the non-active world."""
    from world_engine.writes.pc_drafts import open_draft, save_player_draft, submit_draft

    bea = open_draft(db, world_id=ids["world"], user_id=ids["bea"])
    ids["bea_draft"] = bea.id
    other = open_draft(db, world_id=ids["other"], user_id=ids["ana"])
    save_player_draft(db, other, name="Loin", story="Ailleurs.", start_location_id=None, skills=[],
                      sketches=[], memberships=[], knowledge=[])
    submit_draft(db, other, ())
    ids["other_draft"] = other.id


def _clean_draft(db, ids: dict) -> str:
    from world_engine.models import PcDraftSketch
    from world_engine.writes.pc_drafts import open_draft, save_player_draft, save_review, submit_draft
    from sqlmodel import select

    draft = open_draft(db, world_id=ids["world"], user_id=ids["ana"])
    save_player_draft(
        db, draft, name="Ilse", story="Une histoire.", start_location_id=ids["port"],
        skills=[{"skill_key": ids["necro"], "rank": 1}],
        sketches=[{"name": "Maître Os", "kind": "master", "skill_key": ids["necro"]},
                  {"name": "Sœur", "kind": "family", "group_label": "famille"}],
        memberships=[{"faction_id": ids["guild"], "role": None}], knowledge=[],
    )
    submit_draft(db, draft, ())
    rows = db.exec(select(PcDraftSketch).where(PcDraftSketch.draft_id == draft.id)
                   .order_by(PcDraftSketch.position)).all()
    ids["master_sketch"], ids["family_sketch"] = rows[0].id, rows[1].id
    save_review(db, draft, review_location_id=None, sketches=[
        {"id": rows[0].id, "action": "attach", "entity_id": ids["vieux"], "relation_type": "", "intensity": 60},
        {"id": rows[1].id, "action": "create", "entity_id": None, "relation_type": "ally", "intensity": 60},
    ], memberships=[])
    return draft.id


# --- CR1 -----------------------------------------------------------------------


def _sketch(db, ids, key):
    from world_engine.models import PcDraftSketch

    return db.get(PcDraftSketch, ids[key])


def _set(db, row, **values) -> None:
    for name, value in values.items():
        setattr(row, name, value)
    db.add(row)


def _add_pc(db, ids, user_key: str) -> None:
    from world_engine.models import Character

    entity_id = _entity(db, ids["world"], "character", f"PJ de {user_key}")
    db.add(Character(id=entity_id, world_id=ids["world"], character_type="player", user_id=ids[user_key]))


def _cases(ids: dict) -> list[tuple[str, object, list[str] | None]]:
    """(label, change(db, draft), expected codes -- None: check_creation's own list)."""
    from world_engine.models import PcDraftMembership, PcDraftSketch, PcDraftSkill
    from sqlmodel import select

    def membership(db, draft):
        return db.exec(select(PcDraftMembership).where(PcDraftMembership.draft_id == draft.id)).one()

    def nine(db, draft):
        for position in range(2, 9):
            db.add(PcDraftSketch(draft_id=draft.id, world_id=draft.world_id, position=position,
                                 name=f"Ami {position}", kind="other", origin="player", review_action="create"))

    def duplicate(db, draft):
        _set(db, _sketch(db, ids, "family_sketch"), review_action="attach", review_entity_id=ids["garde"])
        db.add(PcDraftSketch(draft_id=draft.id, world_id=draft.world_id, position=2, name="Cousin",
                             kind="other", origin="player", review_action="attach", review_entity_id=ids["garde"]))

    return [
        ("empty name", lambda db, d: _set(db, d, name=""), ["name_missing"]),
        ("empty story", lambda db, d: _set(db, d, story=""), ["story_missing"]),
        ("no place", lambda db, d: _set(db, d, start_location_id=None, review_location_id=None),
         ["start_place_missing"]),
        ("review place Région", lambda db, d: _set(db, d, review_location_id=ids["region"]),
         ["review_place_invalid"]),
        ("Lame 5", lambda db, d: db.add(PcDraftSkill(draft_id=d.id, world_id=d.world_id,
                                                      skill_key=ids["lame"], player_rank=5)), None),
        ("nine sketches", nine, ["too_many_sketches"]),
        ("the master dropped", lambda db, d: _set(db, _sketch(db, ids, "master_sketch"),
                                                  review_action="drop", review_entity_id=None),
         ["master_without_sketch"]),
        ("the family undecided", lambda db, d: _set(db, _sketch(db, ids, "family_sketch"), review_action=None),
         ["sketch_undecided"]),
        ("the family attached to another world's character",
         lambda db, d: _set(db, _sketch(db, ids, "family_sketch"), review_action="attach",
                            review_entity_id=ids["etranger"]), ["attach_invalid"]),
        ("two sketches attached to Garde", duplicate, ["attach_duplicate"]),
        ("the master attached to Garde", lambda db, d: _set(db, _sketch(db, ids, "master_sketch"),
                                                            review_entity_id=ids["garde"]),
         ["master_not_master"]),
        ("relation type connects_to", lambda db, d: _set(db, _sketch(db, ids, "family_sketch"),
                                                         review_relation_type="connects_to"),
         ["relation_type_invalid"]),
        ("the membership on Ancienne", lambda db, d: _set(db, membership(db, d), faction_id=ids["ancienne"]),
         ["membership_invalid"]),
        ("Bea holds a player character", lambda db, d: _add_pc(db, ids, "bea"), ["world_has_pc"]),
        ("Ana holds a player character", lambda db, d: _add_pc(db, ids, "ana"), ["pc_exists", "world_has_pc"]),
        ("review place Cave (not public)", lambda db, d: _set(db, d, review_location_id=ids["cave"]), []),
    ]


def rule_cr1(engine, ids: dict, draft_id: str) -> int:
    from sqlmodel import Session

    from world_engine.creation_check import REVIEW_VIOLATION_CODES, check_creation, check_review
    from world_engine.models import PcDraft
    from world_engine.writes.characters import write_skill_row

    reached: set[str] = set()
    with Session(engine) as db:
        clean = check_review(db, db.get(PcDraft, draft_id))
        if clean != ():
            fail(f"CR1 the clean draft answers {[v.code for v in clean]}")
    cases = _cases(ids)
    for label, change, expected in cases:
        with Session(engine) as db:
            draft = db.get(PcDraft, draft_id)
            change(db, draft)
            db.flush()
            got = check_review(db, draft)
            if expected is None:
                expected = [v.code for v in check_creation(
                    db, ids["world"], {ids["necro"]: 1, ids["lame"]: 5}, enforce_visibility=True).violations]
                if not expected:
                    fail(f"CR1 {label}: check_creation found nothing")
            if [v.code for v in got] != expected:
                fail(f"CR1 {label}: codes {[v.code for v in got]}, expected {expected}")
            for violation in got:
                reached.add(violation.code)
                want = MESSAGES.get(violation.code)
                if want is not None and violation.message != want:
                    fail(f"CR1 {label}: {violation.code} reads {violation.message!r}, expected {want!r}")
            db.rollback()
    with Session(engine) as db:
        write_skill_row(db, character_id=ids["ombre"], rank=5, skill_definition_id=ids["necro"])
        draft = db.get(PcDraft, draft_id)
        _set(db, _sketch(db, ids, "master_sketch"), review_entity_id=ids["ombre"])
        db.flush()
        got = check_review(db, draft)
        if got != ():
            fail(f"CR1 the master attached to Ombre, a Maître not public: {[v.code for v in got]}")
        db.rollback()
    for code in REVIEW_VIOLATION_CODES:
        if code not in reached:
            fail(f"CR1 the review code {code} was never reached")
    return 1 if len(cases) == 16 else 0


# --- CR2 -----------------------------------------------------------------------


def _names(rows) -> set[str]:
    return {row.get("name") for row in rows}


def rule_cr2(client, ids: dict, draft_id: str) -> int:
    from world_engine.cockpit.crud._shared import RELATION_TYPES
    from world_engine.relation_orientation import is_social

    url = f"/api/pc-reviews/{draft_id}"
    resp = client.get(url)
    if resp.status_code != 200:
        fail(f"CR2 GET answered {resp.status_code}: {resp.text[:200]}")
        return 0
    body = resp.json()
    if set(body) != GET_KEYS:
        fail(f"CR2 GET keys {sorted(body)}")
    choices = body.get("choices", {})
    if choices.get("relation_types") != [t for t in RELATION_TYPES if is_social(t)]:
        fail(f"CR2 relation_types {choices.get('relation_types')!r}")
    places = _names(choices.get("places", []))
    if not {"Port", "Cave", "Quai"} <= places or "Région" in places:
        fail(f"CR2 places {sorted(places)}")
    characters = _names(choices.get("characters", []))
    if characters != {"Vieux", "Garde", "Ombre"}:
        fail(f"CR2 characters {sorted(characters)}")
    if [m.get("name") for m in choices.get("masters", {}).get(ids["necro"], [])] != ["Vieux"]:
        fail(f"CR2 masters {choices.get('masters')!r}")
    if body.get("groups") != [{"label": "famille", "sketch_ids": [ids["family_sketch"]], "lot": None}]:
        fail(f"CR2 groups {body.get('groups')!r}")
    if body.get("blockers") != []:
        fail(f"CR2 blockers {body.get('blockers')!r}")

    good = {"review_location_id": ids["cave"],
            "sketches": [{"id": ids["master_sketch"], "action": "attach", "entity_id": ids["vieux"],
                          "relation_type": "interest", "intensity": 80},
                         {"id": ids["family_sketch"], "action": "create", "entity_id": None,
                          "relation_type": "", "intensity": 40}],
            "memberships": [{"id": body["draft"]["memberships"][0]["id"], "dropped": True}]}
    resp = client.put(url, json=good)
    if resp.status_code != 200:
        fail(f"CR2 PUT answered {resp.status_code}: {resp.text[:200]}")
        return 0
    review = resp.json().get("review", {})
    sketches = {s["id"]: s for s in review.get("sketches", [])}
    master, family = sketches.get(ids["master_sketch"], {}), sketches.get(ids["family_sketch"], {})
    if ((review.get("review_location") or {}).get("entity_id") != ids["cave"]
            or (review.get("place") or {}).get("name") != "Cave"
            or master.get("action") != "attach" or (master.get("entity") or {}).get("name") != "Vieux"
            or master.get("relation_type") != "interest" or master.get("intensity") != 80
            or family.get("action") != "create" or family.get("entity") is not None
            or family.get("relation_type") != "ally" or family.get("intensity") != 40
            or [m.get("dropped") for m in review.get("memberships", [])] != [True]):
        fail(f"CR2 the PUT's review reads {review!r}")
    if resp.json().get("verdict", {}).get("violations") != []:
        fail(f"CR2 the reviewed draft's violations {resp.json().get('verdict', {}).get('violations')!r}")

    before = client.get(url).json()
    for label, sketch, message in (
            ("an unknown sketch id", {"id": "nobody", "action": "create"}, "Personne inconnue."),
            ("action x", {"id": ids["family_sketch"], "action": "x"}, "Choix inconnu."),
            ("intensity 0", {"id": ids["family_sketch"], "action": "create", "intensity": 0},
             "L'intensité va de 1 à 100.")):
        resp = client.put(url, json={"review_location_id": None, "sketches": [sketch], "memberships": []})
        if resp.status_code != 422 or resp.json().get("detail") != message:
            fail(f"CR2 {label} answered {resp.status_code}: {resp.text[:200]}")
        if client.get(url).json() != before:
            fail(f"CR2 {label} changed the draft")
    for label, other in (("a draft-status draft", ids["bea_draft"]), ("another world's draft", ids["other_draft"])):
        resp = client.get(f"/api/pc-reviews/{other}")
        if resp.status_code != 404 or resp.json().get("detail") != "Brouillon introuvable.":
            fail(f"CR2 {label} answered {resp.status_code}: {resp.text[:200]}")
    return 1


# --- CR3 -----------------------------------------------------------------------


def rule_cr3(engine, client, ids: dict, draft_id: str) -> int:
    from sqlmodel import Session

    from world_engine.cockpit.routes.player_creation import _writable
    from world_engine.models import PcDraft
    from world_engine.pc_review_reads import review_view

    url = f"/api/pc-reviews/{draft_id}"
    kept = {s["id"]: s for s in client.get(url).json()["review"]["sketches"]}
    resp = client.post(f"{url}/renvoyer", json={"note": "   "})
    if resp.status_code != 422 or resp.json().get("detail") != "Écris une note pour le joueur.":
        fail(f"CR3 an empty note answered {resp.status_code}: {resp.text[:200]}")
    resp = client.post(f"{url}/renvoyer", json={"note": "  Revois ton maître.  "})
    if resp.status_code != 200 or resp.json() != {"ok": True, "status": "returned"}:
        fail(f"CR3 renvoyer answered {resp.status_code}: {resp.text[:200]}")
        return 0
    with Session(engine) as db:
        draft = db.get(PcDraft, draft_id)
        if draft.status != "returned" or draft.creator_note != "Revois ton maître.":
            fail(f"CR3 the returned draft reads {draft.status!r}, {draft.creator_note!r}")
    if draft_id in [d.get("id") for d in client.get("/api/pc-drafts").json()]:
        fail("CR3 GET /api/pc-drafts still lists the returned draft")
    resp = client.put(url, json={"review_location_id": None, "sketches": [], "memberships": []})
    if resp.status_code != 404:
        fail(f"CR3 PUT on a returned draft answered {resp.status_code}")

    query = {"profile_id": ids["ana"], "world_id": ids["world"]}
    resp = client.get("/api/joueur/creation/brouillon", params=query)
    seen = resp.json().get("draft") or {}
    if resp.status_code != 200 or seen.get("status") != "returned" or seen.get("creator_note") != "Revois ton maître.":
        fail(f"CR3 the player's GET answered {resp.status_code}: {resp.text[:300]}")
    if set(seen) != DRAFT_VIEW_KEYS:
        fail(f"CR3 the player's draft keys {sorted(seen)}, expected draft_view's")
    sketches = [{"id": s["id"], "name": s["name"], "role": s["role"], "sentence": s["sentence"],
                 "group_label": s["group_label"], "kind": s["kind"], "skill_key": s["skill_key"]}
                for s in seen.get("sketches", [])]
    resp = client.put("/api/joueur/creation/brouillon", json={
        **query, "name": "Ilse", "story": "Une histoire revue.", "start_location_id": ids["port"],
        "skills": [{"skill_key": ids["necro"], "rank": 1}], "sketches": sketches,
        "memberships": [{"faction_id": ids["guild"]}], "knowledge": []})
    if resp.status_code != 200:
        fail(f"CR3 the player's PUT answered {resp.status_code}: {resp.text[:200]}")
    with Session(engine) as db:
        try:
            _writable(db.get(PcDraft, draft_id))
        except Exception as exc:  # noqa: BLE001 -- any refusal is the failure
            fail(f"CR3 _writable refused the returned draft: {exc}")
    resp = client.post("/api/joueur/creation/soumettre", json=query)
    if resp.status_code != 200 or resp.json().get("submitted") is not True:
        fail(f"CR3 soumettre answered {resp.status_code}: {resp.text[:300]}")
    with Session(engine) as db:
        after = {s["id"]: s for s in review_view(db, db.get(PcDraft, draft_id))["sketches"]}
    if not kept or after != kept:
        fail(f"CR3 the kept sketches' review columns moved: {kept!r} -> {after!r}")
    return 1


# --- CR4 -----------------------------------------------------------------------


def _code(path: pathlib.Path) -> str:
    """The module's code tokens: strings and comments dropped."""
    source = path.read_text(encoding="utf-8")
    return "".join(tok.string for tok in tokenize.generate_tokens(io.StringIO(source).readline)
                   if tok.type not in (tokenize.STRING, tokenize.COMMENT))


def _route_paths(path: pathlib.Path) -> list[str]:
    paths = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for deco in node.decorator_list:
                if (isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute)
                        and isinstance(deco.func.value, ast.Name) and deco.func.value.id == "router"
                        and deco.args and isinstance(deco.args[0], ast.Constant)):
                    paths.append(deco.args[0].value)
    return paths


def rule_cr4() -> int:
    for path in (REVIEW_ROUTES, REVIEW_READS, PLAYER_READS, PLAYER_ROUTES, CHECK_MODULE, APP_PY):
        if not path.exists():
            fail(f"CR4 {path.relative_to(ROOT)} missing")
            return 0
    for path in (PLAYER_READS, PLAYER_ROUTES):
        if "review_" in _code(path):
            fail(f"CR4 {path.name} names a review column")
    paths = _route_paths(REVIEW_ROUTES)
    if not paths:
        fail("CR4 routes/pc_review.py declares no route")
    for route in paths:
        if not (route.startswith("/api/pc-reviews/") or route.startswith("/api/pc-profiles")):
            fail(f"CR4 routes/pc_review.py path {route}")
    for path in (REVIEW_ROUTES, REVIEW_READS):
        code = _code(path)
        for needle in ("chat(", "public_view("):
            if needle in code:
                fail(f"CR4 {path.name} holds {needle}")
    tree = ast.parse(CHECK_MODULE.read_text(encoding="utf-8"))
    body = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "check_review"), None)
    if body is None:
        fail("CR4 creation_check.py declares no check_review")
    elif any(isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", None)) == "public_view"
             for n in ast.walk(body)):
        fail("CR4 check_review calls public_view")
    if INCLUDE_LINE not in APP_PY.read_text(encoding="utf-8"):
        fail(f"CR4 cockpit/app.py lacks {INCLUDE_LINE}")
    return 1


def main() -> int:
    engine = _fresh_engine()
    from sqlmodel import Session

    from fastapi.testclient import TestClient

    from world_engine.cockpit.app import app

    plan = [("CR4", rule_cr4)]
    try:
        with Session(engine) as db:
            ids = _world(db)
            draft_id = _clean_draft(db, ids)
            _side_drafts(db, ids)
            db.commit()
        client = TestClient(app, base_url="http://127.0.0.1")
        plan = [("CR1", lambda: rule_cr1(engine, ids, draft_id)),
                ("CR2", lambda: rule_cr2(client, ids, draft_id)),
                ("CR3", lambda: rule_cr3(engine, client, ids, draft_id))] + plan
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"fixture raised {type(exc).__name__}: {exc}")
    reached = 0
    for name, rule in plan:
        try:
            got = rule()
        except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
            fail(f"{name} raised {type(exc).__name__}: {exc}")
            got = 0
        if got != 1:
            fail(f"{name} was not reached")
        reached += got
    if reached != 4:
        fail(f"{reached} of 4 rules reached")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: creator_review -- the one check of the creator's final version, every review code "
          "reached with its message, all the lore read; her choices beside the player's version; the "
          "return with a note reopens the draft to its player, who never reads a review column")
    return 0


if __name__ == "__main__":
    sys.exit(main())
