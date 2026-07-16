"""G1 check for TICKET-0032 (BRIEF-0032-a) — scene/join deterministic
targeted join (`target_gathering_id`).

No live Ollama required: `_interpret_mode` is monkeypatched at the
`cockpit.routes.scene` module level (`routes/scene.py` does
`from ..play_physical import (..., _interpret_mode, ...)`, so the
module-level name there — not play_physical.py's own — is the one the
targeted-vs-free-text branch resolves).

Uses a fresh temp-file SQLite DB (WORLD_ENGINE_DATABASE_URL set before any
world_engine import) so this check never touches Nia's real DB.

1. Targeted join (target_gathering_id set): creates conversation +
   gathering_member, conversation.gathering_id set to the target, and
   _interpret_mode is NOT called (zero model calls, G2-b's whole point).
2. Targeted join against a closed gathering -> 404, zero rows written.
3. Targeted join against a gathering at another location -> 400, zero rows
   written.
4. Both player_text and target_gathering_id, or neither -> 422.
5. Free-text join (player_text set, target_gathering_id absent): regression
   — _interpret_mode IS called, response shape unchanged
   ({"conversation_id", "gathering"}).
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile
from datetime import UTC, datetime

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_engine():
    """Point WORLD_ENGINE_DATABASE_URL at a fresh temp SQLite file BEFORE
    importing world_engine.db (module-level engine) — isolates this check
    from the real DB and from any other check already imported in-process."""
    tmp_dir = tempfile.mkdtemp()
    db_path = pathlib.Path(tmp_dir) / "check.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]

    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def _seed_fixture(engine):
    """Minimal hand-built fixture: one world, one location, one player, one
    NPC, an open session, an open gathering with the NPC as its sole active
    member, and active npc_dialogue + mj_interpretation prompt templates
    (each with one prompt_version row — current_prompt raises without one)."""
    from sqlmodel import Session as DbSession

    from world_engine.models import (
        Character,
        Entity,
        Gathering,
        GatheringMember,
        Location,
        PromptTemplate,
        PromptVersion,
        Session as GameSession,
        World,
    )

    with DbSession(engine) as session:
        world = World(name="Check World", is_active=True)
        session.add(world)
        session.commit()
        session.refresh(world)

        loc_entity = Entity(world_id=world.id, type="location", name="Loc")
        session.add(loc_entity)
        session.commit()
        session.refresh(loc_entity)
        session.add(Location(id=loc_entity.id))
        session.commit()

        other_loc_entity = Entity(world_id=world.id, type="location", name="Other Loc")
        session.add(other_loc_entity)
        session.commit()
        session.refresh(other_loc_entity)
        session.add(Location(id=other_loc_entity.id))
        session.commit()

        player_entity = Entity(world_id=world.id, type="character", name="Player")
        session.add(player_entity)
        session.commit()
        session.refresh(player_entity)
        session.add(Character(
            id=player_entity.id, world_id=world.id, character_type="player",
            user_id="check-user", current_location_id=loc_entity.id,
        ))
        session.commit()

        npc_entity = Entity(world_id=world.id, type="character", name="Aldric")
        session.add(npc_entity)
        session.commit()
        session.refresh(npc_entity)
        session.add(Character(
            id=npc_entity.id, world_id=world.id, character_type="npc",
            current_location_id=loc_entity.id,
        ))
        session.commit()

        game_sess = GameSession(
            world_id=world.id, number=1, title="Check session", status="open",
            started_at=datetime.now(UTC),
        )
        session.add(game_sess)
        session.commit()
        session.refresh(game_sess)

        gathering = Gathering(
            world_id=world.id, session_id=game_sess.id, location_id=loc_entity.id,
            label="the group", status="open",
        )
        session.add(gathering)
        session.commit()
        session.refresh(gathering)
        session.add(GatheringMember(gathering_id=gathering.id, entity_id=npc_entity.id))
        session.commit()

        closed_gathering = Gathering(
            world_id=world.id, session_id=game_sess.id, location_id=loc_entity.id,
            label="closed group", status="closed",
        )
        session.add(closed_gathering)
        other_gathering = Gathering(
            world_id=world.id, session_id=game_sess.id, location_id=other_loc_entity.id,
            label="other group", status="open",
        )
        session.add(other_gathering)
        session.commit()
        session.refresh(closed_gathering)
        session.refresh(other_gathering)

        for usage in ("npc_dialogue", "mj_interpretation"):
            tpl = PromptTemplate(name=f"check-{usage}", usage=usage, is_active=True)
            session.add(tpl)
            session.commit()
            session.refresh(tpl)
            session.add(PromptVersion(
                prompt_template_id=tpl.id, version_number=1,
                system_prompt="s", user_template="u",
            ))
            session.commit()

        return {
            "player_id": player_entity.id,
            "npc_id": npc_entity.id,
            "npc_name": npc_entity.name,
            "location_id": loc_entity.id,
            "gathering_id": gathering.id,
            "closed_gathering_id": closed_gathering.id,
            "other_gathering_id": other_gathering.id,
        }


def _count_rows(engine, model) -> int:
    from sqlmodel import Session as DbSession, select
    with DbSession(engine) as session:
        return len(session.exec(select(model)).all())


def check_targeted_and_free_text_join() -> None:
    engine = _fresh_engine()
    fixture = _seed_fixture(engine)

    from fastapi.testclient import TestClient

    from world_engine.cockpit.app import app
    from world_engine.cockpit.routes import scene as _routes_scene
    from world_engine.models import Conversation, GatheringMember
    from world_engine.cockpit.play import ResponseMode

    client = TestClient(app)

    # ── 4. Both / neither -> 422 ────────────────────────────────────────
    resp = client.post("/api/scene/join", json={"player_id": fixture["player_id"]})
    if resp.status_code != 422:
        fail(f"neither field set: expected 422, got {resp.status_code}: {resp.text}")

    resp = client.post("/api/scene/join", json={
        "player_id": fixture["player_id"], "player_text": "x",
        "target_gathering_id": fixture["gathering_id"],
    })
    if resp.status_code != 422:
        fail(f"both fields set: expected 422, got {resp.status_code}: {resp.text}")

    # ── 2. Closed gathering -> 404, zero rows written ───────────────────
    conv_before = _count_rows(engine, Conversation)
    gm_before = _count_rows(engine, GatheringMember)

    def _interpret_forbidden(*_a, **_k):
        fail("_interpret_mode was called for a targeted join — G2-b forbids this")
        raise AssertionError("should not be reached")

    _routes_scene._interpret_mode = _interpret_forbidden

    resp = client.post("/api/scene/join", json={
        "player_id": fixture["player_id"],
        "target_gathering_id": fixture["closed_gathering_id"],
    })
    if resp.status_code != 404:
        fail(f"closed gathering: expected 404, got {resp.status_code}: {resp.text}")
    if _count_rows(engine, Conversation) != conv_before or _count_rows(engine, GatheringMember) != gm_before:
        fail("closed gathering: rows were written despite rejection")

    # ── 3. Wrong location -> 400, zero rows written ─────────────────────
    resp = client.post("/api/scene/join", json={
        "player_id": fixture["player_id"],
        "target_gathering_id": fixture["other_gathering_id"],
    })
    if resp.status_code != 400:
        fail(f"wrong-location gathering: expected 400, got {resp.status_code}: {resp.text}")
    if _count_rows(engine, Conversation) != conv_before or _count_rows(engine, GatheringMember) != gm_before:
        fail("wrong-location gathering: rows were written despite rejection")

    # ── 1. Targeted join succeeds, zero model calls ─────────────────────
    resp = client.post("/api/scene/join", json={
        "player_id": fixture["player_id"],
        "target_gathering_id": fixture["gathering_id"],
    })
    if resp.status_code != 200:
        fail(f"targeted join: expected 200, got {resp.status_code}: {resp.text}")
    else:
        body = resp.json()
        if "conversation_id" not in body or body.get("gathering", {}).get("id") != fixture["gathering_id"]:
            fail(f"targeted join: unexpected response shape: {body}")
        from sqlmodel import Session as DbSession
        with DbSession(engine) as session:
            conv = session.get(Conversation, body["conversation_id"])
            if conv is None:
                fail("targeted join: conversation row not found")
            elif conv.gathering_id != fixture["gathering_id"]:
                fail(f"targeted join: conversation.gathering_id={conv.gathering_id!r}, expected {fixture['gathering_id']!r}")
            gm = session.exec(
                __import__("sqlmodel").select(GatheringMember).where(
                    GatheringMember.gathering_id == fixture["gathering_id"],
                    GatheringMember.entity_id == fixture["player_id"],
                )
            ).first()
            if gm is None:
                fail("targeted join: no gathering_member row inserted for the player")
    # Leave the player's gathering so the free-text check below hits the
    # resolve-and-create path instead of the already-a-member short-circuit.
    with __import__("sqlmodel").Session(engine) as session:
        gm = session.exec(
            __import__("sqlmodel").select(GatheringMember).where(
                GatheringMember.gathering_id == fixture["gathering_id"],
                GatheringMember.entity_id == fixture["player_id"],
            )
        ).first()
        if gm:
            gm.left_at = datetime.now(UTC)
            session.add(gm)
            session.commit()
        conv = session.get(Conversation, resp.json().get("conversation_id")) if resp.status_code == 200 else None
        if conv is not None:
            conv.status = "closed"
            session.add(conv)
            session.commit()

    # ── 5. Free-text regression: interpreter IS called ──────────────────
    calls: list[str] = []

    def _interpret_stub(*, player_line, npc_name, **_k):
        calls.append(player_line)
        return ResponseMode.join, fixture["npc_name"], None

    _routes_scene._interpret_mode = _interpret_stub

    resp = client.post("/api/scene/join", json={
        "player_id": fixture["player_id"],
        "player_text": f"je rejoins {fixture['npc_name']}",
    })
    if not calls:
        fail("free-text join: _interpret_mode was not called — regression")
    if resp.status_code != 200:
        fail(f"free-text join: expected 200, got {resp.status_code}: {resp.text}")
    else:
        body = resp.json()
        if "conversation_id" not in body or "gathering" not in body:
            fail(f"free-text join: unexpected response shape: {body}")


def main() -> int:
    check_targeted_and_free_text_join()

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: scene/join targeted join — success/closed/wrong-location/422, "
        "zero model calls, free-text regression intact"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
