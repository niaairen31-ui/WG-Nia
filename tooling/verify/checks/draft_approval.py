"""G1 check for TICKET-0129 (BRIEF-0129-E) -- the approval writes a drafted character to canon in one transaction, or nothing.

Fixture: an active world; `Port`, `Quai` (visitable); a system with
`Nécromancie` (requires a master) and `Lame` (open); NPCs `Vieux`
(Nécromancie 5, public) and `Ami`; faction `Guild` with members `Membre`
(public, open membership), `Espion` (public, secret membership), `Cache`
(not public, open membership), and a second faction `Autre`; profiles Ana
and Bea; a creator user. Ana's submitted draft `Kael` (two story lines,
place Port reviewed to Quai; Lame 2, perception 2, Nécromancie 1; sketches
`Mère` -- family, group `Famille`, create, ally 70 --, `Maître Sol` --
master of Nécromancie, `Famille`, create, fascination 80 --, `Ami` --
other, attached to Ami, interest 55 --, `Rival` -- other, dropped; a
membership in Guild as `apprenti` and one dropped in Autre; two knowledge
lines, `rumor` and `knows`). Batch `Famille` prepared and generated (two
rows), the generator stubbed by assignment as in `creator_review.py` CR5.
Rules run DA5, DA2, DA3, DA1, DA4: each refusal leaves the fixture as it
found it.

DA1 -- success. `POST /api/pc-reviews/{id}/approuver` -> 200 with
   `character_id` and `name == "Kael"`; one player character, Ana's, at
   Quai; the draft `approved` naming it; the batch and both rows
   `committed`; NPCs `Mère` and `Maître Sol`; `skill_masters` for
   Nécromancie holding Vieux and Maître Sol; Kael's skills exactly the four
   base domains (perception 2, the others 1), Lame 2, Nécromancie 1 taught
   by Maître Sol; one active membership in Guild as `apprenti`, none in
   Autre; two `knowledge` rows, `is_secret` false, at `rumor` and `knows`;
   one `histoire` fact per story line about Kael; relations Mère -> Kael
   (ally 70), Maître Sol -> Kael (fascination 80), Ami -> Kael (interest
   55), each `a_to_b` with its sketch's role as `notes`, none from Rival;
   encounters Kael-Membre `pc_creation`, none Kael-Espion nor Kael-Cache;
   Kael-Mère, Kael-Maître Sol, Kael-Ami `relation`.
DA2 -- atomicity. `pc_approval.write_relation` replaced by a stub raising
   `ValueError("boom")` (restored in `finally`) -> 409 `boom`; the counts
   of `entity`, `character`, `skill`, `faction_membership`, `knowledge`,
   `relation`, `rencontre`, `fact` unchanged; the draft `submitted` with no
   `character_id`; the batch `open`, its rows `proposed`.
DA3 -- refusals, each 409 `Ce personnage ne peut pas encore être approuvé.`
   with every count unchanged: Rival undecided; the `Famille` batch
   abandoned (`lot_missing`); a row rejected (`row_missing`); Bea holding a
   player character in the world (`world_has_pc`). After DA1, the approved
   draft approved again -> 404 `Brouillon introuvable.`.
DA4 -- the creator's route `POST /api/characters/player` still creates a
   character at the four base domains and the open skills at rank 1
   (`write_player_character` called without `ranks` nor `teachers`), no
   row for a skill that requires a master, and refuses a second one for
   the creator with its `{"ok": false}` answer.
DA5 -- static (code tokens: strings and comments dropped).
   `cockpit/pc_approval.py` holds no `db.add(`, `.commit(`, `.flush(`,
   `chat(` outside `prepare_group_lot` and `abandon_review_lots` -- D's two
   functions that stage an ephemeral review batch (BRIEF-0129-D) -- and no
   `.commit(` nor `chat(` anywhere; `routes/pc_review.py`'s
   `approve_review` holds exactly one `db.commit()`;
   `writes/player_characters.py` names neither `npc_batch` nor `NpcBatch`.

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
APPROVAL = PKG / "cockpit" / "pc_approval.py"
REVIEW_ROUTES = PKG / "cockpit" / "routes" / "pc_review.py"
PC_WRITER = PKG / "writes" / "player_characters.py"
STAGING_FUNCTIONS = ("prepare_group_lot", "abandon_review_lots")
REFUSED = "Ce personnage ne peut pas encore être approuvé."
COUNTED = ("entity", "character", "skill", "faction_membership", "knowledge", "relation", "rencontre", "fact")
STORY = "Né sur le port.\nInstruit dans les cryptes."

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


def _entity(db, world_id: str, kind: str, name: str, *, public: bool = True) -> str:
    from world_engine.models import Entity

    entity = Entity(world_id=world_id, type=kind, name=name, is_public=public, status="active")
    db.add(entity)
    db.flush()
    return entity.id


def _location(db, world_id: str, name: str) -> str:
    from world_engine.models import Location

    entity_id = _entity(db, world_id, "location", name)
    db.add(Location(id=entity_id))
    db.flush()
    return entity_id


def _npc(db, world_id: str, name: str, *, public: bool = True) -> str:
    from world_engine.models import Character

    entity_id = _entity(db, world_id, "character", name, public=public)
    db.add(Character(id=entity_id, world_id=world_id, character_type="npc"))
    db.flush()
    return entity_id


def _faction(db, world_id: str, name: str) -> str:
    from world_engine.models import Faction

    entity_id = _entity(db, world_id, "faction", name)
    db.add(Faction(id=entity_id))
    db.flush()
    return entity_id


def _world(db) -> dict:
    from world_engine.models import SkillDefinition, SkillSystem, User, World
    from world_engine.writes.characters import write_skill_row
    from world_engine.writes.factions import write_membership
    from world_engine.writes.users import create_player_profile

    world = World(name="Approbation", is_active=True, open_to_players=True)
    db.add(world)
    db.flush()
    ids = {"world": world.id}
    ids["port"] = _location(db, world.id, "Port")
    ids["quai"] = _location(db, world.id, "Quai")
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
    ids["ami"] = _npc(db, world.id, "Ami")
    write_skill_row(db, character_id=ids["vieux"], rank=5, skill_definition_id=necro.id)
    ids["guild"] = _faction(db, world.id, "Guild")
    ids["autre"] = _faction(db, world.id, "Autre")
    ids["membre"] = _npc(db, world.id, "Membre")
    ids["espion"] = _npc(db, world.id, "Espion")
    ids["cache"] = _npc(db, world.id, "Cache", public=False)
    for key, secret in (("membre", False), ("espion", True), ("cache", False)):
        write_membership(db, mode="open", world_id=world.id, entity_id=ids[key], faction_id=ids["guild"],
                         is_secret=secret)
    ids["ana"] = create_player_profile(db, "Ana").id
    ids["bea"] = create_player_profile(db, "Bea").id
    creator = User(name="Créatrice", role="creator")
    db.add(creator)
    db.flush()
    ids["creator"] = creator.id
    return ids


def _draft(db, ids: dict) -> None:
    """Ana's reviewed draft `Kael` (see the docstring)."""
    from sqlmodel import select

    from world_engine.models import PcDraftMembership, PcDraftSketch
    from world_engine.writes.pc_drafts import open_draft, save_player_draft, save_review, submit_draft

    draft = open_draft(db, world_id=ids["world"], user_id=ids["ana"])
    save_player_draft(
        db, draft, name="Kael", story=STORY, start_location_id=ids["port"],
        skills=[{"skill_key": ids["lame"], "rank": 2}, {"skill_key": "perception", "rank": 2},
                {"skill_key": ids["necro"], "rank": 1}],
        sketches=[{"name": "Mère", "kind": "family", "group_label": "Famille", "role": "sa mère"},
                  {"name": "Maître Sol", "kind": "master", "skill_key": ids["necro"], "group_label": "Famille",
                   "role": "son maître"},
                  {"name": "Ami", "kind": "other", "role": "son ami d'enfance"},
                  {"name": "Rival", "kind": "other", "role": "son rival"}],
        memberships=[{"faction_id": ids["guild"], "role": "apprenti"}, {"faction_id": ids["autre"], "role": None}],
        knowledge=[{"level": "rumor", "content": "Les cryptes ont un gardien."},
                   {"level": "knows", "content": "Le port ferme à la nuit."}],
    )
    submit_draft(db, draft, ())
    rows = db.exec(select(PcDraftSketch).where(PcDraftSketch.draft_id == draft.id)
                   .order_by(PcDraftSketch.position)).all()
    for key, row in zip(("mere_sketch", "sol_sketch", "ami_sketch", "rival_sketch"), rows):
        ids[key] = row.id
    autre = db.exec(select(PcDraftMembership).where(PcDraftMembership.draft_id == draft.id,
                                                    PcDraftMembership.faction_id == ids["autre"])).one()
    save_review(db, draft, review_location_id=ids["quai"], sketches=[
        {"id": ids["mere_sketch"], "action": "create", "entity_id": None, "relation_type": "ally", "intensity": 70},
        {"id": ids["sol_sketch"], "action": "create", "entity_id": None, "relation_type": "fascination",
         "intensity": 80},
        {"id": ids["ami_sketch"], "action": "attach", "entity_id": ids["ami"], "relation_type": "interest",
         "intensity": 55},
        {"id": ids["rival_sketch"], "action": "drop", "entity_id": None, "relation_type": "", "intensity": 60},
    ], memberships=[{"id": autre.id, "dropped": True}])
    ids["draft"] = draft.id


