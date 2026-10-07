"""G1 check for TICKET-0108 -- quest offers, accepted quests, and the
requirement vocabulary they share with day plans.

The lot adds its pieces brief by brief; this check grows with it (the
`npc_skills.py` precedent, TICKET-0107). Each brief adds its rules here in
the same commit.

QA1 -- vocabulary (BRIEF-0108-A, static and import). `day_plan.REQUIREMENT_
   TYPES` holds the eight forms; `MODEL_REQUIREMENT_TYPES` is exactly the
   model's four and a subset of it; `ENTITY_TARGET_TYPES` and
   `KEY_TARGET_TYPES` partition it and `THRESHOLD_TYPES` is inside it; the
   three `type NOT IN (...)` groups of `ck_agenda_step_requirement_shape`
   are, in order, those three constants; `quest_offer_requirement`'s two
   CHECK texts equal `agenda_step_requirement`'s; `day_plan.
   _validate_requirement` (the model's parser) accepts each model form and
   refuses each creator form.
QA2 -- migration `scripts/migrate_v2_17_quests.py`, on a v2.16-shaped
   database (`agenda_step_requirement` in its v2.16 DDL, verbatim below, no
   quest table), holding one requirement row and a `session` row pointing
   to a missing world:
   a. at v2.15 it refuses (non-zero exit) and changes nothing;
   b. at v2.16 it keeps the requirement row, its stored CHECK names the four
      new forms, the four quest tables exist with the models' columns, a
      `has_met` requirement row can be inserted, `PRAGMA foreign_key_check`
      is empty on the five tables it writes, the orphan `session` is noted
      and not stopped on, and `schema_meta` is the code's version;
   c. a second run exits zero and changes no row.
QA3 -- the evaluators (fixture). `relation_gte` reads what the target feels
   toward the character: the character's own row toward the target and a
   structural row are not read. `has_met` reads `rencontre`;
   `faction_member` an active membership, secret included, a left one not;
   `skill_rank_gte` a base domain without a row at Initié, a definition
   without a row as not held, a row at its rank; `quest_completed` a quest
   whose agenda is `completed`, not `paused`. `requirement_detail_fr` names
   the target of each new form. `_clean_requirement` refuses a
   `faction_member` aimed at a character, a `skill_rank_gte` threshold of
   6, an unknown skill, an unknown quest offer, and accepts each form well
   aimed.

QB1 -- the offer writer (BRIEF-0108-B, fixture). `write_quest_offer` refuses
   a location as giver, an empty title, a status `draft`, no step, a cost of
   5, a domain `magic`, a `faction_member` aimed at a character, and an
   offer requiring its own completion -- each with no row written. A valid
   offer writes its eligibility and its steps with their requirements;
   saving it again replaces its steps and requirements whole (the old rows
   gone) and appends one `change_history` entry.
QB2 -- acceptance (fixture, B1, A1, L1). An unmet eligibility refuses with
   no agenda written. Met: one agenda, `paused`, titled as the offer, the
   player's active plan still `active`; its steps copied in order, the first
   `active`, the others `pending`, with their requirements; one `quest` row.
   The same non-repeatable offer is refused a second time; a repeatable one
   is refused while its quest is open, accepted again once it is
   `completed`; a `closed` offer is refused. `available_offers` lists
   exactly the offers accepted would succeed for.
QB3 -- abandon (fixture, N1). A quest with an `agenda_step_change` of its
   step still `proposed` is refused; without it, its agenda becomes
   `abandoned` (one more `change_history` entry, nothing deleted); a second
   abandon is refused. `pinned_plan` (O1) returns the agenda of the player's
   open quest, raises `LookupError` for another character's quest and
   `ValueError` for an abandoned one. The non-repeatable offer, its quest
   now over, is still neither available nor accepted (L1).
QB4 -- what the player sees (fixture and static). `journee_payload` and the
   route functions `journee_quests`, `accept`, `abandon` return no key
   `agenda_id` or `step_id` at any depth; a quest's state reads `en cours`,
   then `abandonnée`. Statically, `routes/quests.py` and `quest_reads.py`
   build no dict literal with either key, and `plan_day` calls
   `quest_reads.pinned_plan(` in the branch that does not call
   `select_plan(`.

QC1 -- the editor's mirror (BRIEF-0108-C, static). `frontend/src/creation/
   questRequirements.js`'s `REQUIREMENT_FORMS` has exactly the keys of
   `day_plan.REQUIREMENT_TYPES`; its forms with `column: 'entity'` are
   `ENTITY_TARGET_TYPES`, with `column: 'key'` `KEY_TARGET_TYPES`, with
   `threshold: true` `THRESHOLD_TYPES`.
QC2 -- the « Quêtes » tab (static). `tabs.js`'s `quetes` entry mounts the
   `questOffers` island in `creation-quetes` and routes « + Nouvelle quête »
   through `triggerPrimaryAction('questOffers')`; `QuestOffers.svelte`
   exports `primaryAction`; `questOffers.svelte.js` creates with `POST
   /api/quest-offers` and saves with `PUT /api/quest-offers/`.
QC3 -- Journée (static). `QuestPanel.svelte` and `quests.svelte.js` contain
   neither `agenda_id` nor `step_id`; `Journee.svelte` renders
   `<QuestPanel` and plans with `planDay(id, questState.pin)`;
   `journee.svelte.js` sends `quest_id` in the plan request's body.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import tempfile
from datetime import UTC, datetime

ROOT = pathlib.Path(__file__).resolve().parents[3]
MIGRATION = ROOT / "scripts" / "migrate_v2_17_quests.py"

FAILURES: list[str] = []

MODEL_FORMS = ("knowledge", "relation_gte", "resource", "location_reachable")
CREATOR_FORMS = ("has_met", "faction_member", "skill_rank_gte", "quest_completed")
QUEST_TABLES = ("quest_offer", "quest_offer_step", "quest_offer_requirement", "quest")

# `agenda_step_requirement` as v2.16 created it (dumped from `main` at 4b06dde).
_V216_DDL = (
    """CREATE TABLE agenda_step_requirement (
	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, step_id VARCHAR NOT NULL,
	type VARCHAR NOT NULL, target_entity_id VARCHAR, target_key VARCHAR, threshold INTEGER,
	PRIMARY KEY (id),
	CONSTRAINT ck_agenda_step_requirement_type CHECK (type IN ('knowledge','relation_gte','resource','location_reachable')),
	CONSTRAINT ck_agenda_step_requirement_shape CHECK ((type NOT IN ('relation_gte','location_reachable') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource') OR threshold IS NOT NULL)),
	FOREIGN KEY(world_id) REFERENCES world (id),
	FOREIGN KEY(step_id) REFERENCES agenda_step (id),
	FOREIGN KEY(target_entity_id) REFERENCES entity (id))""",
    "CREATE UNIQUE INDEX idx_agenda_step_requirement_unique ON agenda_step_requirement "
    "(step_id, type, target_entity_id, target_key)",
)


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> str:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    return db_path


# --- QA1 -----------------------------------------------------------------------

def _check_texts(table) -> dict[str, str]:
    from sqlalchemy import CheckConstraint

    return {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}


def _shape_groups(shape: str) -> list[tuple[str, ...]]:
    return [tuple(re.findall(r"'([^']*)'", group)) for group in re.findall(r"type NOT IN \(([^)]*)\)", shape)]


def check_qa1() -> None:
    from world_engine import day_plan, llm_parse
    from world_engine.models import AgendaStepRequirement, QuestOfferRequirement

    types = day_plan.REQUIREMENT_TYPES
    if tuple(types) != MODEL_FORMS + CREATOR_FORMS:
        fail(f"QA1: REQUIREMENT_TYPES is {types}")
    if tuple(day_plan.MODEL_REQUIREMENT_TYPES) != MODEL_FORMS or not set(MODEL_FORMS) <= set(types):
        fail(f"QA1: MODEL_REQUIREMENT_TYPES is {day_plan.MODEL_REQUIREMENT_TYPES}")
    entity, key, threshold = (set(day_plan.ENTITY_TARGET_TYPES), set(day_plan.KEY_TARGET_TYPES),
                              set(day_plan.THRESHOLD_TYPES))
    if entity & key or entity | key != set(types) or not threshold or not threshold <= set(types):
        fail(f"QA1: the shape groups do not partition the vocabulary: {entity}, {key}, {threshold}")

    agenda = _check_texts(AgendaStepRequirement.__table__)
    offer = _check_texts(QuestOfferRequirement.__table__)
    shape = agenda.get("ck_agenda_step_requirement_shape", "")
    groups = _shape_groups(shape)
    expected = [tuple(day_plan.ENTITY_TARGET_TYPES), tuple(day_plan.KEY_TARGET_TYPES), tuple(day_plan.THRESHOLD_TYPES)]
    if groups != expected:
        fail(f"QA1: the shape CHECK groups are {groups}, expected {expected}")
    pairs = (("ck_agenda_step_requirement_type", "ck_quest_offer_requirement_type"),
             ("ck_agenda_step_requirement_shape", "ck_quest_offer_requirement_shape"))
    for agenda_name, offer_name in pairs:
        if not agenda.get(agenda_name) or agenda.get(agenda_name) != offer.get(offer_name):
            fail(f"QA1: {offer_name} differs from {agenda_name}")

    for form in MODEL_FORMS:
        try:
            day_plan._validate_requirement({"type": form, "target_key": "k", "threshold": 1})
        except llm_parse.LlmParseError as exc:
            fail(f"QA1: the model's parser refuses {form!r}: {exc}")
    for form in CREATOR_FORMS:
        try:
            day_plan._validate_requirement({"type": form, "target_key": "k", "threshold": 1})
        except llm_parse.LlmParseError:
            continue
        fail(f"QA1: the model's parser accepts the creator form {form!r}")


# --- QA2 -----------------------------------------------------------------------

def _run_migration(db_path: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True,
                          text=True, cwd=str(ROOT), timeout=120)


def _shape(conn, table: str) -> list[tuple]:
    return sorted((r[1], r[2], r[3], r[4]) for r in conn.execute(f"PRAGMA table_info({table})"))


def _seed_v216(db_path: str) -> dict:
    from sqlmodel import Session

    from world_engine.db import create_db_and_tables, engine
    from world_engine.models import Agenda, AgendaStep, Entity, SchemaMeta, World

    create_db_and_tables()
    ids: dict = {}
    with Session(engine) as session:
        world = World(name="Quests QA2", is_active=True)
        session.add(world)
        session.flush()
        person = Entity(world_id=world.id, type="character", name="pc")
        session.add(person)
        session.flush()
        agenda = Agenda(world_id=world.id, owner_entity_id=person.id, title="t", change_history=[])
        session.add(agenda)
        session.flush()
        step = AgendaStep(agenda_id=agenda.id, step_order=1, objective="o", change_history=[])
        session.add(step)
        session.flush()
        ids.update(world=world.id, person=person.id, step=step.id)
        if session.get(SchemaMeta, 1) is None:
            session.add(SchemaMeta(id=1, static_version="v2.16"))
        session.commit()
    engine.dispose()
    with sqlite3.connect(db_path) as conn:
        ids["model_shapes"] = {t: _shape(conn, t) for t in QUEST_TABLES}
        conn.execute("PRAGMA foreign_keys=OFF")
        for table in QUEST_TABLES[::-1] + ("agenda_step_requirement",):
            conn.execute(f"DROP TABLE {table}")
        for statement in _V216_DDL:
            conn.execute(statement)
        conn.execute(
            "INSERT INTO agenda_step_requirement (id, world_id, step_id, type, target_key) "
            "VALUES ('req-1', ?, ?, 'knowledge', 'fact-x')", (ids["world"], ids["step"]))
        # A dangling reference this migration never wrote (AMENDMENT-0107-01).
        conn.execute("INSERT INTO session (id, world_id, number) VALUES ('orphan-session', 'gone-world', 9)")
    return ids


def _state(db_path: str) -> dict:
    with sqlite3.connect(db_path) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        return {
            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
            "requirements": conn.execute("SELECT * FROM agenda_step_requirement ORDER BY id").fetchall(),
            "check": conn.execute("SELECT sql FROM sqlite_master WHERE name='agenda_step_requirement'").fetchone()[0],
            "quest_tables": {t: _shape(conn, t) for t in QUEST_TABLES if t in tables},
        }


def check_qa2(db_path: str) -> None:
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION

    ids = _seed_v216(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE schema_meta SET static_version = 'v2.15' WHERE id = 1")
    before = _state(db_path)
    result = _run_migration(db_path)
    if result.returncode == 0 or _state(db_path) != before:
        fail(f"QA2a: at v2.15 the migration exit {result.returncode} or the database changed")
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE schema_meta SET static_version = 'v2.16' WHERE id = 1")
    result = _run_migration(db_path)
    if result.returncode != 0:
        fail(f"QA2b: the migration failed: {result.stdout[-400:]} {result.stderr[-400:]}")
        return
    after = _state(db_path)
    if after["requirements"] != before["requirements"] or not after["requirements"]:
        fail(f"QA2b: the requirement rows are {after['requirements']}")
    absent = [form for form in CREATOR_FORMS if f"'{form}'" not in after["check"]]
    if absent:
        fail(f"QA2b: the stored CHECK lacks {absent}")
    if after["quest_tables"] != ids["model_shapes"]:
        fail(f"QA2b: the quest tables are {after['quest_tables']}, expected the models' {ids['model_shapes']}")
    if after["version"] != EXPECTED_STATIC_SCHEMA_VERSION:
        fail(f"QA2b: schema_meta is {after['version']}")
    if "Note: session rowid" not in result.stdout:
        fail("QA2b: the orphan session row was not noted")
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            conn.execute(
                "INSERT INTO agenda_step_requirement (id, world_id, step_id, type, target_entity_id) "
                "VALUES ('req-2', ?, ?, 'has_met', ?)", (ids["world"], ids["step"], ids["person"]))
        except sqlite3.DatabaseError as exc:
            fail(f"QA2b: a has_met row cannot be inserted: {exc}")
        dangling = [r for t in ("agenda_step_requirement",) + QUEST_TABLES
                    for r in conn.execute(f"PRAGMA foreign_key_check({t})").fetchall()]
        if dangling:
            fail(f"QA2b: foreign_key_check {dangling}")
    again_before = _state(db_path)
    result = _run_migration(db_path)
    if result.returncode != 0 or _state(db_path) != again_before:
        fail(f"QA2c: a second run exit {result.returncode} or changed a row")


# --- QA3 -----------------------------------------------------------------------

def _qa3_world(session) -> dict:
    from world_engine.models import Character, Entity, Faction, SkillDefinition, World

    world = World(name="Quests QA3", is_active=False)
    session.add(world)
    session.flush()
    ids = {"world": world.id}
    for key, kind in (("pc", "player"), ("npc", "npc")):
        row = Entity(world_id=world.id, type="character", name=key.upper())
        session.add(row)
        session.flush()
        session.add(Character(id=row.id, world_id=world.id, character_type=kind))
        ids[key] = row.id
    faction = Entity(world_id=world.id, type="faction", name="Guilde")
    session.add(faction)
    session.flush()
    session.add(Faction(id=faction.id))
    ids["faction"] = faction.id
    definition = SkillDefinition(world_id=world.id, name="Herboristerie", base_domain="perception")
    session.add(definition)
    session.flush()
    ids["definition"] = definition.id
    session.commit()
    return ids


def _verdict(session, character, form: str, **target):
    from world_engine.day_plan import RequirementSpec, evaluate_specs

    return evaluate_specs((RequirementSpec(type=form, **target),), character, session)[0]


def _qa3_relation_and_meeting(session, ids, pc) -> None:
    from world_engine.models import Relation, Rencontre

    session.add(Relation(world_id=ids["world"], entity_a_id=ids["pc"], entity_b_id=ids["npc"],
                         type="ami", direction="a_to_b", intensity=90, change_history=[]))
    session.add(Relation(world_id=ids["world"], entity_a_id=ids["npc"], entity_b_id=ids["pc"],
                         type="controls", direction="a_to_b", intensity=95, change_history=[]))
    session.commit()
    if _verdict(session, pc, "relation_gte", target_entity_id=ids["npc"], threshold=50).met:
        fail("QA3: relation_gte read the character's own row, or a structural row")
    session.add(Relation(world_id=ids["world"], entity_a_id=ids["npc"], entity_b_id=ids["pc"],
                         type="ami", direction="a_to_b", intensity=60, change_history=[]))
    session.commit()
    verdict = _verdict(session, pc, "relation_gte", target_entity_id=ids["npc"], threshold=50)
    if not verdict.met or verdict.current != 60:
        fail(f"QA3: relation_gte with the target's row at 60 is {verdict}")
    if _verdict(session, pc, "has_met", target_entity_id=ids["npc"]).met:
        fail("QA3: has_met is met with no encounter")
    low, high = sorted((ids["pc"], ids["npc"]))
    now = datetime(2026, 1, 1, tzinfo=UTC)
    session.add(Rencontre(world_id=ids["world"], entity_lo_id=low, entity_hi_id=high, first_at=now,
                          last_at=now, source="visit"))
    session.commit()
    if not _verdict(session, pc, "has_met", target_entity_id=ids["npc"]).met:
        fail("QA3: has_met is unmet with an encounter row")


def _qa3_faction_and_skill(session, ids, pc) -> None:
    from world_engine.models import FactionMembership, Skill

    left = FactionMembership(world_id=ids["world"], entity_id=ids["pc"], faction_id=ids["faction"],
                             left_at=datetime(2026, 1, 1, tzinfo=UTC))
    session.add(left)
    session.commit()
    if _verdict(session, pc, "faction_member", target_entity_id=ids["faction"]).met:
        fail("QA3: faction_member is met by a membership the character left")
    session.add(FactionMembership(world_id=ids["world"], entity_id=ids["pc"], faction_id=ids["faction"],
                                  is_secret=True))
    session.commit()
    if not _verdict(session, pc, "faction_member", target_entity_id=ids["faction"]).met:
        fail("QA3: faction_member is unmet by an active secret membership")
    initie = _verdict(session, pc, "skill_rank_gte", target_key="agility", threshold=1)
    apprenti = _verdict(session, pc, "skill_rank_gte", target_key="agility", threshold=2)
    if not initie.met or apprenti.met:
        fail(f"QA3: a base domain with no row reads {initie.current}, not Initié")
    if _verdict(session, pc, "skill_rank_gte", target_key=ids["definition"], threshold=1).met:
        fail("QA3: a skill definition with no row is held")
    session.add(Skill(character_id=ids["pc"], domain="perception", skill_definition_id=ids["definition"],
                      rank=3, change_history=[]))
    session.commit()
    held = _verdict(session, pc, "skill_rank_gte", target_key=ids["definition"], threshold=3)
    if not held.met or held.required_label != "Herboristerie":
        fail(f"QA3: a definition row at rank 3 gives {held}")


def _qa3_quest(session, ids, pc) -> None:
    from world_engine.models import Agenda, Quest, QuestOffer

    offer = QuestOffer(world_id=ids["world"], giver_entity_id=ids["npc"], title="La fourrure", change_history=[])
    agenda = Agenda(world_id=ids["world"], owner_entity_id=ids["pc"], title="La fourrure", status="paused",
                    change_history=[])
    session.add(offer)
    session.add(agenda)
    session.flush()
    session.add(Quest(world_id=ids["world"], offer_id=offer.id, character_id=ids["pc"], agenda_id=agenda.id))
    session.commit()
    ids["offer"] = offer.id
    if _verdict(session, pc, "quest_completed", target_key=offer.id).met:
        fail("QA3: quest_completed is met by a paused quest")
    agenda.status = "completed"
    session.add(agenda)
    session.commit()
    if not _verdict(session, pc, "quest_completed", target_key=offer.id).met:
        fail("QA3: quest_completed is unmet by a completed quest")


def _qa3_wording_and_cleaning(session, ids, pc) -> None:
    from world_engine.day_plan import RequirementSpec
    from world_engine.day_resolve import requirement_detail_fr
    from world_engine.writes.goals_agendas import _clean_requirement

    targets = {
        "has_met": {"target_entity_id": ids["npc"]},
        "faction_member": {"target_entity_id": ids["faction"]},
        "skill_rank_gte": {"target_key": ids["definition"], "threshold": 2},
        "quest_completed": {"target_key": ids["offer"]},
    }
    names = {"has_met": "NPC", "faction_member": "Guilde", "skill_rank_gte": "Herboristerie",
             "quest_completed": "La fourrure"}
    for form, target in targets.items():
        text = requirement_detail_fr(_verdict(session, pc, form, **target))
        if names[form] not in text:
            fail(f"QA3: requirement_detail_fr for {form!r} is {text!r}")
        try:
            _clean_requirement(session, ids["world"], 0, RequirementSpec(type=form, **target))
        except ValueError as exc:
            fail(f"QA3: _clean_requirement refuses a well-aimed {form!r}: {exc}")
    refused = (
        RequirementSpec(type="faction_member", target_entity_id=ids["npc"]),
        RequirementSpec(type="skill_rank_gte", target_key="agility", threshold=6),
        RequirementSpec(type="skill_rank_gte", target_key="no-such-skill", threshold=1),
        RequirementSpec(type="quest_completed", target_key="no-such-offer"),
    )
    for spec in refused:
        try:
            _clean_requirement(session, ids["world"], 0, spec)
        except ValueError:
            continue
        fail(f"QA3: _clean_requirement accepts {spec}")


def check_qa3(engine) -> None:
    from sqlmodel import Session

    from world_engine.models import Character

    with Session(engine) as session:
        ids = _qa3_world(session)
        pc = session.get(Character, ids["pc"])
        _qa3_relation_and_meeting(session, ids, pc)
        _qa3_faction_and_skill(session, ids, pc)
        _qa3_quest(session, ids, pc)
        _qa3_wording_and_cleaning(session, ids, pc)


# --- QB --------------------------------------------------------------------------

def _qb_world(session) -> dict:
    from world_engine.models import Agenda, Character, Entity, Faction, World

    world = World(name="Quests QB", is_active=False)
    session.add(world)
    session.flush()
    ids = {"world": world.id}
    for key, kind in (("pc", "player"), ("npc", "npc"), ("other", "npc")):
        row = Entity(world_id=world.id, type="character", name=key.upper())
        session.add(row)
        session.flush()
        session.add(Character(id=row.id, world_id=world.id, character_type=kind))
        ids[key] = row.id
    for key, kind in (("guild", "faction"), ("place", "location")):
        row = Entity(world_id=world.id, type=kind, name=key.title())
        session.add(row)
        session.flush()
        if kind == "faction":
            session.add(Faction(id=row.id))
        ids[key] = row.id
    plan = Agenda(world_id=world.id, owner_entity_id=ids["pc"], title="Plan du jour", status="active",
                  change_history=[])
    session.add(plan)
    session.commit()
    ids["plan"] = plan.id
    return ids


def _offer_kwargs(ids: dict, **over) -> dict:
    from world_engine.day_plan import PlanStep, RequirementSpec

    steps = [
        PlanStep(objective="Traquer le loup", cost=2, domain="perception",
                 requirements=(RequirementSpec(type="has_met", target_entity_id=ids["npc"]),)),
        PlanStep(objective="Rapporter la fourrure", cost=1, domain=None),
    ]
    base = dict(world_id=ids["world"], offer=None, giver_entity_id=ids["npc"], title="La fourrure",
                summary="Le chasseur veut la fourrure.", repeatable=False, status="open",
                eligibility=[RequirementSpec(type="faction_member", target_entity_id=ids["guild"])], steps=steps)
    base.update(over)
    return base


def _counts(session) -> tuple:
    from sqlmodel import func, select

    from world_engine.models import Agenda, Quest, QuestOffer, QuestOfferRequirement, QuestOfferStep

    return tuple(session.exec(select(func.count()).select_from(m)).one()
                 for m in (QuestOffer, QuestOfferStep, QuestOfferRequirement, Quest, Agenda))


def _qb1_refusals(session, ids) -> None:
    from world_engine.day_plan import PlanStep, RequirementSpec
    from world_engine.writes import write_quest_offer

    bad = (
        {"giver_entity_id": ids["place"]}, {"title": "  "}, {"status": "draft"}, {"steps": []},
        {"steps": [PlanStep(objective="o", cost=5, domain=None)]},
        {"steps": [PlanStep(objective="o", cost=1, domain="magic")]},
        {"eligibility": [RequirementSpec(type="faction_member", target_entity_id=ids["npc"])]},
    )
    for over in bad:
        before = _counts(session)
        try:
            write_quest_offer(session, **_offer_kwargs(ids, **over))
        except ValueError:
            session.rollback()
            if _counts(session) != before:
                fail(f"QB1: a refused offer {over} wrote rows")
            continue
        session.rollback()
        fail(f"QB1: write_quest_offer accepts {over}")


def check_qb1(session, ids) -> None:
    from sqlmodel import select

    from world_engine.day_plan import PlanStep, RequirementSpec
    from world_engine.models import QuestOfferRequirement, QuestOfferStep
    from world_engine.writes import write_quest_offer

    _qb1_refusals(session, ids)
    offer = write_quest_offer(session, **_offer_kwargs(ids))
    session.commit()
    ids["offer"] = offer.id
    steps = session.exec(select(QuestOfferStep).where(QuestOfferStep.offer_id == offer.id)).all()
    reqs = session.exec(select(QuestOfferRequirement).where(QuestOfferRequirement.offer_id == offer.id)).all()
    if [s.step_order for s in sorted(steps, key=lambda s: s.step_order)] != [1, 2] or len(reqs) != 2:
        fail(f"QB1: a new offer wrote {len(steps)} step(s), {len(reqs)} requirement(s)")
    try:
        write_quest_offer(session, **_offer_kwargs(ids, offer=offer, eligibility=[
            RequirementSpec(type="quest_completed", target_key=offer.id)]))
        fail("QB1: an offer requiring its own completion was saved")
    except ValueError:
        session.rollback()
    old_ids = {s.id for s in steps}
    write_quest_offer(session, **_offer_kwargs(ids, offer=offer, steps=[PlanStep(objective="Seule", cost=1, domain=None)]))
    session.commit()
    after = session.exec(select(QuestOfferStep).where(QuestOfferStep.offer_id == offer.id)).all()
    if len(after) != 1 or {s.id for s in after} & old_ids or len(offer.change_history) != 1:
        fail(f"QB1: a save left {len(after)} step(s), history {len(offer.change_history)}")
    write_quest_offer(session, **_offer_kwargs(ids, offer=offer))
    session.commit()


def _accept_refused(session, offer, pc, label: str) -> None:
    from world_engine.writes import accept_quest

    before = _counts(session)
    try:
        accept_quest(session, offer=offer, character=pc)
    except ValueError:
        session.rollback()
        if _counts(session) != before:
            fail(f"QB2: a refused acceptance ({label}) wrote rows")
        return
    session.rollback()
    fail(f"QB2: accept_quest accepts {label}")


def _qb2_accepted(session, ids, quest) -> None:
    from sqlmodel import select

    from world_engine.models import Agenda, AgendaStep, AgendaStepRequirement

    agenda = session.get(Agenda, quest.agenda_id)
    if agenda is None or agenda.status != "paused" or agenda.title != "La fourrure":
        fail(f"QB2: the quest's agenda is {agenda}")
        return
    if session.get(Agenda, ids["plan"]).status != "active":
        fail("QB2: accepting a quest displaced the active plan")
    steps = sorted(session.exec(select(AgendaStep).where(AgendaStep.agenda_id == agenda.id)).all(),
                   key=lambda s: s.step_order)
    if [(s.objective, s.status, s.cost) for s in steps] != [
            ("Traquer le loup", "active", 2), ("Rapporter la fourrure", "pending", 1)]:
        fail(f"QB2: the copied steps are {[(s.objective, s.status, s.cost) for s in steps]}")
    reqs = session.exec(select(AgendaStepRequirement).where(AgendaStepRequirement.step_id == steps[0].id)).all()
    if [(r.type, r.target_entity_id) for r in reqs] != [("has_met", ids["npc"])]:
        fail(f"QB2: the copied requirements are {[(r.type, r.target_entity_id) for r in reqs]}")


def check_qb2(session, ids) -> None:
    from world_engine.models import Agenda, Character, FactionMembership, QuestOffer
    from world_engine.quest_reads import available_offers
    from world_engine.writes import accept_quest, write_quest_offer

    pc = session.get(Character, ids["pc"])
    offer = session.get(QuestOffer, ids["offer"])
    if available_offers(pc, session):
        fail("QB2: an offer whose eligibility is unmet is available")
    _accept_refused(session, offer, pc, "an unmet eligibility")
    session.add(FactionMembership(world_id=ids["world"], entity_id=ids["pc"], faction_id=ids["guild"]))
    session.commit()
    if [o.id for o in available_offers(pc, session)] != [offer.id]:
        fail("QB2: the eligible offer is not available")
    try:
        quest = accept_quest(session, offer=offer, character=pc)
    except ValueError as exc:
        session.rollback()
        fail(f"QB2: an eligible offer was refused: {exc}")
        return
    session.commit()
    ids["quest"] = quest.id
    _qb2_accepted(session, ids, quest)
    if available_offers(pc, session):
        fail("QB2: an offer already taken is still available")
    _accept_refused(session, offer, pc, "a non-repeatable offer taken twice")

    errand = write_quest_offer(session, **_offer_kwargs(ids, title="Bois", repeatable=True, eligibility=[]))
    session.commit()
    first = accept_quest(session, offer=errand, character=pc)
    session.commit()
    _accept_refused(session, errand, pc, "a repeatable offer still open")
    done = session.get(Agenda, first.agenda_id)
    done.status = "completed"
    session.add(done)
    session.commit()
    accept_quest(session, offer=errand, character=pc)
    session.commit()
    closed = write_quest_offer(session, **_offer_kwargs(ids, title="Fermée", status="closed", eligibility=[]))
    session.commit()
    _accept_refused(session, closed, pc, "a closed offer")


def check_qb3(session, ids) -> None:
    from sqlmodel import select

    from world_engine.models import Agenda, AgendaStep, Character, ProposedMutation, Quest, QuestOffer
    from world_engine.quest_reads import available_offers, pinned_plan
    from world_engine.writes import abandon_quest

    quest = session.get(Quest, ids["quest"])
    pc, other = session.get(Character, ids["pc"]), session.get(Character, ids["other"])
    if pinned_plan(quest.id, pc, session).id != quest.agenda_id:
        fail("QB3: pinned_plan does not return the open quest's agenda")
    try:
        pinned_plan(quest.id, other, session)
        fail("QB3: pinned_plan returns another character's quest")
    except LookupError:
        pass
    step = session.exec(select(AgendaStep).where(AgendaStep.agenda_id == quest.agenda_id,
                                                 AgendaStep.status == "active")).first()
    proposal = ProposedMutation(world_id=ids["world"], source_type="pass_play", mutation_type="agenda_step_change",
                                payload={"step_id": step.id, "action": "complete"}, status="proposed")
    session.add(proposal)
    session.commit()
    try:
        abandon_quest(session, quest=quest)
        fail("QB3: a quest with a step change awaiting review was abandoned")
    except ValueError:
        session.rollback()
    proposal.status = "rejected"
    session.add(proposal)
    session.commit()
    agenda = session.get(Agenda, quest.agenda_id)
    history = len(agenda.change_history)
    if agenda.status == "paused":
        abandon_quest(session, quest=quest)
        session.commit()
    if agenda.status != "abandoned" or len(agenda.change_history) != history + 1:
        fail(f"QB3: the abandoned agenda is {agenda.status}, history {len(agenda.change_history)}")
    # L1, the quest now over: a non-repeatable offer is still never taken twice.
    if ids["offer"] in {o.id for o in available_offers(pc, session)}:
        fail("QB3: a non-repeatable offer whose quest is over is available again")
    _accept_refused(session, session.get(QuestOffer, ids["offer"]), pc, "a non-repeatable offer after its quest")
    try:
        abandon_quest(session, quest=quest)
        fail("QB3: a quest was abandoned twice")
    except ValueError:
        session.rollback()
    try:
        pinned_plan(quest.id, pc, session)
        fail("QB3: pinned_plan returns an abandoned quest")
    except ValueError:
        pass


def _keys(value) -> set:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys(v)}
    return set()


def _dict_literal_keys(path: pathlib.Path) -> set:
    import ast

    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {k.value for n in ast.walk(tree) if isinstance(n, ast.Dict)
            for k in n.keys if isinstance(k, ast.Constant)}


def _pin_branch_ok() -> bool:
    import ast

    tree = ast.parse((ROOT / "src" / "world_engine" / "cockpit" / "routes" / "day.py").read_text(encoding="utf-8"))
    plan = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "plan_day"), None)
    for node in ast.walk(plan) if plan is not None else ():
        if isinstance(node, ast.If):
            pinned = ast.unparse(ast.Module(body=node.body, type_ignores=[]))
            other = ast.unparse(ast.Module(body=node.orelse, type_ignores=[]))
            if "quest_reads.pinned_plan(" in pinned and "select_plan(" not in pinned and "select_plan(" in other:
                return True
    return False


def check_qb4(session, ids) -> None:
    from world_engine.models import Character, World
    from world_engine.quest_reads import journee_payload

    payload = journee_payload(session.get(Character, ids["pc"]), session)
    states = [q["state"] for q in payload["quests"]]
    if not payload["quests"] or "abandonnée" not in states or "en cours" not in states:
        fail(f"QB4: the quest states are {states}")
    from sqlmodel import select

    for world in session.exec(select(World).where(World.is_active == True)).all():  # noqa: E712
        world.is_active = False
        session.add(world)
    session.flush()
    ours = session.get(World, ids["world"])
    ours.is_active = True
    session.add(ours)
    session.commit()
    from world_engine.cockpit.routes import quests as routes

    seen = [payload, routes.journee_quests(db=session)]
    if seen[1].get("quests") is None:
        fail("QB4: GET /api/quests returned no quests")
    leaked = {"agenda_id", "step_id"} & set().union(*(_keys(v) for v in seen))
    if leaked:
        fail(f"QB4: the player's payload carries {sorted(leaked)}")
    for path in (ROOT / "src" / "world_engine" / "cockpit" / "routes" / "quests.py",
                 ROOT / "src" / "world_engine" / "quest_reads.py"):
        found = {"agenda_id", "step_id"} & _dict_literal_keys(path)
        if found:
            fail(f"QB4: {path.name} builds a dict with {sorted(found)}")
    if not _pin_branch_ok():
        fail("QB4: plan_day does not call quest_reads.pinned_plan( apart from select_plan(")


def check_qb(engine) -> None:
    from sqlmodel import Session

    with Session(engine) as session:
        ids = _qb_world(session)
        check_qb1(session, ids)
        check_qb2(session, ids)
        if "quest" not in ids:  # QB2 already failed: no quest to abandon or show
            return
        check_qb3(session, ids)
        check_qb4(session, ids)


# --- QC --------------------------------------------------------------------------

FRONTEND = ROOT / "frontend" / "src"


def _read(rel: str) -> str:
    path = FRONTEND / rel
    if not path.is_file():
        fail(f"QC: {rel} not found")
        return ""
    return path.read_text(encoding="utf-8")


def check_qc1() -> None:
    from world_engine import day_plan

    text = _read("creation/questRequirements.js")
    forms = dict(re.findall(r"^\s+(\w+): \{ label: '[^']*', list: '\w+', (column: '\w+', threshold: \w+) \},$",
                            text, re.M))
    if not forms:
        fail("QC1: REQUIREMENT_FORMS holds zero forms")
        return
    if list(forms) != list(day_plan.REQUIREMENT_TYPES):
        fail(f"QC1: REQUIREMENT_FORMS keys {list(forms)} != REQUIREMENT_TYPES")
    groups = {
        "column: 'entity'": tuple(day_plan.ENTITY_TARGET_TYPES), "column: 'key'": tuple(day_plan.KEY_TARGET_TYPES),
        "threshold: true": tuple(day_plan.THRESHOLD_TYPES),
    }
    for marker, expected in groups.items():
        found = tuple(form for form, spec in forms.items() if marker in spec)
        if found != expected:
            fail(f"QC1: the forms with {marker} are {found}, expected {expected}")


def check_qc2() -> None:
    tabs = _read("creation/tabs.js")
    entry = re.search(r"\n  quetes: \{(.*?)\n  \},", tabs, re.S)
    body = entry.group(1) if entry else ""
    for needle in ("{ key: 'questOffers', containerId: 'creation-quetes' }",
                   "triggerPrimaryAction('questOffers')"):
        if needle not in body:
            fail(f"QC2: tabs.js's quetes entry lacks {needle}")
    if "export function primaryAction" not in _read("creation/QuestOffers.svelte"):
        fail("QC2: QuestOffers.svelte exports no primaryAction")
    state = _read("creation/questOffers.svelte.js")
    for needle in ("'/api/quest-offers/' + draft.id", "draft.id ? 'PUT' : 'POST'"):
        if needle not in state:
            fail(f"QC2: questOffers.svelte.js lacks {needle}")


def check_qc3() -> None:
    for rel in ("journee/QuestPanel.svelte", "journee/quests.svelte.js"):
        text = _read(rel)
        for token in ("agenda_id", "step_id"):
            if token in text:
                fail(f"QC3: {rel} names {token}")
    journee = _read("journee/Journee.svelte")
    for needle in ("<QuestPanel", "planDay(id, questState.pin)"):
        if needle not in journee:
            fail(f"QC3: Journee.svelte lacks {needle}")
    if "JSON.stringify({ quest_id: questId })" not in _read("journee/journee.svelte.js"):
        fail("QC3: journee.svelte.js does not send quest_id in the plan body")


def main() -> int:
    db_path = _fresh_db()
    check_qa1()
    check_qa2(db_path)
    from world_engine.db import create_db_and_tables, engine
    create_db_and_tables()
    check_qa3(engine)
    check_qb(engine)
    check_qc1()
    check_qc2()
    check_qc3()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: quests -- v2.17 widens the requirement vocabulary to eight forms the model "
          "emits only four of, shared byte for byte by quest offers, migrates from v2.16 only, "
          "and judges what the target feels, encounters, memberships, ranks and completed quests; "
          "an offer is validated whole and saved whole, accepted only when eligible as a paused "
          "plan with its steps, once unless repeatable, abandoned unless a step awaits review, "
          "pinned to a day, and shown to the player without an agenda or step id; the editor "
          "mirrors the vocabulary, the « Quêtes » tab and Journée's panel are wired")
    return 0


if __name__ == "__main__":
    sys.exit(main())
