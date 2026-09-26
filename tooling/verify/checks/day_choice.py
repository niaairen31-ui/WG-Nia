"""G1 check for TICKET-0094 — Concordance H2, the model chooses and the code
judges. Created by BRIEF-0094-A with the near cases; BRIEF-0094-B adds the
narrowing and the judge; BRIEF-0094-C adds the call; BRIEF-0094-D adds the
static route rules.

N1 -- `near_in_surfaces` (C-03) scores a typo and a shared token like
   `near_candidates` does: "Maelys" -> Maelis 83; "reine" -> La Reine Grise
   63, Reine Ysolde 59.
N2 -- `exclude_ids` drops an entity from the result.
N3 -- every category counts: a location surface is returned with its
   `entity_type`; the caller filters.

J1-J8 -- `judge_choice` (C-06), one case per row of the lot's (b2) table, on
   an `ambiguous` request (Maelis / Ilune, one fact each) and a `near` one
   (Maelis, no facts): declined, out of range, too short, excerpt only in the
   declaration, excerpt shared with another candidate, edge punctuation
   stripped, excerpt in another's facts only, excerpt nowhere.
P -- `parse_answer` returns the three keys; `choix: true`, a missing
   `extrait` and a non-JSON answer raise `LlmParseError`.
Rd -- `render_candidates` renders the numbered list exactly.
Rc -- `record_of` builds the C-02 family shape; `declined` carries no chosen
   entity.
Q1-Q4 -- `choice_requests` (C-05) on a temp SQLite world: an ambiguity's
   evidence is exactly the PC's known fact (never an unknown or creator-only
   one); a near request is category-filtered; inferred and cast mentions
   yield none; an empty result yields `()`.

N, J, P, Rd, Rc are pure; Q builds a fresh temp database
(`WORLD_ENGINE_DATABASE_URL` set before any world_engine import). Vacuity
guards: N1 must have produced candidates, Q1 must have produced a request.
FAILURES list, print FAIL lines, exit 1.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _surfaces():
    from world_engine.name_index import NameSurface

    def name(text: str, entity_id: str, entity_type: str) -> NameSurface:
        return NameSurface(text=text, entity_id=entity_id, entity_name=text, entity_type=entity_type,
                           source="name", fact_id=None)

    return (
        name("Maelis", "m", "character"),
        name("La Reine Grise", "g", "character"),
        name("Reine Ysolde", "y", "character"),
        name("Porte de Vesk", "p", "location"),
    )


def check_near() -> int:
    from world_engine.lore_resolve import near_in_surfaces

    surfaces = _surfaces()

    def scored(found):
        return [(c.entity_id, c.score) for c in found]

    maelys = scored(near_in_surfaces("Maelys", surfaces))
    if maelys != [("m", 83)]:
        fail(f"N1: 'Maelys' -> {maelys}, expected [('m', 83)]")
    reine = scored(near_in_surfaces("reine", surfaces))
    if reine != [("g", 63), ("y", 59)]:
        fail(f"N1: 'reine' -> {reine}, expected [('g', 63), ('y', 59)]")

    excluded = scored(near_in_surfaces("reine", surfaces, exclude_ids=frozenset({"g"})))
    if excluded != [("y", 59)]:
        fail(f"N2: 'reine' excluding g -> {excluded}, expected [('y', 59)]")

    vesk = near_in_surfaces("Vesk", surfaces)
    if not any(c.entity_id == "p" and c.entity_type == "location" for c in vesk):
        fail(f"N3: 'Vesk' -> {[(c.entity_id, c.entity_type) for c in vesk]}, expected p as a location")

    return len(maelys) + len(reine)


# --- judge, parse, render, record (pure) --------------------------------------

_DECLARATION = "Je vais voir la Comtesse pour lui rendre sa bague. Et Maelys."


def _requests():
    from world_engine.day_choice import Candidate, ChoiceRequest
    from world_engine.day_extract import Mention

    mention = Mention(category="person", surface_form="Maelys", kind="named")
    a = Candidate("a", "Maelis", ("Elle a perdu une bague au marché de Vesk.",), ("f1",))
    b = Candidate("b", "Ilune", ("Elle règne sur le val d'Orre.",), ("f2",))
    ambiguous = ChoiceRequest(mention=mention, trigger="ambiguous", candidates=(a, b))
    near = ChoiceRequest(mention=mention, trigger="near",
                         candidates=(Candidate("a", "Maelis", (), ()),))
    return ambiguous, near


def _answer(choix, extrait="", raison="parce que"):
    return {"choix": choix, "extrait": extrait, "raison": raison}


def check_judge():
    from world_engine.day_choice import judge_choice

    ambiguous, near = _requests()

    def expect(label, request, answer, verdict, entity_id, detail):
        got = judge_choice(request, answer, _DECLARATION)
        if (got.verdict, got.entity_id, got.detail) != (verdict, entity_id, detail):
            fail(f"{label} ({request.trigger}): got {(got.verdict, got.entity_id, got.detail)}, "
                 f"expected {(verdict, entity_id, detail)}")
        return got

    for request in (ambiguous, near):
        expect("J1", request, _answer(0, "Maelys"), "declined", None, None)
        expect("J2", request, _answer(3, "Maelys"), "rejected", None, "candidate out of range")
        expect("J3", request, _answer(1, "Va"), "rejected", "a", "excerpt too short")
    expect("J4", ambiguous, _answer(1, "Maelys"), "rejected", "a",
           "excerpt not in the chosen candidate's facts")
    expect("J4", near, _answer(1, "Maelys"), "accepted", "a", None)
    expect("J5", ambiguous, _answer(1, "Elle"), "rejected", "a",
           "excerpt does not single out the chosen candidate")
    j6 = expect("J6", ambiguous, _answer(1, "« a perdu une bague. »"), "accepted", "a", None)
    expect("J7", ambiguous, _answer(2, "a perdu une bague"), "rejected", "b",
           "excerpt not in the chosen candidate's facts")
    expect("J8", near, _answer(1, "Varek"), "rejected", "a", "excerpt not found")
    return j6


def check_parse() -> None:
    from world_engine.day_choice import parse_answer
    from world_engine.llm_parse import LlmParseError

    got = parse_answer('{"choix": 1, "extrait": "a", "raison": "b"}')
    if got != {"choix": 1, "extrait": "a", "raison": "b"}:
        fail(f"P: parse_answer returned {got}")
    for raw in ('{"choix": true, "extrait": "a", "raison": "b"}',
                '{"choix": 1, "raison": "b"}',
                "nope"):
        try:
            parse_answer(raw)
        except LlmParseError:
            continue
        fail(f"P: parse_answer({raw!r}) did not raise LlmParseError")


def check_render() -> None:
    from world_engine.day_choice import render_candidates

    ambiguous, near = _requests()
    got = render_candidates(near)
    if got != "1. Maelis\n   Le personnage ne sait rien de plus sur lui.":
        fail(f"Rd: near render {got!r}")
    got = render_candidates(ambiguous)
    for line in ("   Ce que le personnage sait :",
                 "   - Elle a perdu une bague au marché de Vesk."):
        if line not in got:
            fail(f"Rd: ambiguous render lacks {line!r}: {got!r}")


_RECORD_KEYS = {
    "category", "surface_form", "trigger", "candidate_ids", "evidence_fact_ids", "verdict",
    "chosen_entity_id", "excerpt", "reason", "verdict_detail", "attempts",
}


def check_record(j6) -> None:
    from world_engine.day_choice import ChoiceVerdict, record_of

    ambiguous, _ = _requests()
    declined = record_of(ambiguous, ChoiceVerdict("declined", "a", None, None, None), 1)
    if declined["chosen_entity_id"] is not None:
        fail(f"Rc: declined record chose {declined['chosen_entity_id']!r}")
    record = record_of(ambiguous, j6, 1)
    if set(record) != _RECORD_KEYS:
        fail(f"Rc: record keys {sorted(record)}")
    if record["evidence_fact_ids"] != ["f1", "f2"]:
        fail(f"Rc: evidence_fact_ids {record['evidence_fact_ids']}")
    if record["chosen_entity_id"] != "a" or record["attempts"] != 1:
        fail(f"Rc: chosen/attempts {record['chosen_entity_id']!r}/{record['attempts']!r}")


# --- requests (temp SQLite fixture) -------------------------------------------

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


def _shape(requests):
    return [(r.trigger, [c.entity_id for c in r.candidates]) for r in requests]


def check_requests(engine) -> int:
    from sqlmodel import Session

    from world_engine.day_choice import choice_requests
    from world_engine.day_concordance import (
        AmbiguousMention, CastMention, ConcordanceResult, UnmatchedMention,
    )
    from world_engine.day_extract import Mention
    from world_engine.writes.facets import ScopeChoice, add_entity_fact
    from world_engine.writes.knowledge import write_knowledge

    def result(ambiguous=(), unmatched=(), cast=()):
        return ConcordanceResult(matched=(), cast=tuple(cast), ambiguous=tuple(ambiguous),
                                 unmatched=tuple(unmatched), skipped_rungs=())

    with Session(engine) as session:
        world, entity = _world(session, "Q World")
        mini = entity("character", "Mini")
        maelis = entity("character", "Maelis")
        ilune = entity("character", "Ilune")

        def fact(content, scope):
            return add_entity_fact(session, entity_id=maelis.id, facet="histoire",
                                   content=content, created_by="check", scope=scope)

        known = fact("Elle a perdu une bague.", ScopeChoice("world"))
        unknown = fact("Elle cache un poignard.", ScopeChoice("none"))
        secret = fact("Secret de créatrice.", ScopeChoice("world"))
        write_knowledge(session, entity_id=maelis.id, fact_id=secret.id, subject="creator_meta",
                        level="unaware", is_secret=True, changed_by="check")
        session.flush()
        pc = SimpleNamespace(id=mini.id, world_id=world.id)

        person = Mention(category="person", surface_form="Maelys", kind="named")
        q1 = choice_requests(
            result(ambiguous=[AmbiguousMention(person, (maelis.id, ilune.id))]), pc, session)
        if _shape(q1) != [("ambiguous", [maelis.id, ilune.id])]:
            fail(f"Q1: requests {_shape(q1)}")
        else:
            m = q1[0].candidates[0]
            if m.fact_ids != (known.id,):
                labels = {known.id: "known", unknown.id: "unknown", secret.id: "creator-only"}
                fail(f"Q1: Maelis evidence {[labels.get(f, f) for f in m.fact_ids]}, "
                     f"expected exactly the known fact")
            if m.facts != ("Elle a perdu une bague.",):
                fail(f"Q1: Maelis facts {m.facts}")

        q2 = choice_requests(
            result(unmatched=[UnmatchedMention(person, ("named_exact",))]), pc, session)
        if _shape(q2) != [("near", [maelis.id])]:
            fail(f"Q2: person 'Maelys' -> {_shape(q2)}")
        place = Mention(category="place", surface_form="Maelys", kind="named")
        q2p = choice_requests(
            result(unmatched=[UnmatchedMention(place, ("named_exact",))]), pc, session)
        if q2p != ():
            fail(f"Q2: place 'Maelys' produced {_shape(q2p)}")

        inferred = Mention(category="person", surface_form="Maelys", kind="inferred",
                           role_hint="marchande")
        q3 = choice_requests(
            result(unmatched=[UnmatchedMention(inferred, ("cast",))]), pc, session)
        if q3 != ():
            fail(f"Q3: inferred unmatched produced {_shape(q3)}")
        cast = CastMention(inferred, maelis.id, "cast", "role", (maelis.id, ilune.id))
        q3c = choice_requests(result(cast=[cast]), pc, session)
        if q3c != ():
            fail(f"Q3: cast produced {_shape(q3c)}")

        if choice_requests(result(), pc, session) != ():
            fail("Q4: empty result did not yield ()")
        session.rollback()
    return len(q1)


def main() -> int:
    engine = _fresh_engine()
    if check_near() == 0:
        fail("vacuity: N1 produced no candidates")
    check_record(check_judge())
    check_parse()
    check_render()
    if check_requests(engine) == 0:
        fail("vacuity: Q1 produced no request")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: day_choice — near_in_surfaces scores typos and shared tokens, honours "
        "exclude_ids, and returns every category (N1-N3); the judge follows the (b2) table "
        "(J1-J8); parse (P), render (Rd) and record (Rc) hold; requests carry only known "
        "evidence, filter by category, skip inferred/cast, and yield () when empty (Q1-Q4)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
