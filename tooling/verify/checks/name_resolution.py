"""G1 check for TICKET-0092 — name resolution over the name index.

Created by BRIEF-0092-A so the ticket's acceptance arrow resolves from the
first brief on; BRIEF-0092-B passes the scope to G0 and adds G1-G5;
BRIEF-0092-C adds G6-G8; BRIEF-0092-D adds G9-G11.

G0 (fixture) -- in a fresh world, a character "Maelis Varn" resolves with
   `resolve_named("Maelis Varn", "person", world.id, session,
   scope=CREATOR)` to `matched` on it, via the `named_exact` rung.
G1 (fixture) -- the LOT's "Rungs" table through `resolve_named`, exact
   equality on `(verdict, entity_id, candidate_ids, rung)`.
G2 (fixture) -- the LOT's "Near" table through `near_candidates`: "Maelys"
   yields only Maelis (83); "reine" yields La Reine Grise (63) then Reine
   Ysolde (59); `exclude_ids` drops an id; `scope=PROSE` raises ValueError.
G3 (fixture) -- the day chain sees the perceiver regime: a PC who knows the
   appellation "la reine" of an NPC resolves it via `named_exact`; a PC who
   does not leaves it unmatched.
G4 (fixture) -- `resolve_subject("la reine", ...)` stays unmatched with that
   appellation present (names only, N10a).
G5 (fixture) -- a tokenizer generator mention "Varn" next to "Maelis Varn"
   stays unresolved: no partial rung outside `creator`.
G6 (static) -- the LOT's "Categories after C" table through
   `category_of_type`, a runtime slug "golem" included.
G7 (fixture) -- an `item` "Épée de Kar" resolves under "object"; a "golem"
   "Gardien" resolves under "other", not under "person"; `validate_binding`
   agrees on both and refuses "object" for the golem.
G8 (static) -- `lore_plan._MENTION_CATEGORIES` equals
   `lore_resolve.CATEGORIES` (belt and braces over lore_isolation R9).
G9 (static) -- an `unknown_entity` `LoreResult` whose `near` holds two
   candidates renders the lot's sentence, equal to
   `_UNKNOWN_ENTITY_WITH_NEAR.format(...)` over `_NEAR_ITEM`; with empty
   candidates, the WITHOUT text.
G10 (fixture) -- the LOT's `record_appellation` table: a scope outside the
   three, a blank surface and an unknown entity raise ValueError; a surface
   normalizing to the name or an appellation returns None and writes
   nothing; otherwise one appellation fact, participant = the entity,
   default per scope (rencontre on the entity, world, none).
G11 (fixture, TestClient) -- lookup of "Maelys" returns Maelis in `near`
   at 83; POST /api/lore/appellations writes, then returns `written: false`
   on the same surface; resolve with `record_appellation: true` binds and
   writes one appellation fact; with `scope_type: "nope"` it returns 422 and
   the mention stays open.

Fixtures run on a fresh temp-file SQLite database
(`WORLD_ENGINE_DATABASE_URL` set before any world_engine import — never
Nia's DB). FAILURES list, print FAIL lines, exit 1.
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
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def _world(session, label: str):
    from world_engine.models import Entity, World

    world = World(name=label, is_active=False)
    session.add(world)
    session.flush()

    def entity(kind: str, name: str):
        row = Entity(world_id=world.id, type=kind, name=name)
        session.add(row)
        session.flush()
        return row

    return world, entity


def check_g0(engine) -> None:
    from sqlmodel import Session

    from world_engine.lore_resolve import resolve_named
    from world_engine.name_index import CREATOR

    with Session(engine) as session:
        world, entity = _world(session, "G0 World")
        maelis = entity("character", "Maelis Varn")
        got = resolve_named("Maelis Varn", "person", world.id, session, scope=CREATOR)
        if (got.verdict, got.entity_id, got.rung) != ("matched", maelis.id, "named_exact"):
            fail(f"G0: {(got.verdict, got.entity_id, got.rung)!r} "
                 f"!= ('matched', {maelis.id!r}, 'named_exact')")
        session.rollback()


def _appellation(session, owner, content, scope=None):
    from world_engine.writes.facets import add_entity_fact

    return add_entity_fact(session, entity_id=owner.id, facet="appellation", content=content,
                           created_by="check", scope=scope)


def _got(resolution) -> tuple:
    return (resolution.verdict, resolution.entity_id, resolution.candidate_ids, resolution.rung)


def check_g1(engine) -> None:
    from sqlmodel import Session

    from world_engine.lore_resolve import resolve_named
    from world_engine.name_index import CREATOR, NAMES_ONLY

    with Session(engine) as session:
        world, entity = _world(session, "G1 World")
        maelis = entity("character", "Maelis Varn")
        grise = entity("location", "La Reine Grise")
        ysolde = entity("character", "Ysolde")
        _appellation(session, ysolde, "la reine")
        table = [
            ("la reine", "person", CREATOR, ("matched", ysolde.id, (ysolde.id,), "named_exact")),
            ("la reine", "place", CREATOR, ("matched", grise.id, (grise.id,), "named_partial")),
            ("Varn", "person", CREATOR, ("matched", maelis.id, (maelis.id,), "named_partial")),
            ("Varn", "person", NAMES_ONLY, ("unmatched", None, (), None)),
            ("Ma", "person", CREATOR, ("unmatched", None, (), None)),
        ]
        for surface, category, scope, expected in table:
            got = _got(resolve_named(surface, category, world.id, session, scope=scope))
            if got != expected:
                fail(f"G1 {surface!r} {category} {scope.regime}: {got!r} != {expected!r}")
        reine = entity("character", "Reine")
        expected = ("ambiguous", None, tuple(sorted((ysolde.id, reine.id))), "named_exact")
        got = _got(resolve_named("la reine", "person", world.id, session, scope=CREATOR))
        if got != expected:
            fail(f"G1 'la reine' person creator + 'Reine': {got!r} != {expected!r}")
        session.rollback()


def check_g2(engine) -> None:
    from sqlmodel import Session

    from world_engine.lore_resolve import near_candidates
    from world_engine.name_index import CREATOR, PROSE

    with Session(engine) as session:
        world, entity = _world(session, "G2 World")
        maelis = entity("character", "Maelis")
        entity("character", "Maelis Varn")
        ysolde = entity("character", "Reine Ysolde")
        grise = entity("location", "La Reine Grise")

        def near(surface, **kwargs):
            return near_candidates(surface, world.id, session, scope=CREATOR, **kwargs)

        got = [(c.entity_id, c.score) for c in near("Maelys")]
        if got != [(maelis.id, 83)]:
            fail(f"G2 'Maelys': {got!r} != {[(maelis.id, 83)]!r}")
        got = [(c.entity_id, c.score) for c in near("reine")]
        if got != [(grise.id, 63), (ysolde.id, 59)]:
            fail(f"G2 'reine': {got!r} != {[(grise.id, 63), (ysolde.id, 59)]!r}")
        got = [c.entity_id for c in near("reine", exclude_ids=frozenset({grise.id}))]
        if got != [ysolde.id]:
            fail(f"G2 'reine' excluding La Reine Grise: {got!r} != {[ysolde.id]!r}")
        try:
            near_candidates("reine", world.id, session, scope=PROSE)
            fail("G2: near_candidates(scope=PROSE) did not raise ValueError")
        except ValueError:
            pass
        session.rollback()


def check_g3_g4(engine) -> None:
    from sqlmodel import Session

    from world_engine.day_concordance import concord
    from world_engine.day_extract import Mention
    from world_engine.models import Character, Location
    from world_engine.subject_resolve import resolve_subject
    from world_engine.writes.facets import ScopeChoice
    from world_engine.writes.knowledge import write_knowledge

    with Session(engine) as session:
        world, entity = _world(session, "G3 World")
        place = entity("location", "Taverne")
        session.add(Location(id=place.id))

        def character(name: str, character_type: str):
            row = entity("character", name)
            session.add(Character(id=row.id, world_id=world.id, character_type=character_type,
                                  current_location_id=place.id))
            session.flush()
            return session.get(Character, row.id)

        pc_p, npc_y = character("Pell", "player"), character("Ysolde", "npc")
        pc_q = character("Quill", "player")
        fact = _appellation(session, npc_y, "la reine", ScopeChoice("none"))
        write_knowledge(session, entity_id=pc_p.id, fact_id=fact.id, subject="la reine",
                        level="knows", is_secret=False, changed_by="check")
        session.flush()
        mention = Mention(category="person", surface_form="la reine", kind="named")
        got = concord([mention], pc_p, session)
        seen = [(m.entity_id, m.rung) for m in got.matched]
        if seen != [(npc_y.id, "named_exact")]:
            fail(f"G3 knowing PC: matched {seen!r} != {[(npc_y.id, 'named_exact')]!r}")
        got = concord([mention], pc_q, session)
        if got.matched or got.cast or got.ambiguous or len(got.unmatched) != 1:
            fail(f"G3 unknowing PC: 'la reine' not unmatched: {got!r}")
        subject = resolve_subject("la reine", world.id, session)
        if subject.verdict != "unmatched":
            fail(f"G4: resolve_subject('la reine') is {subject.verdict!r}, not 'unmatched'")
        session.rollback()


def check_g5(engine) -> None:
    from sqlmodel import Session

    from world_engine.prose_tokens import tokenize

    with Session(engine) as session:
        world, entity = _world(session, "G5 World")
        entity("character", "Maelis Varn")
        got = tokenize(session, world_id=world.id, text="Varn arrive.",
                       mentions=[{"name": "Varn", "category": "person"}])
        pairs = [(u.surface, u.reason) for u in got.unresolved]
        if got.text != "Varn arrive." or pairs != [("Varn", "inconnu")]:
            fail(f"G5: {got.text!r} {pairs!r} != 'Varn arrive.' [('Varn', 'inconnu')]")
        session.rollback()


_CATEGORY_TABLE: tuple[tuple[str, str], ...] = (
    ("location", "place"), ("character", "person"), ("faction", "faction"),
    ("item", "object"), ("artifact", "other"), ("golem", "other"), ("", "other"),
)


def check_g6() -> None:
    from world_engine.lore_resolve import category_of_type

    for entity_type, expected in _CATEGORY_TABLE:
        got = category_of_type(entity_type)
        if got != expected:
            fail(f"G6: category_of_type({entity_type!r}) is {got!r}, not {expected!r}")


def check_g7(engine) -> None:
    from sqlmodel import Session

    from world_engine.lore_resolve import resolve_named, validate_binding
    from world_engine.name_index import CREATOR

    with Session(engine) as session:
        world, entity = _world(session, "G7 World")
        sword = entity("item", "Épée de Kar")
        golem = entity("golem", "Gardien")
        got = _got(resolve_named("l'épée de Kar", "object", world.id, session, scope=CREATOR))
        if got[:2] != ("matched", sword.id):
            fail(f"G7 'l'épée de Kar' object: {got!r} is not matched on the item")
        got = _got(resolve_named("Gardien", "other", world.id, session, scope=CREATOR))
        if got[:2] != ("matched", golem.id):
            fail(f"G7 'Gardien' other: {got!r} is not matched on the golem")
        got = _got(resolve_named("Gardien", "person", world.id, session, scope=CREATOR))
        if got[0] != "unmatched":
            fail(f"G7 'Gardien' person: {got!r} is not unmatched")
        for entity_id, category, expected in (
            (sword.id, "object", True), (golem.id, "other", True),
            (golem.id, "object", False), (golem.id, "person", False),
            (sword.id, "other", False), (golem.id, "weapon", False),
        ):
            if validate_binding(entity_id, category, world.id, session) is not expected:
                fail(f"G7: validate_binding({entity_id!r}, {category!r}) is not {expected!r}")
        session.rollback()


def check_g8() -> None:
    from world_engine import lore_plan, lore_resolve

    if lore_plan._MENTION_CATEGORIES != lore_resolve.CATEGORIES:
        fail(f"G8: lore_plan._MENTION_CATEGORIES {lore_plan._MENTION_CATEGORIES!r} != "
             f"lore_resolve.CATEGORIES {lore_resolve.CATEGORIES!r}")


def check_g9() -> None:
    from world_engine.lore_query import LoreResult
    from world_engine.lore_render import (
        _NEAR_ITEM, _UNKNOWN_ENTITY_WITH_NEAR, _UNKNOWN_ENTITY_WITHOUT_NEAR, _render_unknown_entity,
    )

    candidates = [
        {"entity_id": "e1", "name": "Ysolde", "type": "character", "score": 83},
        {"entity_id": "e2", "name": "Reine Grise", "type": "location", "score": 63},
    ]

    def result(near_candidates):
        return LoreResult(
            verdict="unknown_entity", rows=(), trace=[], ambiguous_mentions=(),
            unmatched_surface_forms=("la reyne",), rejection_reason=None,
            near=({"surface_form": "la reyne", "candidates": near_candidates},),
        )

    expected = _UNKNOWN_ENTITY_WITH_NEAR.format(
        surface_form="la reyne",
        noms=", ".join(_NEAR_ITEM.format(nom=c["name"], pct=c["score"]) for c in candidates),
    )
    literal = ("Aucune entité nommée « la reyne » dans ce monde. Noms proches : "
               "Ysolde (ressemblance 83 %), Reine Grise (ressemblance 63 %).")
    got = _render_unknown_entity(result(candidates))
    if got != expected or got != literal:
        fail(f"G9 with near: {got!r} != {literal!r}")
    got = _render_unknown_entity(result([]))
    if got != _UNKNOWN_ENTITY_WITHOUT_NEAR.format(surface_form="la reyne"):
        fail(f"G9 without near: {got!r}")


def _appellation_facts(session, entity_id) -> list:
    from sqlmodel import select

    from world_engine.models import Fact, FactParticipant

    return session.exec(select(Fact).join(FactParticipant, FactParticipant.fact_id == Fact.id).where(
        FactParticipant.entity_id == entity_id, Fact.facet == "appellation",
    )).all()


def _g10_rejects(record) -> None:
    for label, kwargs in (("bad scope", {"surface": "Mae", "scope_type": "nope"}),
                          ("blank surface", {"surface": "   "}),
                          ("unknown entity", {"surface": "Mae", "entity_id": "no-such-entity"})):
        try:
            record(**kwargs)
            fail(f"G10 {label}: no ValueError")
        except ValueError:
            pass


def check_g10(engine) -> None:
    from sqlmodel import Session, select

    from world_engine.models import FactDefault, FactParticipant
    from world_engine.writes.facets import record_appellation

    with Session(engine) as session:
        world, entity = _world(session, "G10 World")
        maelis = entity("character", "Maelis Varn")
        _appellation(session, maelis, "la Rousse")

        def record(surface, scope_type="rencontre", entity_id=maelis.id):
            return record_appellation(session, entity_id=entity_id, surface=surface,
                                      scope_type=scope_type, created_by="check")

        _g10_rejects(record)
        before = len(_appellation_facts(session, maelis.id))
        for surface in ("maelis varn", "  Rousse "):
            if record(surface) is not None:
                fail(f"G10 duplicate {surface!r}: a fact was returned")
        if len(_appellation_facts(session, maelis.id)) != before:
            fail("G10 duplicates wrote an appellation fact")
        for surface, scope_type, expected in (("Mae", "rencontre", [("rencontre", maelis.id)]),
                                              ("la Varn", "world", [("world", None)]),
                                              ("Brune", "none", [])):
            fact = record(surface, scope_type)
            if fact is None or fact.facet != "appellation":
                fail(f"G10 {surface!r} {scope_type}: no appellation fact written")
                continue
            owners = session.exec(select(FactParticipant.entity_id).where(
                FactParticipant.fact_id == fact.id)).all()
            if list(owners) != [maelis.id]:
                fail(f"G10 {surface!r}: participants {owners!r} != [{maelis.id!r}]")
            defaults = [(d.scope_type, d.scope_id) for d in session.exec(
                select(FactDefault).where(FactDefault.fact_id == fact.id)).all()]
            if defaults != expected:
                fail(f"G10 {surface!r} {scope_type}: defaults {defaults!r} != {expected!r}")
        session.rollback()


def _open_mention(session, world, owner, content, surface) -> str:
    from sqlmodel import select

    from world_engine.models import UnresolvedMention
    from world_engine.prose_tokens import Unresolved
    from world_engine.writes.facets import add_entity_fact
    from world_engine.writes.mentions import record_unresolved

    fact = add_entity_fact(session, entity_id=owner.id, facet="histoire", content=content,
                           created_by="check")
    record_unresolved(session, world_id=world.id, fact_id=fact.id,
                      items=(Unresolved(surface, "inconnu", "person"),))
    session.flush()
    return session.exec(select(UnresolvedMention.id).where(
        UnresolvedMention.fact_id == fact.id, UnresolvedMention.surface == surface)).one()


def _g11_fixture(engine) -> tuple:
    from sqlmodel import Session

    with Session(engine) as session:
        world, entity = _world(session, "G11 World")
        world.is_active = True
        maelis = entity("character", "Maelis")
        aldric = entity("character", "Aldric")
        mention_ids = (
            _open_mention(session, world, aldric, "Aldric a vu Maelys au marché.", "Maelys"),
            _open_mention(session, world, aldric, "Aldric doit de l'argent à Maelys.", "Maelys"),
        )
        session.commit()
        return maelis.id, mention_ids


def _g11_panel_reads_and_post(client, maelis_id) -> None:
    resp = client.get("/api/lore/names/lookup", params={"surface": "Maelys"})
    near = [(c["id"], c["score"]) for c in resp.json().get("near", [])] if resp.status_code == 200 else None
    if near is None or (maelis_id, 83) not in near:
        fail(f"G11 lookup 'Maelys': {resp.status_code} near {near!r} lacks ({maelis_id!r}, 83)")
    if client.get("/api/lore/names/lookup", params={"surface": "  "}).status_code != 422:
        fail("G11 lookup of a blank surface is not 422")
    body = {"entity_id": maelis_id, "surface": "Mae la Brune"}
    first = client.post("/api/lore/appellations", json=body)
    second = client.post("/api/lore/appellations", json=body)
    if first.status_code != 200 or not first.json().get("written") or not first.json().get("fact_id"):
        fail(f"G11 appellation POST: {first.status_code} {first.text}")
    if second.status_code != 200 or second.json() != {"ok": True, "written": False, "fact_id": None}:
        fail(f"G11 appellation POST twice: {second.status_code} {second.text}")


def check_g11(engine) -> None:
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from world_engine.cockpit.app import app
    from world_engine.models import UnresolvedMention

    maelis_id, (bound_id, refused_id) = _g11_fixture(engine)
    client = TestClient(app)
    _g11_panel_reads_and_post(client, maelis_id)
    with Session(engine) as session:
        before = len(_appellation_facts(session, maelis_id))
    resp = client.post(f"/api/lore/mentions/{bound_id}/resolve",
                       json={"entity_id": maelis_id, "record_appellation": True})
    if resp.status_code != 200 or resp.json().get("appellation_written") is not True:
        fail(f"G11 resolve with record_appellation: {resp.status_code} {resp.text}")
    resp = client.post(f"/api/lore/mentions/{refused_id}/resolve",
                       json={"entity_id": maelis_id, "record_appellation": True, "scope_type": "nope"})
    if resp.status_code != 422:
        fail(f"G11 resolve with scope_type 'nope': {resp.status_code} != 422")
    with Session(engine) as session:
        written = len(_appellation_facts(session, maelis_id)) - before
        if written != 1:
            fail(f"G11 resolves wrote {written} appellation fact(s), expected 1")
        bound, refused = session.get(UnresolvedMention, bound_id), session.get(UnresolvedMention, refused_id)
        if bound.resolved_at is None or bound.resolved_entity_id != maelis_id:
            fail("G11 resolve with record_appellation did not bind the mention")
        if refused.resolved_at is not None:
            fail("G11 resolve with scope_type 'nope' closed the mention")


def main() -> int:
    engine = _fresh_engine()
    check_g0(engine)
    check_g1(engine)
    check_g2(engine)
    check_g3_g4(engine)
    check_g5(engine)
    check_g6()
    check_g7(engine)
    check_g8()
    check_g9()
    check_g10(engine)
    check_g11(engine)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: name_resolution — exact names resolve, appellations and partial names resolve "
          "for the creator only, near names score and order as the lot's table, the day chain "
          "sees only the appellations its character knows, subjects and tokenizer mentions "
          "stay on names, objects and every other type are nameable categories, near names reach "
          "the Lore answer and the names panel, and the panel records a missed name as an "
          "appellation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
