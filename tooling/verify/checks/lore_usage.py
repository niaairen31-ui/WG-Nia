"""G1 check for TICKET-0103 -- the Lore shell's usage journal.

The lot adds its modules brief by brief; this check grows with it (the
`lore_write.py` precedent, TICKET-0098). Each brief adds its rules below in
the same commit.

U0 -- census. The files under `src/world_engine` that name the journal
   (`LoreUsageEvent` or `lore_usage_event`) equal `_NAMING_FILES` exactly,
   and the files that call `write_usage_event` equal `_WRITER_CALLERS`:
   nothing in the application reads the journal, and one module writes it.
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
_WRITER_CALLERS: frozenset[str] = frozenset({"writes/lore_usage.py"})
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
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: lore_usage -- the journal is named by its model and its writer only; "
          "v2.13 declares it without world_id or FK and migrates from v2.12 only; the "
          "writer refuses every malformed record; a journal row outlives its world; every "
          "Lore model call can be captured with its prompt version and raw reply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
