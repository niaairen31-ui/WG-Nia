"""Disposable record/replay harness for the authoring paths (BRIEF-0027-e).

Proves the `llm_parse.py` chokepoint migration (entity_author.py,
region_author.py) is behavior-preserving. Disposable: deleted at
TICKET-0027 stage g along with the transition baselines it exists to
protect (sibling of `harness_say_replay.py`/`harness_mutation_apply.py`,
same DB-copy discipline — never the live DB). `print` is fine here — this
script lives in scripts/, never in src/.

Both `generate_entity_draft` and the region-author pipeline
(`generate_region_manifest` + `generate_region_draft`) are pure
generate-and-return: they write no canon anywhere in their call path, so
there is nothing to dump from the DB — only the returned dict matters.

Record mode: runs one `generate_entity_draft` call (entity-author) and one
`generate_region_manifest` + `generate_region_draft` pair (region-author,
which transitively exercises `generate_entity_draft` and
`generate_npc_goals` per faction/location/NPC) against a REAL Ollama model
on a disposable copy of the live DB. Captures every Ollama request/response
pair (by monkeypatching `ollama_client.chat`) and the returned dict(s).

Replay mode: restores the exact DB snapshot the record run started from,
then re-runs the same calls with the recorded model responses played back
instead of calling Ollama. Diffs the returned dict(s) against the recorded
fixtures. Empty diff = PASS.

Usage:
    python scripts/harness_entity_author_replay.py record
    python scripts/harness_entity_author_replay.py replay
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

FIXTURE_DIR = Path(__file__).parent / "harness_entity_author_fixtures"
WORKDB_PATH = FIXTURE_DIR / "workdb.sqlite"
PRESTATE_PATH = FIXTURE_DIR / "pre_state.sqlite"
ENTITY_CALLS_PATH = FIXTURE_DIR / "entity_calls.json"
ENTITY_RESULT_PATH = FIXTURE_DIR / "entity_result.json"
REGION_CALLS_PATH = FIXTURE_DIR / "region_calls.json"
REGION_RESULT_PATH = FIXTURE_DIR / "region_result.json"

LIVE_DB_PATH = Path.home() / ".world_engine" / "world_engine.db"

ENTITY_BRIEF = (
    "Un forgeron itinérant, taciturne, qui répare des reliques anciennes "
    "contre des faveurs plutôt que de l'argent."
)
REGION_BRIEF = (
    "Un hameau de pêcheurs isolé sur une côte rocheuse, tiraillé entre une "
    "guilde de pêcheurs traditionaliste et une petite loge de contrebandiers."
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


def _install_record_wrapper(modules: list, calls: list[dict], real_chat):
    """`entity_author.py`/`region_author.py` do `from .ollama_client import
    chat` — a direct name import, not a module-attribute lookup — so
    patching `ollama_client.chat` alone doesn't intercept their calls.
    Patch the imported name on each caller module instead. `real_chat` is
    always the pristine, never-wrapped function — callers must not chain
    wrappers by reusing an already-patched module's `.chat`."""

    def chat(messages, model=None, host=None, timeout=300.0, format=None, options=None):
        kwargs = {"timeout": timeout, "format": format, "options": options}
        if model is not None:
            kwargs["model"] = model
        if host is not None:
            kwargs["host"] = host
        result = real_chat(messages, **kwargs)
        calls.append({
            "model": model, "format": format, "options": options,
            "messages": messages, "response": result,
        })
        return result

    for mod in modules:
        mod.chat = chat


def _install_replay_wrapper(modules: list, queue: list[dict], mismatches: list[dict]) -> None:
    state = {"i": 0}

    def chat(messages, model=None, host=None, timeout=300.0, format=None, options=None):
        entry = queue[state["i"]]
        state["i"] += 1
        if entry["messages"] != messages or entry["model"] != model or entry["options"] != options:
            mismatches.append({"index": state["i"] - 1})
        return entry["response"]

    for mod in modules:
        mod.chat = chat


