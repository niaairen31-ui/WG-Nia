"""G1 check for TICKET-0128 (BRIEF-0128-D) -- the day chain takes its world and its character from the day, never from the active world (INV-71).

INV-71's enforcing check.

DW1 -- static, on code tokens (strings and comments dropped). The day
   modules are every `src/world_engine/day_*.py` and
   `src/world_engine/cockpit/day_*.py` (at least 16 files) plus the 14
   named functions of `cockpit/routes/day.py` (`DAY_FUNCTIONS`, each
   found). None holds `World.is_active`, `_world_id(`, `active_world_id(`,
   `_player_character` or `resolve_active_pc`. Every `premised_prompt(`
   call in a day module passes `world_id=`; both `who_is_at(` calls of
   `day_concordance.py` pass `world_id=`; the three `extract_*(` calls of
   `routes/day.py` pass `world_id=`. Zero files or a function not found is
   a FAILURE.
DW2 -- fixture: world A active (PC Ana, description « Monde A »), world B
   inactive (description « Monde B », PC Bea, NPC Garde placed at B's place
   Port by a `npc_schedule` row), a session, batch and day of Bea in B.
   `_day_world(<B's batch>)` is B; an unknown batch is a 404;
   `_day_character(<the day>)` is Bea; a day whose `character_id` is Garde
   is a 409. On a `day_plan` head (`world_premise._seed_head`),
   `premised_prompt(db, head, world_id=B)` holds « Monde B » and not
   « Monde A »; `premised_prompt(db, head)` holds A's. `who_is_at(Port,
   phase, is_present=True, world_id=B)` holds Garde; without `world_id` it
   does not.
DW3 -- the pin at the declaration, `TestClient(app,
   base_url="http://127.0.0.1")`, `cockpit.day_declare.missing_usages`
   swapped for an empty answer and `cockpit.day_declare.enqueue_day` for a
   recorder, both restored in `finally`, on `quests._qb_world` made
   active, an offer (`quests._offer_kwargs(ids, eligibility=None)`)
   accepted by its PC. `POST /api/day/declare` with that quest -> 200 and
   the day's `quest_id` is it; with an unknown quest -> 404 and no new day;
   after `abandon_quest` -> 409 with the « terminée » message and no new
   day; without `quest_id` -> 200, `quest_id` NULL.

A rule not reached is a FAILURE. Fresh temp-file SQLite database
(`WORLD_ENGINE_DATABASE_URL` set before any world_engine import) -- never
Nia's DB.
"""
from __future__ import annotations

import ast
import io
import os
import pathlib
import sys
import tempfile
import tokenize

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
PACKAGE = SRC / "world_engine"
DAY_ROUTE = PACKAGE / "cockpit" / "routes" / "day.py"
CONCORDANCE = PACKAGE / "day_concordance.py"
DAY_FUNCTIONS = (
    "plan_day", "resolve_day", "_day_world", "_day_character", "_load_plannable_day",
    "_load_resolvable_day", "_extract_and_concord", "_write_declaration_rewrite",
    "_record_refused_choices", "_load_active_agenda", "_guard_no_pending_agenda_step_change",
    "_read_day_rewrite_concordance", "_narrate_and_judge", "_finalize_resolution",
)
BANNED = ("World.is_active", "_world_id(", "active_world_id(", "_player_character", "resolve_active_pc")
MIN_DAY_FILES = 16
TERMINATED = "cette quête est terminée : elle ne peut plus être avancée"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


# --- DW1 -----------------------------------------------------------------------

def _code_only(source: str) -> str:
    """`source` with every string and comment token dropped, tokens joined
    without whitespace, so `World . is_active` reads `World.is_active`."""
    out: list[str] = []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type in (tokenize.STRING, tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE,
                        tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING, tokenize.ENDMARKER):
            continue
        if sys.version_info >= (3, 12) and tok.type in (
            tokenize.FSTRING_START, tokenize.FSTRING_MIDDLE, tokenize.FSTRING_END,
        ):
            continue
        out.append(tok.string)
        out.append(" " if tok.type == tokenize.NAME else "")
    return "".join(out).replace(" .", ".").replace(". ", ".").replace(" (", "(")


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _calls(tree: ast.AST, name_test) -> list[ast.Call]:
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call) and name_test(_call_name(n))]


def _has_world_kw(call: ast.Call) -> bool:
    return any(kw.arg == "world_id" for kw in call.keywords)


