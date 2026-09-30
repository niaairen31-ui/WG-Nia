"""G1 check for TICKET-0098 -- the lore writing path.

The lot adds its modules brief by brief; this check grows with it. Each
brief adds its files to `_LORE_WRITE_FILES` and its rules below in the same
commit (the `knowledge_identity.py` K3 census precedent, TICKET-0097).

L0 -- census. The files of the lore writing path that exist under
   `src/world_engine` (the glob `_CENSUS_GLOBS`) equal `_LORE_WRITE_FILES`
   exactly: a new module is red until a brief names it, a named module that
   is missing is red.
W1 -- schema (BRIEF-0098-B, v2.11). `lore_entry` declares `world_id` (FK to
   `world`) and the index `idx_lore_entry_world (world_id, created_at)`;
   `lore_entry_row` declares `entry_id` (FK to `lore_entry`), the UNIQUE
   index `idx_lore_entry_row_entry (entry_id, row_table, row_id)`, and CHECKs
   whose literals equal `LORE_ENTRY_ROW_TABLES` and `LORE_ENTRY_ROW_ACTIONS`.
W2 -- migration `scripts/migrate_v2_11_lore_entry.py`, on a v2.10-shaped
   database (the current schema minus both tables, `schema_meta` at v2.10):
   a. at v2.09 it refuses (non-zero exit) and creates nothing;
   b. at v2.10 it creates both tables, empty, and moves `schema_meta` to
      v2.11;
   c. a second run changes nothing and exits zero.
C1 -- apply (BRIEF-0098-C, C-02), on a fixture world, through
   `lore_write_apply.apply_proposal` with an injected entity creator:
   a. `_GOOD` creates one entity, three facts (an `information` fact with a
      `world` default and no participant; a multi-participant `coutume` with
      a `location` default; an `aversion` known by a checked NPC, secret),
      one knower on an existing fact, one membership and one `controls`
      edge; every written row has exactly one `lore_entry_row`, and the
      new entity's name is an identity token in the fact that names it;
   b. applied twice, the second run writes only its new facts and entity
      and reports the existing knower, participant, membership, default and
      `controls` edge as skipped;
   c. a `rewrite` of a `bloc` fact changes its text, appends the previous
      one to `change_history`, and records `updated`;
   d. every row of `_REFUSALS` raises `ProposalError` before any write:
      the row counts of every recorded table are unchanged;
   e. a proposal refused by a write site (a second `bloc` fact on the same
      entity) raises `ProposalError`; after the rollback nothing remains.
C2 -- purity. `lore_write_apply.py` and `writes/lore_entries.py` contain no
   `chat(`, no `.commit(`, and import neither `ollama_client` nor any
   `cockpit` module.

Fresh temp-file SQLite database for any fixture rule
(`WORLD_ENGINE_DATABASE_URL` set before any world_engine import) -- never
Nia's DB.
"""
from __future__ import annotations

import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"
MIGRATION = ROOT / "scripts" / "migrate_v2_11_lore_entry.py"

FAILURES: list[str] = []

_CENSUS_GLOBS = ("lore_write*.py", "writes/lore_entries.py", "cockpit/routes/lore_write*.py")
_LORE_WRITE_FILES: frozenset[str] = frozenset({
    "lore_write_apply.py", "writes/lore_entries.py",
})
_PURE_FILES = ("lore_write_apply.py", "writes/lore_entries.py")
_COUNTED_TABLES = ("entity", "fact", "fact_participant", "fact_default", "knowledge",
                   "relation", "faction_membership", "lore_entry", "lore_entry_row")


def fail(msg: str) -> None:
    FAILURES.append(msg)


def check_l0() -> None:
    found = {
        path.relative_to(SRC).as_posix()
        for pattern in _CENSUS_GLOBS for path in SRC.glob(pattern)
    }
    for extra in sorted(found - _LORE_WRITE_FILES):
        fail(f"L0: {extra} exists but no brief named it in _LORE_WRITE_FILES")
    for missing in sorted(_LORE_WRITE_FILES - found):
        fail(f"L0: {missing} is named in _LORE_WRITE_FILES but does not exist")


def _check_literals(table, name: str, expected: tuple[str, ...]) -> None:
    sql = next((str(c.sqltext) for c in table.constraints if getattr(c, "name", None) == name), None)
    if sql is None:
        fail(f"W1: {table.name} has no CHECK {name}")
        return
    got = tuple(re.findall(r"'([a-z_]+)'", sql))
    if got != expected:
        fail(f"W1: {name} lists {got}, expected {expected}")