def _run_record() -> None:
    from sqlmodel import Session
    from world_engine import entity_author, region_author
    from world_engine.db import engine
    from world_engine.entity_author import generate_entity_draft
    from world_engine.ollama_client import chat as pristine_chat
    from world_engine.region_author import generate_region_draft, generate_region_manifest

    entity_calls: list[dict] = []
    _install_record_wrapper([entity_author], entity_calls, pristine_chat)
    with Session(engine) as db:
        entity_result = generate_entity_draft("character", ENTITY_BRIEF, db)

    region_calls: list[dict] = []
    _install_record_wrapper([entity_author, region_author], region_calls, pristine_chat)
    with Session(engine) as db:
        manifest_result = generate_region_manifest(REGION_BRIEF, db)
        if not manifest_result.get("ok"):
            raise SystemExit(f"generate_region_manifest failed: {manifest_result.get('error')}")
        region_result = generate_region_draft(manifest_result["manifest"], db)

    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    ENTITY_CALLS_PATH.write_text(json.dumps(entity_calls, ensure_ascii=False, indent=2), encoding="utf-8")
    ENTITY_RESULT_PATH.write_text(json.dumps(entity_result, ensure_ascii=False, indent=2), encoding="utf-8")
    REGION_CALLS_PATH.write_text(json.dumps(region_calls, ensure_ascii=False, indent=2), encoding="utf-8")
    REGION_RESULT_PATH.write_text(
        json.dumps({"manifest": manifest_result, "draft": region_result}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        f"RECORD: entity-author ({len(entity_calls)} Ollama calls), "
        f"region-author ({len(region_calls)} Ollama calls) captured to {FIXTURE_DIR}"
    )


def _run_replay() -> bool:
    from sqlmodel import Session
    from world_engine import entity_author, region_author
    from world_engine.db import engine
    from world_engine.entity_author import generate_entity_draft
    from world_engine.region_author import generate_region_draft, generate_region_manifest

    ok = True

    entity_calls = json.loads(ENTITY_CALLS_PATH.read_text(encoding="utf-8"))
    recorded_entity_result = json.loads(ENTITY_RESULT_PATH.read_text(encoding="utf-8"))
    mismatches: list[dict] = []
    _install_replay_wrapper([entity_author], entity_calls, mismatches)
    with Session(engine) as db:
        entity_result = generate_entity_draft("character", ENTITY_BRIEF, db)
    if mismatches:
        print(f"WARN: entity-author: {len(mismatches)} Ollama request(s) drifted from the recording")
    if entity_result != recorded_entity_result:
        ok = False
        print("FAIL: entity-author result diverged")
        print(f"  recorded: {recorded_entity_result!r}")
        print(f"  replayed: {entity_result!r}")

    region_calls = json.loads(REGION_CALLS_PATH.read_text(encoding="utf-8"))
    recorded_region_result = json.loads(REGION_RESULT_PATH.read_text(encoding="utf-8"))
    mismatches = []
    _install_replay_wrapper([entity_author, region_author], region_calls, mismatches)
    with Session(engine) as db:
        manifest_result = generate_region_manifest(REGION_BRIEF, db)
        region_result = (
            generate_region_draft(manifest_result["manifest"], db)
            if manifest_result.get("ok")
            else None
        )
    if mismatches:
        print(f"WARN: region-author: {len(mismatches)} Ollama request(s) drifted from the recording")
    replayed_region = {"manifest": manifest_result, "draft": region_result}
    if replayed_region != recorded_region_result:
        ok = False
        print("FAIL: region-author result diverged")
        print(f"  recorded: {recorded_region_result!r}")
        print(f"  replayed: {replayed_region!r}")

    print(
        "REPLAY: PASS — entity-author and region-author outputs match the recording"
        if ok else "REPLAY: FAIL — see diffs above"
    )
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
        if not _run_replay():
            raise SystemExit(1)


if __name__ == "__main__":
    main()