def _stub_draft(entity_type, brief, db):
    return {"ok": True, "draft": {"public": {"name": "Autre nom", "physical_tier": 0},
                                  "secret": {"knowledge": []}, "facets": {}}, "notes": []}


def _stub_goals(*args, **kwargs):
    return {"ok": False, "error": "stub"}


def _lot(engine, ids: dict) -> None:
    """The `Famille` batch prepared and generated: two rows."""
    from sqlmodel import Session

    from world_engine import npc_group_author
    from world_engine.cockpit.pc_approval import prepare_group_lot
    from world_engine.models import NpcBatch, PcDraft

    with Session(engine) as db:
        batch = prepare_group_lot(db, db.get(PcDraft, ids["draft"]), "Famille")
        db.commit()
        ids["batch"] = batch.id
        for _ in range(2):
            npc_group_author.run_next_npc(db, db.get(NpcBatch, batch.id))
        db.commit()


def _counts(engine) -> dict[str, int]:
    from sqlalchemy import text

    with engine.connect() as conn:
        return {t: conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar_one() for t in COUNTED}


def _approve(client, ids: dict):
    return client.post(f"/api/pc-reviews/{ids['draft']}/approuver")


def _staging_intact(engine, ids: dict, label: str) -> None:
    """The draft still submitted, the batch open, its rows proposed."""
    from sqlmodel import Session, select

    from world_engine.models import NpcBatch, NpcBatchRow, PcDraft

    with Session(engine) as db:
        draft = db.get(PcDraft, ids["draft"])
        if draft.status != "submitted" or draft.character_id is not None:
            fail(f"{label}: the draft reads {draft.status!r}, {draft.character_id!r}")
        batch = db.get(NpcBatch, ids["batch"])
        statuses = sorted(r.row_status for r in db.exec(select(NpcBatchRow).where(
            NpcBatchRow.batch_id == ids["batch"])).all())
        if batch.status != "open" or statuses != ["proposed", "proposed"]:
            fail(f"{label}: the batch reads {batch.status!r}, rows {statuses!r}")


