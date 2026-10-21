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

BRIEF-0116-C's rules (D2, C-05, C-06: the `rank` currency, a reward only,
given to who is ready, and the trial gate). INV-64's full law is TB3 with
TC1-TC4:

TC1 -- the writer (fixture). `clean_term` of a reward `rank` on `agility`,
   amount 2, gives exactly C-05's row; it refuses, each with C-05's message:
   a cost, a counterparty, the skill `flying`, amounts 0, 6, None and True.
   `write_quest_offer` with that reward writes it; `accept_quest` copies it
   to `quest_term`. `request_service` with a `rank` reward raises C-05's
   message and writes no `debt`, `ledger` or `skill` row.
TC2 -- the gate (fixture: a world whose rank 1 asks a trial; an offer whose
   reward is `rank` agility 2; player A at agility rank 1 with 10 points --
   ready --, B at rank 1 with 5, C ready in `perception` only).
   `available_offers(A)` holds the offer, `(B)` and `(C)` do not;
   `accept_quest` for B raises « cette épreuve est réservée à qui est prêt
   à passer « Apprenti » en « agility » », nothing written; for A it
   accepts.
TC3 -- the settlement (fixture, continued). Before settling,
   `settlement_context` gives A's `rank` term the note « passe à « Apprenti »
   en « agility » » and the line « Passer au rang « Apprenti » en « agility »
   (épreuve) »; `settle_quest` -> A's agility at rank 2, 0 points, the last
   `change_history` entry `by` `quest_settlement`. D, ready like A,
   accepts; the creator sets D's agility to rank 2 (`write_skill_rank`); D's
   note reads « sans effet : la compétence n'est pas prête pour ce rang »;
   `settle_quest` succeeds and D stays at rank 2 with one history entry.
   `term_value` of a `rank` term is 0; `editor_choices(world)["ranks"]`
   lists ranks 1-5 with the world's labels; `quest_designer._term` of a
   `rank` reward returns `(None, RANK_TERM_FR)`.
TC4 -- static. `QUEST_TERM_CURRENCIES[-1] == "rank"`; `questTerms.js` holds
   the `rank` line verbatim and `export const REWARD_ONLY_CURRENCIES =
   ['rank'];`; `QuestTermRow.svelte` names `REWARD_ONLY_CURRENCIES` and
   `choices?.ranks`; the built bundle carries « Rang (épreuve) »;
   `.claude/rules/skills.md` holds INV-64 ending « -- enforced by
   `rank_trials.py` » and the three new `paths:`.

BRIEF-0116-D's rules (F1, F1-a, C-07: a skill ready for its trial asks the
creator for one):

TD1 -- the opening (fixture: a world whose rank 1 asks a trial; player
   characters P, Q, R, S; an NPC N; each with a base `agility` row at rank 1,
   9 points). N `+1` -> no request (first, so no live request masks it);
   `write_skill_progress(P, +1)` -> exactly one `quest_request`:
   trigger `trial`, `skill_key` `agility`, `target_rank` 2, status `new`,
   `pass_play_id` and `agenda_step_id` None, `declaration` « P a assez
   pratiqué « agility » pour passer de Initié à Apprenti : ce rang demande une
   épreuve. », `subject` « Épreuve de rang : « agility » vers Apprenti »; P
   `+1` again -> still one; Q `+1` -> still one, the same
   row (live). That request moved to `dropped`: R `+1` -> a second request,
   `new`. An open offer whose reward is `rank` agility 2 written through
   `write_quest_offer`: S `+1` -> no new request; `covering_trial_offer(db,
   world, "agility", 2)` is that offer; `(…, "agility", 3)` and
   `(…, "perception", 2)` are None.
TD2 -- the edges. `open_request(trigger="trial", ...)` raises C-07's message;
   `open_trial_request` raises on `target_rank` 6 and on an empty
   `skill_key`; `request_dict` of a trial request gives `day_number` None and
   `trigger` `trial` without raising or warning; `compute_metrics` over the fixture holds
   the row (« Origine », « Épreuve de rang », 2, 2).

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import warnings
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


# --- TC fixture ------------------------------------------------------------------

def _player(session, world_id: str, name: str, skills: tuple = ()) -> str:
    """A player character of `world_id` holding `skills` -- (domain, rank, xp)."""
    from world_engine.models import Character, Entity, Skill

    entity = Entity(world_id=world_id, type="character", name=name)
    session.add(entity)
    session.flush()
    session.add(Character(id=entity.id, world_id=world_id, character_type="player"))
    for domain, rank, xp in skills:
        session.add(Skill(character_id=entity.id, domain=domain, rank=rank, xp=xp))
    session.commit()
    return entity.id


