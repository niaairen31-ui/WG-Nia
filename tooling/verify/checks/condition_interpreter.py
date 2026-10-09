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

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import ast
import json
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

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


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine
    create_db_and_tables()
    check_na1(engine)
    check_na2(engine)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: condition_interpreter -- one coded list names facts, quest offers and skills by code; "
          "one templated JSON call serves the creator's authoring tools")
    return 0


if __name__ == "__main__":
    sys.exit(main())