# --- DA2 -----------------------------------------------------------------------


def rule_da2(engine, client, ids: dict) -> int:
    from world_engine.cockpit import pc_approval

    def boom(*args, **kwargs):
        raise ValueError("boom")

    before = _counts(engine)
    saved = pc_approval.write_relation
    pc_approval.write_relation = boom
    try:
        resp = _approve(client, ids)
    finally:
        pc_approval.write_relation = saved
    if resp.status_code != 409 or resp.json().get("detail") != "boom":
        fail(f"DA2 a failing relation answered {resp.status_code}: {resp.text[:200]}")
    if _counts(engine) != before:
        fail(f"DA2 counts moved: {before} -> {_counts(engine)}")
    _staging_intact(engine, ids, "DA2")
    return 1


# --- DA3 -----------------------------------------------------------------------


def _refusal(engine, client, ids: dict, label: str, change, restore) -> None:
    from sqlmodel import Session

    with Session(engine) as db:
        change(db)
        db.commit()
    before = _counts(engine)
    resp = _approve(client, ids)
    if resp.status_code != 409 or resp.json().get("detail") != REFUSED:
        fail(f"DA3 {label} answered {resp.status_code}: {resp.text[:200]}")
    if _counts(engine) != before:
        fail(f"DA3 {label}: counts moved {before} -> {_counts(engine)}")
    with Session(engine) as db:
        restore(db)
        db.commit()


