"""G1 check for TICKET-0116 (BRIEF-0116-A) -- v2.29 stores the rank trials.

The storage only: where a world, a system or a skill says that leaving a
rank asks a trial, the room in the term tables for a `rank` reward, and the
room in `quest_request` for a request born of a skill rather than a day.

TS1 -- shapes (import). `SkillRank.trial_to_next` is a NOT NULL boolean with
   server default `0`; `SkillSystem` and `SkillDefinition` each declare
   `trial_to_rank_1..5`, nullable; `QUEST_TERM_CURRENCY_CHECK` and
   `QUEST_TERM_SHAPE_CHECK` equal C-01's texts exactly; `QuestOfferTerm` and
   `QuestTerm` carry them under their `ck_*_currency`/`ck_*_shape` names;
   `QuestRequest`'s columns are C-01's tuple in order, `pass_play_id` and
   `agenda_step_id` nullable, its CHECK names `{answer, origin, status,
   trigger}`, `ck_quest_request_origin`'s text is C-01's, its indexes
   `{idx_quest_request_step, idx_quest_request_trial,
   idx_quest_request_world}` with only `idx_quest_request_step` unique;
   `EXPECTED_STATIC_SCHEMA_VERSION` is v2.29 or later; the migration
   `scripts/migrate_v2_29_rank_trials.py` exists and
   `_PREVIOUS_VERSION == "v2.28"`.
TS2 -- the CHECKs hold (fresh `create_all`, raw INSERTs, parents inserted
   raw): a `quest_offer_term` reward `rank` with `skill_key='agility'`,
   `amount=2` inserts; a `rank` cost, a `rank` with `amount` 6, a `rank` with
   `skill_key` NULL each raise `IntegrityError`; a `quest_request` `trial`
   with `skill_key`, `target_rank=3`, no day, no step inserts; a `trial` with
   a step, a `trial` with `target_rank` 0, a `route` with no step, a `route`
   with a `skill_key` each raise `IntegrityError`.
TS3 -- the migration, run as a subprocess (`WORLD_ENGINE_DATABASE_URL` the
   fixture, `WORLD_ENGINE_ENV=test`) on a v2.28-shaped file: `create_all`,
   then the six tables dropped and recreated in their v2.28 DDL (`V228_DDL`,
   compiled from the models at `246e89b`); one row in each (a `skill_rank`
   at rank 2; a system; a definition; an offer term `money` 5; a quest term
   `money` 3; a `route` request whose `pass_play_id` names no row -- a
   dangling reference that predates the migration), parents inserted raw:
   a. at `schema_meta` v2.27 it exits non-zero and changes nothing (the six
      tables' `PRAGMA table_info` unchanged);
   b. at v2.28 it exits zero; the eleven columns exist; the six rows are
      kept with their ids; `trial_to_next` is 0; the rebuilt tables carry
      the model's CHECK names and indexes; its output names the dangling
      `quest_request` row as a note; `schema_meta` is v2.29;
   c. a second run exits zero, prints « DDL already applied. » and changes
      no row.

Fresh temp-file SQLite databases (`WORLD_ENGINE_DATABASE_URL` set before any
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

ROOT = pathlib.Path(__file__).resolve().parents[3]
MIGRATION = ROOT / "scripts" / "migrate_v2_29_rank_trials.py"

FAILURES: list[str] = []

CURRENCY_CHECK = "currency IN ('money','item','relation','fact','skill','rank')"
SHAPE_CHECK = (
    "(currency NOT IN ('money','item','relation') OR (amount IS NOT NULL AND amount >= 1)) "
    "AND (currency <> 'item' OR item_id IS NOT NULL) "
    "AND (currency <> 'fact' OR fact_id IS NOT NULL) "
    "AND (currency <> 'skill' OR skill_key IS NOT NULL) "
    "AND (currency <> 'rank' OR (direction = 'reward' AND skill_key IS NOT NULL AND amount BETWEEN 1 AND 5))"
)
ORIGIN_CHECK = (
    "(trigger = 'trial' AND skill_key IS NOT NULL AND target_rank BETWEEN 1 AND 5 "
    "AND pass_play_id IS NULL AND agenda_step_id IS NULL) "
    "OR (trigger <> 'trial' AND skill_key IS NULL AND target_rank IS NULL "
    "AND pass_play_id IS NOT NULL AND agenda_step_id IS NOT NULL)"
)
REQUEST_COLUMNS = ("id", "world_id", "character_id", "pass_play_id", "agenda_step_id", "trigger", "declaration",
                   "subject", "status", "existence_answer", "creator_text", "existing_entity_id", "lore_entry_id",
                   "mutation_id", "offer_id", "note", "skill_key", "target_rank", "created_at", "updated_at",
                   "change_history")
REQUEST_CHECKS = {"ck_quest_request_answer", "ck_quest_request_origin", "ck_quest_request_status",
                  "ck_quest_request_trigger"}
REQUEST_INDEXES = {"idx_quest_request_step", "idx_quest_request_trial", "idx_quest_request_world"}
TRIAL_COLUMNS = tuple(f"trial_to_rank_{n}" for n in range(1, 6))
ADDED = {"skill_rank": ("trial_to_next",), "skill_system": TRIAL_COLUMNS, "skill_definition": TRIAL_COLUMNS,
         "quest_request": ("skill_key", "target_rank")}
SIX = ("skill_rank", "skill_system", "skill_definition", "quest_offer_term", "quest_term", "quest_request")
REBUILT_CHECKS = {
    "quest_offer_term": {"ck_quest_offer_term_direction", "ck_quest_offer_term_currency",
                         "ck_quest_offer_term_shape"},
    "quest_term": {"ck_quest_term_direction", "ck_quest_term_currency", "ck_quest_term_shape"},
    "quest_request": REQUEST_CHECKS,
}
REBUILT_INDEXES = {
    "quest_offer_term": {"idx_quest_offer_term_offer": 0},
    "quest_term": {"idx_quest_term_quest": 0},
    "quest_request": {"idx_quest_request_step": 1, "idx_quest_request_trial": 0, "idx_quest_request_world": 0},
}

# The six tables in their v2.28 DDL, compiled from the models at `246e89b`.
V228_DDL = """
CREATE TABLE skill_rank (
	id VARCHAR NOT NULL,
	world_id VARCHAR NOT NULL,
	rank INTEGER NOT NULL,
	label VARCHAR NOT NULL,
	points_to_next INTEGER,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_skill_rank_rank CHECK (rank BETWEEN 0 AND 5),
	CONSTRAINT ck_skill_rank_points CHECK ((rank = 5 AND points_to_next IS NULL) OR (rank < 5 AND points_to_next >= 1)),
	FOREIGN KEY(world_id) REFERENCES world (id)
);
CREATE UNIQUE INDEX idx_skill_rank_world_rank ON skill_rank (world_id, rank);

