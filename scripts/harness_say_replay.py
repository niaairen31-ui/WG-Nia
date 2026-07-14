"""Disposable record/replay harness for the `say` play path (BRIEF-0027-b).

Proves the `say`/`_stream` decomposition (app.py -> cockpit/play.py) is
behavior-preserving. Disposable: deleted at TICKET-0027 stage g along with
the transition baselines it exists to protect. `print` is fine here — this
script lives in scripts/, never in src/.

Record mode: runs N reference /say round-trips against a REAL Ollama model
on a disposable copy of the live DB (one plain narration turn, one turn
addressing an NPC, one turn likely to surface new information to the NPC).
Captures every Ollama request/response pair (by monkeypatching
ollama_client.chat / chat_stream), the full SSE stream text, and normalized
before/after dumps of every table the play path can touch. Never opens the
live DB for writing — only `sqlite3 .backup()` reads it once, to make the
disposable copy.

Replay mode: restores the exact DB snapshot the record run started from,
then re-runs the same N round-trips with the recorded model responses
played back instead of calling Ollama, so everything around the model is
deterministic. Diffs the SSE stream and DB writes against the recorded
fixtures. Empty diff = PASS.

Usage:
    python scripts/harness_say_replay.py record
    python scripts/harness_say_replay.py replay
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

FIXTURE_DIR = Path(__file__).parent / "harness_say_fixtures"
WORKDB_PATH = FIXTURE_DIR / "workdb.sqlite"
PRESTATE_PATH = FIXTURE_DIR / "pre_state.sqlite"
CALLS_PATH = FIXTURE_DIR / "ollama_calls.json"
SSE_PATH = FIXTURE_DIR / "sse_streams.json"
DUMPS_PATH = FIXTURE_DIR / "db_dumps.json"

LIVE_DB_PATH = Path.home() / ".world_engine" / "world_engine.db"

# Gathering conversation at loc-dernier-verre (npc-senna, npc-bryn,
# npc-reike, npc-maelis all present) — exercises the fuller play-path shape,
# including the overhearing pass (Tier 4), which requires bystanders and is
# a structural no-op on a plain 1:1 conversation.
REFERENCE_CONVERSATION_ID = "ebbe55c2-bc9a-4d6c-b584-70d69031db26"

TURNS: list[dict[str, Any]] = [
    # Plain narration: environment action, no NPC addressed -> 'scene'.
    {"content": "Je m'installe en silence à une table et observe la salle."},
    # Addresses one present NPC directly -> 'dialogue'.
    {"content": "Bonsoir Maelis. Comment se porte votre établissement, ce soir ?", "target": "npc-maelis"},
    # Reveals information tied to a subject already tracked in this world's
    # knowledge table, to bystanders -> 'dialogue', likely surfaces an
    # overhearing proposed_mutation for one of the other present NPCs.
    {"content": (
        "Écoutez tous : j'ai vu des signes indéniables de magie près du "
        "Nexus la nuit dernière, comme si l'Éveil avait déjà commencé."
    ), "target": "npc-maelis"},
]

DUMP_TABLES = [
    "conversation", "conversation_message", "proposed_mutation",
    "gathering", "gathering_member", "knowledge", "relation",
    "ledger", "item",
]

_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_TS_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(\+\d{2}:\d{2}|Z)?"
)


def _sqlite_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()
    source = sqlite3.connect(src)
    target = sqlite3.connect(dst)
    try:
        source.backup(target)
    finally:
        source.close()
        target.close()


def _prepare_workdb(mode: str) -> None:
    if mode == "record":
        if not LIVE_DB_PATH.exists():
            raise SystemExit(f"Live DB not found at {LIVE_DB_PATH}")
        _sqlite_copy(LIVE_DB_PATH, WORKDB_PATH)
        _sqlite_copy(LIVE_DB_PATH, PRESTATE_PATH)
    else:
        if not PRESTATE_PATH.exists():
            raise SystemExit(
                f"No recorded pre-state at {PRESTATE_PATH} — run `record` first."
            )
        _sqlite_copy(PRESTATE_PATH, WORKDB_PATH)


def _normalize_text(value: str, mapping: dict[tuple[str, str], str]) -> str:
    def repl_uuid(m: re.Match) -> str:
        key = ("uuid", m.group(0))
        if key not in mapping:
            mapping[key] = f"<uuid:{len(mapping)}>"
        return mapping[key]

    def repl_ts(m: re.Match) -> str:
        key = ("ts", m.group(0))
        if key not in mapping:
            mapping[key] = f"<ts:{len(mapping)}>"
        return mapping[key]

    value = _UUID_RE.sub(repl_uuid, value)
    value = _TS_RE.sub(repl_ts, value)
    return value


def _dump_db(db_path: Path) -> dict[str, list[dict]]:
    """Normalized snapshot of every table the play path can touch.

    Traversal order is fixed (table list order, rowid order, sorted column
    names) so the placeholder mapping for volatile values (UUIDs,
    timestamps) is assigned identically whenever the underlying writes are
    structurally identical — which is exactly the property being tested.
    """
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    mapping: dict[tuple[str, str], str] = {}
    dump: dict[str, list[dict]] = {}
    for table in DUMP_TABLES:
        cur = con.execute(f"SELECT *, rowid FROM {table} ORDER BY rowid")
        rows = []
        for row in cur.fetchall():
            d = dict(row)
            d.pop("rowid", None)
            norm = {}
            for k in sorted(d.keys()):
                v = d[k]
                norm[k] = _normalize_text(v, mapping) if isinstance(v, str) else v
            rows.append(norm)
        dump[table] = rows
    con.close()
    return dump


async def _drain(async_iter) -> str:
    """StreamingResponse wraps even a sync generator into an async iterator
    (starlette iterate_in_threadpool) at construction time — drain it the
    same way the ASGI server would.
    """
    return "".join([chunk async for chunk in async_iter])


def _drain_sse(response) -> str:
    return asyncio.run(_drain(response.body_iterator))


def _install_record_wrappers(ollama_client, calls: list[dict]) -> tuple:
    real_chat = ollama_client.chat
    real_chat_stream = ollama_client.chat_stream

    def chat(messages, model=None, host=None, timeout=300.0, format=None, options=None):
        kwargs = {"timeout": timeout, "format": format, "options": options}
        if model is not None:
            kwargs["model"] = model
        if host is not None:
            kwargs["host"] = host
        result = real_chat(messages, **kwargs)
        calls.append({
            "kind": "chat", "model": model, "format": format,
            "options": options, "messages": messages, "response": result,
        })
        return result

    def chat_stream(messages, model=None, host=None, timeout=300.0, options=None):
        kwargs = {"timeout": timeout, "options": options}
        if model is not None:
            kwargs["model"] = model
        if host is not None:
            kwargs["host"] = host
        chunks = list(real_chat_stream(messages, **kwargs))
        calls.append({
            "kind": "chat_stream", "model": model,
            "options": options, "messages": messages, "response": chunks,
        })
        yield from chunks

    ollama_client.chat = chat
    ollama_client.chat_stream = chat_stream
    return real_chat, real_chat_stream


def _install_replay_wrappers(ollama_client, queue: list[dict], mismatches: list[dict]) -> None:
    state = {"i": 0}

    def _check(entry, kind, messages, model, options, extra=None):
        if entry["kind"] != kind or entry["messages"] != messages or entry["model"] != model or entry["options"] != options or (extra is not None and entry.get("format") != extra):
            mismatches.append({
                "index": state["i"] - 1,
                "expected_kind": entry["kind"], "actual_kind": kind,
            })

    def chat(messages, model=None, host=None, timeout=300.0, format=None, options=None):
        entry = queue[state["i"]]
        state["i"] += 1
        _check(entry, "chat", messages, model, options, extra=format)
        return entry["response"]

    def chat_stream(messages, model=None, host=None, timeout=300.0, options=None):
        entry = queue[state["i"]]
        state["i"] += 1
        _check(entry, "chat_stream", messages, model, options)
        yield from entry["response"]

    ollama_client.chat = chat
    ollama_client.chat_stream = chat_stream


def _run_record() -> None:
    from sqlmodel import Session
    from world_engine import ollama_client
    from world_engine.cockpit.routes.play import SayBody, say
    from world_engine.db import engine

    calls: list[dict] = []
    _install_record_wrappers(ollama_client, calls)

    dumps: dict[str, Any] = {"before": _dump_db(WORKDB_PATH)}
    sse: dict[str, str] = {}

    for n, turn in enumerate(TURNS, start=1):
        with Session(engine) as db:
            response = say(conv_id=REFERENCE_CONVERSATION_ID, body=SayBody(**turn), db=db)
            sse[f"turn_{n}"] = _drain_sse(response)
        dumps[f"after_turn_{n}"] = _dump_db(WORKDB_PATH)

    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    CALLS_PATH.write_text(json.dumps(calls, ensure_ascii=False, indent=2), encoding="utf-8")
    SSE_PATH.write_text(json.dumps(sse, ensure_ascii=False, indent=2), encoding="utf-8")
    DUMPS_PATH.write_text(json.dumps(dumps, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"RECORD: {len(calls)} Ollama calls, {len(TURNS)} turns captured to {FIXTURE_DIR}")


def _run_replay() -> bool:
    from sqlmodel import Session
    from world_engine import ollama_client
    from world_engine.cockpit.routes.play import SayBody, say
    from world_engine.db import engine

    calls = json.loads(CALLS_PATH.read_text(encoding="utf-8"))
    recorded_sse = json.loads(SSE_PATH.read_text(encoding="utf-8"))
    recorded_dumps = json.loads(DUMPS_PATH.read_text(encoding="utf-8"))

    mismatches: list[dict] = []
    _install_replay_wrappers(ollama_client, calls, mismatches)

    dumps: dict[str, Any] = {"before": _dump_db(WORKDB_PATH)}
    sse: dict[str, str] = {}

    for n, turn in enumerate(TURNS, start=1):
        with Session(engine) as db:
            response = say(conv_id=REFERENCE_CONVERSATION_ID, body=SayBody(**turn), db=db)
            sse[f"turn_{n}"] = _drain_sse(response)
        dumps[f"after_turn_{n}"] = _dump_db(WORKDB_PATH)

    ok = True
    if mismatches:
        print(f"WARN: {len(mismatches)} Ollama request(s) drifted from the recording:")
        for m in mismatches:
            print(f"  call #{m['index']}: expected {m['expected_kind']}, saw {m['actual_kind']}")

    for key in recorded_sse:
        if sse.get(key) != recorded_sse[key]:
            ok = False
            print(f"FAIL: SSE stream diverged at {key}")
            print(f"  recorded: {recorded_sse[key]!r}")
            print(f"  replayed: {sse.get(key)!r}")

    for key in recorded_dumps:
        if dumps.get(key) != recorded_dumps[key]:
            ok = False
            print(f"FAIL: DB dump diverged at {key}")
            for table in DUMP_TABLES:
                if dumps.get(key, {}).get(table) != recorded_dumps[key].get(table):
                    print(f"  table={table}")
                    print(f"    recorded: {recorded_dumps[key].get(table)}")
                    print(f"    replayed: {dumps.get(key, {}).get(table)}")

    print("REPLAY: PASS — empty diff on SSE and DB writes" if ok else "REPLAY: FAIL — see diffs above")
    return ok


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("record", "replay"):
        raise SystemExit(__doc__)
    mode = sys.argv[1]
    _prepare_workdb(mode)
    # Point the engine at the disposable copy BEFORE any world_engine import,
    # so db.py binds to it instead of the live DB.
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{WORKDB_PATH}"

    if mode == "record":
        _run_record()
    else:
        ok = _run_replay()
        if not ok:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