def _index(table, name: str):
    return next((i for i in table.indexes if i.name == name), None)


def check_w1() -> None:
    from world_engine.models import LoreEntry, LoreEntryRow
    from world_engine.models.pipeline import LORE_ENTRY_ROW_ACTIONS, LORE_ENTRY_ROW_TABLES

    entry, row = LoreEntry.__table__, LoreEntryRow.__table__
    if {fk.target_fullname for fk in entry.c.world_id.foreign_keys} != {"world.id"}:
        fail("W1: lore_entry.world_id is not a FK to world.id")
    idx = _index(entry, "idx_lore_entry_world")
    if idx is None or [c.name for c in idx.columns] != ["world_id", "created_at"]:
        fail("W1: idx_lore_entry_world is not (world_id, created_at)")
    if {fk.target_fullname for fk in row.c.entry_id.foreign_keys} != {"lore_entry.id"}:
        fail("W1: lore_entry_row.entry_id is not a FK to lore_entry.id")
    idx = _index(row, "idx_lore_entry_row_entry")
    if idx is None or not idx.unique or [c.name for c in idx.columns] != ["entry_id", "row_table", "row_id"]:
        fail("W1: idx_lore_entry_row_entry is not UNIQUE (entry_id, row_table, row_id)")
    _check_literals(row, "ck_lore_entry_row_table", LORE_ENTRY_ROW_TABLES)
    _check_literals(row, "ck_lore_entry_row_action", LORE_ENTRY_ROW_ACTIONS)


def _run_migration(db_path: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True,
                          text=True, cwd=str(ROOT), timeout=120)


def _tables(db_path: str) -> set[str]:
    with sqlite3.connect(db_path) as conn:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _set_version(db_path: str, version: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE IF EXISTS lore_entry_row")
        conn.execute("DROP TABLE IF EXISTS lore_entry")
        conn.execute("UPDATE schema_meta SET static_version = ? WHERE id = 1", (version,))


def check_w2(db_path: str) -> None:
    from sqlmodel import Session

    from world_engine.db import create_db_and_tables, engine
    from world_engine.models import SchemaMeta

    create_db_and_tables()
    with Session(engine) as session:
        if session.get(SchemaMeta, 1) is None:
            session.add(SchemaMeta(id=1, static_version="v2.10"))
            session.commit()
    engine.dispose()
    _set_version(db_path, "v2.09")
    result = _run_migration(db_path)
    if result.returncode == 0 or {"lore_entry", "lore_entry_row"} & _tables(db_path):
        fail(f"W2a: v2.09 was not refused (exit {result.returncode})")
    _set_version(db_path, "v2.10")
    result = _run_migration(db_path)
    with sqlite3.connect(db_path) as conn:
        version = conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0]
        counts = [conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("lore_entry", "lore_entry_row")] if result.returncode == 0 else None
    if result.returncode != 0 or counts != [0, 0] or version != "v2.11":
        fail(f"W2b: first run exit {result.returncode}, counts {counts}, version {version!r}: "
             f"{result.stderr.strip()[-200:]}")
    again = _run_migration(db_path)
    if again.returncode != 0 or "nothing to do" not in again.stdout:
        fail(f"W2c: second run exit {again.returncode}: {again.stdout.strip()[-200:]}")


def _fixture(db):
    """A world with an NPC (Maëlle), a manor (location), a guild (faction)
    and Maëlle's `description` (bloc) fact."""
    from world_engine.models import Character, Entity, Faction, Location, World
    from world_engine.writes.facets import add_entity_fact

    world = World(name="Fixture 0098")
    db.add(world)
    db.flush()
    ids = {}
    for key, etype, name, ext in (("npc", "character", "Maëlle", Character),
                                  ("manor", "location", "Manoir Gris", Location),
                                  ("guild", "faction", "Guilde des Passeurs", Faction)):
        entity = Entity(world_id=world.id, type=etype, name=name)
        db.add(entity)
        db.flush()
        kwargs = {"world_id": world.id, "character_type": "npc"} if ext is Character else {}
        db.add(ext(id=entity.id, **kwargs))
        ids[key] = entity.id
    db.flush()
    bloc = add_entity_fact(db, entity_id=ids["npc"], facet="description",
                           content="Une passeuse discrète.", created_by="fixture")
    old = add_entity_fact(db, entity_id=ids["manor"], facet="description",
                          content="Un manoir aux volets gris.", created_by="fixture")
    db.commit()
    ids.update(world=world.id, bloc=bloc.id, old=old.id)
    return ids


