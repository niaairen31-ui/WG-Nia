"""G1 check for TICKET-0103 -- the Lore shell's usage journal.

The lot adds its modules brief by brief; this check grows with it (the
`lore_write.py` precedent, TICKET-0098). Each brief adds its rules below in
the same commit.

U0 -- census. The files under `src/world_engine` that name the journal
   (`LoreUsageEvent` or `lore_usage_event`) equal `_NAMING_FILES` exactly,
   and the files that call `write_usage_event` equal `_WRITER_CALLERS`:
   nothing in the application reads the journal, and one module writes it.
   Under `scripts/`, the files naming the journal equal `_SCRIPTS` (its
   migration and its one reader, BRIEF-0103-E).
U1 -- schema (BRIEF-0103-A, v2.13, I1). `lore_usage_event` has no
   `world_id` column and no foreign key at all; `world_ref`, `world_name`,
   `attempt_id`, `kind`, `step`, `outcome`, `payload`, `model_calls` are NOT
   NULL; the CHECK `ck_lore_usage_event_step` lists exactly the pairs of
   `LORE_USAGE_STEPS`, `ck_lore_usage_event_outcome` exactly
   `LORE_USAGE_OUTCOMES`; the indexes are `idx_lore_usage_event_attempt
   (attempt_id, created_at)` and `idx_lore_usage_event_world (world_ref,
   created_at)`.
U2 -- migration `scripts/migrate_v2_13_lore_usage.py`, on a v2.12-shaped
   database (the current schema minus the table):
   a. at v2.11 it refuses (non-zero exit) and creates nothing;
   b. at v2.12 it creates the table, empty, with the columns, NOT NULLs and
      CHECK names of the model, and moves `schema_meta` to the code constant;
   c. a second run changes nothing and exits zero;
   d. on the migrated table a row written by `write_usage_event` reads back
      with its JSON intact, and a raw INSERT with outcome 'x' is refused by
      the database.
U3 -- writer (C-01, C-02). `_good()` is inserted once; every row of
   `_REFUSALS` raises `ValueError` and inserts nothing.
U4 -- the journal outlives its world (F2). A world tagged by a journal row
   is deleted by `delete_world_cascade`; the journal row is still there,
   with its `world_ref` and `world_name` unchanged.
U5 -- the capture shape (BRIEF-0103-B, C-03). The fields of
   `model_exchange.ModelExchange` equal `writes/lore_usage.MODEL_CALL_KEYS`;
   `model_exchange.py` imports nothing from `world_engine`; `prompt_load.load`
   returns the `id` and `version_number` of the head's current
   `prompt_version`.
U6 -- capture (C-03), `chat` stubbed in each module, on seeded prompt heads:
   a. `lore_plan.draft_plan` given a list appends one exchange: usage
      `PLAN_USAGE`, the head's current version id and number, the rendered
      user message, the raw reply; an unparsable reply raises `LlmParseError`
      and the exchange still holds that raw reply;
   b. `lore_render.render` appends one exchange on `answered` (usage
      `PROSE_USAGE`) and none on any other verdict; an `OllamaError` falls
      back to the template and leaves the exchange with no raw reply and the
      error recorded;
   c. `lore_write_draft.draft_questions` and `draft_proposal` each append one
      exchange, usage `QUESTIONS_USAGE` and `PROPOSAL_USAGE`;
   d. every exchange's `to_record()` is accepted by `write_usage_event`.
U7 -- the recorder (BRIEF-0103-C, C-04). `lore_usage.attempt_id` keeps a
   UUID in canonical form and mints a fresh, distinct one for None, '' and a
   malformed id; `record` writes one row carrying the world's name and
   commits it; a world id matching no world is journaled as
   `WORLD_NAME_UNKNOWN`.
U8 -- the writing routes (C-05), `TestClient` on the active fixture world,
   `lore_write_draft.chat` stubbed, one attempt id:
   a. questions answered -> one `questions/ok` row, its questions as
      answered, one model call; Ollama down -> `questions/unavailable`, error
      `WRITE_UNAVAILABLE_MESSAGE`, its model call carrying the error;
   b. draft answered -> one `draft/ok` row whose `draft` equals the response
      body; an unparsable reply -> 502 and one `draft/parse_error` row whose
      model call keeps the raw reply;
   c. a valid commit -> one `commit/ok` row, `lore_entry_ref` the response's
      `entry_id`, its proposal as sent; an invalid commit -> 422, one
      `commit/refused` row with the response's detail, no canon row written;
   d. every row carries the attempt id and the world's name; a request with
      no attempt id is journaled under a fresh one.
U9 -- the consultation routes (C-05), same client, `lore_plan.chat`,
   `lore_render.chat` and `ollama_client.ping` stubbed:
   a. ping down -> 503 and one `ask/unavailable` row with no model call;
   b. an answered question -> one `ask/ok` row whose `response` equals the
      response body, model calls `[PLAN_USAGE, PROSE_USAGE]`;
   c. an unparsable plan -> 502 and one `ask/parse_error` row keeping the raw
      reply; Ollama failing mid-plan -> 503, one `ask/unavailable` row;
   d. a binding to an unknown ref -> 422 and one `resolve/refused` row; a
      valid resolve -> one `resolve/ok` row under the same attempt.
U10 -- structure. Neither route file calls `write_usage_event` (they go
   through `lore_usage`); `lore_usage.py` contains no `chat(` and no
   `select(`, and imports no consultation-pipeline and no writing-panel
   module.
U11 -- the panels carry the attempt (BRIEF-0103-D), static:
   a. `writePanel.svelte.js`: `blank()` mints `attemptId:
      crypto.randomUUID()`, and its POSTs to `/api/lore/write/questions`,
      `/draft` and `/commit` each send `attempt_id: writeState.attemptId`;
   b. `lore.svelte.js`: `askLore()` mints `loreState.attemptId =
      crypto.randomUUID()` before its POST, both POSTs send `attempt_id:
      loreState.attemptId`, and `reloadForWorld()` clears it;
   c. the built bundle under `cockpit/static/assets` carries `attempt_id`.
U12 -- the reader (BRIEF-0103-E, E1), `scripts/export_lore_usage.py` run as
   a subprocess on this check's database once U3-U9 have filled it:
   a. one line per `(attempt_id, world_ref, kind)` in the journal, each with
      exactly that attempt's events, in order;
   b. U8's write attempt is `committed: true` with its one `lore_entry_ref`;
      U3's (a draft, no commit) is `committed: false`; U9's consultation is
      `committed: null`; U4's attempt is exported with its deleted world's
      name;
   c. `--world-ref` keeps one world's attempts only; `--since` a day after
      today writes an empty file and exits zero;
   d. the script is read-only: no `.add(`, `.commit(`, `.delete(`,
      `.execute(` and no `write_` call;
   e. an `--out` inside the repository is refused (non-zero exit) and no
      file is written there.

Fresh temp-file SQLite database for any fixture rule
(`WORLD_ENGINE_DATABASE_URL` set before any world_engine import) -- never
Nia's DB. A rule that collects zero items is a FAILURE.
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
MIGRATION = ROOT / "scripts" / "migrate_v2_13_lore_usage.py"

FAILURES: list[str] = []

_NAMING_FILES: frozenset[str] = frozenset({
    "models/pipeline.py", "models/__init__.py", "writes/lore_usage.py",
})
_WRITER_CALLERS: frozenset[str] = frozenset({"writes/lore_usage.py", "lore_usage.py"})
_ROUTES = ("cockpit/routes/lore.py", "cockpit/routes/lore_write.py")
_SCRIPTS: frozenset[str] = frozenset({"migrate_v2_13_lore_usage.py", "export_lore_usage.py"})
EXPORT = ROOT / "scripts" / "export_lore_usage.py"
_PIPELINE = {"lore_selectors", "lore_query", "lore_plan", "lore_render", "lore_prompt"}
_PANEL = {"lore_write_apply", "lore_write_draft", "lore_write_read", "lore_mentions_read",
          "lore_choices_read"}
_NOT_NULL = ("attempt_id", "world_ref", "world_name", "kind", "step", "outcome",
             "payload", "model_calls")


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _call(**over) -> dict:
    call = {"usage": "lore_question_to_plan", "prompt_version_id": "pv-1",
            "prompt_version_number": 1, "model": "llama3.1:8b", "system_prompt": "s",
            "user_message": "u", "raw_output": "{}", "error": None}
    call.update(over)
    return call


def _good(**over) -> dict:
    record = {"attempt_id": "att-1", "world_ref": "w-1", "world_name": "Aestia",
              "kind": "write", "step": "draft", "outcome": "ok",
              "payload": {"statement": "s", "answers": None, "draft": {"facts": []}, "error": None},
              "model_calls": [_call()], "lore_entry_ref": None}
    record.update(over)
    return record


_COMMIT_OK = {"proposal": {}, "result": {"entry_id": "le-1"}, "error": None}

_REFUSALS: tuple[tuple[str, dict], ...] = (
    ("empty attempt", _good(attempt_id=" ")),
    ("empty world", _good(world_ref="")),
    ("empty world name", _good(world_name="")),
    ("unknown kind", _good(kind="play")),
    ("step of the other kind", _good(kind="consult", step="draft")),
    ("unknown outcome", _good(outcome="x")),
    ("payload not a dict", _good(payload=["s"])),
    ("payload missing a key", _good(payload={"statement": "s", "draft": {}, "error": None})),
    ("payload of another step", _good(payload={"question": "q", "response": None, "error": None})),
    ("ok with an error", _good(payload={"statement": "s", "answers": None, "draft": None, "error": "x"})),
    ("failure without an error", _good(outcome="unavailable")),
    ("model_calls not a list", _good(model_calls={})),
    ("model call missing a key", _good(model_calls=[{k: v for k, v in _call().items() if k != "error"}])),
    ("model call with an extra key", _good(model_calls=[_call(extra=1)])),
    ("model call without usage", _good(model_calls=[_call(usage="")])),
    ("entry ref on a draft", _good(lore_entry_ref="le-1")),
    ("ok commit without entry ref", _good(step="commit", payload=_COMMIT_OK)),
    ("entry ref on a refused commit", _good(step="commit", outcome="refused", lore_entry_ref="le-1",
                                            payload=dict(_COMMIT_OK, result=None, error="x"))),
)


def _naming(path: pathlib.Path) -> bool:
    text = path.read_text(encoding="utf-8")
    return "LoreUsageEvent" in text or "lore_usage_event" in text


def check_u0() -> None:
    files = sorted(SRC.rglob("*.py"))
    if not files:
        fail("U0: no source file collected")
        return
    named = {p.relative_to(SRC).as_posix() for p in files if _naming(p)}
    for extra in sorted(named - _NAMING_FILES):
        fail(f"U0: {extra} names the journal but is not in _NAMING_FILES")
    for missing in sorted(_NAMING_FILES - named):
        fail(f"U0: {missing} is in _NAMING_FILES but does not name the journal")
    callers = {p.relative_to(SRC).as_posix() for p in files
               if "write_usage_event" in p.read_text(encoding="utf-8")}
    for extra in sorted(callers - _WRITER_CALLERS):
        fail(f"U0: {extra} calls write_usage_event but is not in _WRITER_CALLERS")
    for missing in sorted(_WRITER_CALLERS - callers):
        fail(f"U0: {missing} is in _WRITER_CALLERS but never names write_usage_event")
    scripts = {p.name for p in (ROOT / "scripts").glob("*.py") if _naming(p)}
    if scripts != _SCRIPTS:
        fail(f"U0: scripts naming the journal are {sorted(scripts)}, expected {sorted(_SCRIPTS)}")


def _check_sql(table, name: str) -> str:
    sql = next((str(c.sqltext) for c in table.constraints if getattr(c, "name", None) == name), None)
    if sql is None:
        fail(f"U1: lore_usage_event has no CHECK {name}")
        return ""
    return sql


def check_u1() -> None:
    from world_engine.models import LoreUsageEvent
    from world_engine.models.pipeline import LORE_USAGE_OUTCOMES, LORE_USAGE_STEPS

    table = LoreUsageEvent.__table__
    if "world_id" in table.c:
        fail("U1: lore_usage_event has a world_id column (I1: world_ref, never world_id)")
    fks = [fk.target_fullname for c in table.c for fk in c.foreign_keys]
    if fks:
        fail(f"U1: lore_usage_event declares foreign keys {fks}")
    for name in _NOT_NULL:
        if name not in table.c or table.c[name].nullable:
            fail(f"U1: lore_usage_event.{name} is missing or nullable")
    step_sql = _check_sql(table, "ck_lore_usage_event_step")
    pairs = {(kind, step) for kind, steps in re.findall(r"kind = '([a-z]+)' AND step IN \(([^)]*)\)", step_sql)
             for step in re.findall(r"'([a-z_]+)'", steps)}
    want = {(kind, step) for kind, steps in LORE_USAGE_STEPS.items() for step in steps}
    if not pairs or pairs != want:
        fail(f"U1: ck_lore_usage_event_step lists {sorted(pairs)}, expected {sorted(want)}")
    outcomes = tuple(re.findall(r"'([a-z_]+)'", _check_sql(table, "ck_lore_usage_event_outcome")))
    if outcomes != LORE_USAGE_OUTCOMES:
        fail(f"U1: ck_lore_usage_event_outcome lists {outcomes}, expected {LORE_USAGE_OUTCOMES}")
    _check_sql(table, "ck_lore_usage_event_entry")
    indexes = {i.name: [c.name for c in i.columns] for i in table.indexes}
    if indexes != {"idx_lore_usage_event_attempt": ["attempt_id", "created_at"],
                   "idx_lore_usage_event_world": ["world_ref", "created_at"]}:
        fail(f"U1: lore_usage_event indexes are {indexes}")


def _run_migration(db_path: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True,
                          text=True, cwd=str(ROOT), timeout=120)


def _shape(conn) -> list[tuple[str, int]]:
    return [(r[1], r[3]) for r in conn.execute("PRAGMA table_info(lore_usage_event)")]


def _set_version(db_path: str, version: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE IF EXISTS lore_usage_event")
        conn.execute("UPDATE schema_meta SET static_version = ? WHERE id = 1", (version,))


def check_u2(db_path: str) -> None:
    from sqlmodel import Session

    from world_engine.db import create_db_and_tables, engine
    from world_engine.models import SchemaMeta
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
    from world_engine.writes.lore_usage import write_usage_event

    create_db_and_tables()
    with Session(engine) as session:
        if session.get(SchemaMeta, 1) is None:
            session.add(SchemaMeta(id=1, static_version="v2.12"))
            session.commit()
    engine.dispose()
    with sqlite3.connect(db_path) as conn:
        model_shape = _shape(conn)
        model_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'lore_usage_event'").fetchone()[0]
    if not model_shape:
        fail("U2: the model-created table has no column")
        return
    _set_version(db_path, "v2.11")
    result = _run_migration(db_path)
    with sqlite3.connect(db_path) as conn:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name = 'lore_usage_event'").fetchone()
    if result.returncode == 0 or exists:
        fail(f"U2a: v2.11 was not refused (exit {result.returncode})")
    _set_version(db_path, "v2.12")
    result = _run_migration(db_path)
    with sqlite3.connect(db_path) as conn:
        version = conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0]
        shape = _shape(conn)
        sql = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'lore_usage_event'").fetchone()
        count = conn.execute("SELECT COUNT(*) FROM lore_usage_event").fetchone()[0] if sql else None
    checks = set(re.findall(r"CONSTRAINT (ck_[a-z_]+)", sql[0])) if sql else set()
    want_checks = set(re.findall(r"CONSTRAINT (ck_[a-z_]+)", model_sql))
    if (result.returncode != 0 or count != 0 or version != EXPECTED_STATIC_SCHEMA_VERSION
            or shape != model_shape or not want_checks or checks != want_checks):
        fail(f"U2b: exit {result.returncode}, count {count}, version {version!r}, "
             f"shape {shape} vs {model_shape}, checks {sorted(checks)} vs {sorted(want_checks)}: "
             f"{result.stderr.strip()[-200:]}")
    again = _run_migration(db_path)
    if again.returncode != 0 or "nothing to do" not in again.stdout:
        fail(f"U2c: second run exit {again.returncode}: {again.stdout.strip()[-200:]}")
    with Session(engine) as session:
        event = write_usage_event(session, **_good())
        session.commit()
        event_id = event.id
    with Session(engine) as session:
        from world_engine.models import LoreUsageEvent

        back = session.get(LoreUsageEvent, event_id)
        if back is None or back.payload != _good()["payload"] or back.model_calls != [_call()]:
            fail("U2d: the migrated table does not read back a written row's JSON")
    with sqlite3.connect(db_path) as conn:
        try:
            conn.execute(
                "INSERT INTO lore_usage_event (id, attempt_id, world_ref, world_name, kind, step, "
                "outcome, payload) VALUES ('x', 'a', 'w', 'n', 'write', 'draft', 'x', '{}')")
            fail("U2d: the database accepted outcome 'x'")
        except sqlite3.IntegrityError:
            pass
    engine.dispose()


def _rows(session) -> int:
    from sqlalchemy import text

    return session.exec(text("SELECT COUNT(*) FROM lore_usage_event")).one()[0]


def check_u3() -> None:
    from sqlmodel import Session

    from world_engine.db import engine
    from world_engine.writes.lore_usage import write_usage_event

    with Session(engine) as session:
        before = _rows(session)
        write_usage_event(session, **_good(attempt_id="att-u3"))
        session.commit()
        if _rows(session) != before + 1:
            fail("U3: the good record was not inserted once")
        for label, record in _REFUSALS:
            try:
                write_usage_event(session, **record)
                fail(f"U3: {label!r} was accepted")
            except ValueError:
                pass
            session.rollback()
        if _rows(session) != before + 1:
            fail("U3: a refused record left a row")


def check_u4() -> None:
    from sqlalchemy import text
    from sqlmodel import Session

    from world_engine.db import engine
    from world_engine.models import LoreUsageEvent, World
    from world_engine.writes import delete_world_cascade
    from world_engine.writes.lore_usage import write_usage_event

    with Session(engine) as session:
        world = World(name="Doomed 0103")
        session.add(world)
        session.flush()
        event = write_usage_event(session, **_good(attempt_id="att-u4", world_ref=world.id,
                                                   world_name=world.name))
        session.commit()
        world_id, event_id = world.id, event.id
    with Session(engine) as session:
        delete_world_cascade(world_id, session)
        session.commit()
    with Session(engine) as session:
        gone = session.exec(text("SELECT COUNT(*) FROM world WHERE id = :w").bindparams(w=world_id)).one()[0]
        kept = session.get(LoreUsageEvent, event_id)
        if gone != 0:
            fail("U4: the doomed world was not deleted")
        if kept is None or kept.world_ref != world_id or kept.world_name != "Doomed 0103":
            fail("U4: the journal row did not outlive its world")


def check_u5() -> None:
    import ast
    import dataclasses

    from sqlmodel import Session

    from world_engine import model_exchange, prompt_load
    from world_engine.db import engine
    from world_engine.models import PromptTemplate
    from world_engine.prompt_store import current_prompt
    from world_engine.writes.lore_usage import MODEL_CALL_KEYS

    fields = {f.name for f in dataclasses.fields(model_exchange.ModelExchange)}
    if not fields or fields != MODEL_CALL_KEYS:
        fail(f"U5: ModelExchange fields {sorted(fields)} != MODEL_CALL_KEYS {sorted(MODEL_CALL_KEYS)}")
    tree = ast.parse((SRC / "model_exchange.py").read_text(encoding="utf-8"))
    imports = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
               and (n.level > 0 or (n.module or "").startswith("world_engine"))]
    if imports:
        fail(f"U5: model_exchange.py imports from world_engine at line(s) {[n.lineno for n in imports]}")
    with Session(engine) as db:
        _seed_prompts(db)
        spec = prompt_load.load(db, "lore_question_to_plan")
        template = db.get(PromptTemplate, "pt-lore-question-to-plan")
        version = current_prompt(db, template)
        if (spec.version_id, spec.version_number) != (version.id, version.version_number):
            fail("U5: RenderSpec does not carry the head's current prompt_version")


def _seed_prompts(db) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    import seed_pilot

    from world_engine.models import PromptTemplate

    heads = [
        dict(id="pt-lore-question-to-plan", world_id=None, name="plan", usage="lore_question_to_plan",
             system_prompt=seed_pilot.LORE_QUESTION_TO_PLAN_SYSTEM_PROMPT,
             user_template=seed_pilot.LORE_QUESTION_TO_PLAN_USER_TEMPLATE,
             variables=["selectors", "question"], destination="local"),
        dict(id="pt-lore-rows-to-prose", world_id=None, name="prose", usage="lore_rows_to_prose",
             system_prompt=seed_pilot.LORE_ROWS_TO_PROSE_SYSTEM_PROMPT,
             user_template=seed_pilot.LORE_ROWS_TO_PROSE_USER_TEMPLATE,
             variables=["question", "rows"], destination="local"),
        *seed_pilot.LORE_WRITE_PROMPT_HEADS,
    ]
    for head in heads:
        if db.get(PromptTemplate, head["id"]) is None:
            seed_pilot.upsert_prompt_template(db, **dict(head))
    db.commit()


class _Stub:
    def __init__(self, replies):
        self.replies, self.messages = list(replies), []

    def __call__(self, messages, **kwargs):
        self.messages.append(messages)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply if isinstance(reply, str) else __import__("json").dumps(reply)


def _swap(module, stub):
    original = module.chat
    module.chat = stub
    return original


def _check_exchange(label: str, exchange, usage: str, spec, raw) -> None:
    if (exchange.usage, exchange.prompt_version_id, exchange.prompt_version_number,
            exchange.model, exchange.raw_output) != (usage, spec.version_id, spec.version_number,
                                                     spec.model, raw):
        fail(f"{label}: exchange {exchange.to_record()!r}"[:300])


def check_u6() -> None:
    from sqlmodel import Session

    from world_engine import lore_plan, lore_render, lore_write_draft as lwd, prompt_load
    from world_engine.db import engine
    from world_engine.llm_parse import LlmParseError
    from world_engine.lore_query import LoreResult
    from world_engine.models import World
    from world_engine.ollama_client import OllamaError
    from world_engine.writes.lore_usage import write_usage_event

    collected = []
    with Session(engine) as db:
        _seed_prompts(db)
        world = World(name="Capture 0103")
        db.add(world)
        db.commit()
        plan_spec = prompt_load.load(db, lore_plan.PLAN_USAGE)
        prose_spec = prompt_load.load(db, lore_render.PROSE_USAGE)
        reply = '{"mentions": [], "calls": [{"selector": "world_factions", "args": ["$world"]}]}'
        original = _swap(lore_plan, _Stub([reply, "pas du json"]))
        try:
            exchanges = []
            lore_plan.draft_plan("Quelles factions ?", world.id, db, exchanges)
            if len(exchanges) != 1:
                fail(f"U6a: draft_plan appended {len(exchanges)} exchange(s)")
            else:
                _check_exchange("U6a", exchanges[0], lore_plan.PLAN_USAGE, plan_spec, reply)
                if "Quelles factions ?" not in (exchanges[0].user_message or ""):
                    fail("U6a: the rendered user message was not kept")
            collected += exchanges
            exchanges = []
            try:
                lore_plan.draft_plan("Encore ?", world.id, db, exchanges)
                fail("U6a: an unparsable plan did not raise")
            except LlmParseError:
                pass
            if len(exchanges) != 1 or exchanges[0].raw_output != "pas du json":
                fail("U6a: the unparsable reply was not kept")
        finally:
            lore_plan.chat = original
        answered = LoreResult(verdict="answered", rows=({"section": "factions", "name": "Guilde",
                                                         "faction_type": "guilde"},),
                              trace=[], ambiguous_mentions=(), unmatched_surface_forms=(),
                              rejection_reason=None)
        silent = LoreResult(verdict="silent_canon", rows=(), trace=[], ambiguous_mentions=(),
                            unmatched_surface_forms=(), rejection_reason=None)
        original = _swap(lore_render, _Stub(["Une guilde.", OllamaError("down")]))
        try:
            exchanges = []
            lore_render.render(answered, "Quelles factions ?", prose_spec, {}, exchanges)
            if len(exchanges) != 1:
                fail(f"U6b: render appended {len(exchanges)} exchange(s) on answered")
            else:
                _check_exchange("U6b", exchanges[0], lore_render.PROSE_USAGE, prose_spec, "Une guilde.")
            collected += exchanges
            exchanges = []
            lore_render.render(silent, "Quoi ?", prose_spec, {}, exchanges)
            if exchanges:
                fail("U6b: render appended an exchange on a non-answered verdict")
            rendered = lore_render.render(answered, "Quelles factions ?", prose_spec, {}, exchanges)
            if (rendered.renderer != "template" or len(exchanges) != 1
                    or exchanges[0].raw_output is not None
                    or not (exchanges[0].error or "").startswith("OllamaError")):
                fail(f"U6b: Ollama down left {[e.to_record() for e in exchanges]}"[:300])
            collected += exchanges
        finally:
            lore_render.chat = original
        original = _swap(lwd, _Stub([{"questions": ["Qui ?"]},
                                     {"entities": [], "facts": [], "memberships": [], "controls": []}]))
        try:
            for label, usage, call in (
                ("U6c questions", lwd.QUESTIONS_USAGE,
                 lambda ex: lwd.draft_questions(db, world.id, "Un texte.", ex)),
                ("U6c proposal", lwd.PROPOSAL_USAGE,
                 lambda ex: lwd.draft_proposal(db, world.id, "Un texte.", "", ex)),
            ):
                exchanges = []
                call(exchanges)
                spec = prompt_load.load(db, usage)
                if len(exchanges) != 1:
                    fail(f"{label}: {len(exchanges)} exchange(s)")
                else:
                    _check_exchange(label, exchanges[0], usage, spec, exchanges[0].raw_output or "-")
                    if not exchanges[0].raw_output:
                        fail(f"{label}: no raw reply kept")
                collected += exchanges
        finally:
            lwd.chat = original
        if len(collected) < 5:
            fail(f"U6d: only {len(collected)} exchange(s) collected")
        try:
            write_usage_event(db, **_good(attempt_id="att-u6",
                                          model_calls=[e.to_record() for e in collected]))
            db.rollback()
        except ValueError as exc:
            fail(f"U6d: the writer refused captured exchanges: {exc}")


def _events(db, attempt: str) -> list:
    from sqlmodel import select

    from world_engine.models import LoreUsageEvent

    return list(db.exec(select(LoreUsageEvent).where(LoreUsageEvent.attempt_id == attempt)
                        .order_by(LoreUsageEvent.created_at, LoreUsageEvent.id)).all())


def check_u7() -> None:
    import uuid

    from sqlmodel import Session

    from world_engine import lore_usage
    from world_engine.db import engine
    from world_engine.models import World

    raw = "A0B1C2D3-0000-4000-8000-000000000001"
    if lore_usage.attempt_id(raw) != raw.lower():
        fail("U7: a UUID attempt id is not kept in canonical form")
    minted = [lore_usage.attempt_id(v) for v in (None, "", "pas-un-uuid")]
    if len(set(minted)) != 3 or any(str(uuid.UUID(m)) != m for m in minted):
        fail(f"U7: minted ids {minted}")
    with Session(engine) as db:
        world = World(name="Recorder 0103")
        db.add(world)
        db.commit()
        payload = {"question": "q", "response": None, "error": "x"}
        lore_usage.record(db, attempt="att-u7", world_id=world.id, kind="consult", step="ask",
                          outcome="unavailable", payload=payload)
        lore_usage.record(db, attempt="att-u7", world_id="no-such-world", kind="consult",
                          step="ask", outcome="unavailable", payload=payload)
    with Session(engine) as db:
        names = [e.world_name for e in _events(db, "att-u7")]
        if names != ["Recorder 0103", lore_usage.WORLD_NAME_UNKNOWN]:
            fail(f"U7: recorded world names {names}")


def _route_world(db) -> dict:
    from sqlmodel import select

    from world_engine.models import Entity, Faction, World

    world = World(name="Routes 0103")
    db.add(world)
    db.flush()
    faction = Entity(world_id=world.id, type="faction", name="Guilde des Passeurs")
    db.add(faction)
    db.flush()
    db.add(Faction(id=faction.id))
    for other in db.exec(select(World)).all():
        other.is_active = False
        db.add(other)
    db.flush()
    world.is_active = True
    db.add(world)
    db.commit()
    return {"world": world.id, "faction": faction.id}


def _canon_counts(db) -> dict:
    from sqlalchemy import text

    tables = ("entity", "fact", "knowledge", "lore_entry", "lore_entry_row")
    return {t: db.exec(text(f"SELECT COUNT(*) FROM {t}")).one()[0] for t in tables}


def _one(db, attempt: str, step: str, outcome: str, label: str):
    rows = [e for e in _events(db, attempt) if (e.step, e.outcome) == (step, outcome)]
    if len(rows) != 1:
        fail(f"{label}: {len(rows)} {step}/{outcome} row(s) under {attempt}")
        return None
    return rows[0]


def check_u8() -> None:
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from world_engine import lore_write_draft as lwd
    from world_engine.cockpit.app import app
    from world_engine.db import engine
    from world_engine.ollama_client import OllamaError

    with Session(engine) as db:
        _seed_prompts(db)
        ids = _route_world(db)
    client = TestClient(app, base_url="http://127.0.0.1")
    attempt = "0b0b0b0b-0000-4000-8000-000000000008"
    body = {"statement": "La Guilde des Passeurs garde le port.", "attempt_id": attempt}
    original = _swap(lwd, _Stub([{"questions": ["Qui le sait ?"]}, OllamaError("down"),
                                 {"entities": [], "facts": [], "memberships": [], "controls": []},
                                 "pas du json"]))
    try:
        ok_q = client.post("/api/lore/write/questions", json=body)
        down = client.post("/api/lore/write/questions", json=body)
        draft = client.post("/api/lore/write/draft", json=dict(body, answers="Tout le monde."))
        broken = client.post("/api/lore/write/draft", json=body)
    finally:
        lwd.chat = original
    if (ok_q.status_code, down.status_code, draft.status_code, broken.status_code) != (200, 503, 200, 502):
        fail(f"U8: statuses {ok_q.status_code} {down.status_code} {draft.status_code} {broken.status_code}")
        return
    proposal = {"statement": body["statement"], "entities": [
        {"ref": "e1", "action": "existing", "entity_id": ids["faction"]}], "facts": [
        {"ref": "f1", "action": "create", "facet": "information", "content": "Le port ferme la nuit.",
         "participants": ["e1"], "defaults": [{"scope_type": "world"}], "knowers": []}]}
    with Session(engine) as db:
        before = _canon_counts(db)
    bad = dict(proposal, facts=[dict(proposal["facts"][0], facet="lien")])
    refused = client.post("/api/lore/write/commit", json={"proposal": bad, "attempt_id": attempt})
    with Session(engine) as db:
        if refused.status_code != 422 or _canon_counts(db) != before:
            fail(f"U8c: an invalid commit answered {refused.status_code} or wrote canon")
    done = client.post("/api/lore/write/commit", json={"proposal": proposal, "attempt_id": attempt})
    anonymous = client.post("/api/lore/write/commit", json={"proposal": bad})
    with Session(engine) as db:
        row = _one(db, attempt, "questions", "ok", "U8a")
        if row and (row.payload["questions"] != ["Qui le sait ?"] or len(row.model_calls) != 1):
            fail(f"U8a: questions row {row.payload} / {len(row.model_calls)} call(s)")
        row = _one(db, attempt, "questions", "unavailable", "U8a")
        if row and (row.payload["error"] != lwd.WRITE_UNAVAILABLE_MESSAGE
                    or not (row.model_calls[0]["error"] or "").startswith("OllamaError")):
            fail("U8a: the unavailable row lacks its message or its model call's error")
        row = _one(db, attempt, "draft", "ok", "U8b")
        if row and row.payload["draft"] != draft.json():
            fail("U8b: the draft row is not the response body")
        row = _one(db, attempt, "draft", "parse_error", "U8b")
        if row and row.model_calls[0]["raw_output"] != "pas du json":
            fail("U8b: the parse_error row lost the raw reply")
        row = _one(db, attempt, "commit", "ok", "U8c")
        if row and (done.status_code != 200 or row.lore_entry_ref != done.json().get("entry_id")
                    or row.payload["proposal"] != proposal):
            fail(f"U8c: commit answered {done.status_code}; row {row.lore_entry_ref} {row.payload}"[:300])
        row = _one(db, attempt, "commit", "refused", "U8c")
        if row and row.payload["error"] != refused.json().get("detail"):
            fail("U8c: the refused row does not carry the response's detail")
        rows = _events(db, attempt)
        if len(rows) != 6 or {e.world_name for e in rows} != {"Routes 0103"} \
                or {e.kind for e in rows} != {"write"}:
            fail(f"U8d: {len(rows)} row(s) under the attempt, worlds {[e.world_name for e in rows]}")
        from sqlmodel import select

        from world_engine.models import LoreUsageEvent

        strays = db.exec(select(LoreUsageEvent).where(
            LoreUsageEvent.world_ref == ids["world"], LoreUsageEvent.attempt_id != attempt)).all()
        if anonymous.status_code != 422 or len(strays) != 1:
            fail(f"U8d: a request without attempt id left {len(strays)} row(s) under another id")


def check_u9() -> None:
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from world_engine import lore_plan, lore_render, ollama_client
    from world_engine.cockpit.app import app
    from world_engine.db import engine

    with Session(engine) as db:
        _seed_prompts(db)
        ids = _route_world(db)
    client = TestClient(app, base_url="http://127.0.0.1")
    attempt = "0c0c0c0c-0000-4000-8000-000000000009"
    body = {"question": "Quelles factions ?", "world_id": ids["world"], "attempt_id": attempt}
    plan = {"mentions": [], "calls": [{"selector": "world_factions", "args": ["$world"]}]}
    original_ping = ollama_client.ping

    def down(*args, **kwargs):
        raise ollama_client.OllamaError("down")

    plan_original = _swap(lore_plan, _Stub([plan, "pas du json", ollama_client.OllamaError("down")]))
    prose_original = _swap(lore_render, _Stub(["Une guilde garde le port.", "Toujours elle."]))
    try:
        ollama_client.ping = down
        unavailable = client.post("/api/lore/ask", json=body)
        ollama_client.ping = lambda *a, **k: []
        answered = client.post("/api/lore/ask", json=body)
        broken = client.post("/api/lore/ask", json=body)
        mid = client.post("/api/lore/ask", json=body)
        resolve = {"plan": answered.json().get("plan", plan), "world_id": ids["world"],
                   "question": body["question"], "attempt_id": attempt}
        refused = client.post("/api/lore/resolve", json=dict(resolve, bindings={"m9": ids["faction"]}))
        resolved = client.post("/api/lore/resolve", json=dict(resolve, bindings={}))
    finally:
        ollama_client.ping = original_ping
        lore_plan.chat = plan_original
        lore_render.chat = prose_original
    statuses = (unavailable.status_code, answered.status_code, broken.status_code, mid.status_code,
                refused.status_code, resolved.status_code)
    if statuses != (503, 200, 502, 503, 422, 200):
        fail(f"U9: statuses {statuses}")
        return
    with Session(engine) as db:
        rows = [e for e in _events(db, attempt) if (e.step, e.outcome) == ("ask", "unavailable")]
        if len(rows) != 2 or rows[0].model_calls != [] or len(rows[1].model_calls) != 1:
            fail(f"U9a/c: unavailable rows carry {[len(r.model_calls) for r in rows]} model call(s)")
        row = _one(db, attempt, "ask", "ok", "U9b")
        if row and (row.payload["response"] != answered.json()
                    or [c["usage"] for c in row.model_calls] != [lore_plan.PLAN_USAGE, lore_render.PROSE_USAGE]):
            fail(f"U9b: ask row usages {[c['usage'] for c in row.model_calls]}")
        row = _one(db, attempt, "ask", "parse_error", "U9c")
        if row and row.model_calls[0]["raw_output"] != "pas du json":
            fail("U9c: the parse_error row lost the raw reply")
        row = _one(db, attempt, "resolve", "refused", "U9d")
        if row and row.payload["error"] != refused.json().get("detail"):
            fail("U9d: the refused row does not carry the response's detail")
        row = _one(db, attempt, "resolve", "ok", "U9d")
        if row and (row.payload["response"] != resolved.json() or row.kind != "consult"):
            fail("U9d: the resolve row is not the response body")


def check_u10() -> None:
    import ast

    for rel in _ROUTES:
        if "write_usage_event" in (SRC / rel).read_text(encoding="utf-8"):
            fail(f"U10: {rel} calls write_usage_event directly")
    text = (SRC / "lore_usage.py").read_text(encoding="utf-8")
    for needle in ("chat(", "select("):
        if needle in text:
            fail(f"U10: lore_usage.py contains {needle!r}")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").rsplit(".", 1)[-1])
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            imported.update(alias.name.rsplit(".", 1)[-1] for alias in node.names)
    if not imported:
        fail("U10: no import collected from lore_usage.py")
    hits = imported & (_PIPELINE | _PANEL)
    if hits:
        fail(f"U10: lore_usage.py imports {sorted(hits)}")


def _function_body(text: str, header: str) -> str:
    start = text.find(header)
    if start < 0:
        return ""
    end = text.find("\n}\n", start)
    return text[start:end if end > 0 else len(text)]


def check_u11() -> None:
    lore = ROOT / "frontend" / "src" / "lore"
    write = (lore / "writePanel.svelte.js").read_text(encoding="utf-8")
    if "attemptId: crypto.randomUUID()" not in _function_body(write, "function blank()"):
        fail("U11a: blank() does not mint an attemptId")
    for path in ("questions", "draft", "commit"):
        call = write.find(f"'/api/lore/write/{path}'")
        if call < 0 or "attempt_id: writeState.attemptId" not in write[call:write.find("});", call)]:
            fail(f"U11a: the {path} request does not carry the attempt id")
    consult = (lore / "lore.svelte.js").read_text(encoding="utf-8")
    ask = _function_body(consult, "export async function askLore()")
    minted = ask.find("loreState.attemptId = crypto.randomUUID();")
    if minted < 0 or minted > ask.find("'/api/lore/ask'"):
        fail("U11b: askLore() does not mint an attempt id before its request")
    if consult.count("attempt_id: loreState.attemptId") != 2:
        fail("U11b: the ask and resolve requests do not both carry the attempt id")
    if "loreState.attemptId = '';" not in _function_body(consult, "export function reloadForWorld()"):
        fail("U11b: reloadForWorld() does not clear the attempt id")
    bundles = list((SRC / "cockpit" / "static" / "assets").glob("*.js"))
    if not bundles or not any("attempt_id" in b.read_text(encoding="utf-8") for b in bundles):
        fail("U11c: the built bundle does not carry attempt_id (rebuild the frontend)")


def _export(db_path: str, out: str, *extra: str) -> tuple[subprocess.CompletedProcess, list[dict]]:
    import json

    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    result = subprocess.run([sys.executable, str(EXPORT), "--out", out, *extra], env=env,
                            capture_output=True, text=True, cwd=str(ROOT), timeout=120)
    lines = []
    if result.returncode == 0:
        lines = [json.loads(line) for line in pathlib.Path(out).read_text(encoding="utf-8").splitlines()]
    return result, lines


def check_u12(db_path: str) -> None:
    import ast
    from datetime import date, timedelta

    from sqlmodel import Session, select

    from world_engine.db import engine
    from world_engine.models import LoreUsageEvent

    with Session(engine) as db:
        rows = list(db.exec(select(LoreUsageEvent)).all())
    keys: dict[tuple, int] = {}
    for row in rows:
        keys[(row.attempt_id, row.world_ref, row.kind)] = keys.get((row.attempt_id, row.world_ref, row.kind), 0) + 1
    if len(keys) < 4:
        fail(f"U12: only {len(keys)} attempt(s) to export")
        return
    tmp = tempfile.mkdtemp(prefix="lore_usage_export_")
    result, lines = _export(db_path, f"{tmp}/all.jsonl")
    if result.returncode != 0:
        fail(f"U12a: export exit {result.returncode}: {result.stderr.strip()[-200:]}")
        return
    got = {(a["attempt_id"], a["world_ref"], a["kind"]): len(a["events"]) for a in lines}
    if got != keys or len(lines) != len(keys):
        fail(f"U12a: exported {len(lines)} attempt(s), journal holds {len(keys)}")
    for attempt in lines:
        stamps = [e["created_at"] for e in attempt["events"]]
        if stamps != sorted(stamps):
            fail(f"U12a: attempt {attempt['attempt_id']} events out of order")
    by_id = {a["attempt_id"]: a for a in lines}
    write = by_id.get("0b0b0b0b-0000-4000-8000-000000000008", {})
    if write.get("committed") is not True or len(write.get("lore_entry_refs", [])) != 1:
        fail(f"U12b: the committed write attempt exported as {write.get('committed')!r}")
    if by_id.get("att-u3", {}).get("committed") is not False:
        fail("U12b: an attempt without commit is not committed: false")
    if by_id.get("0c0c0c0c-0000-4000-8000-000000000009", {}).get("committed", "-") is not None:
        fail("U12b: a consultation is not committed: null")
    if by_id.get("att-u4", {}).get("world_name") != "Doomed 0103":
        fail("U12b: the deleted world's attempt is missing or nameless")
    world_ref = write.get("world_ref", "")
    result, lines = _export(db_path, f"{tmp}/one.jsonl", "--world-ref", world_ref)
    if result.returncode != 0 or not lines or {a["world_ref"] for a in lines} != {world_ref}:
        fail(f"U12c: --world-ref exported {[a['world_ref'] for a in lines]}")
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    result, lines = _export(db_path, f"{tmp}/none.jsonl", "--since", tomorrow)
    if result.returncode != 0 or lines:
        fail(f"U12c: --since {tomorrow} exit {result.returncode}, {len(lines)} line(s)")
    inside = ROOT / "tooling" / "verify" / "results" / "lore_usage_refused.jsonl"
    result, _ = _export(db_path, str(inside))
    if result.returncode == 0 or inside.exists():
        fail(f"U12e: an --out inside the repository was accepted (exit {result.returncode})")
        inside.unlink(missing_ok=True)
    tree = ast.parse(EXPORT.read_text(encoding="utf-8"))
    calls = [n.func for n in ast.walk(tree) if isinstance(n, ast.Call)]
    if not calls:
        fail("U12d: no call collected from the export script")
    for func in calls:
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name in ("add", "commit", "delete", "execute") or name.startswith("write_"):
            fail(f"U12d: the export script calls {name}() at line {func.lineno}")


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="lore_usage_")
    db_path = f"{tmp}/u.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    check_u0()
    check_u1()
    check_u2(db_path)
    check_u3()
    check_u4()
    check_u5()
    check_u6()
    check_u7()
    check_u8()
    check_u9()
    check_u10()
    check_u11()
    check_u12(db_path)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: lore_usage -- the journal is named by its model and its writer only; "
          "v2.13 declares it without world_id or FK and migrates from v2.12 only; the "
          "writer refuses every malformed record; a journal row outlives its world; every "
          "Lore model call can be captured with its prompt version and raw reply; every "
          "writing and consultation step is journaled under its attempt, failures included; "
          "both panels send their attempt id; the export reads every attempt and writes nothing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
