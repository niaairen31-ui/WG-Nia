"""G1 check for TICKET-0109 -- objects held in quantity, quest terms, the
indicative unit, and « déclarer accomplie ».

The lot adds its pieces brief by brief; this check grows with it (the
`quests.py` precedent, TICKET-0108). Each brief adds its rules here in the
same commit.

RA1 -- schema (BRIEF-0109-A, v2.18). `item` has exactly the columns `id`,
   `condition`, `value` (default 1, CHECK >= 0); `item_holding` has a unique
   `(item_id, holder_entity_id)` and `quantity >= 0`; `quest_offer_term` and
   `quest_term` carry the same three CHECK texts; `quest.settled_at` is a
   nullable column; `quest_economy` is unique per world. The `item` registry
   fields are `condition` and `value`; no `owner_id`, `location_id` or
   `equipped` attribute is read under `src/` (AST); `_apply_mutation`'s
   `appliers` has no `item_update`.
RA2 -- migration `scripts/migrate_v2_18_quest_terms.py`, on a v2.17-shaped
   database (`item` and `quest` in their v2.17 DDL, verbatim below, none of
   the four new tables), holding an item owned by a character, one lying in
   a place, one with both, one with neither, one whose owner is gone, and a
   `session` row pointing to a missing world:
   a. at v2.16 it refuses (non-zero exit) and changes nothing;
   b. at v2.17 it writes one holding of 1 for the owned item (its owner),
      the lying one (its place), the one with both (its owner), none for the
      others; `item` keeps its five rows with the model's columns and their
      `condition`; the four tables and `quest.settled_at` exist; `PRAGMA
      foreign_key_check` is empty on the six tables it writes; the orphan
      `session` is noted and not stopped on; `schema_meta` is the code's
      version;
   c. a second run exits zero and changes no row.
RA3 -- holdings (fixture). `write_holding` sets and moves a quantity, keeps
   a row at 0, appends the previous quantity to `change_history`; refuses,
   with no write, a result below 0, an entity that is not an item, a holder
   of another world, both or neither of `quantity`/`delta`, and a zone as a
   place that receives -- while taking out of a zone is accepted. The
   inventory line reads « Dague, Fourrure de loup ×10 »; the interpretation
   list names « Dague, Fourrure de loup » with no quantity; the possession
   check finds an item held and not one held at 0; `GET /api/entities/{id}/
   items` and `GET /api/items/{id}/holders` give quantities; `PUT
   /api/item-holdings` sets one and answers 422 on a refusal.

RB1 -- terms (BRIEF-0109-B, fixture). `write_quest_offer` with terms writes
   them in order; it refuses, with no row written: a direction `gift`, a
   currency `favour`, money of 0, an item that is not an item, a fact of
   another world, a relation of 100, a relation, fact or skill term whose
   counterparty is a faction (the giver a faction, none named), a skill cost
   on a base domain, a fact reward at `unaware`, a counterparty location.
   Saving with `terms=None` keeps the terms; with `[]` removes them.
RB2 -- acceptance copies (fixture, B1). An accepted quest holds a copy of
   the offer's terms; editing the offer afterwards changes the offer's
   terms, not the quest's.
RB3 -- the indicative unit (fixture, C1/E1). With no economy row the rates
   are `DEFAULT_RATES`; an offer costing 10 coins and 2 furs of value 3 (16)
   and rewarding a fact and 5 relation points (10) reads 62 % `meagre`;
   rewarding 20 coins instead reads 125 % `balanced`; 30 coins 188 %
   `generous`; no cost `free`. `upsert_quest_economy` sets `rate_fact` 20
   (the fact reward now reads 20), refuses -1, an unknown column and a band
   of 160-150; a None returns a rate to its default. `term_line` reads
   « Donner 2 × Fourrure de loup à Garde » and « La relation de Garde envers
   vous monte de 5 ». The routes `preview_value`, `get_economy`,
   `set_economy` answer the same numbers and 422 on a refusal.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sqlite3
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"
MIGRATION = ROOT / "scripts" / "migrate_v2_18_quest_terms.py"

FAILURES: list[str] = []

NEW_TABLES = ("item_holding", "quest_offer_term", "quest_term", "quest_economy")

# `item` and `quest` as v2.17 created them (dumped from `main` at 1f80b9f).
_V217_DDL = (
    """CREATE TABLE item (
	id VARCHAR NOT NULL, owner_id VARCHAR, location_id VARCHAR,
	equipped BOOLEAN DEFAULT 0 NOT NULL, condition VARCHAR DEFAULT 'intact' NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_item_equipped_owner CHECK (NOT equipped OR owner_id IS NOT NULL),
	FOREIGN KEY(id) REFERENCES entity (id),
	FOREIGN KEY(owner_id) REFERENCES entity (id),
	FOREIGN KEY(location_id) REFERENCES entity (id))""",
    "CREATE INDEX idx_item_location ON item (location_id)",
    "CREATE INDEX idx_item_owner ON item (owner_id)",
    """CREATE TABLE quest (
	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, offer_id VARCHAR NOT NULL,
	character_id VARCHAR NOT NULL, agenda_id VARCHAR NOT NULL,
	accepted_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(world_id) REFERENCES world (id),
	FOREIGN KEY(offer_id) REFERENCES quest_offer (id),
	FOREIGN KEY(character_id) REFERENCES entity (id),
	FOREIGN KEY(agenda_id) REFERENCES agenda (id))""",
    "CREATE INDEX idx_quest_offer ON quest (offer_id)",
    "CREATE UNIQUE INDEX idx_quest_agenda ON quest (agenda_id)",
    "CREATE INDEX idx_quest_character ON quest (character_id)",
)


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> str:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    return db_path


# --- RA1 -----------------------------------------------------------------------

def _checks(table) -> dict[str, str]:
    from sqlalchemy import CheckConstraint

    return {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}


def _attribute_reads(names: set[str]) -> list[str]:
    """`x.owner_id` / `x.location_id` / `x.equipped` on an Item-shaped read:
    every attribute access named so whose object mentions `item`/`Item`."""
    found = []
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in names:
                owner = ast.unparse(node.value)
                if "item" in owner.lower():
                    found.append(f"{path.relative_to(ROOT)}:{node.lineno} {owner}.{node.attr}")
    return found


def check_ra1() -> None:
    from world_engine.cockpit.crud.entities import ENTITY_TYPE_REGISTRY
    from world_engine.models import Item, ItemHolding, Quest, QuestEconomy, QuestOfferTerm, QuestTerm

    if set(Item.__table__.columns.keys()) != {"id", "condition", "value"}:
        fail(f"RA1: item columns are {sorted(Item.__table__.columns.keys())}")
    value = Item.__table__.columns.get("value")
    if value is None or str(value.server_default.arg) != "1" or "value >= 0" not in _checks(Item.__table__).values():
        fail("RA1: item.value is not default 1 with CHECK value >= 0")
    unique = {tuple(c.name for c in i.columns) for i in ItemHolding.__table__.indexes if i.unique}
    if ("item_id", "holder_entity_id") not in unique or "quantity >= 0" not in _checks(ItemHolding.__table__).values():
        fail(f"RA1: item_holding uniques {unique}, checks {_checks(ItemHolding.__table__)}")
    offer, quest = _checks(QuestOfferTerm.__table__), _checks(QuestTerm.__table__)
    for kind in ("direction", "currency", "shape"):
        if not offer.get(f"ck_quest_offer_term_{kind}") or offer.get(f"ck_quest_offer_term_{kind}") != quest.get(f"ck_quest_term_{kind}"):
            fail(f"RA1: the {kind} CHECK differs between quest_offer_term and quest_term")
    settled = Quest.__table__.columns.get("settled_at")
    if settled is None or not settled.nullable:
        fail("RA1: quest.settled_at is missing or not nullable")
    if not any(i.unique and [c.name for c in i.columns] == ["world_id"] for i in QuestEconomy.__table__.indexes):
        fail("RA1: quest_economy is not unique per world")
    names = [f["name"] for f in ENTITY_TYPE_REGISTRY["item"]["fields"]]
    if names != ["condition", "value"]:
        fail(f"RA1: the item registry fields are {names}")
    reads = _attribute_reads({"owner_id", "location_id", "equipped"})
    if reads:
        fail(f"RA1: an item's dropped column is still read: {reads}")
    tree = ast.parse((SRC / "cockpit" / "routes" / "mutations.py").read_text(encoding="utf-8"))
    keys = [k.value for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id == "appliers" for t in n.targets) and isinstance(n.value, ast.Dict)
        for k in n.value.keys if isinstance(k, ast.Constant)]
    if not keys or "item_update" in keys:
        fail(f"RA1: the appliers are {keys}")


# --- RA2 -----------------------------------------------------------------------

def _run_migration(db_path: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True,
                          text=True, cwd=str(ROOT), timeout=120)


def _shape(conn, table: str) -> list[tuple]:
    return sorted((r[1], r[2], r[3], r[4]) for r in conn.execute(f"PRAGMA table_info({table})"))


def _seed_v217(db_path: str) -> dict:
    from sqlmodel import Session

    from world_engine.db import create_db_and_tables, engine
    from world_engine.models import Entity, Location, SchemaMeta, World

    create_db_and_tables()
    ids: dict = {}
    with Session(engine) as session:
        world = World(name="Quest rewards RA2", is_active=True)
        session.add(world)
        session.flush()
        ids["world"] = world.id
        for key, kind in (("pc", "character"), ("place", "location"), ("owned", "item"), ("lying", "item"),
                          ("both", "item"), ("loose", "item"), ("orphan", "item")):
            row = Entity(world_id=world.id, type=kind, name=key)
            session.add(row)
            session.flush()
            ids[key] = row.id
        session.add(Location(id=ids["place"]))
        if session.get(SchemaMeta, 1) is None:
            session.add(SchemaMeta(id=1, static_version="v2.17"))
        session.commit()
    engine.dispose()
    with sqlite3.connect(db_path) as conn:
        ids["model_shapes"] = {t: _shape(conn, t) for t in ("item", "quest") + NEW_TABLES}
        conn.execute("PRAGMA foreign_keys=OFF")
        for table in NEW_TABLES + ("item", "quest"):
            conn.execute(f"DROP TABLE {table}")
        for statement in _V217_DDL:
            conn.execute(statement)
        rows = (("owned", ids["pc"], None, "intact"), ("lying", None, ids["place"], "usé"),
                ("both", ids["pc"], ids["place"], "intact"), ("loose", None, None, "intact"),
                ("orphan", "gone-entity", None, "brisé"))
        for key, owner, place, condition in rows:
            conn.execute("INSERT INTO item (id, owner_id, location_id, equipped, condition) VALUES (?, ?, ?, 0, ?)",
                         (ids[key], owner, place, condition))
        # A dangling reference this migration never wrote (AMENDMENT-0107-01).
        conn.execute("INSERT INTO session (id, world_id, number) VALUES ('orphan-session', 'gone-world', 9)")
    return ids


def _state(db_path: str) -> dict:
    with sqlite3.connect(db_path) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        holdings = (sorted(conn.execute("SELECT item_id, holder_entity_id, quantity FROM item_holding").fetchall())
                    if "item_holding" in tables else None)
        return {
            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
            "items": sorted(conn.execute("SELECT id, condition FROM item").fetchall()),
            "holdings": holdings,
            "shapes": {t: _shape(conn, t) for t in ("item", "quest") + NEW_TABLES if t in tables},
        }


def check_ra2(db_path: str) -> None:
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION

    ids = _seed_v217(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE schema_meta SET static_version = 'v2.16' WHERE id = 1")
    before = _state(db_path)
    result = _run_migration(db_path)
    if result.returncode == 0 or _state(db_path) != before:
        fail(f"RA2a: at v2.16 the migration exit {result.returncode} or the database changed")
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE schema_meta SET static_version = 'v2.17' WHERE id = 1")
    result = _run_migration(db_path)
    if result.returncode != 0:
        fail(f"RA2b: the migration failed: {result.stdout[-400:]} {result.stderr[-400:]}")
        return
    after = _state(db_path)
    expected = sorted([(ids["owned"], ids["pc"], 1), (ids["lying"], ids["place"], 1), (ids["both"], ids["pc"], 1)])
    if after["holdings"] != expected:
        fail(f"RA2b: the holdings are {after['holdings']}, expected {expected}")
    if after["items"] != before["items"] or len(after["items"]) != 5:
        fail(f"RA2b: the item rows are {after['items']}")
    if after["shapes"] != ids["model_shapes"]:
        fail(f"RA2b: the tables are {after['shapes']}, expected the models' {ids['model_shapes']}")
    if after["version"] != EXPECTED_STATIC_SCHEMA_VERSION:
        fail(f"RA2b: schema_meta is {after['version']}")
    if "Note: session rowid" not in result.stdout or "no longer exists" not in result.stdout:
        fail("RA2b: the orphan session row or the gone owner was not noted")
    with sqlite3.connect(db_path) as conn:
        dangling = [r for t in ("item", "quest") + NEW_TABLES
                    for r in conn.execute(f"PRAGMA foreign_key_check({t})").fetchall()]
    if dangling:
        fail(f"RA2b: foreign_key_check {dangling}")
    again = _state(db_path)
    result = _run_migration(db_path)
    if result.returncode != 0 or _state(db_path) != again:
        fail(f"RA2c: a second run exit {result.returncode} or changed a row")


# --- RA3 -----------------------------------------------------------------------

def _ra3_world(session) -> dict:
    from world_engine.models import Character, Entity, Item, Location, World

    worlds = []
    for name in ("Quest rewards RA3", "Elsewhere"):
        world = World(name=name, is_active=False)
        session.add(world)
        session.flush()
        worlds.append(world.id)
    ids = {"world": worlds[0], "other_world": worlds[1]}
    pc = Entity(world_id=worlds[0], type="character", name="Millys")
    stranger = Entity(world_id=worlds[1], type="character", name="Étranger")
    session.add_all([pc, stranger])
    session.flush()
    session.add(Character(id=pc.id, world_id=worlds[0], character_type="player"))
    ids.update(pc=pc.id, stranger=stranger.id)
    for key, parent in (("zone", None), ("room", "zone")):
        loc = Entity(world_id=worlds[0], type="location", name=key)
        session.add(loc)
        session.flush()
        session.add(Location(id=loc.id, parent_location_id=ids.get(parent)))
        ids[key] = loc.id
    for key, name in (("dague", "Dague"), ("fur", "Fourrure de loup"), ("rope", "Corde")):
        row = Entity(world_id=worlds[0], type="item", name=name)
        session.add(row)
        session.flush()
        session.add(Item(id=row.id))
        ids[key] = row.id
    session.commit()
    return ids


def _refused(session, label: str, **kwargs) -> None:
    from sqlmodel import func, select

    from world_engine.models import ItemHolding
    from world_engine.writes import write_holding

    before = session.exec(select(func.count()).select_from(ItemHolding)).one()
    try:
        write_holding(session, changed_by="check", **kwargs)
    except ValueError:
        session.rollback()
        if session.exec(select(func.count()).select_from(ItemHolding)).one() != before:
            fail(f"RA3: a refused holding ({label}) wrote a row")
        return
    session.rollback()
    fail(f"RA3: write_holding accepts {label}")


def _ra3_writer(session, ids) -> None:
    from world_engine.holdings import held_quantity
    from world_engine.writes import write_holding

    w = ids["world"]
    write_holding(session, world_id=w, item_id=ids["dague"], holder_entity_id=ids["pc"], quantity=1, changed_by="check")
    write_holding(session, world_id=w, item_id=ids["fur"], holder_entity_id=ids["pc"], quantity=4, changed_by="check")
    row = write_holding(session, world_id=w, item_id=ids["fur"], holder_entity_id=ids["pc"], delta=6, changed_by="check")
    session.commit()
    if row.quantity != 10 or [h["quantity"] for h in row.change_history] != [4]:
        fail(f"RA3: fur is {row.quantity}, history {row.change_history}")
    write_holding(session, world_id=w, item_id=ids["rope"], holder_entity_id=ids["pc"], quantity=2, changed_by="check")
    rope = write_holding(session, world_id=w, item_id=ids["rope"], holder_entity_id=ids["pc"], delta=-2, changed_by="check")
    session.commit()
    if rope.quantity != 0 or held_quantity(session, ids["pc"], ids["rope"]) != 0:
        fail("RA3: a holding moved to 0 is not kept at 0")
    _refused(session, "a result below 0", world_id=w, item_id=ids["fur"], holder_entity_id=ids["pc"], delta=-11)
    _refused(session, "a character as the item", world_id=w, item_id=ids["pc"], holder_entity_id=ids["pc"], quantity=1)
    _refused(session, "a holder of another world", world_id=w, item_id=ids["fur"], holder_entity_id=ids["stranger"], quantity=1)
    _refused(session, "both quantity and delta", world_id=w, item_id=ids["fur"], holder_entity_id=ids["pc"], quantity=1, delta=1)
    _refused(session, "neither quantity nor delta", world_id=w, item_id=ids["fur"], holder_entity_id=ids["pc"])
    _refused(session, "a zone that receives", world_id=w, item_id=ids["fur"], holder_entity_id=ids["zone"], quantity=1)
    session.execute(__import__("sqlalchemy").text(
        "INSERT INTO item_holding (id, world_id, item_id, holder_entity_id, quantity, updated_at, change_history) "
        "VALUES ('legacy-zone', :w, :i, :z, 3, CURRENT_TIMESTAMP, '[]')"), {"w": w, "i": ids["rope"], "z": ids["zone"]})
    session.commit()
    try:
        write_holding(session, world_id=w, item_id=ids["rope"], holder_entity_id=ids["zone"], delta=-3, changed_by="check")
        session.commit()
    except ValueError as exc:
        session.rollback()
        fail(f"RA3: taking items out of a zone is refused: {exc}")


def _ra3_readers(session, ids) -> None:
    from world_engine.cockpit.play_stream import _find_player_item
    from world_engine.scene_format import format_inventory_line, format_item_list_for_interpretation

    line = format_inventory_line(session, ids["pc"])
    if line != "Objets du joueur : Dague, Fourrure de loup ×10.":
        fail(f"RA3: the inventory line is {line!r}")
    names = format_item_list_for_interpretation(session, ids["pc"])
    if names != "Objets du joueur : Dague, Fourrure de loup.":
        fail(f"RA3: the interpretation list is {names!r}")
    if _find_player_item(session, ids["pc"], "Fourrure de loup") is None:
        fail("RA3: the possession check misses an item held")
    if _find_player_item(session, ids["pc"], "Corde") is not None:
        fail("RA3: the possession check finds an item held at 0")


def _ra3_routes(session, ids) -> None:
    from fastapi import HTTPException

    from world_engine.cockpit.crud.entities import list_entity_items
    from world_engine.cockpit.crud.items import HoldingBody, list_item_holders, set_holding
    from world_engine.models import World

    for world in session.exec(__import__("sqlmodel").select(World).where(World.is_active == True)).all():  # noqa: E712
        world.is_active = False
        session.add(world)
    session.flush()
    session.get(World, ids["world"]).is_active = True
    session.commit()
    items = {(r["name"], r["quantity"]) for r in list_entity_items(ids["pc"], db=session)}
    if items != {("Dague", 1), ("Fourrure de loup", 10)}:
        fail(f"RA3: GET items gives {items}")
    set_holding(HoldingBody(item_id=ids["fur"], holder_entity_id=ids["room"], quantity=3), db=session)
    holders = {(r["name"], r["quantity"]) for r in list_item_holders(ids["fur"], db=session)}
    if holders != {("Millys", 10), ("room", 3)}:
        fail(f"RA3: GET holders gives {holders}")
    try:
        set_holding(HoldingBody(item_id=ids["fur"], holder_entity_id=ids["zone"], quantity=1), db=session)
        fail("RA3: PUT item-holdings accepts a zone")
    except HTTPException as exc:
        if exc.status_code != 422:
            fail(f"RA3: PUT item-holdings on a zone answers {exc.status_code}")


def check_ra3(engine) -> None:
    from sqlmodel import Session

    with Session(engine) as session:
        ids = _ra3_world(session)
        _ra3_writer(session, ids)
        _ra3_readers(session, ids)
        _ra3_routes(session, ids)


# --- RB --------------------------------------------------------------------------

def _rb_world(session) -> dict:
    from world_engine.models import Character, Entity, Fact, Faction, Item, Location, World

    worlds = []
    for name in ("Quest rewards RB", "Other RB"):
        world = World(name=name, is_active=False)
        session.add(world)
        session.flush()
        worlds.append(world.id)
    ids = {"world": worlds[0]}
    for key, kind, name in (("pc", "character", "Millys"), ("npc", "character", "Garde"),
                            ("guild", "faction", "Guilde"), ("place", "location", "Port"),
                            ("fur", "item", "Fourrure de loup")):
        row = Entity(world_id=worlds[0], type=kind, name=name)
        session.add(row)
        session.flush()
        ids[key] = row.id
    session.add_all([Character(id=ids["pc"], world_id=worlds[0], character_type="player"),
                     Character(id=ids["npc"], world_id=worlds[0], character_type="npc"),
                     Faction(id=ids["guild"]), Location(id=ids["place"]), Item(id=ids["fur"], value=3)])
    fact = Fact(world_id=worlds[0], content_raw="Le passage secret", created_by="check")
    alien = Fact(world_id=worlds[1], content_raw="Ailleurs", created_by="check")
    session.add_all([fact, alien])
    session.commit()
    ids.update(fact=fact.id, alien_fact=alien.id)
    return ids


def _offer(ids: dict, **over) -> dict:
    from world_engine.day_plan import PlanStep

    base = dict(world_id=ids["world"], offer=None, giver_entity_id=ids["npc"], title="La fourrure",
                summary=None, repeatable=False, status="open", eligibility=[],
                steps=[PlanStep(objective="Chasser", cost=1, domain=None)])
    base.update(over)
    return base


def _rb_terms(ids: dict) -> list:
    from world_engine.writes import TermSpec

    return [TermSpec(direction="cost", currency="money", amount=10),
            TermSpec(direction="cost", currency="item", item_id=ids["fur"], amount=2),
            TermSpec(direction="reward", currency="fact", fact_id=ids["fact"]),
            TermSpec(direction="reward", currency="relation", amount=5)]


def _rb1_refusals(session, ids) -> None:
    from sqlmodel import func, select

    from world_engine.models import QuestOffer, QuestOfferTerm
    from world_engine.writes import TermSpec, write_quest_offer

    bad = {
        "a direction gift": [TermSpec(direction="gift", currency="money", amount=1)],
        "a currency favour": [TermSpec(direction="cost", currency="favour", amount=1)],
        "money of 0": [TermSpec(direction="cost", currency="money", amount=0)],
        "an item that is not an item": [TermSpec(direction="cost", currency="item", item_id=ids["npc"], amount=1)],
        "a fact of another world": [TermSpec(direction="reward", currency="fact", fact_id=ids["alien_fact"])],
        "a relation of 100": [TermSpec(direction="reward", currency="relation", amount=100)],
        "a skill cost on a base domain": [TermSpec(direction="cost", currency="skill", skill_key="agility")],
        "a fact reward at unaware": [TermSpec(direction="reward", currency="fact", fact_id=ids["fact"], level="unaware")],
        "a counterparty location": [TermSpec(direction="cost", currency="money", amount=1,
                                             counterparty_entity_id=ids["place"])],
    }
    cases = [(label, _offer(ids, terms=terms)) for label, terms in bad.items()]
    cases.append(("a relation term owed by a faction",
                  _offer(ids, giver_entity_id=ids["guild"],
                         terms=[TermSpec(direction="reward", currency="relation", amount=3)])))
    for label, kwargs in cases:
        before = [session.exec(select(func.count()).select_from(m)).one() for m in (QuestOffer, QuestOfferTerm)]
        try:
            write_quest_offer(session, **kwargs)
        except ValueError:
            session.rollback()
            after = [session.exec(select(func.count()).select_from(m)).one() for m in (QuestOffer, QuestOfferTerm)]
            if after != before:
                fail(f"RB1: a refused offer ({label}) wrote rows")
            continue
        session.rollback()
        fail(f"RB1: write_quest_offer accepts {label}")


def check_rb1(session, ids) -> None:
    from world_engine.writes import offer_terms, write_quest_offer

    _rb1_refusals(session, ids)
    offer = write_quest_offer(session, **_offer(ids, terms=_rb_terms(ids)))
    session.commit()
    ids["offer"] = offer.id
    got = [(t.term_order, t.direction, t.currency) for t in offer_terms(session, offer.id)]
    if got != [(1, "cost", "money"), (2, "cost", "item"), (3, "reward", "fact"), (4, "reward", "relation")]:
        fail(f"RB1: the written terms are {got}")
    write_quest_offer(session, **_offer(ids, offer=offer, title="La fourrure du loup"))
    session.commit()
    if len(offer_terms(session, offer.id)) != 4:
        fail("RB1: saving with terms=None did not keep the terms")


def check_rb2(session, ids) -> None:
    from world_engine.models import Character, QuestOffer
    from world_engine.writes import TermSpec, accept_quest, offer_terms, quest_terms, write_quest_offer

    offer = session.get(QuestOffer, ids["offer"])
    quest = accept_quest(session, offer=offer, character=session.get(Character, ids["pc"]))
    session.commit()
    ids["quest"] = quest.id
    copied = [(t.direction, t.currency, t.amount) for t in quest_terms(session, quest.id)]
    if copied != [(t.direction, t.currency, t.amount) for t in offer_terms(session, offer.id)] or len(copied) != 4:
        fail(f"RB2: the quest's terms are {copied}")
    write_quest_offer(session, **_offer(ids, offer=offer, terms=[TermSpec(direction="reward", currency="money", amount=1)]))
    session.commit()
    if len(offer_terms(session, offer.id)) != 1 or len(quest_terms(session, quest.id)) != 4:
        fail("RB2: editing the offer changed the accepted quest's terms, or did not change the offer's")
    write_quest_offer(session, **_offer(ids, offer=offer, terms=[]))
    session.commit()
    if offer_terms(session, offer.id):
        fail("RB1: saving with terms=[] did not remove the terms")


def _rb3_values(session, ids) -> None:
    from world_engine.quest_value import DEFAULT_RATES, offer_value, world_rates
    from world_engine.writes import TermSpec

    if world_rates(session, ids["world"]) != DEFAULT_RATES:
        fail(f"RB3: the default rates are {world_rates(session, ids['world'])}")
    terms = _rb_terms(ids)
    cases = [(terms, (16, 10, 62, "meagre")),
             (terms[:2] + [TermSpec(direction="reward", currency="money", amount=20)], (16, 20, 125, "balanced")),
             (terms[:2] + [TermSpec(direction="reward", currency="money", amount=30)], (16, 30, 188, "generous")),
             (terms[2:], (0, 10, None, "free"))]
    for case_terms, expected in cases:
        v = offer_value(session, ids["world"], case_terms)
        if (v.cost, v.reward, v.ratio_pct, v.verdict) != expected:
            fail(f"RB3: value is {(v.cost, v.reward, v.ratio_pct, v.verdict)}, expected {expected}")


def _rb3_economy(session, ids) -> None:
    from world_engine.quest_value import DEFAULT_RATES, offer_value, world_rates
    from world_engine.writes import upsert_quest_economy

    upsert_quest_economy(session, world_id=ids["world"], values={"rate_fact": 20})
    session.commit()
    if offer_value(session, ids["world"], _rb_terms(ids)).reward != 25:
        fail("RB3: rate_fact 20 is not read")
    for bad in ({"rate_fact": -1}, {"rate_gold": 2}, {"band_low_pct": 160}):
        try:
            upsert_quest_economy(session, world_id=ids["world"], values=bad)
            fail(f"RB3: upsert_quest_economy accepts {bad}")
        except ValueError:
            session.rollback()
    upsert_quest_economy(session, world_id=ids["world"], values={"rate_fact": None})
    session.commit()
    if world_rates(session, ids["world"])["rate_fact"] != DEFAULT_RATES["rate_fact"]:
        fail("RB3: a None rate does not return to the default")


def _rb3_wording_and_routes(session, ids) -> None:
    from fastapi import HTTPException
    from sqlmodel import select

    from world_engine.cockpit.routes import quests as routes
    from world_engine.models import World
    from world_engine.quest_wording import term_line

    terms = _rb_terms(ids)
    lines = [term_line(session, terms[1], ids["npc"]), term_line(session, terms[3], ids["npc"])]
    if lines != ["Donner 2 × Fourrure de loup à Garde", "La relation de Garde envers vous monte de 5"]:
        fail(f"RB3: the term lines are {lines}")
    for world in session.exec(select(World).where(World.is_active == True)).all():  # noqa: E712
        world.is_active = False
        session.add(world)
    session.flush()
    session.get(World, ids["world"]).is_active = True
    session.commit()
    body = routes.ValueBody(terms=[routes.TermBody(**{k: v for k, v in t.__dict__.items()}) for t in terms])
    if routes.preview_value(body, db=session)["ratio_pct"] != 62:
        fail("RB3: POST /api/quest-offers/value disagrees")
    economy = routes.set_economy(routes.EconomyBody(rate_skill=30), db=session)
    if economy["effective"]["rate_skill"] != 30 or economy["stored"]["rate_skill"] != 30:
        fail(f"RB3: PUT /api/quest-economy gives {economy}")
    try:
        routes.set_economy(routes.EconomyBody(band_low_pct=200), db=session)
        fail("RB3: PUT /api/quest-economy accepts a band of 200-150")
    except HTTPException as exc:
        if exc.status_code != 422:
            fail(f"RB3: PUT /api/quest-economy refusal answers {exc.status_code}")


def check_rb(engine) -> None:
    from sqlmodel import Session

    with Session(engine) as session:
        ids = _rb_world(session)
        check_rb1(session, ids)
        check_rb2(session, ids)
        _rb3_values(session, ids)
        _rb3_economy(session, ids)
        _rb3_wording_and_routes(session, ids)


def main() -> int:
    db_path = _fresh_db()
    check_ra1()
    check_ra2(db_path)
    from world_engine.db import create_db_and_tables, engine
    create_db_and_tables()
    check_ra3(engine)
    check_rb(engine)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: quest_rewards -- v2.18 makes an item a kind held in quantity by any entity, "
          "migrates owners and places to holdings from v2.17 only, drops equipped, and one writer "
          "keeps every holding, its history, and zones empty; an offer's terms are validated whole, "
          "copied to the quest that accepts it, and valued in the world's indicative unit against "
          "its band")
    return 0


if __name__ == "__main__":
    sys.exit(main())