CREATE TABLE skill_system (
	id VARCHAR NOT NULL,
	world_id VARCHAR NOT NULL,
	name VARCHAR NOT NULL,
	description VARCHAR,
	points_to_rank_1 INTEGER,
	points_to_rank_2 INTEGER,
	points_to_rank_3 INTEGER,
	points_to_rank_4 INTEGER,
	points_to_rank_5 INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_skill_system_rank_points CHECK ((points_to_rank_1 IS NULL OR points_to_rank_1 >= 1) AND (points_to_rank_2 IS NULL OR points_to_rank_2 >= 1) AND (points_to_rank_3 IS NULL OR points_to_rank_3 >= 1) AND (points_to_rank_4 IS NULL OR points_to_rank_4 >= 1) AND (points_to_rank_5 IS NULL OR points_to_rank_5 >= 1)),
	FOREIGN KEY(world_id) REFERENCES world (id)
);
CREATE INDEX idx_skill_system_world ON skill_system (world_id);
CREATE UNIQUE INDEX idx_skill_system_world_name ON skill_system (world_id, name);

CREATE TABLE skill_definition (
	id VARCHAR NOT NULL,
	world_id VARCHAR NOT NULL,
	name VARCHAR NOT NULL,
	base_domain VARCHAR NOT NULL,
	system_id VARCHAR,
	description VARCHAR,
	points_to_rank_1 INTEGER,
	points_to_rank_2 INTEGER,
	points_to_rank_3 INTEGER,
	points_to_rank_4 INTEGER,
	points_to_rank_5 INTEGER,
	requires_master BOOLEAN DEFAULT 0 NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_skill_definition_base_domain CHECK (base_domain IN ('physical','agility','perception','composure')),
	CONSTRAINT ck_skill_definition_rank_points CHECK ((points_to_rank_1 IS NULL OR points_to_rank_1 >= 1) AND (points_to_rank_2 IS NULL OR points_to_rank_2 >= 1) AND (points_to_rank_3 IS NULL OR points_to_rank_3 >= 1) AND (points_to_rank_4 IS NULL OR points_to_rank_4 >= 1) AND (points_to_rank_5 IS NULL OR points_to_rank_5 >= 1)),
	FOREIGN KEY(world_id) REFERENCES world (id),
	FOREIGN KEY(system_id) REFERENCES skill_system (id) ON DELETE RESTRICT
);
CREATE INDEX idx_skill_definition_system ON skill_definition (system_id);
CREATE INDEX idx_skill_definition_world ON skill_definition (world_id);
CREATE UNIQUE INDEX idx_skill_definition_world_name ON skill_definition (world_id, name);

