"""Disposable record/replay harness for the world-tick path (TICKET-0028,
BRIEF-0028-a, decision D1).

Proves `run_world_tick`'s decomposition (tick.py -> tick.py + tick_context.py
+ tick_normalize.py) is behavior-preserving. Disposable: deleted at
TICKET-0028's close alongside `harness_say_replay.py` and
`harness_mutation_apply.py` and the two transition baselines. `print` is
fine here — this script lives in scripts/, never in src/.

Record mode: runs a small, fixed set of reference `run_world_tick`
invocations against a REAL Ollama model on a disposable copy of the live
DB (never opens the live DB for writing — only `sqlite3 .backup()` reads it
once). Each invocation mixes a per-NPC batch with a scope call (location or
faction), so together the fixed set traverses BOTH model-call sites
(`tick.py:1460` per-NPC, `tick.py:1675` events) at least once each. Captures
per invocation: (a) every Ollama request/response pair (monkeypatching
`ollama_client.chat`), (b) the return value of `run_world_tick`, (c) a
before/after dump of `proposed_mutation` rows written, UUIDs/timestamps
normalized by stable substitution. `run_world_tick` writes to no other
canon table (T1: "model proposes, code judges") so the dump is scoped to
that one table.

Coverage manifest (mandatory, R-learned-in-0027): record mode also
monkeypatches `assemble_tick_context`, `assemble_location_event_context`,
`assemble_faction_event_context`, `_reachable_locations`,
`_normalize_scope_event`, `_normalize_tick_item`, `_normalize_effect_item`
— wherever each is actually DEFINED (tick.py pre-refactor; tick.py +
tick_context.py + tick_normalize.py post-refactor; every module exposing a
copy of the name is patched, so a call resolved via a `from X import Y`
binding is caught regardless of which side of the refactor is checked
out). Replay refuses to report PASS if the manifest does not show both
call sites fired and all three normalizers ran.

Replay mode: restores the exact DB snapshot the record run started from,
then re-runs the same invocations with the recorded model responses played
back instead of calling Ollama. Diffs the return values and the
`proposed_mutation` dumps against the fixtures. Empty diff + a covering
manifest = PASS.

Usage:
    python scripts/harness_tick_replay.py record
    python scripts/harness_tick_replay.py replay
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

FIXTURE_DIR = Path(__file__).parent / "harness_tick_fixtures"
WORKDB_PATH = FIXTURE_DIR / "workdb.sqlite"
PRESTATE_PATH = FIXTURE_DIR / "pre_state.sqlite"
CALLS_PATH = FIXTURE_DIR / "ollama_calls.json"
RESULTS_PATH = FIXTURE_DIR / "results.json"
DUMPS_PATH = FIXTURE_DIR / "db_dumps.json"
MANIFEST_PATH = FIXTURE_DIR / "coverage_manifest.json"

LIVE_DB_PATH = Path.home() / ".world_engine" / "world_engine.db"

# Two reference invocations. Each mixes a per-NPC batch with a scope call,
# so together they traverse both model-call sites at least twice. "a" uses
# npc-dernier-verre's five present NPCs plus Aurora (owns her own active
# agenda, TON INTRIGUE present -> agenda_step_change chance) against the
# location scope; "b" uses L'Ordre des Seigneurs' four members against the
# faction scope (also an active agenda with an active step -> scope-level
# agenda_step_change chance, plus agenda_delegation targeting a member).
INVOCATIONS: list[dict[str, Any]] = [
    {
        "label": "a",
        "npc_ids": [
            "npc-maelis", "npc-senna", "npc-bryn", "npc-reike", "npc-korin",
            "7f35d5d3-8012-49aa-ba9b-4ef84e44a9c1",  # Aurora
        ],
        "interval_label": "quelques semaines",
        "scope_type": "location",
        "scope_id": "loc-dernier-verre",
    },
    {
        "label": "b",
        "npc_ids": [
            "a6406bac-68ff-4166-9774-478a81dcd2ba",  # Alexandre le puissant Alpha
            "d79cf6ba-1417-45fb-9443-a43af0541e56",  # Théo Dumont
            "1f269bec-eb9a-431c-9fc7-7ededd1ac7ce",  # Aurélien
            "a660ac04-c2bd-4729-a27c-4043b97a1a87",  # Sophia l'influenceuse
        ],
        "interval_label": "quelques semaines",
        "scope_type": "faction",
        "scope_id": "8f738244-62e8-44e6-87c9-57373890a2b1",  # L'Ordre des Seigneurs
    },
]

DUMP_TABLES = ["proposed_mutation"]

TRACKED_FUNCTIONS = (
    "assemble_tick_context",
    "assemble_location_event_context",
    "assemble_faction_event_context",
    "_reachable_locations",
    "_normalize_scope_event",
    "_normalize_tick_item",
    "_normalize_effect_item",
)

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


def _normalize_json_value(value: Any, mapping: dict[tuple[str, str], str]) -> Any:
    if isinstance(value, str):
        return _normalize_text(value, mapping)
    if isinstance(value, list):
        return [_normalize_json_value(v, mapping) for v in value]
    if isinstance(value, dict):
        return {k: _normalize_json_value(v, mapping) for k, v in value.items()}
    return value


def _normalize_results(results: list[dict]) -> list[dict]:
    """`run_world_tick`'s return value embeds a fresh `tick_id` (uuid4) per
    invocation — normalize it the same way `_dump_db` normalizes UUID/
    timestamp columns, so a replay comparison isn't a false FAIL on the
    one intentionally-random field."""
    mapping: dict[tuple[str, str], str] = {}
    return [_normalize_json_value(r, mapping) for r in results]


def _dump_db(db_path: Path) -> dict[str, list[dict]]:
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


def _install_record_wrappers(ollama_client, calls: list[dict]) -> None:
    real_chat = ollama_client.chat

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

    ollama_client.chat = chat


def _install_replay_wrappers(ollama_client, queue: list[dict], mismatches: list[dict]) -> None:
    state = {"i": 0}

    def chat(messages, model=None, host=None, timeout=300.0, format=None, options=None):
        entry = queue[state["i"]]
        state["i"] += 1
        if entry["messages"] != messages or entry["model"] != model or entry["format"] != format:
            mismatches.append({"index": state["i"] - 1})
        return entry["response"]

    ollama_client.chat = chat


def _coverage_modules() -> list[Any]:
    import world_engine.tick as tick_mod
    mods = [tick_mod]
    try:
        import world_engine.tick_context as tick_context_mod
        mods.append(tick_context_mod)
    except ImportError:
        pass
    try:
        import world_engine.tick_normalize as tick_normalize_mod
        mods.append(tick_normalize_mod)
    except ImportError:
        pass
    return mods


def _install_coverage_wrappers(modules: list[Any], hits: dict[str, int]) -> list[tuple[Any, str, Any]]:
    """Patch every copy of every tracked function name found across
    `modules` (a name may be bound in more than one module's namespace via
    a `from X import Y` — see module docstring). Returns the (module, name,
    original) triples needed to undo the patch."""
    originals: list[tuple[Any, str, Any]] = []
    for name in TRACKED_FUNCTIONS:
        hits.setdefault(name, 0)
        for mod in modules:
            if not hasattr(mod, name):
                continue
            original = getattr(mod, name)

            def make_wrapper(fn, key):
                def wrapper(*args, **kwargs):
                    hits[key] += 1
                    return fn(*args, **kwargs)
                return wrapper

            setattr(mod, name, make_wrapper(original, name))
            originals.append((mod, name, original))
    return originals


def _uninstall_coverage_wrappers(originals: list[tuple[Any, str, Any]]) -> None:
    for mod, name, original in originals:
        setattr(mod, name, original)


def _call_site_coverage(calls: list[dict]) -> dict[str, bool]:
    npc_fired = False
    scope_fired = False
    for call in calls:
        user_content = call["messages"][1]["content"] if len(call["messages"]) > 1 else ""
        if user_content.startswith("NPC BRIEFING:"):
            npc_fired = True
        elif user_content.startswith("SCOPE BRIEFING:"):
            scope_fired = True
    return {"npc_call_site": npc_fired, "scope_call_site": scope_fired}


def _manifest_covers(manifest: dict[str, Any]) -> bool:
    call_sites = manifest["call_sites"]
    normalizers = manifest["normalizers"]
    return (
        call_sites["npc_call_site"] and call_sites["scope_call_site"]
        and normalizers["_normalize_scope_event"] > 0
        and normalizers["_normalize_tick_item"] > 0
        and normalizers["_normalize_effect_item"] > 0
    )


def _run_invocations() -> tuple[list[dict], list[dict], dict[str, int]]:
    """Runs INVOCATIONS against the current workdb/engine. Returns
    (results, dumps, coverage_hits). Ollama wrappers must already be
    installed by the caller (record vs replay differ)."""
    from sqlmodel import Session
    from world_engine.db import engine
    from world_engine.tick import run_world_tick

    hits: dict[str, int] = {}
    originals = _install_coverage_wrappers(_coverage_modules(), hits)

    results: list[dict] = []
    dumps: list[dict] = [{"before": _dump_db(WORKDB_PATH)}]
    try:
        for inv in INVOCATIONS:
            with Session(engine) as db:
                result = run_world_tick(
                    db,
                    npc_ids=inv["npc_ids"],
                    interval_label=inv["interval_label"],
                    scope_type=inv["scope_type"],
                    scope_id=inv["scope_id"],
                )
            results.append(result)
            dumps.append({"label": inv["label"], "after": _dump_db(WORKDB_PATH)})
    finally:
        _uninstall_coverage_wrappers(originals)

    return results, dumps, hits


def _run_record() -> None:
    from world_engine import ollama_client

    calls: list[dict] = []
    _install_record_wrappers(ollama_client, calls)

    results, dumps, hits = _run_invocations()

    manifest = {
        "call_sites": _call_site_coverage(calls),
        "normalizers": {
            "_normalize_scope_event": hits.get("_normalize_scope_event", 0),
            "_normalize_tick_item": hits.get("_normalize_tick_item", 0),
            "_normalize_effect_item": hits.get("_normalize_effect_item", 0),
        },
        "assemble_functions": {
            "assemble_tick_context": hits.get("assemble_tick_context", 0),
            "assemble_location_event_context": hits.get("assemble_location_event_context", 0),
            "assemble_faction_event_context": hits.get("assemble_faction_event_context", 0),
            "_reachable_locations": hits.get("_reachable_locations", 0),
        },
    }

    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    CALLS_PATH.write_text(json.dumps(calls, ensure_ascii=False, indent=2), encoding="utf-8")
    RESULTS_PATH.write_text(json.dumps(_normalize_results(results), ensure_ascii=False, indent=2), encoding="utf-8")
    DUMPS_PATH.write_text(json.dumps(dumps, ensure_ascii=False, indent=2), encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"RECORD: {len(calls)} Ollama calls, {len(INVOCATIONS)} invocations captured to {FIXTURE_DIR}")
    print(f"RECORD: coverage manifest = {json.dumps(manifest)}")
    if not _manifest_covers(manifest):
        print(
            "RECORD WARNING: manifest does not yet cover both call sites and all "
            "three normalizers — re-run record (model non-determinism) before trusting replay"
        )


def _run_replay() -> bool:
    from world_engine import ollama_client

    calls = json.loads(CALLS_PATH.read_text(encoding="utf-8"))
    recorded_results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    recorded_dumps = json.loads(DUMPS_PATH.read_text(encoding="utf-8"))
    recorded_manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    if not _manifest_covers(recorded_manifest):
        print("REPLAY: FAIL — recorded coverage manifest does not cover both call sites and all three normalizers")
        print(f"  manifest: {json.dumps(recorded_manifest)}")
        return False

    mismatches: list[dict] = []
    _install_replay_wrappers(ollama_client, calls, mismatches)

    results, dumps, hits = _run_invocations()

    replay_manifest = {
        "call_sites": recorded_manifest["call_sites"],  # replay reuses recorded Ollama traffic verbatim
        "normalizers": {
            "_normalize_scope_event": hits.get("_normalize_scope_event", 0),
            "_normalize_tick_item": hits.get("_normalize_tick_item", 0),
            "_normalize_effect_item": hits.get("_normalize_effect_item", 0),
        },
        "assemble_functions": {
            "assemble_tick_context": hits.get("assemble_tick_context", 0),
            "assemble_location_event_context": hits.get("assemble_location_event_context", 0),
            "assemble_faction_event_context": hits.get("assemble_faction_event_context", 0),
            "_reachable_locations": hits.get("_reachable_locations", 0),
        },
    }
    if not _manifest_covers(replay_manifest):
        print("REPLAY: FAIL — replayed run did not re-traverse both call sites and all three normalizers")
        print(f"  manifest: {json.dumps(replay_manifest)}")
        return False

    ok = True
    if mismatches:
        ok = False
        print(f"FAIL: {len(mismatches)} Ollama request(s) drifted from the recording:")
        for m in mismatches:
            print(f"  call #{m['index']}")

    if _normalize_results(results) != recorded_results:
        ok = False
        print("FAIL: run_world_tick return values diverged")
        for i, (got, want) in enumerate(zip(results, recorded_results)):
            if got != want:
                print(f"  invocation #{i}: recorded={want!r}")
                print(f"  invocation #{i}: replayed={got!r}")

    if dumps != recorded_dumps:
        ok = False
        print("FAIL: proposed_mutation dump diverged")
        for i, (got, want) in enumerate(zip(dumps, recorded_dumps)):
            if got != want:
                print(f"  dump #{i}: recorded={want}")
                print(f"  dump #{i}: replayed={got}")

    print("REPLAY: PASS — empty diff on results and proposed_mutation writes, manifest covers both call sites + all three normalizers" if ok else "REPLAY: FAIL — see diffs above")
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
