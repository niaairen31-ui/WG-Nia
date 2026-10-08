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
K9 -- migration v2.10 (`scripts/migrate_v2_10_drop_knowledge_subject.py`),
   run on the K2 database after v2.09:
   a. a row whose subject is neither `creator_meta`, nor its fact's content,
      nor backed by a participant aborts the run;
   b. otherwise `knowledge.subject` and `idx_knowledge_subject` are gone and
      the row count is unchanged;
   c. a second run reports the column already gone.
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
K5 -- models name facts by code (C-03, C-04, C-05):
   a. `code_facts` / `CodedFacts` on the `_CODE_CASES` table;
   b. overhearing (L1): the classifier's list shows the speaker's
      non-secret fact and never the text of its secret one; the code the
      model answers resolves to that fact -- an unaware bystander gets a
      `new_knowledge` on it, a bystander holding it lower gets a
      `knowledge_change` on it; an unknown code proposes nothing;
   c. the tick briefing tags each knowledge line with its fact code, and
      the tick normalizer (Z2) resolves `source_fact`: a secret source sets
      `secret_derived` and the `fact_id`, never `is_secret`; an unknown code
      sets neither; a content containing a secret's text sets
      `secret_derived`.
K6 -- day gates name facts (D1'a, C-06):
   a. `learnable_facts` codes exactly the facts another entity of the world
      holds on a non-secret row and the character does not hold, ordered by
      text;
   b. `emit_plan` appends that list, and a `knowledge` requirement's code
      comes back as its fact id; an unknown code comes back as emitted, and
      `anchor_requirements` drops it;
   c. `_eval_knowledge` judges by fact id and carries the fact's text as
      `required_label`, which `requirement_detail_fr` shows instead of the id;
   d. a blocked step's lead is a `new_knowledge` on the gate's fact.
K7 -- aboutness is the fact's participants (G1, H1):
   a. a staged link-agent knowledge row stamps `subject_entity_ids =
      [other side]`; committed, its new fact carries that participant;
   b. `_shared_knowledge_lines` shows what the holder knows on facts the
      other side participates in, and nothing about a third party;
   c. the link canon graph lists a roster-touching knowledge row with its
      fact's `about_entity_ids`;
   d. a signpost cluster is silent once the player knows the fact of every
      hidden detail in it, and speaks while one detail has no fact yet.
K8 -- the creator surface (K1, I1, J1, C-08):
   a. `unbound_facts` lists a known free fact without participant with its
      text, first knower's version, knower count and the resolver's single
      candidate for a name; a bound fact and a typed fact are not listed;
   b. the creator CRUD creates a row without `subject` (the fact carries
      the content) and refuses a create with neither content nor fact_id;
      the knowledge dict carries no `subject` key.

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
MIGRATION_V2_10 = ROOT / "scripts" / "migrate_v2_10_drop_knowledge_subject.py"

FAILURES: list[str] = []

_SUBJECT_CENSUS: dict[str, int] = {
    "src/world_engine/analyzer_transcript.py": 3,
    "src/world_engine/cockpit/crud/locations.py": 7,
    "src/world_engine/cockpit/play_discovery.py": 1,
    # TICKET-0101, BRIEF-0101-C: `discoverable_detail.subject`, the label a
    # promotion lists for a detail it moves -- never a knowledge key.
    "src/world_engine/writes/zone_promotion.py": 3,
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
    to the v2.08 shape: without the two objects v2.09 creates, and with the
    `knowledge.subject` column and index v2.10 drops."""
    from sqlalchemy import create_engine
    from sqlmodel import SQLModel

    db_path = pathlib.Path(tempfile.mkdtemp()) / "v2_08.db"
    SQLModel.metadata.create_all(create_engine(f"sqlite:///{db_path}"))
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.execute("DROP INDEX idx_knowledge_entity_fact")
    conn.execute("ALTER TABLE knowledge ADD COLUMN subject TEXT NOT NULL DEFAULT ''")
    conn.execute("CREATE INDEX idx_knowledge_subject ON knowledge(subject)")
    conn.execute("DROP TABLE discoverable_detail")
    conn.execute(_V2_08_DETAIL)
    _insert(conn.cursor(), _ROWS)
    return conn


def _load_migration(path: pathlib.Path = MIGRATION_V2_09):
    spec = importlib.util.spec_from_file_location(f"{path.stem}_check", path)
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
    _k9(conn)


def _k9(conn) -> None:
    """K9 on the migrated K2 database."""
    drop = _load_migration(MIGRATION_V2_10)
    cursor = conn.cursor()
    count = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
    conn.execute("INSERT INTO fact (id, world_id, content, created_by, change_history) "
                 "VALUES ('f-lone', 'w1', 'lone', 'check', '[]')")
    conn.execute("INSERT INTO knowledge (id, entity_id, fact_id, subject, level, change_history, "
                 "updated_at) VALUES ('k-lone', ?, 'f-lone', 'other label', 'rumor', '[]', "
                 "'2026-01-01 00:00:00')", (P,))
    for expect_abort in (True, False):
        cursor.execute("BEGIN")
        try:
            dropped = drop.migrate(cursor)
            cursor.execute("COMMIT")
            if expect_abort:
                fail("K9a a label with no fact content and no participant did not abort v2.10")
        except drop.Abort:
            cursor.execute("ROLLBACK")
            if not expect_abort:
                fail("K9b v2.10 aborted on a clean database")
                return
        conn.execute("DELETE FROM knowledge WHERE id = 'k-lone'")
        conn.execute("DELETE FROM fact WHERE id = 'f-lone'")
    columns = [row[1] for row in conn.execute("PRAGMA table_info(knowledge)")]
    if not dropped or "subject" in columns or conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name = 'idx_knowledge_subject'").fetchone():
        fail(f"K9b knowledge.subject or its index survived v2.10: {columns!r}")
    if conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0] != count:
        fail("K9b v2.10 changed the knowledge row count")
    cursor.execute("BEGIN")
    if drop.migrate(cursor) is not False:
        fail("K9c a second v2.10 run did not report the column already gone")
    cursor.execute("COMMIT")


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


def _k5_codes(session, ids) -> None:
    from world_engine.fact_refs import code_facts
    from world_engine.writes import create_fact

    one = create_fact(session, world_id=ids["w"], content="Un.", created_by="check", facet="information")
    two = create_fact(session, world_id=ids["w"], content="Deux.", created_by="check", facet="information")
    session.flush()
    coded = code_facts(session, [two.id, one.id, two.id, "no-such-fact"])
    cases = (
        (coded.lines, ("f1 — Deux.", "f2 — Un.")), (coded.resolve("f2"), one.id),
        (coded.resolve("[F1]"), two.id), (coded.resolve(" f1 "), two.id), (coded.resolve("f3"), None),
        (coded.resolve(1), None), (coded.code_of(one.id), "f2"), (coded.code_of("no-such-fact"), None),
    )
    for index, (got, expected) in enumerate(cases):
        if got != expected:
            fail(f"K5a case {index}: got {got!r}, expected {expected!r}")


def _k5_prompt_head(session, usage: str) -> None:
    from world_engine.models import PromptTemplate
    from world_engine.writes import write_prompt_variables, write_prompt_version

    head = PromptTemplate(world_id=None, name=f"check-{usage}", usage=usage, is_active=True)
    session.add(head)
    session.flush()
    write_prompt_variables(session, template_id=head.id, variables=["fact_list", "player_line", "npc_line"])
    write_prompt_version(session, template_id=head.id, system_prompt="sys",
                         user_template="{fact_list}|{player_line}|{npc_line}")


def _k5_overhearing(session, ids) -> None:
    import json as _json

    from world_engine import ollama_client
    from world_engine.analyzer_transcript import AttributionContext, analyze_overheard_lines
    from world_engine.writes import write_knowledge

    spoken = write_knowledge(session, entity_id=ids["bel"], content="Le pont est tombé.", level="knows")
    write_knowledge(session, entity_id=ids["bel"], content="Bel vole le trésor.", level="knows",
                    is_secret=True)
    write_knowledge(session, entity_id=ids["cid"], fact_id=spoken.fact_id, content="x", level="rumor")
    _k5_prompt_head(session, "overhearing_classification")
    session.flush()
    seen: list[str] = []
    original = ollama_client.chat

    def stub(messages, **_kw):
        seen.append(messages[-1]["content"])
        return _json.dumps(answer)

    ollama_client.chat = stub
    try:
        results = []
        for answer in ([{"fact": "f1", "speaker": "npc"}], [{"fact": "f9", "speaker": "npc"}]):
            results.append(analyze_overheard_lines(
                speaker_line="...", listener_line="...", receiver_ids={ids["ana"], ids["cid"]},
                world_id=ids["w"], location_id=None, existing_keys=(set(), set()),
                attribution=AttributionContext(default_subject_id=ids["bel"], default_counterparty_id=None),
                db=session))
    finally:
        ollama_client.chat = original
    if not seen or "f1 — Le pont est tombé." not in seen[0] or "trésor" in seen[0]:
        fail(f"K5b the classifier list is wrong: {seen[:1]!r}")
    got = sorted((m.mutation_type, m.payload.get("entity_id"), m.payload.get("fact_id"))
                 for m in results[0].mutations)
    expected = sorted([("new_knowledge", ids["ana"], spoken.fact_id),
                       ("knowledge_change", ids["cid"], spoken.fact_id)])
    if got != expected or any("subject" in m.payload for m in results[0].mutations):
        fail(f"K5b overhearing proposals are {got!r}, expected {expected!r}")
    if results[1].mutations:
        fail("K5b an unknown code proposed something")


def _k5_tick(session, ids) -> None:
    from sqlmodel import select

    from world_engine.models import Knowledge
    from world_engine.tick_context import _tick_knowledge_block, tick_fact_codes
    from world_engine.tick_normalize import _tick_normalize_new_knowledge

    rows = session.exec(
        select(Knowledge).where(Knowledge.entity_id == ids["bel"]).order_by(Knowledge.id)
    ).all()
    codes = tick_fact_codes(ids["bel"], session)
    secret = next(k for k in rows if k.is_secret)
    block = _tick_knowledge_block(ids["bel"], session)
    if [line[:6] for line in block.splitlines()] != [f"- [f{i}]" for i in range(1, len(rows) + 1)]:
        fail(f"K5c tick briefing lines are not code-tagged: {block!r}")
    secret_code = codes.code_of(secret.fact_id)
    cases = (
        ({"source_fact": secret_code, "is_secret": False}, secret.fact_id, True),
        ({"source_fact": "f99"}, None, False),
        ({"content": "Il murmure que Bel vole le trésor."}, None, True),
    )
    for payload_in, fact_id, derived in cases:
        payload_in = {"recipient": "self", "content": "Une nouvelle.", **payload_in}
        payload, _t = _tick_normalize_new_knowledge(
            payload_in, npc_id=ids["bel"], roster={}, fact_codes=codes,
            secret_fact_ids={secret.fact_id}, secret_texts={"bel vole le trésor."})
        if payload.get("fact_id") != fact_id or payload["secret_derived"] is not derived \
                or payload["is_secret"] is not False:
            fail(f"K5c tick normalizer on {payload_in!r} gave {payload!r}")


def rule_k5(engine) -> None:
    from sqlmodel import Session

    from world_engine.models import Character, Entity

    with Session(engine) as session:
        ids = _k4_world(session)
        cid = Entity(world_id=ids["w"], type="character", name="Cid")
        session.add(cid)
        session.flush()
        session.add(Character(id=cid.id, world_id=ids["w"], character_type="npc"))
        ids["cid"] = cid.id
        _k5_codes(session, ids)
        _k5_overhearing(session, ids)
        _k5_tick(session, ids)
        session.rollback()


def _k6_world(session, ids) -> dict:
    from world_engine.models import Character, Entity, PromptTemplate
    from world_engine.writes import write_knowledge, write_prompt_variables, write_prompt_version

    pc = Entity(world_id=ids["w"], type="character", name="Pia")
    session.add(pc)
    session.flush()
    session.add(Character(id=pc.id, world_id=ids["w"], character_type="player"))
    facts = {}
    for key, text, holder, secret in (
        ("port", "Le port ferme.", "ana", False), ("mer", "La mer monte.", "bel", False),
        ("vol", "Bel vole.", "bel", True), ("held", "Il pleut.", "ana", False),
        ("far", "Ailleurs.", "out", False),
    ):
        facts[key] = write_knowledge(session, entity_id=ids[holder], content=text, level="knows",
                                     is_secret=secret).fact_id
    write_knowledge(session, entity_id=pc.id, fact_id=facts["held"], content="Il pleut.", level="knows")
    head = PromptTemplate(world_id=None, name="check-day-plan", usage="day_plan", is_active=True)
    session.add(head)
    session.flush()
    write_prompt_variables(session, template_id=head.id, variables=["character_name", "declaration"])
    write_prompt_version(session, template_id=head.id, system_prompt="sys",
                         user_template="{character_name}: {declaration}")
    session.flush()
    return {"pc": pc.id, **facts}


def _k6_plan(session, day) -> None:
    import json as _json

    from world_engine import ollama_client
    from world_engine.day_plan import anchor_requirements, emit_plan, learnable_facts
    from world_engine.models import Character

    character = session.get(Character, day["pc"])
    learnable = learnable_facts(character, session)
    if learnable.lines != ("f1 — La mer monte.", "f2 — Le port ferme."):
        fail(f"K6a learnable facts are {learnable.lines!r}")
    sent: list[str] = []
    plan = {"title": "t", "steps": [{"objective": "o", "cost": 1, "domain": None, "requires": [
        {"type": "knowledge", "target_key": "f2"}, {"type": "knowledge", "target_key": "f9"}]}]}

    def stub(messages, **_kw):
        sent.append(messages[-1]["content"])
        return _json.dumps(plan)

    original = ollama_client.chat
    ollama_client.chat = stub
    try:
        steps = emit_plan("déclaration", character, session)
    finally:
        ollama_client.chat = original
    keys = [req.target_key for req in steps[0].requirements]
    if not sent or "f2 — Le port ferme." not in sent[0] or keys != [day["port"], "f9"]:
        fail(f"K6b emit_plan sent {sent[:1]!r} and returned keys {keys!r}")
    anchored, dropped = anchor_requirements(steps, character, session)
    if [r.target_key for r in anchored[0].requirements] != [day["port"]] \
            or [d["target_key"] for d in dropped] != ["f9"]:
        fail(f"K6b anchoring kept {anchored[0].requirements!r}, dropped {dropped!r}")


def _k6_verdicts(session, day) -> None:
    from types import SimpleNamespace

    from world_engine.day_mutations import _emit_new_knowledge
    from world_engine.condition_forms import RequirementSpec, _eval_knowledge
    from world_engine.day_resolve import BLOCKED_BAND, requirement_detail_fr
    from world_engine.models import Character

    character = session.get(Character, day["pc"])
    held = _eval_knowledge(RequirementSpec(type="knowledge", target_key=day["held"]), character, session, None)
    unheld = _eval_knowledge(RequirementSpec(type="knowledge", target_key=day["port"]), character, session, None)
    detail = requirement_detail_fr(unheld)
    if not held.met or unheld.met or unheld.required_label != "Le port ferme." \
            or "Le port ferme." not in detail or day["port"] in detail:
        fail(f"K6c verdicts: held={held!r} unheld={unheld!r} detail={detail!r}")
    outcome = SimpleNamespace(band=BLOCKED_BAND, requirement_verdicts=(unheld,), objective="o", step_order=1)
    leads = _emit_new_knowledge(outcome, SimpleNamespace(id="pp"), character, character.world_id, session)
    if [m.payload.get("fact_id") for m in leads] != [day["port"]] or any("subject" in m.payload for m in leads):
        fail(f"K6d blocked lead payloads are {[m.payload for m in leads]!r}")


def rule_k6(engine) -> None:
    from sqlmodel import Session

    with Session(engine) as session:
        ids = _k4_world(session)
        day = _k6_world(session, ids)
        _k6_plan(session, day)
        _k6_verdicts(session, day)
        session.rollback()


def _k7_link(session, ids) -> None:
    from sqlmodel import select

    from world_engine.link_author import _build_knowledge_row, _shared_knowledge_lines, commit_batch
    from world_engine.link_context import _canon_entries
    from world_engine.models import FactParticipant, Knowledge, LinkBatch
    from world_engine.writes import write_knowledge

    batch = LinkBatch(world_id=ids["w"], scope={"npc_ids": [ids["ana"], ids["bel"]]},
                      coherence_status="complete")
    session.add(batch)
    session.flush()
    row = _build_knowledge_row(batch, ids["ana"], ids["bel"], {
        "holder": "a", "level": "knows", "content": "Bel ment souvent.", "share_threshold": 50})
    if row.payload.get("subject_entity_ids") != [ids["bel"]] or "subject" in row.payload:
        fail(f"K7a staged payload is {row.payload!r}")
    session.add(row)
    session.flush()
    commit_batch(session, batch)
    known = session.exec(select(Knowledge).where(Knowledge.entity_id == ids["ana"])).all()
    about = {p.entity_id for k in known for p in session.exec(
        select(FactParticipant).where(FactParticipant.fact_id == k.fact_id)).all()}
    if about != {ids["bel"]}:
        fail(f"K7a the committed fact's participants are {about!r}")
    write_knowledge(session, entity_id=ids["ana"], content="Le marché ouvre.", level="knows")
    lines = _shared_knowledge_lines(session, ids["ana"], ids["bel"], "Ana")
    if len(lines) != 1 or "Bel ment souvent." not in lines[0]:
        fail(f"K7b shared knowledge lines are {lines!r}")
    rows = [entry[3] for entry in _canon_entries(session, batch) if entry[1] == "knowledge"]
    abouts = sorted(tuple(r["about_entity_ids"]) for r in rows)
    if (ids["bel"],) not in abouts or any("subject" in r for r in rows):
        fail(f"K7c canon graph knowledge rows are {rows!r}")


def _k7_signposts(session, ids) -> None:
    from world_engine.models import DiscoverableDetail
    from world_engine.scene_format import active_signposts
    from world_engine.writes import write_knowledge

    for key, level in (("panel", "ambient"), ("h1", "hidden"), ("h2", "hidden")):
        detail = DiscoverableDetail(world_id=ids["w"], location_id=ids["loc"], subject=key,
                                    content=f"Texte {key}.", access_level=level, signpost_group="g")
        session.add(detail)
        session.flush()
        ids[key] = detail
    h1_fact = write_knowledge(session, entity_id=ids["bel"], content="Texte h1.", level="knows").fact_id
    write_knowledge(session, entity_id=ids["ana"], fact_id=h1_fact, content="x", level="rumor")
    session.flush()
    ids["h1"].fact_id = h1_fact
    session.flush()
    if active_signposts(session, ids["loc"], ids["ana"]) != ["Texte panel."]:
        fail("K7d the cluster fell silent while a detail had no fact")
    h2_fact = write_knowledge(session, entity_id=ids["ana"], content="Texte h2.", level="rumor").fact_id
    session.flush()
    ids["h2"].fact_id = h2_fact
    session.flush()
    if active_signposts(session, ids["loc"], ids["ana"]) != []:
        fail("K7d the cluster still speaks although every hidden fact is known")


def rule_k7(engine) -> None:
    from sqlmodel import Session

    with Session(engine) as session:
        ids = _k4_world(session)
        _k7_link(session, ids)
        _k7_signposts(session, ids)
        session.rollback()


def _k8(session, ids) -> None:
    from fastapi import HTTPException

    from world_engine.cockpit.crud._shared import _knowledge_dict
    from world_engine.cockpit.crud.knowledge import KnowledgeWriteBody, _create_knowledge_core
    from world_engine.unbound_facts import unbound_facts
    from world_engine.writes import attach_participants, write_knowledge
    from world_engine.models import Fact

    named = write_knowledge(session, entity_id=ids["ana"], content="Bel", level="knows")
    write_knowledge(session, entity_id=ids["bel"], fact_id=named.fact_id, content="Elle", level="rumor")
    bound = write_knowledge(session, entity_id=ids["ana"], content="Lié.", level="knows")
    attach_participants(session, fact=session.get(Fact, bound.fact_id), entity_ids=[ids["bel"]])
    session.flush()
    rows = unbound_facts(ids["w"], session)
    listed = {r["fact_id"]: r for r in rows}
    row = listed.get(named.fact_id)
    if row is None or bound.fact_id in listed:
        fail(f"K8a unbound facts are {sorted(listed)!r}")
    elif (row["fact"], row["knower_count"], row["excerpt"], [c["id"] for c in row["candidates"]]) != (
            "Bel", 2, {"entity_name": "Ana", "text": "Bel"}, [ids["bel"]]):
        fail(f"K8a row is {row!r}")
    made = _create_knowledge_core(ids["bel"], KnowledgeWriteBody(level="knows", content="Il neige."), session)
    session.flush()
    if session.get(Fact, made.fact_id).content_raw != "Il neige." or "subject" in _knowledge_dict(made, session):
        fail("K8b the CRUD create does not give the fact the row's content, or the dict has a subject")
    try:
        _create_knowledge_core(ids["bel"], KnowledgeWriteBody(level="knows"), session)
        fail("K8b a create with neither content nor fact_id was accepted")
    except HTTPException as exc:
        if exc.status_code != 422:
            fail(f"K8b refusal status is {exc.status_code}")


def rule_k8(engine) -> None:
    from sqlmodel import Session

    with Session(engine) as session:
        _k8(session, _k4_world(session))
        session.rollback()


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
    rule_k5(engine)
    rule_k6(engine)
    rule_k7(engine)
    rule_k8(engine)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: knowledge_identity -- knowledge is unique per (entity, fact); v2.09 migrates "
          "and is idempotent; the subject census matches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
