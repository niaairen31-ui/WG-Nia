"""G1 check for TICKET-0112 -- the condition interpreter.

The lot adds its pieces brief by brief; this check grows with it (the
`conditions.py` precedent). Each brief adds its rules here in the same
commit.

NA1 -- one coded list (BRIEF-0112-A, ID1a; import, fixture). `fact_refs`
   declares `CodedRefs` and `code_refs`; no module under `src/` declares or
   names `CodedFacts`. `code_refs("q", ...)` codes pairs in order under its
   prefix, keeps the first of a repeated id, skips an empty id; `resolve`
   tolerates case, spaces and brackets and returns None for a code the list
   did not show, a code of another prefix and a non-string; `code_of` is its
   inverse. `code_facts` returns a `CodedRefs` whose lines read
   `f<n> — <the fact's text>`, skipping a missing fact.
NA2 -- one templated JSON call (BRIEF-0112-A; static, AST, and a stub).
   `prompt_call.call_json` is declared in `prompt_call.py`, which imports
   neither `ollama_client` nor anything under `cockpit`, and calls none of
   `add`, `commit`, `delete`, `execute`, `flush`. `lore_write_draft._call`
   is one `return` of `prompt_call.call_json(..., chat)` with this module's
   `chat`; `lore_write_draft.py` calls `chat` nowhere else. With
   `lore_write_draft.chat` stubbed, `draft_proposal` still reaches the stub
   and records one exchange whose raw output is the stub's reply.
   `lore_write_draft.world_fact_ids` is public and `_world_facts` gone.

NB1 -- the journal's table (BRIEF-0112-B, IH1; import). `condition_draft`
   carries exactly its contract's columns, CHECK names and texts, and its
   two indexes; no column is `world_id` and no column has a FK;
   `CONDITION_DRAFT_OUTCOMES` is the outcome CHECK's list, in order, and
   equals `FIRST_OUTCOMES` with every outcome `CONDITION_DRAFT_MOVES`
   reaches; the role CHECK quotes `CONDITION_ROLES`; `JSON_COLUMN_ALLOWLIST`
   names `ConditionDraft.payload` and `ConditionDraft.model_calls`; the
   code's schema version is v2.21 or later.
NB2 -- the writer (fixture). `write_condition_draft` records a proposal
   with its world's name; refused with a `ValueError` and no row: an
   unknown role, a first outcome `inserted`, a payload missing a key, an
   empty instruction. `move_condition_draft` takes `needs_choice` to
   `proposed` with a new payload and `proposed` to `inserted`, stamping
   `decided_at`; it refuses `proposed` -> `saved`, `refused` -> `inserted`
   and `inserted` -> `discarded`, changing nothing. `mark_draft_saved`
   marks an inserted draft `saved` with its offer and `saved_as_proposed`
   true for the proposed tree and false for another; it returns False and
   writes nothing for a draft of another world, a `proposed` draft, an
   unknown id and None. The database refuses a `saved` row without an
   offer, and an outcome outside the list.
NB3 -- migration `scripts/migrate_v2_21_condition_draft.py` on a database
   without the table: at v2.19 it refuses and creates nothing; at v2.20 it
   creates the table with the model's columns and CHECK names, zero rows,
   and sets `schema_meta` to the code's version; a second run says nothing
   to do; a row written through the writer reads back its JSON.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import ast
import json
import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"
MIGRATION = ROOT / "scripts" / "migrate_v2_21_condition_draft.py"

FAILURES: list[str] = []

_WRITE_CALLS = {"add", "commit", "delete", "execute", "flush"}


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> str:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    return db_path


def _parse(path: pathlib.Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _callee(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _imported(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


class _Stub:
    def __init__(self, replies):
        self.replies, self.messages = list(replies), []

    def __call__(self, messages, **kwargs):
        self.messages.append(messages)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply if isinstance(reply, str) else json.dumps(reply)


# --- NA1 -----------------------------------------------------------------------

def _na1_static() -> None:
    declared = {node.name for node in _parse(SRC / "fact_refs.py").body
                if isinstance(node, (ast.ClassDef, ast.FunctionDef))}
    for name in ("CodedRefs", "code_refs", "code_facts"):
        if name not in declared:
            fail(f"NA1: fact_refs.py does not declare {name}")
    scanned = 0
    for path in sorted(SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        scanned += 1
        if "CodedFacts" in path.read_text(encoding="utf-8"):
            fail(f"NA1: {path.relative_to(ROOT).as_posix()} still names CodedFacts")
    if scanned == 0:
        fail("NA1: scanned zero modules under src/")


def _na1_lists() -> None:
    from world_engine.fact_refs import CodedRefs, code_refs

    coded = code_refs("q", [("o-1", "La fourrure"), ("", "vide"), ("o-2", "Le pont"), ("o-1", "doublon")])
    if not isinstance(coded, CodedRefs) or coded.lines != ("q1 — La fourrure", "q2 — Le pont"):
        fail(f"NA1: code_refs lines read {getattr(coded, 'lines', coded)!r}")
    cases = {"q1": "o-1", " Q2 ": "o-2", "[q2]": "o-2", "q3": None, "f1": None, None: None, 2: None}
    for code, expected in cases.items():
        if coded.resolve(code) != expected:
            fail(f"NA1: resolve({code!r}) gave {coded.resolve(code)!r}, expected {expected!r}")
    if coded.code_of("o-2") != "q2" or coded.code_of("o-9") is not None:
        fail("NA1: code_of is not resolve's inverse")


def _na1_facts(engine) -> None:
    from sqlmodel import Session

    from world_engine.fact_refs import CodedRefs, code_facts
    from world_engine.models import World
    from world_engine.writes.facts import create_fact

    with Session(engine) as session:
        world = World(name="Interprète NA1", is_active=False)
        session.add(world)
        session.flush()
        one = create_fact(session, world_id=world.id, content="Le pont est fragile", created_by="check",
                          facet="information")
        two = create_fact(session, world_id=world.id, content="La rivière monte", created_by="check",
                          facet="information")
        session.commit()
        coded = code_facts(session, [two.id, "no-such-fact", one.id, two.id])
        if not isinstance(coded, CodedRefs) or coded.lines != ("f1 — La rivière monte", "f2 — Le pont est fragile") \
                or coded.resolve("f2") != one.id:
            fail(f"NA1: code_facts reads {coded!r}")


def check_na1(engine) -> None:
    _na1_static()
    _na1_lists()
    _na1_facts(engine)


# --- NA2 -----------------------------------------------------------------------

def _na2_static() -> None:
    call_file = SRC / "prompt_call.py"
    if not call_file.exists():
        fail("NA2: prompt_call.py is missing")
        return
    tree = _parse(call_file)
    if not any(isinstance(n, ast.FunctionDef) and n.name == "call_json" for n in tree.body):
        fail("NA2: prompt_call.py does not declare call_json")
    bad = {m for m in _imported(tree) if "ollama_client" in m or "cockpit" in m}
    if bad:
        fail(f"NA2: prompt_call.py imports {sorted(bad)}")
    writes = {_callee(n) for n in ast.walk(tree) if isinstance(n, ast.Call)} & _WRITE_CALLS
    if writes:
        fail(f"NA2: prompt_call.py calls {sorted(writes)}")
    draft = _parse(SRC / "lore_write_draft.py")
    call = next((n for n in draft.body if isinstance(n, ast.FunctionDef) and n.name == "_call"), None)
    body = [n for n in call.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))] if call else []
    ok = (len(body) == 1 and isinstance(body[0], ast.Return) and isinstance(body[0].value, ast.Call)
          and _callee(body[0].value) == "call_json"
          and isinstance(body[0].value.args[-1], ast.Name) and body[0].value.args[-1].id == "chat")
    if not ok:
        fail("NA2: lore_write_draft._call is not one return of prompt_call.call_json(..., chat)")
    chats = [n for n in ast.walk(draft) if isinstance(n, ast.Call) and _callee(n) == "chat"]
    if chats:
        fail(f"NA2: lore_write_draft.py still calls chat( at line(s) {[n.lineno for n in chats]}")
    names = {n.name for n in draft.body if isinstance(n, ast.FunctionDef)}
    if "world_fact_ids" not in names or "_world_facts" in names:
        fail("NA2: lore_write_draft.world_fact_ids is not the public name of the world facts")


def _seed_lore_prompts(session) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    import seed_pilot
    from world_engine.models import PromptTemplate

    for head in seed_pilot.LORE_WRITE_PROMPT_HEADS:
        if session.get(PromptTemplate, head["id"]) is None:
            seed_pilot.upsert_prompt_template(session, **dict(head))
    session.commit()


def _na2_stub(engine) -> None:
    from sqlmodel import Session

    from world_engine import lore_write_draft as lwd
    from world_engine.models import World

    with Session(engine) as session:
        _seed_lore_prompts(session)
        world = World(name="Interprète NA2", is_active=False)
        session.add(world)
        session.commit()
        reply = json.dumps({"entities": [], "facts": []})
        stub, original = _Stub([reply]), lwd.chat
        lwd.chat = stub
        try:
            exchanges: list = []
            lwd.draft_proposal(session, world.id, "La rivière monte.", exchanges=exchanges)
        finally:
            lwd.chat = original
        if len(stub.messages) != 1 or len(exchanges) != 1 or exchanges[0].raw_output != reply \
                or exchanges[0].usage != lwd.PROPOSAL_USAGE:
            fail(f"NA2: the stubbed draft reached chat {len(stub.messages)} time(s), {len(exchanges)} exchange(s)")


def check_na2(engine) -> None:
    _na2_static()
    _na2_stub(engine)


# --- NB1 -----------------------------------------------------------------------

DRAFT_COLUMNS = ("id", "attempt_id", "world_ref", "world_name", "role", "instruction", "outcome", "retried",
                 "offer_ref", "saved_as_proposed", "payload", "model_calls", "created_at", "decided_at")
DRAFT_CHECKS = {
    "ck_condition_draft_role": "role IN ('eligibility','prerequisite','completion')",
    "ck_condition_draft_outcome": "outcome IN ('proposed','needs_choice','refused','unavailable','parse_error',"
                                  "'inserted','discarded','saved')",
    "ck_condition_draft_saved": "(offer_ref IS NOT NULL) = (outcome = 'saved') "
                                "AND (saved_as_proposed IS NOT NULL) = (outcome = 'saved')",
}
DRAFT_INDEXES = {"idx_condition_draft_attempt": ("attempt_id", "created_at"),
                 "idx_condition_draft_world": ("world_ref", "created_at")}


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def check_nb1() -> None:
    from sqlalchemy import CheckConstraint

    from world_engine.models import CONDITION_DRAFT_OUTCOMES, CONDITION_ROLES, ConditionDraft
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
    from world_engine.writes.condition_drafts import CONDITION_DRAFT_MOVES, FIRST_OUTCOMES

    table = ConditionDraft.__table__
    columns = tuple(c.name for c in table.columns)
    if columns != DRAFT_COLUMNS:
        fail(f"NB1: condition_draft columns are {columns}")
    if any(c.foreign_keys for c in table.columns) or "world_id" in columns:
        fail("NB1: condition_draft carries a FK or a world_id")
    checks = {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}
    if checks != DRAFT_CHECKS:
        fail(f"NB1: condition_draft CHECKs are {checks}")
    indexes = {i.name: tuple(c.name for c in i.columns) for i in table.indexes}
    if indexes != DRAFT_INDEXES:
        fail(f"NB1: condition_draft indexes are {indexes}")
    quoted = tuple(re.findall(r"'([a-z_]+)'", checks.get("ck_condition_draft_outcome", "")))
    reached = set(FIRST_OUTCOMES) | {o for moves in CONDITION_DRAFT_MOVES.values() for o in moves}
    if quoted != CONDITION_DRAFT_OUTCOMES or set(CONDITION_DRAFT_OUTCOMES) != reached:
        fail(f"NB1: outcomes {CONDITION_DRAFT_OUTCOMES} vs CHECK {quoted} vs moves {sorted(reached)}")
    roles = tuple(re.findall(r"'([a-z_]+)'", checks.get("ck_condition_draft_role", "")))
    if roles != CONDITION_ROLES:
        fail(f"NB1: the role CHECK quotes {roles}, not CONDITION_ROLES")
    boundary = (ROOT / "tooling" / "verify" / "checks" / "json_ui_boundary.py").read_text(encoding="utf-8")
    for name in ("ConditionDraft.payload", "ConditionDraft.model_calls"):
        if f'"{name}"' not in boundary:
            fail(f"NB1: JSON_COLUMN_ALLOWLIST does not name {name}")
    if _version_key(EXPECTED_STATIC_SCHEMA_VERSION) < (2, 21):
        fail(f"NB1: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}")


# --- NB2 -----------------------------------------------------------------------

def _payload(**over) -> dict:
    base = {"current": None, "pending": None, "mentions": [], "bindings": {}, "proposed": None,
            "notes": [], "errors": []}
    base.update(over)
    return base


def _nb2_refusals(session, world_id: str) -> None:
    from sqlmodel import func, select

    from world_engine.models import ConditionDraft
    from world_engine.writes.condition_drafts import write_condition_draft

    before = session.exec(select(func.count()).select_from(ConditionDraft)).one()
    bad = {"an unknown role": dict(role="reward"), "a first outcome inserted": dict(outcome="inserted"),
           "a payload missing a key": dict(payload={"current": None}), "an empty instruction": dict(instruction=" ")}
    for label, over in bad.items():
        kwargs = dict(attempt_id="a", world_id=world_id, role="eligibility", instruction="x",
                      outcome="proposed", payload=_payload(), model_calls=[])
        kwargs.update(over)
        try:
            write_condition_draft(session, **kwargs)
            fail(f"NB2: the writer accepted {label}")
        except ValueError:
            pass
    session.rollback()
    if session.exec(select(func.count()).select_from(ConditionDraft)).one() != before:
        fail("NB2: a refused proposal wrote a row")


def _nb2_moves(session, world_id: str) -> None:
    from world_engine.writes.condition_drafts import move_condition_draft, write_condition_draft

    tree = {"op": "leaf", "type": "vital_status", "subject_role": "doer", "subject_entity_id": None,
            "target_entity_id": None, "target_key": None, "threshold": None, "value": "alive"}
    draft = write_condition_draft(session, attempt_id="a", world_id=world_id, role="completion",
                                  instruction="Le joueur est en vie", outcome="needs_choice",
                                  payload=_payload(), model_calls=[])
    session.commit()
    if draft.world_name != "Interprète NB" or draft.decided_at is not None:
        fail(f"NB2: a proposal reads world {draft.world_name!r}, decided {draft.decided_at}")
    move_condition_draft(session, draft, "proposed", _payload(proposed=tree))
    move_condition_draft(session, draft, "inserted")
    session.commit()
    if draft.outcome != "inserted" or draft.payload["proposed"] != tree or draft.decided_at is None:
        fail(f"NB2: the moves left {draft.outcome}, {draft.payload['proposed']}")
    refused = write_condition_draft(session, attempt_id="a", world_id=world_id, role="completion",
                                    instruction="x", outcome="refused", payload=_payload(), model_calls=[])
    proposed = write_condition_draft(session, attempt_id="a", world_id=world_id, role="completion",
                                     instruction="x", outcome="proposed", payload=_payload(), model_calls=[])
    session.commit()
    for row, outcome in ((proposed, "saved"), (refused, "inserted"), (draft, "discarded")):
        was = row.outcome
        try:
            move_condition_draft(session, row, outcome)
            fail(f"NB2: {was} -> {outcome} was allowed")
        except ValueError:
            if row.outcome != was:
                fail(f"NB2: a refused move changed {was} to {row.outcome}")
    return draft, proposed, tree


def _nb2_saved(session, world_id: str, other_world: str, draft, proposed, tree) -> None:
    from world_engine.writes.condition_drafts import mark_draft_saved, move_condition_draft, write_condition_draft

    for label, args in (("another world", (other_world, draft.id)), ("a proposed draft", (world_id, proposed.id)),
                        ("an unknown id", (world_id, "no-such-draft")), ("None", (world_id, None))):
        if mark_draft_saved(session, world_id=args[0], draft_id=args[1], offer_id="offer-1", tree=tree):
            fail(f"NB2: mark_draft_saved marked {label}")
    if proposed.outcome != "proposed" or draft.outcome != "inserted":
        fail("NB2: a skipped mark wrote a row")
    if not mark_draft_saved(session, world_id=world_id, draft_id=draft.id, offer_id="offer-1", tree=dict(tree)):
        fail("NB2: an inserted draft was not marked")
    other = write_condition_draft(session, attempt_id="b", world_id=world_id, role="eligibility",
                                  instruction="y", outcome="proposed", payload=_payload(proposed=tree),
                                  model_calls=[])
    move_condition_draft(session, other, "inserted")
    mark_draft_saved(session, world_id=world_id, draft_id=other.id, offer_id="offer-2",
                     tree={**tree, "value": "dead"})
    session.commit()
    if (draft.outcome, draft.offer_ref, draft.saved_as_proposed) != ("saved", "offer-1", True) \
            or (other.outcome, other.saved_as_proposed) != ("saved", False):
        fail(f"NB2: saved drafts read {draft.outcome, draft.offer_ref, draft.saved_as_proposed}, "
             f"{other.outcome, other.saved_as_proposed}")


def _nb2_database(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        for label, outcome, offer, saved in (("a saved row without offer", "saved", None, None),
                                             ("an outcome outside the list", "accepted", None, None)):
            try:
                conn.execute(
                    "INSERT INTO condition_draft (id, attempt_id, world_ref, world_name, role, instruction, "
                    "outcome, offer_ref, saved_as_proposed, payload) VALUES (?, 'a', 'w', 'n', 'eligibility', "
                    "'x', ?, ?, ?, '{}')", (f"raw-{outcome}", outcome, offer, saved))
                fail(f"NB2: the database accepted {label}")
            except sqlite3.IntegrityError:
                pass


def check_nb2(engine, db_path: str) -> None:
    from sqlmodel import Session

    from world_engine.models import World

    with Session(engine) as session:
        world, other = World(name="Interprète NB", is_active=False), World(name="Autre NB", is_active=False)
        session.add(world)
        session.add(other)
        session.commit()
        _nb2_refusals(session, world.id)
        draft, proposed, tree = _nb2_moves(session, world.id)
        _nb2_saved(session, world.id, other.id, draft, proposed, tree)
    _nb2_database(db_path)


# --- NB3 -----------------------------------------------------------------------

def _run_migration(db_path: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True,
                          text=True, cwd=str(ROOT), timeout=120)


def _draft_state(db_path: str):
    with sqlite3.connect(db_path) as conn:
        sql = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'condition_draft'").fetchone()
        shape = [r[1] for r in conn.execute("PRAGMA table_info(condition_draft)")]
        count = conn.execute("SELECT COUNT(*) FROM condition_draft").fetchone()[0] if sql else None
        version = conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0]
    checks = set(re.findall(r"CONSTRAINT (ck_[a-z_]+)", sql[0])) if sql else set()
    return shape, checks, count, version


def _set_version(db_path: str, version: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE IF EXISTS condition_draft")
        conn.execute("UPDATE schema_meta SET static_version = ? WHERE id = 1", (version,))


def check_nb3() -> None:
    from sqlalchemy import create_engine
    from sqlmodel import Session, SQLModel

    from world_engine.models import ConditionDraft, SchemaMeta, World
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
    from world_engine.writes.condition_drafts import write_condition_draft

    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "migrate.db")
    eng = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(eng)
    with Session(eng) as session:
        session.add(SchemaMeta(id=1, static_version="v2.20"))
        session.commit()
    eng.dispose()
    _set_version(db_path, "v2.19")
    result = _run_migration(db_path)
    if result.returncode == 0 or _draft_state(db_path)[0]:
        fail(f"NB3: v2.19 was not refused (exit {result.returncode})")
    _set_version(db_path, "v2.20")
    result = _run_migration(db_path)
    shape, checks, count, version = _draft_state(db_path)
    if result.returncode != 0 or tuple(shape) != DRAFT_COLUMNS or checks != set(DRAFT_CHECKS) or count != 0 \
            or version != EXPECTED_STATIC_SCHEMA_VERSION:
        fail(f"NB3: exit {result.returncode}, shape {shape}, checks {sorted(checks)}, count {count}, "
             f"version {version}: {result.stderr.strip()[-200:]}")
    again = _run_migration(db_path)
    if again.returncode != 0 or "nothing to do" not in again.stdout:
        fail(f"NB3: a second run exit {again.returncode}: {again.stdout.strip()[-200:]}")
    eng = create_engine(f"sqlite:///{db_path}")
    with Session(eng) as session:
        world = World(name="Migrée", is_active=False)
        session.add(world)
        session.commit()
        payload = _payload(notes=["une note"])
        row = write_condition_draft(session, attempt_id="a", world_id=world.id, role="prerequisite",
                                    instruction="x", outcome="refused", payload=payload,
                                    model_calls=[{"usage": "u"}])
        session.commit()
        back = session.get(ConditionDraft, row.id)
        if back.payload != payload or back.model_calls != [{"usage": "u"}] or back.retried is not False:
            fail("NB3: the migrated table does not read back a written row")
    eng.dispose()


def main() -> int:
    db_path = _fresh_db()
    from world_engine.db import create_db_and_tables, engine
    create_db_and_tables()
    check_na1(engine)
    check_na2(engine)
    check_nb1()
    check_nb2(engine, db_path)
    check_nb3()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: condition_interpreter -- one coded list names facts, quest offers and skills by code; "
          "one templated JSON call serves the creator's authoring tools; v2.21 journals every proposal "
          "of the interpreter, outside any world, its outcome moving one way to « saved »")
    return 0


if __name__ == "__main__":
    sys.exit(main())