def _set(db, model, row_id: str, **values) -> None:
    row = db.get(model, row_id)
    for name, value in values.items():
        setattr(row, name, value)
    db.add(row)


def rule_da3(engine, client, ids: dict) -> int:
    from datetime import UTC, datetime

    from sqlmodel import select

    from world_engine.models import Character, Entity, NpcBatch, NpcBatchRow, PcDraftSketch

    def first_row(db):
        return db.exec(select(NpcBatchRow).where(NpcBatchRow.batch_id == ids["batch"])
                       .order_by(NpcBatchRow.line_index)).first().id

    def bea_pc(db):
        entity = Entity(world_id=ids["world"], type="character", name="PJ de Bea", status="active")
        db.add(entity)
        db.flush()
        db.add(Character(id=entity.id, world_id=ids["world"], character_type="player", user_id=ids["bea"]))
        ids["bea_pc"] = entity.id

    def no_bea_pc(db):
        db.delete(db.get(Character, ids["bea_pc"]))
        db.flush()
        db.delete(db.get(Entity, ids["bea_pc"]))

    cases = [
        ("Rival undecided", lambda db: _set(db, PcDraftSketch, ids["rival_sketch"], review_action=None),
         lambda db: _set(db, PcDraftSketch, ids["rival_sketch"], review_action="drop")),
        ("the Famille batch abandoned",
         lambda db: _set(db, NpcBatch, ids["batch"], status="abandoned", closed_at=datetime.now(UTC)),
         lambda db: _set(db, NpcBatch, ids["batch"], status="open", closed_at=None)),
        ("a row rejected", lambda db: _set(db, NpcBatchRow, first_row(db), row_status="rejected"),
         lambda db: _set(db, NpcBatchRow, first_row(db), row_status="proposed")),
        ("Bea holding a player character", bea_pc, no_bea_pc),
    ]
    for label, change, restore in cases:
        _refusal(engine, client, ids, label, change, restore)
    _staging_intact(engine, ids, "DA3")
    return 1


# --- DA1 -----------------------------------------------------------------------


def _named(db, world_id: str, name: str) -> str | None:
    from sqlmodel import select

    from world_engine.models import Entity

    entity = db.exec(select(Entity).where(Entity.world_id == world_id, Entity.name == name,
                                          Entity.type == "character")).first()
    return entity.id if entity is not None else None


def _da1_people(db, ids: dict, kael: str) -> None:
    from sqlmodel import select

    from world_engine.models import BASE_SKILL_DOMAINS, Relation, Rencontre, Skill
    from world_engine.skill_access import skill_masters

    mere, sol = _named(db, ids["world"], "Mère"), _named(db, ids["world"], "Maître Sol")
    if mere is None or sol is None:
        fail(f"DA1 the created people read Mère {mere!r}, Maître Sol {sol!r}")
        return
    masters = {m["id"] for m in skill_masters(db, ids["world"], definition_id=ids["necro"], domain=None)}
    if masters != {ids["vieux"], sol}:
        fail(f"DA1 the Maîtres of Nécromancie read {masters!r}")
    skills = db.exec(select(Skill).where(Skill.character_id == kael)).all()
    got = sorted((s.skill_definition_id or s.domain, s.rank, s.taught_by_id or "") for s in skills)
    want = sorted([(d, 2 if d == "perception" else 1, "") for d in BASE_SKILL_DOMAINS]
                  + [(ids["lame"], 2, ""), (ids["necro"], 1, sol)])
    if got != want:
        fail(f"DA1 Kael's skills read {got!r}, not {want!r}")
    relations = sorted((r.entity_a_id, r.type, r.intensity, r.notes, r.direction) for r in db.exec(
        select(Relation).where(Relation.entity_b_id == kael)).all())
    want_rel = sorted([(mere, "ally", 70, "sa mère", "a_to_b"), (sol, "fascination", 80, "son maître", "a_to_b"),
                       (ids["ami"], "interest", 55, "son ami d'enfance", "a_to_b")])
    if relations != want_rel:
        fail(f"DA1 the relations to Kael read {relations!r}")
    met = {frozenset((r.entity_lo_id, r.entity_hi_id)): r.source for r in db.exec(select(Rencontre)).all()}
    for other, source in ((ids["membre"], "pc_creation"), (mere, "relation"), (sol, "relation"),
                          (ids["ami"], "relation")):
        if met.get(frozenset((kael, other))) != source:
            fail(f"DA1 the encounter Kael-{other} reads {met.get(frozenset((kael, other)))!r}, not {source!r}")
    for key in ("espion", "cache"):
        if frozenset((kael, ids[key])) in met:
            fail(f"DA1 Kael met {key}")


