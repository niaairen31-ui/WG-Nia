"""G1 check for TICKET-0107 -- NPC skill sheets, and skills learned from a
master.

The lot adds its pieces brief by brief; this check grows with it (the
`skill_progression.py` precedent, TICKET-0106). Each brief adds its rules
here in the same commit.

A1 -- schema (BRIEF-0107-A, v2.16). `skill_definition.requires_master` is a
   NOT NULL boolean defaulting to 0; `skill.taught_by_id` is a nullable
   foreign key to `entity`; `character` has no `physical_tier`; the
   `character` registry fields (`ENTITY_TYPE_REGISTRY`) name no
   `physical_tier`.
A2 -- migration `scripts/migrate_v2_16_npc_skills.py`, on a v2.15-shaped
   database (`character.physical_tier` present, `skill_definition` and
   `skill` in their v2.15 DDL, verbatim below), holding NPCs at tiers -1, 0
   and 2, an NPC at tier 2 that already holds a `physical` row at rank 4, a
   player at tier 1, and a definition:
   a. at v2.14 it refuses (non-zero exit) and changes nothing; with a tier
      of 5 it refuses and changes nothing;
   b. at v2.15 it gives the tier -1 NPC a `physical` row at rank 0 and the
      tier 2 NPC one at rank 3; the tier 0 NPC and the player get none; the
      NPC that held a row keeps it at rank 4, alone; `physical_tier` is
      gone, both new columns exist (the definition's `requires_master` 0),
      the three tables have the models' columns, `PRAGMA
      foreign_key_check` is empty on those three tables, and `schema_meta`
      is the code's version -- with a `session` row pointing to a missing
      world in the database, which the migration lists and does not stop on
      (AMENDMENT-0107-01);
   c. a second run exits zero and changes no row.
A3 -- the rows a roll reads (fixture, D1). For the player:
   `skill_access.player_skill` on a base domain reads the base row; on a
   definition the player holds, that row; on a definition he lacks, his base
   row for its domain. For an opposing NPC: `opposition_modifier` reads its
   row for the definition (rank 5: +3), else its base row for the domain
   (rank 3: +2), else 0.
A4 -- the carrure at creation (fixture and static). Creating a character
   with `carrure` 2 writes its `physical` row at rank 3, with 0 or none
   writes no row, with 9 clamps to rank 3; `write_skill_row` refuses a
   second row for the same skill, both or neither of domain/definition, and
   rank 6, each before any write. No `.physical_tier` attribute under `src/`
   (AST); `npc_agent.py` passes `carrure=`; `play_physical.py` calls
   `skill_access.opposition_modifier(` and `skill_access.player_skill(`.

B1 -- the flag (BRIEF-0107-B, fixture, A2). `POST /api/skill-definitions`
   with `requires_master` gives no player a row and serves the flag; without
   it, every player gets one at `DEFAULT_RANK`. Turning the flag off
   (`PUT`) backfills every player lacking the row; turning it on keeps every
   row held. `_pc_custom_skill_defs` (a new PC's seed) lists no
   `requires_master` definition.
B2 -- the lock in Play (fixture, B1). `player_skill` on a `requires_master`
   definition the player lacks is `locked`, row None, with no fallback to
   the base row; on one he holds, it is that row. With a minimal turn
   context, `_say_physical_resolve_verdict` on the locked skill returns the
   band `locked`, dice (0, 0), the skill's name as `domain`, `progress`
   None on the verdict event, and writes no `skill_progress` mutation.
   `_say_physical_discovery` returns `locked_rubric`; `_mj_user_physical`
   with the band `locked` carries the rubric and no « Résultat mécanique ».
B3 -- learning (fixture, C1). `GET /api/skills/learnable` lists, for a
   player, exactly the `requires_master` definitions he lacks, each with its
   masters (characters at rank 5 in it); for an NPC, its missing base
   domains and every definition it lacks. `POST /api/skills` with a master
   writes the row at the given rank with `taught_by_id`; with a non-master,
   or the learner as his own master, 422; a second time, 409; without a
   master, the row with `taught_by_id` None; an NPC base domain at rank 4.
   `GET /api/skills` serves `requires_master` and `taught_by_id`.
B4 -- documentation (static). CLAUDE.md names `requires_master` and
   `skill_access`'s lock.

C1 -- the routes the fiche reads (BRIEF-0107-C, fixture).
   `GET /api/skills/player-characters?character_type=npc` lists the
   world's NPCs only, `player` its players only, another value 422; `GET
   /api/skills` serves `taught_by_name` (the master's name, None without
   one).
C2 -- the UI (static). `tabs.js`'s `npc` entry mounts the `pjSkillFiche`
   island and declares its `fiche` slot; `PjSkillFiche.svelte` asks for
   `character_type=${characterType}`, reads `/api/skills/learnable`, POSTs
   `/api/skills` with rank 0 for a player, offers « Apprendre » and « Sans
   maître »; `CompetencesSheet.svelte` binds `requires_master`;
   `competences.svelte.js` sends it; the built bundle carries « Exige un
   maître » and « À apprendre ».

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that examines zero rows is a
FAILURE.
"""
from __future__ import annotations

