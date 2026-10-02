"""G1 check for TICKET-0101 (BRIEF-0101-A) — geographic links follow the tree.

DB-backed, self-contained fresh temp-file SQLite fixture (WORLD_ENGINE_
DATABASE_URL set BEFORE any world_engine import) — same idiom as
relation_orientation.py, so this check never touches Nia's real DB. Fixture
data is built through the REAL sanctioned writers (`write_relation`,
`spatial_author.link_locations`). Zero rows examined in any assertion is a
FAIL, never a vacuous pass.

Fixture: visitable locations V1, V2, V3; zone Z with active child C; P,
visitable at first, linked to V3 by `connects_to`, then given a child Q.

Five assertions:
  a. L1 at write: `connects_to` V1-Z and `borde` V1-V2 are refused
     (`ValueError`); `connects_to` V1-V2 and `borde` V1-Z are accepted;
     `connects_to` between a location and a character is refused.
  b. Derivation: `link_locations` writes `borde` for V2-Z and `connects_to`
     for V2-V3; a second call on the same pair returns the same row and
     writes no second one.
  c. V1, no retype across the pair: a `borde` row cannot become `ally`; an
     `ally` row cannot become `connects_to`.
  d. N1: once P has a child, `link_locations(V3, P)` retypes the existing
     row in place — same id, type `borde`, `change_history` one longer — and
     rewrites its fact to `borde_fact_content(...)`, the old content kept in
     the fact's `change_history`.
  e. The structural split: `borde` is in `RELATION_GRAPH_EXCLUDED_TYPES`,
     `is_social("borde")` is False, a born `borde` row has exactly one fact
     at `knows` and records no encounter; the two relation scans that spelled
     `!= "connects_to"` (lore_selectors.py, day_concordance.py) now exclude
     `MAP_TOPOLOGY_TYPES` and spell no such literal.

Named mutations: delete `_require_map_shape`'s derived-type raise -> (a);
drop `"borde"` from the tuple -> (e); delete `_refresh_map_content`'s call
-> (d); make `link_locations` skip its `find_map_relation` reuse -> (b).
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

FAILURES: list[str] = []
COUNTS: dict[str, int] = {}


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


def _seed(session):
    """V1, V2, V3, P visitable; Z with child C; one character H."""
    from world_engine.models import Entity, Location, World

    world = World(name="Zone Check", is_active=True)
    session.add(world)
    session.commit()
    session.refresh(world)
    ids: dict[str, str] = {}
    for label, parent in (("V1", None), ("V2", None), ("V3", None), ("P", None), ("Z", None), ("C", "Z")):
        entity = Entity(world_id=world.id, type="location", name=f"Lieu {label}")
        session.add(entity)
        session.flush()
        session.add(Location(id=entity.id, parent_location_id=ids.get(parent) if parent else None))
        session.commit()
        ids[label] = entity.id
    hero = Entity(world_id=world.id, type="character", name="Héros")
    session.add(hero)
    session.commit()
    ids["H"] = hero.id
    return world.id, ids


def _refused(session, label: str, **kwargs) -> int:
    from world_engine.writes.relations import write_relation

    try:
        write_relation(session, mode="set", value=50, direction="mutual", **kwargs)
    except ValueError:
        session.rollback()
        return 1
    session.rollback()
    fail(f"{label}: write accepted")
    return 0


def check_a_l1(session, world_id, ids) -> None:
    from world_engine.writes.relations import write_relation

    n = _refused(session, "(a) connects_to V1-Z", world_id=world_id, entity_a_id=ids["V1"],
                 entity_b_id=ids["Z"], type="connects_to")
    n += _refused(session, "(a) borde V1-V2", world_id=world_id, entity_a_id=ids["V1"],
                  entity_b_id=ids["V2"], type="borde")
    n += _refused(session, "(a) connects_to V1-character", world_id=world_id, entity_a_id=ids["V1"],
                  entity_b_id=ids["H"], type="connects_to")
    for a, b, t in (("V1", "V2", "connects_to"), ("V1", "Z", "borde")):
        rel = write_relation(session, mode="set", world_id=world_id, entity_a_id=ids[a],
                             entity_b_id=ids[b], type=t, value=50, direction="mutual")
        session.commit()
        if rel.type != t:
            fail(f"(a) {a}-{b} stored as {rel.type!r}, expected {t!r}")
        n += 1
    if n != 5:
        fail(f"(a) expected 3 refusals and 2 writes, got {n} outcomes")
    COUNTS["a"] = n


def check_b_derivation(session, world_id, ids) -> None:
    from sqlmodel import select

    from world_engine.models import Relation
    from world_engine.spatial_author import link_locations

    seen = 0
    for a, b, expected in (("V2", "Z", "borde"), ("V2", "V3", "connects_to")):
        first = link_locations(session, world_id=world_id, entity_a_id=ids[a], entity_b_id=ids[b], changed_by="check")
        session.commit()
        again = link_locations(session, world_id=world_id, entity_a_id=ids[b], entity_b_id=ids[a], changed_by="check")
        session.commit()
        if first.type != expected:
            fail(f"(b) link_locations({a}, {b}) wrote {first.type!r}, expected {expected!r}")
        if again.id != first.id:
            fail(f"(b) a second link_locations({b}, {a}) returned a different row")
        rows = session.exec(select(Relation).where(
            ((Relation.entity_a_id == ids[a]) & (Relation.entity_b_id == ids[b]))
            | ((Relation.entity_a_id == ids[b]) & (Relation.entity_b_id == ids[a]))
        )).all()
        if len(rows) != 1:
            fail(f"(b) {a}-{b} carries {len(rows)} relation rows, expected 1")
        seen += len(rows)
    COUNTS["b"] = seen


def check_c_no_cross_retype(session, world_id, ids) -> None:
    from sqlmodel import select

    from world_engine.models import Entity, Relation
    from world_engine.writes.relations import write_relation

    borde = session.exec(select(Relation).where(Relation.type == "borde")).first()
    other = Entity(world_id=world_id, type="character", name="Autre")
    session.add(other)
    session.commit()
    ally = write_relation(session, mode="set", world_id=world_id, entity_a_id=ids["H"],
                          entity_b_id=other.id, type="ally", value=60)
    session.commit()
    n = 0
    for rel, new_type, direction in ((borde, "ally", "a_to_b"), (ally, "connects_to", "mutual")):
        if rel is None:
            fail("(c) fixture row missing")
            continue
        before = rel.type
        try:
            write_relation(session, mode="set", relation_id=rel.id, type=new_type, value=50, direction=direction)
        except ValueError:
            n += 1
        else:
            fail(f"(c) a {before} row was retyped into {new_type}")
        session.rollback()
        session.refresh(rel)
        if rel.type != before:
            fail(f"(c) refused retype still changed the row to {rel.type!r}")
    COUNTS["c"] = n


def check_d_in_place_retype(session, world_id, ids) -> None:
    from world_engine.models import Entity, Location
    from world_engine.prose_render import entity_token
    from world_engine.relation_orientation import borde_fact_content
    from world_engine.spatial_author import link_locations
    from world_engine.writes.relations import lien_fact_of, write_relation

    rel = write_relation(session, mode="set", world_id=world_id, entity_a_id=ids["V3"],
                         entity_b_id=ids["P"], type="connects_to", value=50, direction="mutual")
    session.commit()
    rel_id, history_before = rel.id, len(rel.change_history or [])
    fact = lien_fact_of(session, rel)
    fact_history_before = len(fact.change_history or []) if fact else -1

    child = Entity(world_id=world_id, type="location", name="Lieu Q")
    session.add(child)
    session.flush()
    session.add(Location(id=child.id, parent_location_id=ids["P"]))
    session.commit()

    out = link_locations(session, world_id=world_id, entity_a_id=ids["V3"], entity_b_id=ids["P"], changed_by="check")
    session.commit()
    session.refresh(out)
    if out.id != rel_id:
        fail("(d) the retype wrote a new row instead of changing the existing one")
    if out.type != "borde":
        fail(f"(d) V3-P is {out.type!r} after P gained a child, expected 'borde'")
    if len(out.change_history or []) != history_before + 1:
        fail("(d) relation change_history did not grow by one")
    fact = lien_fact_of(session, out)
    if fact is None:
        fail("(d) the retyped row lost its fact")
        return
    session.refresh(fact)
    expected = borde_fact_content(entity_token(ids["V3"], "Lieu V3"), entity_token(ids["P"], "Lieu P"))
    if fact.content_raw != expected:
        fail(f"(d) fact content {fact.content_raw!r}, expected {expected!r}")
    if len(fact.change_history or []) != fact_history_before + 1:
        fail("(d) fact change_history did not keep the previous content")
    COUNTS["d"] = 1 + len(out.change_history or [])


def check_e_structural(session, world_id, ids) -> None:
    from sqlmodel import select

    from world_engine.models import Fact, Relation, Rencontre
    from world_engine.relation_orientation import RELATION_GRAPH_EXCLUDED_TYPES, is_social

    n = 0
    if "borde" not in RELATION_GRAPH_EXCLUDED_TYPES:
        fail("(e) 'borde' missing from RELATION_GRAPH_EXCLUDED_TYPES")
    if is_social("borde"):
        fail("(e) is_social('borde') is True")
    rows = session.exec(select(Relation).where(Relation.type == "borde")).all()
    for rel in rows:
        facts = session.exec(select(Fact).where(Fact.relation_id == rel.id)).all()
        if len(facts) != 1 or facts[0].default_level != "knows":
            fail(f"(e) borde row {rel.id} has {len(facts)} fact(s), expected one at 'knows'")
        n += 1
    encounters = session.exec(select(Rencontre)).all()
    location_ids = {ids[k] for k in ("V1", "V2", "V3", "P", "Z", "C")}
    for row in encounters:
        ends = {row.entity_lo_id, row.entity_hi_id}
        if ends & location_ids:
            fail("(e) an encounter was recorded between locations")
    for rel_path in ("lore_selectors.py", "day_concordance.py"):
        text = (SRC / "world_engine" / rel_path).read_text(encoding="utf-8")
        if 'Relation.type != "connects_to"' in text:
            fail(f"(e) {rel_path} still excludes connects_to alone")
        if "Relation.type.not_in(MAP_TOPOLOGY_TYPES)" not in text:
            fail(f"(e) {rel_path} does not exclude MAP_TOPOLOGY_TYPES")
        n += 1
    COUNTS["e"] = n


def main() -> int:
    engine = _fresh_engine()
    from sqlmodel import Session as DbSession

    with DbSession(engine) as session:
        world_id, ids = _seed(session)
        check_a_l1(session, world_id, ids)
        check_b_derivation(session, world_id, ids)
        check_c_no_cross_retype(session, world_id, ids)
        check_d_in_place_retype(session, world_id, ids)
        check_e_structural(session, world_id, ids)

    for key in ("a", "b", "c", "d", "e"):
        if not COUNTS.get(key):
            fail(f"({key}) vacuous-proof: zero rows examined")

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: zone_map_links — "
        f"(a) L1 at write [{COUNTS['a']}], (b) derived type, no duplicate [{COUNTS['b']}], "
        f"(c) no retype across the pair [{COUNTS['c']}], (d) in-place retype [{COUNTS['d']}], "
        f"(e) structural split [{COUNTS['e']}]"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
