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
D1 -- draft (BRIEF-0098-D, C-05), with `lore_write_draft.chat` replaced by a
   stub that records the messages and returns canned JSON:
   a. `draft_context` lists the entities the statement names, codes their
      facts and the world-level facts, and never codes a creator-only fact;
   b. `draft_questions` keeps at most `MAX_QUESTIONS` non-empty strings;
   c. `draft_proposal` returns a matched entity as `existing` with its id, a
      name two entities share as `ambiguous` with both candidates, an
      unknown name as `new` with the type of its category; resolves a
      listed code to its fact id; drops an unlisted code and a typed or
      unknown facet with one note per dropped fact, and silently drops a
      knower with an unknown level and a ref to no entity;
   d. no entity id and no fact id appears in any message sent to the model;
   e. the draft, its ambiguity settled, passes `lore_write_apply.validate`;
   f. an `OllamaError` from the model propagates out of both calls.
D2 -- prompts. `seed_pilot.LORE_WRITE_PROMPT_HEADS` holds exactly the usages
   `QUESTIONS_USAGE` and `PROPOSAL_USAGE`; each head's `variables` equal the
   `{placeholders}` of its user template; `apply_ticket_0098_lore_write_prompts.py`
   reads that tuple and embeds no prompt text; `lore_prompt.py` re-exports
   `prompt_load.load`, the loader the writing path imports.
E1 -- routes (BRIEF-0098-E), through `TestClient(app, base_url=...)` on the
   active fixture world, `lore_write_draft.chat` stubbed:
   a. `POST /api/lore/write/questions` answers the questions; with Ollama
      down it answers 503 with exactly `WRITE_UNAVAILABLE_MESSAGE`;
   b. `POST /api/lore/write/draft` answers the draft; with Ollama down, 503;
      no draft request changes any row count;
   c. `POST /api/lore/write/commit` of a valid proposal creating a
      character answers 200; the entity has its `character` row as an NPC;
      `GET /api/lore/write/entries` lists the entry first, with a label per
      row; an invalid proposal answers 422 and changes no row count;
   d. the same commit with a non-local `Origin` answers 403 and changes no
      row count.
E2 -- thin route. `cockpit/routes/lore_write.py` contains no `select(` and
   no `chat(`, and exactly one `.commit(` -- inside `write_commit`.
F1 -- panel (BRIEF-0098-F), static:
   a. `frontend/src/lore/Lore.svelte` imports `WritePanel.svelte` and renders
      it only under `loreTab === 'write'`;
   b. `frontend/src/lore/writePanel.svelte.js` calls exactly the paths
      `/api/lore/write/questions`, `/api/lore/write/draft`,
      `/api/lore/write/commit`, `/api/lore/write/entries` and `/api/entities`;
   c. `WritePanel.svelte` lists the facets it offers from `draft.facets`
      (served from `FACETS`), never from a literal list, and offers no free
      text field for an entity id.
C2 -- purity. `lore_write_apply.py` and `writes/lore_entries.py` contain no
   `chat(`, no `.commit(`, and import neither `ollama_client` nor any
   `cockpit` module; `lore_write_draft.py` contains no `db.add(`, no
   `.commit(`, and calls no writer (`write_`, `add_lore_fact(`,
   `apply_proposal(`).

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
    "lore_write_apply.py", "writes/lore_entries.py", "lore_write_draft.py",
    "lore_write_read.py", "cockpit/routes/lore_write.py",
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
    draft = (SRC / "lore_write_draft.py").read_text(encoding="utf-8")
    for needle in ("db.add(", ".commit(", "write_knowledge(", "write_lore_entry(",
                   "add_lore_fact(", "apply_proposal("):
        if needle in draft:
            fail(f"C2: lore_write_draft.py contains {needle!r}")


class _Stub:
    def __init__(self, replies):
        self.replies, self.messages = list(replies), []

    def __call__(self, messages, **kwargs):
        self.messages.append(messages)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return __import__("json").dumps(reply)