def _trial_world(session, name: str) -> dict:
    """A world whose rank 1 asks a trial (10 points to leave it), an NPC
    giver, and an offer whose one reward is `rank` agility 2."""
    from world_engine.day_plan import PlanStep
    from world_engine.models import Character, Entity
    from world_engine.writes import TermSpec, upsert_skill_rank, write_quest_offer

    ids = _world(session, name)
    upsert_skill_rank(session, world_id=ids["world"], rank=1, label="Initié", points_to_next=10, trial_to_next=True)
    npc = Entity(world_id=ids["world"], type="character", name=f"Maître d'armes {name}")
    session.add(npc)
    session.flush()
    session.add(Character(id=npc.id, world_id=ids["world"], character_type="npc"))
    session.flush()
    offer = write_quest_offer(
        session, world_id=ids["world"], offer=None, giver_entity_id=npc.id, title="L'épreuve d'agilité",
        summary=None, repeatable=False, status="open", eligibility=None,
        steps=[PlanStep(objective="Franchir le gué", cost=1, domain=None)],
        terms=[TermSpec(direction="reward", currency="rank", skill_key="agility", amount=2)])
    session.commit()
    return {**ids, "npc": npc.id, "offer": offer.id}


def _counts(session) -> tuple:
    from sqlmodel import func, select

    from world_engine.models import Debt, Ledger, Skill

    return tuple(session.exec(select(func.count()).select_from(model)).one() for model in (Debt, Ledger, Skill))


# --- TC1 -------------------------------------------------------------------------

RANK_REFUSAL = "term 1: a rank reward names the rank it gives, 1 to 5"


def check_tc1(engine) -> None:
    from sqlmodel import Session, select

    from world_engine.models import Character, QuestOffer, QuestOfferTerm, QuestTerm
    from world_engine.writes import TermSpec, accept_quest
    from world_engine.writes.quest_terms import clean_term

    with Session(engine) as session:
        ids = _trial_world(session, "Trials TC1")
        world = ids["world"]

        def rank(**over) -> TermSpec:
            return TermSpec(**{"direction": "reward", "currency": "rank", "skill_key": "agility", "amount": 2,
                               **over})

        want = {"direction": "reward", "currency": "rank", "counterparty_entity_id": None, "item_id": None,
                "fact_id": None, "skill_key": "agility", "amount": 2, "level": None}
        got = clean_term(session, world, ids["npc"], 0, rank())
        if got != want:
            fail(f"TC1: clean_term of a rank reward gave {got}")
        refusals = (
            (rank(direction="cost"), "term 1: a rank is a reward only -- a rank trial gives it"),
            (rank(counterparty_entity_id=ids["npc"]), "term 1: a rank reward names no counterparty"),
            (rank(skill_key="flying"), "term 1: 'flying' is not a skill of this world"),
            *((rank(amount=amount), RANK_REFUSAL) for amount in (0, 6, None, True)),
        )
        for term, message in refusals:
            try:
                clean_term(session, world, ids["npc"], 0, term)
                fail(f"TC1: clean_term accepted {term}")
            except ValueError as exc:
                if str(exc) != message:
                    fail(f"TC1: clean_term refused {term} with {exc!s}, want {message!r}")
        written = session.exec(select(QuestOfferTerm).where(QuestOfferTerm.offer_id == ids["offer"])).all()
        if [(t.currency, t.skill_key, t.amount) for t in written] != [("rank", "agility", 2)]:
            fail(f"TC1: write_quest_offer wrote {[(t.currency, t.skill_key, t.amount) for t in written]}")
        ready = _player(session, world, "Prête TC1", (("agility", 1, 10),))
        quest = accept_quest(session, offer=session.get(QuestOffer, ids["offer"]),
                             character=session.get(Character, ready))
        session.commit()
        copied = session.exec(select(QuestTerm).where(QuestTerm.quest_id == quest.id)).all()
        if [(t.currency, t.skill_key, t.amount) for t in copied] != [("rank", "agility", 2)]:
            fail(f"TC1: accept_quest copied {[(t.currency, t.skill_key, t.amount) for t in copied]}")
        _tc1_service(session, ids, ready, rank())