import os
import pathlib
import sqlite3
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"
MIGRATION = ROOT / "scripts" / "migrate_v2_16_npc_skills.py"

FAILURES: list[str] = []

# The two tables as v2.15 created them (dumped from `main` at 7b1ef23).
_V215_DDL = (
    """CREATE TABLE skill_definition (
	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, name VARCHAR NOT NULL,
	base_domain VARCHAR NOT NULL, system_id VARCHAR, description VARCHAR,
	points_to_rank_1 INTEGER, points_to_rank_2 INTEGER, points_to_rank_3 INTEGER,
	points_to_rank_4 INTEGER, points_to_rank_5 INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_skill_definition_base_domain CHECK (base_domain IN ('physical','agility','perception','composure')),
	CONSTRAINT ck_skill_definition_rank_points CHECK ((points_to_rank_1 IS NULL OR points_to_rank_1 >= 1) AND (points_to_rank_2 IS NULL OR points_to_rank_2 >= 1) AND (points_to_rank_3 IS NULL OR points_to_rank_3 >= 1) AND (points_to_rank_4 IS NULL OR points_to_rank_4 >= 1) AND (points_to_rank_5 IS NULL OR points_to_rank_5 >= 1)),
	FOREIGN KEY(world_id) REFERENCES world (id),
	FOREIGN KEY(system_id) REFERENCES skill_system (id) ON DELETE RESTRICT)""",
    "CREATE INDEX idx_skill_definition_world ON skill_definition (world_id)",
    "CREATE INDEX idx_skill_definition_system ON skill_definition (system_id)",
    "CREATE UNIQUE INDEX idx_skill_definition_world_name ON skill_definition (world_id, name)",
    """CREATE TABLE skill (
	id VARCHAR NOT NULL, character_id VARCHAR NOT NULL, domain VARCHAR NOT NULL,
	rank INTEGER DEFAULT 1 NOT NULL, xp INTEGER DEFAULT 0 NOT NULL,
	change_history JSON DEFAULT '[]' NOT NULL, skill_definition_id VARCHAR,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_skill_rank CHECK (rank BETWEEN 0 AND 5),
	CONSTRAINT ck_skill_xp CHECK (xp >= 0),
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


# --- A1 ------------------------------------------------------------------------

def check_a1() -> None:
    from world_engine.cockpit.crud.entities import ENTITY_TYPE_REGISTRY
    from world_engine.models import Character, Skill, SkillDefinition

    flag = SkillDefinition.__table__.columns.get("requires_master")
    if flag is None or flag.nullable or str(flag.server_default.arg) != "0":
        fail(f"A1: skill_definition.requires_master is {flag!r}")
    teacher = Skill.__table__.columns.get("taught_by_id")
    if teacher is None or not teacher.nullable or [fk.target_fullname for fk in teacher.foreign_keys] != ["entity.id"]:
        fail(f"A1: skill.taught_by_id is {teacher!r}")
    if "physical_tier" in Character.__table__.columns:
        fail("A1: character still declares physical_tier")
    names = [f["name"] for f in ENTITY_TYPE_REGISTRY["character"]["fields"]]
    if not names or "physical_tier" in names:
        fail(f"A1: the character registry fields are {names}")


# --- A2 ------------------------------------------------------------------------

def _run_migration(db_path: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True,
                          text=True, cwd=str(ROOT), timeout=120)


def _shape(conn, table: str) -> list[tuple]:
    return sorted((r[1], r[2], r[3], r[4]) for r in conn.execute(f"PRAGMA table_info({table})"))


def _seed_v215(db_path: str) -> dict:
    from sqlmodel import Session

    from world_engine.db import create_db_and_tables, engine
    from world_engine.models import Character, Entity, SchemaMeta, World

    create_db_and_tables()
    ids: dict = {}
    with Session(engine) as session:
        world = World(name="NPC skills A2", is_active=True)
        session.add(world)
        session.flush()
        ids["world"] = world.id
        for key, kind in (("m1", "npc"), ("z", "npc"), ("p2", "npc"), ("held", "npc"), ("pc", "player")):
            row = Entity(world_id=world.id, type="character", name=key)
            session.add(row)
            session.flush()
            session.add(Character(id=row.id, world_id=world.id, character_type=kind))
            ids[key] = row.id
        if session.get(SchemaMeta, 1) is None:
            session.add(SchemaMeta(id=1, static_version="v2.15"))
        session.commit()
    engine.dispose()
    with sqlite3.connect(db_path) as conn:
        ids["model_shapes"] = {t: _shape(conn, t) for t in ("skill", "skill_definition", "character")}
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DROP TABLE skill")
        conn.execute("DROP TABLE skill_definition")
        for statement in _V215_DDL:
            conn.execute(statement)
        conn.execute("ALTER TABLE character ADD COLUMN physical_tier INTEGER DEFAULT 0 NOT NULL")
        for key, tier in (("m1", -1), ("z", 0), ("p2", 2), ("held", 2), ("pc", 1)):
            conn.execute("UPDATE character SET physical_tier = ? WHERE id = ?", (tier, ids[key]))
        conn.execute("INSERT INTO skill_definition (id, world_id, name, base_domain) VALUES ('def', ?, 'Feu', 'composure')",
                     (ids["world"],))
        conn.execute("INSERT INTO skill (id, character_id, domain, rank) VALUES ('held-phys', ?, 'physical', 4)",
                     (ids["held"],))
        # A dangling reference this migration never wrote (AMENDMENT-0107-01).
        conn.execute("INSERT INTO session (id, world_id, number) VALUES ('orphan-session', 'gone-world', 9)")
    return ids


def _set(db_path: str, sql: str, params: tuple = ()) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(sql, params)


def _state(db_path: str) -> dict:
    with sqlite3.connect(db_path) as conn:
        return {
            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
            "shapes": {t: _shape(conn, t) for t in ("skill", "skill_definition", "character")},
            "skills": sorted(conn.execute("SELECT character_id, domain, rank, skill_definition_id FROM skill").fetchall()),
            "definitions": conn.execute("SELECT * FROM skill_definition").fetchall(),
            "fk": [r for t in ("skill", "skill_definition", "character")
                   for r in conn.execute(f"PRAGMA foreign_key_check({t})").fetchall()],
        }


def check_a2(db_path: str) -> None:
    ids = _seed_v215(db_path)
    _set(db_path, "UPDATE schema_meta SET static_version = 'v2.14' WHERE id = 1")
    before = _state(db_path)
    result = _run_migration(db_path)
    if result.returncode == 0 or _state(db_path) != before:
        fail(f"A2a: v2.14 was not refused, or changed rows (exit {result.returncode})")
    _set(db_path, "UPDATE schema_meta SET static_version = 'v2.15' WHERE id = 1")
    _set(db_path, "UPDATE character SET physical_tier = 5 WHERE id = ?", (ids["z"],))
    before = _state(db_path)
    result = _run_migration(db_path)
    if result.returncode == 0 or _state(db_path) != before:
        fail(f"A2a: a tier of 5 was not refused, or changed rows (exit {result.returncode})")
    _set(db_path, "UPDATE character SET physical_tier = 0 WHERE id = ?", (ids["z"],))
    result = _run_migration(db_path)
    after = _state(db_path)
    if result.returncode == 0 and "session rowid" not in result.stdout:
        fail("A2b: the dangling session row was not listed")
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
    if result.returncode != 0 or after["version"] != EXPECTED_STATIC_SCHEMA_VERSION:
        fail(f"A2b: exit {result.returncode}, version {after['version']!r}: {result.stderr.strip()[-400:]}")
        return
    want = sorted([(ids["m1"], "physical", 0, None), (ids["p2"], "physical", 3, None),
                   (ids["held"], "physical", 4, None)])
    if after["skills"] != want:
        fail(f"A2b: skill rows are {after['skills']}, want {want}")
    if after["shapes"] != ids["model_shapes"]:
        fail(f"A2b: shapes {after['shapes']} differ from the models {ids['model_shapes']}")
    with sqlite3.connect(db_path) as conn:
        flag = conn.execute("SELECT requires_master FROM skill_definition WHERE id = 'def'").fetchone()
    if flag != (0,) or after["fk"]:
        fail(f"A2b: requires_master {flag}, foreign_key_check {after['fk']}")
    again = _run_migration(db_path)
    if again.returncode != 0 or _state(db_path) != after:
        fail(f"A2c: second run exit {again.returncode} or changed rows: {again.stdout.strip()[-200:]}")


# --- A3-A4 ---------------------------------------------------------------------

def _a_world(session) -> dict:
    from sqlmodel import select

    from world_engine.models import Character, Entity, Skill, SkillDefinition, World

    for world in session.exec(select(World)).all():
        world.is_active = False
        session.add(world)
    world = World(name="NPC skills A3", is_active=True)
    session.add(world)
    session.flush()
    ids = {"world": world.id}
    for key, kind in (("pc", "player"), ("master", "npc"), ("brute", "npc"), ("plain", "npc")):
        row = Entity(world_id=world.id, type="character", name=key)
        session.add(row)
        session.flush()
        session.add(Character(id=row.id, world_id=world.id, character_type=kind))
        ids[key] = row.id
    for key, domain in (("escrime", "physical"), ("feu", "composure")):
        d = SkillDefinition(world_id=world.id, name=key, base_domain=domain)
        session.add(d)
        session.flush()
        ids[key] = d
    rows = {
        "pc_phys": Skill(character_id=ids["pc"], domain="physical", rank=2),
        "pc_comp": Skill(character_id=ids["pc"], domain="composure", rank=0),
        "pc_escrime": Skill(character_id=ids["pc"], domain="physical", rank=4, skill_definition_id=ids["escrime"].id),
        "master_escrime": Skill(character_id=ids["master"], domain="physical", rank=5,
                                skill_definition_id=ids["escrime"].id),
        "brute_phys": Skill(character_id=ids["brute"], domain="physical", rank=3),
    }
    for row in rows.values():
        session.add(row)
    session.commit()
    ids.update({k: r.id for k, r in rows.items()})
    session.exec(select(World))  # keep the session usable
    return ids


def check_a3(engine) -> None:
    from sqlmodel import Session

    from world_engine.skill_access import opposition_modifier, player_skill

    with Session(engine) as session:
        ids = _a_world(session)
        defs = {"escrime": ids["escrime"], "feu": ids["feu"]}
        cases = (("physical", ids["pc_phys"], "physical"), ("escrime", ids["pc_escrime"], "physical"),
                 ("feu", ids["pc_comp"], "composure"))
        for token, row_id, base in cases:
            got = player_skill(session, ids["pc"], token, defs)
            if (got.row.id if got.row else None, got.base_domain) != (row_id, base):
                fail(f"A3: player_skill({token!r}) read {got.row.id if got.row else None}/{got.base_domain}")
        modifiers = (("master", "physical", ids["escrime"], 3), ("brute", "physical", ids["escrime"], 2),
                     ("plain", "physical", ids["escrime"], 0), ("brute", "physical", None, 2),
                     ("master", "physical", None, 0))
        for npc, base, definition, want in modifiers:
            got = opposition_modifier(session, ids[npc], base, definition)
            if got != want:
                fail(f"A3: opposition_modifier({npc}, {base}, {definition.name if definition else None}) = {got}, want {want}")


def check_a4(engine) -> None:
    import ast

    from sqlmodel import Session, select

    from world_engine.cockpit.crud.entities import EntityWriteBody, _create_entity_core
    from world_engine.models import Skill
    from world_engine.writes import write_skill_row

    with Session(engine) as session:
        ids = _a_world(session)
        for name, carrure, want in (("c2", 2, [3]), ("c0", 0, []), ("cnone", None, []), ("c9", 9, [3])):
            body = EntityWriteBody(entity={"name": name, "type": "character"},
                                   extension={"character_type": "npc"}, carrure=carrure)
            entity = _create_entity_core(body, session)
            session.commit()
            ranks = [r.rank for r in session.exec(select(Skill).where(Skill.character_id == entity.id)).all()]
            if ranks != want:
                fail(f"A4: carrure {carrure} wrote ranks {ranks}, want {want}")
        bad_calls = (
            dict(character_id=ids["brute"], domain="physical", rank=1),
            dict(character_id=ids["master"], skill_definition_id=ids["escrime"].id, rank=1),
            dict(character_id=ids["plain"], rank=1),
            dict(character_id=ids["plain"], domain="physical", skill_definition_id=ids["feu"].id, rank=1),
            dict(character_id=ids["plain"], domain="physical", rank=6),
        )
        for kwargs in bad_calls:
            count = len(session.exec(select(Skill)).all())
            try:
                write_skill_row(session, **kwargs)
                fail(f"A4: write_skill_row accepted {kwargs}")
            except ValueError:
                pass
            session.flush()
            if len(session.exec(select(Skill)).all()) != count:
                fail(f"A4: a refused write_skill_row wrote a row ({kwargs})")
        session.rollback()
    scanned = 0
    for path in sorted((ROOT / "src").rglob("*.py")):
        scanned += 1
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Attribute) and node.attr == "physical_tier":
                fail(f"A4: .physical_tier read at {path.relative_to(ROOT)}:{node.lineno}")
    if scanned == 0:
        fail("A4: no file scanned")
    if "carrure=" not in (SRC / "cockpit" / "routes" / "npc_agent.py").read_text(encoding="utf-8"):
        fail("A4: npc_agent.py does not pass the carrure")
    play = (SRC / "cockpit" / "play_physical.py").read_text(encoding="utf-8")
    if "skill_access.opposition_modifier(" not in play or "skill_access.player_skill(" not in play:
        fail("A4: play_physical.py does not read its rows through skill_access")


# --- B1-B4 ---------------------------------------------------------------------

def check_b1(engine) -> None:
    from sqlmodel import Session, select

    from world_engine.cockpit.crud.skills import (
        SkillDefinitionWriteBody, create_skill_definition, update_skill_definition,
    )
    from world_engine.cockpit.routes.creator import _pc_custom_skill_defs
    from world_engine.models import Skill
    from world_engine.skill_ranks import DEFAULT_RANK

    with Session(engine) as session:
        ids = _a_world(session)

        def holders(definition_id: str) -> list:
            return sorted((r.character_id, r.rank) for r in session.exec(
                select(Skill).where(Skill.skill_definition_id == definition_id)).all())

        locked = create_skill_definition(SkillDefinitionWriteBody(
            name="Alchimie", base_domain="perception", requires_master=True), session)
        if holders(locked["id"]) or locked.get("requires_master") is not True:
            fail(f"B1: a requires_master skill gave rows {holders(locked['id'])} / served {locked}")
        open_ = create_skill_definition(SkillDefinitionWriteBody(name="Course", base_domain="agility"), session)
        if holders(open_["id"]) != [(ids["pc"], DEFAULT_RANK)]:
            fail(f"B1: an open skill gave rows {holders(open_['id'])}")
        update_skill_definition(locked["id"], SkillDefinitionWriteBody(
            name="Alchimie", base_domain="perception", requires_master=False), session)
        if holders(locked["id"]) != [(ids["pc"], DEFAULT_RANK)]:
            fail(f"B1: opening the skill gave rows {holders(locked['id'])}")
        update_skill_definition(locked["id"], SkillDefinitionWriteBody(
            name="Alchimie", base_domain="perception", requires_master=True), session)
        if holders(locked["id"]) != [(ids["pc"], DEFAULT_RANK)]:
            fail(f"B1: locking the skill again changed rows to {holders(locked['id'])}")
        seeded = {d.name for d in _pc_custom_skill_defs(ids["world"], session)}
        if "Alchimie" in seeded or "Course" not in seeded:
            fail(f"B1: a new PC would be seeded with {sorted(seeded)}")


def check_b2(engine) -> None:
    import json
    from types import SimpleNamespace

    from sqlmodel import Session, select

    from world_engine.cockpit.play_physical import _say_physical_discovery, _say_physical_resolve_verdict
    from world_engine.cockpit.play_stream import _mj_user_physical
    from world_engine.models import Conversation, ProposedMutation, Session as GameSession, Skill, SkillDefinition
    from world_engine.skill_access import locked_rubric, player_skill

    with Session(engine) as session:
        ids = _a_world(session)
        magic = SkillDefinition(world_id=ids["world"], name="Magie", base_domain="composure", requires_master=True)
        rune = SkillDefinition(world_id=ids["world"], name="Rune", base_domain="composure", requires_master=True)
        session.add(magic)
        session.add(rune)
        session.flush()
        session.add(Skill(character_id=ids["pc"], domain="composure", rank=3, skill_definition_id=rune.id))
        game = GameSession(world_id=ids["world"], number=1)
        session.add(game)
        session.flush()
        conv = Conversation(world_id=ids["world"], session_id=game.id, player_id=ids["pc"])
        session.add(conv)
        session.commit()
        defs = {"Magie": magic, "Rune": rune}
        got = player_skill(session, ids["pc"], "Magie", defs)
        if not got.locked or got.row is not None:
            fail(f"B2: an untaught master skill read locked={got.locked}, row={got.row}")
        got = player_skill(session, ids["pc"], "Rune", defs)
        if got.locked or got.row is None or got.row.rank != 3:
            fail(f"B2: a taught master skill read locked={got.locked}, row={got.row}")
        ctx = SimpleNamespace(db=session, conv=SimpleNamespace(player_id=ids["pc"]), world_id=ids["world"],
                              conv_id=conv.id)
        base, verdict, _opposed, line = _say_physical_resolve_verdict(ctx, "Magie", None, None, defs)
        event = json.loads(line[len("data: "):])["verdict"]
        if (verdict.band, tuple(verdict.dice), verdict.domain, base) != ("locked", (0, 0), "Magie", "composure") \
                or event.get("progress") is not None:
            fail(f"B2: the locked roll gave {verdict} / {event}")
        written = session.exec(select(ProposedMutation).where(ProposedMutation.world_id == ids["world"])).all()
        if written:
            fail(f"B2: the locked roll wrote {len(written)} mutation(s)")
        rubric = _say_physical_discovery(ctx, base, None, verdict)
        if rubric != locked_rubric("Magie"):
            fail(f"B2: discovery returned {rubric!r}")
        text = _mj_user_physical("", "", "Salle", "je lance un sort", "", "", "locked", rubric)
        if "Résultat mécanique" in text or "COMPÉTENCE NON MAÎTRISÉE" not in text:
            fail("B2: the MJ message for a locked skill keeps the verdict block or lacks the rubric")


def check_b3(engine) -> None:
    from fastapi import HTTPException
    from sqlmodel import Session

    from world_engine.cockpit.crud.skills import SkillGrantBody, grant_skill, list_learnable_skills, list_skills
    from world_engine.models import SkillDefinition

    with Session(engine) as session:
        ids = _a_world(session)
        alch = SkillDefinition(world_id=ids["world"], name="Alchimie", base_domain="perception", requires_master=True)
        session.add(alch)
        session.commit()
        ids["escrime"].requires_master = True
        session.add(ids["escrime"])
        session.commit()
        learnable = {e["name"]: [m["id"] for m in e["masters"]] for e in list_learnable_skills(ids["pc"], session)}
        if learnable != {"Alchimie": []}:
            fail(f"B3: the player may learn {learnable}")
        npc = {e["name"] for e in list_learnable_skills(ids["brute"], session)}
        if npc != {"agility", "perception", "composure", "Alchimie", "escrime", "feu"}:
            fail(f"B3: the NPC may be given {sorted(npc)}")
        plain_learn = {e["name"]: [m["id"] for m in e["masters"]] for e in list_learnable_skills(ids["plain"], session)}
        if plain_learn.get("escrime") != [ids["master"]]:
            fail(f"B3: escrime's masters are {plain_learn.get('escrime')}")

        def call(**kwargs):
            try:
                return grant_skill(SkillGrantBody(**kwargs), session)
            except HTTPException as exc:
                session.rollback()
                return exc.status_code

        if call(character_id=ids["plain"], skill_definition_id=ids["escrime"].id, taught_by_id=ids["brute"]) != 422:
            fail("B3: a non-master taught")
        if call(character_id=ids["master"], skill_definition_id=alch.id, taught_by_id=ids["master"]) != 422:
            fail("B3: a character taught himself")
        row = call(character_id=ids["plain"], skill_definition_id=ids["escrime"].id, taught_by_id=ids["master"])
        if not isinstance(row, dict) or (row["rank"], row["taught_by_id"]) != (0, ids["master"]):
            fail(f"B3: learning from the master gave {row}")
        if call(character_id=ids["plain"], skill_definition_id=ids["escrime"].id) != 409:
            fail("B3: a second grant of the same skill was not refused")
        row = call(character_id=ids["pc"], skill_definition_id=alch.id)
        if not isinstance(row, dict) or row["taught_by_id"] is not None or row["requires_master"] is not True:
            fail(f"B3: the creator's grant without a master gave {row}")
        row = call(character_id=ids["plain"], domain="agility", rank=4)
        if not isinstance(row, dict) or (row["domain"], row["rank"]) != ("agility", 4):
            fail(f"B3: an NPC base domain grant gave {row}")
        sheet = {r["definition_name"]: r for r in list_skills(character_id=ids["plain"], db=session)}
        if sheet.get("escrime", {}).get("taught_by_id") != ids["master"]:
            fail(f"B3: GET /api/skills served {sheet.get('escrime')}")


def check_b4() -> None:
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    if "requires_master" not in text or "skill_access" not in text:
        fail("B4: CLAUDE.md does not name requires_master and skill_access")


# --- C1-C2 ---------------------------------------------------------------------

def check_c1(engine) -> None:
    from fastapi import HTTPException
    from sqlmodel import Session

    from world_engine.cockpit.crud.skills import list_skill_player_characters, list_skills
    from world_engine.models import Skill

    with Session(engine) as session:
        ids = _a_world(session)
        npcs = {c["id"] for c in list_skill_player_characters("npc", session)}
        players = {c["id"] for c in list_skill_player_characters("player", session)}
        if npcs != {ids["master"], ids["brute"], ids["plain"]} or players != {ids["pc"]}:
            fail(f"C1: npc list {npcs}, player list {players}")
        try:
            list_skill_player_characters("monster", session)
            fail("C1: an unknown character_type was accepted")
        except HTTPException as exc:
            if exc.status_code != 422:
                fail(f"C1: an unknown character_type answered {exc.status_code}")
        row = session.get(Skill, ids["brute_phys"])
        row.taught_by_id = ids["master"]
        session.add(row)
        session.commit()
        names = {r["id"]: r["taught_by_name"] for r in list_skills(character_id=ids["brute"], db=session)}
        if names.get(ids["brute_phys"]) != "master":
            fail(f"C1: taught_by_name is {names}")
        others = [r["taught_by_name"] for r in list_skills(character_id=ids["pc"], db=session)]
        if any(others) or not others:
            fail(f"C1: rows without a master serve {others}")


def check_c2() -> None:
    root = ROOT / "frontend" / "src" / "creation"
    tabs = (root / "tabs.js").read_text(encoding="utf-8")
    npc = tabs[tabs.index("  npc: {"):tabs.index("  pj: {")]
    if "key: 'pjSkillFiche'" not in npc or "id: 'fiche', containerId: 'creation-pj-skill'" not in npc:
        fail("C2: the npc tab does not mount the skill fiche")
    fiche = (root / "PjSkillFiche.svelte").read_text(encoding="utf-8")
    for needle in ("character_type=${characterType}", "/api/skills/learnable", "method: 'POST'",
                   "characterType === 'player' ? 0", "'Apprendre'", "Sans maître"):
        if needle not in fiche:
            fail(f"C2: PjSkillFiche.svelte lacks {needle!r}")
    if "bind:checked={creationState.sheetDetail.requires_master}" not in (root / "CompetencesSheet.svelte").read_text(encoding="utf-8"):
        fail("C2: CompetencesSheet.svelte does not bind requires_master")
    if "requires_master: !!record.requires_master" not in (root / "competences.svelte.js").read_text(encoding="utf-8"):
        fail("C2: competences.svelte.js does not send requires_master")
    bundle = "".join(p.read_text(encoding="utf-8") for p in
                     (ROOT / "src" / "world_engine" / "cockpit" / "static" / "assets").glob("*.js"))
    for needle in ("Exige un maître", "À apprendre"):
        if needle not in bundle:
            fail(f"C2: the built bundle does not carry « {needle} »")


def main() -> int:
    db_path = _fresh_db()
    check_a1()
    check_a2(db_path)
    from world_engine.db import create_db_and_tables, engine
    create_db_and_tables()
    check_a3(engine)
    check_a4(engine)
    check_b1(engine)
    check_b2(engine)
    check_b3(engine)
    check_b4()
    check_c1(engine)
    check_c2()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: npc_skills -- v2.16 gives NPCs skill rows in place of physical_tier, migrates "
          "every carrure to a physical row from v2.15 only, and an opposing NPC rolls its own "
          "row for the skill, else its base domain, else Initié; a skill that requires a master "
          "is held only once taught, cannot be rolled until then, and is taught by a Maître or "
          "granted by the creator; the fiche serves NPCs and players, and teaches from it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
