"""G1 check for TICKET-0097 -- a knowledge row is identified by the fact it
knows, never by its free-text `subject`.

K1 -- model. `knowledge` declares the unique index
   `idx_knowledge_entity_fact` on exactly `(entity_id, fact_id)`;
   `discoverable_detail.fact_id` is a nullable foreign key to `fact.id`.
K2 -- migration v2.09 (`scripts/migrate_v2_09_knowledge_identity.py`), run
   on a v2.08-shaped fixture database:
   a. a subject spread over two facts in one world aborts the run, and the
      rolled-back database is unchanged; `creator_meta` spread over two
      facts does not abort;
   b. a duplicated `(entity_id, fact_id)` keeps its highest-level row, the
      other row's state lands in the survivor's `change_history` with its
      `absorbed_knowledge_id`, and `unresolved_mention.knowledge_id` follows
      the survivor;
   c. the unique index exists afterwards;
   d. a `npc:<uuid>` fact of a known entity gets that entity as participant
      and the content `[[e:<uuid>|<name>]]`; its previous content is in the
      fact's `change_history`;
   e. `discoverable_detail.fact_id` exists afterwards;
   f. a knowledge gate keyed by a subject is rekeyed to that subject's
      fact id; a gate keyed by an unknown string is untouched;
   g. a second run changes nothing.
K3 -- census. The `subject` references of `src/world_engine` (an attribute
   `.subject`, a string constant `"subject"`, a `subject=` keyword or a
   `subject` parameter), counted per file, equal `_SUBJECT_CENSUS` exactly.
   Each brief of TICKET-0097 lowers it in the same commit that removes a
   reference; a new reference is red until someone decides it belongs.
K4 -- the mutation pipeline keys knowledge by fact (C-01, C-02):
   a. `knowledge_key` on the `_KEY_CASES` table;
   b. `new_knowledge` without `fact_id` creates a fact whose content is the
      row's stored text (M1);
   c. `new_knowledge` with a `fact_id` attaches to it once; a second apply
      for the same entity, or a fact of another world, is refused;
   d. `knowledge_change` finds its row by `fact_id`; a payload without one
      is refused;
   e. two approved discoveries of one detail share the detail's fact (H1);
   f. a `resource_change` knowledge leg the buyer already holds (same text)
      is refused; a leg without content is refused;
   g. window normalization drops a model-emitted `knowledge_change` (N1)
      and strips `subject` / `fact_id` from a model `new_knowledge`.

Fresh temp-file SQLite databases (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import pathlib
import sqlite3
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
MIGRATION_V2_09 = ROOT / "scripts" / "migrate_v2_09_knowledge_identity.py"

FAILURES: list[str] = []

_SUBJECT_CENSUS: dict[str, int] = {
    "src/world_engine/analyzer.py": 2,
    "src/world_engine/analyzer_transcript.py": 10,
    "src/world_engine/cockpit/crud/_shared.py": 3,
    "src/world_engine/cockpit/crud/knowledge.py": 8,
    "src/world_engine/cockpit/crud/locations.py": 7,
    "src/world_engine/cockpit/play_discovery.py": 3,
    "src/world_engine/cockpit/routes/creator.py": 2,
    "src/world_engine/cockpit/routes/day.py": 2,
    "src/world_engine/cockpit/routes/npc_agent.py": 2,
    "src/world_engine/context.py": 4,
    "src/world_engine/day_mutations.py": 4,
    "src/world_engine/day_plan.py": 3,
    "src/world_engine/entity_author.py": 4,
    "src/world_engine/knowledge_resolve.py": 1,
    "src/world_engine/link_author.py": 5,
    "src/world_engine/link_context.py": 4,
    "src/world_engine/lore_render.py": 1,
    "src/world_engine/lore_selectors.py": 2,
    "src/world_engine/models/canon_knowledge.py": 1,
    "src/world_engine/scene_format.py": 3,
    "src/world_engine/subject_resolve.py": 4,
    "src/world_engine/tick.py": 2,
    "src/world_engine/tick_context.py": 1,
    "src/world_engine/tick_normalize.py": 2,
    "src/world_engine/writes/facets.py": 1,
    "src/world_engine/writes/knowledge.py": 8,
    "src/world_engine/writes/relations.py": 1,
}

A = "11111111-1111-1111-1111-111111111111"
B = "22222222-2222-2222-2222-222222222222"
P = "33333333-3333-3333-3333-333333333333"

# The v2.08 shape of the one table v2.09 alters (the other tables come from
# the current metadata; the index v2.09 creates is dropped before the run).
_V2_08_DETAIL = (
    "CREATE TABLE discoverable_detail (id TEXT PRIMARY KEY, world_id TEXT NOT NULL, "
    "location_id TEXT NOT NULL, subject TEXT NOT NULL, content TEXT NOT NULL)"
)

_ROWS: tuple[tuple[str, dict], ...] = (
    ("world", {"id": "w1", "name": "W"}),
    ("entity", {"id": A, "world_id": "w1", "type": "character", "name": "Ana"}),
    ("entity", {"id": B, "world_id": "w1", "type": "character", "name": "Bel"}),
    ("entity", {"id": P, "world_id": "w1", "type": "character", "name": "Pio"}),
    ("fact", {"id": "f-topic", "world_id": "w1", "content": "topic"}),
    ("fact", {"id": "f-dup", "world_id": "w1", "content": "dup"}),
    ("fact", {"id": "f-npc", "world_id": "w1", "content": f"npc:{B}"}),
    ("fact", {"id": "f-meta-a", "world_id": "w1", "content": "note a"}),
    ("fact", {"id": "f-meta-b", "world_id": "w1", "content": "note b"}),
    ("knowledge", {"id": "k-a-topic", "entity_id": A, "fact_id": "f-topic", "subject": "topic",
                   "level": "knows"}),
    ("knowledge", {"id": "k-b-topic", "entity_id": B, "fact_id": "f-topic", "subject": "topic",
                   "level": "rumor"}),
    ("knowledge", {"id": "k-dup-low", "entity_id": A, "fact_id": "f-dup", "subject": "dup",
                   "level": "rumor", "content": "low"}),
    ("knowledge", {"id": "k-dup-high", "entity_id": A, "fact_id": "f-dup", "subject": "dup",
                   "level": "knows", "content": "high"}),
    ("knowledge", {"id": "k-npc", "entity_id": A, "fact_id": "f-npc", "subject": f"npc:{B}",
                   "level": "knows"}),
    ("knowledge", {"id": "k-meta-a", "entity_id": A, "fact_id": "f-meta-a",
                   "subject": "creator_meta", "level": "unaware"}),
    ("knowledge", {"id": "k-meta-b", "entity_id": B, "fact_id": "f-meta-b",
                   "subject": "creator_meta", "level": "unaware"}),
    ("unresolved_mention", {"id": "um-1", "world_id": "w1", "knowledge_id": "k-dup-low",
                            "surface": "s", "reason": "inconnu"}),
    ("agenda", {"id": "ag-1", "world_id": "w1", "owner_entity_id": P, "title": "t"}),
    ("agenda_step", {"id": "ags-1", "agenda_id": "ag-1", "step_order": 1, "objective": "o"}),
    ("agenda_step_requirement", {"id": "req-topic", "world_id": "w1", "step_id": "ags-1",
                                 "type": "knowledge", "target_key": "topic"}),
    ("agenda_step_requirement", {"id": "req-ghost", "world_id": "w1", "step_id": "ags-1",
                                 "type": "knowledge", "target_key": "ghost"}),
)
_SPLIT_ROWS: tuple[tuple[str, dict], ...] = (
    ("fact", {"id": "f-split", "world_id": "w1", "content": "topic"}),
    ("knowledge", {"id": "k-split", "entity_id": P, "fact_id": "f-split", "subject": "topic",
                   "level": "rumor"}),
)


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{pathlib.Path(tmp_dir) / 'check.db'}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]
    from world_engine.db import create_db_and_tables, engine
    create_db_and_tables()
    return engine


def rule_k1(tables) -> None:
    knowledge = tables["knowledge"]
    matches = [ix for ix in knowledge.indexes if ix.name == "idx_knowledge_entity_fact"]
    if not matches:
        fail("K1 knowledge declares no idx_knowledge_entity_fact")
    elif not matches[0].unique or [c.name for c in matches[0].columns] != ["entity_id", "fact_id"]:
        fail("K1 idx_knowledge_entity_fact is not UNIQUE on exactly (entity_id, fact_id)")
    column = tables["discoverable_detail"].c.get("fact_id")
    if column is None:
        fail("K1 discoverable_detail declares no fact_id")
    elif not column.nullable or [fk.column.table.name for fk in column.foreign_keys] != ["fact"]:
        fail("K1 discoverable_detail.fact_id is not a nullable foreign key to fact")


def _insert(cursor, rows) -> None:
    for table, values in rows:
        values = dict(values)
        if table == "fact":
            values.setdefault("created_by", "check")
            values.setdefault("change_history", "[]")
        if table == "knowledge":
            values.setdefault("change_history", "[]")
            values.setdefault("updated_at", "2026-01-01 00:00:00")
        columns = ", ".join(values)
        marks = ", ".join("?" for _ in values)
        cursor.execute(f"INSERT INTO {table} ({columns}) VALUES ({marks})", tuple(values.values()))


def _v2_08_database() -> sqlite3.Connection:
    """A second database, built from the current metadata, then taken back
    to the v2.08 shape of the two objects v2.09 creates."""
    from sqlalchemy import create_engine
    from sqlmodel import SQLModel

    db_path = pathlib.Path(tempfile.mkdtemp()) / "v2_08.db"
    SQLModel.metadata.create_all(create_engine(f"sqlite:///{db_path}"))
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.execute("DROP INDEX idx_knowledge_entity_fact")
    conn.execute("DROP TABLE discoverable_detail")
    conn.execute(_V2_08_DETAIL)
    _insert(conn.cursor(), _ROWS)
    return conn


def _load_migration():
    spec = importlib.util.spec_from_file_location("migrate_v2_09_check", MIGRATION_V2_09)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _snapshot(conn) -> dict:
    return {
        table: conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
        for table in ("knowledge", "fact", "fact_participant", "agenda_step_requirement")
    }


def _run(conn, migration):
    cursor = conn.cursor()
    cursor.execute("BEGIN")
    try:
        report = migration.migrate(cursor)
    except migration.Abort:
        cursor.execute("ROLLBACK")
        raise
    cursor.execute("COMMIT")
    return report


def _k2a(conn, migration) -> None:
    before = _snapshot(conn)
    _insert(conn.cursor(), _SPLIT_ROWS)
    try:
        _run(conn, migration)
        fail("K2a a subject on two facts did not abort the migration")
    except migration.Abort as exc:
        if "'topic' on 2 facts" not in str(exc):
            fail(f"K2a abort message does not name the split subject: {exc}")
    conn.execute("DELETE FROM knowledge WHERE id = 'k-split'")
    conn.execute("DELETE FROM fact WHERE id = 'f-split'")
    if _snapshot(conn) != before:
        fail("K2a the aborted run changed the database")


def _k2b_to_f(conn) -> None:
    rows = conn.execute("SELECT id, level, change_history FROM knowledge WHERE fact_id = 'f-dup'").fetchall()
    if [(r[0], r[1]) for r in rows] != [("k-dup-high", "knows")]:
        fail(f"K2b duplicate group left {rows!r}, expected only k-dup-high")
    else:
        history = json.loads(rows[0][2])
        if [h.get("absorbed_knowledge_id") for h in history] != ["k-dup-low"] or history[0]["content"] != "low":
            fail(f"K2b survivor change_history is {history!r}")
    if conn.execute("SELECT knowledge_id FROM unresolved_mention").fetchone() != ("k-dup-high",):
        fail("K2b unresolved_mention does not follow the survivor")
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'idx_knowledge_entity_fact'").fetchone():
        fail("K2c idx_knowledge_entity_fact missing after the run")
    content, history = conn.execute("SELECT content, change_history FROM fact WHERE id = 'f-npc'").fetchone()
    if content != f"[[e:{B}|Bel]]" or json.loads(history)[-1].get("content") != f"npc:{B}":
        fail(f"K2d npc fact is {content!r} with history {history!r}")
    if conn.execute("SELECT entity_id FROM fact_participant WHERE fact_id = 'f-npc'").fetchall() != [(B,)]:
        fail("K2d npc fact does not carry its entity as participant")
    if "fact_id" not in [r[1] for r in conn.execute("PRAGMA table_info(discoverable_detail)")]:
        fail("K2e discoverable_detail.fact_id missing after the run")
    gates = dict(conn.execute("SELECT id, target_key FROM agenda_step_requirement").fetchall())
    if gates != {"req-topic": "f-topic", "req-ghost": "ghost"}:
        fail(f"K2f gates are {gates!r}")


def rule_k2() -> None:
    migration = _load_migration()
    conn = _v2_08_database()
    _k2a(conn, migration)
    try:
        _run(conn, migration)
    except migration.Abort as exc:
        fail(f"K2 the migration aborted on a clean fixture: {exc}")
        return
    _k2b_to_f(conn)
    before = _snapshot(conn)
    report = _run(conn, migration)
    if report["absorbed"] or report["index_created"] or report["npc_facts"]["token"] \
            or report["detail_column_added"] or report["gates_rekeyed"] or _snapshot(conn) != before:
        fail(f"K2g the second run changed something: {report!r}")


_KEY_CASES: tuple[tuple[dict, tuple[str, str]], ...] = (
    ({"fact_id": "f-9"}, ("fact", "f-9")),
    ({"fact_id": "f-9", "content": "Le Conseil ment"}, ("fact", "f-9")),
    ({"content": "Le Conseil cache l'un de ses membres."}, ("text", "le_conseil_cache_lun_de")),
    ({"content": ""}, ("text", "unknown")),
    ({}, ("text", "unknown")),
)


def _k4_world(session):
    from world_engine.models import Character, DiscoverableDetail, Entity, World

    ids = {}
    for key, name in (("w", "W"), ("w2", "W2")):
        world = World(name=name)
        session.add(world)
        session.flush()
        ids[key] = world.id
    for key, world_key, etype, name in (
        ("ana", "w", "character", "Ana"), ("bel", "w", "character", "Bel"),
        ("loc", "w", "location", "Lieu"), ("out", "w2", "character", "Out"),
    ):
        entity = Entity(world_id=ids[world_key], type=etype, name=name)
        session.add(entity)
        session.flush()
        ids[key] = entity.id
        if etype == "character":
            session.add(Character(id=entity.id, world_id=ids[world_key], character_type="npc"))
    detail = DiscoverableDetail(world_id=ids["w"], location_id=ids["loc"], subject="lettre",
                                content="Une lettre cachée sous le comptoir.")
    session.add(detail)
    session.flush()
    ids["detail"] = detail.id
    return ids


def _k4_mutation(session, world_id: str, mutation_type: str):
    from world_engine.models import ProposedMutation

    mut = ProposedMutation(world_id=world_id, source_type="conversation", mutation_type=mutation_type,
                           payload={}, status="proposed", proposed_by="check")
    session.add(mut)
    session.flush()
    return mut


def _k4_apply(session, ids) -> None:
    from sqlmodel import select

    from world_engine.cockpit.mutations import (
        _mutation_apply_knowledge_change, _mutation_apply_new_knowledge,
        _mutation_apply_resource_change,
    )
    from world_engine.models import DiscoverableDetail, Fact, Knowledge
    from world_engine.writes import create_fact

    new = _k4_mutation(session, ids["w"], "new_knowledge")
    err = _mutation_apply_new_knowledge(new, {"entity_id": ids["ana"], "content": "La mer est rouge."}, session)
    row = session.exec(select(Knowledge).where(Knowledge.entity_id == ids["ana"])).one()
    fact = session.get(Fact, row.fact_id)
    if err or fact.content_raw != row.content_raw:
        fail(f"K4b a new fact does not carry the row's text: err={err!r} fact={fact.content_raw!r}")
    shared = create_fact(session, world_id=ids["w"], content="Le port ferme.", created_by="check",
                         facet="information")
    foreign = create_fact(session, world_id=ids["w2"], content="Ailleurs.", created_by="check",
                          facet="information")
    session.flush()
    for entity, fact_id, expect in ((ids["bel"], shared.id, None), (ids["bel"], shared.id, "already knows"),
                                    (ids["bel"], foreign.id, "not a fact of this world")):
        err = _mutation_apply_new_knowledge(
            new, {"entity_id": entity, "fact_id": fact_id, "content": "x", "level": "rumor"}, session)
        if (err is None) != (expect is None) or (expect and expect not in err):
            fail(f"K4c new_knowledge on fact {fact_id[:6]}: got {err!r}, expected {expect!r}")
    session.flush()
    change = _k4_mutation(session, ids["w"], "knowledge_change")
    err = _mutation_apply_knowledge_change(
        change, {"entity_id": ids["bel"], "fact_id": shared.id, "to_level": "knows"}, session)
    level = session.exec(select(Knowledge.level).where(
        Knowledge.entity_id == ids["bel"], Knowledge.fact_id == shared.id)).one()
    if err or level != "knows":
        fail(f"K4d knowledge_change by fact_id: err={err!r} level={level!r}")
    err = _mutation_apply_knowledge_change(
        change, {"entity_id": ids["bel"], "subject": "Le port ferme.", "to_level": "fully_understands"}, session)
    if not err or "fact_id" not in err:
        fail(f"K4d a knowledge_change without fact_id was not refused: {err!r}")
    for learner in ("ana", "bel"):
        err = _mutation_apply_new_knowledge(new, {
            "entity_id": ids[learner], "content": "Une lettre cachée sous le comptoir.",
            "level": "knows", "discoverable_detail_id": ids["detail"]}, session)
        if err:
            fail(f"K4e discovery by {learner} refused: {err!r}")
        session.flush()
    detail = session.get(DiscoverableDetail, ids["detail"])
    holders = session.exec(select(Knowledge.entity_id).where(Knowledge.fact_id == detail.fact_id)).all()
    if not detail.discovered or sorted(holders) != sorted([ids["ana"], ids["bel"]]):
        fail(f"K4e the detail's fact is not shared by both discoverers: {holders!r}")
    buy = _k4_mutation(session, ids["w"], "resource_change")
    for leg, expect in (({"entity_id": ids["ana"], "content": "La mer est rouge."}, "already held"),
                        ({"entity_id": ids["ana"], "subject": "mer_rouge"}, "content")):
        err = _mutation_apply_resource_change(buy, {"entity_id": ids["ana"], "amount": 0,
                                                    "knowledge": leg}, session)
        if not err or expect not in err:
            fail(f"K4f resource leg {leg!r}: got {err!r}, expected {expect!r}")


def _k4_window() -> None:
    from world_engine.analyzer_transcript import AttributionContext, _normalize_to_schema

    attribution = AttributionContext(default_subject_id="npc", default_counterparty_id="pc")
    item, _u, _mt = _normalize_to_schema(
        {"mutation_type": "knowledge_change", "payload": {"entity_id": "pc", "subject": "x"}},
        "w", attribution, None)
    if item is not None:
        fail("K4g a model-emitted knowledge_change was not dropped (N1)")
    item, _u, _mt = _normalize_to_schema(
        {"mutation_type": "new_knowledge", "target_table": "knowledge",
         "payload": {"entity_id": "pc", "subject": "mer_rouge", "fact_id": "forged", "content": ""}},
        "w", attribution, None)
    payload = item["payload"] if item else {}
    if "subject" in payload or "fact_id" in payload or payload.get("content") != "mer_rouge":
        fail(f"K4g a model new_knowledge payload kept a fact name: {payload!r}")


def rule_k4(engine) -> None:
    from sqlmodel import Session

    from world_engine.fact_refs import knowledge_key

    for payload, expected in _KEY_CASES:
        if knowledge_key(payload) != expected:
            fail(f"K4a knowledge_key({payload!r}) = {knowledge_key(payload)!r}, expected {expected!r}")
    with Session(engine) as session:
        ids = _k4_world(session)
        _k4_apply(session, ids)
        session.rollback()
    _k4_window()


def census() -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in sorted((SRC / "world_engine").rglob("*.py")):
        n = 0
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Attribute) and node.attr == "subject":
                n += 1
            elif isinstance(node, ast.Constant) and node.value == "subject":
                n += 1
            elif isinstance(node, (ast.keyword, ast.arg)) and node.arg == "subject":
                n += 1
        if n:
            counts[path.relative_to(ROOT).as_posix()] = n
    return counts


def rule_k3() -> None:
    counts = census()
    for path in sorted(set(counts) | set(_SUBJECT_CENSUS)):
        if counts.get(path, 0) != _SUBJECT_CENSUS.get(path, 0):
            fail(f"K3 {path}: {counts.get(path, 0)} subject reference(s), census pins "
                 f"{_SUBJECT_CENSUS.get(path, 0)}")


def main() -> int:
    engine = _fresh_engine()
    from sqlmodel import SQLModel

    import world_engine.models  # noqa: F401 -- registers every table

    rule_k1(SQLModel.metadata.tables)
    rule_k2()
    rule_k3()
    rule_k4(engine)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: knowledge_identity -- knowledge is unique per (entity, fact); v2.09 migrates "
          "and is idempotent; the subject census matches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