def check_d1() -> None:
    from sqlmodel import Session

    from world_engine import lore_write_apply as lwa
    from world_engine import lore_write_draft as lwd
    from world_engine.db import engine
    from world_engine.models import Entity, Knowledge, Location
    from world_engine.ollama_client import OllamaError
    from world_engine.writes.facets import add_lore_fact

    sys.path.insert(0, str(ROOT / "scripts"))
    import seed_pilot

    with Session(engine) as db:
        for head in seed_pilot.LORE_WRITE_PROMPT_HEADS:
            if db.get(__import__("world_engine.models", fromlist=["PromptTemplate"]).PromptTemplate,
                      head["id"]) is None:
                seed_pilot.upsert_prompt_template(db, **head)
        db.commit()
        ids = _fixture(db)
        world = ids["world"]
        for name in ("Tour Nord", "Tour Nord"):
            twin = Entity(world_id=world, type="location", name=name)
            db.add(twin)
            db.flush()
            db.add(Location(id=twin.id))
        general = add_lore_fact(db, world_id=world, facet="information", created_by="fixture",
                                content="Les marées montent deux fois par nuit.", participant_ids=[])
        hidden = add_lore_fact(db, world_id=world, facet="histoire", created_by="fixture",
                               content="Maëlle est une espionne.", participant_ids=[ids["npc"]])
        db.flush()
        db.add(Knowledge(entity_id=ids["npc"], fact_id=hidden.fact.id, level="unaware",
                         is_secret=True))
        db.commit()
        statement = "Maëlle dirige le Manoir Gris depuis la Tour Nord."
        context = lwd.draft_context(db, world, statement)
        joined = "\n".join(context.coded.lines)
        if not any("Maëlle" in line for line in context.entity_lines) or \
                not any("Manoir Gris" in line for line in context.entity_lines):
            fail(f"D1a: named entities missing: {context.entity_lines}")
        if context.coded.code_of(ids["bloc"]) is None or context.coded.code_of(general.fact.id) is None:
            fail("D1a: an entity fact or a world-level fact is not coded")
        if context.coded.code_of(hidden.fact.id) is not None or "espionne" in joined:
            fail("D1a: a creator-only fact was coded")
        bloc_code = context.coded.code_of(ids["bloc"])
        stub = _Stub([
            {"questions": ["Q1 ?", "", 3, "Q2 ?", "Q3 ?", "Q4 ?"]},
            {"entities": [
                {"ref": "e1", "name": "Maëlle", "category": "person"},
                {"ref": "e2", "name": "Tour Nord", "category": "place"},
                {"ref": "e3", "name": "Brume Salée", "category": "object"},
                {"ref": "e4", "name": "Manoir Gris", "category": "place"}],
             "facts": [
                {"action": "create", "content": "Maëlle dirige le manoir.", "facet": "statut",
                 "participants": ["e1", "e4"], "defaults": [{"scope_type": "location", "scope_ref": "e4"}],
                 "knowers": [{"entity_ref": "e1", "level": "knows"},
                             {"entity_ref": "e1", "level": "certain"}]},
                {"action": "existing", "code": bloc_code, "participants": ["e9"]},
                {"action": "existing", "code": "f999"},
                {"action": "create", "content": "Lien.", "facet": "lien"},
                {"action": "create", "content": "Humeur.", "facet": "humeur"}],
             "memberships": [{"entity_ref": "e1", "faction_ref": "e9"}],
             "controls": [{"owner_ref": "e1", "location_ref": "e4"}]},
            OllamaError("down"), OllamaError("down"),
        ])
        original = lwd.chat
        lwd.chat = stub
        try:
            questions = lwd.draft_questions(db, world, statement)
            draft = lwd.draft_proposal(db, world, statement, "Tout le monde au manoir.")
            for call in (lambda: lwd.draft_questions(db, world, statement),
                         lambda: lwd.draft_proposal(db, world, statement)):
                try:
                    call()
                    fail("D1f: an OllamaError did not propagate")
                except OllamaError:
                    pass
        finally:
            lwd.chat = original
        if questions != ["Q1 ?", "Q2 ?", "Q3 ?"]:
            fail(f"D1b: questions {questions!r}")
        by_ref = {e["ref"]: e for e in draft["entities"]}
        if by_ref.get("e1", {}).get("entity_id") != ids["npc"] or by_ref["e1"]["action"] != "existing":
            fail(f"D1c: Maëlle not matched: {by_ref.get('e1')}")
        if by_ref.get("e2", {}).get("status") != "ambiguous" or len(by_ref["e2"].get("candidates", [])) != 2:
            fail(f"D1c: Tour Nord not ambiguous with two candidates: {by_ref.get('e2')}")
        if by_ref.get("e3", {}).get("status") != "new" or by_ref["e3"].get("type") != "item":
            fail(f"D1c: Brume Salée not new as an item: {by_ref.get('e3')}")
        facts = draft["facts"]
        if [f["action"] for f in facts] != ["create", "existing"] or facts[1].get("fact_id") != ids["bloc"]:
            fail(f"D1c: facts kept {[(f['action'], f.get('fact_id')) for f in facts]}")
        if len(facts[0]["knowers"]) != 1 or facts[1]["participants"] != [] or draft["memberships"]:
            fail("D1c: an invalid knower, participant ref or membership survived")
        if len(draft["notes"]) != 3 or draft["controls"] != [{"owner_ref": "e1", "location_ref": "e4"}]:
            fail(f"D1c: notes {draft['notes']!r}, controls {draft['controls']!r}")
        sent = __import__("json").dumps(stub.messages, ensure_ascii=False)
        for secret_id in (ids["npc"], ids["manor"], ids["bloc"], general.fact.id):
            if secret_id in sent:
                fail(f"D1d: id {secret_id} reached the model")
        by_ref["e2"].update(action="existing", entity_id=by_ref["e2"]["candidates"][0]["entity_id"])
        try:
            lwa.validate(db, world, draft)
        except lwa.ProposalError as exc:
            fail(f"D1e: the settled draft does not validate: {exc}")