def _tc1_service(session, ids: dict, character_id: str, reward) -> None:
    from world_engine.models import Character
    from world_engine.writes import request_service

    before = _counts(session)
    try:
        request_service(session, character=session.get(Character, character_id), provider_id=ids["npc"],
                        on_behalf_of_id=None, terms=[reward], owed=[], reason="une épreuve", is_secret=False)
        fail("TC1: request_service accepted a rank reward")
    except ValueError as exc:
        if str(exc) != "request_service: a rank is given by a rank trial, never by a service":
            fail(f"TC1: request_service refused a rank with {exc!s}")
    session.rollback()
    if _counts(session) != before:
        fail(f"TC1: a refused service moved (debt, ledger, skill) from {before} to {_counts(session)}")


# --- TC2 / TC3 -------------------------------------------------------------------

def check_tc2_tc3(engine) -> None:
    from sqlmodel import Session

    from world_engine.models import Character
    from world_engine.quest_reads import available_offers

    with Session(engine) as session:
        ids = _trial_world(session, "Trials TC2")
        world = ids["world"]
        players = {name: _player(session, world, f"{name} TC2", skills) for name, skills in (
            ("A", (("agility", 1, 10),)), ("B", (("agility", 1, 5),)),
            ("C", (("agility", 1, 5), ("perception", 1, 10))), ("D", (("agility", 1, 10),)))}
        for name, want in (("A", True), ("B", False), ("C", False)):
            listed = ids["offer"] in {o.id for o in available_offers(session.get(Character, players[name]), session)}
            if listed != want:
                fail(f"TC2: available_offers({name}) {'holds' if listed else 'lacks'} the trial")
        _tc2_accept(session, ids, players)
        _tc3_settle(session, ids, players)
        _tc3_readers(session, world)


def _tc2_accept(session, ids: dict, players: dict) -> None:
    from world_engine.models import Character, QuestOffer
    from world_engine.writes import accept_quest

    offer = session.get(QuestOffer, ids["offer"])
    before = _counts(session)
    try:
        accept_quest(session, offer=offer, character=session.get(Character, players["B"]))
        fail("TC2: accept_quest accepted B, not ready")
    except ValueError as exc:
        want = "cette épreuve est réservée à qui est prêt à passer « Apprenti » en « agility »"
        if str(exc) != want:
            fail(f"TC2: accept_quest refused B with {exc!s}")
    session.rollback()
    if _counts(session) != before:
        fail("TC2: a refused acceptance wrote rows")
    for name in ("A", "D"):
        ids[f"quest_{name}"] = accept_quest(session, offer=offer, character=session.get(Character, players[name])).id
    session.commit()


def _tc3_settle(session, ids: dict, players: dict) -> None:
    from world_engine.models import Quest
    from world_engine.quest_settlement_view import settlement_context
    from world_engine.writes import write_skill_rank
    from world_engine.writes.quest_settlement import settle_quest, skill_row

    seen = settlement_context(session, session.get(Quest, ids["quest_A"]))["terms"]
    want = [{"direction": "reward", "line": "Passer au rang « Apprenti » en « agility » (épreuve)",
             "note": "passe à « Apprenti » en « agility »"}]
    if seen != want:
        fail(f"TC3: A's settlement shows {seen}")
    settle_quest(session, quest=session.get(Quest, ids["quest_A"]))
    session.commit()
    row = skill_row(session, players["A"], "agility")
    if (row.rank, row.xp, (row.change_history or [{}])[-1].get("by")) != (2, 0, "quest_settlement"):
        fail(f"TC3: A's agility after settling is {(row.rank, row.xp, row.change_history)}")
    d_row = skill_row(session, players["D"], "agility")
    write_skill_rank(session, skill_id=d_row.id, rank=2, changed_by="creator")
    session.commit()
    note = settlement_context(session, session.get(Quest, ids["quest_D"]))["terms"][0]["note"]
    if note != "sans effet : la compétence n'est pas prête pour ce rang":
        fail(f"TC3: D's note reads {note!r}")
    settle_quest(session, quest=session.get(Quest, ids["quest_D"]))
    session.commit()
    d_row = skill_row(session, players["D"], "agility")
    if (d_row.rank, len(d_row.change_history or [])) != (2, 1):
        fail(f"TC3: D after settling is at rank {d_row.rank} with {len(d_row.change_history or [])} history entries")