CREATE TABLE quest_offer_term (
	id VARCHAR NOT NULL,
	world_id VARCHAR NOT NULL,
	offer_id VARCHAR NOT NULL,
	term_order INTEGER NOT NULL,
	direction VARCHAR NOT NULL,
	currency VARCHAR NOT NULL,
	counterparty_entity_id VARCHAR,
	item_id VARCHAR,
	fact_id VARCHAR,
	skill_key VARCHAR,
	amount INTEGER,
	level VARCHAR,
	PRIMARY KEY (id),
	CONSTRAINT ck_quest_offer_term_direction CHECK (direction IN ('cost','reward')),
	CONSTRAINT ck_quest_offer_term_currency CHECK (currency IN ('money','item','relation','fact','skill')),
	CONSTRAINT ck_quest_offer_term_shape CHECK ((currency NOT IN ('money','item','relation') OR (amount IS NOT NULL AND amount >= 1)) AND (currency <> 'item' OR item_id IS NOT NULL) AND (currency <> 'fact' OR fact_id IS NOT NULL) AND (currency <> 'skill' OR skill_key IS NOT NULL)),
	FOREIGN KEY(world_id) REFERENCES world (id),
	FOREIGN KEY(offer_id) REFERENCES quest_offer (id),
	FOREIGN KEY(counterparty_entity_id) REFERENCES entity (id),
	FOREIGN KEY(item_id) REFERENCES item (id),
	FOREIGN KEY(fact_id) REFERENCES fact (id)
);
CREATE INDEX idx_quest_offer_term_offer ON quest_offer_term (offer_id);

