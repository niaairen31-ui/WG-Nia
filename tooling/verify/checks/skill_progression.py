"""G1 check for TICKET-0106 -- a skill progresses from Inexpérimenté to Maître.

The lot adds its pieces brief by brief; this check grows with it (the
`fact_learning.py` precedent, TICKET-0105). Each brief adds its rules here in
the same commit.

A1 -- schema (BRIEF-0106-A, v2.15). `skill` declares `rank` (default
   `skill_ranks.DEFAULT_RANK`) and `xp` (default 0), the CHECKs
   `ck_skill_rank` (`rank BETWEEN 0 AND 5`) and `ck_skill_xp` (`xp >= 0`), and
   no `tier`; `skill_system` and `skill_definition` each declare the five
   nullable `points_to_rank_1..5` and a `ck_*_rank_points` CHECK;
   `skill_rank` declares exactly `id, world_id, rank, label, points_to_next,
   updated_at`, the CHECKs `ck_skill_rank_rank`, `ck_skill_rank_points` and
   the UNIQUE index `idx_skill_rank_world_rank (world_id, rank)`.
   `skill_ranks` carries six ranks, the modifiers (-1, 0, 1, 2, 2, 3), the
   labels Inexpérimenté .. Maître, the default points (5, 10, 20, 40, 80),
   and `TIER_TO_RANK` keeps every former tier's modifier.
A2 -- migration `scripts/migrate_v2_15_skill_ranks.py`, on a v2.14-shaped
   database (the three skill tables in their v2.14 DDL, verbatim below,
   `skill_rank` absent), holding a system, a definition attached to it, and
   four skill rows at tiers -1, 0, 1, 2:
   a. at v2.13 it refuses (non-zero exit) and changes nothing;
   b. at v2.14 it gives ranks 0, 1, 2, 3 and xp 0 to the four rows (ids,
      domains, definitions and histories kept), keeps the system and the
      definition, rebuilds the three tables with the models' shape and
      CHECKs, creates `skill_rank` empty, leaves `PRAGMA foreign_key_check`
      empty and moves `schema_meta` to the code's version;
   c. a second run exits zero and changes no row.
A3 -- the ladder and its readers (fixture). `world_ladder` of a world with
   no row is the engine default; a `skill_rank` row renames its rank and
   changes its points; `points_to_next` takes the definition's column, else
   its system's, else the ladder's (a system and a definition both setting
   rank 3: the definition wins), and is None at rank 5. `GET
   /api/skill-ranks` serves the six steps; `GET /api/skills` serves `rank`,
   `rank_label`, `xp`, `points_to_next`; `PATCH /api/skills/{id}` with
   `{rank}` appends the previous rank and points to `change_history` and
   restarts `xp` at 0, refuses rank 6 with 422, and is a no-op on the same
   rank. Both rolls read the rank's modifier: a rank-4 base row gives
   `day_resolve._step_player_tier` 2.
A4 -- no tier left (AST and static). No `.tier` attribute and no `tier=`
   keyword argument under `src/` or in `scripts/seed_pilot.py`;
   `PjSkillFiche.svelte` and `cockpit/crud/skills.py` do not contain the
   word `tier`; `play_physical.py` calls `rank_modifier(`.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that examines zero rows is a
FAILURE.
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
SRC = ROOT / "src" / "world_engine"
MIGRATION = ROOT / "scripts" / "migrate_v2_15_skill_ranks.py"

FAILURES: list[str] = []

# The three tables as v2.14 created them (dumped from `main` at a5fbc1e).
_V214_DDL = (
    """CREATE TABLE skill_system (
	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, name VARCHAR NOT NULL,
	description VARCHAR,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id), FOREIGN KEY(world_id) REFERENCES world (id))""",
    "CREATE UNIQUE INDEX idx_skill_system_world_name ON skill_system (world_id, name)",
    "CREATE INDEX idx_skill_system_world ON skill_system (world_id)",
    """CREATE TABLE skill_definition (
	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, name VARCHAR NOT NULL,
	base_domain VARCHAR NOT NULL, system_id VARCHAR, description VARCHAR,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_skill_definition_base_domain CHECK (base_domain IN ('physical','agility','perception','composure')),
	FOREIGN KEY(world_id) REFERENCES world (id),
	FOREIGN KEY(system_id) REFERENCES skill_system (id) ON DELETE RESTRICT)""",
    "CREATE UNIQUE INDEX idx_skill_definition_world_name ON skill_definition (world_id, name)",
    "CREATE INDEX idx_skill_definition_system ON skill_definition (system_id)",
    "CREATE INDEX idx_skill_definition_world ON skill_definition (world_id)",
    """CREATE TABLE skill (
	id VARCHAR NOT NULL, character_id VARCHAR NOT NULL, domain VARCHAR NOT NULL,
	tier INTEGER DEFAULT 0 NOT NULL, change_history JSON DEFAULT '[]' NOT NULL,
	skill_definition_id VARCHAR,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id), CONSTRAINT ck_skill_tier CHECK (tier BETWEEN -1 AND 2),
	FOREIGN KEY(character_id) REFERENCES entity (id),
	FOREIGN KEY(skill_definition_id) REFERENCES skill_definition (id) ON DELETE RESTRICT)""",
    "CREATE INDEX idx_skill_character ON skill (character_id)",
)


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> str:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    return db_path


def _checks_of(table) -> dict[str, str]:
    from sqlalchemy import CheckConstraint
    return {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}


# --- A1 ------------------------------------------------------------------------

def check_a1() -> None:
    from world_engine import skill_ranks
    from world_engine.models import Skill, SkillDefinition, SkillRank, SkillSystem

    skill = {c.name: c for c in Skill.__table__.columns}
    if "tier" in skill or not {"rank", "xp"} <= set(skill):
        fail(f"A1: skill columns are {sorted(skill)}")
    else:
        if str(skill["rank"].server_default.arg) != str(skill_ranks.DEFAULT_RANK):
            fail(f"A1: skill.rank defaults to {skill['rank'].server_default.arg!r}")
        if str(skill["xp"].server_default.arg) != "0":
            fail(f"A1: skill.xp defaults to {skill['xp'].server_default.arg!r}")
    checks = _checks_of(Skill.__table__)
    if checks.get("ck_skill_rank") != "rank BETWEEN 0 AND 5" or checks.get("ck_skill_xp") != "xp >= 0" \
            or "ck_skill_tier" in checks:
        fail(f"A1: skill CHECKs are {checks}")
    for model, name in ((SkillSystem, "ck_skill_system_rank_points"),
                        (SkillDefinition, "ck_skill_definition_rank_points")):
        columns = {c.name: c for c in model.__table__.columns}
        for column in skill_ranks.RANK_POINTS_COLUMNS:
            if column not in columns or not columns[column].nullable:
                fail(f"A1: {model.__tablename__}.{column} is missing or NOT NULL")
        text = _checks_of(model.__table__).get(name, "")
        if any(f"{c} >= 1" not in text for c in skill_ranks.RANK_POINTS_COLUMNS):
            fail(f"A1: {model.__tablename__} {name} is {text!r}")
    ladder = SkillRank.__table__
    if {c.name for c in ladder.columns} != {"id", "world_id", "rank", "label", "points_to_next", "updated_at"}:
        fail(f"A1: skill_rank columns are {sorted(c.name for c in ladder.columns)}")
    if set(_checks_of(ladder)) != {"ck_skill_rank_rank", "ck_skill_rank_points"}:
        fail(f"A1: skill_rank CHECKs are {_checks_of(ladder)}")
    indexes = {i.name: ([c.name for c in i.columns], bool(i.unique)) for i in ladder.indexes}
    if indexes != {"idx_skill_rank_world_rank": (["world_id", "rank"], True)}:
        fail(f"A1: skill_rank indexes are {indexes}")
    expected = (
        (skill_ranks.RANKS, (0, 1, 2, 3, 4, 5)),
        (skill_ranks.RANK_MODIFIERS, (-1, 0, 1, 2, 2, 3)),
        (skill_ranks.DEFAULT_RANK_LABELS,
         ("Inexpérimenté", "Initié", "Apprenti", "Confirmé", "Expert", "Maître")),
        (skill_ranks.DEFAULT_POINTS_TO_NEXT, (5, 10, 20, 40, 80)),
    )
    for got, want in expected:
        if tuple(got) != want:
            fail(f"A1: skill_ranks carries {got}, expected {want}")
    if sorted(skill_ranks.TIER_TO_RANK) != [-1, 0, 1, 2] or any(
            skill_ranks.RANK_MODIFIERS[r] != t for t, r in skill_ranks.TIER_TO_RANK.items()):
        fail(f"A1: TIER_TO_RANK {skill_ranks.TIER_TO_RANK} changes a former tier's modifier")


# --- A2 ------------------------------------------------------------------------

def _run_migration(db_path: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True,
                          text=True, cwd=str(ROOT), timeout=120)


def _shape(conn, table: str) -> list[tuple]:
    return [(r[1], r[2], r[3], r[4]) for r in conn.execute(f"PRAGMA table_info({table})")]


def _seed_v214(db_path: str) -> dict:
    from sqlmodel import Session

    from world_engine.db import create_db_and_tables, engine
    from world_engine.models import Character, Entity, SchemaMeta, World

    create_db_and_tables()
    with Session(engine) as session:
        world = World(name="Ranks A2", is_active=True)
        session.add(world)
        session.flush()
        pc = Entity(world_id=world.id, type="character", name="PC")
        session.add(pc)
        session.flush()
        session.add(Character(id=pc.id, world_id=world.id, character_type="player"))
        if session.get(SchemaMeta, 1) is None:
            session.add(SchemaMeta(id=1, static_version="v2.14"))
        session.commit()
        ids = {"world": world.id, "pc": pc.id}
    engine.dispose()
    with sqlite3.connect(db_path) as conn:
        model_shapes = {t: _shape(conn, t) for t in ("skill_system", "skill_definition", "skill", "skill_rank")}
        conn.execute("PRAGMA foreign_keys=OFF")
        for table in ("skill", "skill_definition", "skill_system", "skill_rank"):
            conn.execute(f"DROP TABLE {table}")
        for statement in _V214_DDL:
            conn.execute(statement)
        conn.execute("INSERT INTO skill_system (id, world_id, name) VALUES ('sys', ?, 'Magie')", (ids["world"],))
        conn.execute("INSERT INTO skill_definition (id, world_id, name, base_domain, system_id) "
                     "VALUES ('def', ?, 'Feu', 'composure', 'sys')", (ids["world"],))
        for tier, domain, definition in ((-1, "physical", None), (0, "agility", None),
                                         (1, "perception", None), (2, "composure", "def")):
            conn.execute("INSERT INTO skill (id, character_id, domain, tier, change_history, "
                         "skill_definition_id) VALUES (?, ?, ?, ?, ?, ?)",
                         (f"t{tier}", ids["pc"], domain, tier, '[{"tier": 0}]', definition))
    ids["model_shapes"] = model_shapes
    return ids


def _set_version(db_path: str, version: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE schema_meta SET static_version = ? WHERE id = 1", (version,))


def _state(db_path: str) -> dict:
    with sqlite3.connect(db_path) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        skill_columns = {r[1] for r in conn.execute("PRAGMA table_info(skill)")}
        state = {
            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
            "shapes": {t: _shape(conn, t) for t in ("skill_system", "skill_definition", "skill", "skill_rank")
                       if t in tables},
            "systems": conn.execute("SELECT id, name FROM skill_system").fetchall(),
            "definitions": conn.execute("SELECT id, system_id FROM skill_definition").fetchall(),
            "fk": conn.execute("PRAGMA foreign_key_check").fetchall(),
            "ladder": conn.execute("SELECT COUNT(*) FROM skill_rank").fetchone()[0] if "skill_rank" in tables else None,
            "ddl": sorted(r[0] for r in conn.execute(
                "SELECT sql FROM sqlite_master WHERE tbl_name IN ('skill','skill_system','skill_definition') "
                "AND sql IS NOT NULL")),
        }
        state["skills"] = sorted(conn.execute(
            "SELECT id, domain, rank, xp, change_history, skill_definition_id FROM skill").fetchall()
        ) if "rank" in skill_columns else None
    return state


def check_a2(db_path: str) -> None:
    ids = _seed_v214(db_path)
    _set_version(db_path, "v2.13")
    before = _state(db_path)
    result = _run_migration(db_path)
    if result.returncode == 0 or _state(db_path) != before:
        fail(f"A2a: v2.13 was not refused, or changed rows (exit {result.returncode})")
    _set_version(db_path, "v2.14")
    result = _run_migration(db_path)
    after = _state(db_path)
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
    if result.returncode != 0 or after["version"] != EXPECTED_STATIC_SCHEMA_VERSION:
        fail(f"A2b: exit {result.returncode}, version {after['version']!r}: {result.stderr.strip()[-400:]}")
        return
    want = [("t-1", "physical", 0, 0, '[{"tier": 0}]', None), ("t0", "agility", 1, 0, '[{"tier": 0}]', None),
            ("t1", "perception", 2, 0, '[{"tier": 0}]', None), ("t2", "composure", 3, 0, '[{"tier": 0}]', "def")]
    if after["skills"] != want:
        fail(f"A2b: skills are {after['skills']}")
    if after["systems"] != [("sys", "Magie")] or after["definitions"] != [("def", "sys")]:
        fail(f"A2b: systems {after['systems']}, definitions {after['definitions']}")
    if after["shapes"] != ids["model_shapes"]:
        fail(f"A2b: shapes {after['shapes']} differ from the models {ids['model_shapes']}")
    if after["ladder"] != 0 or after["fk"]:
        fail(f"A2b: skill_rank rows {after['ladder']}, foreign_key_check {after['fk']}")
    ddl = " ".join(after["ddl"])
    for name in ("ck_skill_rank", "ck_skill_xp", "ck_skill_system_rank_points",
                 "ck_skill_definition_rank_points", "ck_skill_definition_base_domain"):
        if name not in ddl:
            fail(f"A2b: {name} missing after the rebuild")
    again = _run_migration(db_path)
    if again.returncode != 0 or _state(db_path) != after:
        fail(f"A2c: second run exit {again.returncode} or changed rows: {again.stdout.strip()[-200:]}")


# --- A3 ------------------------------------------------------------------------

def _a3_world(session) -> dict:
    from world_engine.models import Character, Entity, Skill, SkillDefinition, SkillSystem, World

    for world in session.exec(__import__("sqlmodel").select(World)).all():
        world.is_active = False
        session.add(world)
    world = World(name="Ranks A3", is_active=True)
    session.add(world)
    session.flush()
    pc = Entity(world_id=world.id, type="character", name="Millys")
    session.add(pc)
    session.flush()
    session.add(Character(id=pc.id, world_id=world.id, character_type="player"))
    system = SkillSystem(world_id=world.id, name="Alchimie", points_to_rank_2=7, points_to_rank_3=9)
    session.add(system)
    session.flush()
    definition = SkillDefinition(world_id=world.id, name="Distillation", base_domain="composure",
                                 system_id=system.id, points_to_rank_3=3)
    session.add(definition)
    session.flush()
    base = Skill(character_id=pc.id, domain="physical", rank=4)
    custom = Skill(character_id=pc.id, domain="composure", rank=1, skill_definition_id=definition.id)
    session.add(base)
    session.add(custom)
    session.commit()
    return {"world": world.id, "pc": pc.id, "system": system, "definition": definition,
            "base": base.id, "custom": custom.id}


def check_a3(engine) -> None:
    from fastapi import HTTPException
    from sqlmodel import Session

    from world_engine import skill_ranks
    from world_engine.cockpit.crud.skills import (
        SkillRankBody, list_skill_ranks, list_skills, update_skill_rank,
    )
    from world_engine.day_resolve import _step_player_tier
    from world_engine.models import Character, Skill, SkillRank

    with Session(engine) as session:
        ids = _a3_world(session)
        ladder = skill_ranks.world_ladder(session, ids["world"])
        if ladder != skill_ranks.default_ladder():
            fail(f"A3: an empty world's ladder is {ladder}")
        session.add(SkillRank(world_id=ids["world"], rank=2, label="Disciple", points_to_next=30))
        session.commit()
        ladder = skill_ranks.world_ladder(session, ids["world"])
        if (ladder[2].label, ladder[2].points_to_next) != ("Disciple", 30) or ladder[1] != skill_ranks.default_ladder()[1]:
            fail(f"A3: the ladder with one row is {ladder}")
        system, definition = ids["system"], ids["definition"]
        cases = (
            ((2, None, None), 30), ((2, system, None), 9), ((1, system, None), 7),
            ((2, system, definition), 3), ((1, None, definition), 10), ((5, system, definition), None),
        )
        for (rank, sys_, def_), want in cases:
            got = skill_ranks.points_to_next(rank, ladder, system=sys_, definition=def_)
            if got != want:
                fail(f"A3: points_to_next(rank {rank}, system {bool(sys_)}, definition {bool(def_)}) = {got}, want {want}")
        served = list_skill_ranks(session)
        if [s["label"] for s in served] != [st.label for st in ladder] or len(served) != 6:
            fail(f"A3: GET /api/skill-ranks served {served}")
        sheet = {row["id"]: row for row in list_skills(character_id=ids["pc"], db=session)}
        base = sheet.get(ids["base"], {})
        if (base.get("rank"), base.get("rank_label"), base.get("xp"), base.get("points_to_next")) != (4, "Expert", 0, 80):
            fail(f"A3: GET /api/skills served {base}")
        custom = sheet.get(ids["custom"], {})
        if custom.get("points_to_next") != 7:
            fail(f"A3: the custom row's points_to_next is {custom.get('points_to_next')} (system override 7)")
        if _step_player_tier(session.get(Character, ids["pc"]), "physical", session) != 2:
            fail("A3: a rank-4 base row does not roll +2 in a day step")
        row = session.get(Skill, ids["base"])
        row.xp = 12
        session.add(row)
        session.commit()
        served = update_skill_rank(ids["base"], SkillRankBody(rank=5), session)
        row = session.get(Skill, ids["base"])
        if (row.rank, row.xp) != (5, 0) or row.change_history[-1].get("rank") != 4 \
                or row.change_history[-1].get("xp") != 12 or served.get("rank_label") != "Maître":
            fail(f"A3: PATCH rank 5 left rank {row.rank}, xp {row.xp}, history {row.change_history}, served {served}")
        length = len(row.change_history)
        update_skill_rank(ids["base"], SkillRankBody(rank=5), session)
        if len(session.get(Skill, ids["base"]).change_history) != length:
            fail("A3: the same rank appended a history entry")
        try:
            update_skill_rank(ids["base"], SkillRankBody(rank=6), session)
            fail("A3: rank 6 was accepted")
        except HTTPException as exc:
            if exc.status_code != 422:
                fail(f"A3: rank 6 answered {exc.status_code}")


# --- A4 ------------------------------------------------------------------------

def check_a4() -> None:
    import ast

    scanned = 0
    for path in sorted((ROOT / "src").rglob("*.py")) + [ROOT / "scripts" / "seed_pilot.py"]:
        scanned += 1
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Attribute) and node.attr == "tier":
                fail(f"A4: .tier read at {path.relative_to(ROOT)}:{node.lineno}")
            if isinstance(node, ast.keyword) and node.arg == "tier":
                fail(f"A4: tier= written at {path.relative_to(ROOT)}:{node.value.lineno}")
    if scanned == 0:
        fail("A4: no file scanned")
    for rel in ("frontend/src/creation/PjSkillFiche.svelte", "src/world_engine/cockpit/crud/skills.py"):
        if re.search(r"\btier\b", (ROOT / rel).read_text(encoding="utf-8")):
            fail(f"A4: {rel} still names a tier")
    if "rank_modifier(" not in (SRC / "cockpit" / "play_physical.py").read_text(encoding="utf-8"):
        fail("A4: play_physical.py does not call rank_modifier(")


def main() -> int:
    db_path = _fresh_db()
    check_a1()
    check_a2(db_path)
    # The migrated database is the v2.15 one the later rules write into.
    from world_engine.db import create_db_and_tables, engine
    create_db_and_tables()
    check_a3(engine)
    check_a4()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: skill_progression -- v2.15 gives a skill a rank (0-5) and points in place of "
          "its tier, keeps every former tier's roll, lets a world, a system and a skill set "
          "the points of each rank, and migrates from v2.14 only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