def rule_dw1() -> int:
    files = sorted({*PACKAGE.glob("day_*.py"), *(PACKAGE / "cockpit").glob("day_*.py")})
    if len(files) < MIN_DAY_FILES:
        fail(f"DW1: {len(files)} day module file(s), expected at least {MIN_DAY_FILES}")
    reached = 0
    units: list[tuple[str, str, ast.AST]] = []
    for path in files:
        source = path.read_text(encoding="utf-8")
        units.append((str(path.relative_to(ROOT)), source, ast.parse(source)))
    route_source = DAY_ROUTE.read_text(encoding="utf-8")
    route_tree = ast.parse(route_source)
    found = {n.name: n for n in route_tree.body if isinstance(n, ast.FunctionDef)}
    for name in DAY_FUNCTIONS:
        node = found.get(name)
        if node is None:
            fail(f"DW1: routes/day.py defines no top-level {name}")
            continue
        segment = ast.get_source_segment(route_source, node) or ""
        units.append((f"routes/day.py::{name}", segment, node))
    for label, source, tree in units:
        reached += 1
        code = _code_only(source)
        for token in BANNED:
            if token in code:
                fail(f"DW1: {label} holds {token!r}")
        for call in _calls(tree, lambda n: n == "premised_prompt"):
            if not _has_world_kw(call):
                fail(f"DW1: {label}:{call.lineno} calls premised_prompt( without world_id=")
    who = _calls(ast.parse(CONCORDANCE.read_text(encoding="utf-8")), lambda n: n == "who_is_at")
    if len(who) != 2:
        fail(f"DW1: day_concordance.py holds {len(who)} who_is_at( call(s), expected 2")
    for call in who:
        if not _has_world_kw(call):
            fail(f"DW1: day_concordance.py:{call.lineno} calls who_is_at( without world_id=")
    extracts = _calls(route_tree, lambda n: n in ("extract_places", "extract_persons", "extract_factions"))
    if len(extracts) != 3:
        fail(f"DW1: routes/day.py holds {len(extracts)} extract_*( call(s), expected 3")
    for call in extracts:
        if not _has_world_kw(call):
            fail(f"DW1: routes/day.py:{call.lineno} calls {_call_name(call)}( without world_id=")
    return reached


# --- fixture -------------------------------------------------------------------

def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{pathlib.Path(tmp_dir) / 'check.db'}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]
    from sqlmodel import SQLModel

    import world_engine.models  # noqa: F401 -- registers every table
    from world_engine.db import engine

    SQLModel.metadata.create_all(engine)
    return engine


def _add_entity(db, world_id: str, name: str, *, character_type: str | None = None,
                entity_type: str = "character") -> str:
    from world_engine.models import Character, Entity, Location

    entity = Entity(world_id=world_id, type=entity_type, name=name)
    db.add(entity)
    db.flush()
    if character_type is not None:
        db.add(Character(id=entity.id, world_id=world_id, character_type=character_type))
    if entity_type == "location":
        db.add(Location(id=entity.id))
    db.flush()
    return entity.id


def _open_day(db, world_id: str, character_id: str) -> tuple[str, object]:
    from datetime import UTC, datetime

    from world_engine.models import Session as GameSession
    from world_engine.writes import write_batch, write_pass_play

    sess = GameSession(world_id=world_id, number=1, title="check", status="open",
                       started_at=datetime.now(UTC))
    db.add(sess)
    db.flush()
    batch = write_batch(db, session_id=sess.id, changed_by="player")
    db.add(batch)
    db.flush()
    pass_play = write_pass_play(db, batch_id=batch.id, session_id=sess.id,
                                character_id=character_id, declared_action="Je flâne au port.")
    db.add(pass_play)
    db.commit()
    return batch.id, pass_play


# --- DW2 -----------------------------------------------------------------------

def rule_dw2(engine) -> int:
    from fastapi import HTTPException
    from sqlmodel import Session

    import world_premise as wp_check  # the check module, for its `_seed_head`
    from world_engine.cockpit.routes.day import _day_character, _day_world
    from world_engine.models import NpcSchedule, PassPlay, World
    from world_engine.prompt_store import premised_prompt
    from world_engine.schedule_reads import who_is_at

    reached = 0
    with Session(engine) as db:
        world_a = World(name="Alpha", description="Monde A", is_active=True)
        world_b = World(name="Beta", description="Monde B", is_active=False)
        db.add(world_a)
        db.add(world_b)
        db.flush()
        _add_entity(db, world_a.id, "Ana", character_type="player")
        bea = _add_entity(db, world_b.id, "Bea", character_type="player")
        garde = _add_entity(db, world_b.id, "Garde", character_type="npc")
        port = _add_entity(db, world_b.id, "Port", entity_type="location")
        db.add(NpcSchedule(world_id=world_b.id, npc_id=garde, phase="matin", location_id=port))
        db.commit()
        batch_id, pass_play = _open_day(db, world_b.id, bea)

        reached += 1
        if _day_world(batch_id, db) != world_b.id:
            fail("DW2: _day_world did not answer the day's world B")
        reached += 1
        try:
            _day_world("no-such-batch", db)
            fail("DW2: _day_world answered for an unknown batch")
        except HTTPException as exc:
            if exc.status_code != 404:
                fail(f"DW2: unknown batch -> {exc.status_code}, expected 404")
        reached += 1
        if _day_character(pass_play, db).id != bea:
            fail("DW2: _day_character did not answer Bea")
        reached += 1
        stray = PassPlay(batch_id=batch_id, session_id=pass_play.session_id, character_id=garde,
                         declared_action="x", status="submitted", batch_order=2, history=[])
        try:
            _day_character(stray, db)
            fail("DW2: _day_character accepted an NPC's day")
        except HTTPException as exc:
            if exc.status_code != 409:
                fail(f"DW2: an NPC's day -> {exc.status_code}, expected 409")

        head, _version = wp_check._seed_head(db, "day_plan", "{world_premise}X")
        db.commit()
        reached += 1
        text_b = premised_prompt(db, head, world_id=world_b.id).system_prompt
        if "Monde B" not in text_b or "Monde A" in text_b:
            fail(f"DW2: premised_prompt(world_id=B) is {text_b!r}")
        reached += 1
        text_active = premised_prompt(db, head).system_prompt
        if "Monde A" not in text_active:
            fail(f"DW2: premised_prompt() without world_id is {text_active!r}")

        reached += 1
        if garde not in who_is_at(port, "matin", db, is_present=True, world_id=world_b.id):
            fail("DW2: who_is_at(world_id=B) does not hold Garde")
        reached += 1
        if garde in who_is_at(port, "matin", db, is_present=True):
            fail("DW2: who_is_at() without world_id holds Garde of the inactive world")
    return reached


