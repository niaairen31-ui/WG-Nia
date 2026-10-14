"""G1 check for TICKET-0121 -- the lore is searched by its words, not only by the names it holds.

BRIEF-0121-C's rules (S2 of the quest designer's lot):

LF1 -- the search (fixture). `facts_mentioning("acier noir", A)` returns the `coverage` row, then exactly
   the facts of world A whose text holds both words -- the secret-known one with its secret knower
   marked, the creator-only one flagged, nothing of world B and nothing that holds only one word.
LF2 -- the floor (fixture). A query with no token of three letters or more gives the `coverage` row
   alone, `counted_rows == 0`.
LF3 -- the plan (fixture). `validate_plan` accepts `facts_mentioning("text:acier", "$world")` and refuses
   `("$world", "$world")`, `("text:", "$world")` and a `text:` argument given to `entity_dossier`;
   `execute_plan` on the accepted plan answers `answered` with the `mentions` rows.
LF4 -- the render (fixture). `render_template` of that result holds the formatted line, with no
   `ValueError` for the `mentions` section.
LF5 -- the designer's gathering (fixture). `gather_lore` gives the facts of the keywords, then of the
   named entity, then of the Lore entry, without duplicates, one line each; a request on nothing the
   canon holds is `empty` with no entity.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any world_engine import) --
never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> None:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))


def _seed(session) -> dict:
    from world_engine.models import Character, Entity, Fact, World
    from world_engine.writes import attach_participants, create_fact, write_knowledge
    from world_engine.writes.lore_entries import record_entry_row, write_lore_entry

    ids: dict = {}
    world_a = World(name="LF A", is_active=False)
    world_b = World(name="LF B", is_active=False)
    session.add_all([world_a, world_b])
    session.flush()
    ids["A"], ids["B"] = world_a.id, world_b.id

    def npc(world_id: str, name: str) -> str:
        entity = Entity(world_id=world_id, type="character", name=name)
        session.add(entity)
        session.flush()
        session.add(Character(id=entity.id, world_id=world_id, character_type="npc"))
        return entity.id

    def fact(world_id: str, content: str) -> str:
        row = create_fact(session, world_id=world_id, content=content, created_by="check",
                          facet="information")
        session.flush()
        return row.id

    ids["npc"] = npc(world_a.id, "Orvane")
    ids["npc_b"] = npc(world_b.id, "Orvane")
    ids["secret"] = fact(world_a.id, "Le secret de l'acier noir tient dans la trempe")
    ids["ordinary"] = fact(world_a.id, "L'acier ordinaire vient du nord")
    ids["creator"] = fact(world_a.id, "Orvane cache l'acier noir de la guilde")
    ids["brother"] = fact(world_a.id, "Orvane a un frère à Kess")
    ids["other_world"] = fact(world_b.id, "L'acier noir dort sous la montagne")
    for key in ("creator", "brother"):
        attach_participants(session, fact=session.get(Fact, ids[key]), entity_ids=[ids["npc"]])
    session.flush()
    write_knowledge(session, entity_id=ids["npc"], fact_id=ids["secret"], level="knows",
                    is_secret=True, changed_by="check")
    write_knowledge(session, entity_id=ids["npc"], fact_id=ids["creator"], level="unaware",
                    is_secret=True, changed_by="check")
    entry = write_lore_entry(session, world_id=world_a.id, statement="Le nord forge l'acier")
    session.flush()
    record_entry_row(session, entry_id=entry.id, row_table="fact", row_id=ids["ordinary"])
    ids["entry"] = entry.id
    session.commit()
    return ids


def check_lf1_lf2(session, ids: dict) -> None:
    from world_engine.lore_selectors import facts_mentioning

    rows = facts_mentioning("acier noir", ids["A"], session)
    if not rows or rows[0].get("section") != "coverage":
        fail(f"LF1: the first row is not the coverage row: {rows[:1]!r}")
        return
    mentions = [r for r in rows if r.get("section") == "mentions"]
    if rows[0].get("counted_rows") != len(mentions):
        fail(f"LF1: coverage counts {rows[0].get('counted_rows')} for {len(mentions)} rows")
    got = {m["fact_id"] for m in mentions}
    want = {ids["secret"], ids["creator"]}
    if got != want:
        fail(f"LF1: the facts are {sorted(got)}, expected exactly world A's two 'acier noir' facts")
    by_id = {m["fact_id"]: m for m in mentions}
    secret = by_id.get(ids["secret"])
    if secret is None or secret["creator_only"] or not any(
        k["knower_entity_id"] == ids["npc"] and k["is_secret"] for k in secret["knowers"]
    ):
        fail(f"LF1: the secret fact does not carry its secret knower: {secret!r}")
    creator = by_id.get(ids["creator"])
    if creator is None or not creator["creator_only"]:
        fail(f"LF1: the creator-only fact is not flagged: {creator!r}")
    if ids["other_world"] in got or ids["ordinary"] in got:
        fail("LF1: a fact of another world, or holding one word only, was returned")

    floor = facts_mentioning("de la", ids["A"], session)
    if len(floor) != 1 or floor[0].get("section") != "coverage" or floor[0].get("counted_rows") != 0:
        fail(f"LF2: a query without a 3-letter token returned {floor!r}")
    # The floor drops short words from the query, not from the match: "de" is ignored, "nord" counts.
    short = [r for r in facts_mentioning("nord de", ids["A"], session) if r.get("section") == "mentions"]
    if [r["fact_id"] for r in short] != [ids["ordinary"]]:
        fail(f"LF2: a short word in the query changed the match: {short!r}")


def check_lf3_lf4(session, ids: dict) -> None:
    from world_engine.lore_query import LorePlan, PlanCall, execute_plan, validate_plan
    from world_engine.lore_render import render_template

    def plan(selector: str, *args: str) -> LorePlan:
        return LorePlan(mentions=(), calls=(PlanCall(selector=selector, args=tuple(args)),))

    if not validate_plan(plan("facts_mentioning", "text:acier", "$world"), session).ok:
        fail("LF3: facts_mentioning('text:acier', '$world') is refused")
    for label, bad in (
        ("a bare $world for the text", plan("facts_mentioning", "$world", "$world")),
        ("an empty text:", plan("facts_mentioning", "text:", "$world")),
        ("a bare string for the text", plan("facts_mentioning", "acier", "$world")),
        ("a text: argument on entity_dossier", plan("entity_dossier", "text:acier", "$world")),
    ):
        if validate_plan(bad, session).ok:
            fail(f"LF3: validate_plan accepts {label}")

    result = execute_plan(plan("facts_mentioning", "text:acier noir", "$world"), ids["A"], session)
    if result.verdict != "answered" or not any(r.get("section") == "mentions" for r in result.rows):
        fail(f"LF3: execute_plan gave {result.verdict!r} with {len(result.rows)} row(s)")
        return
    silent = execute_plan(plan("facts_mentioning", "text:dragon", "$world"), ids["A"], session)
    if silent.verdict != "silent_canon":
        fail(f"LF3: a search finding nothing is {silent.verdict!r}, not silent_canon")

    try:
        prose = render_template(result).prose
    except ValueError as exc:
        fail(f"LF4: render_template raised {exc}")
        return
    if "« Le secret de l'acier noir tient dans la trempe »" not in prose or "su par Orvane" not in prose:
        fail(f"LF4: the rendered prose lacks the formatted mention: {prose!r}")
    if "(réservé à la créatrice)" not in prose:
        fail(f"LF4: the creator-only fact is not marked in the prose: {prose!r}")


def check_lf5(session, ids: dict) -> None:
    from world_engine.quest_lore import gather_lore

    got = gather_lore(session, ids["A"], keywords=["acier", "noir"], names=["Orvane"],
                      lore_entry_id=ids["entry"])
    want = (ids["secret"], ids["creator"], ids["brother"], ids["ordinary"])
    if got.fact_ids != want:
        fail(f"LF5: the facts are {got.fact_ids}, expected {want}")
    if got.entity_ids != (ids["npc"],):
        fail(f"LF5: the entities are {got.entity_ids}, expected the NPC alone")
    if len(got.lines) != len(got.fact_ids) or got.empty:
        fail(f"LF5: {len(got.lines)} line(s) for {len(got.fact_ids)} fact(s), empty={got.empty}")
    if not any("su de personne" in line for line in got.lines):
        fail("LF5: the fact nobody knows is not written « su de personne »")
    if not any(line.endswith("(réservé à la créatrice)") for line in got.lines):
        fail("LF5: the creator-only fact is not marked")

    none = gather_lore(session, ids["A"], keywords=["dragon"], names=["Zorglub"])
    if not none.empty or none.entity_ids or none.fact_ids:
        fail(f"LF5: a request on nothing is not empty: {none!r}")


def main() -> int:
    _fresh_db()
    from sqlmodel import Session, SQLModel

    from world_engine import models  # noqa: F401  (registers every table)
    from world_engine.db import engine

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        ids = _seed(session)
        check_lf1_lf2(session, ids)
        check_lf3_lf4(session, ids)
        check_lf5(session, ids)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: lore_facts_mentioning -- the lore is searched by its words: the facts holding every "
          "word of three letters or more, of that world only, with their knowers, secrets and "
          "creator-only notes marked; a text: argument is validated and rendered; the designer's "
          "gathering orders and de-duplicates its facts and says when canon holds nothing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