CREATE TABLE quest_term (
	id VARCHAR NOT NULL,
	world_id VARCHAR NOT NULL,
	quest_id VARCHAR NOT NULL,
	term_order INTEGER NOT NULL,
	direction VARCHAR NOT NULL,
	currency VARCHAR NOT NULL,
	counterparty_entity_id VARCHAR,
	item_id VARCHAR,
	fact_id VARCHAR,
	skill_key VARCHAR,
	amount INTEGER,
	level VARCHAR,
	PRIMARY KEY (id),
	CONSTRAINT ck_quest_term_direction CHECK (direction IN ('cost','reward')),
	CONSTRAINT ck_quest_term_currency CHECK (currency IN ('money','item','relation','fact','skill')),
	CONSTRAINT ck_quest_term_shape CHECK ((currency NOT IN ('money','item','relation') OR (amount IS NOT NULL AND amount >= 1)) AND (currency <> 'item' OR item_id IS NOT NULL) AND (currency <> 'fact' OR fact_id IS NOT NULL) AND (currency <> 'skill' OR skill_key IS NOT NULL)),
	FOREIGN KEY(world_id) REFERENCES world (id),
	FOREIGN KEY(quest_id) REFERENCES quest (id),
	FOREIGN KEY(counterparty_entity_id) REFERENCES entity (id),
	FOREIGN KEY(item_id) REFERENCES item (id),
	FOREIGN KEY(fact_id) REFERENCES fact (id)
);
CREATE INDEX idx_quest_term_quest ON quest_term (quest_id);