def _da1_lore(db, ids: dict, kael: str) -> None:
    from sqlmodel import select

    from world_engine.models import Fact, FactionMembership, FactParticipant, Knowledge

    memberships = db.exec(select(FactionMembership).where(FactionMembership.entity_id == kael,
                                                          FactionMembership.left_at.is_(None))).all()
    if sorted((m.faction_id, m.role) for m in memberships) != [(ids["guild"], "apprenti")]:
        fail(f"DA1 Kael's memberships read {[(m.faction_id, m.role) for m in memberships]!r}")
    knowledge = db.exec(select(Knowledge).where(Knowledge.entity_id == kael)).all()
    if sorted((k.level, k.is_secret) for k in knowledge) != [("knows", False), ("rumor", False)]:
        fail(f"DA1 Kael's knowledge reads {[(k.level, k.is_secret) for k in knowledge]!r}")
    facts = db.exec(select(Fact).join(FactParticipant, FactParticipant.fact_id == Fact.id).where(
        FactParticipant.entity_id == kael, Fact.facet == "histoire")).all()
    if len(facts) != len(STORY.splitlines()):
        fail(f"DA1 Kael's histoire facts: {len(facts)} for {len(STORY.splitlines())} story lines")


def rule_da1(engine, client, ids: dict) -> int:
    from sqlmodel import Session, select

    from world_engine.models import Character, NpcBatch, NpcBatchRow, PcDraft

    resp = _approve(client, ids)
    data = resp.json() if resp.status_code == 200 else {}
    if not data.get("ok") or not data.get("character_id") or data.get("name") != "Kael":
        fail(f"DA1 the approval answered {resp.status_code}: {resp.text[:300]}")
        return 0
    kael = data["character_id"]
    with Session(engine) as db:
        pcs = db.exec(select(Character).where(Character.world_id == ids["world"],
                                              Character.character_type == "player")).all()
        if [(c.id, c.user_id, c.current_location_id) for c in pcs] != [(kael, ids["ana"], ids["quai"])]:
            fail(f"DA1 the world's player characters read {[(c.id, c.user_id) for c in pcs]!r}")
        draft = db.get(PcDraft, ids["draft"])
        if draft.status != "approved" or draft.character_id != kael:
            fail(f"DA1 the draft reads {draft.status!r}, {draft.character_id!r}")
        statuses = sorted(r.row_status for r in db.exec(select(NpcBatchRow).where(
            NpcBatchRow.batch_id == ids["batch"])).all())
        if db.get(NpcBatch, ids["batch"]).status != "committed" or statuses != ["committed", "committed"]:
            fail(f"DA1 the batch reads {db.get(NpcBatch, ids['batch']).status!r}, rows {statuses!r}")
        _da1_people(db, ids, kael)
        _da1_lore(db, ids, kael)
    resp = _approve(client, ids)
    if resp.status_code != 404 or resp.json().get("detail") != "Brouillon introuvable.":
        fail(f"DA3 the approved draft approved again answered {resp.status_code}: {resp.text[:200]}")
    return 1


# --- DA5 -----------------------------------------------------------------------