def check_e1() -> None:
    from fastapi.testclient import TestClient
    from sqlmodel import Session, select

    from world_engine import lore_write_draft as lwd
    from world_engine.cockpit.app import app
    from world_engine.db import engine
    from world_engine.models import Character, Entity, World
    from world_engine.ollama_client import OllamaError

    with Session(engine) as db:
        ids = _fixture(db)
        for world in db.exec(select(World)).all():
            world.is_active = world.id == ids["world"]
            db.add(world)
        db.commit()
    client = TestClient(app, base_url="http://127.0.0.1")
    stub = _Stub([{"questions": ["Qui le sait ?"]}, OllamaError("down"),
                  {"entities": [{"ref": "e1", "name": "Maëlle", "category": "person"}],
                   "facts": [], "memberships": [], "controls": []}, OllamaError("down")])
    original = lwd.chat
    lwd.chat = stub
    with Session(engine) as db:
        before = _counts(db)
    try:
        body = {"statement": "Maëlle garde le Manoir Gris."}
        resp = client.post("/api/lore/write/questions", json=body)
        if resp.status_code != 200 or resp.json() != {"questions": ["Qui le sait ?"]}:
            fail(f"E1a: questions answered {resp.status_code} {resp.text[:120]}")
        resp = client.post("/api/lore/write/questions", json=body)
        if resp.status_code != 503 or resp.json().get("detail") != lwd.WRITE_UNAVAILABLE_MESSAGE:
            fail(f"E1a: Ollama down answered {resp.status_code} {resp.text[:120]}")
        resp = client.post("/api/lore/write/draft", json=dict(body, answers="Tout le monde."))
        if resp.status_code != 200 or resp.json()["entities"][0].get("entity_id") != ids["npc"]:
            fail(f"E1b: draft answered {resp.status_code} {resp.text[:160]}")
        resp = client.post("/api/lore/write/draft", json=body)
        if resp.status_code != 503:
            fail(f"E1b: Ollama down on draft answered {resp.status_code}")
    finally:
        lwd.chat = original
    with Session(engine) as db:
        if _counts(db) != before:
            fail("E1b: a draft request changed rows")
    proposal = {"statement": "Joss, un docker, sert Maëlle.", "entities": [
        {"ref": "e1", "action": "create", "name": "Joss Fer", "type": "character"},
        {"ref": "e2", "action": "existing", "entity_id": ids["npc"]}], "facts": [
        {"ref": "f1", "action": "create", "facet": "histoire", "content": "Joss Fer sert Maëlle.",
         "participants": ["e1", "e2"], "knowers": [{"entity_ref": "e2", "level": "knows"}]}]}
    with Session(engine) as db:
        before = _counts(db)
    far = client.post("/api/lore/write/commit", json={"proposal": proposal},
                      headers={"origin": "https://evil.example"})
    with Session(engine) as db:
        if far.status_code != 403 or _counts(db) != before:
            fail(f"E1d: a non-local commit answered {far.status_code} or wrote rows")
    resp = client.post("/api/lore/write/commit", json={"proposal": proposal})
    with Session(engine) as db:
        joss = db.exec(select(Entity).where(Entity.name == "Joss Fer",
                                            Entity.world_id == ids["world"])).first()
        char = db.get(Character, joss.id) if joss else None
        if resp.status_code != 200 or char is None or char.character_type != "npc":
            fail(f"E1c: commit answered {resp.status_code} {resp.text[:160]}")
    entries = client.get("/api/lore/write/entries").json().get("entries") or [{}]
    labels = [r["label"] for r in entries[0].get("rows", [])]
    if entries[0].get("statement") != proposal["statement"] or not labels \
            or not any("Joss Fer" in label for label in labels):
        fail(f"E1c: entries listed {entries[0]!r}"[:300])
    proposal["facts"][0]["facet"] = "lien"
    with Session(engine) as db:
        before = _counts(db)
    resp = client.post("/api/lore/write/commit", json={"proposal": proposal})
    with Session(engine) as db:
        if resp.status_code != 422 or _counts(db) != before:
            fail(f"E1c: an invalid commit answered {resp.status_code} or wrote rows")