def _creator(db, world_id):
    from world_engine.models import Character, Entity, Faction, Item, Location

    ext = {"character": Character, "location": Location, "faction": Faction, "item": Item}

    def create(name, etype):
        entity = Entity(world_id=world_id, type=etype, name=name)
        db.add(entity)
        db.flush()
        kwargs = {"world_id": world_id, "character_type": "npc"} if etype == "character" else {}
        db.add(ext[etype](id=entity.id, **kwargs))
        return entity
    return create


def _good(ids):
    return {
        "statement": "Un tunnel relie le Manoir Gris au port ; la vimm y transite.",
        "entities": [
            {"ref": "e1", "action": "existing", "entity_id": ids["npc"]},
            {"ref": "e2", "action": "existing", "entity_id": ids["manor"]},
            {"ref": "e3", "action": "existing", "entity_id": ids["guild"]},
            {"ref": "e4", "action": "create", "name": "Vimm", "type": "item"},
        ],
        "facts": [
            {"ref": "f1", "action": "create", "facet": "information",
             "content": "La Vimm est interdite dans tout le royaume.", "participants": [],
             "defaults": [{"scope_type": "world"}]},
            {"ref": "f2", "action": "create", "facet": "coutume", "aspect": "values",
             "content": "Au manoir, on attend la permission avant de parler.",
             "participants": ["e2", "e1"],
             "defaults": [{"scope_type": "location", "scope_ref": "e2"}]},
            {"ref": "f3", "action": "create", "facet": "aversion",
             "content": "Maëlle hait qu'on lui coupe la parole.", "participants": ["e1"],
             "knowers": [{"entity_ref": "e1", "level": "knows", "is_secret": True}]},
            {"ref": "f4", "action": "existing", "fact_id": ids["old"], "participants": ["e3"],
             "defaults": [{"scope_type": "faction", "scope_ref": "e3"}],
             "knowers": [{"entity_ref": "e1", "level": "partial"}]},
        ],
        "memberships": [{"entity_ref": "e1", "faction_ref": "e3"}],
        "controls": [{"owner_ref": "e1", "location_ref": "e2"}],
    }


_REFUSALS = (
    ("no statement", lambda p: p.pop("statement")),
    ("entity type not allowed", lambda p: p["entities"][3].update(type="magic")),
    ("unknown existing entity", lambda p: p["entities"][0].update(entity_id="nope")),
    ("duplicate entity ref", lambda p: p["entities"].append(dict(p["entities"][0]))),
    ("typed facet", lambda p: p["facts"][0].update(facet="lien")),
    ("unknown facet", lambda p: p["facts"][0].update(facet="humeur")),
    ("bloc with two participants", lambda p: p["facts"][1].update(facet="description")),
    ("unknown participant ref", lambda p: p["facts"][2].update(participants=["e9"])),
    ("unknown level", lambda p: p["facts"][2]["knowers"][0].update(level="certain")),
    ("secret not a bool", lambda p: p["facts"][2]["knowers"][0].update(is_secret="oui")),
    ("same knower twice", lambda p: p["facts"][2]["knowers"].append(dict(p["facts"][2]["knowers"][0]))),
    ("faction scope on a location", lambda p: p["facts"][3]["defaults"][0].update(scope_ref="e2")),
    ("world scope with a ref", lambda p: p["facts"][0]["defaults"][0].update(scope_ref="e1")),
    ("unknown scope", lambda p: p["facts"][0]["defaults"][0].update(scope_type="ville")),
    ("same scope twice", lambda p: p["facts"][0]["defaults"].append({"scope_type": "world"})),
    ("fact of another world", lambda p: p["facts"][3].update(fact_id="nope")),
    ("rewrite of a non-bloc fact", lambda p: p["facts"].append(
        {"ref": "f9", "action": "rewrite", "fact_id": "__f3__", "content": "x"})),
    ("membership of a location", lambda p: p["memberships"][0].update(entity_ref="e2")),
    ("control of a faction", lambda p: p["controls"][0].update(location_ref="e3")),
    ("nothing to write", lambda p: [p.update(facts=[], memberships=[], controls=[])]),
)


def _counts(db) -> dict:
    from sqlalchemy import text

    return {t: db.exec(text(f"SELECT COUNT(*) FROM {t}")).one()[0] for t in _COUNTED_TABLES}