def _tokens(path: pathlib.Path, skip: tuple[str, ...] = (), only: str | None = None) -> str:
    """The module's code tokens, strings and comments dropped; the top-level
    functions named in `skip` dropped, or only the one named `only` kept."""
    source = path.read_text(encoding="utf-8")
    spans = [(n.name, n.lineno, n.end_lineno) for n in ast.parse(source).body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    dropped = [(a, b) for name, a, b in spans if name in skip]
    kept = [(a, b) for name, a, b in spans if name == only]
    if only is not None and not kept:
        fail(f"DA5 {path.name} declares no {only}")
    out = []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type in (tokenize.STRING, tokenize.COMMENT):
            continue
        line = tok.start[0]
        if any(a <= line <= b for a, b in dropped):
            continue
        if only is not None and not any(a <= line <= b for a, b in kept):
            continue
        out.append(tok.string)
    return "".join(out)


def rule_da5() -> int:
    for path in (APPROVAL, REVIEW_ROUTES, PC_WRITER):
        if not path.exists():
            fail(f"DA5 {path.relative_to(ROOT)} missing")
            return 0
    approval = _tokens(APPROVAL, skip=STAGING_FUNCTIONS)
    if "defapprove_draft(" not in approval:
        fail("DA5 cockpit/pc_approval.py declares no approve_draft")
    for needle in ("db.add(", ".commit(", ".flush(", "chat("):
        if needle in approval:
            fail(f"DA5 cockpit/pc_approval.py holds {needle} outside the staging functions")
    whole = _tokens(APPROVAL)
    for needle in (".commit(", "chat("):
        if needle in whole:
            fail(f"DA5 cockpit/pc_approval.py holds {needle}")
    route = _tokens(REVIEW_ROUTES, only="approve_review")
    if route.count("db.commit()") != 1:
        fail(f"DA5 approve_review holds {route.count('db.commit()')} db.commit()")
    writer = _tokens(PC_WRITER)
    for needle in ("npc_batch", "NpcBatch"):
        if needle in writer:
            fail(f"DA5 writes/player_characters.py names {needle}")
    return 1


# --- DA4 -----------------------------------------------------------------------


def rule_da4(engine, client, ids: dict) -> int:
    from sqlmodel import Session, select

    from world_engine.models import BASE_SKILL_DOMAINS, Character, Skill

    body = {"name": "Créé", "current_location_id": ids["port"]}
    resp = client.post("/api/characters/player", json=body)
    data = resp.json() if resp.status_code == 200 else {}
    if not data.get("ok"):
        fail(f"DA4 the creator's route answered {resp.status_code}: {resp.text[:200]}")
        return 0
    with Session(engine) as db:
        character = db.get(Character, data["id"])
        if character is None or character.user_id != ids["creator"] or character.character_type != "player":
            fail("DA4 the creator's character is not hers")
        skills = db.exec(select(Skill).where(Skill.character_id == data["id"])).all()
        got = sorted((s.skill_definition_id or s.domain, s.rank, s.taught_by_id) for s in skills)
        want = sorted([(d, 1, None) for d in BASE_SKILL_DOMAINS] + [(ids["lame"], 1, None)])
        if got != want:
            fail(f"DA4 the creator's character holds {got!r}, not {want!r}")
    resp = client.post("/api/characters/player", json={"name": "Second", "current_location_id": ids["port"]})
    if resp.status_code != 200 or resp.json().get("ok") is not False:
        fail(f"DA4 a second creator's character answered {resp.status_code}: {resp.text[:200]}")
    return 1


def main() -> int:
    engine = _fresh_engine()
    from sqlmodel import Session

    from fastapi.testclient import TestClient

    from world_engine.cockpit.app import app

    from world_engine import npc_group_author

    plan: list = [("DA5", rule_da5)]
    saved = (npc_group_author.generate_entity_draft, npc_group_author.generate_npc_goals,
             npc_group_author.JOURNAL_DIR)
    npc_group_author.generate_entity_draft = _stub_draft
    npc_group_author.generate_npc_goals = _stub_goals
    npc_group_author.JOURNAL_DIR = pathlib.Path(tempfile.mkdtemp())
    try:
        with Session(engine) as db:
            ids = _world(db)
            _draft(db, ids)
            db.commit()
        _lot(engine, ids)
        client = TestClient(app, base_url="http://127.0.0.1")
        plan += [("DA2", lambda: rule_da2(engine, client, ids)),
                 ("DA3", lambda: rule_da3(engine, client, ids)),
                 ("DA1", lambda: rule_da1(engine, client, ids)),
                 ("DA4", lambda: rule_da4(engine, client, ids))]
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
    (npc_group_author.generate_entity_draft, npc_group_author.generate_npc_goals,
     npc_group_author.JOURNAL_DIR) = saved
    if reached != 5:
        fail(f"{reached} of 5 rules reached")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: draft_approval -- one transaction writes the people of the story, the masters' rank, "
          "the character at the player's ranks with each taught skill's master, his memberships, his "
          "knowledge, the encounters with public members only and the relations to him, or nothing; "
          "every refusal writes nothing; the creator's own route keeps its default ranks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
