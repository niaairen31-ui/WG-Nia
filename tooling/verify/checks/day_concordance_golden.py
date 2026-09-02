"""Golden-case fixture for `day_concordance.concord` (TICKET-0081,
BRIEF-0081-a) and `day_concordance.emit_germs` (BRIEF-0081-c). Same
fresh-temp-SQLite-DB idiom as `context_disclosure_
floor.py`. Every case below is a FAILING input against the PRE-change code
(BRIEF-0075-c's plain-casefold `named_exact`, no `named_token` rung, no
casting, no E2c reachability scope) — each is asserted with exact set
equality on `concord`'s four verdict buckets, never a substring or a count.

Fixture: one world, an origin location ("Taverne", the PC's
`current_location_id`) and a distant location ("Chateau") with NO
`connects_to` edge between them, so `reachable_location_ids` from the origin
is `{Taverne}` only. Every case runs its OWN `concord()` call with a single
mention, so cases can never interfere with each other's verdict.

Case 1 (leading article, `_normalize_surface`): NPC "Tavernier", mention
"le tavernier" (named). Pre-change: `"le tavernier" != "tavernier"` under a
plain casefold — unmatched. Post-change: the leading-article strip narrows
it to "tavernier" — matched via `named_exact`. Mutation this detects:
removing `_normalize_surface` from either side of `named_exact`'s
comparison flips this back to unmatched.

Case 2 (trailing qualifier, `named_token`): NPC "Aldric", mention "Aldric le
forgeron" (named). Pre-change: no `named_token` rung exists at all, and
`named_exact`'s whole-string comparison never matches a qualified surface
form — unmatched. Post-change: `named_token`'s entity-name-tokens-subset-of-
surface-tokens test matches "Aldric" as the only entity whose (normalized)
name token set is a subset. Mutation this detects: removing `_normalize_
surface` from either side breaks the case-fold parity the subset test
depends on (a raw "Aldric" is not a member of the lower-cased surface token
set) and flips this to unmatched too.

Case 3 (casting, C2-partition): three NPCs ("Bruno", "Corentin", "Dagobert")
each hold an active standing goal mentioning "garde" and a schedule row at
the reachable origin. An inferred mention with role_hint "garde" matches all
three via `occupation`. Pre-change: three candidates on any rung is
`ambiguous` — the day could never plan (TICKET-0081's whole reason for
existing). Post-change: an INFERRED multi-candidate is casting, not a
collision; none of the three are present anywhere, and none holds a
`Relation` to the PC, so precedence falls through to `stable` — the
lexicographically lowest id wins. Mutation this detects: removing the
`kind == "named"` guard from `_classify` (i.e. treating INFERRED like NAMED)
flips this to `ambiguous`.

Case 4 (identity collision stays ambiguous): two active NPCs both named
"Marin". A NAMED mention "Marin" matches both via `named_exact`. This must
stay `ambiguous` and must NEVER be cast, regardless of candidate count —
proving the partition is keyed on `Mention.kind`, not on rung or count.

Case 5 (E2c reachability scope): NPC "Selvane" holds an active standing goal
mentioning "brigand" but her schedule is at the DISTANT location (Chateau),
outside the PC's reachable set. Pre-change: `occupation` has no proximity
scope at all — it would resolve her from anywhere in the world (E2's whole
finding). Post-change: the reachability `WHERE ... IN` filter excludes her
schedule row; `occupation` returns None and `presence` is inert (no place
mention in this call), so the mention is `unmatched` (and germinates,
per the ticket's live-gate expectation). Mutation this detects: removing
the `NpcSchedule.location_id.in_(ctx.reachable_location_ids)` filter (or the
`if not ctx.reachable_location_ids: return None` fail-closed guard) resolves
her anyway, flipping this to `matched` or `cast`.
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
    db_path = pathlib.Path(tmp_dir) / "check.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]

    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def _seed_fixture(engine) -> dict:
    from sqlmodel import Session as DbSession

    from world_engine.models import (
        Character,
        Entity,
        Location,
        NpcGoal,
        NpcSchedule,
        World,
    )

    with DbSession(engine) as session:
        world = World(name="Golden Concordance World", is_active=True)
        session.add(world)
        session.commit()
        session.refresh(world)

        def _make_location(name: str) -> str:
            entity = Entity(world_id=world.id, type="location", name=name)
            session.add(entity)
            session.commit()
            session.refresh(entity)
            session.add(Location(id=entity.id))
            session.commit()
            return entity.id

        taverne_id = _make_location("Taverne")
        chateau_id = _make_location("Chateau")
        # Deliberately no `connects_to` Relation between them — from the
        # origin (Taverne), `reachable_location_ids` is `{Taverne}` only.

        def _make_npc(name: str, location_id: str) -> str:
            entity = Entity(world_id=world.id, type="character", name=name)
            session.add(entity)
            session.commit()
            session.refresh(entity)
            session.add(Character(
                id=entity.id, world_id=world.id, character_type="npc",
                current_location_id=location_id,
            ))
            session.commit()
            return entity.id

        pc_entity = Entity(world_id=world.id, type="character", name="Le joueur")
        session.add(pc_entity)
        session.commit()
        session.refresh(pc_entity)
        session.add(Character(
            id=pc_entity.id, world_id=world.id, character_type="player",
            current_location_id=taverne_id,
        ))
        session.commit()

        tavernier_id = _make_npc("Tavernier", taverne_id)
        aldric_id = _make_npc("Aldric", taverne_id)
        marin_1_id = _make_npc("Marin", taverne_id)
        marin_2_id = _make_npc("Marin", taverne_id)

        def _make_standing_goal(npc_id: str, description: str) -> str:
            goal = NpcGoal(
                world_id=world.id, npc_id=npc_id, description=description,
                horizon="long", kind="standing", status="active",
            )
            session.add(goal)
            session.commit()
            session.refresh(goal)
            return goal.id

        guard_ids = []
        for guard_name in ("Bruno", "Corentin", "Dagobert"):
            guard_id = _make_npc(guard_name, taverne_id)
            goal_id = _make_standing_goal(guard_id, "Fait la garde de nuit devant la porte.")
            session.add(NpcSchedule(
                world_id=world.id, npc_id=guard_id, phase="matin",
                location_id=taverne_id, standing_goal_id=goal_id,
            ))
            session.commit()
            guard_ids.append(guard_id)

        selvane_id = _make_npc("Selvane", chateau_id)
        selvane_goal_id = _make_standing_goal(selvane_id, "Rançonne les voyageurs, brigand notoire.")
        session.add(NpcSchedule(
            world_id=world.id, npc_id=selvane_id, phase="matin",
            location_id=chateau_id, standing_goal_id=selvane_goal_id,
        ))
        session.commit()

        return {
            "world_id": world.id,
            "pc_id": pc_entity.id,
            "tavernier_id": tavernier_id,
            "aldric_id": aldric_id,
            "marin_ids": frozenset({marin_1_id, marin_2_id}),
            "guard_ids": frozenset(guard_ids),
            "selvane_id": selvane_id,
        }


def check_golden_cases():
    """Returns `(engine, fixture)` so `check_rewrite_golden_cases` (BRIEF-
    0081-b) can reuse the SAME engine/world rather than calling
    `_fresh_engine()` a second time in this process — `SQLModel.metadata`
    is a process-global singleton, so a second from-scratch `create_db_and_
    tables()` in the same run collides on "Table already defined"."""
    engine = _fresh_engine()
    fixture = _seed_fixture(engine)

    # ── Vacuous-proof guard, checked FIRST: a fixture that produced no data
    # must not silently pass (or crash past the guard trying to use it) —
    # it must fail here, loudly and by name.
    if len(fixture.get("guard_ids") or ()) != 3:
        fail(f"vacuous fixture: expected exactly 3 guard NPCs for case 3, got {fixture.get('guard_ids')!r}")
    if len(fixture.get("marin_ids") or ()) != 2:
        fail(f"vacuous fixture: expected exactly 2 same-named NPCs for case 4, got {fixture.get('marin_ids')!r}")
    if not fixture.get("pc_id") or not fixture.get("tavernier_id") or not fixture.get("aldric_id") or not fixture.get("selvane_id"):
        fail("vacuous fixture: one or more required fixture ids are missing")
    if FAILURES:
        return engine, fixture

    from sqlmodel import Session as DbSession

    from world_engine.day_concordance import concord
    from world_engine.day_extract import Mention
    from world_engine.models import Character

    with DbSession(engine) as session:
        character = session.get(Character, fixture["pc_id"])

        # ── Case 1: leading article, matched via named_exact ─────────────
        case1 = Mention(category="person", surface_form="le tavernier", kind="named")
        result1 = concord([case1], character, session)
        if {mm.entity_id for mm in result1.matched} != {fixture["tavernier_id"]}:
            fail(
                f"case 1 (leading article): expected matched=={{tavernier}}, "
                f"got matched={[mm.entity_id for mm in result1.matched]!r} "
                f"cast={list(result1.cast)!r} ambiguous={list(result1.ambiguous)!r} "
                f"unmatched={list(result1.unmatched)!r}"
            )
        if result1.cast or result1.ambiguous or result1.unmatched:
            fail("case 1 (leading article): non-matched buckets are not all empty")

        # ── Case 2: trailing qualifier, matched via named_token ───────────
        case2 = Mention(category="person", surface_form="Aldric le forgeron", kind="named")
        result2 = concord([case2], character, session)
        if {mm.entity_id for mm in result2.matched} != {fixture["aldric_id"]}:
            fail(
                f"case 2 (trailing qualifier): expected matched=={{aldric}}, "
                f"got matched={[mm.entity_id for mm in result2.matched]!r} "
                f"cast={list(result2.cast)!r} ambiguous={list(result2.ambiguous)!r} "
                f"unmatched={list(result2.unmatched)!r}"
            )
        elif any(mm.rung != "named_token" for mm in result2.matched):
            fail(f"case 2 (trailing qualifier): matched via {[mm.rung for mm in result2.matched]!r}, expected named_token")
        if result2.cast or result2.ambiguous or result2.unmatched:
            fail("case 2 (trailing qualifier): non-matched buckets are not all empty")

        # ── Case 3: inferred, 3 candidates -> cast, basis 'stable' ────────
        case3 = Mention(category="person", surface_form="un garde", kind="inferred", role_hint="garde")
        result3 = concord([case3], character, session)
        if {cm.entity_id for cm in result3.cast} != {min(fixture["guard_ids"])}:
            fail(
                f"case 3 (casting): expected cast=={{{min(fixture['guard_ids'])}}}, "
                f"got matched={list(result3.matched)!r} "
                f"cast={[cm.entity_id for cm in result3.cast]!r} "
                f"ambiguous={list(result3.ambiguous)!r} unmatched={list(result3.unmatched)!r}"
            )
        elif any(cm.basis != "stable" for cm in result3.cast):
            fail(f"case 3 (casting): basis is {[cm.basis for cm in result3.cast]!r}, expected 'stable'")
        if result3.matched or result3.ambiguous or result3.unmatched:
            fail("case 3 (casting): non-cast buckets are not all empty — MUST NOT appear in ambiguous")

        # ── Case 4: identity collision -> ambiguous, never cast ───────────
        case4 = Mention(category="person", surface_form="Marin", kind="named")
        result4 = concord([case4], character, session)
        if {am.candidate_ids for am in result4.ambiguous} != {tuple(sorted(fixture["marin_ids"]))}:
            fail(
                f"case 4 (identity collision): expected ambiguous candidate_ids=="
                f"{{{tuple(sorted(fixture['marin_ids']))!r}}}, got "
                f"matched={list(result4.matched)!r} cast={list(result4.cast)!r} "
                f"ambiguous={[am.candidate_ids for am in result4.ambiguous]!r} "
                f"unmatched={list(result4.unmatched)!r}"
            )
        if result4.matched or result4.cast or result4.unmatched:
            fail("case 4 (identity collision): non-ambiguous buckets are not all empty — MUST NOT be cast")

        # ── Case 5: occupation candidate outside reachable set -> unmatched
        case5 = Mention(category="person", surface_form="un brigand", kind="inferred", role_hint="brigand")
        result5 = concord([case5], character, session)
        if {um.mention.surface_form for um in result5.unmatched} != {"un brigand"}:
            fail(
                f"case 5 (E2c reachability): expected unmatched=={{'un brigand'}}, "
                f"got matched={list(result5.matched)!r} cast={list(result5.cast)!r} "
                f"ambiguous={list(result5.ambiguous)!r} "
                f"unmatched={[um.mention.surface_form for um in result5.unmatched]!r}"
            )
        if result5.matched or result5.cast or result5.ambiguous:
            fail("case 5 (E2c reachability): non-unmatched buckets are not all empty")

    return engine, fixture


def check_rewrite_golden_cases(engine, fixture) -> None:
    """TICKET-0081, BRIEF-0081-b, Scope IN item 11: four FAILING-input golden
    cases for `day_rewrite.render`/`write_day_rewrite`/`load_latest`, in this
    same fixture module. Each is asserted directly against the pre-change
    behaviour it would regress to if the corresponding guard were removed.
    Reuses the `(engine, fixture)` `check_golden_cases` already built — see
    that function's docstring for why a second `_fresh_engine()` call in
    this same process is unsafe."""
    if not fixture.get("world_id") or not fixture.get("tavernier_id"):
        fail("vacuous fixture (rewrite cases): required fixture ids are missing")
        return

    from sqlmodel import Session as DbSession
    from sqlmodel import select as db_select

    from world_engine import day_rewrite
    from world_engine.day_concordance import AmbiguousMention, ConcordanceResult, MatchedMention
    from world_engine.day_extract import Mention
    from world_engine.models import DayRewrite
    from world_engine.writes import write_day_rewrite

    # ── Case 6: render() raises on a non-empty `ambiguous` bucket ─────────
    ambiguous_mention = Mention(category="person", surface_form="Marin", kind="named")
    ambiguous_result = ConcordanceResult(
        matched=(), cast=(),
        ambiguous=(AmbiguousMention(mention=ambiguous_mention, candidate_ids=("a", "b")),),
        unmatched=(), skipped_rungs=(),
    )
    try:
        day_rewrite.render("le joueur parle a Marin", ambiguous_result, db=None)
        fail("case 6 (ambiguity guard): render() did not raise on a non-empty ambiguous bucket")
    except ValueError:
        pass

    # ── Case 7: render() is deterministic — two calls, byte-identical ─────
    with DbSession(engine) as session:
        matched_mention = Mention(category="person", surface_form="le tavernier", kind="named")
        matched_result = ConcordanceResult(
            matched=(MatchedMention(mention=matched_mention, entity_id=fixture["tavernier_id"], rung="named_exact"),),
            cast=(), ambiguous=(), unmatched=(), skipped_rungs=(),
        )
        declaration = "Je vais voir le tavernier."
        rendered_1 = day_rewrite.render(declaration, matched_result, session)
        rendered_2 = day_rewrite.render(declaration, matched_result, session)
        if rendered_1 != rendered_2:
            fail(
                f"case 7 (determinism): two render() calls over identical inputs diverged: "
                f"{rendered_1!r} != {rendered_2!r}"
            )

    # ── Case 8: write_day_rewrite rejects cast/cast_basis=None, no row built
    with DbSession(engine) as session:
        try:
            write_day_rewrite(
                session, world_id=fixture["world_id"], pass_play_id="fake-pass-play",
                generation=1, rendered_text="x",
                resolutions=[{
                    "ordinal": 1, "category": "person", "surface_form": "un garde", "kind": "inferred",
                    "role_hint": "garde", "verdict": "cast", "entity_id": fixture["tavernier_id"],
                    "rung": "occupation", "cast_basis": None,
                }],
            )
            fail("case 8 (write_day_rewrite validation): accepted a cast resolution with cast_basis=None")
        except ValueError:
            pass
        session.rollback()
        leftover = session.exec(
            db_select(DayRewrite).where(DayRewrite.pass_play_id == "fake-pass-play")
        ).all()
        if leftover:
            fail("case 8 (write_day_rewrite validation): a DayRewrite row was constructed despite the rejection")

    # ── Case 9: load_latest() returns None with no day_rewrite row ────────
    with DbSession(engine) as session:
        result = day_rewrite.load_latest("a-pass-play-with-no-rewrite", fixture["world_id"], session)
        if result is not None:
            fail("case 9 (resolve-path fail-closed): load_latest() returned a result with no day_rewrite row stored")


def check_germ_golden_cases(engine, fixture) -> None:
    """TICKET-0081, BRIEF-0081-c, Scope IN item 8: four FAILING-input golden
    cases for `emit_germs`'s two emission-side guards and its quota. Reuses
    the SAME `(engine, fixture)` pair as `check_rewrite_golden_cases` — see
    `check_golden_cases`'s docstring for why a second `_fresh_engine()` call
    in this same process is unsafe."""
    if not fixture.get("world_id") or not fixture.get("pc_id"):
        fail("vacuous fixture (germ cases): required fixture ids are missing")
        return

    from sqlmodel import Session as DbSession

    from world_engine.day_concordance import MAX_GERMS_PER_DECLARATION, UnmatchedMention, emit_germs
    from world_engine.day_extract import Mention
    from world_engine.models import Entity, PassPlay, ProposedMutation

    world_id = fixture["world_id"]
    # Never added/committed — emit_germs only reads .id/.character_id off it,
    # so it need not satisfy pass_play's DB-level NOT NULL FKs here.
    pass_play = PassPlay(id="germ-fixture-pass-play", character_id=fixture["pc_id"], declared_action="x")

    def _unmatched(surface_form: str, role_hint: str) -> "UnmatchedMention":
        return UnmatchedMention(
            mention=Mention(category="person", surface_form=surface_form, kind="inferred", role_hint=role_hint),
            rungs_tried=("occupation", "presence"),
        )

    with DbSession(engine) as session:
        # A live NPC the collision guard must find.
        session.add(Entity(world_id=world_id, type="character", name="Barde", status="active"))
        # A pending germ the dedup guard must find.
        session.add(ProposedMutation(
            world_id=world_id, source_type="pass_play", pass_play_id=None,
            mutation_type="entity_creation", status="proposed",
            payload={"entity_type": "character", "name": "Chasseur"},
            proposed_by="local_ai",
        ))
        # A REALIZED germ (created_entity_id set) — must NOT block a new one.
        session.add(ProposedMutation(
            world_id=world_id, source_type="pass_play", pass_play_id=None,
            mutation_type="entity_creation", status="approved",
            payload={"entity_type": "character", "name": "Marchand", "created_entity_id": "already-real"},
            proposed_by="local_ai",
        ))
        session.commit()

        # ── Case 10: collision guard — role_hint case-folds onto an ACTIVE
        # entity name -> ZERO germs. Removing the collision guard must make
        # this case fail.
        germs = emit_germs((_unmatched("un barde", "Barde"),), pass_play, session)
        if germs:
            fail(f"case 10 (collision guard): expected zero germs, got {[g.payload.get('name') for g in germs]!r}")

        # ── Case 11: pending dedup — role_hint case-folds onto a PENDING
        # germ's payload name -> ZERO germs. Removing the dedup must make
        # this case fail.
        germs = emit_germs((_unmatched("un chasseur", "chasseur"),), pass_play, session)
        if germs:
            fail(f"case 11 (pending dedup): expected zero germs, got {[g.payload.get('name') for g in germs]!r}")

        # ── Case 12: a germ whose payload already carries created_entity_id
        # must NOT block a new one — the entity was realized, a second,
        # different one may legitimately be needed. Widening the dedup to
        # ignore created_entity_id must make this case fail.
        germs = emit_germs((_unmatched("un marchand", "marchand"),), pass_play, session)
        if {g.payload.get("name") for g in germs} != {"marchand"}:
            fail(
                f"case 12 (realized germ does not block): expected one germ named 'marchand', "
                f"got {[g.payload.get('name') for g in germs]!r}"
            )

        # ── Case 13: quota — five distinct unmatched persons -> exactly
        # MAX_GERMS_PER_DECLARATION germs, kept in mention order. Removing
        # the quota must make this case fail.
        five = tuple(_unmatched(f"un inconnu {i}", f"role-{i}") for i in range(5))
        germs = emit_germs(five, pass_play, session)
        if len(germs) != MAX_GERMS_PER_DECLARATION:
            fail(f"case 13 (quota): expected {MAX_GERMS_PER_DECLARATION} germs, got {len(germs)}")
        elif [g.payload.get("name") for g in germs] != [f"role-{i}" for i in range(MAX_GERMS_PER_DECLARATION)]:
            fail(
                f"case 13 (quota): expected the first {MAX_GERMS_PER_DECLARATION} in mention order, "
                f"got names={[g.payload.get('name') for g in germs]!r}"
            )


def main() -> None:
    engine, fixture = check_golden_cases()
    check_rewrite_golden_cases(engine, fixture)
    check_germ_golden_cases(engine, fixture)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: day_concordance_golden — leading-article and trailing-qualifier "
        "matching, casting (C2-partition, basis 'stable'), identity-collision "
        "ambiguity, E2c reachability scoping, the rewrite golden cases "
        "(ambiguity guard, determinism, cast/cast_basis validation, fail-closed "
        "resolve reader), and the germ emission golden cases (collision guard, "
        "pending dedup, realized-germ non-block, quota) all resolve correctly"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
