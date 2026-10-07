"""G1 check for TICKET-0110 -- debts and services.

The lot adds its pieces brief by brief; this check grows with it (the
`quests.py` and `quest_rewards.py` precedent). Each brief adds its rules
here in the same commit.

DA1 -- schema and vocabulary (BRIEF-0110-A, import and static).
   a. `debt` and `debt_term` carry exactly their contract's columns and
      CHECK texts; `DEBT_ORIGINS`, `DEBT_STATUSES`, `DEBT_CURRENCIES` are the
      values those CHECKs quote, in order; `quest_offer` has
      `contact_entity_id` and `quest_economy` `debt_fact_relation` and
      `debt_skill_relation`; `DEFAULT_RATES` gives them 10 and 20 and
      `ECONOMY_COLUMNS` lists them; the code's schema version is v2.19.
   b. `day_plan.REQUIREMENT_TYPES` ends with `has_debt_to`, `no_debt_to`;
      both are in `ENTITY_TARGET_TYPES`, neither in `THRESHOLD_TYPES` nor
      `MODEL_REQUIREMENT_TYPES`; each has an evaluator and a French blocked
      detail; `questRequirements.js` offers both on the `givers` list.
   c. I2: `debt` is in `RETIRED_RELATION_TYPES` and in neither the fiche's
      `RELATION_TYPES` nor the link agent's `_LINK_RELATION_TYPES`; the
      seeded link-pair prompt does not offer it; `write_relation` refuses
      it with no row written.
DA2 -- migration `scripts/migrate_v2_19_debts.py`, on a v2.18-shaped
   database (the four tables it changes in their v2.18 DDL, verbatim below;
   no debt table), holding one row in each and a `session` row pointing to
   a missing world:
   a. at v2.17 it refuses (non-zero exit) and changes nothing;
   b. at v2.18 it keeps every row, both requirement CHECKs name the two
      forms, the columns and the two tables exist with the models' shapes, a
      `has_debt_to` row can be inserted, `PRAGMA foreign_key_check` is empty
      on the six tables it writes, the orphan `session` is noted and not
      stopped on, and `schema_meta` is the code's version;
   c. a second run exits zero and changes no row.
DA3 -- the evaluators (fixture). With an OPEN debt of the character toward
   the creditor: `has_debt_to` met, `no_debt_to` not. A settled debt, a
   debt toward another creditor and a debt the character is OWED count for
   nothing. A faction creditor is judged like a character.
   `requirement_detail_fr` names the creditor in both forms.
   `_clean_requirement` accepts a character and a faction as target and
   refuses a location.

DB1 -- writing a debt (BRIEF-0110-B, fixture). `create_debt` refuses, each
   with no row written: a location debtor, a debtor owing himself, a faction
   creditor with no contact, a contact who is not its active member, a
   character creditor with a contact, an origin `quest` with no quest, a
   money term of 0, a skill term on a base domain, and nothing owed without
   a reason. A valid debt toward a character: one row `open`, its terms in
   order, its fact free (`information`, aspect `dette`) with the debtor and
   the creditor as participants and the reason in its text, both parties
   knowing it at `knows`, secret as the debt is. Toward a faction, not
   secret: the contact is a participant and knows it, the faction has a
   `faction` default at `knows`; secret: no default.
DB2 -- repaying and forgiving (fixture). `settle_debt` refuses, with no row
   written: coins or items the debtor lacks, a fact he does not know and the
   receiver does not, a skill he is not Maître in. Once he can: the coins
   (ledger `debt`) and the items move to the creditor, the fact is learned
   and the skill taught by the receiver; a fact or a skill the receiver
   already holds lowers the receiver's regard toward the debtor by the
   world's setting instead (here 7 and 11). The debt is `settled` with
   `closed_at`, its fact rewritten as a `changement` (« a réglé »), both
   parties' rows refreshed, `has_debt_to` no longer met; a second repayment
   is refused. `forgive_debt` closes an open debt `forgiven` with its note
   (« a fait grâce »), and refuses a closed one.
DB3 -- a service (fixture, S2). `request_service` refuses, with no row
   written: the player as his own provider, a provider acting for a faction
   he is not a member of, a cost the player cannot pay now, nothing owed
   without a reason. Valid: the reward reaches the player (ledger
   `service`), the cost lowers the provider's regard, and one debt
   `service` is owed to the provider -- or to his faction, the provider its
   contact.
DB4 -- « régler à crédit » (fixture, A2). A quest whose giver is a faction
   with a contact costs 30 coins and 3 furs; the player has 10 coins and 1
   fur: `settle_quest` refuses, `credit_plan` pays 10 and 1 and owes the
   faction 20 coins and 2 furs; `settle_quest_on_credit` pays them, gives
   the reward, settles the quest and writes that one debt, origin `quest`,
   linked to the offer's contact. A quest with a fact cost the player does
   not know, or with nothing lacking, is refused credit with no row
   written. A faction creditor that is not the giver needs a contact named,
   and a member.
DB5 -- what the surfaces read (fixture and route functions). `debt_dict`
   carries exactly C-06's keys and its value in the world's unit; nothing
   the routes return carries `agenda_id` or `step_id`. `player_debts` splits
   what the player owes from what he is owed, an open one with its
   refusals. The routes answer 201/422 on a debt by hand, 409 on a refused
   repayment and forgiveness, 201/422 on a service. An offer's contact is
   refused on a character giver and for a non-member, kept and shown by
   `offer_dict`; `editor_choices` lists each faction's members; the
   settlement context's `credit` names the creditor, the lines owed and the
   preselected contact.

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
MIGRATION = ROOT / "scripts" / "migrate_v2_19_debts.py"
FRONTEND = ROOT / "frontend" / "src"

FAILURES: list[str] = []

DEBT_FORMS = ("has_debt_to", "no_debt_to")
DEBT_COLUMNS = (
    "id", "world_id", "debtor_entity_id", "creditor_entity_id", "contact_entity_id", "origin",
    "origin_quest_id", "reason", "is_secret", "fact_id", "status", "created_at", "closed_at", "closed_note",
)
DEBT_TERM_COLUMNS = ("id", "world_id", "debt_id", "term_order", "currency", "item_id", "fact_id", "skill_key", "amount")
DEBT_CHECKS = {
    "ck_debt_origin": "origin IN ('service','quest','creator')",
    "ck_debt_status": "status IN ('open','settled','forgiven')",
    "ck_debt_parties": "debtor_entity_id <> creditor_entity_id",
    "ck_debt_origin_quest": "(origin = 'quest') = (origin_quest_id IS NOT NULL)",
    "ck_debt_closed": "(status = 'open') = (closed_at IS NULL)",
}
DEBT_TERM_CHECKS = {
    "ck_debt_term_currency": "currency IN ('money','item','fact','skill')",
    "ck_debt_term_shape": (
        "(currency NOT IN ('money','item') OR (amount IS NOT NULL AND amount >= 1)) "
        "AND (currency <> 'item' OR item_id IS NOT NULL) "
        "AND (currency <> 'fact' OR fact_id IS NOT NULL) "
        "AND (currency <> 'skill' OR skill_key IS NOT NULL)"
    ),
}
CHANGED_TABLES = ("agenda_step_requirement", "quest_offer_requirement", "quest_economy", "quest_offer")

# The four tables as v2.18 created them (dumped from `main` at 42f2310).
_V218_DDL = (
    """CREATE TABLE agenda_step_requirement (
	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, step_id VARCHAR NOT NULL, type VARCHAR NOT NULL,
	target_entity_id VARCHAR, target_key VARCHAR, threshold INTEGER, PRIMARY KEY (id),
	CONSTRAINT ck_agenda_step_requirement_type CHECK (type IN ('knowledge','relation_gte','resource','location_reachable','has_met','faction_member','skill_rank_gte','quest_completed')),
	CONSTRAINT ck_agenda_step_requirement_shape CHECK ((type NOT IN ('relation_gte','location_reachable','has_met','faction_member') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)),
	FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(step_id) REFERENCES agenda_step (id),
	FOREIGN KEY(target_entity_id) REFERENCES entity (id))""",
    "CREATE UNIQUE INDEX idx_agenda_step_requirement_unique ON agenda_step_requirement "
    "(step_id, type, target_entity_id, target_key)",
    """CREATE TABLE quest_offer_requirement (
	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, offer_id VARCHAR NOT NULL, step_id VARCHAR,
	type VARCHAR NOT NULL, target_entity_id VARCHAR, target_key VARCHAR, threshold INTEGER, PRIMARY KEY (id),
	CONSTRAINT ck_quest_offer_requirement_type CHECK (type IN ('knowledge','relation_gte','resource','location_reachable','has_met','faction_member','skill_rank_gte','quest_completed')),
	CONSTRAINT ck_quest_offer_requirement_shape CHECK ((type NOT IN ('relation_gte','location_reachable','has_met','faction_member') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)),
	FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(offer_id) REFERENCES quest_offer (id),
	FOREIGN KEY(step_id) REFERENCES quest_offer_step (id), FOREIGN KEY(target_entity_id) REFERENCES entity (id))""",
    "CREATE INDEX idx_quest_offer_requirement_offer ON quest_offer_requirement (offer_id)",
    """CREATE TABLE quest_economy (
	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, rate_money INTEGER, rate_relation INTEGER,
	rate_fact INTEGER, rate_skill INTEGER, band_low_pct INTEGER, band_high_pct INTEGER,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, PRIMARY KEY (id),
	CONSTRAINT ck_quest_economy_rates CHECK ((rate_money IS NULL OR rate_money >= 0) AND (rate_relation IS NULL OR rate_relation >= 0) AND (rate_fact IS NULL OR rate_fact >= 0) AND (rate_skill IS NULL OR rate_skill >= 0) AND (band_low_pct IS NULL OR band_low_pct >= 0) AND (band_high_pct IS NULL OR band_high_pct >= 0)),
	FOREIGN KEY(world_id) REFERENCES world (id))""",
    "CREATE UNIQUE INDEX idx_quest_economy_world ON quest_economy (world_id)",
    """CREATE TABLE quest_offer (
	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, giver_entity_id VARCHAR NOT NULL, title VARCHAR NOT NULL,
	summary VARCHAR, repeatable BOOLEAN DEFAULT 0 NOT NULL, status VARCHAR DEFAULT 'open' NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	change_history JSON DEFAULT '[]' NOT NULL, PRIMARY KEY (id),
	CONSTRAINT ck_quest_offer_status CHECK (status IN ('open','closed')),
	FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(giver_entity_id) REFERENCES entity (id))""",
    "CREATE INDEX idx_quest_offer_world ON quest_offer (world_id)",
)


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> str:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    return db_path


def _read(rel: str) -> str:
    path = FRONTEND / rel
    if not path.exists():
        fail(f"{rel} is missing")
        return ""
    return path.read_text(encoding="utf-8")


# --- DA1 -----------------------------------------------------------------------

def _check_texts(table) -> dict[str, str]:
    from sqlalchemy import CheckConstraint

    return {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}


def _quoted(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"'([^']*)'", text))


def check_da1a() -> None:
    from world_engine import models
    from world_engine.quest_value import DEFAULT_RATES
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
    from world_engine.writes.quest_terms import ECONOMY_COLUMNS

    for model, columns, checks in ((models.Debt, DEBT_COLUMNS, DEBT_CHECKS),
                                   (models.DebtTerm, DEBT_TERM_COLUMNS, DEBT_TERM_CHECKS)):
        found = tuple(c.name for c in model.__table__.columns)
        if found != columns:
            fail(f"DA1a: {model.__tablename__} columns are {found}")
        if _check_texts(model.__table__) != checks:
            fail(f"DA1a: {model.__tablename__} CHECKs are {_check_texts(model.__table__)}")
    pairs = ((models.DEBT_ORIGINS, DEBT_CHECKS["ck_debt_origin"]), (models.DEBT_STATUSES, DEBT_CHECKS["ck_debt_status"]),
             (models.DEBT_CURRENCIES, DEBT_TERM_CHECKS["ck_debt_term_currency"]))
    for constant, check in pairs:
        if tuple(constant) != _quoted(check):
            fail(f"DA1a: {constant} differs from the CHECK {check}")
    if "contact_entity_id" not in models.QuestOffer.__table__.columns:
        fail("DA1a: quest_offer has no contact_entity_id")
    for name, default in (("debt_fact_relation", 10), ("debt_skill_relation", 20)):
        if name not in models.QuestEconomy.__table__.columns:
            fail(f"DA1a: quest_economy has no {name}")
        if DEFAULT_RATES.get(name) != default or name not in ECONOMY_COLUMNS:
            fail(f"DA1a: {name} is not a default {default} economy column")
    if EXPECTED_STATIC_SCHEMA_VERSION != "v2.19":
        fail(f"DA1a: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}")


def check_da1b() -> None:
    from world_engine import day_plan, day_resolve

    if tuple(day_plan.REQUIREMENT_TYPES[-2:]) != DEBT_FORMS:
        fail(f"DA1b: REQUIREMENT_TYPES ends with {day_plan.REQUIREMENT_TYPES[-2:]}")
    for form in DEBT_FORMS:
        if form not in day_plan.ENTITY_TARGET_TYPES:
            fail(f"DA1b: {form} is not an entity-target form")
        if form in day_plan.THRESHOLD_TYPES or form in day_plan.MODEL_REQUIREMENT_TYPES:
            fail(f"DA1b: {form} takes a threshold or is offered to the model")
        if form not in day_plan._EVALUATORS or form not in day_resolve._BLOCKED_DETAIL_FR:
            fail(f"DA1b: {form} has no evaluator or no French detail")
    text = _read("creation/questRequirements.js")
    for form in DEBT_FORMS:
        if not re.search(rf"^\s+{form}: \{{ label: '[^']+', list: 'givers', column: 'entity', threshold: false \}},$",
                         text, re.M):
            fail(f"DA1b: questRequirements.js does not offer {form} on the givers list")
    if "case 'givers': return choices.givers" not in text:
        fail("DA1b: targetOptions has no givers list")


def check_da1c(engine) -> None:
    from sqlmodel import Session, func, select

    from world_engine import link_author
    from world_engine.cockpit.crud._shared import RELATION_TYPES
    from world_engine.models import Entity, Relation, World
    from world_engine.relation_orientation import RETIRED_RELATION_TYPES
    from world_engine.writes import write_relation

    if "debt" not in RETIRED_RELATION_TYPES:
        fail("DA1c: debt is not retired")
    if "debt" in RELATION_TYPES or "debt" in link_author._LINK_RELATION_TYPES:
        fail("DA1c: debt is still offered as a relation type")
    seed = (ROOT / "scripts" / "seed_pilot.py").read_text(encoding="utf-8")
    template = re.search(r'NPC_LINK_PAIR_USER_TEMPLATE = """(.*?)"""', seed, re.S)
    if template is None or "debt" in template.group(1) or "fascination" not in template.group(1):
        fail("DA1c: the seeded link-pair prompt still offers debt, or was not found")
    with Session(engine) as session:
        world = World(name="Debts DA1", is_active=False)
        session.add(world)
        session.flush()
        a, b = Entity(world_id=world.id, type="character", name="A"), Entity(world_id=world.id, type="character", name="B")
        session.add_all([a, b])
        session.commit()
        before = session.exec(select(func.count()).select_from(Relation)).one()
        for mode in ("set", "delta"):
            try:
                write_relation(session, mode=mode, world_id=world.id, entity_a_id=a.id, entity_b_id=b.id,
                               type="debt", value=5)
                fail(f"DA1c: write_relation({mode}) accepted the type debt")
            except ValueError:
                pass
            session.rollback()
        if session.exec(select(func.count()).select_from(Relation)).one() != before:
            fail("DA1c: a refused debt relation wrote a row")


# --- DA2 -----------------------------------------------------------------------

def _shape(conn, table: str) -> list[tuple]:
    return sorted((r[1], r[2], r[3], r[4]) for r in conn.execute(f"PRAGMA table_info({table})"))


def _seed_v218(db_path: str) -> dict:
    from sqlmodel import Session

    from world_engine.db import create_db_and_tables, engine
    from world_engine.models import Agenda, AgendaStep, Entity, SchemaMeta, World

    create_db_and_tables()
    ids: dict = {}
    with Session(engine) as session:
        world = World(name="Debts DA2", is_active=True)
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
            session.add(SchemaMeta(id=1, static_version="v2.18"))
        session.commit()
    engine.dispose()
    with sqlite3.connect(db_path) as conn:
        ids["model_shapes"] = {t: _shape(conn, t) for t in CHANGED_TABLES + ("debt", "debt_term")}
        conn.execute("PRAGMA foreign_keys=OFF")
        for table in ("debt_term", "debt") + CHANGED_TABLES:
            conn.execute(f"DROP TABLE {table}")
        for statement in _V218_DDL:
            conn.execute(statement)
        w, p, s = ids["world"], ids["person"], ids["step"]
        conn.execute("INSERT INTO agenda_step_requirement (id, world_id, step_id, type, target_key) "
                     "VALUES ('req-1', ?, ?, 'knowledge', 'fact-x')", (w, s))
        conn.execute("INSERT INTO quest_offer (id, world_id, giver_entity_id, title) VALUES ('qo-1', ?, ?, 'q')", (w, p))
        conn.execute("INSERT INTO quest_offer_requirement (id, world_id, offer_id, type, target_entity_id) "
                     "VALUES ('qor-1', ?, 'qo-1', 'has_met', ?)", (w, p))
        conn.execute("INSERT INTO quest_economy (id, world_id, rate_fact, band_high_pct) VALUES ('qe-1', ?, 7, 140)", (w,))
        # A dangling reference this migration never wrote (AMENDMENT-0107-01).
        conn.execute("INSERT INTO session (id, world_id, number) VALUES ('orphan-session', 'gone-world', 9)")
    return ids


def _state(db_path: str) -> dict:
    with sqlite3.connect(db_path) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        return {
            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
            "rows": {t: conn.execute(f"SELECT id FROM {t} ORDER BY id").fetchall() for t in CHANGED_TABLES},
            "economy": conn.execute("SELECT rate_fact, band_high_pct FROM quest_economy").fetchall(),
            "sql": {t: conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (t,)).fetchone()[0]
                    for t in CHANGED_TABLES},
            "shapes": {t: _shape(conn, t) for t in CHANGED_TABLES + ("debt", "debt_term") if t in tables},
        }


def _run_migration(db_path: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True,
                          text=True, cwd=str(ROOT), timeout=120)


def check_da2(db_path: str) -> None:
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION

    ids = _seed_v218(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE schema_meta SET static_version = 'v2.17' WHERE id = 1")
    before = _state(db_path)
    result = _run_migration(db_path)
    if result.returncode == 0 or _state(db_path) != before:
        fail("DA2a: the migration ran on a v2.17 database or changed it")
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE schema_meta SET static_version = 'v2.18' WHERE id = 1")
    result = _run_migration(db_path)
    if result.returncode != 0:
        fail(f"DA2b: the migration failed: {result.stdout[-400:]} {result.stderr[-400:]}")
        return
    after = _state(db_path)
    if after["rows"] != before["rows"] or not all(after["rows"].values()):
        fail(f"DA2b: the rows are {after['rows']}")
    if after["economy"] != [(7, 140)]:
        fail(f"DA2b: the economy row is {after['economy']}")
    for table in ("agenda_step_requirement", "quest_offer_requirement"):
        absent = [form for form in DEBT_FORMS if f"'{form}'" not in after["sql"][table]]
        if absent:
            fail(f"DA2b: {table}'s stored CHECK lacks {absent}")
    for table in ("quest_economy", "debt", "debt_term"):
        if after["shapes"].get(table) != ids["model_shapes"][table]:
            fail(f"DA2b: {table} is {after['shapes'].get(table)}, expected the model's")
    if "contact_entity_id" not in {c[0] for c in after["shapes"]["quest_offer"]}:
        fail("DA2b: quest_offer has no contact_entity_id")
    if after["version"] != EXPECTED_STATIC_SCHEMA_VERSION:
        fail(f"DA2b: schema_meta is {after['version']}")
    if "Note: session rowid" not in result.stdout:
        fail("DA2b: the orphan session row was not noted")
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            conn.execute("INSERT INTO agenda_step_requirement (id, world_id, step_id, type, target_entity_id) "
                         "VALUES ('req-2', ?, ?, 'has_debt_to', ?)", (ids["world"], ids["step"], ids["person"]))
        except sqlite3.DatabaseError as exc:
            fail(f"DA2b: a has_debt_to row cannot be inserted: {exc}")
        dangling = [r for t in CHANGED_TABLES + ("debt", "debt_term")
                    for r in conn.execute(f"PRAGMA foreign_key_check({t})").fetchall()]
        if dangling:
            fail(f"DA2b: foreign_key_check {dangling}")
    again_before = _state(db_path)
    result = _run_migration(db_path)
    if result.returncode != 0 or _state(db_path) != again_before:
        fail(f"DA2c: a second run exit {result.returncode} or changed a row")


# --- DA3 -----------------------------------------------------------------------

def _da3_world(session) -> dict:
    from world_engine.models import Character, Entity, Faction, World

    world = World(name="Debts DA3", is_active=False)
    session.add(world)
    session.flush()
    ids = {"world": world.id}
    for key in ("pc", "npc", "other"):
        row = Entity(world_id=world.id, type="character", name=key.upper())
        session.add(row)
        session.flush()
        session.add(Character(id=row.id, world_id=world.id, character_type="player" if key == "pc" else "npc"))
        ids[key] = row.id
    for key, kind in (("guild", "faction"), ("place", "location")):
        row = Entity(world_id=world.id, type=kind, name=key.title())
        session.add(row)
        session.flush()
        if kind == "faction":
            session.add(Faction(id=row.id))
        ids[key] = row.id
    session.commit()
    return ids


def _debt(session, ids: dict, debtor: str, creditor: str, status: str = "open") -> None:
    from world_engine.models import Debt
    from world_engine.writes.facts import create_fact

    fact = create_fact(session, world_id=ids["world"], content="dette", created_by="check", facet="information")
    session.flush()
    session.add(Debt(world_id=ids["world"], debtor_entity_id=ids[debtor], creditor_entity_id=ids[creditor],
                     contact_entity_id=ids["other"] if creditor == "guild" else None, origin="creator",
                     fact_id=fact.id, status=status,
                     closed_at=None if status == "open" else datetime.now(UTC)))
    session.commit()


def _verdicts(session, pc, target: str) -> tuple[bool, bool]:
    from world_engine.day_plan import RequirementSpec, evaluate_specs

    has, none = evaluate_specs((RequirementSpec(type="has_debt_to", target_entity_id=target),
                                RequirementSpec(type="no_debt_to", target_entity_id=target)), pc, session)
    return has.met, none.met


def check_da3(engine) -> None:
    from sqlmodel import Session

    from world_engine.day_plan import RequirementSpec, evaluate_specs
    from world_engine.day_resolve import requirement_detail_fr
    from world_engine.models import Character
    from world_engine.writes.goals_agendas import _clean_requirement

    with Session(engine) as session:
        ids = _da3_world(session)
        pc = session.get(Character, ids["pc"])
        if _verdicts(session, pc, ids["npc"]) != (False, True):
            fail("DA3: with no debt, has_debt_to is met or no_debt_to is not")
        _debt(session, ids, "pc", "npc", status="settled")
        _debt(session, ids, "pc", "other")
        _debt(session, ids, "npc", "pc")
        if _verdicts(session, pc, ids["npc"]) != (False, True):
            fail("DA3: a settled debt, a debt to another or a debt owed to the character counted")
        _debt(session, ids, "pc", "npc")
        if _verdicts(session, pc, ids["npc"]) != (True, False):
            fail("DA3: an open debt toward the NPC is not seen")
        _debt(session, ids, "pc", "guild")
        if _verdicts(session, pc, ids["guild"]) != (True, False):
            fail("DA3: an open debt toward a faction is not seen")
        verdicts = evaluate_specs((RequirementSpec(type="has_debt_to", target_entity_id=ids["place"]),
                                   RequirementSpec(type="no_debt_to", target_entity_id=ids["npc"])), pc, session)
        details = [requirement_detail_fr(v) for v in verdicts]
        if details != ["il ne doit rien à Place", "il a encore une dette envers NPC"]:
            fail(f"DA3: the French details are {details}")
        for target, ok in (("npc", True), ("guild", True), ("place", False)):
            for form in DEBT_FORMS:
                try:
                    _clean_requirement(session, ids["world"], 0, RequirementSpec(type=form, target_entity_id=ids[target]))
                    accepted = True
                except ValueError:
                    accepted = False
                if accepted != ok:
                    fail(f"DA3: _clean_requirement {'refuses' if ok else 'accepts'} {form} toward {target}")


# --- DB --------------------------------------------------------------------------

def _db_world(session, active: bool = False) -> dict:
    from world_engine.models import Character, Entity, Fact, Faction, Item, SkillDefinition, World
    from world_engine.writes import write_membership

    world = World(name="Debts DB", is_active=active)
    session.add(world)
    session.flush()
    ids = {"world": world.id}
    for key, kind, name in (("pc", "character", "Millys"), ("npc", "character", "Garde"),
                            ("agent", "character", "Ivo"), ("outsider", "character", "Pell"),
                            ("guild", "faction", "Guilde"), ("other_guild", "faction", "Ordre"),
                            ("place", "location", "Col"), ("fur", "item", "Fourrure")):
        row = Entity(world_id=world.id, type=kind, name=name)
        session.add(row)
        session.flush()
        ids[key] = row.id
    session.add_all([Character(id=ids[k], world_id=world.id, character_type="player" if k == "pc" else "npc")
                     for k in ("pc", "npc", "agent", "outsider")]
                    + [Faction(id=ids["guild"]), Faction(id=ids["other_guild"]), Item(id=ids["fur"], value=3)])
    for key, name in (("herb", "Herboristerie"), ("forge", "Forge")):
        definition = SkillDefinition(world_id=world.id, name=name, base_domain="perception")
        session.add(definition)
        session.flush()
        ids[key] = definition.id
    for key, text in (("secret", "Le passage secret"), ("map", "La carte du col"), ("rumor", "Une rumeur")):
        fact = Fact(world_id=world.id, content_raw=text, created_by="check", facet="information")
        session.add(fact)
        session.flush()
        ids[key] = fact.id
    for member, faction in (("agent", "guild"), ("npc", "other_guild")):
        session.add(write_membership(session, mode="open", world_id=world.id, entity_id=ids[member],
                                     faction_id=ids[faction]))
    session.commit()
    return ids


def _counts(session) -> tuple:
    from sqlmodel import func, select

    from world_engine.models import Debt, DebtTerm, Fact, FactDefault, ItemHolding, Knowledge, Ledger, Relation, Skill

    return tuple(session.exec(select(func.count()).select_from(m)).one()
                 for m in (Debt, DebtTerm, Fact, FactDefault, Knowledge, Ledger, ItemHolding, Relation, Skill))


def _refused(session, label: str, call) -> None:
    before = _counts(session)
    try:
        call()
    except ValueError:
        session.rollback()
        if _counts(session) != before:
            fail(f"{label}: a refusal wrote rows")
        return
    session.rollback()
    fail(f"{label}: accepted")


def _new_debt(session, ids, creditor="npc", contact=None, secret=False, terms=None, reason="pour la corde"):
    from world_engine.writes import DebtTermSpec, create_debt

    terms = terms if terms is not None else [DebtTermSpec(currency="money", amount=5)]
    debt = create_debt(session, world_id=ids["world"], debtor_id=ids["pc"], creditor_id=ids[creditor],
                       contact_id=ids[contact] if contact else None, origin="creator", reason=reason,
                       is_secret=secret, terms=terms, changed_by="check")
    session.commit()
    return debt


def _knowledge(session, entity_id, fact_id):
    from sqlmodel import select

    from world_engine.models import Knowledge

    return session.exec(select(Knowledge).where(Knowledge.entity_id == entity_id, Knowledge.fact_id == fact_id)).first()


def check_db1(session, ids) -> None:
    from sqlmodel import select

    from world_engine.models import DebtTerm, Fact, FactDefault, FactParticipant
    from world_engine.writes import DebtTermSpec, create_debt

    def make(**over):
        fields = dict(world_id=ids["world"], debtor_id=ids["pc"], creditor_id=ids["npc"], contact_id=None,
                      origin="creator", reason="r", is_secret=False, terms=[DebtTermSpec(currency="money", amount=5)])
        fields.update(over)
        return lambda: create_debt(session, changed_by="check", **fields)

    bad = {
        "a location debtor": make(debtor_id=ids["place"]),
        "a debtor owing himself": make(creditor_id=ids["pc"]),
        "a faction with no contact": make(creditor_id=ids["guild"]),
        "a contact not a member": make(creditor_id=ids["guild"], contact_id=ids["outsider"]),
        "a character creditor with a contact": make(contact_id=ids["agent"]),
        "origin quest with no quest": make(origin="quest"),
        "a money term of 0": make(terms=[DebtTermSpec(currency="money", amount=0)]),
        "a skill term on a base domain": make(terms=[DebtTermSpec(currency="skill", skill_key="perception")]),
        "nothing owed without a reason": make(terms=[], reason="  "),
    }
    for label, call in bad.items():
        _refused(session, f"DB1 ({label})", call)
    debt = _new_debt(session, ids, secret=True, terms=[DebtTermSpec(currency="money", amount=5),
                                                       DebtTermSpec(currency="item", item_id=ids["fur"], amount=2)])
    terms = session.exec(select(DebtTerm).where(DebtTerm.debt_id == debt.id).order_by(DebtTerm.term_order)).all()
    fact = session.get(Fact, debt.fact_id)
    parts = set(session.exec(select(FactParticipant.entity_id).where(FactParticipant.fact_id == fact.id)).all())
    if debt.status != "open" or [(t.term_order, t.currency) for t in terms] != [(1, "money"), (2, "item")]:
        fail(f"DB1: the debt is {debt.status} with terms {[(t.term_order, t.currency) for t in terms]}")
    if fact.facet != "information" or fact.aspect != "dette" or "pour la corde" not in fact.content_raw:
        fail(f"DB1: the fact is {fact.facet}/{fact.aspect} « {fact.content_raw} »")
    if parts != {ids["pc"], ids["npc"]}:
        fail(f"DB1: the participants are {parts}")
    for party in ("pc", "npc"):
        row = _knowledge(session, ids[party], fact.id)
        if row is None or row.level != "knows" or not row.is_secret:
            fail(f"DB1: {party} does not know the secret debt at knows")
    open_debt = _new_debt(session, ids, creditor="guild", contact="agent")
    secret_debt = _new_debt(session, ids, creditor="guild", contact="agent", secret=True)
    for d, expected in ((open_debt, 1), (secret_debt, 0)):
        defaults = session.exec(select(FactDefault).where(FactDefault.fact_id == d.fact_id)).all()
        if len(defaults) != expected or any(x.scope_type != "faction" or x.scope_id != ids["guild"] for x in defaults):
            fail(f"DB1: a faction debt (secret {d.is_secret}) has defaults {[(x.scope_type, x.scope_id) for x in defaults]}")
    if _knowledge(session, ids["agent"], open_debt.fact_id) is None:
        fail("DB1: the contact does not know the faction debt")


def _db2_stock(session, ids) -> None:
    from world_engine.models import Knowledge, Skill
    from world_engine.writes import upsert_quest_economy, write_holding, write_ledger_entry

    w = ids["world"]
    write_ledger_entry(session, world_id=w, entity_id=ids["pc"], amount=50, source_type="creator")
    write_holding(session, world_id=w, item_id=ids["fur"], holder_entity_id=ids["pc"], quantity=5, changed_by="check")
    session.add_all([Knowledge(entity_id=ids["pc"], fact_id=ids["secret"], level="knows"),
                     Knowledge(entity_id=ids["pc"], fact_id=ids["map"], level="knows"),
                     Knowledge(entity_id=ids["npc"], fact_id=ids["map"], level="knows"),
                     Skill(character_id=ids["pc"], domain="perception", skill_definition_id=ids["herb"], rank=5,
                           change_history=[]),
                     Skill(character_id=ids["pc"], domain="perception", skill_definition_id=ids["forge"], rank=5,
                           change_history=[]),
                     Skill(character_id=ids["npc"], domain="perception", skill_definition_id=ids["forge"], rank=0,
                           change_history=[])])
    upsert_quest_economy(session, world_id=w, values={"debt_fact_relation": 7, "debt_skill_relation": 11})
    session.commit()


def _regard(session, ids, who="npc") -> int:
    from sqlmodel import select

    from world_engine.models import Relation

    row = session.exec(select(Relation).where(Relation.entity_a_id == ids[who], Relation.entity_b_id == ids["pc"])).first()
    return row.intensity if row else 50


def check_db2(session, ids) -> None:
    from world_engine.day_plan import RequirementSpec, evaluate_specs
    from world_engine.ledger import get_balance
    from world_engine.holdings import held_quantity
    from sqlmodel import select

    from world_engine.models import Character, Debt, Fact
    from world_engine.writes import DebtTermSpec, forgive_debt, settle_debt
    from world_engine.writes.quest_settlement import skill_row

    lacking = (("coins", [DebtTermSpec(currency="money", amount=500)]),
               ("furs", [DebtTermSpec(currency="item", item_id=ids["fur"], amount=9)]),
               ("a fact", [DebtTermSpec(currency="fact", fact_id=ids["secret"])]),
               ("a skill", [DebtTermSpec(currency="skill", skill_key=ids["herb"])]))
    for label, terms in lacking:
        debt = _new_debt(session, ids, creditor="outsider", terms=terms)
        _refused(session, f"DB2 ({label} lacking)", lambda d=debt: settle_debt(session, debt=d, changed_by="check"))
    _db2_stock(session, ids)
    terms = [DebtTermSpec(currency="money", amount=20), DebtTermSpec(currency="item", item_id=ids["fur"], amount=2),
             DebtTermSpec(currency="fact", fact_id=ids["secret"]), DebtTermSpec(currency="fact", fact_id=ids["map"]),
             DebtTermSpec(currency="skill", skill_key=ids["herb"]), DebtTermSpec(currency="skill", skill_key=ids["forge"])]
    debt = _new_debt(session, ids, terms=terms)
    pc = session.get(Character, ids["pc"])
    regard = _regard(session, ids)
    balance, furs = get_balance(session, ids["pc"]), held_quantity(session, ids["pc"], ids["fur"])
    settle_debt(session, debt=debt, changed_by="check")
    session.commit()
    if get_balance(session, ids["pc"]) != balance - 20 or held_quantity(session, ids["pc"], ids["fur"]) != furs - 2:
        fail("DB2: the coins or the furs did not leave the debtor")
    if get_balance(session, ids["npc"]) < 20 or held_quantity(session, ids["npc"], ids["fur"]) != 2:
        fail("DB2: the creditor did not receive the coins or the furs")
    if _knowledge(session, ids["npc"], ids["secret"]) is None or skill_row(session, ids["npc"], ids["herb"]) is None:
        fail("DB2: the fact was not learned or the skill not taught")
    if _regard(session, ids) != regard - 7 - 11:
        fail(f"DB2: the regard went {regard} -> {_regard(session, ids)}, expected -7 -11")
    fact = session.get(Fact, debt.fact_id)
    if debt.status != "settled" or debt.closed_at is None or "a réglé" not in fact.content_raw:
        fail(f"DB2: the debt is {debt.status}, fact « {fact.content_raw} »")
    if not fact.change_history or fact.change_history[-1].get("kind") != "changement":
        fail("DB2: the fact was not rewritten as a changement")
    row = _knowledge(session, ids["pc"], fact.id)
    if row is None or len(row.change_history or []) < 1:
        fail("DB2: the debtor's knowledge of the debt was not refreshed")
    for left in session.exec(select(Debt).where(Debt.creditor_entity_id == ids["npc"], Debt.status == "open")).all():
        forgive_debt(session, debt=left, note=None, changed_by="check")
    session.commit()
    if evaluate_specs((RequirementSpec(type="has_debt_to", target_entity_id=ids["npc"]),), pc, session)[0].met:
        fail("DB2: a settled debt is still owed")
    _refused(session, "DB2 (a second repayment)", lambda: settle_debt(session, debt=debt, changed_by="check"))
    other = _new_debt(session, ids)
    forgive_debt(session, debt=other, note="en souvenir", changed_by="check")
    session.commit()
    text = session.get(Fact, other.fact_id).content_raw
    if other.status != "forgiven" or other.closed_note != "en souvenir" or "a fait grâce" not in text:
        fail(f"DB2: the forgiven debt is {other.status} « {text} »")
    _refused(session, "DB2 (forgiving a closed debt)", lambda: forgive_debt(session, debt=other, note=None,
                                                                             changed_by="check"))


def check_db3(session, ids) -> None:
    from sqlmodel import select

    from world_engine.models import Character, Ledger
    from world_engine.writes import DebtTermSpec, TermSpec, request_service

    pc = session.get(Character, ids["pc"])
    owed = [DebtTermSpec(currency="money", amount=15)]
    reward = [TermSpec(direction="reward", currency="money", amount=15),
              TermSpec(direction="cost", currency="relation", amount=4)]

    def ask(**over):
        fields = dict(character=pc, provider_id=ids["npc"], on_behalf_of_id=None, terms=reward, owed=owed,
                      reason="un prêt", is_secret=False)
        fields.update(over)
        return lambda: request_service(session, **fields)

    _refused(session, "DB3 (himself as provider)", ask(provider_id=ids["pc"]))
    _refused(session, "DB3 (for a faction he is not in)", ask(on_behalf_of_id=ids["guild"]))
    _refused(session, "DB3 (an unpayable cost)", ask(terms=[TermSpec(direction="cost", currency="money", amount=9999)]))
    _refused(session, "DB3 (nothing owed, no reason)", ask(owed=[], reason=None))
    regard = _regard(session, ids)
    debt = ask()()
    session.commit()
    lines = session.exec(select(Ledger).where(Ledger.entity_id == ids["pc"], Ledger.source_type == "service")).all()
    if [line.amount for line in lines] != [15]:
        fail(f"DB3: the service's ledger lines are {[line.amount for line in lines]}")
    if _regard(session, ids) != regard - 4:
        fail("DB3: the service's cost did not lower the provider's regard")
    if (debt.origin, debt.creditor_entity_id, debt.contact_entity_id) != ("service", ids["npc"], None):
        fail(f"DB3: the service's debt is {(debt.origin, debt.creditor_entity_id, debt.contact_entity_id)}")
    debt = ask(provider_id=ids["agent"], on_behalf_of_id=ids["guild"], terms=[])()
    session.commit()
    if (debt.creditor_entity_id, debt.contact_entity_id) != (ids["guild"], ids["agent"]):
        fail("DB3: a service for a faction is not owed to it, its provider the contact")


def _db4_quest(session, ids, giver, terms, title, contact=None):
    from world_engine.day_plan import PlanStep
    from world_engine.models import Character
    from world_engine.writes import accept_quest, write_quest_offer

    offer = write_quest_offer(session, world_id=ids["world"], offer=None, giver_entity_id=ids[giver], title=title,
                              summary=None, repeatable=True, status="open", eligibility=[],
                              steps=[PlanStep(objective="Chasser", cost=1, domain=None)], terms=terms,
                              contact_entity_id=ids[contact] if contact else None)
    session.flush()
    quest = accept_quest(session, offer=offer, character=session.get(Character, ids["pc"]))
    session.commit()
    return quest


def check_db4(session, ids) -> None:
    from sqlmodel import select

    from world_engine.holdings import held_quantity
    from world_engine.ledger import get_balance
    from world_engine.models import Debt, DebtTerm
    from world_engine.writes import (
        TermSpec, credit_plan, settle_quest, settle_quest_on_credit, write_holding, write_ledger_entry,
    )

    w = ids["world"]
    write_ledger_entry(session, world_id=w, entity_id=ids["pc"], amount=10 - get_balance(session, ids["pc"]),
                       source_type="creator")
    write_holding(session, world_id=w, item_id=ids["fur"], holder_entity_id=ids["pc"], quantity=1, changed_by="check")
    session.commit()
    terms = [TermSpec(direction="cost", currency="money", amount=30),
             TermSpec(direction="cost", currency="item", item_id=ids["fur"], amount=3),
             TermSpec(direction="reward", currency="relation", amount=5, counterparty_entity_id=ids["agent"])]
    quest = _db4_quest(session, ids, "guild", terms, "La meute", contact="agent")
    _refused(session, "DB4 (settle_quest with coins lacking)", lambda: settle_quest(session, quest=quest))
    plan = credit_plan(session, quest)
    owed = {k: [(t.currency, t.amount) for t in v] for k, v in plan.owed.items()}
    if plan.refusals or sorted(plan.paid.values()) != [1, 10] or owed != {ids["guild"]: [("money", 20), ("item", 2)]}:
        fail(f"DB4: the plan is {plan.refusals} {plan.paid} {owed}")
    settle_quest_on_credit(session, quest=quest, contacts={}, is_secret=False)
    session.commit()
    debt = session.exec(select(Debt).where(Debt.origin_quest_id == quest.id)).first()
    if quest.settled_at is None or get_balance(session, ids["pc"]) != 0 or held_quantity(session, ids["pc"], ids["fur"]):
        fail("DB4: the quest was not settled with what the player had")
    if debt is None or (debt.creditor_entity_id, debt.contact_entity_id, debt.origin) != (ids["guild"], ids["agent"], "quest"):
        fail("DB4: no debt toward the giver faction, linked to the offer's contact")
    else:
        rows = session.exec(select(DebtTerm).where(DebtTerm.debt_id == debt.id).order_by(DebtTerm.term_order)).all()
        if [(t.currency, t.amount) for t in rows] != [("money", 20), ("item", 2)]:
            fail(f"DB4: the debt owes {[(t.currency, t.amount) for t in rows]}")
    fact_quest = _db4_quest(session, ids, "npc", [TermSpec(direction="cost", currency="fact", fact_id=ids["rumor"],
                                                           counterparty_entity_id=ids["outsider"]),
                                                  TermSpec(direction="cost", currency="money", amount=99)], "Le col")
    paid_quest = _db4_quest(session, ids, "npc", [TermSpec(direction="reward", currency="money", amount=1)], "Rien")
    for label, q in (("a fact cost", fact_quest), ("nothing lacking", paid_quest)):
        _refused(session, f"DB4 (credit with {label})",
                 lambda q=q: settle_quest_on_credit(session, quest=q, contacts={}, is_secret=False))
    other = _db4_quest(session, ids, "npc", [TermSpec(direction="cost", currency="money", amount=5,
                                                      counterparty_entity_id=ids["other_guild"])], "L'ordre")
    _refused(session, "DB4 (a faction creditor with no contact)",
             lambda: settle_quest_on_credit(session, quest=other, contacts={}, is_secret=False))
    _refused(session, "DB4 (a contact who is not a member)",
             lambda: settle_quest_on_credit(session, quest=other, contacts={ids["other_guild"]: ids["agent"]},
                                            is_secret=False))
    settle_quest_on_credit(session, quest=other, contacts={ids["other_guild"]: ids["npc"]}, is_secret=True)
    session.commit()


DEBT_DICT_KEYS = {
    "id", "debtor_id", "debtor_name", "creditor_id", "creditor_name", "contact_id", "contact_name", "origin",
    "origin_label", "reason", "is_secret", "status", "status_label", "created_at", "closed_at", "closed_note",
    "terms", "value",
}


def _keys_deep(value) -> set:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys_deep(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys_deep(v)}
    return set()


def _http(label: str, status: int, call) -> None:
    from fastapi import HTTPException

    try:
        call()
    except HTTPException as exc:
        if exc.status_code != status:
            fail(f"{label}: answered {exc.status_code}, expected {status}")
        return
    fail(f"{label}: answered 2xx, expected {status}")


def _db5_routes(session, ids) -> None:
    from world_engine.cockpit.routes import debts as routes
    from world_engine.cockpit.routes import quests as quest_routes

    created = routes.write_debt_by_hand(routes.DebtBody(
        debtor_entity_id=ids["pc"], creditor_entity_id=ids["npc"], reason="un service",
        terms=[routes.DebtTermBody(currency="money", amount=500)]), db=session)
    if set(created) != DEBT_DICT_KEYS or created["value"] != 500 or created["status_label"] != "due":
        fail(f"DB5: debt_dict is {sorted(created)} value {created.get('value')}")
    _http("DB5 (a debt by hand toward a place)", 422, lambda: routes.write_debt_by_hand(routes.DebtBody(
        debtor_entity_id=ids["pc"], creditor_entity_id=ids["place"], reason="r"), db=session))
    _http("DB5 (an unpayable repayment)", 409, lambda: routes.repay(created["id"], db=session))
    routes.forgive(created["id"], routes.ForgiveBody(note="n"), db=session)
    _http("DB5 (forgiving twice)", 409, lambda: routes.forgive(created["id"], routes.ForgiveBody(), db=session))
    payload = routes.journee_debts(db=session)
    owes_ids = {d["id"] for d in payload["owes"]}
    if created["id"] not in owes_ids or "owed" not in payload or any(d["debtor_id"] != ids["pc"]
                                                                    for d in payload["owes"]):
        fail("DB5: player_debts does not list what the player owes")
    if not all("refusals" in d and "repayable" in d for d in payload["owes"] + payload["owed"]):
        fail("DB5: player_debts lacks the refusals")
    served = routes.ask_service(routes.ServiceBody(provider_entity_id=ids["npc"], reason="un abri"), db=session)
    _http("DB5 (a service from a place)", 422, lambda: routes.ask_service(
        routes.ServiceBody(provider_entity_id=ids["place"], reason="r"), db=session))
    every = [created, routes.list_debts(db=session), payload, served]
    if _keys_deep(every) & {"agenda_id", "step_id"}:
        fail("DB5: a debt payload names an agenda or a step")
    _http("DB5 (an offer contact on a character giver)", 422, lambda: quest_routes.create_offer(
        quest_routes.OfferBody(giver_entity_id=ids["npc"], contact_entity_id=ids["agent"], title="t",
                               steps=[quest_routes.OfferStepBody(objective="o", cost=1)]), db=session))
    _http("DB5 (an offer contact not a member)", 422, lambda: quest_routes.create_offer(
        quest_routes.OfferBody(giver_entity_id=ids["guild"], contact_entity_id=ids["outsider"], title="t",
                               steps=[quest_routes.OfferStepBody(objective="o", cost=1)]), db=session))
    offer = quest_routes.create_offer(quest_routes.OfferBody(
        giver_entity_id=ids["guild"], contact_entity_id=ids["agent"], title="t",
        steps=[quest_routes.OfferStepBody(objective="o", cost=1)]), db=session)
    if (offer["contact_entity_id"], offer["contact_name"]) != (ids["agent"], "Ivo"):
        fail(f"DB5: offer_dict shows the contact {offer.get('contact_entity_id')}")
    members = quest_routes.offer_choices(db=session)["members"]
    if [m["id"] for m in members.get(ids["guild"], [])] != [ids["agent"]]:
        fail(f"DB5: editor_choices lists the guild's members as {members.get(ids['guild'])}")


def _db5_credit_context(session, ids) -> None:
    from world_engine.ledger import get_balance
    from world_engine.quest_settlement_view import settlement_context
    from world_engine.writes import TermSpec, write_ledger_entry

    balance = get_balance(session, ids["pc"])
    if balance > 0:
        write_ledger_entry(session, world_id=ids["world"], entity_id=ids["pc"], amount=-balance, source_type="creator")
    quest = _db4_quest(session, ids, "guild", [TermSpec(direction="cost", currency="money", amount=8)], "Dîme",
                       contact="agent")
    credit = settlement_context(session, quest)["credit"]
    debts = credit["debts"]
    if not credit["possible"] or len(debts) != 1 or debts[0]["creditor_id"] != ids["guild"] \
            or debts[0]["lines"] != ["8 pièce(s)"] or debts[0]["contact_id"] != ids["agent"] \
            or [m["id"] for m in debts[0]["members"]] != [ids["agent"]]:
        fail(f"DB5: the settlement's credit is {credit}")


def check_db(engine) -> None:
    from sqlmodel import Session

    with Session(engine) as session:
        ids = _db_world(session)
        check_db1(session, ids)
        check_db2(session, ids)
        check_db3(session, ids)
        check_db4(session, ids)
    with Session(engine) as session:
        from world_engine.models import World

        for world in session.exec(__import__("sqlmodel").select(World)).all():
            world.is_active = False
            session.add(world)
        session.commit()
        ids = _db_world(session, active=True)
        _db5_routes(session, ids)
        _db5_credit_context(session, ids)


def main() -> int:
    db_path = _fresh_db()
    check_da1a()
    check_da1b()
    check_da2(db_path)
    from world_engine.db import create_db_and_tables, engine
    create_db_and_tables()
    check_da1c(engine)
    check_da3(engine)
    check_db(engine)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: debts -- v2.19 lays the debt tables, an offer's contact and the economy's two debt "
          "settings, migrates from v2.18 only, widens the requirement vocabulary with has_debt_to and "
          "no_debt_to for the creator alone, judges an open debt toward a character or a faction, and "
          "retires the relation type debt; a debt is validated whole, written with its fact known by "
          "both parties (secret as it is, a faction's members when it is not), repaid at once or "
          "forgiven and never deleted, its fact changed; a service applies its terms and owes the rest; "
          "« régler à crédit » pays what the player has and owes the rest per creditor; the surfaces "
          "read every debt without an agenda or step id")
    return 0


if __name__ == "__main__":
    sys.exit(main())
