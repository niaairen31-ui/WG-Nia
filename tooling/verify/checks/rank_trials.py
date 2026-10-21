"""G1 check for TICKET-0116 -- a rank that asks a trial is earned by a quest.

Each brief of the lot adds its rules here in the same commit (the
`quest_rewards.py` precedent).

BRIEF-0116-B's rules (B1, A1, C1: the cascade, « ready », and the points
that stop at a waiting threshold):

TB1 -- the cascade (fixture). A world with no `skill_rank` row: `world_ladder`
   gives `trial_to_next` False at every rank. `upsert_skill_rank(rank=3,
   trial_to_next=True)` -> `world_ladder(...)[3].trial_to_next` True;
   `trial_required(3, ladder)` True; with a system whose `trial_to_rank_4` is
   False, False; with a definition of that system whose `trial_to_rank_4` is
   True, True; `trial_required(5, ...)` False. With the default points (40 to
   leave rank 3): `trial_target(3, 39, ...)` None, `trial_target(3, 40, ...)`
   4. `upsert_skill_rank(rank=5, trial_to_next=True)` and
   `trial_to_next="yes"` raise `ValueError`, no row written.
   `held_trial_target` of a character with no row for the key is None.
TB2 -- the CRUD (fixture; the route functions called with the session).
   `update_skill_ranks` with rank 5 `trial_to_next` True -> 422 and no
   `skill_rank` row written; with rank 3 `trial_to_next` True serves it.
   `create_skill_system` with `trial_to_rank_4=False` serves it;
   `update_skill_system` without it serves None. The same for
   `create_skill_definition` / `update_skill_definition`. `list_skills`
   serves `trial_ready` True for a waiting row, False for another.
TB3 -- the waiting threshold (fixture; a world whose rank 1 asks a trial --
   10 points to leave it --, a player character). A base `agility` row at
   rank 1, 9 points: `write_skill_progress(+1)` -> rank 1, 10 points,
   `awaiting_trial` True, no `change_history` entry; `+1` again -> rank 1,
   10 points, `awaiting_trial` True; `-1` -> rank 1, 9 points,
   `awaiting_trial` False. In a second world with no trial, the same row at 9
   points `+1` -> rank 2, 0 points. The waiting row: `held_trial_target` is
   2; `record_roll` returns None and no `skill_progress` mutation is written;
   `grant_step_roll` for an `agility` step leaves it at 10;
   `skill_reward_points` is None; `_skill_note` reads « épreuve de rang à
   passer en « agility » : rien » (a Maître row still reads « déjà Maître en
   « agility » : rien »).

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[3]

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> None:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))


# --- fixture ---------------------------------------------------------------------

def _world(session, name: str, *, active: bool = False) -> dict:
    """A world with one player character (and its game session and
    conversation); `active` deactivates every other world first."""
    from sqlmodel import select

    from world_engine.models import Character, Conversation, Entity, World
    from world_engine.models import Session as GameSession

    if active:
        for other in session.exec(select(World)).all():
            other.is_active = False
            session.add(other)
    world = World(name=name, is_active=active)
    session.add(world)
    session.flush()
    pc = Entity(world_id=world.id, type="character", name=f"PC {name}")
    session.add(pc)
    session.flush()
    session.add(Character(id=pc.id, world_id=world.id, character_type="player"))
    game = GameSession(world_id=world.id, number=1)
    session.add(game)
    session.flush()
    conv = Conversation(world_id=world.id, session_id=game.id, player_id=pc.id)
    session.add(conv)
    session.commit()
    return {"world": world.id, "pc": pc.id, "conv": conv.id}


# --- TB1 -------------------------------------------------------------------------

def check_tb1(engine) -> None:
    from sqlmodel import Session, select

    from world_engine.models import SkillDefinition, SkillRank, SkillSystem
    from world_engine.skill_access import held_trial_target
    from world_engine.skill_ranks import trial_required, trial_target, world_ladder
    from world_engine.writes import upsert_skill_rank

    with Session(engine) as session:
        ids = _world(session, "Trials TB1")
        bare = world_ladder(session, ids["world"])
        if len(bare) != 6 or any(step.trial_to_next for step in bare):
            fail(f"TB1: a world with no skill_rank row reads {[s.trial_to_next for s in bare]}")
        upsert_skill_rank(session, world_id=ids["world"], rank=3, label="Confirmé", points_to_next=40,
                          trial_to_next=True)
        session.commit()
        ladder = world_ladder(session, ids["world"])
        if not ladder[3].trial_to_next:
            fail("TB1: world_ladder does not read the stored trial_to_next of rank 3")
        system = SkillSystem(world_id=ids["world"], name="Lame", trial_to_rank_4=False)
        definition = SkillDefinition(world_id=ids["world"], name="Escrime", base_domain="physical",
                                     trial_to_rank_4=True)
        cases = (
            ("the world", trial_required(3, ladder), True),
            ("the system over the world", trial_required(3, ladder, system=system), False),
            ("the definition over its system", trial_required(3, ladder, system=system, definition=definition), True),
            ("the top rank", trial_required(5, ladder), False),
            ("39 points", trial_target(3, 39, ladder), None),
            ("40 points", trial_target(3, 40, ladder), 4),
        )
        for label, got, want in cases:
            if got != want:
                fail(f"TB1: {label} gave {got!r}, want {want!r}")
        for rank, label, points, trial in ((5, "Maître", None, True), (2, "Apprenti", 20, "yes")):
            try:
                upsert_skill_rank(session, world_id=ids["world"], rank=rank, label=label, points_to_next=points,
                                  trial_to_next=trial)
                fail(f"TB1: upsert_skill_rank accepted rank {rank} with trial_to_next {trial!r}")
            except ValueError:
                pass
        session.rollback()
        ranks = sorted(r.rank for r in session.exec(select(SkillRank).where(SkillRank.world_id == ids["world"])).all())
        if ranks != [3]:
            fail(f"TB1: the refused upserts left the ranks {ranks}")
        got = held_trial_target(session, world_id=ids["world"], character_id=ids["pc"], skill_key="agility")
        if got is not None:
            fail(f"TB1: held_trial_target with no row gave {got!r}")


# --- TB2 -------------------------------------------------------------------------

def check_tb2(engine) -> None:
    from fastapi import HTTPException
    from sqlmodel import Session, select

    from world_engine.cockpit.crud.skills import (
        SkillDefinitionWriteBody, SkillRanksBody, SkillSystemWriteBody, create_skill_definition,
        create_skill_system, list_skills, update_skill_definition, update_skill_ranks, update_skill_system,
    )
    from world_engine.models import Skill, SkillRank

    with Session(engine) as session:
        ids = _world(session, "Trials TB2", active=True)

        def steps(trial_rank: int) -> list[dict]:
            return [{"rank": r, "label": f"R{r}", "points_to_next": None if r == 5 else 10 + r,
                     "trial_to_next": r == trial_rank} for r in range(6)]

        try:
            update_skill_ranks(SkillRanksBody(ranks=steps(5)), session)
            fail("TB2: the PUT accepted a trial at rank 5")
        except HTTPException as exc:
            if exc.status_code != 422:
                fail(f"TB2: the PUT of a rank-5 trial answered {exc.status_code}")
        if session.exec(select(SkillRank).where(SkillRank.world_id == ids["world"])).all():
            fail("TB2: a refused PUT wrote skill_rank rows")
        served = update_skill_ranks(SkillRanksBody(ranks=steps(3)), session)
        if [s.get("trial_to_next") for s in served] != [False, False, False, True, False, False]:
            fail(f"TB2: the PUT served {served}")

        system = create_skill_system(SkillSystemWriteBody(name="Épée", trial_to_rank_4=False), session)
        if system.get("trial_to_rank_4") is not False or system.get("trial_to_rank_1") is not None:
            fail(f"TB2: the system was served {system}")
        cleared = update_skill_system(system["id"], SkillSystemWriteBody(name="Épée"), session)
        if cleared.get("trial_to_rank_4") is not None:
            fail(f"TB2: a system PUT without trials served {cleared}")
        definition = create_skill_definition(SkillDefinitionWriteBody(
            name="Rapière", base_domain="agility", system_id=system["id"], trial_to_rank_4=False), session)
        if definition.get("trial_to_rank_4") is not False:
            fail(f"TB2: the definition was served {definition}")
        cleared = update_skill_definition(definition["id"], SkillDefinitionWriteBody(
            name="Rapière", base_domain="agility", system_id=system["id"]), session)
        if cleared.get("trial_to_rank_4") is not None:
            fail(f"TB2: a definition PUT without trials served {cleared}")

        waiting = Skill(character_id=ids["pc"], domain="physical", rank=3, xp=13)
        other = Skill(character_id=ids["pc"], domain="perception", rank=2, xp=0)
        session.add(waiting)
        session.add(other)
        session.commit()
        sheet = {row["id"]: row for row in list_skills(character_id=ids["pc"], db=session)}
        if (sheet.get(waiting.id, {}).get("trial_ready"), sheet.get(other.id, {}).get("trial_ready")) != (True, False):
            fail(f"TB2: list_skills served trial_ready {[(r['domain'], r.get('trial_ready')) for r in sheet.values()]}")


# --- TB3 -------------------------------------------------------------------------

def check_tb3(engine) -> None:
    from sqlmodel import Session, select

    from world_engine.cockpit.skill_progress import grant_step_roll, record_roll
    from world_engine.models import ProposedMutation, Skill
    from world_engine.quest_settlement_view import _skill_note
    from world_engine.skill_access import held_trial_target
    from world_engine.writes import upsert_skill_rank, write_skill_progress
    from world_engine.writes.quest_settlement import skill_reward_points

    with Session(engine) as session:
        ids = _world(session, "Trials TB3")
        plain = _world(session, "Trials TB3 plain")
        upsert_skill_rank(session, world_id=ids["world"], rank=1, label="Initié", points_to_next=10,
                          trial_to_next=True)
        row = Skill(character_id=ids["pc"], domain="agility", rank=1, xp=9)
        plain_row = Skill(character_id=plain["pc"], domain="agility", rank=1, xp=9)
        session.add(row)
        session.add(plain_row)
        session.commit()

        def step(skill_id: str, world_id: str, points: int) -> tuple:
            progress = write_skill_progress(session, skill_id=skill_id, world_id=world_id, points=points,
                                            changed_by="check")
            session.commit()
            got = session.get(Skill, skill_id)
            return got.rank, got.xp, progress.awaiting_trial, len(got.change_history or [])

        table = ((row.id, ids["world"], 1, (1, 10, True, 0)), (row.id, ids["world"], 1, (1, 10, True, 0)),
                 (row.id, ids["world"], -1, (1, 9, False, 0)), (plain_row.id, plain["world"], 1, (2, 0, False, 1)))
        for skill_id, world_id, points, want in table:
            got = step(skill_id, world_id, points)
            if got != want:
                fail(f"TB3: {points:+d} gave (rank, xp, awaiting_trial, history) {got}, want {want}")
        step(row.id, ids["world"], 1)
        target = held_trial_target(session, world_id=ids["world"], character_id=ids["pc"], skill_key="agility")
        if target != 2:
            fail(f"TB3: held_trial_target of the waiting row gave {target!r}")
        master = _world(session, "Trials TB3 master")
        upsert_skill_rank(session, world_id=master["world"], rank=1, label="Initié", points_to_next=10,
                          trial_to_next=True)
        session.add(Skill(character_id=master["pc"], domain="agility", rank=5, xp=0))
        session.commit()
        row_id = row.id

    got = record_roll(world_id=ids["world"], conversation_id=ids["conv"], skill_id=row_id, band="success")
    with Session(engine) as session:
        written = session.exec(select(ProposedMutation).where(
            ProposedMutation.mutation_type == "skill_progress", ProposedMutation.world_id == ids["world"])).all()
        if got is not None or written:
            fail(f"TB3: record_roll on a waiting row returned {got} and wrote {len(written)} mutation(s)")
        grant_step_roll(session, step=SimpleNamespace(domain="agility"), owner_id=ids["pc"], world_id=ids["world"],
                        mutation_id="check")
        session.commit()
        waiting = session.get(Skill, row_id)
        if (waiting.rank, waiting.xp) != (1, 10):
            fail(f"TB3: grant_step_roll moved the waiting row to {(waiting.rank, waiting.xp)}")
        points = skill_reward_points(session, ids["world"], waiting)
        if points is not None:
            fail(f"TB3: skill_reward_points of a waiting row gave {points!r}")
        term = SimpleNamespace(skill_key="agility")
        for who, want in ((ids, "épreuve de rang à passer en « agility » : rien"),
                          (master, "déjà Maître en « agility » : rien")):
            note = _skill_note(session, SimpleNamespace(character_id=who["pc"], world_id=who["world"]), term)
            if note != want:
                fail(f"TB3: _skill_note read {note!r}, want {want!r}")


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine
    create_db_and_tables()
    check_tb1(engine)
    check_tb2(engine)
    check_tb3(engine)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: rank_trials -- whether leaving a rank asks a trial follows the points' cascade, "
          "a skill is ready when its points reached such a threshold, the points stop there and "
          "the rolls and the point reward skip a waiting skill, and the creator's CRUD carries the flags")
    return 0


if __name__ == "__main__":
    sys.exit(main())
