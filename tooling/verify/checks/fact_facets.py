"""G1 check for TICKET-0091 (BRIEF-0091-A) — the facet registry and the
facet-bearing fact chokepoint.

R1  `facets.py::FACETS` matches the C-01 table exactly: names in display
    order, family, granularity, preset, aspects — plus the derived sets
    `DESCRIPTIVE_FACETS`, `KNOWLEDGE_SECTION_FACETS` and `TYPED_FACET_BY_FK`.
    Labels and descriptions are UI help; no rule reads them.
R2  AST: every `create_fact(` call in `src/` and `scripts/` passes a
    `facet=` keyword. Vacuity-guarded: the three known production callers
    (`writes/knowledge.py`, `writes/relations.py`, `writes/facets.py`)
    must be found.
R3  AST: a `create_fact(` whose `facet=` is a descriptive literal (a
    `DESCRIPTIVE_FACETS` name) or a non-literal appears only in
    `writes/facets.py`. A negative-existence rule over a possibly-empty
    search space (the `lore_isolation.py` R5-R7 precedent): finding nothing
    IS the pass, so it carries no vacuity guard of its own.
R4  Fixture: C-02's case table (facet x typed FK), run against the real
    `writes/facts.py::create_fact` on a fresh temp-file SQLite database
    (WORLD_ENGINE_DATABASE_URL set before any world_engine import — never
    Nia's DB). Every `ok` row is flushed and its stored facet/aspect read
    back; every refusal row must raise `ValueError`.
R5  Fixture (BRIEF-0091-E, C-05): `writes/facets.py::add_entity_fact`
    refuses a second fact on a `bloc` facet with the same aspect about the
    same entity (`ValueError`), and `write_entity_facets` splits an
    affirmation string into one fact per non-empty line, writes a hidden
    `coutume` with no default and a visible one with a `location` default at
    the location itself, and turns `creator_meta` into a `histoire` fact with
    no default plus one `unaware`, `is_secret` knowledge row for the entity
    itself.
R6  Fixture (BRIEF-0091-D, C-09 default-row filter): a descriptive fact
    with a `world` default is absent from
    `knowledge_resolve.resolve_default_rows`; an `information` fact with the
    same default is present — the speakable knowledge section never
    receives what is said of an entity (Q13a).
R7  AST (AMENDMENT-0091-01): a keyword `include_creator_only` whose value is
    not the literal `False` appears only in
    `src/world_engine/lore_selectors.py` (the creator's dossier). A
    negative-existence rule (the R3 precedent): finding nothing IS the pass;
    its vacuity guard is on the scan itself (files parsed > 0).
R8  Fixture (AMENDMENT-0091-01): a creator-only fact (a `creator_meta`
    note) is absent from `facet_reads.facts_of` and `known_facts_of`,
    present with `include_creator_only=True`, and reported by
    `creator_only_fact_ids`; an ordinary fact of the same entity is present
    in all three reads and not reported.

FAILURES list, print FAIL lines, exit 1.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
FACET_WRITER = "src/world_engine/writes/facets.py"
CREATOR_ONLY_READER = "src/world_engine/lore_selectors.py"
KNOWN_CALLERS = (
    "src/world_engine/writes/knowledge.py",
    "src/world_engine/writes/relations.py",
    # The seed's create_fact moved into writes/knowledge.py::upsert_knowledge_row
    # (TICKET-0091, AMENDMENT-0091-05); writes/facets.py is the third caller.
    "src/world_engine/writes/facets.py",
)

# C-01, verbatim: (name, family, granularity, preset, aspects), display order.
EXPECTED_FACETS = (
    ("appellation", "identite", "affirmation", "location", ()),
    ("statut", "identite", "affirmation", "location", ()),
    ("physique", "identite", "bloc", "rencontre", ()),
    ("tenue", "identite", "bloc", "none", ()),
    ("description", "identite", "bloc", "public_world", ()),
    ("reputation", "identite", "affirmation", "location", ()),
    ("histoire", "interiorite", "affirmation", "none", ()),
    ("personnalite", "interiorite", "affirmation", "none", ()),
    ("preference", "interiorite", "affirmation", "none", ()),
    ("aversion", "interiorite", "affirmation", "none", ()),
    ("doctrine", "collectif", "bloc", "world", ()),
    ("organisation", "collectif", "bloc", "none", ()),
    ("tension", "collectif", "affirmation", "none", ()),
    ("visee", "collectif", "affirmation", "none", ()),
    ("coutume", "collectif", "affirmation", "location", ("values",)),
    ("information", "monde", "affirmation", "none", ()),
    ("lien", "monde", "typed", "typed", ()),
    ("evenement", "monde", "typed", "typed", ()),
    ("loi", "monde", "typed", "typed", ()),
)

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


# --- R1 -----------------------------------------------------------------------

def check_registry() -> None:
    from world_engine import facets

    actual = tuple(
        (s.name, s.family, s.granularity, s.preset, s.aspects) for s in facets.FACETS.values()
    )
    if actual != EXPECTED_FACETS:
        fail(f"R1: FACETS differs from the C-01 table: {actual!r}")
    if any(name != spec.name for name, spec in facets.FACETS.items()):
        fail("R1: a FACETS key differs from its spec's name")
    for spec in facets.FACETS.values():
        if (spec.family not in facets.FAMILIES or spec.granularity not in facets.GRANULARITIES
                or spec.preset not in facets.PRESETS):
            fail(f"R1: facet {spec.name!r} uses a value outside FAMILIES/GRANULARITIES/PRESETS")
    descriptive = {n for n, f, *_ in EXPECTED_FACETS if f in ("identite", "interiorite", "collectif")}
    if len(descriptive) != 15 or facets.DESCRIPTIVE_FACETS != frozenset(descriptive):
        fail(f"R1: DESCRIPTIVE_FACETS is {sorted(facets.DESCRIPTIVE_FACETS)!r}")
    if facets.KNOWLEDGE_SECTION_FACETS != frozenset({"information", "lien", "evenement", "loi"}):
        fail(f"R1: KNOWLEDGE_SECTION_FACETS is {sorted(facets.KNOWLEDGE_SECTION_FACETS)!r}")
    if facets.TYPED_FACET_BY_FK != {"relation_id": "lien", "event_id": "evenement",
                                    "world_law_id": "loi"}:
        fail(f"R1: TYPED_FACET_BY_FK is {facets.TYPED_FACET_BY_FK!r}")
    try:
        facets.facet_spec("nope")
        fail("R1: facet_spec of an unknown name did not raise ValueError")
    except ValueError:
        pass
    for raw, expected in (("  Values ", "values"), ("", None), ("   ", None), (None, None)):
        if facets.normalize_aspect(raw) != expected:
            fail(f"R1: normalize_aspect({raw!r}) != {expected!r}")


# --- R2 / R3 --------------------------------------------------------------------

def _create_fact_calls():
    """Yield (repo-relative path, call node) for every `create_fact(` call
    (bare name or attribute) in src/ and scripts/."""
    for base in (SRC, SCRIPTS):
        for path in sorted(base.rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as exc:
                fail(f"{path}: SyntaxError: {exc}")
                continue
            rel = path.relative_to(ROOT).as_posix()
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = func.id if isinstance(func, ast.Name) else (
                    func.attr if isinstance(func, ast.Attribute) else None)
                if name == "create_fact":
                    yield rel, node


def check_call_sites() -> None:
    from world_engine.facets import DESCRIPTIVE_FACETS

    seen: set[str] = set()
    for rel, node in _create_fact_calls():
        seen.add(rel)
        facet_kw = next((kw for kw in node.keywords if kw.arg == "facet"), None)
        if facet_kw is None:
            fail(f"R2: {rel}:{node.lineno} -- create_fact( without a facet= keyword")
            continue
        value = facet_kw.value
        literal = value.value if isinstance(value, ast.Constant) else None
        descriptive_or_dynamic = not isinstance(literal, str) or literal in DESCRIPTIVE_FACETS
        if descriptive_or_dynamic and rel != FACET_WRITER:
            fail(
                f"R3: {rel}:{node.lineno} -- create_fact(facet={ast.unparse(value)}) is a "
                f"descriptive or non-literal facet outside {FACET_WRITER}"
            )
    missing = [c for c in KNOWN_CALLERS if c not in seen]
    if missing:
        fail(f"R2 vacuous-proof: known create_fact callers not found by the scan: {missing}")


# --- R4 -------------------------------------------------------------------------

def check_case_table(engine) -> None:
    from sqlmodel import Session as DbSession

    from world_engine.models import Entity, Event, Fact, Relation, World, WorldLaw
    from world_engine.writes.facts import create_fact

    with DbSession(engine) as session:
        world = World(name="Facet Check World", is_active=True)
        session.add(world)
        session.commit()
        wid = world.id
        a = Entity(world_id=wid, type="character", name="A")
        b = Entity(world_id=wid, type="character", name="B")
        session.add_all([a, b])
        session.commit()
        rel = Relation(world_id=wid, entity_a_id=a.id, entity_b_id=b.id, type="controls")
        event = Event(world_id=wid, title="an event")
        law = WorldLaw(world_id=wid, text_="a law")
        session.add_all([rel, event, law])
        session.commit()
        fks = {"relation_id": rel.id, "event_id": event.id, "world_law_id": law.id}

        cases = [
            # (label, facet, typed FK name or None, expected ok)
            ("None facet, free", None, None, False),
            ("None facet, relation", None, "relation_id", False),
            ("unknown facet", "nope", None, False),
            ("lien + relation", "lien", "relation_id", True),
            ("lien, free", "lien", None, False),
            ("evenement + event", "evenement", "event_id", True),
            ("loi + world_law", "loi", "world_law_id", True),
            ("information, free", "information", None, True),
            ("descriptive, free", "coutume", None, True),
            ("information + relation", "information", "relation_id", False),
            ("information + event", "information", "event_id", False),
            ("descriptive + world_law", "physique", "world_law_id", False),
            ("evenement + relation", "evenement", "relation_id", False),
        ]
        for label, facet, fk, expect_ok in cases:
            kwargs = {fk: fks[fk]} if fk else {}
            try:
                fact = create_fact(
                    session, world_id=wid, content=label, created_by="check",
                    facet=facet, aspect="  Values " if facet == "coutume" else None, **kwargs,
                )
            except ValueError:
                if expect_ok:
                    fail(f"R4: case {label!r} raised ValueError, expected ok")
                continue
            if not expect_ok:
                fail(f"R4: case {label!r} was accepted, expected ValueError")
                session.rollback()
                continue
            session.commit()
            stored = session.get(Fact, fact.id)
            if stored is None or stored.facet != facet:
                fail(f"R4: case {label!r} stored facet {getattr(stored, 'facet', None)!r}")
            elif facet == "coutume" and stored.aspect != "values":
                fail(f"R4: aspect not normalized on {label!r}: {stored.aspect!r}")


# --- R5 -------------------------------------------------------------------------

def check_entity_facets_writer(engine) -> None:
    from sqlmodel import Session as DbSession, select

    from world_engine.models import Entity, FactDefault, FactParticipant, Knowledge, World
    from world_engine.writes.facets import add_entity_fact, write_entity_facets
    from world_engine.prose_render import fact_text

    with DbSession(engine) as session:
        world = World(name="R5 World", is_active=False)  # one active world per DB
        session.add(world)
        session.commit()
        wid = world.id
        npc = Entity(world_id=wid, type="character", name="R5 NPC")
        place = Entity(world_id=wid, type="location", name="R5 Place")
        session.add_all([npc, place])
        session.commit()

        add_entity_fact(session, entity_id=npc.id, facet="physique", content="grand", created_by="check")
        session.commit()
        try:
            add_entity_fact(session, entity_id=npc.id, facet="physique", content="petit", created_by="check")
            fail("R5: a second physique fact on the same entity was accepted")
        except ValueError:
            session.rollback()

        facts = write_entity_facets(session, entity_id=npc.id, created_by="check", facets={
            "aversion": "le soleil\n\n  la mer  \n", "creator_meta": "un traître", "tenue": "",
        })
        session.commit()
        aversions = [fact_text(session, f) for f in facts if f.facet == "aversion"]
        if aversions != ["le soleil", "la mer"]:
            fail(f"R5: aversion string not split into one fact per line: {aversions!r}")
        meta = [f for f in facts if f.facet == "histoire"]
        if len(facts) != 3 or len(meta) != 1:
            fail(f"R5: write_entity_facets created {[f.facet for f in facts]!r}")
        else:
            rows = session.exec(select(Knowledge).where(Knowledge.fact_id == meta[0].id)).all()
            if [(k.entity_id, k.level, k.is_secret, k.subject) for k in rows] != [
                    (npc.id, "unaware", True, "creator_meta")]:
                fail("R5: creator_meta is not one unaware, secret knowledge row of its own entity")
            if session.exec(select(FactDefault).where(FactDefault.fact_id == meta[0].id)).first():
                fail("R5: creator_meta fact carries a default")
        for fact in facts:
            if session.exec(select(FactParticipant.entity_id).where(
                    FactParticipant.fact_id == fact.id)).all() != [npc.id]:
                fail(f"R5: fact {fact_text(session, fact)!r} does not have the entity as its one participant")

        customs = write_entity_facets(session, entity_id=place.id, created_by="check", facets={
            "coutume": [
                {"aspect": " Values ", "content": "on salue", "hidden": False},
                {"aspect": None, "content": "un passage secret", "hidden": True},
            ],
        })
        session.commit()
        scopes = [
            [(d.scope_type, d.scope_id, d.level) for d in session.exec(
                select(FactDefault).where(FactDefault.fact_id == f.id)).all()]
            for f in customs
        ]
        if scopes != [[("location", place.id, "knows")], []]:
            fail(f"R5: coutume defaults are {scopes!r}")
        if [f.aspect for f in customs] != ["values", None]:
            fail(f"R5: coutume aspects are {[f.aspect for f in customs]!r}")


# --- R6 -------------------------------------------------------------------------

def check_default_rows_filter(engine) -> None:
    from sqlmodel import Session as DbSession

    from world_engine.knowledge_resolve import resolve_default_rows
    from world_engine.models import Entity, World
    from world_engine.writes.facts import attach_participants, create_fact, create_fact_default

    with DbSession(engine) as session:
        world = World(name="R6 World", is_active=False)  # one active world per DB
        session.add(world)
        session.commit()
        wid = world.id
        perceiver = Entity(world_id=wid, type="character", name="Perceiver")
        subject = Entity(world_id=wid, type="character", name="Subject")
        session.add_all([perceiver, subject])
        session.commit()

        fact_ids = {}
        for facet in ("physique", "information"):
            fact = create_fact(
                session, world_id=wid, content=f"R6 {facet}", created_by="check", facet=facet,
            )
            session.flush()
            attach_participants(session, fact=fact, entity_ids=[subject.id])
            create_fact_default(
                session, world_id=wid, fact_id=fact.id, scope_type="world", scope_id=None,
                level="knows", created_by="check",
            )
            session.commit()
            fact_ids[facet] = fact.id

        rows = resolve_default_rows(session, perceiver.id, set())
        present = {row.fact_id for row in rows}
        if fact_ids["physique"] in present:
            fail("R6: a descriptive (physique) fact with a world default reached resolve_default_rows")
        if fact_ids["information"] not in present:
            fail("R6: an information fact with a world default is missing from resolve_default_rows")


# --- R7 -------------------------------------------------------------------------

def check_creator_only_opt_in() -> None:
    parsed = 0
    for base in (SRC, SCRIPTS):
        for path in sorted(base.rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as exc:
                fail(f"{path}: SyntaxError: {exc}")
                continue
            parsed += 1
            rel = path.relative_to(ROOT).as_posix()
            if rel == CREATOR_ONLY_READER:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                for kw in node.keywords:
                    if kw.arg != "include_creator_only":
                        continue
                    if isinstance(kw.value, ast.Constant) and kw.value.value is False:
                        continue
                    fail(
                        f"R7: {rel}:{node.lineno} -- include_creator_only="
                        f"{ast.unparse(kw.value)} outside {CREATOR_ONLY_READER}"
                    )
    if parsed == 0:
        fail("R7 vacuous-proof: no source file parsed")


# --- R8 -------------------------------------------------------------------------

def check_creator_only_reads(engine) -> None:
    from sqlmodel import Session as DbSession

    from world_engine.facet_reads import creator_only_fact_ids, facts_of, known_facts_of
    from world_engine.prose_render import fact_text
    from world_engine.models import Entity, World
    from world_engine.writes.facets import write_entity_facets

    with DbSession(engine) as session:
        world = World(name="R8 World", is_active=False)  # one active world per DB
        session.add(world)
        session.commit()
        npc = Entity(world_id=world.id, type="character", name="R8 NPC")
        session.add(npc)
        session.commit()
        facts = write_entity_facets(session, entity_id=npc.id, created_by="check", facets={
            "histoire": "ancien soldat", "creator_meta": "un traitre",
        })
        session.commit()
        by_content = {fact_text(session, f): f.id for f in facts}
        plain, meta = by_content.get("ancien soldat"), by_content.get("un traitre")
        if plain is None or meta is None:
            fail(f"R8: fixture facts not written: {sorted(by_content)!r}")
            return

        def ids(rows):
            return {row.fact_id for row in rows}

        default_read = ids(facts_of(session, entity_id=npc.id, facets=("histoire",)))
        known_read = ids(known_facts_of(
            session, perceiver_id=npc.id, entity_id=npc.id, facets=("histoire",)))
        dossier_read = ids(facts_of(
            session, entity_id=npc.id, facets=("histoire",), include_creator_only=True))
        if default_read != {plain}:
            fail(f"R8: facts_of returned {default_read!r}, expected only the ordinary fact")
        if known_read != {plain}:
            fail(f"R8: known_facts_of returned {known_read!r}, expected only the ordinary fact")
        if dossier_read != {plain, meta}:
            fail("R8: facts_of(include_creator_only=True) does not return both facts")
        if creator_only_fact_ids(session, [plain, meta]) != {meta}:
            fail("R8: creator_only_fact_ids does not report exactly the creator note")


def main() -> int:
    engine = _fresh_engine()
    check_registry()
    check_call_sites()
    check_case_table(engine)
    check_entity_facets_writer(engine)
    check_default_rows_filter(engine)
    check_creator_only_opt_in()
    check_creator_only_reads(engine)

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: fact_facets — FACETS matches C-01, every create_fact( passes a facet, "
        "descriptive/dynamic facets stay in writes/facets.py, C-02's case table holds, "
        "the entity-fact writer guards blocs and writes customs and creator_meta, "
        "resolve_default_rows skips descriptive facts, "
        "and creator-only facts stay out of facet reads outside the dossier"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
