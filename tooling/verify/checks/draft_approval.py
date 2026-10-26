"""G1 check for TICKET-0129 (BRIEF-0129-E) -- the approval writes a drafted character to canon in one transaction, or nothing.

DA4 -- the creator's route `POST /api/characters/player` still creates a
   character at the four base domains and the open skills at rank 1
   (`write_player_character` called without `ranks` nor `teachers`), no
   row for a skill that requires a master, and refuses a second one for
   the creator with its `{"ok": false}` answer.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A case not reached is a FAILURE.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

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

    plan: list = []
    try:
        with Session(engine) as db:
            ids = _world(db)
            db.commit()
        client = TestClient(app, base_url="http://127.0.0.1")
        plan = [("DA4", lambda: rule_da4(engine, client, ids))]
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
    if reached != 1:
        fail(f"{reached} of 1 rules reached")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: draft_approval -- the creator's own route still writes a character at the default "
          "ranks, open skills only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