# --- DW3 -----------------------------------------------------------------------

def _day_count(db) -> int:
    from sqlmodel import func, select

    from world_engine.models import PassPlay

    db.rollback()
    return db.exec(select(func.count()).select_from(PassPlay)).one()


def rule_dw3(engine) -> int:
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    import quests as q_check  # the check module, for its fixture helpers
    from world_engine.cockpit.app import app
    from world_engine.cockpit import day_declare
    from world_engine.models import Character, PassPlay, Quest, World
    from world_engine.writes.quests import abandon_quest, accept_quest, write_quest_offer

    reached = 0
    originals = (day_declare.missing_usages, day_declare.enqueue_day)
    day_declare.missing_usages = lambda *a, **k: []
    day_declare.enqueue_day = lambda batch_id: None
    try:
        with Session(engine) as db:
            for world in db.exec(__import__("sqlmodel").select(World)).all():
                world.is_active = False
                db.add(world)
            db.commit()
            ids = q_check._qb_world(db)
            world = db.get(World, ids["world"])
            world.is_active = True
            db.add(world)
            db.commit()
            offer = write_quest_offer(db, **q_check._offer_kwargs(ids, eligibility=None))
            db.commit()
            quest = accept_quest(db, offer=offer, character=db.get(Character, ids["pc"]))
            db.commit()
            quest_id = quest.id

            client = TestClient(app, base_url="http://127.0.0.1")
            body = {"declared_action": "Je traque le loup."}

            reached += 1
            resp = client.post("/api/day/declare", json={**body, "quest_id": quest_id})
            if resp.status_code != 200:
                fail(f"DW3: declare with a quest -> {resp.status_code} {resp.text}")
            else:
                db.rollback()
                row = db.get(PassPlay, resp.json()["pass_play_id"])
                if row is None or row.quest_id != quest_id:
                    fail(f"DW3: the day's quest_id is {getattr(row, 'quest_id', None)!r}")

            reached += 1
            before = _day_count(db)
            resp = client.post("/api/day/declare", json={**body, "quest_id": "no-such-quest"})
            if resp.status_code != 404:
                fail(f"DW3: unknown quest -> {resp.status_code}, expected 404")
            if _day_count(db) != before:
                fail("DW3: an unknown quest still wrote a day")

            reached += 1
            abandon_quest(db, quest=db.get(Quest, quest_id))
            db.commit()
            before = _day_count(db)
            resp = client.post("/api/day/declare", json={**body, "quest_id": quest_id})
            if resp.status_code != 409 or resp.json().get("detail") != TERMINATED:
                fail(f"DW3: abandoned quest -> {resp.status_code} {resp.text}")
            if _day_count(db) != before:
                fail("DW3: an abandoned quest still wrote a day")

            reached += 1
            resp = client.post("/api/day/declare", json=body)
            if resp.status_code != 200:
                fail(f"DW3: declare without a quest -> {resp.status_code} {resp.text}")
            else:
                db.rollback()
                row = db.get(PassPlay, resp.json()["pass_play_id"])
                if row is None or row.quest_id is not None:
                    fail(f"DW3: an unpinned day's quest_id is {getattr(row, 'quest_id', None)!r}")
    finally:
        day_declare.missing_usages, day_declare.enqueue_day = originals
    return reached


def main() -> int:
    expected = {"DW2": 8, "DW3": 4}
    reached: dict[str, int] = {}
    if rule_dw1() == 0:
        fail("DW1 scanned nothing")
    engine = _fresh_engine()
    for rule, fn in (("DW2", rule_dw2), ("DW3", rule_dw3)):
        try:
            reached[rule] = fn(engine)
        except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
            fail(f"{rule} raised {type(exc).__name__}: {exc}")
    for rule, count in expected.items():
        if reached.get(rule, 0) != count:
            fail(f"{rule} reached {reached.get(rule, 0)} of its {count} rows")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: day_chain_world -- DW1-DW3")
    return 0


if __name__ == "__main__":
    sys.exit(main())
