"""G1 check for TICKET-0126 (BRIEF-0126-B) -- schema v2.32: the creation rules, the overrides, the draft tables and the creation journal kind.

CS1 -- static. By AST: `models/canon_skill.py` declares the classes
   `SkillSystem`, `SkillDefinition`, `Skill`, `CreationRules` and assigns
   `BASE_SKILL_DOMAINS`, `RANK_POINTS_CHECK`; `models/canon.py` declares none
   of them. By import: `CreationRules`' columns, their nullability and server
   defaults, its CHECK `ck_creation_rules_values` and unique index
   `idx_creation_rules_world` are C-02's; the four `skill_system` and two
   `skill_definition` override columns exist and are nullable; each draft
   table's columns, CHECK names and index names (with uniqueness) are
   C-02's, `idx_pc_draft_open` carrying `WHERE status <> 'approved'`; none
   of the six new tables has a JSON column; `LORE_USAGE_STEPS["creation"]
   == ("creation_subject", "creation_design")`; the two `PAYLOAD_KEYS`
   entries hold exactly C-02's keys; `EXPECTED_STATIC_SCHEMA_VERSION ==
   "v2.32"`; `scripts/migrate_v2_32_character_creation.py` exists and its
   `_PREVIOUS_VERSION` is `"v2.31"`.
CS2 -- CHECKs (fresh `create_all`, raw INSERTs, parents raw). A
   `creation_rules` row given only `id, world_id` reads back every default;
   `pool = -1`, `cost_to_rank_3 = -1`, `max_rank = 0`, `cap_at_rank_2 = -1`
   and a second row for the same world are each refused; a `pc_draft` of
   status `x` is refused; two `draft` rows for one (world, user) are refused,
   an `approved` plus a `draft` are admitted; a `pc_draft_skill` with both
   ranks NULL, or `player_rank = 6`, is refused; a `master` sketch without
   `skill_key`, or a `family` sketch with one, is refused; a knowledge line
   at level `unaware` is refused; `write_usage_event` writes kind
   `creation`, step `creation_design` with C-02's keys and outcome `ok`; a
   raw INSERT of kind `creation`, step `ask` is refused. Each refusal is
   paired with an admitted row of the same table, so no refusal is vacuous.
CS3 -- migration. The fixture drops the six new tables and recreates
   `skill_system`, `skill_definition` and `lore_usage_event` from the literal
   `V231_DDL` (compiled from the models at `fb8557a`), with one system, one
   definition and one journal row inserted raw, then
   `scripts/migrate_v2_32_character_creation.py` runs as a subprocess:
   (a) at `schema_meta` v2.30 it exits non-zero and nothing changes;
   (b) at v2.31 it exits zero: the six tables and the six columns exist, the
       stored journal SQL holds `'creation_design'`, the three rows are kept
       with their ids and values, `schema_meta` reads v2.32;
   (c) a second run exits zero and changes nothing;
   (d) (AMENDMENT-0126-01) at v2.32, `pc_draft` recreated from the literal
       `PC_DRAFT_BACKSTORY_DDL` (C-02's table at `a4cda95`, column
       `backstory`) with one row: the script exits zero, the column is
       `story` and `backstory` is gone, the row keeps its id and text; a
       second run changes nothing.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collected nothing, or a
sub-rule not reached, is a FAILURE.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sqlite3
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
MODELS = SRC / "world_engine" / "models"
MIGRATION = SCRIPTS / "migrate_v2_32_character_creation.py"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


SKILL_NAMES = {"SkillSystem", "SkillDefinition", "Skill", "CreationRules"}
SKILL_ASSIGNS = {"BASE_SKILL_DOMAINS", "RANK_POINTS_CHECK"}

# column -> (nullable, server default text or None), C-02.
CREATION_RULES_COLUMNS: dict[str, tuple[bool, str | None]] = {
    "id": (False, None), "world_id": (False, None), "pool": (False, "6"),
    "cost_to_rank_1": (False, "1"), "cost_to_rank_2": (False, "1"), "cost_to_rank_3": (False, "2"),
    "cost_to_rank_4": (False, "3"), "cost_to_rank_5": (False, "4"),
    "cap_at_rank_0": (True, "2"), "cap_at_rank_2": (True, None), "cap_at_rank_3": (True, None),
    "cap_at_rank_4": (True, None), "cap_at_rank_5": (True, None),
    "max_rank": (False, "5"), "max_master_skills": (False, "1"), "skills_visible": (False, "1"),
    "updated_at": (False, "now()"),  # _created_ts(): func.now(), CURRENT_TIMESTAMP on SQLite
}
OVERRIDE_COLUMNS = {
    "skill_system": ("visible_at_creation", "max_rank_at_creation", "cap_raised_at_creation",
                     "cap_held_at_creation"),
    "skill_definition": ("visible_at_creation", "max_rank_at_creation"),
}
# table -> (columns, CHECK names, {index name: unique})
DRAFT_TABLES: dict[str, tuple[set[str], set[str], dict[str, bool]]] = {
    "pc_draft": (
        {"id", "world_id", "user_id", "status", "name", "story", "start_location_id",
         "start_location_set_by", "creator_note", "submitted_at", "created_at", "updated_at"},
        {"ck_pc_draft_status", "ck_pc_draft_set_by"},
        {"idx_pc_draft_world": False, "idx_pc_draft_open": True},
    ),
    "pc_draft_skill": (
        {"id", "draft_id", "world_id", "skill_key", "player_rank", "designer_rank",
         "justification", "designer_reason"},
        {"ck_pc_draft_skill_ranks", "ck_pc_draft_skill_some"},
        {"idx_pc_draft_skill_key": True},
    ),
    "pc_draft_sketch": (
        {"id", "draft_id", "world_id", "position", "name", "role", "sentence", "group_label",
         "kind", "skill_key", "existing_entity_id", "origin"},
        {"ck_pc_draft_sketch_kind", "ck_pc_draft_sketch_master", "ck_pc_draft_sketch_origin"},
        {"idx_pc_draft_sketch_draft": False},
    ),
    "pc_draft_membership": (
        {"id", "draft_id", "world_id", "faction_id", "role", "origin"},
        {"ck_pc_draft_membership_origin"},
        {"idx_pc_draft_membership_faction": True},
    ),
    "pc_draft_knowledge": (
        {"id", "draft_id", "world_id", "position", "level", "content", "origin"},
        {"ck_pc_draft_knowledge_level", "ck_pc_draft_knowledge_origin"},
        {"idx_pc_draft_knowledge_draft": False},
    ),
}
NEW_TABLES = ("creation_rules", *DRAFT_TABLES)
C02_KEYS = {
    "creation_subject": {"draft_id", "asked_by", "story", "names", "keywords", "error"},
    "creation_design": {"draft_id", "asked_by", "lore", "proposal", "violations", "notes", "error"},
}

V231_DDL = """
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
    trial_to_rank_1 BOOLEAN,
    trial_to_rank_2 BOOLEAN,
    trial_to_rank_3 BOOLEAN,
    trial_to_rank_4 BOOLEAN,
    trial_to_rank_5 BOOLEAN,
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
    trial_to_rank_1 BOOLEAN,
    trial_to_rank_2 BOOLEAN,
    trial_to_rank_3 BOOLEAN,
    trial_to_rank_4 BOOLEAN,
    trial_to_rank_5 BOOLEAN,
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
CREATE TABLE lore_usage_event (
    id VARCHAR NOT NULL,
    attempt_id VARCHAR NOT NULL,
    world_ref VARCHAR NOT NULL,
    world_name VARCHAR NOT NULL,
    kind VARCHAR NOT NULL,
    step VARCHAR NOT NULL,
    outcome VARCHAR NOT NULL,
    payload JSON NOT NULL,
    model_calls JSON DEFAULT '[]' NOT NULL,
    lore_entry_ref VARCHAR,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_lore_usage_event_step CHECK ((kind = 'write' AND step IN ('questions','draft','commit')) OR (kind = 'consult' AND step IN ('ask','resolve')) OR (kind = 'perspective' AND step IN ('perspective_ask','perspective_resolve'))),
    CONSTRAINT ck_lore_usage_event_outcome CHECK (outcome IN ('ok','unavailable','parse_error','refused')),
    CONSTRAINT ck_lore_usage_event_entry CHECK ((lore_entry_ref IS NOT NULL) = (step = 'commit' AND outcome = 'ok'))
);
CREATE INDEX idx_lore_usage_event_attempt ON lore_usage_event (attempt_id, created_at);
CREATE INDEX idx_lore_usage_event_world ON lore_usage_event (world_ref, created_at);
"""


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
    return engine, pathlib.Path(tmp_dir) / "check.db"


def _top_level(path: pathlib.Path) -> tuple[set[str], set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    classes = {n.name for n in tree.body if isinstance(n, ast.ClassDef)}
    assigns = set()
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else (
            [node.target] if isinstance(node, ast.AnnAssign) else [])
        assigns |= {t.id for t in targets if isinstance(t, ast.Name)}
    return classes, assigns


def _default(column) -> str | None:
    default = column.server_default
    if default is None:
        return None
    return str(getattr(default, "arg", default))


def _cs1_layout() -> int:
    collected = 0
    classes, assigns = _top_level(MODELS / "canon_skill.py")
    for name in sorted(SKILL_NAMES - classes):
        fail(f"CS1 canon_skill.py does not declare class {name}")
    for name in sorted(SKILL_ASSIGNS - assigns):
        fail(f"CS1 canon_skill.py does not assign {name}")
    collected += len(classes & SKILL_NAMES) + len(assigns & SKILL_ASSIGNS)
    classes, assigns = _top_level(MODELS / "canon.py")
    for name in sorted((classes & SKILL_NAMES) | (assigns & SKILL_ASSIGNS)):
        fail(f"CS1 canon.py still declares {name}")
    return collected


def _cs1_creation_rules() -> int:
    from world_engine.models import CreationRules

    table = CreationRules.__table__
    got = {c.name: (c.nullable, _default(c)) for c in table.columns}
    if got != CREATION_RULES_COLUMNS:
        for name in sorted(set(got) | set(CREATION_RULES_COLUMNS)):
            if got.get(name) != CREATION_RULES_COLUMNS.get(name):
                fail(f"CS1 creation_rules.{name} is {got.get(name)!r}, "
                     f"expected {CREATION_RULES_COLUMNS.get(name)!r}")
    checks = {c.name for c in table.constraints if c.name and c.name.startswith("ck_")}
    if checks != {"ck_creation_rules_values"}:
        fail(f"CS1 creation_rules CHECKs are {sorted(checks)}")
    indexes = {i.name: i.unique for i in table.indexes}
    if indexes != {"idx_creation_rules_world": True}:
        fail(f"CS1 creation_rules indexes are {indexes}")
    return len(got)


def _cs1_overrides() -> int:
    from sqlmodel import SQLModel

    collected = 0
    for table_name, columns in OVERRIDE_COLUMNS.items():
        table = SQLModel.metadata.tables[table_name]
        for name in columns:
            column = table.columns.get(name)
            if column is None:
                fail(f"CS1 {table_name}.{name} is missing")
            elif not column.nullable or column.server_default is not None:
                fail(f"CS1 {table_name}.{name} must be nullable with no default")
            else:
                collected += 1
    return collected


def _cs1_drafts() -> int:
    from sqlalchemy import JSON
    from sqlmodel import SQLModel

    collected = 0
    for table_name, (columns, checks, indexes) in DRAFT_TABLES.items():
        table = SQLModel.metadata.tables.get(table_name)
        if table is None:
            fail(f"CS1 table {table_name} is missing")
            continue
        got_columns = {c.name for c in table.columns}
        if got_columns != columns:
            fail(f"CS1 {table_name} columns differ: extra {sorted(got_columns - columns)}, "
                 f"missing {sorted(columns - got_columns)}")
        got_checks = {c.name for c in table.constraints if c.name and c.name.startswith("ck_")}
        if got_checks != checks:
            fail(f"CS1 {table_name} CHECKs are {sorted(got_checks)}, expected {sorted(checks)}")
        got_indexes = {i.name: i.unique for i in table.indexes}
        if got_indexes != indexes:
            fail(f"CS1 {table_name} indexes are {got_indexes}, expected {indexes}")
        collected += len(got_columns)
    open_index = next((i for i in SQLModel.metadata.tables["pc_draft"].indexes
                       if i.name == "idx_pc_draft_open"), None)
    where = open_index.dialect_options["sqlite"]["where"] if open_index is not None else None
    if where is None or str(where) != "status <> 'approved'":
        fail(f"CS1 idx_pc_draft_open's WHERE is {where!s}, expected status <> 'approved'")
    for table_name in NEW_TABLES:
        table = SQLModel.metadata.tables.get(table_name)
        for column in table.columns if table is not None else ():
            if isinstance(column.type, JSON):
                fail(f"CS1 {table_name}.{column.name} is a JSON column (INV-20)")
    return collected


def _cs1_journal_and_version() -> int:
    from world_engine.models.pipeline import LORE_USAGE_STEPS
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
    from world_engine.writes.lore_usage import PAYLOAD_KEYS

    if LORE_USAGE_STEPS.get("creation") != ("creation_subject", "creation_design"):
        fail(f"CS1 LORE_USAGE_STEPS['creation'] is {LORE_USAGE_STEPS.get('creation')!r}")
    for step, keys in C02_KEYS.items():
        got = PAYLOAD_KEYS.get(step)
        if got is None or set(got) != keys:
            fail(f"CS1 PAYLOAD_KEYS[{step!r}] is {sorted(got) if got else got!r}, expected {sorted(keys)}")
    if EXPECTED_STATIC_SCHEMA_VERSION != "v2.32":
        fail(f"CS1 EXPECTED_STATIC_SCHEMA_VERSION is {EXPECTED_STATIC_SCHEMA_VERSION!r}")
    if not MIGRATION.exists():
        fail(f"CS1 {MIGRATION.name} is missing")
        return 0
    previous = None
    for node in ast.parse(MIGRATION.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "_PREVIOUS_VERSION" for t in node.targets):
            previous = getattr(node.value, "value", None)
    if previous != "v2.31":
        fail(f"CS1 the migration's _PREVIOUS_VERSION is {previous!r}, expected 'v2.31'")
    return 1


def rule_cs1() -> None:
    collected = (_cs1_layout() + _cs1_creation_rules() + _cs1_overrides() + _cs1_drafts()
                 + _cs1_journal_and_version())
    if collected == 0:
        fail("CS1 collected nothing")


def _raises(engine, sql: str, params: dict | None = None) -> bool:
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    try:
        with engine.begin() as conn:
            conn.execute(text(sql), params or {})
    except IntegrityError:
        return True
    return False


def _refused(engine, label: str, sql: str, params: dict | None = None) -> int:
    if not _raises(engine, sql, params):
        fail(f"CS2 {label} was admitted")
    return 1


def _admitted(engine, label: str, sql: str, params: dict | None = None) -> int:
    if _raises(engine, sql, params):
        fail(f"CS2 {label} was refused")
    return 1


def rule_cs2(engine) -> int:
    from sqlalchemy import text
    from sqlmodel import Session

    from world_engine.writes.lore_usage import write_usage_event

    with engine.begin() as conn:
        for world in ("w1", "w2"):
            conn.execute(text("INSERT INTO world (id, name, is_active) VALUES (:w, :w, 0)"), {"w": world})
        for user in ("u1", "u2"):
            conn.execute(text("INSERT INTO user (id, name, role) VALUES (:u, :u, 'player')"), {"u": user})
    counted = 0
    rules = "INSERT INTO creation_rules (id, world_id{c}) VALUES (:id, :w{v})"
    counted += _admitted(engine, "a creation_rules row with only id and world_id",
                         rules.format(c="", v=""), {"id": "cr1", "w": "w1"})
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT pool, cost_to_rank_1, cost_to_rank_2, cost_to_rank_3, cost_to_rank_4, "
            "cost_to_rank_5, cap_at_rank_0, cap_at_rank_2, cap_at_rank_3, cap_at_rank_4, "
            "cap_at_rank_5, max_rank, max_master_skills, skills_visible FROM creation_rules "
            "WHERE id = 'cr1'")).first()
    expected = (6, 1, 1, 2, 3, 4, 2, None, None, None, None, 5, 1, 1)
    if row is None or tuple(row) != expected:
        fail(f"CS2 creation_rules defaults read {tuple(row) if row else row!r}, expected {expected}")
    for column, value in (("pool", -1), ("cost_to_rank_3", -1), ("max_rank", 0), ("cap_at_rank_2", -1)):
        counted += _refused(engine, f"creation_rules {column} = {value}",
                            rules.format(c=f", {column}", v=", :x"), {"id": f"cr-{column}", "w": "w2", "x": value})
    counted += _refused(engine, "a second creation_rules row for one world",
                        rules.format(c="", v=""), {"id": "cr2", "w": "w1"})

    draft = "INSERT INTO pc_draft (id, world_id, user_id, status) VALUES (:id, :w, :u, :s)"
    counted += _refused(engine, "a pc_draft of status x", draft, {"id": "dx", "w": "w1", "u": "u1", "s": "x"})
    counted += _admitted(engine, "a first open pc_draft", draft, {"id": "d1", "w": "w1", "u": "u1", "s": "draft"})
    counted += _refused(engine, "a second open pc_draft for one (world, user)", draft,
                        {"id": "d2", "w": "w1", "u": "u1", "s": "draft"})
    counted += _admitted(engine, "an approved pc_draft", draft, {"id": "d3", "w": "w1", "u": "u2", "s": "approved"})
    counted += _admitted(engine, "a draft beside an approved one", draft,
                         {"id": "d4", "w": "w1", "u": "u2", "s": "draft"})

    skill = ("INSERT INTO pc_draft_skill (id, draft_id, world_id, skill_key, player_rank, designer_rank) "
             "VALUES (:id, 'd1', 'w1', :k, :p, :d)")
    counted += _admitted(engine, "a pc_draft_skill at player_rank 2", skill, {"id": "s1", "k": "agility", "p": 2, "d": None})
    counted += _refused(engine, "a pc_draft_skill with both ranks NULL", skill,
                        {"id": "s2", "k": "physical", "p": None, "d": None})
    counted += _refused(engine, "a pc_draft_skill at player_rank 6", skill, {"id": "s3", "k": "perception", "p": 6, "d": None})

    sketch = ("INSERT INTO pc_draft_sketch (id, draft_id, world_id, position, name, kind, skill_key, origin) "
              "VALUES (:id, 'd1', 'w1', 0, 'N', :kind, :k, 'player')")
    counted += _admitted(engine, "a master sketch with its skill", sketch, {"id": "k1", "kind": "master", "k": "agility"})
    counted += _admitted(engine, "a family sketch", sketch, {"id": "k2", "kind": "family", "k": None})
    counted += _refused(engine, "a master sketch without skill_key", sketch, {"id": "k3", "kind": "master", "k": None})
    counted += _refused(engine, "a family sketch with a skill_key", sketch, {"id": "k4", "kind": "family", "k": "agility"})

    knowledge = ("INSERT INTO pc_draft_knowledge (id, draft_id, world_id, position, level, content, origin) "
                 "VALUES (:id, 'd1', 'w1', 0, :level, 'c', 'player')")
    counted += _admitted(engine, "a knowledge line at rumor", knowledge, {"id": "n1", "level": "rumor"})
    counted += _refused(engine, "a knowledge line at unaware", knowledge, {"id": "n2", "level": "unaware"})

    with Session(engine) as db:
        payload = {key: None for key in C02_KEYS["creation_design"]}
        payload.update(draft_id="d1", asked_by="player:u1", violations=[], notes=[])
        event = write_usage_event(db, attempt_id="attempt-1", world_ref="w1", world_name="W",
                                  kind="creation", step="creation_design", outcome="ok",
                                  payload=payload, model_calls=[])
        db.commit()
        event_id = event.id
    with engine.connect() as conn:
        back = conn.execute(text("SELECT kind, step FROM lore_usage_event WHERE id = :i"), {"i": event_id}).first()
    if back is None or tuple(back) != ("creation", "creation_design"):
        fail(f"CS2 the creation journal row reads back {back!r}")
    counted += 1
    counted += _refused(engine, "a raw journal row of kind creation, step ask",
                        "INSERT INTO lore_usage_event (id, attempt_id, world_ref, world_name, kind, step, "
                        "outcome, payload) VALUES ('raw-x', 'a', 'w', 'W', 'creation', 'ask', 'ok', '{}')")
    return counted


SYSTEM_ROW = ("sys-1", "w1", "Magie", "d", None, None, None, None, None, 1, None, None, None, None,
              "2026-01-01 00:00:00", "2026-01-01 00:00:00")
DEFINITION_ROW = ("def-1", "w1", "Feu", "composure", "sys-1", None, None, None, None, None, None,
                  None, None, None, None, None, 1, "2026-01-01 00:00:00", "2026-01-01 00:00:00")
JOURNAL_ROW = ("raw-1", "attempt-1", "w1", "Monde", "consult", "ask", "ok",
               '{"question": "q", "response": "r", "error": null}', "[]", None, "2026-01-01 00:00:00")
_ROW_SELECTS = {
    "skill_system": "SELECT id, world_id, name, description, points_to_rank_1, points_to_rank_2, "
                    "points_to_rank_3, points_to_rank_4, points_to_rank_5, trial_to_rank_1, trial_to_rank_2, "
                    "trial_to_rank_3, trial_to_rank_4, trial_to_rank_5, created_at, updated_at FROM skill_system",
    "skill_definition": "SELECT id, world_id, name, base_domain, system_id, description, points_to_rank_1, "
                        "points_to_rank_2, points_to_rank_3, points_to_rank_4, points_to_rank_5, "
                        "trial_to_rank_1, trial_to_rank_2, trial_to_rank_3, trial_to_rank_4, "
                        "trial_to_rank_5, requires_master, created_at, updated_at FROM skill_definition",
    "lore_usage_event": "SELECT id, attempt_id, world_ref, world_name, kind, step, outcome, payload, "
                        "model_calls, lore_entry_ref, created_at FROM lore_usage_event",
}
_EXPECTED_ROWS = {"skill_system": [SYSTEM_ROW], "skill_definition": [DEFINITION_ROW],
                  "lore_usage_event": [JOURNAL_ROW]}

# C-02's pc_draft at a4cda95, before AMENDMENT-0126-01 renamed `backstory` to `story`.
PC_DRAFT_BACKSTORY_DDL = """
CREATE TABLE pc_draft (
    id VARCHAR NOT NULL,
    world_id VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'draft' NOT NULL,
    name VARCHAR DEFAULT '' NOT NULL,
    backstory VARCHAR DEFAULT '' NOT NULL,
    start_location_id VARCHAR,
    start_location_set_by VARCHAR,
    creator_note VARCHAR,
    submitted_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_pc_draft_status CHECK (status IN ('draft','submitted','returned','approved')),
    CONSTRAINT ck_pc_draft_set_by CHECK (start_location_set_by IS NULL OR start_location_set_by IN ('player','designer')),
    FOREIGN KEY(world_id) REFERENCES world (id),
    FOREIGN KEY(user_id) REFERENCES user (id),
    FOREIGN KEY(start_location_id) REFERENCES entity (id)
);
CREATE UNIQUE INDEX idx_pc_draft_open ON pc_draft (world_id, user_id) WHERE status <> 'approved';
CREATE INDEX idx_pc_draft_world ON pc_draft (world_id);
"""
DRAFT_ROW = ("draft-cs3d", "world-cs3d", "user-cs3d", "Une histoire Ã©crite avant l'amendement.")


def _reshape_to_v2_31(db_path: pathlib.Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        for table in reversed(NEW_TABLES):
            conn.execute(f"DROP TABLE {table}")
        for table in ("skill_definition", "skill_system", "lore_usage_event"):
            conn.execute(f"DROP TABLE {table}")
        conn.executescript(V231_DDL)
        conn.execute(f"INSERT INTO skill_system VALUES ({', '.join('?' * len(SYSTEM_ROW))})", SYSTEM_ROW)
        conn.execute(f"INSERT INTO skill_definition VALUES ({', '.join('?' * len(DEFINITION_ROW))})",
                     DEFINITION_ROW)
        conn.execute(f"INSERT INTO lore_usage_event VALUES ({', '.join('?' * len(JOURNAL_ROW))})", JOURNAL_ROW)
        conn.execute("INSERT INTO schema_meta (id, static_version) VALUES (1, 'v2.31')")
        conn.commit()
    finally:
        conn.close()


def _snapshot(db_path: pathlib.Path) -> tuple:
    conn = sqlite3.connect(db_path)
    try:
        master = tuple(conn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY type, name"))
        rows = tuple(tuple(conn.execute(f"SELECT * FROM {t} ORDER BY id")) for t in _ROW_SELECTS)
        meta = conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()
    finally:
        conn.close()
    return master, rows, meta


def _set_version(db_path: pathlib.Path, version: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("UPDATE schema_meta SET static_version = ? WHERE id = 1", (version,))
        conn.commit()
    finally:
        conn.close()


def _run_migration() -> int:
    proc = subprocess.run([sys.executable, str(MIGRATION)], env=dict(os.environ),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode


def rule_cs3(engine, db_path: pathlib.Path) -> int:
    reached = 0
    if not MIGRATION.exists():
        fail(f"CS3 {MIGRATION.name} missing")
        return reached
    engine.dispose()
    _reshape_to_v2_31(db_path)

    # (a) below v2.31: refused, nothing changes.
    _set_version(db_path, "v2.30")
    before = _snapshot(db_path)
    if _run_migration() == 0:
        fail("CS3a the migration exited zero at v2.30")
    if _snapshot(db_path) != before:
        fail("CS3a the refused migration changed the database")
    reached += 1

    # (b) at v2.31: applied, rows kept.
    _set_version(db_path, "v2.31")
    if _run_migration() != 0:
        fail("CS3b the migration exited non-zero at v2.31")
    conn = sqlite3.connect(db_path)
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in NEW_TABLES:
            if table not in tables:
                fail(f"CS3b table {table} is missing after the migration")
        for table, columns in OVERRIDE_COLUMNS.items():
            present = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
            for column in columns:
                if column not in present:
                    fail(f"CS3b {table}.{column} is missing after the migration")
        journal_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='lore_usage_event'").fetchone()
        if journal_sql is None or "'creation_design'" not in journal_sql[0]:
            fail("CS3b the stored lore_usage_event SQL lacks 'creation_design'")
        for table, select in _ROW_SELECTS.items():
            rows = [tuple(r) for r in conn.execute(select)]
            if rows != _EXPECTED_ROWS[table]:
                fail(f"CS3b {table} rows are {rows!r}, expected {_EXPECTED_ROWS[table]!r}")
        meta = conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()
        if meta is None or meta[0] != "v2.32":
            fail(f"CS3b schema_meta reads {meta!r}, expected 'v2.32'")
    finally:
        conn.close()
    reached += 1

    # (c) a second run changes nothing.
    before = _snapshot(db_path)
    if _run_migration() != 0:
        fail("CS3c the second run exited non-zero")
    if _snapshot(db_path) != before:
        fail("CS3c the second run changed the database")
    reached += 1
    return reached + _cs3d(db_path)


def _draft_state(db_path: pathlib.Path) -> tuple[set[str], list[tuple]]:
    conn = sqlite3.connect(db_path)
    try:
        columns = {r[1] for r in conn.execute("PRAGMA table_info(pc_draft)")}
        text_column = "story" if "story" in columns else "backstory"
        rows = [tuple(r) for r in conn.execute(f"SELECT id, {text_column} FROM pc_draft ORDER BY id")]
    finally:
        conn.close()
    return columns, rows


def _cs3d(db_path: pathlib.Path) -> int:
    """(d) a database that ran v2.32 before AMENDMENT-0126-01: the column is renamed, the row kept."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DROP TABLE pc_draft")
        conn.executescript(PC_DRAFT_BACKSTORY_DDL)
        conn.execute("INSERT INTO pc_draft (id, world_id, user_id, backstory) VALUES (?, ?, ?, ?)", DRAFT_ROW)
        conn.commit()
    finally:
        conn.close()
    if _run_migration() != 0:
        fail("CS3d the migration exited non-zero on a pc_draft holding backstory")
    columns, rows = _draft_state(db_path)
    if "story" not in columns or "backstory" in columns:
        fail(f"CS3d pc_draft columns after the migration are {sorted(columns)}")
    if rows != [(DRAFT_ROW[0], DRAFT_ROW[3])]:
        fail(f"CS3d pc_draft rows are {rows!r}, expected the row with its id and text")
    before = _snapshot(db_path)
    if _run_migration() != 0:
        fail("CS3d the second run exited non-zero")
    if _snapshot(db_path) != before or _draft_state(db_path) != (columns, rows):
        fail("CS3d the second run changed the database")
    return 1


def main() -> int:
    engine, db_path = _fresh_engine()
    try:
        rule_cs1()
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"CS1 raised {type(exc).__name__}: {exc}")
    counted = 0
    try:
        counted = rule_cs2(engine)
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"CS2 raised {type(exc).__name__}: {exc}")
    if counted == 0:
        fail("CS2 collected nothing")
    reached = 0
    try:
        reached = rule_cs3(engine, db_path)
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"CS3 raised {type(exc).__name__}: {exc}")
    if reached != 4:
        fail(f"CS3 reached {reached} of its 4 sub-rules")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(f"PASS: creation_schema -- v2.32: creation rules, overrides and draft tables as C-02, "
          f"{counted} CHECK probes, the creation journal kind, migration idempotent and refusing "
          f"below v2.31")
    return 0


if __name__ == "__main__":
    sys.exit(main())