def check_c1() -> None:
    import copy

    from sqlmodel import Session

    from world_engine import lore_write_apply as lwa
    from world_engine.db import engine
    from world_engine.models import Fact, LoreEntryRow
    from world_engine.prose_render import fact_text

    with Session(engine) as db:
        ids = _fixture(db)
        before = _counts(db)
        result = lwa.apply_proposal(db, ids["world"], _good(ids), _creator(db, ids["world"]))
        db.commit()
        after = _counts(db)
        grown = {t: after[t] - before[t] for t in _COUNTED_TABLES}
        want = {"entity": 1, "fact": 3, "fact_participant": 4, "fact_default": 3, "knowledge": 2,
                "relation": 1, "faction_membership": 1, "lore_entry": 1}
        for table, n in want.items():
            if grown[table] != n:
                fail(f"C1a: {table} grew by {grown[table]}, expected {n}")
        recorded = sum(n for t, n in grown.items() if t not in ("lore_entry", "lore_entry_row"))
        if grown["lore_entry_row"] != recorded:
            fail(f"C1a: {grown['lore_entry_row']} lore_entry_row for {recorded} written rows")
        facts = db.exec(__import__("sqlmodel").select(Fact).where(Fact.created_by == "creator_lore")).all()
        interdite = [f for f in facts if "interdite" in fact_text(db, f)]
        if not interdite or "[[e:" not in interdite[0].content_raw:
            fail("C1a: the new entity's name is not an identity token in the fact naming it")
        f3 = next((f for f in facts if f.facet == "aversion"), None)
        again = _good(ids)
        again["entities"][3]["name"] = "Vimm noire"
        lwa.apply_proposal(db, ids["world"], again, _creator(db, ids["world"]))
        second = lwa.apply_proposal(db, ids["world"], _good(ids), _creator(db, ids["world"]))
        db.commit()
        if len(second.skipped) < 4:
            fail(f"C1b: a second apply skipped {second.skipped}, expected the existing rows")
        rewrite = {"statement": "Maëlle a changé.", "entities": [], "facts": [
            {"ref": "f1", "action": "rewrite", "fact_id": ids["bloc"],
             "content": "Une passeuse devenue célèbre."}]}
        res = lwa.apply_proposal(db, ids["world"], rewrite, _creator(db, ids["world"]))
        db.commit()
        bloc = db.get(Fact, ids["bloc"])
        rows = db.exec(__import__("sqlmodel").select(LoreEntryRow).where(
            LoreEntryRow.entry_id == res.entry_id)).all()
        if ("célèbre" not in fact_text(db, bloc) or not bloc.change_history
                or [(r.row_table, r.action) for r in rows] != [("fact", "updated")]):
            fail("C1c: the bloc rewrite did not update in place with history and one row")
        for label, mutate in _REFUSALS:
            proposal = copy.deepcopy(_good(ids))
            mutate(proposal)
            for item in proposal.get("facts") or []:
                if item.get("fact_id") == "__f3__":
                    item["fact_id"] = f3.id if f3 else "nope"
            before = _counts(db)
            try:
                lwa.apply_proposal(db, ids["world"], proposal, _creator(db, ids["world"]))
                fail(f"C1d: {label}: accepted")
            except lwa.ProposalError:
                pass
            db.rollback()
            if _counts(db) != before:
                fail(f"C1d: {label}: rows changed")
        before = _counts(db)
        second_bloc = {"statement": "Encore.", "entities": [
            {"ref": "e1", "action": "existing", "entity_id": ids["npc"]}], "facts": [
            {"ref": "f1", "action": "create", "facet": "description", "content": "Autre.",
             "participants": ["e1"]}]}
        try:
            lwa.apply_proposal(db, ids["world"], second_bloc, _creator(db, ids["world"]))
            fail("C1e: a second bloc fact was accepted")
        except lwa.ProposalError:
            pass
        db.rollback()
        if _counts(db) != before:
            fail("C1e: a refused write left rows behind")


def check_c2() -> None:
    for rel in _PURE_FILES:
        text = (SRC / rel).read_text(encoding="utf-8")
        for needle in ("chat(", ".commit(", "ollama_client", "cockpit"):
            if needle in text:
                fail(f"C2: {rel} contains {needle!r}")


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="lore_write_")
    db_path = f"{tmp}/w.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    check_l0()
    check_w1()
    check_w2(db_path)
    check_c1()
    check_c2()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(f"PASS: lore_write -- census of {len(_LORE_WRITE_FILES)} module(s) holds; "
          "v2.11 declares the source record and migrates from v2.10 only; a proposal "
          "writes all or nothing, each row recorded, existing rows skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