def _tc3_readers(session, world: str) -> None:
    from world_engine.quest_designer import RANK_TERM_FR, _term
    from world_engine.quest_reads import editor_choices
    from world_engine.quest_value import term_value, world_rates

    value = term_value(session, SimpleNamespace(currency="rank", amount=2, item_id=None), world_rates(session, world))
    if value != 0:
        fail(f"TC3: term_value of a rank term is {value}")
    ranks = editor_choices(world, session)["ranks"]
    labels = ("Initié", "Apprenti", "Confirmé", "Expert", "Maître")
    if ranks != [{"rank": r, "label": label} for r, label in enumerate(labels, start=1)]:
        fail(f"TC3: editor_choices serves the ranks {ranks}")
    got = _term(session, world, None, {"direction": "reward", "currency": "rank", "target": "s1", "amount": 2,
                                       "level": None})
    if got != (None, RANK_TERM_FR):
        fail(f"TC3: the designer's _term of a rank reward gave {got}")


# --- TC4 -------------------------------------------------------------------------

TC4_NEEDLES: tuple[tuple[str, str], ...] = (
    ("questTerms.js", "\n  rank: { label: 'Rang (épreuve)', list: 'skills', counted: false, personal: false },\n"),
    ("questTerms.js", "export const REWARD_ONLY_CURRENCIES = ['rank'];"),
    ("QuestTermRow.svelte", "REWARD_ONLY_CURRENCIES"),
    ("QuestTermRow.svelte", "choices?.ranks"),
    ("skills.md", "- **INV-64** "),
    ("skills.md", "  -- enforced by `rank_trials.py`"),
    ("skills.md", '  - "src/world_engine/writes/characters.py"'),
    ("skills.md", '  - "src/world_engine/writes/quest_settlement.py"'),
    ("skills.md", '  - "src/world_engine/writes/quests.py"'),
)


def check_tc4() -> None:
    from world_engine.models import QUEST_TERM_CURRENCIES

    if QUEST_TERM_CURRENCIES[-1:] != ("rank",):
        fail(f"TC4: QUEST_TERM_CURRENCIES is {QUEST_TERM_CURRENCIES}")
    creation = ROOT / "frontend" / "src" / "creation"
    texts = {}
    for path in (creation / "questTerms.js", creation / "QuestTermRow.svelte", ROOT / ".claude" / "rules" / "skills.md"):
        try:
            texts[path.name] = path.read_text(encoding="utf-8")
        except OSError as exc:
            fail(f"TC4: cannot read {path}: {exc}")
            return
    for name, needle in TC4_NEEDLES:
        if needle not in texts[name]:
            fail(f"TC4: {name} lacks {needle.strip()!r}")
    bundles = list((ROOT / "src" / "world_engine" / "cockpit" / "static" / "assets").glob("*.js"))
    if not bundles:
        fail("TC4: no built bundle under cockpit/static/assets")
    elif not any("Rang (épreuve)" in b.read_text(encoding="utf-8") for b in bundles):
        fail("TC4: the built bundle does not carry « Rang (épreuve) » -- rebuild the frontend")


# --- TD1 / TD2 -------------------------------------------------------------------

def _trial_requests(session, world_id: str) -> list:
    from sqlmodel import select

    from world_engine.models import QuestRequest

    return list(session.exec(select(QuestRequest).where(QuestRequest.world_id == world_id)
                             .order_by(QuestRequest.created_at, QuestRequest.id)).all())


def check_td1_td2(engine) -> None:
    from sqlmodel import Session, select

    from world_engine.models import Character, Entity, Skill
    from world_engine.writes import upsert_skill_rank, write_skill_progress

    with Session(engine) as session:
        ids = _world(session, "Trials TD")
        world = ids["world"]
        upsert_skill_rank(session, world_id=world, rank=1, label="Initié", points_to_next=10, trial_to_next=True)
        who = {name: _player(session, world, name, (("agility", 1, 9),)) for name in "PQRS"}
        npc = Entity(world_id=world, type="character", name="N")
        session.add(npc)
        session.flush()
        session.add(Character(id=npc.id, world_id=world, character_type="npc"))
        session.add(Skill(character_id=npc.id, domain="agility", rank=1, xp=9))
        session.commit()
        who["N"] = npc.id

        def gain(name: str) -> list:
            row = session.exec(select(Skill).where(Skill.character_id == who[name], Skill.domain == "agility")).one()
            write_skill_progress(session, skill_id=row.id, world_id=world, points=1, changed_by="check")
            session.commit()
            return _trial_requests(session, world)

        _td1_opening(session, ids, gain)
        _td2_edges(session, ids, who)