CREATE TABLE quest_request (
	id VARCHAR NOT NULL,
	world_id VARCHAR NOT NULL,
	character_id VARCHAR NOT NULL,
	pass_play_id VARCHAR NOT NULL,
	agenda_step_id VARCHAR NOT NULL,
	"trigger" VARCHAR NOT NULL,
	declaration VARCHAR NOT NULL,
	subject VARCHAR,
	status VARCHAR DEFAULT 'new' NOT NULL,
	existence_answer VARCHAR,
	creator_text VARCHAR,
	existing_entity_id VARCHAR,
	lore_entry_id VARCHAR,
	mutation_id VARCHAR,
	offer_id VARCHAR,
	note VARCHAR,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	change_history JSON DEFAULT '[]' NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_quest_request_trigger CHECK (trigger IN ('route','blocked','dropped')),
	CONSTRAINT ck_quest_request_status CHECK (status IN ('new','asking','writing_lore','proposed','covered','dropped')),
	CONSTRAINT ck_quest_request_answer CHECK (existence_answer IS NULL OR existence_answer IN ('exists','absent','already')),
	FOREIGN KEY(world_id) REFERENCES world (id),
	FOREIGN KEY(character_id) REFERENCES entity (id),
	FOREIGN KEY(pass_play_id) REFERENCES pass_play (id),
	FOREIGN KEY(agenda_step_id) REFERENCES agenda_step (id),
	FOREIGN KEY(existing_entity_id) REFERENCES entity (id),
	FOREIGN KEY(lore_entry_id) REFERENCES lore_entry (id),
	FOREIGN KEY(mutation_id) REFERENCES proposed_mutation (id),
	FOREIGN KEY(offer_id) REFERENCES quest_offer (id)
);
CREATE UNIQUE INDEX idx_quest_request_step ON quest_request (agenda_step_id);
CREATE INDEX idx_quest_request_world ON quest_request (world_id, created_at);
"""

# The parents every fixture row needs, inserted raw (TS2 and TS3).
PARENTS = (
    "INSERT INTO world (id, name) VALUES ('w', 'Monde')",
    "INSERT INTO entity (id, world_id, type, name) VALUES ('pc', 'w', 'character', 'Doer')",
    "INSERT INTO session (id, world_id, number) VALUES ('s', 'w', 1)",
    "INSERT INTO batch (id, session_id) VALUES ('b', 's')",
    "INSERT INTO pass_play (id, batch_id, session_id, character_id, declared_action) "
    "VALUES ('pp', 'b', 's', 'pc', 'agir')",
    "INSERT INTO agenda (id, world_id, owner_entity_id, title) VALUES ('ag', 'w', 'pc', 'Plan')",
    "INSERT INTO agenda_step (id, agenda_id, step_order, objective) VALUES ('st', 'ag', 1, 'o1')",
    "INSERT INTO agenda_step (id, agenda_id, step_order, objective) VALUES ('st2', 'ag', 2, 'o2')",
    "INSERT INTO quest_offer (id, world_id, giver_entity_id, title) VALUES ('of', 'w', 'pc', 'Offre')",
    "INSERT INTO quest (id, world_id, offer_id, character_id, agenda_id) VALUES ('q', 'w', 'of', 'pc', 'ag')",
)


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> str:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    return db_path


# --- TS1 -------------------------------------------------------------------------

def _checks_of(table) -> dict[str, str]:
    from sqlalchemy import CheckConstraint

    return {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}


def check_ts1() -> None:
    from sqlalchemy import Boolean

    from world_engine.models import QuestOfferTerm, QuestRequest, QuestTerm, SkillDefinition, SkillRank, SkillSystem
    from world_engine.models import quests
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION

    flag = SkillRank.__table__.c.get("trial_to_next")
    default = getattr(getattr(flag, "server_default", None), "arg", None)
    if flag is None or flag.nullable or not isinstance(flag.type, Boolean) or str(default) != "0":
        fail("TS1: skill_rank.trial_to_next is not a NOT NULL boolean with server default 0")
    for model in (SkillSystem, SkillDefinition):
        for name in TRIAL_COLUMNS:
            column = model.__table__.c.get(name)
            if column is None or not column.nullable or not isinstance(column.type, Boolean):
                fail(f"TS1: {model.__tablename__}.{name} is missing, NOT NULL or not a boolean")
    if quests.QUEST_TERM_CURRENCY_CHECK != CURRENCY_CHECK:
        fail(f"TS1: QUEST_TERM_CURRENCY_CHECK is {quests.QUEST_TERM_CURRENCY_CHECK!r}")
    if quests.QUEST_TERM_SHAPE_CHECK != SHAPE_CHECK:
        fail(f"TS1: QUEST_TERM_SHAPE_CHECK is {quests.QUEST_TERM_SHAPE_CHECK!r}")
    for model in (QuestOfferTerm, QuestTerm):
        found = _checks_of(model.__table__)
        name = model.__tablename__
        if found.get(f"ck_{name}_currency") != CURRENCY_CHECK or found.get(f"ck_{name}_shape") != SHAPE_CHECK:
            fail(f"TS1: {name}'s currency/shape CHECKs are not C-01's")
    table = QuestRequest.__table__
    if tuple(table.c.keys()) != REQUEST_COLUMNS:
        fail(f"TS1: quest_request columns are {tuple(table.c.keys())}")
    if not table.c.pass_play_id.nullable or not table.c.agenda_step_id.nullable:
        fail("TS1: quest_request.pass_play_id / agenda_step_id are NOT NULL")
    found = _checks_of(table)
    if set(found) != REQUEST_CHECKS:
        fail(f"TS1: quest_request CHECKs are {sorted(found)}")
    if found.get("ck_quest_request_origin") != ORIGIN_CHECK:
        fail(f"TS1: ck_quest_request_origin is {found.get('ck_quest_request_origin')!r}")
    if {i.name for i in table.indexes} != REQUEST_INDEXES:
        fail(f"TS1: quest_request indexes are {sorted(i.name for i in table.indexes)}")
    if [i.name for i in table.indexes if i.unique] != ["idx_quest_request_step"]:
        fail(f"TS1: unique indexes are {[i.name for i in table.indexes if i.unique]}")
    major, minor = EXPECTED_STATIC_SCHEMA_VERSION.lstrip("v").split(".")
    if (int(major), int(minor)) < (2, 29):
        fail(f"TS1: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}")
    if not MIGRATION.is_file():
        fail("TS1: scripts/migrate_v2_29_rank_trials.py is missing")
    elif not re.search(r'^_PREVIOUS_VERSION = "v2\.28"$', MIGRATION.read_text(encoding="utf-8"), re.M):
        fail('TS1: the migration\'s _PREVIOUS_VERSION is not "v2.28"')


# --- TS2 -------------------------------------------------------------------------

def _term(rid: str, direction: str = "reward", skill: str | None = "'agility'", amount: int = 2) -> str:
    skill_sql = skill if skill is not None else "NULL"
    return ("INSERT INTO quest_offer_term (id, world_id, offer_id, term_order, direction, currency, skill_key, "
            f"amount) VALUES ('{rid}', 'w', 'of', 0, '{direction}', 'rank', {skill_sql}, {amount})")


def _request(rid: str, trigger: str, *, pp: str = "NULL", step: str = "NULL", skill: str = "NULL",
             rank: str = "NULL") -> str:
    return ("INSERT INTO quest_request (id, world_id, character_id, pass_play_id, agenda_step_id, \"trigger\", "
            f"declaration, skill_key, target_rank) VALUES ('{rid}', 'w', 'pc', {pp}, {step}, '{trigger}', 'd', "
            f"{skill}, {rank})")


def check_ts2(engine) -> None:
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    with engine.begin() as conn:
        for sql in PARENTS:
            conn.execute(text(sql))

    def refused(sql: str) -> bool:
        with engine.connect() as conn:
            try:
                conn.execute(text(sql))
                conn.commit()
                return False
            except IntegrityError:
                conn.rollback()
                return True

    accepted = (("a rank reward", _term("t-ok")),
                ("a trial request", _request("r-ok", "trial", skill="'agility'", rank="3")),
                ("a route request with its day and step", _request("r-route", "route", pp="'pp'", step="'st'")))
    for label, sql in accepted:
        if refused(sql):
            fail(f"TS2: {label} was refused")
    rejected = (("a rank cost", _term("t1", direction="cost")),
                ("a rank of 6", _term("t2", amount=6)),
                ("a rank with no skill", _term("t3", skill=None)),
                ("a trial with a step", _request("r1", "trial", step="'st2'", skill="'agility'", rank="3")),
                ("a trial at rank 0", _request("r2", "trial", skill="'agility'", rank="0")),
                ("a route with no step", _request("r3", "route", pp="'pp'")),
                ("a route with a skill", _request("r4", "route", pp="'pp'", step="'st2'", skill="'agility'")))
    for label, sql in rejected:
        if not refused(sql):
            fail(f"TS2: {label} was accepted")


# --- TS3 -------------------------------------------------------------------------

def _build_v228(db_path: str) -> None:
    from sqlalchemy import create_engine
    from sqlmodel import SQLModel

    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)
    engine.dispose()
    with sqlite3.connect(db_path) as conn:
        for table in SIX:
            conn.execute(f"DROP TABLE {table}")
        conn.executescript(V228_DDL)
        for sql in PARENTS:
            conn.execute(sql)
        conn.executescript("""
            INSERT INTO skill_rank (id, world_id, rank, label, points_to_next) VALUES ('sr', 'w', 2, 'Adepte', 5);
            INSERT INTO skill_system (id, world_id, name) VALUES ('sy', 'w', 'Magie');
            INSERT INTO skill_definition (id, world_id, name, base_domain, system_id)
                VALUES ('sd', 'w', 'Escrime', 'agility', 'sy');
            INSERT INTO quest_offer_term (id, world_id, offer_id, term_order, direction, currency, amount)
                VALUES ('ot', 'w', 'of', 0, 'reward', 'money', 5);
            INSERT INTO quest_term (id, world_id, quest_id, term_order, direction, currency, amount)
                VALUES ('qt', 'w', 'q', 0, 'reward', 'money', 3);
            INSERT INTO quest_request (id, world_id, character_id, pass_play_id, agenda_step_id, "trigger",
                declaration, change_history) VALUES ('rq', 'w', 'pc', 'missing-pp', 'st', 'route', 'd', '[{"x": 1}]');
        """)


def _set_version(db_path: str, version: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM schema_meta")
        conn.execute("INSERT INTO schema_meta (id, static_version) VALUES (1, ?)", (version,))


def _snapshot(db_path: str, columns: dict[str, list[str]] | None = None) -> dict:
    with sqlite3.connect(db_path) as conn:
        info = {t: [r[1:] for r in conn.execute(f"PRAGMA table_info({t})")] for t in SIX}
        names = columns or {t: [c[0] for c in info[t]] for t in SIX}
        rows = {t: sorted(conn.execute(f'SELECT {", ".join(chr(34) + c + chr(34) for c in names[t])} FROM {t}'))
                for t in SIX}
        version = conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()
        sql = {t: conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone()[0]
               for t in SIX}
        indexes = {t: {r[1]: r[2] for r in conn.execute(f"PRAGMA index_list({t})")} for t in SIX}
        flags = conn.execute("SELECT trial_to_next FROM skill_rank").fetchall() if any(
            c[0] == "trial_to_next" for c in info["skill_rank"]) else None
    return {"info": info, "names": names, "rows": rows, "version": version and version[0], "sql": sql,
            "indexes": indexes, "flags": flags}


def _run_migration(db_path: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test",
               PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True,
                          text=True, encoding="utf-8", cwd=str(ROOT), timeout=60)


def check_ts3() -> None:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "v228.db")
    _build_v228(db_path)
    _set_version(db_path, "v2.27")
    before = _snapshot(db_path)
    if sum(len(r) for r in before["rows"].values()) != 6:
        fail(f"TS3: the fixture holds {before['rows']}, want one row per table")
    result = _run_migration(db_path)
    if result.returncode == 0 or _snapshot(db_path)["info"] != before["info"]:
        fail(f"TS3a: at v2.27 exit {result.returncode}, or the tables changed")
    _set_version(db_path, "v2.28")
    result = _run_migration(db_path)
    after = _snapshot(db_path, before["names"])
    if result.returncode != 0:
        fail(f"TS3b: exit {result.returncode}: {(result.stdout + result.stderr).strip()[-600:]}")
        return
    for table, columns in ADDED.items():
        missing = [c for c in columns if c not in {i[0] for i in after["info"][table]}]
        if missing:
            fail(f"TS3b: {table} lacks {missing}")
    if after["rows"] != before["rows"]:
        fail(f"TS3b: rows {before['rows']} became {after['rows']}")
    if after["flags"] != [(0,)]:
        fail(f"TS3b: skill_rank.trial_to_next is {after['flags']}")
    for table, names in REBUILT_CHECKS.items():
        absent = [n for n in names if f"CONSTRAINT {n} " not in after["sql"][table]]
        if absent or "'rank'" not in after["sql"]["quest_term"]:
            fail(f"TS3b: {table} lacks CHECK(s) {absent} or the rank currency")
    for table, expected in REBUILT_INDEXES.items():
        if {n: after["indexes"][table].get(n) for n in expected} != expected:
            fail(f"TS3b: {table} indexes are {after['indexes'][table]}")
    if not re.search(r"Note: quest_request rowid \d+ points to a missing pass_play row", result.stdout):
        fail(f"TS3b: the dangling quest_request row was not listed: {result.stdout.strip()[-400:]}")
    if after["version"] != "v2.29":
        fail(f"TS3b: schema_meta is {after['version']!r}")
    result = _run_migration(db_path)
    again = _snapshot(db_path, before["names"])
    if result.returncode != 0 or "DDL already applied." not in result.stdout or again["rows"] != after["rows"]:
        fail(f"TS3c: second run exit {result.returncode}, or it applied DDL or changed a row")


def main() -> None:
    _fresh_db()
    from sqlmodel import SQLModel

    from world_engine import models  # noqa: F401 -- registers every table
    from world_engine.db import engine

    SQLModel.metadata.create_all(engine)
    check_ts1()
    check_ts2(engine)
    check_ts3()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: rank_trial_schema -- v2.29 lets a rank ask a trial, admits a rank reward in both term tables, "
          "a trial request with no day, and migrates from v2.28 only, keeping every row")


if __name__ == "__main__":
    main()