def check_e2() -> None:
    import ast

    route = SRC / "cockpit" / "routes" / "lore_write.py"
    text = route.read_text(encoding="utf-8")
    for needle in ("select(", "chat("):
        if needle in text:
            fail(f"E2: the writing route contains {needle!r}")
    tree = ast.parse(text)
    commits = [(fn.name, node) for fn in tree.body if isinstance(fn, ast.FunctionDef)
               for node in ast.walk(fn) if isinstance(node, ast.Call)
               and isinstance(node.func, ast.Attribute) and node.func.attr == "commit"]
    if [name for name, _ in commits] != ["write_commit"]:
        fail(f"E2: commits in {[name for name, _ in commits]}, expected only write_commit")


def check_f1() -> None:
    lore = (ROOT / "frontend" / "src" / "lore")
    shell = (lore / "Lore.svelte").read_text(encoding="utf-8")
    if "import WritePanel from './WritePanel.svelte';" not in shell or \
            "{#if loreTab === 'write'}\n    <WritePanel" not in shell:
        fail("F1a: Lore.svelte does not render WritePanel under the 'write' tab")
    state = (lore / "writePanel.svelte.js").read_text(encoding="utf-8")
    paths = set(re.findall(r"'(/api/[a-z/_-]+)'", state))
    want = {"/api/lore/write/questions", "/api/lore/write/draft", "/api/lore/write/commit",
            "/api/lore/write/entries", "/api/entities"}
    if paths != want:
        fail(f"F1b: writePanel.svelte.js calls {sorted(paths)}")
    panel = (lore / "WritePanel.svelte").read_text(encoding="utf-8")
    if "draft.facets" not in panel or re.search(r"'(aversion|preference|coutume)'", panel):
        fail("F1c: WritePanel.svelte does not take its facets from the draft")
    if "entity_id" in re.sub(r"entity\.entity_id|c\.entity_id|entity_id\)", "", panel):
        fail("F1c: WritePanel.svelte exposes an entity id outside a picker")


def check_d2() -> None:
    import re as _re

    sys.path.insert(0, str(ROOT / "scripts"))
    import seed_pilot

    from world_engine import lore_prompt, lore_write_draft as lwd, prompt_load

    heads = seed_pilot.LORE_WRITE_PROMPT_HEADS
    if sorted(h["usage"] for h in heads) != sorted([lwd.QUESTIONS_USAGE, lwd.PROPOSAL_USAGE]):
        fail(f"D2: heads carry usages {[h['usage'] for h in heads]}")
    for head in heads:
        found = set(_re.findall(r"\{([a-z_]+)\}", head["user_template"]))
        if found != set(head["variables"]):
            fail(f"D2: {head['id']} declares {head['variables']} but uses {sorted(found)}")
    script = (ROOT / "scripts" / "apply_ticket_0098_lore_write_prompts.py").read_text(encoding="utf-8")
    if "LORE_WRITE_PROMPT_HEADS" not in script or "Tu " in script:
        fail("D2: the delivery script does not read the single source, or embeds text")
    if lore_prompt.load is not prompt_load.load:
        fail("D2: lore_prompt.load is not prompt_load.load")


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
    check_d1()
    check_d2()
    check_e1()
    check_e2()
    check_f1()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(f"PASS: lore_write -- census of {len(_LORE_WRITE_FILES)} module(s) holds; "
          "v2.11 declares the source record and migrates from v2.10 only; a proposal "
          "writes all or nothing, each row recorded, existing rows skipped; the draft "
          "names things by name and code only and resolves both in code; the routes are "
          "thin, guarded, and write only on commit; the panel lives in the Lore shell's "
          "'Écrire' tab")
    return 0


if __name__ == "__main__":
    sys.exit(main())
