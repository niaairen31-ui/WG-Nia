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


def main() -> int:
    db_path = _fresh_db()
    check_da1a()
    check_da1b()
    check_da2(db_path)
    from world_engine.db import create_db_and_tables, engine
    create_db_and_tables()
    check_da1c(engine)
    check_da3(engine)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: debts -- v2.19 lays the debt tables, an offer's contact and the economy's two debt "
          "settings, migrates from v2.18 only, widens the requirement vocabulary with has_debt_to and "
          "no_debt_to for the creator alone, judges an open debt toward a character or a faction, and "
          "retires the relation type debt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