def _td1_opening(session, ids: dict, gain) -> None:
    from world_engine.day_plan import PlanStep
    from world_engine.models import QuestRequest
    from world_engine.quest_requests import covering_trial_offer
    from world_engine.writes import TermSpec, write_quest_offer
    from world_engine.writes.quest_requests import move_request

    world = ids["world"]
    # N first: behind P's live request, an NPC's opening would be masked.
    if gain("N"):
        fail("TD1: the NPC N opened a trial request")
    got = gain("P")
    want =("trial", "agility", 2, "new", None, None,
            "P a assez pratiqué « agility » pour passer de Initié à Apprenti : ce rang demande une épreuve.",
            "Épreuve de rang : « agility » vers Apprenti")
    shape = [(r.trigger, r.skill_key, r.target_rank, r.status, r.pass_play_id, r.agenda_step_id, r.declaration,
              r.subject) for r in got]
    if shape != [want]:
        fail(f"TD1: P's readiness opened {shape}")
        return
    first = got[0].id
    for name in ("P", "Q"):
        now = [r.id for r in gain(name)]
        if now != [first]:
            fail(f"TD1: {name} +1 left the requests {now}, want the one live request")
    move_request(session, session.get(QuestRequest, first), "dropped")
    session.commit()
    got = gain("R")
    if len(got) != 2 or got[-1].id == first or got[-1].status != "new":
        fail(f"TD1: R after a dropped request left {[(r.id == first, r.status) for r in got]}")
    offer = write_quest_offer(
        session, world_id=world, offer=None, giver_entity_id=ids["pc"], title="L'épreuve du gué",
        summary=None, repeatable=False, status="open", eligibility=None,
        steps=[PlanStep(objective="Franchir le gué", cost=1, domain=None)],
        terms=[TermSpec(direction="reward", currency="rank", skill_key="agility", amount=2)])
    session.commit()
    if len(gain("S")) != 2:
        fail("TD1: S opened a request while an open offer gives the rank")
    found = covering_trial_offer(session, world, "agility", 2)
    if found is None or found.id != offer.id:
        fail(f"TD1: covering_trial_offer(agility, 2) gave {found}")
    for key, rank in (("agility", 3), ("perception", 2)):
        if covering_trial_offer(session, world, key, rank) is not None:
            fail(f"TD1: covering_trial_offer({key}, {rank}) found an offer")


def _td2_edges(session, ids: dict, who: dict) -> None:
    from world_engine.dashboard_metrics import Scope, compute_metrics
    from world_engine.quest_requests import request_dict
    from world_engine.writes.quest_requests import open_request, open_trial_request

    world = ids["world"]
    try:
        open_request(session, world_id=world, character_id=who["P"], pass_play_id="x", trigger="trial",
                     declaration="d", agenda_step_id="x")
        fail("TD2: open_request accepted a trial")
    except ValueError as exc:
        if str(exc) != "quest_request: a trial request opens through open_trial_request":
            fail(f"TD2: open_request refused a trial with {exc!s}")
    for key, rank in (("agility", 6), ("", 2)):
        try:
            open_trial_request(session, world_id=world, character_id=who["P"], skill_key=key, target_rank=rank)
            fail(f"TD2: open_trial_request accepted ({key!r}, {rank})")
        except ValueError:
            pass
    session.rollback()
    requests = _trial_requests(session, world)
    try:
        # A get by a NULL key only warns today (SAWarning) and may raise tomorrow: either fails.
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            shown = request_dict(requests[0], session) if requests else None
        if shown is None or (shown["day_number"], shown["trigger"]) != (None, "trial"):
            fail(f"TD2: request_dict of a trial request gave {shown}")
    except Exception as exc:  # noqa: BLE001 -- the rule is « without raising »
        fail(f"TD2: request_dict of a trial request raised {exc!r}")
    out = compute_metrics(session, Scope(world_ids=(world,)))
    metric = next((m for m in out if m["key"] == "quest_requests"), None)
    rows = [(r["group"], r["label"], r["value"], r["of"]) for r in (metric or {}).get("rows", [])]
    if ("Origine", "Épreuve de rang", 2, 2) not in rows:
        fail(f"TD2: the quest_requests metric rows are {rows}")


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine
    create_db_and_tables()
    check_tb1(engine)
    check_tb2(engine)
    check_tb3(engine)
    check_tc1(engine)
    check_tc2_tc3(engine)
    check_tc4()
    check_td1_td2(engine)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: rank_trials -- whether leaving a rank asks a trial follows the points' cascade, "
          "a skill is ready when its points reached such a threshold, the points stop there and "
          "the rolls and the point reward skip a waiting skill, the creator's CRUD carries the flags, "
          "a rank is a reward only, offered to and given only to the character ready for it, "
          "and a ready player skill asks the creator for its trial, once per skill and rank")
    return 0


if __name__ == "__main__":
    sys.exit(main())
